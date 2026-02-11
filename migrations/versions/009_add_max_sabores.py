"""009 - Adiciona campo max_sabores em variacoes_produto

Revision ID: 009_add_max_sabores
Revises: 008_add_combos
Create Date: 2026-02-09

Novo campo:
- variacoes_produto.max_sabores: Máximo de sabores para variações tipo "tamanho"
"""

from alembic import op
import sqlalchemy as sa

revision = '009_add_max_sabores'
down_revision = '008_add_combos'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('variacoes_produto', sa.Column('max_sabores', sa.Integer(), server_default='1'))


def downgrade():
    op.drop_column('variacoes_produto', 'max_sabores')
