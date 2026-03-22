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

logger = logging.getLogger("superfood.billing")

# Planos fallback (usado quando tabela planos ainda não existe no BD)
PLANOS_FALLBACK = {
    "Básico": {"valor": 169.90, "limite_motoboys": 2, "descricao": "Ideal para começar"},
    "Essencial": {"valor": 279.90, "limite_motoboys": 5, "descricao": "Para restaurantes em crescimento"},
    "Avançado": {"valor": 329.90, "limite_motoboys": 10, "descricao": "Para operações maiores"},
    "Premium": {"valor": 527.00, "limite_motoboys": 999, "descricao": "Sem limites"},
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
    restaurante.plano = plano
    restaurante.plano_ciclo = ciclo
    restaurante.valor_plano = valor  # valor por ciclo: mensal ou anual total
    restaurante.limite_motoboys = plano_info["limite_motoboys"]
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
    """Retorna lista de planos com preços mensal e anual."""
    config = _get_config(db)
    desconto = config.desconto_anual_percentual
    planos = get_planos(db)

    resultado = []
    for nome, info in planos.items():
        valor_mensal = info["valor"]
        valor_anual_total = round(valor_mensal * 12 * (1 - desconto / 100), 2)
        valor_anual_mensal = round(valor_anual_total / 12, 2)
        resultado.append({
            "nome": nome,
            "descricao": info["descricao"],
            "limite_motoboys": info["limite_motoboys"],
            "valor_mensal": valor_mensal,
            "valor_anual_total": valor_anual_total,
            "valor_anual_mensal": valor_anual_mensal,
            "desconto_anual_percentual": desconto,
        })
    return resultado
