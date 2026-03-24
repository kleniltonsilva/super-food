"""
033 — Bridge Printer: tabelas bridge_patterns e bridge_intercepted_orders
Permite ao Bridge Agent interceptar impressões de plataformas externas e criar pedidos.

Revision ID: 033_bridge_printer
Revises: 032_garcom
"""
from alembic import op
import sqlalchemy as sa

revision = '033_bridge_printer'
down_revision = '032_garcom'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Tabela bridge_patterns ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS bridge_patterns (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            plataforma VARCHAR(50) NOT NULL,
            nome_pattern VARCHAR(100),
            regex_detectar TEXT NOT NULL,
            mapeamento_json JSON NOT NULL,
            confianca FLOAT DEFAULT 0.5,
            usos INTEGER DEFAULT 0,
            validado BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bridge_patterns_restaurante ON bridge_patterns (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bridge_patterns_plataforma ON bridge_patterns (restaurante_id, plataforma)")

    # ── Tabela bridge_intercepted_orders ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS bridge_intercepted_orders (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            impressora_origem VARCHAR(200),
            plataforma_detectada VARCHAR(50),
            texto_bruto TEXT NOT NULL,
            dados_parseados JSON,
            pattern_id INTEGER REFERENCES bridge_patterns(id) ON DELETE SET NULL,
            pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            status VARCHAR(30) DEFAULT 'pendente',
            erro_mensagem TEXT,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bridge_orders_restaurante ON bridge_intercepted_orders (restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bridge_orders_status ON bridge_intercepted_orders (restaurante_id, status)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS bridge_intercepted_orders")
    op.execute("DROP TABLE IF EXISTS bridge_patterns")
