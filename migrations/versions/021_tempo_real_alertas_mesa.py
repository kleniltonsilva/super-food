"""tempo real, alertas atraso, sugestoes tempo, mesa fechada

Revision ID: 021_tempo_real_alertas
Revises: 020_horarios_controle_pedidos
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '021_tempo_real_alertas'
down_revision = '020_horarios_controle_pedidos'
branch_labels = None
depends_on = None


def upgrade():
    # ── Tabela alertas_atraso ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS alertas_atraso (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            tipo_alerta VARCHAR(30) NOT NULL,
            tipo_pedido VARCHAR(20) NOT NULL,
            tempo_estimado_min INTEGER,
            tempo_real_min INTEGER,
            atraso_min INTEGER,
            resolvido BOOLEAN DEFAULT false,
            criado_em TIMESTAMP DEFAULT NOW(),
            resolvido_em TIMESTAMP
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_alerta_atraso_rest_data ON alertas_atraso (restaurante_id, criado_em)")

    # ── Tabela sugestoes_tempo ──
    op.execute("""
        CREATE TABLE IF NOT EXISTS sugestoes_tempo (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            tipo VARCHAR(20) NOT NULL,
            valor_antes INTEGER,
            valor_sugerido INTEGER,
            aceita BOOLEAN,
            motivo TEXT,
            criado_em TIMESTAMP DEFAULT NOW(),
            respondido_em TIMESTAMP
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_sugestao_tempo_rest_data ON sugestoes_tempo (restaurante_id, criado_em)")

    # ── Novos campos em pedidos ──
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'tempo_preparo_real_min'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN tempo_preparo_real_min INTEGER;
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'pedidos' AND column_name = 'mesa_fechada_em'
            ) THEN
                ALTER TABLE pedidos ADD COLUMN mesa_fechada_em TIMESTAMP;
            END IF;
        END $$;
    """)

    # ── Novo campo em notificacoes ──
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'notificacoes' AND column_name = 'dados_json'
            ) THEN
                ALTER TABLE notificacoes ADD COLUMN dados_json JSON;
            END IF;
        END $$;
    """)

    # ── Novo campo em config_restaurante ──
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'tempo_alerta_mesa_min'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN tempo_alerta_mesa_min INTEGER DEFAULT 60;
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS sugestoes_tempo")
    op.execute("DROP TABLE IF EXISTS alertas_atraso")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS tempo_preparo_real_min")
    op.execute("ALTER TABLE pedidos DROP COLUMN IF EXISTS mesa_fechada_em")
    op.execute("ALTER TABLE notificacoes DROP COLUMN IF EXISTS dados_json")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS tempo_alerta_mesa_min")
