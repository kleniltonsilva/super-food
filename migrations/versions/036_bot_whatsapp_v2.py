"""Bot WhatsApp V2: políticas de erro, Google Maps, resolução automática, repescagem inteligente.

Revision ID: 036_bot_whatsapp_v2
Revises: 035_bot_whatsapp
Create Date: 2026-03-26
"""
from alembic import op
import sqlalchemy as sa

revision = '036_bot_whatsapp_v2'
down_revision = '035_bot_whatsapp'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── Novos campos em bot_config ───
    # Nota: usar sa.text() com \\: para escapar ":" antes de dígitos (SQLAlchemy interpreta :0 como bind param)
    op.execute(sa.text(
        'ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS politica_atraso JSON DEFAULT \'{"acao":"desculpar","desconto_pct"\\:0,"mensagem":""}\';'
    ))
    op.execute(sa.text(
        'ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS politica_pedido_errado JSON DEFAULT \'{"acao":"desculpar","desconto_pct"\\:0,"mensagem":""}\';'
    ))
    op.execute(sa.text(
        'ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS politica_item_faltando JSON DEFAULT \'{"acao":"desculpar","desconto_pct"\\:0,"mensagem":""}\';'
    ))
    op.execute(sa.text(
        'ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS politica_qualidade JSON DEFAULT \'{"acao":"desculpar","desconto_pct"\\:0,"mensagem":""}\';'
    ))
    op.execute("""
        ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS google_maps_url VARCHAR(500);
    """)
    op.execute("""
        ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS avaliacao_perguntar_problemas BOOLEAN DEFAULT TRUE;
    """)
    op.execute("""
        ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS avaliacao_pedir_google_review BOOLEAN DEFAULT TRUE;
    """)
    op.execute("""
        ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS repescagem_ultima_execucao TIMESTAMP;
    """)
    op.execute("""
        ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS repescagem_usar_frequencia BOOLEAN DEFAULT TRUE;
    """)

    # Alterar default de delay_avaliacao_min de 10 para 20
    op.execute("""
        ALTER TABLE bot_config ALTER COLUMN delay_avaliacao_min SET DEFAULT 20;
    """)

    # ─── Novos campos em bot_problemas ───
    op.execute("""
        ALTER TABLE bot_problemas ADD COLUMN IF NOT EXISTS resolucao_tipo VARCHAR(30);
    """)
    op.execute("""
        ALTER TABLE bot_problemas ADD COLUMN IF NOT EXISTS cupom_gerado VARCHAR(50);
    """)
    op.execute("""
        ALTER TABLE bot_problemas ADD COLUMN IF NOT EXISTS desconto_pct FLOAT;
    """)
    op.execute("""
        ALTER TABLE bot_problemas ADD COLUMN IF NOT EXISTS resolvido_automaticamente BOOLEAN DEFAULT FALSE;
    """)


def downgrade() -> None:
    # bot_config
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS politica_atraso;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS politica_pedido_errado;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS politica_item_faltando;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS politica_qualidade;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS google_maps_url;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS avaliacao_perguntar_problemas;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS avaliacao_pedir_google_review;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS repescagem_ultima_execucao;")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS repescagem_usar_frequencia;")
    op.execute("ALTER TABLE bot_config ALTER COLUMN delay_avaliacao_min SET DEFAULT 10;")
    # bot_problemas
    op.execute("ALTER TABLE bot_problemas DROP COLUMN IF EXISTS resolucao_tipo;")
    op.execute("ALTER TABLE bot_problemas DROP COLUMN IF EXISTS cupom_gerado;")
    op.execute("ALTER TABLE bot_problemas DROP COLUMN IF EXISTS desconto_pct;")
    op.execute("ALTER TABLE bot_problemas DROP COLUMN IF EXISTS resolvido_automaticamente;")
