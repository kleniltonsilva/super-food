# migrations/env.py

"""
Configuracao do ambiente Alembic
Carrega models SQLAlchemy para autogenerate funcionar
Le DATABASE_URL do .env (prioridade sobre alembic.ini)
"""

from logging.config import fileConfig
import os
import sys

# Adiciona raiz do projeto ao path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importa Base e models
from database.base import Base
from database.models import *  # noqa: F403

# Config do ini
config = context.config

# Sobrescreve URL do banco com .env (se definida)
database_url = os.getenv("DATABASE_URL")
if database_url:
    # SQLAlchemy 2.0 nao aceita "postgres://" — converte para "postgresql://"
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    config.set_main_option("sqlalchemy.url", database_url)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata para autogenerate
target_metadata = Base.metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Pre-criar alembic_version com coluna maior (padrao Alembic e VARCHAR(32))
        from sqlalchemy import text, inspect
        inspector = inspect(connection)
        if not inspector.has_table("alembic_version"):
            connection.execute(text(
                "CREATE TABLE alembic_version ("
                "version_num VARCHAR(128) NOT NULL, "
                "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num))"
            ))
            connection.commit()
        else:
            # Expandir coluna se ja existe com tamanho menor (só PostgreSQL)
            if connection.dialect.name == "postgresql":
                connection.execute(text(
                    "ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"
                ))
                connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()