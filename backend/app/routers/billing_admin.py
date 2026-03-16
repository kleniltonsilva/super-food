# backend/app/routers/billing_admin.py
"""
Endpoints de billing para o Super Admin.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from datetime import datetime, timedelta

from .. import models, database, auth
from ..billing.billing_service import (
    iniciar_trial, registrar_audit, migrar_restaurante_asaas,
    reativar_por_pagamento, cancelar_por_inadimplencia,
    PLANOS, _get_config,
)
from ..billing.asaas_client import asaas_client

router = APIRouter(prefix="/api/admin/billing", tags=["Billing Admin"])


class ConfigBillingUpdate(BaseModel):
    trial_dias: Optional[int] = None
    trial_plano: Optional[str] = None
    dias_lembrete_antes: Optional[int] = None
    dias_suspensao: Optional[int] = None
    dias_aviso_cancelamento: Optional[int] = None
    dias_cancelamento: Optional[int] = None
    dias_preservacao_dados: Optional[int] = None
    desconto_anual_percentual: Optional[float] = None
    asaas_webhook_token: Optional[str] = None

    @field_validator(
        "trial_dias", "dias_lembrete_antes", "dias_suspensao",
        "dias_aviso_cancelamento", "dias_cancelamento", "dias_preservacao_dados",
        mode="before",
    )
    @classmethod
    def validar_dias(cls, v):
        if v is not None and v < 1:
            raise ValueError("Valor de dias deve ser >= 1")
        return v

    @field_validator("desconto_anual_percentual", mode="before")
    @classmethod
    def validar_desconto(cls, v):
        if v is not None and (v < 0 or v > 99):
            raise ValueError("Desconto deve ser entre 0 e 99%")
        return v


class EstenderTrialRequest(BaseModel):
    dias: int

    @field_validator("dias", mode="before")
    @classmethod
    def validar_dias(cls, v):
        if v < 1:
            raise ValueError("Dias deve ser >= 1")
        return v


class AtualizarPlanoRequest(BaseModel):
    plano: str
    ciclo: Optional[Literal["MONTHLY", "YEARLY"]] = None
    valor_override: Optional[float] = None

    @field_validator("valor_override", mode="before")
    @classmethod
    def validar_valor(cls, v):
        if v is not None and v < 0:
            raise ValueError("Valor deve ser >= 0")
        return v


# ─── Config ─────────────────────────────────────────────

@router.get("/config")
def get_config_billing(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Retorna configuração global de billing."""
    config = _get_config(db)
    return {
        "trial_dias": config.trial_dias,
        "trial_plano": config.trial_plano,
        "dias_lembrete_antes": config.dias_lembrete_antes,
        "dias_suspensao": config.dias_suspensao,
        "dias_aviso_cancelamento": config.dias_aviso_cancelamento,
        "dias_cancelamento": config.dias_cancelamento,
        "dias_preservacao_dados": config.dias_preservacao_dados,
        "desconto_anual_percentual": config.desconto_anual_percentual,
        "asaas_webhook_token": config.asaas_webhook_token,
        "asaas_environment": "production" if "api.asaas.com" in (asaas_client.base_url or "") else "sandbox",
        "asaas_configured": asaas_client.configured,
    }


@router.put("/config")
def atualizar_config_billing(
    dados: ConfigBillingUpdate,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza configuração global de billing."""
    config = _get_config(db)
    campos = dados.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        setattr(config, campo, valor)
    db.commit()
    return {"mensagem": "Configuração atualizada"}


# ─── Dashboard ──────────────────────────────────────────

@router.get("/dashboard")
def billing_dashboard(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Dashboard de billing — MRR, churn, trials, inadimplentes."""
    # Contagem por billing_status
    status_counts = {}
    rows = db.query(
        models.Restaurante.billing_status, func.count(models.Restaurante.id)
    ).group_by(models.Restaurante.billing_status).all()
    for status, count in rows:
        status_counts[status or "manual"] = count

    # MRR (Monthly Recurring Revenue)
    assinaturas_ativas = db.query(models.AsaasAssinatura).filter(
        models.AsaasAssinatura.status == "ACTIVE",
    ).all()
    mrr = sum(
        a.valor if a.ciclo == "MONTHLY" else round(a.valor / 12, 2)
        for a in assinaturas_ativas
    )

    # Receita recebida no mês atual
    inicio_mes = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    receita_mes = db.query(func.sum(models.AsaasPagamento.valor_liquido)).filter(
        models.AsaasPagamento.status.in_(["RECEIVED", "CONFIRMED"]),
        models.AsaasPagamento.data_pagamento >= inicio_mes,
    ).scalar() or 0

    # Total de restaurantes
    total_restaurantes = db.query(func.count(models.Restaurante.id)).scalar() or 0

    return {
        "mrr": round(mrr, 2),
        "receita_anual_projetada": round(mrr * 12, 2),
        "receita_mes_atual": round(float(receita_mes), 2),
        "total_restaurantes": total_restaurantes,
        "por_status": status_counts,
        "total_trials": status_counts.get("trial", 0),
        "total_ativos": status_counts.get("active", 0),
        "total_overdue": status_counts.get("overdue", 0),
        "total_suspensos": status_counts.get("suspended_billing", 0),
        "total_cancelados": status_counts.get("canceled_billing", 0),
        "total_manuais": status_counts.get("manual", 0),
    }


# ─── Audit Log ──────────────────────────────────────────

@router.get("/audit-log")
def listar_audit_log(
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
    restaurante_id: Optional[int] = None,
    acao: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Lista audit log de billing."""
    query = db.query(models.BillingAuditLog)
    if restaurante_id:
        query = query.filter(models.BillingAuditLog.restaurante_id == restaurante_id)
    if acao:
        query = query.filter(models.BillingAuditLog.acao == acao)

    total = query.count()
    logs = query.order_by(models.BillingAuditLog.criado_em.desc()).offset(offset).limit(limit).all()

    # Buscar nomes dos restaurantes
    rest_ids = {log.restaurante_id for log in logs if log.restaurante_id}
    nomes = {}
    if rest_ids:
        rests = db.query(models.Restaurante.id, models.Restaurante.nome_fantasia).filter(
            models.Restaurante.id.in_(rest_ids)
        ).all()
        nomes = {r.id: r.nome_fantasia for r in rests}

    return {
        "logs": [
            {
                "id": log.id,
                "restaurante_id": log.restaurante_id,
                "restaurante_nome": nomes.get(log.restaurante_id, ""),
                "acao": log.acao,
                "detalhes": log.detalhes,
                "admin_id": log.admin_id,
                "automatico": log.automatico,
                "criado_em": log.criado_em.isoformat() if log.criado_em else None,
            }
            for log in logs
        ],
        "total": total,
    }


# ─── Ações por Restaurante ─────────────────────────────

@router.post("/restaurantes/{restaurante_id}/iniciar-trial")
async def endpoint_iniciar_trial(
    restaurante_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Inicia trial para um restaurante."""
    try:
        resultado = await iniciar_trial(restaurante_id, db, admin_id=admin.id)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restaurantes/{restaurante_id}/estender-trial")
def endpoint_estender_trial(
    restaurante_id: int,
    dados: EstenderTrialRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Estende o trial de um restaurante."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    if restaurante.billing_status not in ("trial", "suspended_billing"):
        raise HTTPException(status_code=400, detail=f"Billing status '{restaurante.billing_status}' não permite estender trial")

    base = restaurante.trial_fim or datetime.utcnow()
    if base < datetime.utcnow():
        base = datetime.utcnow()

    restaurante.trial_fim = base + timedelta(days=dados.dias)
    restaurante.billing_status = "trial"
    restaurante.ativo = True
    restaurante.status = "ativo"
    restaurante.dias_vencido = 0
    db.commit()

    registrar_audit(db, restaurante_id, "trial_extended", {
        "dias": dados.dias,
        "novo_trial_fim": restaurante.trial_fim.isoformat(),
    }, admin_id=admin.id)

    return {"trial_fim": restaurante.trial_fim.isoformat(), "dias": dados.dias}


@router.post("/restaurantes/{restaurante_id}/reativar")
async def endpoint_reativar(
    restaurante_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Reativa manualmente um restaurante suspenso/cancelado."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    await reativar_por_pagamento(restaurante, db)
    registrar_audit(db, restaurante_id, "reactivated_admin", admin_id=admin.id)

    return {"mensagem": "Restaurante reativado"}


@router.post("/restaurantes/{restaurante_id}/migrar-asaas")
async def endpoint_migrar_asaas(
    restaurante_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Migra restaurante manual para Asaas."""
    try:
        resultado = await migrar_restaurante_asaas(restaurante_id, db, admin_id=admin.id)
        return resultado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/restaurantes/{restaurante_id}/plano")
def endpoint_atualizar_plano(
    restaurante_id: int,
    dados: AtualizarPlanoRequest,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Atualiza plano de um restaurante (Super Admin override)."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    if dados.plano not in PLANOS:
        raise HTTPException(status_code=400, detail=f"Plano inválido: {dados.plano}")

    plano_info = PLANOS[dados.plano]
    restaurante.plano = dados.plano
    restaurante.limite_motoboys = plano_info["limite_motoboys"]
    restaurante.valor_plano = dados.valor_override if dados.valor_override is not None else plano_info["valor"]
    if dados.ciclo:
        restaurante.plano_ciclo = dados.ciclo

    # Atualizar assinatura local
    assinatura = db.query(models.AsaasAssinatura).filter(
        models.AsaasAssinatura.restaurante_id == restaurante_id,
        models.AsaasAssinatura.status == "ACTIVE",
    ).first()
    if assinatura:
        assinatura.plano = dados.plano
        assinatura.valor = restaurante.valor_plano
        if dados.ciclo:
            assinatura.ciclo = dados.ciclo

    db.commit()
    registrar_audit(db, restaurante_id, "plan_changed_admin", {
        "plano": dados.plano, "ciclo": dados.ciclo, "valor": restaurante.valor_plano,
    }, admin_id=admin.id)

    return {"mensagem": f"Plano atualizado para {dados.plano}"}


@router.post("/restaurantes/{restaurante_id}/cancelar")
async def endpoint_cancelar(
    restaurante_id: int,
    admin: models.SuperAdmin = Depends(auth.get_current_admin),
    db: Session = Depends(database.get_db),
):
    """Cancela assinatura de um restaurante."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == restaurante_id
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    await cancelar_por_inadimplencia(restaurante, db)
    registrar_audit(db, restaurante_id, "canceled_admin", admin_id=admin.id)

    return {"mensagem": "Assinatura cancelada"}
