# migrations/versions/048_pedido_pago_online.py
"""Adiciona campos pago_online e data_pagamento_online ao Pedido.

Permite rastrear pedidos pagos via Pix Online (Woovi) em todo o sistema:
painel admin, motoboy, site cliente.
"""

from alembic import op
import sqlalchemy as sa

revision = "048"
down_revision = "047"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE pedidos
        ADD COLUMN IF NOT EXISTS pago_online BOOLEAN DEFAULT FALSE;
    """)
    op.execute("""
        ALTER TABLE pedidos
        ADD COLUMN IF NOT EXISTS data_pagamento_online TIMESTAMP;
    """)


def downgrade():
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS data_pagamento_online;")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS pago_online;")
