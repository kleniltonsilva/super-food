"""Billing separado para add-ons — tabela addon_cobrancas + campos recorrência

Revision ID: 047_addon_billing_separado
Revises: 046_bot_phone_registration
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa

revision = "047_addon_billing_separado"
down_revision = "046_bot_phone_registration"
branch_labels = None
depends_on = None


def upgrade():
    # ── Tabela addon_cobrancas ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS addon_cobrancas (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            addon VARCHAR(50) NOT NULL DEFAULT 'bot_whatsapp',
            asaas_payment_id VARCHAR(100) UNIQUE,
            valor FLOAT NOT NULL DEFAULT 99.45,
            billing_type VARCHAR(20) DEFAULT 'UNDEFINED',
            status VARCHAR(30) DEFAULT 'PENDING',
            data_vencimento TIMESTAMP,
            data_pagamento TIMESTAMP,
            pix_qr_code TEXT,
            pix_copia_cola TEXT,
            boleto_url VARCHAR(500),
            invoice_url VARCHAR(500),
            ciclo_inicio DATE,
            ciclo_numero INTEGER DEFAULT 1,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_cobranca_rest ON addon_cobrancas(restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_cobranca_status ON addon_cobrancas(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_addon_cobranca_asaas ON addon_cobrancas(asaas_payment_id)")

    # ── Novos campos em restaurantes ──
    op.execute("ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS addon_bot_ciclo_inicio DATE")
    op.execute("ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS addon_bot_proximo_vencimento DATE")
    op.execute("ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS addon_bot_asaas_payment_id VARCHAR(100)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS addon_cobrancas")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS addon_bot_ciclo_inicio")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS addon_bot_proximo_vencimento")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS addon_bot_asaas_payment_id")
