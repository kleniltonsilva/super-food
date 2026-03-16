# backend/app/routers/billing.py
"""
Endpoints de billing para o painel do restaurante.
Restaurantes suspensos PODEM acessar estes endpoints (para pagar).
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .. import models, database, auth
from ..billing.billing_service import get_billing_status, selecionar_plano, get_planos_disponiveis
from ..billing.asaas_client import asaas_client

router = APIRouter(prefix="/painel/billing", tags=["Billing Restaurante"])


class SelecionarPlanoRequest(BaseModel):
    plano: str
    ciclo: Literal["MONTHLY", "YEARLY"] = "MONTHLY"
    billing_type: Literal["PIX", "BOLETO"] = "PIX"


def _get_restaurante_billing(
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
) -> models.Restaurante:
    """Permite acesso mesmo para restaurantes suspensos."""
    return current_restaurante


# ─── Endpoints ──────────────────────────────────────────

@router.get("/status")
def billing_status(
    restaurante: models.Restaurante = Depends(_get_restaurante_billing),
    db: Session = Depends(database.get_db),
):
    """Status completo de billing do restaurante."""
    return get_billing_status(restaurante, db)


@router.get("/planos")
def listar_planos(
    db: Session = Depends(database.get_db),
    restaurante: models.Restaurante = Depends(_get_restaurante_billing),
):
    """Lista planos disponíveis com preços mensal/anual."""
    return get_planos_disponiveis(db)


@router.post("/selecionar-plano")
async def endpoint_selecionar_plano(
    dados: SelecionarPlanoRequest,
    restaurante: models.Restaurante = Depends(_get_restaurante_billing),
    db: Session = Depends(database.get_db),
):
    """Restaurante seleciona/troca plano."""
    try:
        resultado = await selecionar_plano(
            restaurante_id=restaurante.id,
            plano=dados.plano,
            ciclo=dados.ciclo,
            billing_type=dados.billing_type,
            db=db,
        )
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/faturas")
def listar_faturas(
    restaurante: models.Restaurante = Depends(_get_restaurante_billing),
    db: Session = Depends(database.get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista histórico de faturas/pagamentos."""
    pagamentos = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.restaurante_id == restaurante.id,
    ).order_by(models.AsaasPagamento.criado_em.desc()).offset(offset).limit(limit).all()

    total = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.restaurante_id == restaurante.id,
    ).count()

    return {
        "faturas": [
            {
                "id": p.id,
                "asaas_payment_id": p.asaas_payment_id,
                "valor": p.valor,
                "valor_liquido": p.valor_liquido,
                "billing_type": p.billing_type,
                "status": p.status,
                "data_vencimento": p.data_vencimento.isoformat() if p.data_vencimento else None,
                "data_pagamento": p.data_pagamento.isoformat() if p.data_pagamento else None,
                "invoice_url": p.invoice_url,
                "boleto_url": p.boleto_url,
                "criado_em": p.criado_em.isoformat() if p.criado_em else None,
            }
            for p in pagamentos
        ],
        "total": total,
    }


@router.get("/faturas/{fatura_id}/pix")
async def get_fatura_pix(
    fatura_id: int,
    restaurante: models.Restaurante = Depends(_get_restaurante_billing),
    db: Session = Depends(database.get_db),
):
    """Retorna QR Code PIX + copia-e-cola de uma fatura."""
    pagamento = db.query(models.AsaasPagamento).filter(
        models.AsaasPagamento.id == fatura_id,
        models.AsaasPagamento.restaurante_id == restaurante.id,
    ).first()

    if not pagamento:
        raise HTTPException(status_code=404, detail="Fatura não encontrada")

    # Se já tem PIX salvo, retornar
    if pagamento.pix_qr_code and pagamento.pix_copia_cola:
        return {
            "qr_code": pagamento.pix_qr_code,
            "copia_cola": pagamento.pix_copia_cola,
            "valor": pagamento.valor,
            "data_vencimento": pagamento.data_vencimento.isoformat() if pagamento.data_vencimento else None,
        }

    # Buscar do Asaas
    if asaas_client.configured and pagamento.asaas_payment_id:
        try:
            pix_data = await asaas_client.get_pix_qr_code(pagamento.asaas_payment_id)
            pagamento.pix_qr_code = pix_data.get("encodedImage", "")
            pagamento.pix_copia_cola = pix_data.get("payload", "")
            db.commit()
            return {
                "qr_code": pagamento.pix_qr_code,
                "copia_cola": pagamento.pix_copia_cola,
                "valor": pagamento.valor,
                "data_vencimento": pagamento.data_vencimento.isoformat() if pagamento.data_vencimento else None,
            }
        except Exception:
            raise HTTPException(status_code=502, detail="Erro ao buscar PIX no Asaas")

    raise HTTPException(status_code=404, detail="PIX não disponível para esta fatura")
