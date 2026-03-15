"""Adicionar valor_subtotal e valor_taxa_entrega em pedidos

Revision ID: 023_pedido_taxa_entrega
Revises: 022_printer_agent
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = '023_pedido_taxa_entrega'
down_revision = '022_printer_agent'
branch_labels = None
depends_on = None


def upgrade():
    # Adicionar valor_subtotal e valor_taxa_entrega ao pedido
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'valor_subtotal'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN valor_subtotal FLOAT DEFAULT 0.0;
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'valor_taxa_entrega'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN valor_taxa_entrega FLOAT DEFAULT 0.0;
            END IF;
        END $$;
    """)

    # Preencher valor_subtotal retroativamente para pedidos existentes
    # subtotal = valor_total + valor_desconto (taxa era embutida no total)
    op.execute("""
        UPDATE pedidos
        SET valor_subtotal = COALESCE(valor_total, 0) + COALESCE(valor_desconto, 0),
            valor_taxa_entrega = 0
        WHERE valor_subtotal IS NULL OR valor_subtotal = 0;
    """)


def downgrade():
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS valor_subtotal")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS valor_taxa_entrega")
