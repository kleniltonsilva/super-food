"""
Database Configuration - Super Food API
Suporta SQLite (dev) e PostgreSQL (producao)
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Adiciona raiz do projeto ao path para importar models compartilhados
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

# URL do banco
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/super_food.db")

# SQLAlchemy 2.0 nao aceita "postgres://" — converte para "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Detecta se esta usando PgBouncer (porta 6432 ou env var)
PGBOUNCER_ACTIVE = os.getenv("PGBOUNCER_ACTIVE", "").lower() == "true" or ":6432/" in DATABASE_URL

# Configuracoes do engine
if "sqlite" in DATABASE_URL:
    # SQLite: usar StaticPool e check_same_thread=False
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
elif PGBOUNCER_ACTIVE:
    # PostgreSQL via PgBouncer: pool pequeno (PgBouncer gerencia conexoes)
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_recycle=1800,
        echo=False
    )
else:
    # PostgreSQL direto: pool padrao para producao
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=1800,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importar Base do projeto principal para compartilhar models
from database.base import Base


def get_db():
    """Dependency para injecao em routers FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
