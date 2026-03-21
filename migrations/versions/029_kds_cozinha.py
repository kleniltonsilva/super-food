"""KDS Cozinha - Kitchen Display System

Revision ID: 029_kds_cozinha
Revises: 028_pix_woovi
Create Date: 2026-03-21

- Cria tabela cozinheiros (login cozinheiro no KDS)
- Cria tabela cozinheiro_produtos (vinculo cozinheiro <-> produtos que prepara)
- Cria tabela pedidos_cozinha (pedidos vistos no KDS)
- Cria tabela config_cozinha (configuracao KDS por restaurante)
"""
from alembic import op
import sqlalchemy as sa

revision = '029_kds_cozinha'
down_revision = '028_pix_woovi'
branch_labels = None
depends_on = None


def upgrade():
    # --- cozinheiros ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cozinheiros (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            nome VARCHAR(100) NOT NULL,
            login VARCHAR(50) NOT NULL,
            senha_hash VARCHAR(256) NOT NULL,
            modo VARCHAR(20) NOT NULL DEFAULT 'todos',
            avatar_emoji VARCHAR(10),
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cozinheiro_restaurante ON cozinheiros (restaurante_id, ativo)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cozinheiro_login ON cozinheiros (restaurante_id, login)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cozinheiro_login_restaurante') THEN
                ALTER TABLE cozinheiros ADD CONSTRAINT uq_cozinheiro_login_restaurante UNIQUE (restaurante_id, login);
            END IF;
        END $$;
    """)

    # --- cozinheiro_produtos ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cozinheiro_produtos (
            id SERIAL PRIMARY KEY,
            cozinheiro_id INTEGER NOT NULL REFERENCES cozinheiros(id) ON DELETE CASCADE,
            produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_cozinheiro_produto_cozinheiro ON cozinheiro_produtos (cozinheiro_id)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cozinheiro_produto') THEN
                ALTER TABLE cozinheiro_produtos ADD CONSTRAINT uq_cozinheiro_produto UNIQUE (cozinheiro_id, produto_id);
            END IF;
        END $$;
    """)

    # --- pedidos_cozinha ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS pedidos_cozinha (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            pedido_id INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
            status VARCHAR(20) NOT NULL DEFAULT 'NOVO',
            cozinheiro_id INTEGER REFERENCES cozinheiros(id) ON DELETE SET NULL,
            urgente BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT NOW(),
            iniciado_em TIMESTAMP,
            feito_em TIMESTAMP,
            pronto_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_pedido_cozinha_restaurante ON pedidos_cozinha (restaurante_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pedido_cozinha_pedido ON pedidos_cozinha (pedido_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_pedido_cozinha_cozinheiro ON pedidos_cozinha (cozinheiro_id)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_pedido_cozinha_pedido') THEN
                ALTER TABLE pedidos_cozinha ADD CONSTRAINT uq_pedido_cozinha_pedido UNIQUE (pedido_id);
            END IF;
        END $$;
    """)

    # --- config_cozinha ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS config_cozinha (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            kds_ativo BOOLEAN DEFAULT FALSE,
            tempo_alerta_min INTEGER DEFAULT 15,
            tempo_critico_min INTEGER DEFAULT 25,
            som_novo_pedido BOOLEAN DEFAULT TRUE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_config_cozinha_restaurante ON config_cozinha (restaurante_id)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_config_cozinha_restaurante') THEN
                ALTER TABLE config_cozinha ADD CONSTRAINT uq_config_cozinha_restaurante UNIQUE (restaurante_id);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS config_cozinha CASCADE")
    op.execute("DROP TABLE IF EXISTS pedidos_cozinha CASCADE")
    op.execute("DROP TABLE IF EXISTS cozinheiro_produtos CASCADE")
    op.execute("DROP TABLE IF EXISTS cozinheiros CASCADE")
