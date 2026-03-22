"""
032 — App Garçom: tabelas garcons, garcom_mesas, config_garcom, sessoes_mesa, sessao_pedidos, itens_esgotados
+ colunas novas em pedidos (course, tipo_origem, label_origem)

Revision ID: 032_garcom
Revises: 031_kds_pausa
"""
from alembic import op
import sqlalchemy as sa

revision = '032_garcom'
down_revision = '031_kds_pausa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tabela garcons ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS garcons (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            nome VARCHAR(100) NOT NULL,
            login VARCHAR(50) NOT NULL,
            senha_hash VARCHAR(256) NOT NULL,
            secao_inicio INTEGER,
            secao_fim INTEGER,
            modo_secao VARCHAR(20) DEFAULT 'FAIXA',
            avatar_emoji VARCHAR(10),
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_garcom_login_restaurante') THEN
                ALTER TABLE garcons ADD CONSTRAINT uq_garcom_login_restaurante UNIQUE (restaurante_id, login);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_garcom_restaurante ON garcons (restaurante_id, ativo)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_garcom_login ON garcons (restaurante_id, login)")

    # ── Tabela garcom_mesas ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS garcom_mesas (
            id SERIAL PRIMARY KEY,
            garcom_id INTEGER NOT NULL REFERENCES garcons(id) ON DELETE CASCADE,
            mesa_id INTEGER NOT NULL
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_garcom_mesa') THEN
                ALTER TABLE garcom_mesas ADD CONSTRAINT uq_garcom_mesa UNIQUE (garcom_id, mesa_id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_garcom_mesa_garcom ON garcom_mesas (garcom_id)")

    # ── Tabela config_garcom ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS config_garcom (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            garcom_ativo BOOLEAN DEFAULT FALSE,
            taxa_servico FLOAT DEFAULT 0.10,
            pct_taxa BOOLEAN DEFAULT TRUE,
            couvert_auto BOOLEAN DEFAULT FALSE,
            item_couvert_id INTEGER,
            campos_obrigatorios JSON,
            permitir_cancelamento BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_config_garcom_restaurante') THEN
                ALTER TABLE config_garcom ADD CONSTRAINT uq_config_garcom_restaurante UNIQUE (restaurante_id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_config_garcom_restaurante ON config_garcom (restaurante_id)")

    # ── Tabela sessoes_mesa ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessoes_mesa (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            mesa_id INTEGER NOT NULL,
            garcom_id INTEGER REFERENCES garcons(id) ON DELETE SET NULL,
            status VARCHAR(20) DEFAULT 'ABERTA',
            qtd_pessoas INTEGER DEFAULT 1,
            alergia TEXT,
            tags JSON,
            notas TEXT,
            subtotal FLOAT DEFAULT 0,
            taxa FLOAT DEFAULT 0,
            total FLOAT DEFAULT 0,
            criado_em TIMESTAMP DEFAULT NOW(),
            fechado_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessao_mesa_restaurante ON sessoes_mesa (restaurante_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessao_mesa_mesa ON sessoes_mesa (restaurante_id, mesa_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessao_mesa_garcom ON sessoes_mesa (garcom_id)")

    # ── Tabela sessao_pedidos ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS sessao_pedidos (
            id SERIAL PRIMARY KEY,
            sessao_id INTEGER NOT NULL REFERENCES sessoes_mesa(id) ON DELETE CASCADE,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE
        )
    """)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_sessao_pedido') THEN
                ALTER TABLE sessao_pedidos ADD CONSTRAINT uq_sessao_pedido UNIQUE (sessao_id, pedido_id);
            END IF;
        END $$;
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessao_pedido_sessao ON sessao_pedidos (sessao_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_sessao_pedido_pedido ON sessao_pedidos (pedido_id)")

    # ── Tabela itens_esgotados ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS itens_esgotados (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            item_cardapio_id INTEGER NOT NULL,
            reportado_por INTEGER REFERENCES garcons(id) ON DELETE SET NULL,
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_itens_esgotados_restaurante ON itens_esgotados (restaurante_id, ativo)")

    # ── Colunas novas em pedidos ──
    op.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS course VARCHAR(20)")
    op.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS tipo_origem VARCHAR(20)")
    op.execute("ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS label_origem VARCHAR(100)")


def downgrade() -> None:
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS label_origem")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS tipo_origem")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS course")
    op.execute("DROP TABLE IF EXISTS itens_esgotados")
    op.execute("DROP TABLE IF EXISTS sessao_pedidos")
    op.execute("DROP TABLE IF EXISTS sessoes_mesa")
    op.execute("DROP TABLE IF EXISTS config_garcom")
    op.execute("DROP TABLE IF EXISTS garcom_mesas")
    op.execute("DROP TABLE IF EXISTS garcons")
