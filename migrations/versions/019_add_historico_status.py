"""add historico_status JSON column to pedidos

Revision ID: 019_historico_status
Revises: 018_dominios_personalizados
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '019_historico_status'
down_revision = '018_dominios_personalizados'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'historico_status'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN historico_status JSON;
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS historico_status")
