"""Pix Online via Woovi/OpenPix - tabelas de config, cobrancas, saques e event log

Revision ID: 028_pix_woovi
Revises: 027_operadores_caixa
Create Date: 2026-03-21

- Cria tabela pix_config (configuracao Pix por restaurante, subconta Woovi)
- Cria tabela pix_cobrancas (cobrancas Pix por pedido)
- Cria tabela pix_saques (historico de saques)
- Cria tabela pix_event_log (log de webhooks para idempotencia)
"""
from alembic import op
import sqlalchemy as sa

revision = '028_pix_woovi'
down_revision = '027_operadores_caixa'
branch_labels = None
depends_on = None


def upgrade():
    # --- pix_config ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS pix_config (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            ativo BOOLEAN DEFAULT FALSE,
            pix_chave VARCHAR(255) NOT NULL,
            tipo_chave VARCHAR(20) NOT NULL,
            nome_subconta VARCHAR(200) NOT NULL,
            termos_aceitos_em TIMESTAMP NOT NULL,
            ativado_em TIMESTAMP,
            saque_automatico BOOLEAN DEFAULT FALSE,
            saque_minimo_centavos INTEGER DEFAULT 50000,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_config_restaurante ON pix_config (restaurante_id)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pix_config_restaurante') THEN
                ALTER TABLE pix_config ADD CONSTRAINT uq_pix_config_restaurante UNIQUE (restaurante_id);
            END IF;
        END $$;
    """)

    # --- pix_cobrancas ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS pix_cobrancas (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            woovi_charge_id VARCHAR(100),
            correlation_id VARCHAR(100) NOT NULL,
            valor_centavos INTEGER NOT NULL,
            transaction_id VARCHAR(100),
            status VARCHAR(30) DEFAULT 'ACTIVE',
            qr_code_imagem TEXT,
            br_code TEXT,
            expira_em TIMESTAMP,
            pago_em TIMESTAMP,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_cobranca_restaurante ON pix_cobrancas (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_cobranca_pedido ON pix_cobrancas (pedido_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_cobranca_status ON pix_cobrancas (restaurante_id, status)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pix_cobranca_woovi_charge_id') THEN
                ALTER TABLE pix_cobrancas ADD CONSTRAINT uq_pix_cobranca_woovi_charge_id UNIQUE (woovi_charge_id);
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pix_cobranca_correlation_id') THEN
                ALTER TABLE pix_cobrancas ADD CONSTRAINT uq_pix_cobranca_correlation_id UNIQUE (correlation_id);
            END IF;
        END $$;
    """)

    # --- pix_saques ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS pix_saques (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            valor_centavos INTEGER NOT NULL,
            taxa_centavos INTEGER DEFAULT 0,
            status VARCHAR(30) DEFAULT 'solicitado',
            automatico BOOLEAN DEFAULT FALSE,
            solicitado_em TIMESTAMP DEFAULT NOW(),
            concluido_em TIMESTAMP,
            erro TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_saque_restaurante ON pix_saques (restaurante_id)")

    # --- pix_event_log ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS pix_event_log (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(200) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            woovi_charge_id VARCHAR(100),
            restaurante_id INTEGER REFERENCES restaurantes(id) ON DELETE SET NULL,
            payload_json JSONB,
            processed BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pix_event_id') THEN
                ALTER TABLE pix_event_log ADD CONSTRAINT uq_pix_event_id UNIQUE (event_id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pix_event_id ON pix_event_log (event_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS pix_event_log")
    op.execute("DROP TABLE IF EXISTS pix_saques")
    op.execute("DROP TABLE IF EXISTS pix_cobrancas")
    op.execute("DROP TABLE IF EXISTS pix_config")
