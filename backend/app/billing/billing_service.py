# backend/app/billing/billing_service.py
"""
Lógica de negócios do sistema de billing.
Gerencia trials, assinaturas, pagamentos, suspensões e reativações.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .. import models
from .asaas_client import asaas_client
from ..feature_flags import (
    get_tier, get_features_list_for_plano, get_new_features_for_plano,
    FEATURE_LABELS, MOTOBOYS_POR_TIER, PlanTier, TIER_TO_PLANO,
    ADDON_PRICES, ADDON_MIN_TIER, ADDON_INCLUDED_TIER, ADDON_LABELS,
)

logger = logging.getLogger("superfood.billing")

# Planos fallback (usado quando tabela planos ainda não existe no BD)
PLANOS_FALLBACK = {
    "Básico": {"valor": 169.90, "limite_motoboys": 2, "descricao": "Ideal para começar", "tier": 1},
    "Essencial": {"valor": 279.90, "limite_motoboys": 5, "descricao": "Para restaurantes em crescimento", "tier": 2},
    "Avançado": {"valor": 329.90, "limite_motoboys": 10, "descricao": "Para operações maiores", "tier": 3},
    "Premium": {"valor": 527.00, "limite_motoboys": 999, "descricao": "Sem limites", "tier": 4},
}


def get_planos(db: Session) -> dict:
    """Retorna planos do BD. Fallback para dict hardcoded se tabela não existir."""
    try:
        planos_db = db.query(models.Plano).filter(models.Plano.ativo == True).order_by(models.Plano.ordem).all()
        if planos_db:
            return {
                p.nome: {"valor": p.valor, "limite_motoboys": p.limite_motoboys, "descricao": p.descricao}
                for p in planos_db
            }
    except Exception:
        pass
    return PLANOS_FALLBACK


# Retrocompatibilidade: PLANOS aponta para fallback (usado em imports diretos)
PLANOS = PLANOS_FALLBACK


def _get_config(db: Session) -> models.ConfigBilling:
    config = db.query(models.ConfigBilling).first()
    if not config:
        config = models.ConfigBilling()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def registrar_audit(
    db: Session,
    restaurante_id: int,
    acao: str,
    detalhes: Optional[dict] = None,
    admin_id: Optional[int] = None,
    automatico: bool = False,
):
    log = models.BillingAuditLog(
        restaurante_id=restaurante_id,
        acao=acao,
        detalhes=detalhes,
        admin_id=admin_id,
        automatico=automatico,
    )
    db.add(log)
    db.commit()


async def iniciar_trial(restaurante_id: int, db: Session, admin_id: Optional[int] = None):
    """Inicia período de trial para o restaurante."""
    config = _get_config(db)
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise ValueError("Restaurante não encontrado")

    trial_fim = datetime.utcnow() + timedelta(days=config.trial_dias)

    restaurante.billing_status = "trial"
    restaurante.plano = config.trial_plano
    restaurante.trial_fim = trial_fim
    restaurante.dias_vencido = 0
    restaurante.plano_tier = PlanTier.PREMIUM  # Trial = acesso total

    # Atualizar limites conforme plano do trial
    planos = get_planos(db)
    plano_info = planos.get(config.trial_plano, planos.get("Premium", PLANOS_FALLBACK["Premium"]))
    restaurante.limite_motoboys = plano_info["limite_motoboys"]
    restaurante.valor_plano = plano_info["valor"]

    # Criar customer no Asaas se API configurada
    if asaas_client.configured:
        try:
            asaas_data = await asaas_client.criar_cliente(
                name=restaurante.nome_fantasia or restaurante.nome,
                cpf_cnpj=restaurante.cnpj or "",
                email=restaurante.email,
                phone=restaurante.telefone or "",
            )
            asaas_cliente = models.AsaasCliente(
                restaurante_id=restaurante.id,
                asaas_customer_id=asaas_data["id"],
                nome=restaurante.nome_fantasia or restaurante.nome,
                cpf_cnpj=restaurante.cnpj,
                email=restaurante.email,
                telefone=restaurante.telefone,
            )
            db.add(asaas_cliente)
        except Exception as e:
            logger.warning(f"Erro ao criar customer Asaas para restaurante {restaurante_id}: {e}")

    db.commit()
    registrar_audit(db, restaurante_id, "trial_started", {
        "trial_dias": config.trial_dias,
        "trial_plano": config.trial_plano,
        "trial_fim": trial_fim.isoformat(),
    }, admin_id=admin_id, automatico=admin_id is None)

    return {"trial_fim": trial_fim, "plano": config.trial_plano}


async def selecionar_plano(
    restaurante_id: int,
    plano: str,
    ciclo: str,
    billing_type: str,
    db: Session,
):
    """Restaurante seleciona plano — cria/atualiza assinatura no Asaas."""
    if plano not in PLANOS:
        raise ValueError(f"Plano inválido: {plano}")
    if ciclo not in ("MONTHLY", "YEARLY"):
        raise ValueError(f"Ciclo inválido: {ciclo}")
    if billing_type not in ("PIX", "BOLETO"):
        raise ValueError(f"Tipo de cobrança inválido: {billing_type}")

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise ValueError("Restaurante não encontrado")

    config = _get_config(db)
    planos = get_planos(db)
    plano_info = planos.get(plano, PLANOS_FALLBACK.get(plano, PLANOS_FALLBACK["Básico"]))
    valor = plano_info["valor"]

    # Desconto anual
    desconto = 0.0
    if ciclo == "YEARLY":
        desconto = config.desconto_anual_percentual
        valor = round(valor * 12 * (1 - desconto / 100), 2)


    # Próximo vencimento
    if restaurante.billing_status == "trial" and restaurante.trial_fim and restaurante.trial_fim > datetime.utcnow():
        proximo_vencimento = restaurante.trial_fim
    else:
        proximo_vencimento = datetime.utcnow() + timedelta(days=1)

    # Capturar estado antes de mudar
    was_trial = restaurante.billing_status == "trial"

    # Atualizar plano/limites do restaurante (status será atualizado após Asaas)
    novo_tier = get_tier(plano)

    # Se upgrade para Premium (tier 4) e tem addon bot ativo → auto-desativar (já incluso)
    addon_desativado = False
    if novo_tier >= 4 and getattr(restaurante, "addon_bot_whatsapp", False):
        restaurante.addon_bot_whatsapp = False
        restaurante.addon_bot_valor = 0.0
        restaurante.addon_bot_desativado_em = datetime.utcnow()
        addon_desativado = True
        addon_audit = models.AddonAuditLog(
            restaurante_id=restaurante_id,
            addon="bot_whatsapp",
            acao="auto_desativado",
            valor_anterior=ADDON_PRICES.get("bot_whatsapp", 99.45),
            valor_novo=0,
            motivo=f"Upgrade para plano {plano} (bot incluso)",
        )
        db.add(addon_audit)

    # Se tem addon ativo e troca plano (tier < 4) → somar addon ao valor
    addon_valor = 0.0
    if not addon_desativado and getattr(restaurante, "addon_bot_whatsapp", False):
        addon_valor = ADDON_PRICES.get("bot_whatsapp", 99.45)
        if ciclo == "MONTHLY":
            valor = round(valor + addon_valor, 2)

    restaurante.plano = plano
    restaurante.plano_ciclo = ciclo
    restaurante.valor_plano = valor  # valor por ciclo: mensal ou anual total
    restaurante.limite_motoboys = plano_info["limite_motoboys"]
    restaurante.plano_tier = novo_tier
    restaurante.data_vencimento = proximo_vencimento

    # Criar assinatura no Asaas
    asaas_sub_id = None
    if asaas_client.configured:
        # Validar CPF/CNPJ antes de chamar Asaas
        if not restaurante.cnpj:
            raise ValueError(
                "CPF/CNPJ é obrigatório para ativar cobrança. "
                "Preencha em Configurações antes de selecionar um plano."
            )

        asaas_cli = db.query(models.AsaasCliente).filter(
            models.AsaasCliente.restaurante_id == restaurante_id
        ).first()

        # Customer não existe — criar on-demand
        if not asaas_cli:
            asaas_data = await asaas_client.criar_cliente(
                name=restaurante.nome_fantasia or restaurante.nome,
                cpf_cnpj=restaurante.cnpj,
                email=restaurante.email or "",
                phone=restaurante.telefone or "",
            )
            asaas_cli = models.AsaasCliente(
                restaurante_id=restaurante.id,
                asaas_customer_id=asaas_data["id"],
                nome=restaurante.nome_fantasia or restaurante.nome,
                cpf_cnpj=restaurante.cnpj,
                email=restaurante.email,
                telefone=restaurante.telefone,
            )
            db.add(asaas_cli)
            db.flush()
            logger.info(f"Customer Asaas criado on-demand para restaurante {restaurante_id}")

        # Criar assinatura — se falhar, propaga o erro (não ativa silenciosamente)
        # valor já é o preço correto por ciclo: mensal para MONTHLY, anual total para YEARLY
        sub_data = await asaas_client.criar_assinatura(
            customer_id=asaas_cli.asaas_customer_id,
            billing_type=billing_type,
            value=valor,
            cycle=ciclo,
            next_due_date=proximo_vencimento.strftime("%Y-%m-%d"),
            description=f"Derekh Food - Plano {plano} ({ciclo})",
        )
        asaas_sub_id = sub_data.get("id")

    # Status só muda para "active" APÓS Asaas ter sucesso (ou não estar configurado)
    if restaurante.billing_status in ("manual", "trial"):
        restaurante.billing_status = "active"

    # Salvar assinatura local
    assinatura_existente = db.query(models.AsaasAssinatura).filter(
        models.AsaasAssinatura.restaurante_id == restaurante_id,
        models.AsaasAssinatura.status == "ACTIVE",
    ).first()

    if assinatura_existente:
        assinatura_existente.plano = plano
        assinatura_existente.valor = valor
        assinatura_existente.ciclo = ciclo
        assinatura_existente.billing_type = billing_type
        assinatura_existente.proximo_vencimento = proximo_vencimento
        assinatura_existente.desconto_percentual = desconto
        if asaas_sub_id:
            assinatura_existente.asaas_subscription_id = asaas_sub_id
    else:
        nova_assinatura = models.AsaasAssinatura(
            restaurante_id=restaurante_id,
            asaas_subscription_id=asaas_sub_id,
            plano=plano,
            valor=valor,
            ciclo=ciclo,
            billing_type=billing_type,
            status="ACTIVE",
            proximo_vencimento=proximo_vencimento,
            desconto_percentual=desconto,
            em_trial=was_trial,
            trial_fim=restaurante.trial_fim,
        )
        db.add(nova_assinatura)

    db.commit()
    registrar_audit(db, restaurante_id, "plan_selected", {
        "plano": plano, "ciclo": ciclo, "billing_type": billing_type, "valor": valor,
    })

    return {"plano": plano, "ciclo": ciclo, "valor": valor, "proximo_vencimento": proximo_vencimento}


async def processar_pagamento_confirmado(payment_data: dict, db: Session):
    """Processa pagamento confirmado (webhook ou polling)."""
    asaas_payment_id = payment_data.get("id", "")
    subscription_id = payment_data.get("subscription", "")

    # Buscar pagamento local
    pagamento = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.asaas_payment_id == asaas_payment_id
    ).first()

    if pagamento:
        pagamento.status = "RECEIVED"
        pagamento.data_pagamento = datetime.utcnow()
        pagamento.valor_liquido = payment_data.get("netValue", pagamento.valor)
    else:
        # Buscar restaurante via assinatura
        assinatura = db.query(models.AsaasAssinatura).filter(
            models.AsaasAssinatura.asaas_subscription_id == subscription_id
        ).first()
        restaurante_id = assinatura.restaurante_id if assinatura else None

        if not restaurante_id:
            # Tentar via customer
            customer_id = payment_data.get("customer", "")
            asaas_cli = db.query(models.AsaasCliente).filter(
                models.AsaasCliente.asaas_customer_id == customer_id
            ).first()
            restaurante_id = asaas_cli.restaurante_id if asaas_cli else None

        if restaurante_id:
            pagamento = models.AsaasPagamento(
                restaurante_id=restaurante_id,
                asaas_payment_id=asaas_payment_id,
                asaas_subscription_id=subscription_id,
                valor=payment_data.get("value", 0),
                valor_liquido=payment_data.get("netValue"),
                billing_type=payment_data.get("billingType", "PIX"),
                status="RECEIVED",
                data_vencimento=datetime.fromisoformat(payment_data["dueDate"]) if payment_data.get("dueDate") else None,
                data_pagamento=datetime.utcnow(),
            )
            db.add(pagamento)

    # Reativar restaurante se estava suspenso/overdue
    if pagamento and pagamento.restaurante_id:
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.id == pagamento.restaurante_id
        ).first()
        if restaurante and restaurante.billing_status in ("overdue", "suspended_billing"):
            await reativar_por_pagamento(restaurante, db)

    db.commit()


async def processar_pagamento_vencido(payment_data: dict, db: Session):
    """Marca pagamento como vencido."""
    asaas_payment_id = payment_data.get("id", "")

    pagamento = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.asaas_payment_id == asaas_payment_id
    ).first()

    if pagamento:
        pagamento.status = "OVERDUE"
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.id == pagamento.restaurante_id
        ).first()
        if restaurante and restaurante.billing_status == "active":
            restaurante.billing_status = "overdue"
            restaurante.dias_vencido = 0
            registrar_audit(db, restaurante.id, "payment_overdue", {
                "payment_id": asaas_payment_id,
            }, automatico=True)
    else:
        # Criar registro do pagamento vencido
        subscription_id = payment_data.get("subscription", "")
        assinatura = db.query(models.AsaasAssinatura).filter(
            models.AsaasAssinatura.asaas_subscription_id == subscription_id
        ).first()
        if assinatura:
            pagamento = models.AsaasPagamento(
                restaurante_id=assinatura.restaurante_id,
                asaas_payment_id=asaas_payment_id,
                asaas_subscription_id=subscription_id,
                valor=payment_data.get("value", 0),
                billing_type=payment_data.get("billingType", "PIX"),
                status="OVERDUE",
                data_vencimento=datetime.fromisoformat(payment_data["dueDate"]) if payment_data.get("dueDate") else None,
            )
            db.add(pagamento)

    db.commit()


async def suspender_por_inadimplencia(restaurante: models.Restaurante, db: Session):
    """Suspende restaurante por falta de pagamento."""
    restaurante.billing_status = "suspended_billing"
    restaurante.ativo = False
    restaurante.status = "suspenso"

    # Desativar domínios personalizados
    dominios = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.restaurante_id == restaurante.id,
        models.DominioPersonalizado.ativo == True,
    ).all()
    for dom in dominios:
        dom.ativo = False

    db.commit()
    registrar_audit(db, restaurante.id, "suspended_billing", {
        "dias_vencido": restaurante.dias_vencido,
    }, automatico=True)
    logger.info(f"Restaurante {restaurante.id} suspenso por inadimplência ({restaurante.dias_vencido} dias)")


async def reativar_por_pagamento(restaurante: models.Restaurante, db: Session):
    """Reativa restaurante após pagamento."""
    restaurante.billing_status = "active"
    restaurante.dias_vencido = 0
    restaurante.ativo = True
    restaurante.status = "ativo"

    # Reativar domínios
    dominios = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.restaurante_id == restaurante.id,
        models.DominioPersonalizado.ativo == False,
    ).all()
    for dom in dominios:
        dom.ativo = True

    db.commit()
    registrar_audit(db, restaurante.id, "reactivated_payment", automatico=True)
    logger.info(f"Restaurante {restaurante.id} reativado por pagamento")


async def cancelar_por_inadimplencia(restaurante: models.Restaurante, db: Session):
    """Cancela restaurante após período de suspensão expirado."""
    restaurante.billing_status = "canceled_billing"

    # Cancelar assinatura no Asaas
    assinatura = db.query(models.AsaasAssinatura).filter(
        models.AsaasAssinatura.restaurante_id == restaurante.id,
        models.AsaasAssinatura.status == "ACTIVE",
    ).first()

    if assinatura:
        assinatura.status = "INACTIVE"
        if assinatura.asaas_subscription_id and asaas_client.configured:
            try:
                await asaas_client.cancelar_assinatura(assinatura.asaas_subscription_id)
            except Exception as e:
                logger.warning(f"Erro ao cancelar assinatura Asaas: {e}")

    db.commit()
    registrar_audit(db, restaurante.id, "canceled_billing", {
        "dias_vencido": restaurante.dias_vencido,
    }, automatico=True)
    logger.info(f"Restaurante {restaurante.id} cancelado por inadimplência ({restaurante.dias_vencido} dias)")


def get_billing_status(restaurante: models.Restaurante, db: Session) -> dict:
    """Retorna status completo de billing do restaurante."""
    assinatura = db.query(models.AsaasAssinatura).filter(
        models.AsaasAssinatura.restaurante_id == restaurante.id,
    ).order_by(models.AsaasAssinatura.criado_em.desc()).first()

    # PIX QR code do pagamento mais recente pendente/vencido
    pix_info = None
    pagamento_pendente = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.restaurante_id == restaurante.id,
        models.AsaasPagamento.status.in_(["PENDING", "OVERDUE"]),
    ).order_by(models.AsaasPagamento.data_vencimento.desc()).first()

    if pagamento_pendente:
        pix_info = {
            "qr_code": pagamento_pendente.pix_qr_code,
            "copia_cola": pagamento_pendente.pix_copia_cola,
            "boleto_url": pagamento_pendente.boleto_url,
            "invoice_url": pagamento_pendente.invoice_url,
            "valor": pagamento_pendente.valor,
            "data_vencimento": pagamento_pendente.data_vencimento.isoformat() if pagamento_pendente.data_vencimento else None,
        }

    config = _get_config(db)

    return {
        "billing_status": restaurante.billing_status,
        "plano": restaurante.plano,
        "valor_plano": restaurante.valor_plano,
        "plano_ciclo": restaurante.plano_ciclo or "MONTHLY",
        "trial_fim": restaurante.trial_fim.isoformat() if restaurante.trial_fim else None,
        "dias_vencido": restaurante.dias_vencido or 0,
        "proximo_vencimento": assinatura.proximo_vencimento.isoformat() if assinatura and assinatura.proximo_vencimento else None,
        "billing_type": assinatura.billing_type if assinatura else None,
        "pix_info": pix_info,
        "dias_cancelamento": config.dias_cancelamento,
        "dias_suspensao": config.dias_suspensao,
        # Add-ons
        "addon_bot_whatsapp": bool(getattr(restaurante, "addon_bot_whatsapp", False)),
        "addon_bot_valor": getattr(restaurante, "addon_bot_valor", 0) or 0,
        "valor_base_plano": assinatura.valor_base_plano if assinatura else None,
        "valor_addons": assinatura.valor_addons if assinatura else 0,
    }


async def migrar_restaurante_asaas(restaurante_id: int, db: Session, admin_id: Optional[int] = None):
    """Migra restaurante manual para Asaas (cria customer + subscription)."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise ValueError("Restaurante não encontrado")

    if restaurante.billing_status != "manual":
        raise ValueError(f"Restaurante já está no billing ({restaurante.billing_status})")

    if not asaas_client.configured:
        raise ValueError("Asaas não configurado (ASAAS_API_KEY ausente)")

    # Criar customer
    asaas_cli_existente = db.query(models.AsaasCliente).filter(
        models.AsaasCliente.restaurante_id == restaurante_id
    ).first()

    if not asaas_cli_existente:
        asaas_data = await asaas_client.criar_cliente(
            name=restaurante.nome_fantasia or restaurante.nome,
            cpf_cnpj=restaurante.cnpj or "",
            email=restaurante.email,
            phone=restaurante.telefone or "",
        )
        asaas_cli_existente = models.AsaasCliente(
            restaurante_id=restaurante.id,
            asaas_customer_id=asaas_data["id"],
            nome=restaurante.nome_fantasia or restaurante.nome,
            cpf_cnpj=restaurante.cnpj,
            email=restaurante.email,
            telefone=restaurante.telefone,
        )
        db.add(asaas_cli_existente)
        db.commit()

    # Criar assinatura
    plano = restaurante.plano or "Básico"
    planos = get_planos(db)
    plano_info = planos.get(plano, PLANOS_FALLBACK["Básico"])
    ciclo = restaurante.plano_ciclo or "MONTHLY"
    config = _get_config(db)

    # Calcular valor por ciclo
    valor_assinatura = plano_info["valor"]
    if ciclo == "YEARLY":
        desconto = config.desconto_anual_percentual
        valor_assinatura = round(plano_info["valor"] * 12 * (1 - desconto / 100), 2)

    proximo_vencimento = datetime.utcnow() + timedelta(days=1)

    try:
        sub_data = await asaas_client.criar_assinatura(
            customer_id=asaas_cli_existente.asaas_customer_id,
            billing_type="PIX",
            value=valor_assinatura,
            cycle=ciclo,
            next_due_date=proximo_vencimento.strftime("%Y-%m-%d"),
            description=f"Derekh Food - Plano {plano} ({ciclo})",
        )
        asaas_sub_id = sub_data.get("id")
    except Exception as e:
        logger.warning(f"Erro ao criar assinatura Asaas na migração: {e}")
        asaas_sub_id = None

    assinatura = models.AsaasAssinatura(
        restaurante_id=restaurante_id,
        asaas_subscription_id=asaas_sub_id,
        plano=plano,
        valor=plano_info["valor"],
        ciclo=ciclo,
        billing_type="PIX",
        status="ACTIVE",
        proximo_vencimento=proximo_vencimento,
    )
    db.add(assinatura)

    restaurante.billing_status = "active"
    restaurante.valor_plano = plano_info["valor"]
    restaurante.limite_motoboys = plano_info["limite_motoboys"]
    restaurante.data_vencimento = proximo_vencimento

    db.commit()
    registrar_audit(db, restaurante_id, "migrated_to_asaas", {
        "plano": plano, "asaas_customer_id": asaas_cli_existente.asaas_customer_id,
    }, admin_id=admin_id)

    return {"status": "migrado", "asaas_customer_id": asaas_cli_existente.asaas_customer_id}


def get_planos_disponiveis(db: Session) -> list:
    """Retorna lista de planos com preços mensal e anual + features."""
    config = _get_config(db)
    desconto = config.desconto_anual_percentual
    planos = get_planos(db)

    resultado = []
    for nome, info in planos.items():
        valor_mensal = info["valor"]
        valor_anual_total = round(valor_mensal * 12 * (1 - desconto / 100), 2)
        valor_anual_mensal = round(valor_anual_total / 12, 2)
        tier = info.get("tier") or get_tier(nome)

        # Features cumulativas (todas do tier e abaixo)
        all_features = get_features_list_for_plano(nome)
        # Features novas neste tier
        new_features = get_new_features_for_plano(nome)

        resultado.append({
            "nome": nome,
            "descricao": info["descricao"],
            "limite_motoboys": info["limite_motoboys"],
            "valor_mensal": valor_mensal,
            "valor_anual_total": valor_anual_total,
            "valor_anual_mensal": valor_anual_mensal,
            "desconto_anual_percentual": desconto,
            "tier": tier,
            "features": [
                {"key": f, "label": FEATURE_LABELS.get(f, f), "new": f in new_features}
                for f in all_features
            ],
            "new_features": [
                {"key": f, "label": FEATURE_LABELS.get(f, f)}
                for f in new_features
            ],
        })

    return resultado


async def criar_cobranca_addon_bot(restaurante_id: int, db: Session) -> dict:
    """Cria cobrança avulsa para add-on Bot WhatsApp.
    NÃO ativa o add-on — apenas cria a cobrança Asaas e retorna dados de pagamento.
    O add-on só será ativado quando o webhook confirmar pagamento."""
    from datetime import date

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise ValueError("Restaurante não encontrado")

    tier = getattr(restaurante, "plano_tier", None) or get_tier(restaurante.plano)
    addon_price = ADDON_PRICES.get("bot_whatsapp", 99.45)
    min_tier = ADDON_MIN_TIER.get("bot_whatsapp", 2)
    included_tier = ADDON_INCLUDED_TIER.get("bot_whatsapp", 4)

    # Validações
    if restaurante.billing_status == "trial":
        raise ValueError("Durante o período de teste você já tem acesso ao Bot WhatsApp (Premium).")
    if tier < min_tier:
        raise ValueError(f"Plano mínimo para este add-on é Essencial (Tier {min_tier}). Seu plano atual é {restaurante.plano}.")
    if tier >= included_tier:
        raise ValueError("O Bot WhatsApp já está incluso no seu plano Premium.")
    if restaurante.billing_status not in ("active",):
        raise ValueError("Sua assinatura precisa estar ativa para contratar add-ons.")
    if getattr(restaurante, "addon_bot_whatsapp", False):
        raise ValueError("Add-on Bot WhatsApp já está ativo.")

    # Verificar se já existe cobrança PENDING
    cobranca_pendente = db.query(models.AddonCobranca).filter(
        models.AddonCobranca.restaurante_id == restaurante_id,
        models.AddonCobranca.addon == "bot_whatsapp",
        models.AddonCobranca.status == "PENDING",
    ).first()
    if cobranca_pendente:
        # Retornar dados da cobrança existente
        return {
            "asaas_payment_id": cobranca_pendente.asaas_payment_id,
            "pix_qr_code": cobranca_pendente.pix_qr_code,
            "pix_copia_cola": cobranca_pendente.pix_copia_cola,
            "boleto_url": cobranca_pendente.boleto_url,
            "invoice_url": cobranca_pendente.invoice_url,
            "valor": cobranca_pendente.valor,
            "status": cobranca_pendente.status,
        }

    # Buscar customer Asaas
    asaas_cli = db.query(models.AsaasCliente).filter(
        models.AsaasCliente.restaurante_id == restaurante_id
    ).first()

    if not asaas_cli:
        # Criar customer on-demand
        if not asaas_client.configured:
            raise ValueError("Sistema de pagamento não configurado. Contate o suporte.")
        if not restaurante.cnpj:
            raise ValueError("CPF/CNPJ é obrigatório para cobrança. Preencha em Configurações.")
        asaas_data = await asaas_client.criar_cliente(
            name=restaurante.nome_fantasia or restaurante.nome,
            cpf_cnpj=restaurante.cnpj,
            email=restaurante.email or "",
            phone=restaurante.telefone or "",
        )
        asaas_cli = models.AsaasCliente(
            restaurante_id=restaurante.id,
            asaas_customer_id=asaas_data["id"],
            nome=restaurante.nome_fantasia or restaurante.nome,
            cpf_cnpj=restaurante.cnpj,
            email=restaurante.email,
            telefone=restaurante.telefone,
        )
        db.add(asaas_cli)
        db.flush()

    # Criar cobrança avulsa no Asaas
    vencimento = date.today() + timedelta(days=3)
    ext_ref = f"addon_bot_{restaurante_id}"

    asaas_payment_id = None
    pix_qr_code = None
    pix_copia_cola = None
    boleto_url = None
    invoice_url = None

    if asaas_client.configured:
        payment_data = await asaas_client.criar_cobranca_avulsa(
            customer_id=asaas_cli.asaas_customer_id,
            value=addon_price,
            due_date=vencimento.strftime("%Y-%m-%d"),
            description=f"Derekh Food — Add-on WhatsApp Humanoide (mensal)",
            external_reference=ext_ref,
        )
        asaas_payment_id = payment_data.get("id")
        boleto_url = payment_data.get("bankSlipUrl")
        invoice_url = payment_data.get("invoiceUrl")

        # Buscar QR Code Pix
        if asaas_payment_id:
            try:
                pix_data = await asaas_client.get_pix_qr_code(asaas_payment_id)
                pix_qr_code = pix_data.get("encodedImage", "")
                pix_copia_cola = pix_data.get("payload", "")
            except Exception as e:
                logger.warning(f"Erro ao buscar QR Pix para addon: {e}")

    # Criar registro no BD
    cobranca = models.AddonCobranca(
        restaurante_id=restaurante_id,
        addon="bot_whatsapp",
        asaas_payment_id=asaas_payment_id,
        valor=addon_price,
        billing_type="UNDEFINED",
        status="PENDING",
        data_vencimento=datetime(vencimento.year, vencimento.month, vencimento.day),
        pix_qr_code=pix_qr_code,
        pix_copia_cola=pix_copia_cola,
        boleto_url=boleto_url,
        invoice_url=invoice_url,
        ciclo_numero=1,
    )
    db.add(cobranca)

    restaurante.addon_bot_asaas_payment_id = asaas_payment_id

    # Audit
    addon_audit = models.AddonAuditLog(
        restaurante_id=restaurante_id,
        addon="bot_whatsapp",
        acao="cobranca_criada",
        valor_anterior=0,
        valor_novo=addon_price,
        motivo=f"Cobrança avulsa criada — aguardando pagamento",
    )
    db.add(addon_audit)
    registrar_audit(db, restaurante_id, "addon_cobranca_criada", {
        "addon": "bot_whatsapp",
        "valor": addon_price,
        "asaas_payment_id": asaas_payment_id,
    })

    db.commit()

    return {
        "asaas_payment_id": asaas_payment_id,
        "pix_qr_code": pix_qr_code,
        "pix_copia_cola": pix_copia_cola,
        "boleto_url": boleto_url,
        "invoice_url": invoice_url,
        "valor": addon_price,
        "status": "PENDING",
    }


async def processar_addon_pago(addon_cobranca: "models.AddonCobranca", db: Session):
    """Ativa add-on após confirmação de pagamento via webhook.
    - Marca addon_bot_whatsapp = True
    - Define ciclo_inicio (se primeiro pagamento)
    - Define proximo_vencimento = ciclo_inicio + 1 mês
    - Muda phone_registration_status de pending_payment → pending_code
    - Registra número na Meta WABA automaticamente
    """
    from datetime import date
    from dateutil.relativedelta import relativedelta

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == addon_cobranca.restaurante_id
    ).first()
    if not restaurante:
        logger.error(f"Restaurante {addon_cobranca.restaurante_id} não encontrado ao processar addon pago")
        return

    # Marcar cobrança como paga
    addon_cobranca.status = "RECEIVED"
    addon_cobranca.data_pagamento = datetime.utcnow()

    # Ativar add-on
    addon_price = ADDON_PRICES.get("bot_whatsapp", 99.45)
    restaurante.addon_bot_whatsapp = True
    restaurante.addon_bot_valor = addon_price
    restaurante.addon_bot_ativado_em = datetime.utcnow()
    restaurante.addon_bot_desativado_em = None

    # Ciclo de recorrência
    hoje = date.today()
    if not restaurante.addon_bot_ciclo_inicio:
        restaurante.addon_bot_ciclo_inicio = hoje
        addon_cobranca.ciclo_inicio = hoje

    restaurante.addon_bot_proximo_vencimento = hoje + relativedelta(months=1)
    restaurante.addon_bot_asaas_payment_id = addon_cobranca.asaas_payment_id

    # Registrar número na Meta WABA automaticamente
    bot_config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante.id
    ).first()

    if bot_config and getattr(bot_config, "phone_registration_status", "") == "pending_payment":
        numero = bot_config.whatsapp_numero
        display_name = bot_config.phone_display_name or restaurante.nome_fantasia

        if numero:
            try:
                from ..bot.meta_phone_manager import registrar_numero, solicitar_codigo
                result = await registrar_numero(numero, display_name)
                phone_number_id = result["phone_number_id"]

                import os
                bot_config.meta_phone_number_id = phone_number_id
                bot_config.meta_access_token = os.getenv("META_ACCESS_TOKEN", "")
                bot_config.meta_waba_id = os.getenv("META_WABA_ID", "")
                bot_config.meta_app_secret = os.getenv("META_APP_SECRET", "")
                bot_config.meta_webhook_verify_token = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
                bot_config.whatsapp_provider = "meta"
                bot_config.phone_registration_status = "pending_code"

                # Solicitar código SMS
                try:
                    await solicitar_codigo(phone_number_id, "SMS")
                except Exception as e:
                    logger.warning(f"Erro ao solicitar SMS após pagamento addon: {e}")

                logger.info(f"Número {numero} registrado na WABA após pagamento addon (restaurante {restaurante.id})")
            except Exception as e:
                logger.error(f"Erro ao registrar número após pagamento addon: {e}")
                bot_config.phone_registration_status = "pending_code"

    # Audit
    addon_audit = models.AddonAuditLog(
        restaurante_id=restaurante.id,
        addon="bot_whatsapp",
        acao="ativado",
        valor_anterior=0,
        valor_novo=addon_price,
        motivo=f"Add-on ativado por pagamento confirmado (ciclo {addon_cobranca.ciclo_numero})",
    )
    db.add(addon_audit)
    registrar_audit(db, restaurante.id, "addon_activated", {
        "addon": "bot_whatsapp",
        "addon_price": addon_price,
        "ciclo": addon_cobranca.ciclo_numero,
        "asaas_payment_id": addon_cobranca.asaas_payment_id,
    })

    db.commit()
    logger.info(f"Add-on bot_whatsapp ativado para restaurante {restaurante.id} (pagamento confirmado)")


async def criar_recorrencia_addon(restaurante_id: int, db: Session):
    """Cria nova cobrança mensal para add-on ativo (recorrência manual)."""
    from datetime import date
    from dateutil.relativedelta import relativedelta

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        return

    addon_price = ADDON_PRICES.get("bot_whatsapp", 99.45)

    # Buscar último ciclo
    ultima_cobranca = db.query(models.AddonCobranca).filter(
        models.AddonCobranca.restaurante_id == restaurante_id,
        models.AddonCobranca.addon == "bot_whatsapp",
    ).order_by(models.AddonCobranca.ciclo_numero.desc()).first()

    ciclo_numero = (ultima_cobranca.ciclo_numero or 1) + 1 if ultima_cobranca else 1
    vencimento = date.today() + timedelta(days=3)

    # Buscar customer Asaas
    asaas_cli = db.query(models.AsaasCliente).filter(
        models.AsaasCliente.restaurante_id == restaurante_id
    ).first()

    asaas_payment_id = None
    pix_qr_code = None
    pix_copia_cola = None
    boleto_url = None
    invoice_url = None

    if asaas_client.configured and asaas_cli:
        try:
            payment_data = await asaas_client.criar_cobranca_avulsa(
                customer_id=asaas_cli.asaas_customer_id,
                value=addon_price,
                due_date=vencimento.strftime("%Y-%m-%d"),
                description=f"Derekh Food — Add-on WhatsApp Humanoide (ciclo {ciclo_numero})",
                external_reference=f"addon_bot_{restaurante_id}_c{ciclo_numero}",
            )
            asaas_payment_id = payment_data.get("id")
            boleto_url = payment_data.get("bankSlipUrl")
            invoice_url = payment_data.get("invoiceUrl")

            if asaas_payment_id:
                try:
                    pix_data = await asaas_client.get_pix_qr_code(asaas_payment_id)
                    pix_qr_code = pix_data.get("encodedImage", "")
                    pix_copia_cola = pix_data.get("payload", "")
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Erro ao criar recorrência addon para restaurante {restaurante_id}: {e}")
            return

    cobranca = models.AddonCobranca(
        restaurante_id=restaurante_id,
        addon="bot_whatsapp",
        asaas_payment_id=asaas_payment_id,
        valor=addon_price,
        billing_type="UNDEFINED",
        status="PENDING",
        data_vencimento=datetime(vencimento.year, vencimento.month, vencimento.day),
        pix_qr_code=pix_qr_code,
        pix_copia_cola=pix_copia_cola,
        boleto_url=boleto_url,
        invoice_url=invoice_url,
        ciclo_numero=ciclo_numero,
    )
    db.add(cobranca)

    # Atualizar próximo vencimento
    restaurante.addon_bot_proximo_vencimento = date.today() + relativedelta(months=1)
    restaurante.addon_bot_asaas_payment_id = asaas_payment_id

    db.commit()
    logger.info(f"Recorrência addon bot ciclo {ciclo_numero} criada para restaurante {restaurante_id}")


async def desativar_addon_por_inadimplencia(restaurante_id: int, db: Session):
    """Desativa add-on por falta de pagamento (após 5 dias vencido)."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        return

    restaurante.addon_bot_whatsapp = False
    restaurante.addon_bot_valor = 0.0
    restaurante.addon_bot_desativado_em = datetime.utcnow()

    # Desligar bot
    bot_config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante_id
    ).first()
    if bot_config and bot_config.bot_ativo:
        bot_config.bot_ativo = False

    # Audit
    addon_audit = models.AddonAuditLog(
        restaurante_id=restaurante_id,
        addon="bot_whatsapp",
        acao="auto_desativado",
        valor_anterior=ADDON_PRICES.get("bot_whatsapp", 99.45),
        valor_novo=0,
        motivo="Desativado por inadimplência (pagamento vencido há mais de 5 dias)",
    )
    db.add(addon_audit)
    registrar_audit(db, restaurante_id, "addon_deactivated_overdue", {
        "addon": "bot_whatsapp",
    }, automatico=True)

    db.commit()
    logger.info(f"Add-on bot_whatsapp desativado por inadimplência — restaurante {restaurante_id}")


async def ativar_addon_bot(restaurante_id: int, db: Session):
    """DEPRECATED — Mantido para retrocompatibilidade.
    Agora redireciona para criar_cobranca_addon_bot (billing separado)."""
    return await criar_cobranca_addon_bot(restaurante_id, db)


async def desativar_addon_bot(restaurante_id: int, db: Session):
    """Desativa add-on Bot WhatsApp. Não mexe na assinatura principal (billing separado).
    Cancela cobranças PENDING no Asaas."""

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise ValueError("Restaurante não encontrado")

    if not getattr(restaurante, "addon_bot_whatsapp", False):
        raise ValueError("Add-on Bot WhatsApp não está ativo.")

    addon_price = ADDON_PRICES.get("bot_whatsapp", 99.45)

    # Cancelar cobranças PENDING no Asaas
    cobrancas_pendentes = db.query(models.AddonCobranca).filter(
        models.AddonCobranca.restaurante_id == restaurante_id,
        models.AddonCobranca.addon == "bot_whatsapp",
        models.AddonCobranca.status == "PENDING",
    ).all()

    for cob in cobrancas_pendentes:
        cob.status = "CANCELED"
        if cob.asaas_payment_id and asaas_client.configured:
            try:
                await asaas_client.cancelar_cobranca(cob.asaas_payment_id)
            except Exception as e:
                logger.warning(f"Erro ao cancelar cobrança Asaas {cob.asaas_payment_id}: {e}")

    # Desativar add-on
    restaurante.addon_bot_whatsapp = False
    restaurante.addon_bot_valor = 0.0
    restaurante.addon_bot_desativado_em = datetime.utcnow()

    # Desligar bot ativo
    bot_config = db.query(models.BotConfig).filter(
        models.BotConfig.restaurante_id == restaurante_id
    ).first()
    if bot_config and bot_config.bot_ativo:
        bot_config.bot_ativo = False

    # Audit
    addon_audit = models.AddonAuditLog(
        restaurante_id=restaurante_id,
        addon="bot_whatsapp",
        acao="desativado",
        valor_anterior=addon_price,
        valor_novo=0,
        motivo="Add-on desativado pelo restaurante",
    )
    db.add(addon_audit)
    registrar_audit(db, restaurante_id, "addon_deactivated", {
        "addon": "bot_whatsapp",
        "addon_price": addon_price,
    })

    db.commit()
    return {
        "addon": "bot_whatsapp",
        "desativado": True,
    }


def get_addons_status(restaurante: models.Restaurante, db: Session) -> list:
    """Retorna lista de add-ons com status para o restaurante."""
    tier = getattr(restaurante, "plano_tier", None) or get_tier(restaurante.plano)
    result = []

    for addon_key, price in ADDON_PRICES.items():
        min_tier = ADDON_MIN_TIER.get(addon_key, 2)
        included_tier = ADDON_INCLUDED_TIER.get(addon_key, 4)
        is_trial = restaurante.billing_status == "trial"
        is_included = tier >= included_tier or is_trial
        is_active = bool(getattr(restaurante, f"addon_{addon_key}", False))
        can_subscribe = (
            tier >= min_tier
            and tier < included_tier
            and not is_trial
            and restaurante.billing_status == "active"
            and not is_active
        )

        result.append({
            "key": addon_key,
            "label": ADDON_LABELS.get(addon_key, addon_key),
            "price": price,
            "active": is_active,
            "included": is_included,
            "can_subscribe": can_subscribe,
            "min_tier": min_tier,
            "min_plano": TIER_TO_PLANO.get(min_tier, "Essencial"),
            "included_tier": included_tier,
            "included_plano": TIER_TO_PLANO.get(included_tier, "Premium"),
            "ativado_em": getattr(restaurante, f"addon_{addon_key}_ativado_em", None),
        })

    return result
