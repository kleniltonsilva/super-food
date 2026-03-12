"""013 - Adiciona campos de pagamento no caixa e movimentações

Revision ID: 013_add_caixa_pagamento_fields
Revises: 012_add_tolerancia_atraso
Create Date: 2026-03-11

Novos campos:
- caixa: total_dinheiro, total_cartao, total_pix, total_vale (Float default 0)
- movimentacoes_caixa: forma_pagamento (String 50), pedido_id (FK pedidos.id)
"""

from alembic import op
import sqlalchemy as sa

revision = '013_add_caixa_pagamento_fields'
down_revision = '012_add_tolerancia_atraso'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('caixa', sa.Column('total_dinheiro', sa.Float(), server_default='0', nullable=False))
    op.add_column('caixa', sa.Column('total_cartao', sa.Float(), server_default='0', nullable=False))
    op.add_column('caixa', sa.Column('total_pix', sa.Float(), server_default='0', nullable=False))
    op.add_column('caixa', sa.Column('total_vale', sa.Float(), server_default='0', nullable=False))
    op.add_column('movimentacoes_caixa', sa.Column('forma_pagamento', sa.String(50), nullable=True))
    op.add_column('movimentacoes_caixa', sa.Column('pedido_id', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('movimentacoes_caixa', 'pedido_id')
    op.drop_column('movimentacoes_caixa', 'forma_pagamento')
    op.drop_column('caixa', 'total_vale')
    op.drop_column('caixa', 'total_pix')
    op.drop_column('caixa', 'total_cartao')
    op.drop_column('caixa', 'total_dinheiro')
