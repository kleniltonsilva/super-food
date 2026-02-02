"""
Migration: Add unique constraint for motoboy usuario per restaurant

Garante que o nome de usuario do motoboy seja unico dentro de cada restaurante.
Isso previne conflitos de login e garante isolamento correto multi-tenant.

Revision ID: 005
Revises: 004
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '005_add_motoboy_usuario_unique'
down_revision = '004_add_motoboy_selection'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona constraint unique para (restaurante_id, usuario) na tabela motoboys.
    Isso garante que cada usuario seja unico dentro de um restaurante.
    """
    # Criar indice unico composto
    op.create_index(
        'ix_motoboys_restaurante_usuario_unique',
        'motoboys',
        ['restaurante_id', 'usuario'],
        unique=True
    )


def downgrade():
    """Remove a constraint unique."""
    op.drop_index('ix_motoboys_restaurante_usuario_unique', table_name='motoboys')
