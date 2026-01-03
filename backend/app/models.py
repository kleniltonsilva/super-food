from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import enum

class StatusPedido(str, enum.Enum):
    pendente = "pendente"
    atribuido = "atribuido"
    em_rota = "em_rota"
    entregue = "entregue"

class StatusMotoboy(str, enum.Enum):
    disponivel = "disponivel"
    ocupado = "ocupado"
    offline = "offline"

class Restaurante(Base):
    __tablename__ = "restaurantes"

    id = Column(Integer, primary_key=True, index=True)
    nome_fantasia = Column(String, unique=True, index=True)
    razao_social = Column(String, nullable=True)
    cnpj = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    telefone = Column(String)
    endereco_completo = Column(Text)
    lat = Column(Float)
    lon = Column(Float)
    taxa_entrega = Column(Float, default=0.0)
    tempo_medio_preparo = Column(Integer, default=30)
    ativo = Column(Boolean, default=True)
    data_criacao = Column(DateTime, default=datetime.utcnow)

    pedidos = relationship("Pedido", back_populates="restaurante")
    motoboys = relationship("Motoboy", back_populates="restaurante")

class Motoboy(Base):
    __tablename__ = "motoboys"

    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id"))
    nome = Column(String)
    telefone = Column(String)
    lat_atual = Column(Float, nullable=True)
    lon_atual = Column(Float, nullable=True)
    status = Column(Enum(StatusMotoboy), default=StatusMotoboy.offline)
    ultimo_disponivel = Column(DateTime, nullable=True)
    entregas_hoje = Column(Integer, default=0)
    km_rodados_hoje = Column(Float, default=0.0)
    ativo = Column(Boolean, default=True)

    restaurante = relationship("Restaurante", back_populates="motoboys")
    pedidos = relationship("Pedido", back_populates="motoboy")

class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id"))
    motoboy_id = Column(Integer, ForeignKey("motoboys.id"), nullable=True)

    nome_cliente = Column(String)
    telefone_cliente = Column(String)
    endereco = Column(Text)
    lat_cliente = Column(Float)
    lon_cliente = Column(Float)
    itens = Column(Text)
    valor_total = Column(Float)
    sequencia_entrega = Column(Integer, nullable=True)
    distancia_estimada = Column(Float, nullable=True)

    status = Column(Enum(StatusPedido), default=StatusPedido.pendente)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atribuicao = Column(DateTime, nullable=True)

    restaurante = relationship("Restaurante", back_populates="pedidos")
    motoboy = relationship("Motoboy", back_populates="pedidos")
