"""007 - Adiciona colunas faltantes em restaurantes, config_restaurante e entregas

Revision ID: 007_add_missing_columns
Revises: b7b9e66c49bc
Create Date: 2026-02-08

Corrige discrepância entre models.py e o banco de dados:
- restaurantes: cidade, estado, cep
- config_restaurante: valor_base_motoboy, valor_km_extra_motoboy, max_pedidos_por_rota, permitir_ver_saldo_motoboy
- entregas: valor_motoboy, valor_base_motoboy, valor_extra_motoboy
"""

from alembic import op
import sqlalchemy as sa

revision = '007_add_missing_columns'
down_revision = 'b7b9e66c49bc'
branch_labels = None
depends_on = None


def upgrade():
    # === RESTAURANTES: cidade, estado, cep ===
    op.add_column('restaurantes', sa.Column('cidade', sa.String(100), nullable=True))
    op.add_column('restaurantes', sa.Column('estado', sa.String(2), nullable=True))
    op.add_column('restaurantes', sa.Column('cep', sa.String(10), nullable=True))

    # === CONFIG_RESTAURANTE: campos de pagamento motoboy e rota ===
    op.add_column('config_restaurante', sa.Column('valor_base_motoboy', sa.Float(), nullable=True, server_default='5.0'))
    op.add_column('config_restaurante', sa.Column('valor_km_extra_motoboy', sa.Float(), nullable=True, server_default='1.0'))
    op.add_column('config_restaurante', sa.Column('max_pedidos_por_rota', sa.Integer(), nullable=True, server_default='5'))
    op.add_column('config_restaurante', sa.Column('permitir_ver_saldo_motoboy', sa.Boolean(), nullable=True, server_default=sa.true()))

    # === ENTREGAS: campos de pagamento ao motoboy ===
    op.add_column('entregas', sa.Column('valor_motoboy', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('entregas', sa.Column('valor_base_motoboy', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('entregas', sa.Column('valor_extra_motoboy', sa.Float(), nullable=True, server_default='0.0'))


def downgrade():
    # Entregas
    op.drop_column('entregas', 'valor_extra_motoboy')
    op.drop_column('entregas', 'valor_base_motoboy')
    op.drop_column('entregas', 'valor_motoboy')

    # Config restaurante
    op.drop_column('config_restaurante', 'permitir_ver_saldo_motoboy')
    op.drop_column('config_restaurante', 'max_pedidos_por_rota')
    op.drop_column('config_restaurante', 'valor_km_extra_motoboy')
    op.drop_column('config_restaurante', 'valor_base_motoboy')

    # Restaurantes
    op.drop_column('restaurantes', 'cep')
    op.drop_column('restaurantes', 'estado')
    op.drop_column('restaurantes', 'cidade')
