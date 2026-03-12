"""016 - Adiciona campo ingredientes_adicionais_pizza ao SiteConfig

Revision ID: 016_add_ingredientes_adicionais_pizza
Revises: 015_add_modo_preco_pizza
Create Date: 2026-03-12

Novo campo:
- site_config: ingredientes_adicionais_pizza (JSON) — lista global de ingredientes
  adicionais para pizzaria. Ex: [{"nome": "Bacon", "preco": 5.0}, {"nome": "Champignon", "preco": 4.0}]
"""

from alembic import op
import sqlalchemy as sa

revision = '016_add_ingredientes_adicionais_pizza'
down_revision = '015_add_modo_preco_pizza'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('site_config', sa.Column('ingredientes_adicionais_pizza', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('site_config', 'ingredientes_adicionais_pizza')
