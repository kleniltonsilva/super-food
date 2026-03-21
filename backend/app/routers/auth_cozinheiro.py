"""
Router Auth Cozinheiro - Login e perfil KDS
Sprint 18 — KDS / Comanda Digital
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from .. import models, database, auth

COZINHEIRO_TOKEN_DAYS = 7

router = APIRouter(prefix="/auth/cozinheiro", tags=["Auth Cozinheiro"])


# ========== Schemas ==========

class CozinheiroLoginRequest(BaseModel):
    codigo_restaurante: str
    login: str
    senha: str


class CozinheiroLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    cozinheiro: dict
    restaurante: dict


class CozinheiroMeResponse(BaseModel):
    id: int
    nome: str
    login: str
    modo: str
    avatar_emoji: Optional[str] = None
    ativo: bool
    criado_em: Optional[datetime] = None
    produto_ids: list
    restaurante: dict

    class Config:
        from_attributes = True


# ========== Endpoints ==========

@router.post("/login", response_model=CozinheiroLoginResponse)
def login_cozinheiro(
    dados: CozinheiroLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do cozinheiro por código do restaurante + login + senha. Retorna JWT + dados."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == dados.codigo_restaurante.strip().upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Código do restaurante inválido"
        )

    cozinheiro = db.query(models.Cozinheiro).filter(
        models.Cozinheiro.restaurante_id == restaurante.id,
        models.Cozinheiro.login == dados.login.strip().lower(),
        models.Cozinheiro.ativo == True
    ).first()

    if not cozinheiro or not cozinheiro.verificar_senha(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login ou senha incorretos"
        )

    # Verificar se KDS está ativo
    config_kds = db.query(models.ConfigCozinha).filter(
        models.ConfigCozinha.restaurante_id == restaurante.id
    ).first()
    if not config_kds or not config_kds.kds_ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="KDS não está ativo neste restaurante"
        )

    # Buscar produto_ids vinculados
    produto_ids = [cp.produto_id for cp in cozinheiro.produtos]

    token = auth.create_access_token(
        data={
            "sub": str(cozinheiro.id),
            "role": "cozinheiro",
            "restaurante_id": restaurante.id
        },
        expires_delta=timedelta(days=COZINHEIRO_TOKEN_DAYS)
    )

    # Logo do restaurante
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()

    return CozinheiroLoginResponse(
        access_token=token,
        cozinheiro={
            "id": cozinheiro.id,
            "nome": cozinheiro.nome,
            "login": cozinheiro.login,
            "modo": cozinheiro.modo,
            "avatar_emoji": cozinheiro.avatar_emoji,
            "produto_ids": produto_ids,
        },
        restaurante={
            "id": restaurante.id,
            "nome": restaurante.nome,
            "nome_fantasia": restaurante.nome_fantasia,
            "codigo_acesso": restaurante.codigo_acesso,
            "logo_url": site_config.logo_url if site_config else None,
        }
    )


@router.get("/me", response_model=CozinheiroMeResponse)
def me_cozinheiro(
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Retorna dados completos do cozinheiro logado + info do restaurante."""
    rest = current_cozinheiro.restaurante
    produto_ids = [cp.produto_id for cp in current_cozinheiro.produtos]

    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()

    return CozinheiroMeResponse(
        id=current_cozinheiro.id,
        nome=current_cozinheiro.nome,
        login=current_cozinheiro.login,
        modo=current_cozinheiro.modo,
        avatar_emoji=current_cozinheiro.avatar_emoji,
        ativo=current_cozinheiro.ativo,
        criado_em=current_cozinheiro.criado_em,
        produto_ids=produto_ids,
        restaurante={
            "id": rest.id,
            "nome": rest.nome,
            "nome_fantasia": rest.nome_fantasia,
            "codigo_acesso": rest.codigo_acesso,
            "logo_url": site_config.logo_url if site_config else None,
        }
    )
