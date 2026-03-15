"""horarios por dia da semana + controle pedidos online

Revision ID: 019_horarios_controle_pedidos
Revises: 018_dominios_personalizados
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '019_horarios_controle_pedidos'
down_revision = '018_dominios_personalizados'
branch_labels = None
depends_on = None


def upgrade():
    # Horários por dia da semana (JSON string)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'horarios_por_dia'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN horarios_por_dia TEXT;
            END IF;
        END $$;
    """)

    # Pedidos online ativos (boolean, default true)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'pedidos_online_ativos'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN pedidos_online_ativos BOOLEAN DEFAULT true;
            END IF;
        END $$;
    """)

    # Entregas ativas (boolean, default true)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'entregas_ativas'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN entregas_ativas BOOLEAN DEFAULT true;
            END IF;
        END $$;
    """)

    # Motivo do controle de pedidos
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'controle_pedidos_motivo'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN controle_pedidos_motivo VARCHAR(200);
            END IF;
        END $$;
    """)

    # Data/hora até quando fica desativado
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'controle_pedidos_ate'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN controle_pedidos_ate TIMESTAMP;
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS horarios_por_dia")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS pedidos_online_ativos")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS entregas_ativas")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS controle_pedidos_motivo")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS controle_pedidos_ate")
