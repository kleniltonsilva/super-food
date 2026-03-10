# backend/app/routers/auth_admin.py

"""
Router Auth Super Admin - Login e perfil
Sprint 5 da migração v4.0
Tarefas 129-130
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .. import models, database, auth

router = APIRouter(prefix="/auth/admin", tags=["Auth Super Admin"])


# ========== Schemas ==========

class AdminLoginRequest(BaseModel):
    usuario: str
    senha: str


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class AdminMeResponse(BaseModel):
    id: int
    usuario: str
    email: Optional[str] = None
    ativo: bool
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


# ========== Endpoints ==========

@router.post("/login", response_model=AdminLoginResponse)
def login_admin(
    dados: AdminLoginRequest,
    db: Session = Depends(database.get_db)
):
    """Login do super admin por usuário + senha. Retorna JWT + dados."""
    admin = db.query(models.SuperAdmin).filter(
        models.SuperAdmin.usuario == dados.usuario.strip(),
        models.SuperAdmin.ativo == True
    ).first()

    if not admin or not admin.verificar_senha(dados.senha):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário ou senha incorretos"
        )

    token = auth.create_access_token(
        data={"sub": str(admin.id), "role": "admin"}
    )

    return AdminLoginResponse(
        access_token=token,
        admin={
            "id": admin.id,
            "usuario": admin.usuario,
            "email": admin.email,
            "ativo": admin.ativo,
        }
    )


@router.get("/me", response_model=AdminMeResponse)
def me_admin(
    current_admin: models.SuperAdmin = Depends(auth.get_current_admin),
):
    """Retorna dados do super admin logado."""
    return current_admin
