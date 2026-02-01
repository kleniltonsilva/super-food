"""
Database Configuration - Super Food API
Compartilha o mesmo banco de dados com o Streamlit (super_food.db)
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

# URL do banco - MESMO banco usado pelo Streamlit
# IMPORTANTE: O banco fica na RAIZ do projeto (super_food.db)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/super_food.db")

# Configurações do engine
if "sqlite" in DATABASE_URL:
    # SQLite: usar StaticPool e check_same_thread=False
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    # PostgreSQL: configuração padrão para produção
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=False
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Importar Base do projeto principal para compartilhar models
from database.base import Base


def get_db():
    """Dependency para injeção em routers FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
