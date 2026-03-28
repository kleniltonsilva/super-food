"""Adicionar colunas restantes faltantes em promocoes

Revision ID: 039_fix_promocoes_remaining_cols
Revises: 038_add_missing_columns
Create Date: 2026-03-28

Migration 038 já adicionou descricao + atualizado_em.
Esta adiciona: desconto_maximo, valor_pedido_minimo, uso_limitado,
limite_usos, usos_realizados, data_inicio, data_fim, codigo_cupom.
"""

from alembic import op
import sqlalchemy as sa

revision = '039_fix_promocoes_remaining_cols'
down_revision = '038_add_missing_columns'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'promocoes') THEN
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS desconto_maximo FLOAT;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS valor_pedido_minimo FLOAT DEFAULT 0.0;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS uso_limitado BOOLEAN DEFAULT FALSE;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS limite_usos INTEGER;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS usos_realizados INTEGER DEFAULT 0;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS data_inicio TIMESTAMP;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS data_fim TIMESTAMP;
                ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS codigo_cupom VARCHAR(50);
            END IF;
        END $$;
    """)

    # Indices para consultas de promoções
    op.execute("CREATE INDEX IF NOT EXISTS idx_promocao_datas ON promocoes (restaurante_id, data_inicio, data_fim)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_promocao_codigo ON promocoes (restaurante_id, codigo_cupom)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_promocao_codigo")
    op.execute("DROP INDEX IF EXISTS idx_promocao_datas")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'promocoes') THEN
                ALTER TABLE promocoes DROP COLUMN IF EXISTS codigo_cupom;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS data_fim;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS data_inicio;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS usos_realizados;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS limite_usos;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS uso_limitado;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS valor_pedido_minimo;
                ALTER TABLE promocoes DROP COLUMN IF EXISTS desconto_maximo;
            END IF;
        END $$;
    """)
