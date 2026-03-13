"""004 - Adiciona campos para seleção justa de motoboys

Revision ID: 004_add_motoboy_selection
Revises: 003_add_site_cliente_schema
Create Date: 2026-01-31

Adiciona campos ao model Motoboy para suportar:
- Rotação justa na seleção de entregas
- Controle de disponibilidade e status de rota
- Rastreamento de última entrega/rota
- Soft delete com reativação em 30 dias
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '004_add_motoboy_selection'
down_revision = '003_add_site_cliente_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Adiciona novos campos à tabela motoboys"""

    # Adicionar novos campos
    with op.batch_alter_table('motoboys', schema=None) as batch_op:
        # Total km percorridos
        batch_op.add_column(sa.Column('total_km', sa.Float(), nullable=True, default=0.0))

        # Seleção justa
        batch_op.add_column(sa.Column('ordem_hierarquia', sa.Integer(), nullable=True, default=0))
        batch_op.add_column(sa.Column('disponivel', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('em_rota', sa.Boolean(), nullable=True, default=False))
        batch_op.add_column(sa.Column('entregas_pendentes', sa.Integer(), nullable=True, default=0))
        batch_op.add_column(sa.Column('ultima_entrega_em', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('ultima_rota_em', sa.DateTime(), nullable=True))

        # Soft delete
        batch_op.add_column(sa.Column('data_exclusao', sa.DateTime(), nullable=True))

        # Novos índices
        batch_op.create_index('idx_motoboy_disponivel', ['restaurante_id', 'disponivel', 'em_rota'])
        batch_op.create_index('idx_motoboy_hierarquia', ['restaurante_id', 'ordem_hierarquia'])

    # Inicializar valores padrão nos registros existentes
    op.execute("UPDATE motoboys SET total_km = 0.0 WHERE total_km IS NULL")
    op.execute("UPDATE motoboys SET ordem_hierarquia = id WHERE ordem_hierarquia IS NULL")
    op.execute("UPDATE motoboys SET disponivel = false WHERE disponivel IS NULL")
    op.execute("UPDATE motoboys SET em_rota = false WHERE em_rota IS NULL")
    op.execute("UPDATE motoboys SET entregas_pendentes = 0 WHERE entregas_pendentes IS NULL")


def downgrade():
    """Remove campos adicionados"""

    with op.batch_alter_table('motoboys', schema=None) as batch_op:
        # Remover índices
        batch_op.drop_index('idx_motoboy_disponivel')
        batch_op.drop_index('idx_motoboy_hierarquia')

        # Remover colunas
        batch_op.drop_column('data_exclusao')
        batch_op.drop_column('ultima_rota_em')
        batch_op.drop_column('ultima_entrega_em')
        batch_op.drop_column('entregas_pendentes')
        batch_op.drop_column('em_rota')
        batch_op.drop_column('disponivel')
        batch_op.drop_column('ordem_hierarquia')
        batch_op.drop_column('total_km')
