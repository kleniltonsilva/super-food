"""Repescagem avançada, verificação email e reset senha

Revision ID: 037_repescagem_verificacao_senha
Revises: 036_bot_whatsapp_v2
Create Date: 2026-03-26

- clientes: +6 campos (verificação email + reset senha)
- promocoes: +2 campos (cliente_id, tipo_cupom)
- bot_repescagens: +6 campos (cupom_validade, lembrete, canal, email, promocao_id)
"""

from alembic import op
import sqlalchemy as sa

revision = '037_repescagem_verificacao_senha'
down_revision = '036_bot_whatsapp_v2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === CLIENTES: campos verificação email ===
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_verificacao VARCHAR(6)")
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_verificacao_expira TIMESTAMP")
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS verificacao_enviada_em TIMESTAMP")

    # === CLIENTES: campos reset senha ===
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_reset_senha VARCHAR(6)")
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS codigo_reset_expira TIMESTAMP")
    op.execute("ALTER TABLE clientes ADD COLUMN IF NOT EXISTS reset_enviado_em TIMESTAMP")

    # === PROMOCOES: cupom exclusivo por cliente ===
    op.execute("ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS cliente_id INTEGER")
    op.execute("ALTER TABLE promocoes ADD COLUMN IF NOT EXISTS tipo_cupom VARCHAR(20) DEFAULT 'global'")

    # FK promocoes.cliente_id -> clientes.id
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_promocao_cliente') THEN
                ALTER TABLE promocoes ADD CONSTRAINT fk_promocao_cliente
                    FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # Index parcial para cupons exclusivos
    op.execute("CREATE INDEX IF NOT EXISTS idx_promocao_cliente ON promocoes (cliente_id) WHERE cliente_id IS NOT NULL")

    # === BOT_REPESCAGENS: campos avançados ===
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS cupom_validade_dias INTEGER DEFAULT 7")
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS lembrete_enviado BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS lembrete_enviado_em TIMESTAMP")
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS canal VARCHAR(20) DEFAULT 'whatsapp'")
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS email_enviado BOOLEAN DEFAULT FALSE")
    op.execute("ALTER TABLE bot_repescagens ADD COLUMN IF NOT EXISTS promocao_id INTEGER")

    # FK bot_repescagens.promocao_id -> promocoes.id
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_repescagem_promocao') THEN
                ALTER TABLE bot_repescagens ADD CONSTRAINT fk_repescagem_promocao
                    FOREIGN KEY (promocao_id) REFERENCES promocoes(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # bot_repescagens
    op.execute("ALTER TABLE bot_repescagens DROP CONSTRAINT IF EXISTS fk_repescagem_promocao")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS promocao_id")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS email_enviado")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS canal")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS lembrete_enviado_em")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS lembrete_enviado")
    op.execute("ALTER TABLE bot_repescagens DROP COLUMN IF EXISTS cupom_validade_dias")

    # promocoes
    op.execute("DROP INDEX IF EXISTS idx_promocao_cliente")
    op.execute("ALTER TABLE promocoes DROP CONSTRAINT IF EXISTS fk_promocao_cliente")
    op.execute("ALTER TABLE promocoes DROP COLUMN IF EXISTS tipo_cupom")
    op.execute("ALTER TABLE promocoes DROP COLUMN IF EXISTS cliente_id")

    # clientes
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS reset_enviado_em")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS codigo_reset_expira")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS codigo_reset_senha")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS verificacao_enviada_em")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS codigo_verificacao_expira")
    op.execute("ALTER TABLE clientes DROP COLUMN IF EXISTS codigo_verificacao")
