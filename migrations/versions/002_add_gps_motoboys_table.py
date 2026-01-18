# migrations/versions/002_add_gps_motoboys_table.py

"""add gps_motoboys table

Revision ID: 002_add_gps_motoboys_table
Revises: 001_initial_schema
Create Date: 2026-01-17 23:00:00.000000

Cria tabela gps_motoboys para histórico de localização dos motoboys
"""

from alembic import op
import sqlalchemy as sa

revision = '002_add_gps_motoboys_table'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('gps_motoboys',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('motoboy_id', sa.Integer(), sa.ForeignKey('motoboys.id', ondelete="CASCADE"), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete="CASCADE"), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=False),
        sa.Column('longitude', sa.Float(), nullable=False),
        sa.Column('velocidade', sa.Float(), default=0.0),
        sa.Column('timestamp', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Index('idx_gps_motoboy_timestamp', 'motoboy_id', 'timestamp'),
        sa.Index('idx_gps_restaurante', 'restaurante_id', 'timestamp')
    )

def downgrade():
    op.drop_table('gps_motoboys')