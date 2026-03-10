# backend/app/schemas/__init__.py
# Schemas legados para rotas /restaurantes e /pedidos
# Corrigidos para refletir campos reais do models.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class RestauranteBase(BaseModel):
    nome_fantasia: str = Field(..., min_length=3)
    razao_social: Optional[str] = None
    cnpj: Optional[str] = None
    email: EmailStr
    telefone: str
    endereco_completo: str


class RestauranteCreate(RestauranteBase):
    senha: str = Field(..., min_length=6)
    plano: Optional[str] = "basico"


class RestauranteUpdate(BaseModel):
    nome_fantasia: Optional[str] = None
    telefone: Optional[str] = None
    endereco_completo: Optional[str] = None


class RestaurantePublic(BaseModel):
    id: int
    nome_fantasia: str
    email: EmailStr
    telefone: str
    endereco_completo: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    plano: str
    codigo_acesso: str
    ativo: bool
    criado_em: Optional[datetime] = None

    class Config:
        from_attributes = True


class PedidoBase(BaseModel):
    cliente_nome: str
    cliente_telefone: str
    endereco_entrega: str
    itens: str
    valor_total: float


class PedidoCreate(PedidoBase):
    pass


class PedidoPublic(BaseModel):
    id: int
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    endereco_entrega: Optional[str] = None
    itens: Optional[str] = None
    valor_total: Optional[float] = None
    status: Optional[str] = None
    data_criacao: Optional[datetime] = None

    class Config:
        from_attributes = True
