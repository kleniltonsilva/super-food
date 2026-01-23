"""
Script para recriar o banco SQLite do Super Food do zero
Cria super_admin e restaurantes básicas.
Depois você poderá rodar Alembic upgrade head sem erros
"""

import os
from sqlalchemy import create_engine, Column, Integer, String, Boolean, Float, DateTime, Table, MetaData
from datetime import datetime

DB_PATH = "super_food.db"

# Apaga banco antigo
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

# Cria engine SQLite
engine = create_engine(f"sqlite:///{DB_PATH}")

metadata = MetaData()

# Tabela super_admin
super_admin = Table(
    "super_admin",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("usuario", String(50), nullable=False),
    Column("senha_hash", String(256), nullable=False),
    Column("email", String(100)),
    Column("ativo", Boolean, default=True),
    Column("criado_em", DateTime, default=datetime.utcnow),
)

# Tabela restaurantes
restaurantes = Table(
    "restaurantes",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nome", String(100)),
    Column("nome_fantasia", String(100)),
    Column("razao_social", String(100)),
    Column("cnpj", String(20)),
    Column("email", String(100)),
    Column("senha", String(100)),  # coluna que depois será renomeada pelo Alembic
    Column("telefone", String(30)),
    Column("endereco_completo", String(255)),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("plano", String(50)),
    Column("valor_plano", Float),
    Column("limite_motoboys", Integer),
    Column("codigo_acesso", String(50)),
    Column("ativo", Boolean, default=True),
    Column("status", String(50)),
    Column("criado_em", DateTime, default=datetime.utcnow),
    Column("data_vencimento", DateTime),
)

# Cria todas as tabelas
metadata.create_all(engine)

print("Banco recriado com sucesso! Agora rode: alembic upgrade head")
