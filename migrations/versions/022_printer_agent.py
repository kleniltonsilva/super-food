"""Add printer agent columns: setor_impressao, impressao_automatica, largura_impressao

Revision ID: 022_printer_agent
Revises: 021_tempo_real_alertas
Create Date: 2026-03-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '022_printer_agent'
down_revision = '021_tempo_real_alertas'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # setor_impressao em categorias_menu
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'categorias_menu' AND column_name = 'setor_impressao'
            ) THEN
                ALTER TABLE categorias_menu ADD COLUMN setor_impressao VARCHAR(20) DEFAULT 'geral';
            END IF;
        END $$;
    """)

    # impressao_automatica em config_restaurante
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'impressao_automatica'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN impressao_automatica BOOLEAN DEFAULT false;
            END IF;
        END $$;
    """)

    # largura_impressao em config_restaurante
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'config_restaurante' AND column_name = 'largura_impressao'
            ) THEN
                ALTER TABLE config_restaurante ADD COLUMN largura_impressao INTEGER DEFAULT 80;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE categorias_menu DROP COLUMN IF EXISTS setor_impressao")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS impressao_automatica")
    op.execute("ALTER TABLE config_restaurante DROP COLUMN IF EXISTS largura_impressao")
