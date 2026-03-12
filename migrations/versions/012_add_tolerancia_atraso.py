"""012 - Adiciona tolerancia_atraso_min em config_restaurante

Revision ID: 012_add_tolerancia_atraso
Revises: 011_add_aceitar_pedido_site_auto
Create Date: 2026-03-11

Novo campo:
- config_restaurante.tolerancia_atraso_min: Integer (default=10)
  Minutos de tolerância antes de marcar entrega como atrasada.
"""

from alembic import op
import sqlalchemy as sa

revision = '012_add_tolerancia_atraso'
down_revision = '011_add_aceitar_pedido_site_auto'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'config_restaurante',
        sa.Column('tolerancia_atraso_min', sa.Integer(), server_default='10', nullable=False)
    )


def downgrade():
    op.drop_column('config_restaurante', 'tolerancia_atraso_min')
