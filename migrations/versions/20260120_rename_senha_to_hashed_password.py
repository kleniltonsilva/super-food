# migrations/versions/20260120_rename_senha_to_hashed_password.py
"""Renomear coluna senha para hashed_password na tabela restaurantes

Revision ID: 20260120
Revises: (head anterior)
Create Date: 2026-01-20 23:42:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260120'
down_revision = None  # ajuste se houver migration anterior
branch_labels = None
depends_on = None

def upgrade():
    # Renomeia coluna preservando dados existentes
    op.alter_column(
        table_name='restaurantes',
        column_name='senha',
        new_column_name='hashed_password',
        existing_type=sa.String(length=256),
        existing_nullable=False
    )

def downgrade():
    # Reverte renomeação
    op.alter_column(
        table_name='restaurantes',
        column_name='hashed_password',
        new_column_name='senha',
        existing_type=sa.String(length=256),
        existing_nullable=False
    )