# backend/app/billing/billing_tasks.py
"""
Task assíncrona periódica de billing.
Verifica trials, pagamentos vencidos, suspensões e cancelamentos.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal
from .billing_service import (
    suspender_por_inadimplencia,
    cancelar_por_inadimplencia,
    registrar_audit,
    asaas_client,
)

logger = logging.getLogger("superfood.billing")

INTERVALO_VERIFICACAO = 30 * 60  # 30 minutos
INTERVALO_POLLING_ASAAS = 6 * 60 * 60  # 6 horas
_ultimo_polling = datetime.utcnow()


async def verificar_billing_periodico(ws_manager):
    """Task principal de billing — roda a cada 30 minutos."""
    global _ultimo_polling

    # Aguarda 60s antes da primeira execução para o app estabilizar
    await asyncio.sleep(60)

    while True:
        try:
            db = SessionLocal()
            try:
                config = db.query(models.ConfigBilling).first()
                if not config:
                    await asyncio.sleep(INTERVALO_VERIFICACAO)
                    continue

                agora = datetime.utcnow()

                # ── 1. Trials vencendo em ≤ dias_lembrete_antes ──
                await _verificar_trials_vencendo(db, config, agora, ws_manager)

                # ── 2. Trials vencidos sem plano → suspender ──
                await _verificar_trials_vencidos(db, agora)

                # ── 3. Overdue ≥ dias_suspensao → suspender ──
                await _verificar_overdue_suspensao(db, config)

                # ── 4. Suspended ≥ dias_cancelamento → cancelar ──
                await _verificar_suspended_cancelamento(db, config)

                # ── 5. Atualizar dias_vencido (1x/dia) ──
                _atualizar_dias_vencido(db)

                # ── 6. Fallback polling Asaas (cada 6h) ──
                if (agora - _ultimo_polling).total_seconds() >= INTERVALO_POLLING_ASAAS:
                    await _polling_pagamentos_asaas(db)
                    _ultimo_polling = agora

            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro na task de billing: {e}")

        await asyncio.sleep(INTERVALO_VERIFICACAO)


async def _verificar_trials_vencendo(db: Session, config: models.ConfigBilling, agora: datetime, ws_manager):
    """Notifica restaurantes com trial prestes a vencer."""
    limite = agora + timedelta(days=config.dias_lembrete_antes)

    trials_vencendo = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "trial",
        models.Restaurante.trial_fim != None,
        models.Restaurante.trial_fim <= limite,
        models.Restaurante.trial_fim > agora,
    ).all()

    for rest in trials_vencendo:
        dias_restantes = max(0, (rest.trial_fim - agora).days)

        # Verificar se já notificou hoje
        hoje = agora.date()
        notificacao_existente = db.query(models.Notificacao).filter(
            models.Notificacao.restaurante_id == rest.id,
            models.Notificacao.tipo == "trial_expiring",
            models.Notificacao.data_criacao >= datetime(hoje.year, hoje.month, hoje.day),
        ).first()

        if not notificacao_existente:
            notif = models.Notificacao(
                restaurante_id=rest.id,
                tipo="trial_expiring",
                titulo="Período de teste terminando",
                mensagem=f"Seu período de teste termina em {dias_restantes} dia{'s' if dias_restantes != 1 else ''}. Escolha um plano para continuar.",
                dados_json={"dias_restantes": dias_restantes},
            )
            db.add(notif)

            # WebSocket broadcast
            try:
                await ws_manager.broadcast({
                    "tipo": "billing_alert",
                    "dados": {
                        "alert_type": "trial_expiring",
                        "dias_restantes": dias_restantes,
                    }
                }, rest.id)
            except Exception:
                pass

    db.commit()


async def _verificar_trials_vencidos(db: Session, agora: datetime):
    """Suspende restaurantes com trial vencido que não selecionaram plano."""
    trials_vencidos = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "trial",
        models.Restaurante.trial_fim != None,
        models.Restaurante.trial_fim <= agora,
    ).all()

    for rest in trials_vencidos:
        await suspender_por_inadimplencia(rest, db)
        logger.info(f"Trial vencido — restaurante {rest.id} suspenso")


async def _verificar_overdue_suspensao(db: Session, config: models.ConfigBilling):
    """Suspende restaurantes overdue por mais de dias_suspensao dias."""
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "overdue",
        models.Restaurante.dias_vencido >= config.dias_suspensao,
    ).all()

    for rest in restaurantes:
        await suspender_por_inadimplencia(rest, db)


async def _verificar_suspended_cancelamento(db: Session, config: models.ConfigBilling):
    """Cancela restaurantes suspensos por mais de dias_cancelamento dias."""
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "suspended_billing",
        models.Restaurante.dias_vencido >= config.dias_cancelamento,
    ).all()

    for rest in restaurantes:
        await cancelar_por_inadimplencia(rest, db)


def _atualizar_dias_vencido(db: Session):
    """Incrementa dias_vencido para restaurantes overdue/suspended."""
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status.in_(["overdue", "suspended_billing"]),
    ).all()

    for rest in restaurantes:
        rest.dias_vencido = (rest.dias_vencido or 0) + 1

    if restaurantes:
        db.commit()


async def _polling_pagamentos_asaas(db: Session):
    """Polling de fallback — consulta Asaas por pagamentos recentes não processados."""
    if not asaas_client.configured:
        return

    clientes = db.query(models.AsaasCliente).all()
    for cli in clientes:
        try:
            result = await asaas_client.listar_pagamentos(cli.asaas_customer_id, status="RECEIVED")
            pagamentos = result.get("data", [])
            for pag in pagamentos:
                asaas_id = pag.get("id", "")
                existente = db.query(models.AsaasPagamento).filter(
                    models.AsaasPagamento.asaas_payment_id == asaas_id,
                    models.AsaasPagamento.status == "RECEIVED",
                ).first()
                if not existente:
                    from .billing_service import processar_pagamento_confirmado
                    await processar_pagamento_confirmado(pag, db)
                    logger.info(f"Polling: pagamento {asaas_id} processado para restaurante {cli.restaurante_id}")
        except Exception as e:
            logger.debug(f"Polling Asaas para customer {cli.asaas_customer_id}: {e}")
