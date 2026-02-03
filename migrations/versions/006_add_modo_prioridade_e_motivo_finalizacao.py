"""
Migration: Add modo_prioridade_entrega and motivo_finalizacao fields

v2.8.1 - Correções de bugs e melhorias:
1. Adiciona campo modo_prioridade_entrega em config_restaurante
   - rapido_economico: TSP por proximidade (padrão)
   - cronologico_inteligente: Agrupa por tempo, depois TSP
   - manual: Restaurante atribui manualmente

2. Adiciona campos motivo_finalizacao e motivo_cancelamento em entregas
   - Permite rastrear motivo de finalização (entregue, cliente_ausente, etc)
   - Motoboy recebe ganho mesmo em cancelamentos

Revision ID: 006
Revises: 005
Create Date: 2026-02-02
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '006_add_modo_prioridade'
down_revision = '005_add_motoboy_usuario_unique'
branch_labels = None
depends_on = None


def upgrade():
    """
    Adiciona campos para modo de prioridade de entrega e motivo de finalização.
    """
    # Adicionar campo modo_prioridade_entrega em config_restaurante
    op.add_column(
        'config_restaurante',
        sa.Column(
            'modo_prioridade_entrega',
            sa.String(50),
            nullable=True,
            server_default='rapido_economico'
        )
    )

    # Adicionar campo motivo_finalizacao em entregas
    op.add_column(
        'entregas',
        sa.Column(
            'motivo_finalizacao',
            sa.String(50),
            nullable=True
        )
    )

    # Adicionar campo motivo_cancelamento em entregas (se não existir)
    # Este campo pode já existir em algumas instalações
    try:
        op.add_column(
            'entregas',
            sa.Column(
                'motivo_cancelamento',
                sa.Text,
                nullable=True
            )
        )
    except Exception:
        # Campo já existe, ignorar
        pass


def downgrade():
    """Remove os campos adicionados."""
    # Remover campo motivo_cancelamento de entregas
    try:
        op.drop_column('entregas', 'motivo_cancelamento')
    except Exception:
        pass

    # Remover campo motivo_finalizacao de entregas
    op.drop_column('entregas', 'motivo_finalizacao')

    # Remover campo modo_prioridade_entrega de config_restaurante
    op.drop_column('config_restaurante', 'modo_prioridade_entrega')
