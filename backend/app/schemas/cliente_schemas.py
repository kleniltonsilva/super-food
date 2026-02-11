# backend/app/schemas/cliente_schemas.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import date, datetime


# ==================== AUTH ====================

class ClienteCadastroRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    telefone: str = Field(..., min_length=10, max_length=20)
    senha: str = Field(..., min_length=6)
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None
    codigo_acesso_restaurante: str


class ClienteLoginRequest(BaseModel):
    email: EmailStr
    senha: str
    codigo_acesso_restaurante: str


class ClienteResponse(BaseModel):
    id: int
    nome: str
    email: str
    telefone: str
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    cliente: ClienteResponse


class RegistroPosPedidoRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    telefone: str = Field(..., min_length=10, max_length=20)
    senha: str = Field(..., min_length=6)
    codigo_acesso_restaurante: str
    pedido_id: Optional[int] = None


class ClientePerfilUpdate(BaseModel):
    nome: Optional[str] = Field(None, min_length=2, max_length=200)
    telefone: Optional[str] = Field(None, min_length=10, max_length=20)
    cpf: Optional[str] = None
    data_nascimento: Optional[date] = None


# ==================== ENDERECOS ====================

class EnderecoCreateRequest(BaseModel):
    apelido: Optional[str] = Field(None, max_length=50)
    cep: Optional[str] = Field(None, max_length=8)
    endereco_completo: str = Field(..., min_length=5)
    numero: Optional[str] = Field(None, max_length=10)
    complemento: Optional[str] = Field(None, max_length=200)
    bairro: Optional[str] = Field(None, max_length=100)
    cidade: Optional[str] = Field(None, max_length=100)
    estado: Optional[str] = Field(None, max_length=2)
    referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    padrao: Optional[bool] = False


class EnderecoUpdateRequest(BaseModel):
    apelido: Optional[str] = None
    cep: Optional[str] = None
    endereco_completo: Optional[str] = None
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    padrao: Optional[bool] = None


class EnderecoResponse(BaseModel):
    id: int
    apelido: Optional[str] = None
    cep: Optional[str] = None
    endereco_completo: str
    numero: Optional[str] = None
    complemento: Optional[str] = None
    bairro: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    referencia: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    padrao: bool = False

    class Config:
        from_attributes = True


# ==================== PEDIDOS DO CLIENTE ====================

class PedidoItemResponse(BaseModel):
    id: int
    produto_nome: Optional[str] = None
    quantidade: int
    preco_unitario: float
    observacoes: Optional[str] = None

    class Config:
        from_attributes = True


class PedidoClienteResponse(BaseModel):
    id: int
    comanda: Optional[str] = None
    status: str
    tipo: Optional[str] = None
    tipo_entrega: Optional[str] = None
    endereco_entrega: Optional[str] = None
    valor_total: float
    forma_pagamento: Optional[str] = None
    observacoes: Optional[str] = None
    data_criacao: datetime
    itens_texto: Optional[str] = None
    carrinho_json: Optional[list] = None

    class Config:
        from_attributes = True
