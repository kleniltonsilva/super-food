"""KDS - campos pausa/despausar em pedidos_cozinha

Revision ID: 031_kds_pausa
Revises: 030_planos_tabela
Create Date: 2026-03-22

- Adiciona campos pausado, pausado_em, despausado_em, posicao_original em pedidos_cozinha
"""
from alembic import op
import sqlalchemy as sa

revision = '031_kds_pausa'
down_revision = '030_planos_tabela'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Campos de pausa em pedidos_cozinha
    op.execute("ALTER TABLE pedidos_cozinha ADD COLUMN IF NOT EXISTS pausado BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE pedidos_cozinha ADD COLUMN IF NOT EXISTS pausado_em TIMESTAMP")
    op.execute("ALTER TABLE pedidos_cozinha ADD COLUMN IF NOT EXISTS despausado_em TIMESTAMP")
    op.execute("ALTER TABLE pedidos_cozinha ADD COLUMN IF NOT EXISTS posicao_original INTEGER")


def downgrade() -> None:
    op.execute("ALTER TABLE pedidos_cozinha DROP COLUMN IF EXISTS pausado")
    op.execute("ALTER TABLE pedidos_cozinha DROP COLUMN IF EXISTS pausado_em")
    op.execute("ALTER TABLE pedidos_cozinha DROP COLUMN IF EXISTS despausado_em")
    op.execute("ALTER TABLE pedidos_cozinha DROP COLUMN IF EXISTS posicao_original")
