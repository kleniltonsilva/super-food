"""Adicionar colunas faltantes em bairros_entrega e promocoes

Revision ID: 038_add_missing_columns
Revises: 037_repescagem_verificacao_senha
Create Date: 2026-03-28

Corrige: bairros_entrega.atualizado_em, promocoes.descricao, promocoes.atualizado_em
Causa: ORM model define colunas que nunca foram adicionadas via migration.
"""

from alembic import op
import sqlalchemy as sa

revision = '038_add_missing_columns'
down_revision = '037_repescagem_verificacao_senha'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === BAIRROS_ENTREGA: atualizado_em ===
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bairros_entrega') THEN
                ALTER TABLE bairros_entrega ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT now();
            END IF;
        END $$;
    """)

    # === PROMOCOES: descricao + atualizado_em ===
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'promocoes') THEN
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS descricao TEXT;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS atualizado_em TIMESTAMP DEFAULT now();
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'promocoes') THEN
                ALTER TABLE promocoes DROP COLUMN IF EXISTS atualizado_em;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS descricao;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'bairros_entrega') THEN
                ALTER TABLE bairros_entrega DROP COLUMN IF EXISTS atualizado_em;
            END IF;
        END $$;
    """)
