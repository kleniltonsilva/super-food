"""
Database Session Manager - Super Food SaaS
Gerencia conexões e sessões do SQLAlchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os
from dotenv import load_dotenv

from .base import Base

# Carrega variáveis de ambiente
load_dotenv()

# URL do banco de dados (SQLite para dev, PostgreSQL para prod)
# IMPORTANTE: O banco fica na RAIZ do projeto, não dentro de /database/
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")

# SQLAlchemy 2.0 nao aceita "postgres://" — converte para "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Configurações do engine
if "sqlite" in DATABASE_URL:
    # SQLite: usar StaticPool e check_same_thread=False
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Mude para True para ver SQL no console
    )
else:
    # PostgreSQL: configuração padrão
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Testa conexão antes de usar
        echo=False
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Inicializa o banco de dados criando todas as tabelas
    Deve ser chamado no início do app
    """
    Base.metadata.create_all(bind=engine)
    print(f"✅ Banco de dados inicializado: {DATABASE_URL}")


def get_db():
    """
    Dependency para injeção de sessão
    Uso: db = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """
    Retorna uma sessão direta (sem generator)
    Uso: db = get_db_session()
    IMPORTANTE: Lembre de chamar db.close() depois!
    """
    return SessionLocal()


# ==================== FUNÇÕES AUXILIARES ====================
# Estas funções são wrappers para manter compatibilidade com código existente.
# A lógica principal está em database/seed/

def criar_super_admin_padrao():
    """
    Cria super admin padrão se não existir.

    Wrapper para compatibilidade - usa o sistema de seeds.
    """
    from database.seed.seed_001_super_admin import SuperAdminSeed

    db = get_db_session()
    try:
        seed = SuperAdminSeed()
        count = seed.run(db)
        if count > 0:
            print("✅ Super Admin padrão criado")
        else:
            print("ℹ️ Super Admin já existe")
    except Exception as e:
        print(f"❌ Erro ao criar super admin: {e}")
        db.rollback()
    finally:
        db.close()


def criar_config_padrao_restaurante(restaurante_id: int):
    """
    Cria configuração padrão para um restaurante.

    Wrapper para compatibilidade - usa o sistema de seeds.
    """
    from database.seed import criar_config_para_restaurante

    db = get_db_session()
    try:
        criar_config_para_restaurante(db, restaurante_id)
        print(f"✅ Config criada para restaurante {restaurante_id}")
    except Exception as e:
        print(f"❌ Erro ao criar config: {e}")
        db.rollback()
    finally:
        db.close()


def criar_categorias_padrao_restaurante(restaurante_id: int):
    """
    Cria categorias de menu padrão para um restaurante.

    Função nova - usa o sistema de seeds.
    """
    from database.seed import criar_categorias_para_restaurante

    db = get_db_session()
    try:
        count = criar_categorias_para_restaurante(db, restaurante_id)
        print(f"✅ {count} categorias criadas para restaurante {restaurante_id}")
    except Exception as e:
        print(f"❌ Erro ao criar categorias: {e}")
        db.rollback()
    finally:
        db.close()