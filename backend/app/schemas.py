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
    taxa_entrega: Optional[float] = 0.0
    tempo_medio_preparo: Optional[int] = 30

class RestauranteCreate(RestauranteBase):
    senha: str = Field(..., min_length=6)

class RestauranteUpdate(BaseModel):
    nome_fantasia: Optional[str] = None
    telefone: Optional[str] = None
    endereco_completo: Optional[str] = None
    taxa_entrega: Optional[float] = None
    tempo_medio_preparo: Optional[int] = None

class RestaurantePublic(BaseModel):
    id: int
    nome_fantasia: str
    email: EmailStr
    telefone: str
    endereco_completo: str
    lat: float
    lon: float
    taxa_entrega: float
    tempo_medio_preparo: int
    ativo: bool
    data_criacao: datetime

    class Config:
        from_attributes = True

class PedidoBase(BaseModel):
    nome_cliente: str
    telefone_cliente: str
    endereco: str
    itens: str
    valor_total: float

class PedidoCreate(PedidoBase):
    pass

class PedidoPublic(PedidoBase):
    id: int
    motoboy_id: Optional[int]
    status: str
    sequencia_entrega: Optional[int]
    distancia_estimada: Optional[float]
    data_criacao: datetime

    class Config:
        from_attributes = True
