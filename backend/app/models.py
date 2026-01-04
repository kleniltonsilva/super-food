# Substitua o arquivo completo backend/app/models.py (adiciona plano e codigo_acesso ao modelo Restaurante)
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import secrets

class Restaurante(Base):
    __tablename__ = "restaurantes"

    id = Column(Integer, primary_key=True, index=True)
    nome_fantasia = Column(String, index=True, nullable=False)
    razao_social = Column(String, nullable=True)
    cnpj = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    telefone = Column(String, nullable=False)
    endereco_completo = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    taxa_entrega = Column(Float, default=0.0)
    tempo_medio_preparo = Column(Integer, default=30)
    plano = Column(String, default="basico")  # basico, medio, premium
    codigo_acesso = Column(String, unique=True, nullable=False)  # Código para motoboys se cadastrarem
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    # Relacionamentos
    pedidos = relationship("Pedido", back_populates="restaurante")
    motoboys = relationship("Motoboy", back_populates="restaurante")

    def gerar_codigo_acesso(self):
        self.codigo_acesso = secrets.token_hex(4).upper()  # Ex: A1B2C3D4 (8 caracteres hex)

class Motoboy(Base):
    __tablename__ = "motoboys"

    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id"), nullable=False)
    nome = Column(String, nullable=False)
    status = Column(String, default="disponivel")  # disponivel, ocupado, offline
    lat_atual = Column(Float, nullable=True)
    lon_atual = Column(Float, nullable=True)
    ultimo_disponivel = Column(DateTime, nullable=True)
    entregas_hoje = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)

    restaurante = relationship("Restaurante", back_populates="motoboys")
    pedidos = relationship("Pedido", back_populates="motoboy")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id"), nullable=False)
    motoboy_id = Column(Integer, ForeignKey("motoboys.id"), nullable=True)
    comanda = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # Entrega, Retirada na loja, Para mesa
    cliente_nome = Column(String, nullable=False)
    cliente_telefone = Column(String, nullable=True)
    endereco_entrega = Column(String, nullable=True)
    numero_mesa = Column(String, nullable=True)
    lat_cliente = Column(Float, nullable=True)
    lon_cliente = Column(Float, nullable=True)
    itens = Column(String, nullable=False)
    observacoes = Column(String, nullable=True)
    tempo_estimado = Column(Integer, nullable=False)
    status = Column(String, default="pendente")  # pendente, atribuido, em_rota, entregue, etc.
    sequencia_entrega = Column(Integer, nullable=True)
    distancia_estimada = Column(Float, nullable=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atribuicao = Column(DateTime, nullable=True)

    restaurante = relationship("Restaurante", back_populates="pedidos")
    motoboy = relationship("Motoboy", back_populates="pedidos")
