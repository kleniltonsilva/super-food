"""Credenciais de plataforma + refatorar integracoes_marketplace

Revision ID: 025_platform_credentials
Revises: 024_marketplace_integration
Create Date: 2026-03-16

- Cria tabela credenciais_plataforma (1 por marketplace, Super Admin)
- Adiciona authorization_status e authorized_at em integracoes_marketplace
- Migra client_id/client_secret existentes para credenciais_plataforma
- Remove client_id/client_secret de integracoes_marketplace
"""
from alembic import op
import sqlalchemy as sa

revision = '025_platform_credentials'
down_revision = '024_marketplace_integration'
branch_labels = None
depends_on = None


def upgrade():
    # ─── 1. Criar tabela credenciais_plataforma ───
    op.execute("""
        CREATE TABLE IF NOT EXISTS credenciais_plataforma (
            id SERIAL PRIMARY KEY,
            marketplace VARCHAR(30) NOT NULL UNIQUE,
            client_id VARCHAR(200),
            client_secret VARCHAR(500),
            ativo BOOLEAN DEFAULT true,
            config_json JSON,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)

    # ─── 2. Adicionar campos de autorização em integracoes_marketplace ───
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'integracoes_marketplace' AND column_name = 'authorization_status'
            ) THEN
                ALTER TABLE integracoes_marketplace ADD COLUMN authorization_status VARCHAR(20) DEFAULT 'pending';
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'integracoes_marketplace' AND column_name = 'authorized_at'
            ) THEN
                ALTER TABLE integracoes_marketplace ADD COLUMN authorized_at TIMESTAMP;
            END IF;
        END $$;
    """)

    # ─── 3. Migrar credenciais existentes para credenciais_plataforma ───
    # Para cada marketplace que tenha client_id configurado, mover para a tabela da plataforma
    op.execute("""
        INSERT INTO credenciais_plataforma (marketplace, client_id, client_secret, ativo, criado_em)
        SELECT DISTINCT ON (marketplace)
            marketplace, client_id, client_secret, true, NOW()
        FROM integracoes_marketplace
        WHERE client_id IS NOT NULL AND client_id != ''
        ON CONFLICT (marketplace) DO NOTHING
    """)

    # ─── 4. Marcar integrações existentes com tokens como autorizadas ───
    op.execute("""
        UPDATE integracoes_marketplace
        SET authorization_status = 'authorized', authorized_at = criado_em
        WHERE access_token IS NOT NULL AND access_token != ''
    """)

    # ─── 5. Remover client_id e client_secret de integracoes_marketplace ───
    op.execute("ALTER TABLE integracoes_marketplace DROP COLUMN IF EXISTS client_id")
    op.execute("ALTER TABLE integracoes_marketplace DROP COLUMN IF EXISTS client_secret")


def downgrade():
    # Restaurar colunas em integracoes_marketplace
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'integracoes_marketplace' AND column_name = 'client_id'
            ) THEN
                ALTER TABLE integracoes_marketplace ADD COLUMN client_id VARCHAR(200);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'integracoes_marketplace' AND column_name = 'client_secret'
            ) THEN
                ALTER TABLE integracoes_marketplace ADD COLUMN client_secret VARCHAR(200);
            END IF;
        END $$;
    """)

    # Restaurar credenciais da plataforma de volta para integracoes
    op.execute("""
        UPDATE integracoes_marketplace im
        SET client_id = cp.client_id, client_secret = cp.client_secret
        FROM credenciais_plataforma cp
        WHERE im.marketplace = cp.marketplace
    """)

    # Remover campos novos
    op.execute("ALTER TABLE integracoes_marketplace DROP COLUMN IF EXISTS authorization_status")
    op.execute("ALTER TABLE integracoes_marketplace DROP COLUMN IF EXISTS authorized_at")

    # Dropar tabela
    op.execute("DROP TABLE IF EXISTS credenciais_plataforma")
