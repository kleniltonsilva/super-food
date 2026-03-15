"""create dominios_personalizados table

Revision ID: 018_dominios_personalizados
Revises: 017_eh_pizza_email
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '018_dominios_personalizados'
down_revision = '017_eh_pizza_email'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS dominios_personalizados (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            dominio VARCHAR(255) NOT NULL UNIQUE,
            tipo VARCHAR(20) NOT NULL DEFAULT 'cname',
            verificado BOOLEAN DEFAULT false,
            dns_verificado_em TIMESTAMP,
            ssl_ativo BOOLEAN DEFAULT false,
            ativo BOOLEAN DEFAULT true,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_dominio_restaurante ON dominios_personalizados (restaurante_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_dominio_dominio ON dominios_personalizados (dominio)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS dominios_personalizados")
