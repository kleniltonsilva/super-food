"""Feature flags por plano — plano_tier, features_override, features_json

Revision ID: 034_feature_flags
Revises: 033_bridge_printer
Create Date: 2026-03-24
"""
from alembic import op
import sqlalchemy as sa

revision = '034_feature_flags'
down_revision = '033_bridge_printer'
branch_labels = None
depends_on = None


def upgrade():
    # === Restaurantes: plano_tier + features_override ===
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'restaurantes' AND column_name = 'plano_tier'
            ) THEN
                ALTER TABLE restaurantes ADD COLUMN plano_tier INTEGER DEFAULT 1;
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'restaurantes' AND column_name = 'features_override'
            ) THEN
                ALTER TABLE restaurantes ADD COLUMN features_override TEXT DEFAULT NULL;
            END IF;
        END $$;
    """)

    # === Planos: features_json ===
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'planos' AND column_name = 'features_json'
            ) THEN
                ALTER TABLE planos ADD COLUMN features_json TEXT DEFAULT NULL;
            END IF;
        END $$;
    """)

    # === Backfill plano_tier baseado no plano atual ===
    op.execute("UPDATE restaurantes SET plano_tier = 1 WHERE plano_tier IS NULL AND (LOWER(plano) = 'basico' OR LOWER(plano) = 'básico')")
    op.execute("UPDATE restaurantes SET plano_tier = 2 WHERE LOWER(plano) = 'essencial'")
    op.execute("UPDATE restaurantes SET plano_tier = 3 WHERE LOWER(plano) IN ('avancado', 'avançado')")
    op.execute("UPDATE restaurantes SET plano_tier = 4 WHERE LOWER(plano) = 'premium'")
    # Default: qualquer plano não reconhecido → tier 1
    op.execute("UPDATE restaurantes SET plano_tier = 1 WHERE plano_tier IS NULL")

    # === Backfill features_json nos planos ===
    op.execute("""
        UPDATE planos SET features_json = '["site_cardapio","pedidos","dashboard","caixa","bairros_taxas","motoboys","configuracoes","relatorios_basicos"]'
        WHERE LOWER(nome) IN ('basico', 'básico')
    """)
    op.execute("""
        UPDATE planos SET features_json = '["site_cardapio","pedidos","dashboard","caixa","bairros_taxas","motoboys","configuracoes","relatorios_basicos","cupons_promocoes","fidelidade","combos","relatorios_avancados","operadores_caixa","kds_cozinha"]'
        WHERE LOWER(nome) = 'essencial'
    """)
    op.execute("""
        UPDATE planos SET features_json = '["site_cardapio","pedidos","dashboard","caixa","bairros_taxas","motoboys","configuracoes","relatorios_basicos","cupons_promocoes","fidelidade","combos","relatorios_avancados","operadores_caixa","kds_cozinha","app_garcom","integracoes_marketplace","pix_online","dominio_personalizado","analytics_avancado"]'
        WHERE LOWER(nome) IN ('avancado', 'avançado')
    """)
    op.execute("""
        UPDATE planos SET features_json = '["site_cardapio","pedidos","dashboard","caixa","bairros_taxas","motoboys","configuracoes","relatorios_basicos","cupons_promocoes","fidelidade","combos","relatorios_avancados","operadores_caixa","kds_cozinha","app_garcom","integracoes_marketplace","pix_online","dominio_personalizado","analytics_avancado","bridge_printer","bot_whatsapp","suporte_dedicado"]'
        WHERE LOWER(nome) = 'premium'
    """)

    # === Index ===
    op.execute("CREATE INDEX IF NOT EXISTS idx_restaurante_plano_tier ON restaurantes (plano_tier)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_restaurante_plano_tier")
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'restaurantes' AND column_name = 'plano_tier'
            ) THEN
                ALTER TABLE restaurantes DROP COLUMN plano_tier;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'restaurantes' AND column_name = 'features_override'
            ) THEN
                ALTER TABLE restaurantes DROP COLUMN features_override;
            END IF;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'planos' AND column_name = 'features_json'
            ) THEN
                ALTER TABLE planos DROP COLUMN features_json;
            END IF;
        END $$;
    """)
