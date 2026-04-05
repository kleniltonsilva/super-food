# backend/app/pix/pix_service.py
"""
Logica de negocios do sistema Pix Online (Woovi/OpenPix).
Gerencia ativacao, cobrancas, pagamentos, saques e saque automatico.

Modelo de negocio:
- Woovi cobra R$0,85 por transacao Pix — Derekh Food NAO cobra nada do restaurante
- Restaurante NAO precisa ter conta Woovi — subconta 100% virtual
- Saque: R$1,00 por transferencia | Isento para saques >= R$500
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from .. import models
from .woovi_client import woovi_client

logger = logging.getLogger("superfood.pix")

# Taxa de saque em centavos (R$1,00)
TAXA_SAQUE_CENTAVOS = 100
# Valor minimo para isencao de taxa (R$500,00 = 50000 centavos)
ISENCAO_TAXA_CENTAVOS = 50000

TIPOS_CHAVE_VALIDOS = ("cpf", "cnpj", "email", "celular", "aleatoria")


async def ativar_pix(
    restaurante_id: int,
    pix_chave: str,
    tipo_chave: str,
    nome: str,
    db: Session,
) -> dict:
    """
    Ativa Pix Online para o restaurante.

    - Valida tipo de chave
    - Verifica se ja esta ativo
    - Cria subconta Woovi
    - Cria/atualiza PixConfig no BD
    """
    # Validar tipo de chave
    tipo_chave = tipo_chave.strip().lower()
    if tipo_chave not in TIPOS_CHAVE_VALIDOS:
        raise ValueError(
            f"Tipo de chave invalido: {tipo_chave}. "
            f"Valores aceitos: {', '.join(TIPOS_CHAVE_VALIDOS)}"
        )

    pix_chave = pix_chave.strip()
    nome = nome.strip()

    if not pix_chave:
        raise ValueError("Chave Pix e obrigatoria")
    if not nome:
        raise ValueError("Nome da subconta e obrigatorio")

    # Verificar se ja existe config ativa
    config_existente = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
    ).first()

    if config_existente and config_existente.ativo:
        raise ValueError(
            "Pix Online ja esta ativo para este restaurante. "
            "Desative primeiro para alterar a chave."
        )

    # Criar subconta na Woovi
    if woovi_client.configured:
        try:
            await woovi_client.criar_subconta(pix_chave, nome)
            logger.info(
                f"Subconta Woovi criada para restaurante {restaurante_id}: "
                f"{tipo_chave} {pix_chave[:4]}***"
            )
        except Exception as e:
            logger.error(
                f"Erro ao criar subconta Woovi para restaurante {restaurante_id}: {e}"
            )
            raise ValueError(
                f"Erro ao criar subconta de pagamento: {e}. "
                "Verifique se a chave Pix esta correta."
            )
    else:
        logger.warning(
            "Woovi nao configurado (WOOVI_APP_ID ausente). "
            f"PixConfig salvo localmente para restaurante {restaurante_id}."
        )

    # Criar ou atualizar PixConfig
    agora = datetime.utcnow()

    if config_existente:
        config_existente.pix_chave = pix_chave
        config_existente.tipo_chave = tipo_chave
        config_existente.nome_subconta = nome
        config_existente.ativo = True
        config_existente.ativado_em = agora
        config_existente.termos_aceitos_em = agora
        config = config_existente
    else:
        config = models.PixConfig(
            restaurante_id=restaurante_id,
            pix_chave=pix_chave,
            tipo_chave=tipo_chave,
            nome_subconta=nome,
            ativo=True,
            ativado_em=agora,
            termos_aceitos_em=agora,
            saque_automatico=False,
            saque_minimo_centavos=50000,  # R$500,00
        )
        db.add(config)

    db.commit()
    db.refresh(config)

    logger.info(f"Pix ativado para restaurante {restaurante_id}")

    return {
        "id": config.id,
        "restaurante_id": config.restaurante_id,
        "pix_chave": config.pix_chave,
        "tipo_chave": config.tipo_chave,
        "nome_subconta": config.nome_subconta,
        "ativo": config.ativo,
        "ativado_em": config.ativado_em.isoformat() if config.ativado_em else None,
        "saque_automatico": config.saque_automatico,
        "saque_minimo_centavos": config.saque_minimo_centavos,
    }


async def desativar_pix(restaurante_id: int, db: Session):
    """
    Desativa Pix Online para o restaurante.
    Nao deleta a subconta Woovi — apenas marca como inativo no BD.
    """
    config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
    ).first()

    if not config:
        raise ValueError("Pix Online nao esta configurado para este restaurante")

    if not config.ativo:
        raise ValueError("Pix Online ja esta desativado")

    config.ativo = False
    config.saque_automatico = False
    db.commit()

    logger.info(f"Pix desativado para restaurante {restaurante_id}")


async def get_pix_status(restaurante_id: int, db: Session) -> dict:
    """
    Retorna status completo do Pix para o restaurante.

    Inclui: config, saldo em tempo real (se ativo), ultimos saques.
    """
    config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
    ).first()

    if not config:
        return {
            "ativo": False,
            "pix_chave": None,
            "tipo_chave": None,
            "nome_subconta": None,
            "saldo_centavos": 0,
            "saque_automatico": False,
            "saque_minimo_centavos": 50000,
            "ultimos_saques": [],
        }

    # Consultar saldo em tempo real se ativo
    saldo_centavos = 0
    if config.ativo and woovi_client.configured:
        try:
            resp = await woovi_client.consultar_saldo(config.pix_chave)
            # A API retorna o saldo dentro de subaccount.balance
            subaccount = resp.get("subaccount", resp)
            saldo_centavos = subaccount.get("balance", 0)
        except Exception as e:
            logger.warning(
                f"Erro ao consultar saldo Woovi para restaurante {restaurante_id}: {e}"
            )

    # Ultimos 10 saques
    saques = (
        db.query(models.PixSaque)
        .filter(models.PixSaque.restaurante_id == restaurante_id)
        .order_by(models.PixSaque.solicitado_em.desc())
        .limit(10)
        .all()
    )

    ultimos_saques = [
        {
            "id": s.id,
            "valor_centavos": s.valor_centavos,
            "taxa_centavos": s.taxa_centavos,
            "valor_liquido_centavos": s.valor_centavos - s.taxa_centavos,
            "status": s.status,
            "automatico": s.automatico,
            "solicitado_em": s.solicitado_em.isoformat() if s.solicitado_em else None,
            "concluido_em": s.concluido_em.isoformat() if s.concluido_em else None,
        }
        for s in saques
    ]

    return {
        "ativo": config.ativo,
        "pix_chave": config.pix_chave,
        "tipo_chave": config.tipo_chave,
        "nome_subconta": config.nome_subconta,
        "saldo_centavos": saldo_centavos,
        "saque_automatico": config.saque_automatico,
        "saque_minimo_centavos": config.saque_minimo_centavos,
        "ativado_em": config.ativado_em.isoformat() if config.ativado_em else None,
        "ultimos_saques": ultimos_saques,
    }


async def criar_cobranca_pedido(pedido_id: int, db: Session) -> dict:
    """
    Gera cobranca Pix (QR Code) para um pedido.

    - Busca pedido e config Pix do restaurante
    - Cria cobranca na Woovi com split para subconta do restaurante (valor - taxa 0,80%)
    - Registra PixCobranca no BD
    - Retorna QR code, br_code e dados da cobranca
    """
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
    ).first()

    if not pedido:
        raise ValueError("Pedido nao encontrado")

    pix_config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == pedido.restaurante_id,
        models.PixConfig.ativo == True,
    ).first()

    if not pix_config:
        raise ValueError("Pix Online nao esta ativo para este restaurante")

    # Verificar se ja existe cobranca ativa para este pedido
    cobranca_existente = db.query(models.PixCobranca).filter(
        models.PixCobranca.pedido_id == pedido_id,
        models.PixCobranca.status.in_(["ACTIVE", "PENDING"]),
    ).first()

    if cobranca_existente:
        return {
            "cobranca_id": cobranca_existente.id,
            "correlation_id": cobranca_existente.correlation_id,
            "qr_code_image": cobranca_existente.qr_code_imagem,
            "br_code": cobranca_existente.br_code,
            "payment_link_url": cobranca_existente.payment_link_url or "",
            "valor_centavos": cobranca_existente.valor_centavos,
            "expira_em": cobranca_existente.expira_em.isoformat() if cobranca_existente.expira_em else None,
        }

    # Gerar correlation ID unico
    correlation_id = f"derekh_{pedido_id}_{uuid.uuid4().hex[:8]}"

    # Calcular valor em centavos
    valor_centavos = int(round(pedido.valor_total * 100))
    if valor_centavos <= 0:
        raise ValueError("Valor do pedido deve ser maior que zero")

    # Criar cobranca na Woovi
    if not woovi_client.configured:
        raise ValueError("Woovi nao configurado (WOOVI_APP_ID ausente)")

    try:
        resultado = await woovi_client.criar_cobranca(
            valor_centavos=valor_centavos,
            correlation_id=correlation_id,
            pix_chave_restaurante=pix_config.pix_chave,
            descricao=f"Pedido #{pedido.comanda} - Derekh Food",
        )
    except Exception as e:
        logger.error(f"Erro ao criar cobranca Woovi para pedido {pedido_id}: {e}")
        raise ValueError(f"Erro ao gerar cobranca Pix: {e}")

    # Extrair dados da resposta Woovi
    charge = resultado.get("charge", resultado)
    woovi_charge_id = charge.get("correlationID", correlation_id)
    qr_code_imagem = charge.get("qrCodeImage", "")
    br_code = charge.get("brCode", "")
    payment_link_url = charge.get("paymentLinkUrl", "")
    transaction_id = charge.get("transactionID", "")

    # Expiracao: 30 minutos a partir de agora
    expira_em = datetime.utcnow() + timedelta(minutes=30)

    # Registrar cobranca no BD
    cobranca = models.PixCobranca(
        restaurante_id=pedido.restaurante_id,
        pedido_id=pedido_id,
        woovi_charge_id=woovi_charge_id,
        correlation_id=correlation_id,
        transaction_id=transaction_id,
        valor_centavos=valor_centavos,
        status="ACTIVE",
        qr_code_imagem=qr_code_imagem,
        br_code=br_code,
        payment_link_url=payment_link_url,
        expira_em=expira_em,
        criado_em=datetime.utcnow(),
    )
    db.add(cobranca)
    db.commit()
    db.refresh(cobranca)

    logger.info(
        f"Cobranca Pix criada para pedido {pedido_id}: "
        f"R${valor_centavos/100:.2f} (correlation: {correlation_id})"
    )

    return {
        "cobranca_id": cobranca.id,
        "correlation_id": correlation_id,
        "qr_code_image": qr_code_imagem,
        "br_code": br_code,
        "payment_link_url": payment_link_url,
        "valor_centavos": valor_centavos,
        "expira_em": expira_em.isoformat(),
    }


async def processar_pagamento_confirmado(
    charge_id: str,
    db: Session,
    ws_manager=None,
):
    """
    Processa pagamento Pix confirmado (webhook OPENPIX:CHARGE_COMPLETED).

    - Encontra PixCobranca pelo charge_id ou correlation_id
    - Atualiza status para COMPLETED
    - Atualiza pedido: pendente → em_preparo (pix pago = vai pra cozinha)
    - Se KDS ativo: cria PedidoCozinha
    - Notifica restaurante via WebSocket
    - Se pedido veio do WhatsApp bot: envia mensagem de confirmação via Evolution
    """
    # Buscar cobranca por woovi_charge_id ou correlation_id
    cobranca = db.query(models.PixCobranca).filter(
        (models.PixCobranca.woovi_charge_id == charge_id)
        | (models.PixCobranca.correlation_id == charge_id)
    ).first()

    if not cobranca:
        logger.warning(f"Cobranca Pix nao encontrada para charge_id: {charge_id}")
        return

    if cobranca.status == "COMPLETED":
        logger.info(f"Cobranca {charge_id} ja foi processada (COMPLETED)")
        return

    # Atualizar cobranca
    cobranca.status = "COMPLETED"
    cobranca.pago_em = datetime.utcnow()

    # Atualizar pedido — pix confirmado = pode ir pra cozinha (em_preparo)
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == cobranca.pedido_id,
    ).first()

    if pedido and pedido.status == "pendente":
        # Verificar se KDS ativo para enviar direto pra cozinha
        config_kds = None
        try:
            config_kds = db.query(models.ConfigCozinha).filter(
                models.ConfigCozinha.restaurante_id == pedido.restaurante_id,
                models.ConfigCozinha.kds_ativo == True,
            ).first()
        except Exception:
            pass

        if config_kds:
            pedido.status = "em_preparo"
            # Criar PedidoCozinha
            try:
                pc = models.PedidoCozinha(
                    restaurante_id=pedido.restaurante_id,
                    pedido_id=pedido.id,
                    status="NOVO",
                    criado_em=datetime.utcnow(),
                )
                db.add(pc)
            except Exception as e:
                logger.warning(f"Erro ao criar PedidoCozinha apos Pix: {e}")
        else:
            pedido.status = "confirmado"

        # Atualizar historico_status
        historico = list(pedido.historico_status or [])
        historico.append({"status": pedido.status, "timestamp": datetime.utcnow().isoformat()})
        pedido.historico_status = historico
        flag_modified(pedido, "historico_status")

        logger.info(
            f"Pedido {pedido.id} (comanda {pedido.comanda}) → {pedido.status} via Pix"
        )

    db.commit()

    # Notificar restaurante via WebSocket
    if ws_manager and pedido:
        try:
            await ws_manager.broadcast(
                {
                    "tipo": "pix_confirmado",
                    "dados": {
                        "pedido_id": pedido.id,
                        "comanda": pedido.comanda,
                        "valor_centavos": cobranca.valor_centavos,
                        "valor": cobranca.valor_centavos / 100,
                    },
                },
                cobranca.restaurante_id,
            )
        except Exception as e:
            logger.warning(f"Erro ao enviar WebSocket pix_confirmado: {e}")

    # Disparar impressão automática agora que o pagamento foi confirmado
    # (pedido saiu de "pendente" → "em_preparo"/"confirmado")
    if pedido and pedido.status in ("em_preparo", "confirmado"):
        try:
            config_rest = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == pedido.restaurante_id
            ).first()
            if config_rest and config_rest.impressao_automatica:
                from ..main import printer_manager
                await printer_manager.broadcast(
                    {
                        "tipo": "imprimir_pedido",
                        "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda},
                    },
                    pedido.restaurante_id,
                )
                logger.info(
                    f"[Pix] Broadcast imprimir_pedido disparado apos pagamento — pedido #{pedido.comanda}"
                )
        except Exception as e:
            logger.warning(
                f"[Pix] Falha ao disparar broadcast de impressao para pedido #{pedido.comanda}: {e}"
            )

    # Se pedido veio do WhatsApp bot: notificar cliente via WhatsApp (Meta ou Evolution)
    if pedido and pedido.origem == "whatsapp_bot" and pedido.cliente_telefone:
        try:
            bot_config = db.query(models.BotConfig).filter(
                models.BotConfig.restaurante_id == pedido.restaurante_id,
                models.BotConfig.ativo == True,
            ).first()

            if bot_config:
                from ..bot.whatsapp_client import enviar_texto as wa_enviar_texto

                valor_fmt = f"R${cobranca.valor_centavos/100:.2f}"
                texto = (
                    f"Pagamento Pix de {valor_fmt} confirmado! "
                    f"Seu pedido #{pedido.comanda} já foi para a cozinha. "
                    f"Obrigado!"
                )

                await wa_enviar_texto(
                    numero=pedido.cliente_telefone,
                    texto=texto,
                    bot_config=bot_config,
                )

                # Registrar BotMensagem
                conversa = db.query(models.BotConversa).filter(
                    models.BotConversa.restaurante_id == pedido.restaurante_id,
                    models.BotConversa.telefone.like(f"%{pedido.cliente_telefone[-8:]}"),
                    models.BotConversa.ativa == True,
                ).first()

                if conversa:
                    msg = models.BotMensagem(
                        conversa_id=conversa.id,
                        direcao="saida",
                        tipo="texto",
                        conteudo=texto,
                        tokens_usados=0,
                    )
                    db.add(msg)
                    db.commit()

                provider = getattr(bot_config, "whatsapp_provider", "evolution")
                logger.info(
                    f"Notificacao Pix confirmado enviada via WhatsApp ({provider}) "
                    f"para {pedido.cliente_telefone[:8]}***"
                )
        except Exception as e:
            logger.warning(f"Erro ao notificar cliente WhatsApp sobre Pix confirmado: {e}")

    logger.info(
        f"Pagamento Pix confirmado: cobranca {cobranca.id}, "
        f"pedido {cobranca.pedido_id}, R${cobranca.valor_centavos/100:.2f}"
    )


async def processar_cobranca_expirada(charge_id: str, db: Session):
    """
    Processa cobranca Pix expirada (webhook OPENPIX:CHARGE_EXPIRED).
    Atualiza status para EXPIRED.
    """
    cobranca = db.query(models.PixCobranca).filter(
        (models.PixCobranca.woovi_charge_id == charge_id)
        | (models.PixCobranca.correlation_id == charge_id)
    ).first()

    if not cobranca:
        logger.warning(f"Cobranca Pix nao encontrada para expirar: {charge_id}")
        return

    if cobranca.status in ("COMPLETED", "EXPIRED"):
        return

    cobranca.status = "EXPIRED"
    db.commit()

    logger.info(f"Cobranca Pix expirada: {cobranca.id} (pedido {cobranca.pedido_id})")


async def consultar_saldo(restaurante_id: int, db: Session) -> int:
    """
    Consulta saldo em tempo real da subconta Woovi do restaurante.
    Retorna saldo em centavos.
    """
    config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
        models.PixConfig.ativo == True,
    ).first()

    if not config:
        raise ValueError("Pix Online nao esta ativo para este restaurante")

    if not woovi_client.configured:
        raise ValueError("Woovi nao configurado (WOOVI_APP_ID ausente)")

    try:
        resp = await woovi_client.consultar_saldo(config.pix_chave)
        subaccount = resp.get("subaccount", resp)
        return subaccount.get("balance", 0)
    except Exception as e:
        logger.error(
            f"Erro ao consultar saldo Woovi para restaurante {restaurante_id}: {e}"
        )
        raise ValueError(f"Erro ao consultar saldo: {e}")


async def solicitar_saque(
    restaurante_id: int,
    valor_centavos: int,
    db: Session,
) -> dict:
    """
    Solicita e executa saque da subconta Woovi do restaurante.

    - Valida config e saldo
    - Calcula taxa (R$1,00 se < R$500, isento se >= R$500)
    - Executa saque parcial ou total via Woovi
    - Registra PixSaque no BD
    """
    config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
        models.PixConfig.ativo == True,
    ).first()

    if not config:
        raise ValueError("Pix Online nao esta ativo para este restaurante")

    if not woovi_client.configured:
        raise ValueError("Woovi nao configurado (WOOVI_APP_ID ausente)")

    if valor_centavos <= 0:
        raise ValueError("Valor do saque deve ser maior que zero")

    # Consultar saldo atual
    try:
        resp = await woovi_client.consultar_saldo(config.pix_chave)
        subaccount = resp.get("subaccount", resp)
        saldo_atual = subaccount.get("balance", 0)
    except Exception as e:
        logger.error(f"Erro ao consultar saldo para saque: {e}")
        raise ValueError(f"Erro ao consultar saldo: {e}")

    if valor_centavos > saldo_atual:
        raise ValueError(
            f"Saldo insuficiente. Disponivel: R${saldo_atual/100:.2f}, "
            f"solicitado: R${valor_centavos/100:.2f}"
        )

    # Calcular taxa
    taxa_centavos = 0 if valor_centavos >= ISENCAO_TAXA_CENTAVOS else TAXA_SAQUE_CENTAVOS

    # Criar registro de saque
    saque = models.PixSaque(
        restaurante_id=restaurante_id,
        valor_centavos=valor_centavos,
        taxa_centavos=taxa_centavos,
        status="solicitado",
        automatico=False,
        solicitado_em=datetime.utcnow(),
    )
    db.add(saque)
    db.commit()
    db.refresh(saque)

    # Executar saque na Woovi
    try:
        if valor_centavos >= saldo_atual:
            # Saque total
            await woovi_client.sacar_total(config.pix_chave)
        else:
            # Saque parcial (via vault workaround)
            await woovi_client.sacar_parcial(
                config.pix_chave, valor_centavos, saldo_atual
            )

        saque.status = "concluido"
        saque.concluido_em = datetime.utcnow()
        db.commit()

        logger.info(
            f"Saque concluido para restaurante {restaurante_id}: "
            f"R${valor_centavos/100:.2f} (taxa: R${taxa_centavos/100:.2f})"
        )

    except Exception as e:
        saque.status = "falhou"
        saque.concluido_em = datetime.utcnow()
        db.commit()

        logger.error(
            f"Saque falhou para restaurante {restaurante_id}: {e}"
        )
        raise ValueError(f"Erro ao executar saque: {e}")

    return {
        "saque_id": saque.id,
        "valor_centavos": saque.valor_centavos,
        "taxa_centavos": saque.taxa_centavos,
        "valor_liquido_centavos": saque.valor_centavos - saque.taxa_centavos,
        "status": saque.status,
    }


async def atualizar_config_saque(
    restaurante_id: int,
    saque_automatico: bool,
    saque_minimo_centavos: int,
    db: Session,
):
    """
    Atualiza configuracao de saque automatico do restaurante.

    - saque_automatico: liga/desliga saque automatico
    - saque_minimo_centavos: valor minimo para disparar saque automatico
    """
    config = db.query(models.PixConfig).filter(
        models.PixConfig.restaurante_id == restaurante_id,
        models.PixConfig.ativo == True,
    ).first()

    if not config:
        raise ValueError("Pix Online nao esta ativo para este restaurante")

    if saque_minimo_centavos < ISENCAO_TAXA_CENTAVOS:
        raise ValueError(
            f"Valor minimo para saque automatico deve ser pelo menos "
            f"R${ISENCAO_TAXA_CENTAVOS/100:.2f} (isento de taxa)"
        )

    config.saque_automatico = saque_automatico
    config.saque_minimo_centavos = saque_minimo_centavos
    db.commit()

    logger.info(
        f"Config saque atualizada para restaurante {restaurante_id}: "
        f"automatico={saque_automatico}, minimo=R${saque_minimo_centavos/100:.2f}"
    )


async def executar_saques_automaticos(db: Session):
    """
    Task periodica: verifica restaurantes com saque automatico ativo
    e executa saque quando saldo >= valor minimo configurado.

    Roda a cada 30 minutos via pix_tasks.py.
    """
    configs = (
        db.query(models.PixConfig)
        .filter(
            models.PixConfig.ativo == True,
            models.PixConfig.saque_automatico == True,
        )
        .all()
    )

    if not configs:
        return

    if not woovi_client.configured:
        logger.debug("Woovi nao configurado — saques automaticos ignorados")
        return

    total_saques = 0
    total_erros = 0

    for config in configs:
        try:
            # Consultar saldo
            resp = await woovi_client.consultar_saldo(config.pix_chave)
            subaccount = resp.get("subaccount", resp)
            saldo = subaccount.get("balance", 0)

            if saldo < config.saque_minimo_centavos:
                continue

            # Calcular taxa
            taxa = 0 if saldo >= ISENCAO_TAXA_CENTAVOS else TAXA_SAQUE_CENTAVOS

            # Criar registro de saque
            saque = models.PixSaque(
                restaurante_id=config.restaurante_id,
                valor_centavos=saldo,
                taxa_centavos=taxa,
                status="solicitado",
                automatico=True,
                solicitado_em=datetime.utcnow(),
            )
            db.add(saque)
            db.commit()
            db.refresh(saque)

            # Executar saque total (automatico sempre saca tudo)
            try:
                await woovi_client.sacar_total(config.pix_chave)
                saque.status = "concluido"
                saque.concluido_em = datetime.utcnow()
                db.commit()
                total_saques += 1

                logger.info(
                    f"Saque automatico concluido: restaurante {config.restaurante_id}, "
                    f"R${saldo/100:.2f} (taxa: R${taxa/100:.2f})"
                )
            except Exception as e:
                saque.status = "falhou"
                saque.concluido_em = datetime.utcnow()
                db.commit()
                total_erros += 1

                logger.error(
                    f"Saque automatico falhou para restaurante {config.restaurante_id}: {e}"
                )

        except Exception as e:
            total_erros += 1
            logger.error(
                f"Erro ao processar saque automatico para restaurante "
                f"{config.restaurante_id}: {e}"
            )

    if total_saques > 0 or total_erros > 0:
        logger.info(
            f"Saques automaticos: {total_saques} concluidos, {total_erros} erros "
            f"(de {len(configs)} configs ativas)"
        )
