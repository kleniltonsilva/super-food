"""015 - Adiciona campo modo_preco_pizza ao ConfigRestaurante

Revision ID: 015_add_modo_preco_pizza
Revises: 014_add_ingredientes_json
Create Date: 2026-03-12

Novo campo:
- config_restaurante: modo_preco_pizza (String 20, default 'mais_caro')
  Modos: "mais_caro" (cobra pelo sabor mais caro) ou "proporcional" (divide proporcionalmente)
"""

from alembic import op
import sqlalchemy as sa

revision = '015_add_modo_preco_pizza'
down_revision = '014_add_ingredientes_json'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('config_restaurante', sa.Column('modo_preco_pizza', sa.String(20), server_default='mais_caro'))


def downgrade():
    op.drop_column('config_restaurante', 'modo_preco_pizza')
