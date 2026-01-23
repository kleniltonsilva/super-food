# backend/app/schemas/cliente_schemas.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date, datetime

class ClienteCadastroRequest(BaseModel):
    nome: str
    email: EmailStr
    telefone: str
    senha: str
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
   
    class Config:
        from_attributes = True