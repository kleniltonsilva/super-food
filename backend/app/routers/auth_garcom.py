"""
Router Auth Garçom - Login e perfil App Garçom
Sprint 19 — App Garçom (Atendimento Mesa)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from .. import models, database, auth
from ..feature_flags import has_feature, get_tier

GARCOM_TOKEN_DAYS = 7

router = APIRouter(prefix="/garcom/auth", tags=["Auth Garçom"])


# ========== Schemas ==========

class GarcomLoginRequest(BaseModel):
    codigo_restaurante: str
    login: str
    senha: str


class GarcomLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    garcom: dict
    restaurante: dict


class GarcomMeResponse(BaseModel):
    id: int
    nome: str
    login: str
    modo_secao: str
    secao_inicio: Optional[int] = None
    secao_fim: Optional[int] = None
    avatar_emoji: Optional[str] = None
    ativo: bool
    criado_em: Optional[datetime] = None
    mesa_ids: list
    restaurante: dict

    class Config:
        from_attributes = True


# ========== Endpoints ==========

@router.post("/login", response_model=GarcomLoginResponse)
def login_garcom(
    dados: GarcomLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do garçom por código do restaurante + login + senha. Retorna JWT + dados."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_restaurante.strip().upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código do restaurante inválido"
        )

    garcom = db.query(models.Garcom).filter(
        models.Garcom.restaurante_id == restaurante.id,
        models.Garcom.login == dados.login.strip().lower(),
        models.Garcom.ativo == True
    ).first()

    if not garcom or not garcom.verificar_senha(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos"
        )

    # Verificar se app garçom está ativo
    config_garcom = db.query(models.ConfigGarcom).filter(
        models.ConfigGarcom.restaurante_id == restaurante.id
    ).first()
    if not config_garcom or not config_garcom.garcom_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="App Garçom não está ativo neste restaurante"
        )

    # Verificar feature flag do plano (trial = acesso total)
    if restaurante.billing_status != "trial":
        tier = getattr(restaurante, "plano_tier", None) or get_tier(restaurante.plano)
        overrides = getattr(restaurante, "features_override", None)
        if not has_feature(restaurante.plano, "app_garcom", overrides=overrides, plano_tier=tier):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "type": "feature_blocked",
                    "feature": "app_garcom",
                    "feature_label": "App Garçom",
                    "current_plano": restaurante.plano,
                    "required_plano": "Avançado",
                    "message": "O App Garçom requer o plano Avançado ou superior.",
                },
            )

    # Buscar mesa_ids vinculados (modo CUSTOM)
    mesa_ids = [gm.mesa_id for gm in garcom.mesas_custom]

    token = auth.create_access_token(
        data={
            "sub": str(garcom.id),
            "role": "garcom",
            "restaurante_id": restaurante.id
        },
        expires_delta=timedelta(days=GARCOM_TOKEN_DAYS)
    )

    # Logo do restaurante
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()

    return GarcomLoginResponse(
        access_token=token,
        garcom={
            "id": garcom.id,
            "nome": garcom.nome,
            "login": garcom.login,
            "modo_secao": garcom.modo_secao,
            "secao_inicio": garcom.secao_inicio,
            "secao_fim": garcom.secao_fim,
            "avatar_emoji": garcom.avatar_emoji,
            "mesa_ids": mesa_ids,
        },
        restaurante={
            "id": restaurante.id,
            "nome": restaurante.nome,
            "nome_fantasia": restaurante.nome_fantasia,
            "codigo_acesso": restaurante.codigo_acesso,
            "logo_url": site_config.logo_url if site_config else None,
        }
    )


@router.get("/me", response_model=GarcomMeResponse)
def me_garcom(
    current_garcom: models.Garcom = Depends(auth.get_current_garcom),
    db: Session = Depends(database.get_db)
):
    """Retorna dados completos do garçom logado + info do restaurante."""
    rest = current_garcom.restaurante
    mesa_ids = [gm.mesa_id for gm in current_garcom.mesas_custom]

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()

    return GarcomMeResponse(
        id=current_garcom.id,
        nome=current_garcom.nome,
        login=current_garcom.login,
        modo_secao=current_garcom.modo_secao,
        secao_inicio=current_garcom.secao_inicio,
        secao_fim=current_garcom.secao_fim,
        avatar_emoji=current_garcom.avatar_emoji,
        ativo=current_garcom.ativo,
        criado_em=current_garcom.criado_em,
        mesa_ids=mesa_ids,
        restaurante={
            "id": rest.id,
            "nome": rest.nome,
            "nome_fantasia": rest.nome_fantasia,
            "codigo_acesso": rest.codigo_acesso,
            "logo_url": site_config.logo_url if site_config else None,
        }
    )
