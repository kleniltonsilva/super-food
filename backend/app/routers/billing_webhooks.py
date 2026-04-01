# backend/app/routers/billing_webhooks.py
"""
Webhook do Asaas — recebe eventos de pagamento.
Sem autenticação JWT (validado via asaas-access-token header).
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .. import models
from ..database import SessionLocal
from ..billing.billing_service import (
    processar_pagamento_confirmado,
    processar_pagamento_vencido,
    processar_addon_pago,
    registrar_audit,
)
from ..billing.asaas_client import asaas_client

logger = logging.getLogger("superfood.billing")

router = APIRouter(tags=["Billing Webhooks"])


@router.post("/webhooks/asaas")
async def webhook_asaas(request: Request):
    """Recebe eventos do Asaas (pagamentos)."""
    db = SessionLocal()
    try:
        # Validar token do webhook (OBRIGATÓRIO — rejeita se não configurado)
        config = db.query(models.ConfigBilling).first()
        webhook_token = config.asaas_webhook_token if config else None

        if not webhook_token:
            raise HTTPException(status_code=403, detail="Webhook token não configurado")

        received_token = request.headers.get("asaas-access-token", "")
        if received_token != webhook_token:
            raise HTTPException(status_code=401, detail="Token inválido")

        body = await request.json()
        event_type = body.get("event", "")
        payment = body.get("payment", {})
        payment_id = payment.get("id", "")

        if not event_type or not payment_id:
            return {"status": "ignored", "reason": "missing event or payment id"}

        # Gerar event_id único
        event_id = f"{event_type}_{payment_id}"

        # Idempotência atômica — INSERT ON CONFLICT DO NOTHING
        stmt = pg_insert(models.AsaasEventLog).values(
            event_id=event_id,
            event_type=event_type,
            asaas_payment_id=payment_id,
            payload_json=body,
            processed=False,
        ).on_conflict_do_nothing(index_elements=["event_id"])
        result = db.execute(stmt)
        db.commit()

        if result.rowcount == 0:
            # Já existia — verificar se já processado
            evento_log = db.query(models.AsaasEventLog).filter(
                models.AsaasEventLog.event_id == event_id
            ).first()
            if evento_log and evento_log.processed:
                return {"status": "already_processed"}
        else:
            evento_log = db.query(models.AsaasEventLog).filter(
                models.AsaasEventLog.event_id == event_id
            ).first()

        if not evento_log:
            return {"status": "error", "message": "Falha ao registrar evento"}

        # Processar evento
        try:
            if event_type in ("PAYMENT_RECEIVED", "PAYMENT_CONFIRMED"):
                # Verificar se é pagamento de add-on
                addon_cob = db.query(models.AddonCobranca).filter(
                    models.AddonCobranca.asaas_payment_id == payment_id
                ).first()
                if addon_cob:
                    await processar_addon_pago(addon_cob, db)
                else:
                    await processar_pagamento_confirmado(payment, db)
                # Buscar PIX QR code para pagamentos futuros
                if payment.get("billingType") == "PIX" and asaas_client.configured:
                    try:
                        pix_data = await asaas_client.get_pix_qr_code(payment_id)
                        pag = db.query(models.AsaasPagamento).filter(
                            models.AsaasPagamento.asaas_payment_id == payment_id
                        ).first()
                        if pag:
                            pag.pix_qr_code = pix_data.get("encodedImage", "")
                            pag.pix_copia_cola = pix_data.get("payload", "")
                            db.commit()
                    except Exception:
                        pass

            elif event_type == "PAYMENT_OVERDUE":
                # Verificar se é add-on
                addon_cob_overdue = db.query(models.AddonCobranca).filter(
                    models.AddonCobranca.asaas_payment_id == payment_id
                ).first()
                if addon_cob_overdue:
                    addon_cob_overdue.status = "OVERDUE"
                    db.commit()
                else:
                    await processar_pagamento_vencido(payment, db)

            elif event_type == "PAYMENT_CREATED":
                # Registrar pagamento novo
                subscription_id = payment.get("subscription", "")
                assinatura = db.query(models.AsaasAssinatura).filter(
                    models.AsaasAssinatura.asaas_subscription_id == subscription_id
                ).first()
                restaurante_id = assinatura.restaurante_id if assinatura else None

                if not restaurante_id:
                    customer_id = payment.get("customer", "")
                    asaas_cli = db.query(models.AsaasCliente).filter(
                        models.AsaasCliente.asaas_customer_id == customer_id
                    ).first()
                    restaurante_id = asaas_cli.restaurante_id if asaas_cli else None

                if restaurante_id:
                    pag_existente = db.query(models.AsaasPagamento).filter(
                        models.AsaasPagamento.asaas_payment_id == payment_id
                    ).first()
                    if not pag_existente:
                        novo_pag = models.AsaasPagamento(
                            restaurante_id=restaurante_id,
                            asaas_payment_id=payment_id,
                            asaas_subscription_id=subscription_id,
                            valor=payment.get("value", 0),
                            billing_type=payment.get("billingType", "PIX"),
                            status=payment.get("status", "PENDING"),
                            data_vencimento=datetime.fromisoformat(payment["dueDate"]) if payment.get("dueDate") else None,
                            invoice_url=payment.get("invoiceUrl"),
                            boleto_url=payment.get("bankSlipUrl"),
                        )
                        db.add(novo_pag)

                        # Buscar PIX QR code
                        if payment.get("billingType") == "PIX" and asaas_client.configured:
                            try:
                                pix_data = await asaas_client.get_pix_qr_code(payment_id)
                                novo_pag.pix_qr_code = pix_data.get("encodedImage", "")
                                novo_pag.pix_copia_cola = pix_data.get("payload", "")
                            except Exception:
                                pass

                        db.commit()

                    evento_log.restaurante_id = restaurante_id

            elif event_type == "PAYMENT_DELETED":
                pag = db.query(models.AsaasPagamento).filter(
                    models.AsaasPagamento.asaas_payment_id == payment_id
                ).first()
                if pag:
                    pag.status = "DELETED"
                    db.commit()

            elif event_type == "PAYMENT_REFUNDED":
                pag = db.query(models.AsaasPagamento).filter(
                    models.AsaasPagamento.asaas_payment_id == payment_id
                ).first()
                if pag:
                    pag.status = "REFUNDED"
                    db.commit()

            evento_log.processed = True
            db.commit()

        except Exception as e:
            evento_log.error_message = str(e)[:500]
            db.commit()
            logger.error(f"Erro processando webhook Asaas {event_type}: {e}")

        return {"status": "processed", "event": event_type}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro no webhook Asaas: {e}")
        return {"status": "error", "message": str(e)[:200]}
    finally:
        db.close()
