"""008 - Adiciona tabelas de Combos

Revision ID: 008_add_combos
Revises: 007_add_missing_columns
Create Date: 2026-02-09

Novas tabelas:
- combos: Combos promocionais do restaurante
- combo_itens: Itens que compõem cada combo
"""

from alembic import op
import sqlalchemy as sa

revision = '008_add_combos'
down_revision = '007_add_missing_columns'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'combos',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('nome', sa.String(200), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('preco_combo', sa.Float(), nullable=False),
        sa.Column('preco_original', sa.Float(), nullable=False),
        sa.Column('imagem_url', sa.String(500)),
        sa.Column('ativo', sa.Boolean(), default=True),
        sa.Column('ordem_exibicao', sa.Integer(), default=0),
        sa.Column('data_inicio', sa.DateTime()),
        sa.Column('data_fim', sa.DateTime()),
        sa.Column('criado_em', sa.DateTime()),
        sa.Column('atualizado_em', sa.DateTime()),
    )
    op.create_index('idx_combo_restaurante', 'combos', ['restaurante_id', 'ativo'])
    op.create_index('idx_combo_datas', 'combos', ['restaurante_id', 'data_inicio', 'data_fim'])

    op.create_table(
        'combo_itens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('combo_id', sa.Integer(), sa.ForeignKey('combos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('produto_id', sa.Integer(), sa.ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quantidade', sa.Integer(), nullable=False, default=1),
    )
    op.create_index('idx_combo_item_combo', 'combo_itens', ['combo_id'])


def downgrade():
    op.drop_index('idx_combo_item_combo', table_name='combo_itens')
    op.drop_table('combo_itens')
    op.drop_index('idx_combo_datas', table_name='combos')
    op.drop_index('idx_combo_restaurante', table_name='combos')
    op.drop_table('combos')
