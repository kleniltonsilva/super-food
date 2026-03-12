# backend/app/routers/auth_restaurante.py

"""
Router Auth Restaurante - Login, perfil, senha
Sprint 1.1 da migração v4.0
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta

from .. import models, database, auth

# Token do restaurante dura 30 dias para sessão persistente
RESTAURANTE_TOKEN_EXPIRE = timedelta(days=30)

router = APIRouter(prefix="/auth/restaurante", tags=["Auth Restaurante"])


# ========== Schemas ==========

class RestauranteLoginRequest(BaseModel):
    email: str
    senha: str


class RestauranteLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    restaurante: dict


class RestauranteMeResponse(BaseModel):
    id: int
    nome: str
    nome_fantasia: str
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: str
    telefone: str
    endereco_completo: str
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plano: str
    valor_plano: float
    limite_motoboys: int
    codigo_acesso: str
    ativo: bool
    status: Optional[str] = None
    criado_em: Optional[datetime] = None
    data_vencimento: Optional[datetime] = None

    class Config:
        from_attributes = True


class RestaurantePerfilUpdate(BaseModel):
    nome_fantasia: Optional[str] = None
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    endereco_completo: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None


class RestauranteSenhaUpdate(BaseModel):
    senha_atual: str
    nova_senha: str


# ========== Endpoints ==========

@router.post("/login", response_model=RestauranteLoginResponse)
def login_restaurante(
    dados: RestauranteLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do restaurante por email + senha. Retorna JWT + dados."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.email == dados.email.strip().lower(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante or not restaurante.verificar_senha(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos"
        )

    token = auth.create_access_token(
        data={"sub": str(restaurante.id), "role": "restaurante"},
        expires_delta=RESTAURANTE_TOKEN_EXPIRE,
    )

    return RestauranteLoginResponse(
        access_token=token,
        restaurante={
            "id": restaurante.id,
            "nome": restaurante.nome,
            "nome_fantasia": restaurante.nome_fantasia,
            "email": restaurante.email,
            "codigo_acesso": restaurante.codigo_acesso,
            "plano": restaurante.plano,
            "ativo": restaurante.ativo,
        }
    )


@router.get("/me")
def me_restaurante(
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
):
    """Retorna dados completos do restaurante logado + token renovado."""
    # Renova o token a cada chamada para manter sessão persistente
    new_token = auth.create_access_token(
        data={"sub": str(current_restaurante.id), "role": "restaurante"},
        expires_delta=RESTAURANTE_TOKEN_EXPIRE,
    )
    data = RestauranteMeResponse.model_validate(current_restaurante).model_dump()
    data["refreshed_token"] = new_token
    return data


@router.put("/perfil", response_model=RestauranteMeResponse)
def atualizar_perfil(
    dados: RestaurantePerfilUpdate,
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db)
):
    """Atualiza dados do perfil do restaurante. Se endereco_completo mudar, geocodifica."""
    campos_atualizados = dados.model_dump(exclude_unset=True)

    if not campos_atualizados:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    # Se endereço mudou, geocodificar antes de salvar
    novo_endereco = campos_atualizados.get("endereco_completo")
    if novo_endereco and novo_endereco.strip() != (current_restaurante.endereco_completo or "").strip():
        try:
            from utils.mapbox_api import geocode_address
            from utils.calculos import detectar_cidade_endereco
            coords = geocode_address(novo_endereco.strip())
            if coords:
                lat, lng = coords
                current_restaurante.latitude = lat
                current_restaurante.longitude = lng
                info = detectar_cidade_endereco(novo_endereco.strip())
                if info:
                    if info.get("cidade"):
                        current_restaurante.cidade = info["cidade"]
                    if info.get("estado"):
                        current_restaurante.estado = info["estado"]
        except Exception:
            pass  # Salva endereço mesmo sem geocoding

    for campo, valor in campos_atualizados.items():
        setattr(current_restaurante, campo, valor)

    # Se mudou nome_fantasia, atualizar nome também
    if "nome_fantasia" in campos_atualizados:
        current_restaurante.nome = campos_atualizados["nome_fantasia"]

    db.commit()
    db.refresh(current_restaurante)
    return current_restaurante


@router.put("/senha")
def alterar_senha(
    dados: RestauranteSenhaUpdate,
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db)
):
    """Altera a senha do restaurante."""
    if not current_restaurante.verificar_senha(dados.senha_atual):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")

    if len(dados.nova_senha.strip()) < 6:
        raise HTTPException(status_code=400, detail="Nova senha deve ter no mínimo 6 caracteres")

    current_restaurante.set_senha(dados.nova_senha)
    db.commit()

    return {"mensagem": "Senha alterada com sucesso"}
