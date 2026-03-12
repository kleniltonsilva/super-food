"""011 - Adiciona aceitar_pedido_site_auto em config_restaurante

Revision ID: 011_add_aceitar_pedido_site_auto
Revises: 010_add_combo_types
Create Date: 2026-03-10

Novo campo:
- config_restaurante.aceitar_pedido_site_auto: Boolean (default=False)
  Se True, pedidos do site são aceitos automaticamente para clientes
  que já têm ao menos 1 pedido concluído com sucesso neste restaurante.
"""

from alembic import op
import sqlalchemy as sa

revision = '011_add_aceitar_pedido_site_auto'
down_revision = '010_add_combo_types'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'config_restaurante',
        sa.Column('aceitar_pedido_site_auto', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade():
    op.drop_column('config_restaurante', 'aceitar_pedido_site_auto')
