"""Integração marketplace (iFood, 99Food, Rappi, Keeta)

Revision ID: 024_marketplace_integration
Revises: 023_pedido_taxa_entrega
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = '024_marketplace_integration'
down_revision = '023_pedido_taxa_entrega'
branch_labels = None
depends_on = None


def upgrade():
    # ─── Campos marketplace em pedidos ───
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'marketplace_source'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN marketplace_source VARCHAR(30);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'marketplace_order_id'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN marketplace_order_id VARCHAR(100);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'marketplace_display_id'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN marketplace_display_id VARCHAR(50);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'marketplace_raw_json'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN marketplace_raw_json JSON;
            END IF;
        END $$;
    """)

    # Índice marketplace em pedidos
    op.execute("CREATE INDEX IF NOT EXISTS idx_pedido_marketplace ON pedidos (restaurante_id, marketplace_source)")

    # ─── Tabela integracoes_marketplace ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS integracoes_marketplace (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            marketplace VARCHAR(30) NOT NULL,
            ativo BOOLEAN DEFAULT false,
            client_id VARCHAR(200),
            client_secret VARCHAR(200),
            merchant_id VARCHAR(200),
            access_token TEXT,
            refresh_token TEXT,
            token_expires_at TIMESTAMP,
            config_json JSON,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uq_integracao_marketplace UNIQUE (restaurante_id, marketplace)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_integracao_restaurante ON integracoes_marketplace (restaurante_id, marketplace)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_integracao_ativo ON integracoes_marketplace (marketplace, ativo)")

    # ─── Tabela marketplace_event_log ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS marketplace_event_log (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            marketplace VARCHAR(30) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            event_id VARCHAR(200) NOT NULL UNIQUE,
            payload_json JSON,
            processed BOOLEAN DEFAULT false,
            error_message TEXT,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_event_id ON marketplace_event_log (event_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_marketplace_event_rest ON marketplace_event_log (restaurante_id, marketplace, criado_em)")


def downgrade():
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS marketplace_source")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS marketplace_order_id")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS marketplace_display_id")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS marketplace_raw_json")
    op.execute("DROP INDEX IF EXISTS idx_pedido_marketplace")
    op.execute("DROP TABLE IF EXISTS marketplace_event_log")
    op.execute("DROP TABLE IF EXISTS integracoes_marketplace")
