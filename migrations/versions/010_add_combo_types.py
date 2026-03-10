"""010 - Adiciona campos tipo_combo, dia_semana, quantidade_pessoas em combos

Revision ID: 010_add_combo_types
Revises: 009_add_max_sabores
Create Date: 2026-03-08

Novos campos:
- combos.tipo_combo: 'padrao' | 'do_dia' | 'kit_festa'
- combos.dia_semana: 0=Seg...6=Dom (para combos do dia)
- combos.quantidade_pessoas: Para kits festa (ex: 10, 20, 50)
"""

from alembic import op
import sqlalchemy as sa

revision = '010_add_combo_types'
down_revision = '009_add_max_sabores'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('combos', sa.Column('tipo_combo', sa.String(20), server_default='padrao'))
    op.add_column('combos', sa.Column('dia_semana', sa.Integer(), nullable=True))
    op.add_column('combos', sa.Column('quantidade_pessoas', sa.Integer(), nullable=True))
    op.create_index('idx_combo_tipo', 'combos', ['restaurante_id', 'tipo_combo', 'ativo'])


def downgrade():
    op.drop_index('idx_combo_tipo', table_name='combos')
    op.drop_column('combos', 'quantidade_pessoas')
    op.drop_column('combos', 'dia_semana')
    op.drop_column('combos', 'tipo_combo')
