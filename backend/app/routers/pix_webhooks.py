# backend/app/routers/pix_webhooks.py
"""
Webhook da Woovi/OpenPix — recebe eventos de pagamento Pix.
Sem autenticação JWT (validado via HMAC-SHA256 no header x-webhook-signature).
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import models
from ..database import SessionLocal
from ..pix import pix_service
from ..pix.woovi_client import woovi_client

logger = logging.getLogger("superfood.pix")

router = APIRouter(tags=["Pix Webhooks"])


@router.post("/webhooks/woovi")
async def webhook_woovi(request: Request):
    """Recebe eventos da Woovi/OpenPix (pagamentos Pix)."""
    db = SessionLocal()
    try:
        body_bytes = await request.body()

        # Validar assinatura HMAC-SHA256
        signature = request.headers.get("x-webhook-signature", "")
        if not woovi_client.validar_webhook(body_bytes, signature):
            raise HTTPException(status_code=401, detail="Assinatura inválida")

        body = await request.json()
        event_type = body.get("event", "")  # OPENPIX:CHARGE_COMPLETED, OPENPIX:CHARGE_EXPIRED
        charge = body.get("charge", {})
        charge_id = charge.get("correlationID", "") or charge.get("identifier", "")

        if not event_type or not charge_id:
            return {"status": "ignored", "reason": "missing event or charge id"}

        # Gerar event_id único
        event_id = f"{event_type}_{charge_id}"

        # Buscar restaurante_id a partir da cobrança
        cobranca = (
            db.query(models.PixCobranca)
            .filter(
                (models.PixCobranca.correlation_id == charge_id)
                | (models.PixCobranca.woovi_charge_id == charge_id)
            )
            .first()
        )
        restaurante_id = cobranca.restaurante_id if cobranca else None

        # Idempotência atômica — INSERT ON CONFLICT DO NOTHING
        stmt = (
            pg_insert(models.PixEventLog)
            .values(
                event_id=event_id,
                event_type=event_type,
                woovi_charge_id=charge_id,
                restaurante_id=restaurante_id,
                payload_json=body,
                processed=False,
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        result = db.execute(stmt)
        db.commit()

        if result.rowcount == 0:
            # Já existia — verificar se já processado
            evento_log = (
                db.query(models.PixEventLog)
                .filter(models.PixEventLog.event_id == event_id)
                .first()
            )
            if evento_log and evento_log.processed:
                return {"status": "already_processed"}
        else:
            evento_log = (
                db.query(models.PixEventLog)
                .filter(models.PixEventLog.event_id == event_id)
                .first()
            )

        if not evento_log:
            return {"status": "error", "message": "Falha ao registrar evento"}

        # Processar evento
        try:
            if event_type == "OPENPIX:CHARGE_COMPLETED":
                # Obter ws_manager do app state para notificar restaurante
                ws_manager = getattr(request.app.state, "ws_manager", None)
                await pix_service.processar_pagamento_confirmado(
                    charge_id, db, ws_manager
                )

            elif event_type == "OPENPIX:CHARGE_EXPIRED":
                await pix_service.processar_cobranca_expirada(charge_id, db)

            evento_log.processed = True
            db.commit()

        except Exception as e:
            evento_log.error_message = str(e)[:500]
            db.commit()
            logger.error(f"Erro processando webhook Woovi {event_type}: {e}")

        return {"status": "processed", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook Woovi: {e}")
        return {"status": "error"}
    finally:
        db.close()
