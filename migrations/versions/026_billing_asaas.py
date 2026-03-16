"""Sistema de billing/assinatura com Asaas

Revision ID: 026_billing_asaas
Revises: 025_platform_credentials
Create Date: 2026-03-16

- Cria 6 tabelas de billing (config, clientes, assinaturas, pagamentos, event_log, audit_log)
- Adiciona campos billing_status, dias_vencido, trial_fim, plano_ciclo em restaurantes
- Insere config_billing default
- Marca restaurantes existentes como billing_status = 'manual'
"""
from alembic import op
import sqlalchemy as sa

revision = '026_billing_asaas'
down_revision = '025_platform_credentials'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. Tabela config_billing ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS config_billing (
            id SERIAL PRIMARY KEY,
            trial_dias INTEGER DEFAULT 20,
            trial_plano VARCHAR(50) DEFAULT 'Premium',
            dias_lembrete_antes INTEGER DEFAULT 5,
            dias_suspensao INTEGER DEFAULT 2,
            dias_aviso_cancelamento INTEGER DEFAULT 5,
            dias_cancelamento INTEGER DEFAULT 15,
            dias_preservacao_dados INTEGER DEFAULT 90,
            desconto_anual_percentual FLOAT DEFAULT 20.0,
            asaas_webhook_token VARCHAR(200),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)

    # ── 2. Tabela asaas_clientes ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS asaas_clientes (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            asaas_customer_id VARCHAR(100) NOT NULL UNIQUE,
            nome VARCHAR(200),
            cpf_cnpj VARCHAR(20),
            email VARCHAR(100),
            telefone VARCHAR(20),
            sincronizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_asaas_cliente_restaurante ON asaas_clientes (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_cliente_customer ON asaas_clientes (asaas_customer_id)")

    # ── 3. Tabela asaas_assinaturas ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS asaas_assinaturas (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            asaas_subscription_id VARCHAR(100) UNIQUE,
            plano VARCHAR(50) NOT NULL,
            valor FLOAT NOT NULL,
            ciclo VARCHAR(20) DEFAULT 'MONTHLY',
            billing_type VARCHAR(20) DEFAULT 'PIX',
            status VARCHAR(20) DEFAULT 'ACTIVE',
            proximo_vencimento TIMESTAMP,
            desconto_percentual FLOAT DEFAULT 0.0,
            em_trial BOOLEAN DEFAULT FALSE,
            trial_fim TIMESTAMP,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_assinatura_restaurante ON asaas_assinaturas (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_assinatura_status ON asaas_assinaturas (status)")

    # ── 4. Tabela asaas_pagamentos ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS asaas_pagamentos (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            asaas_payment_id VARCHAR(100) NOT NULL UNIQUE,
            asaas_subscription_id VARCHAR(100),
            valor FLOAT NOT NULL,
            valor_liquido FLOAT,
            billing_type VARCHAR(20),
            status VARCHAR(30) DEFAULT 'PENDING',
            data_vencimento TIMESTAMP,
            data_pagamento TIMESTAMP,
            pix_qr_code TEXT,
            pix_copia_cola TEXT,
            boleto_url VARCHAR(500),
            invoice_url VARCHAR(500),
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_pagamento_restaurante ON asaas_pagamentos (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_pagamento_status ON asaas_pagamentos (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_pagamento_vencimento ON asaas_pagamentos (data_vencimento)")

    # ── 5. Tabela asaas_event_log ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS asaas_event_log (
            id SERIAL PRIMARY KEY,
            event_id VARCHAR(200) NOT NULL UNIQUE,
            event_type VARCHAR(50) NOT NULL,
            asaas_payment_id VARCHAR(100),
            restaurante_id INTEGER REFERENCES restaurantes(id) ON DELETE SET NULL,
            payload_json JSON,
            processed BOOLEAN DEFAULT FALSE,
            error_message TEXT,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_asaas_event_type ON asaas_event_log (event_type, criado_em)")

    # ── 6. Tabela billing_audit_log ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS billing_audit_log (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER REFERENCES restaurantes(id) ON DELETE SET NULL,
            acao VARCHAR(50) NOT NULL,
            detalhes JSON,
            admin_id INTEGER,
            automatico BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_audit_restaurante ON billing_audit_log (restaurante_id, criado_em)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_billing_audit_acao ON billing_audit_log (acao, criado_em)")

    # ── 7. Colunas novas em restaurantes ──
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='restaurantes' AND column_name='billing_status') THEN
                ALTER TABLE restaurantes ADD COLUMN billing_status VARCHAR(30) DEFAULT 'manual';
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='restaurantes' AND column_name='dias_vencido') THEN
                ALTER TABLE restaurantes ADD COLUMN dias_vencido INTEGER DEFAULT 0;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='restaurantes' AND column_name='trial_fim') THEN
                ALTER TABLE restaurantes ADD COLUMN trial_fim TIMESTAMP;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='restaurantes' AND column_name='plano_ciclo') THEN
                ALTER TABLE restaurantes ADD COLUMN plano_ciclo VARCHAR(20) DEFAULT 'MONTHLY';
            END IF;
        END $$;
    """)

    # ── 8. Inserir config_billing default ──
    op.execute("""
        INSERT INTO config_billing (trial_dias, trial_plano, dias_lembrete_antes, dias_suspensao, dias_aviso_cancelamento, dias_cancelamento, dias_preservacao_dados, desconto_anual_percentual)
        SELECT 20, 'Premium', 5, 2, 5, 15, 90, 20.0
        WHERE NOT EXISTS (SELECT 1 FROM config_billing LIMIT 1)
    """)

    # ── 9. Marcar restaurantes existentes como 'manual' ──
    op.execute("UPDATE restaurantes SET billing_status = 'manual' WHERE billing_status IS NULL")


def downgrade():
    op.execute("DROP TABLE IF EXISTS billing_audit_log CASCADE")
    op.execute("DROP TABLE IF EXISTS asaas_event_log CASCADE")
    op.execute("DROP TABLE IF EXISTS asaas_pagamentos CASCADE")
    op.execute("DROP TABLE IF EXISTS asaas_assinaturas CASCADE")
    op.execute("DROP TABLE IF EXISTS asaas_clientes CASCADE")
    op.execute("DROP TABLE IF EXISTS config_billing CASCADE")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS billing_status")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS dias_vencido")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS trial_fim")
    op.execute("ALTER TABLE restaurantes DROP COLUMN IF EXISTS plano_ciclo")
