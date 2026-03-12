"""014 - Adiciona campo ingredientes_json ao Produto

Revision ID: 014_add_ingredientes_json
Revises: 013_add_caixa_pagamento_fields
Create Date: 2026-03-11

Novo campo:
- produtos: ingredientes_json (JSON) — lista de ingredientes do produto
  Ex: ["Calabresa", "Cebola", "Molho de Tomate", "Mussarela"]
"""

from alembic import op
import sqlalchemy as sa

revision = '014_add_ingredientes_json'
down_revision = '013_add_caixa_pagamento_fields'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('produtos', sa.Column('ingredientes_json', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('produtos', 'ingredientes_json')
