"""Campos Meta Cloud API no bot_config — provider meta/evolution

Revision ID: 045_bot_meta_provider
Revises: 044_bot_meta_gateway
Create Date: 2026-03-31
"""

from alembic import op
import sqlalchemy as sa

revision = "045_bot_meta_provider"
down_revision = "044_bot_meta_gateway"
branch_labels = None
depends_on = None


def upgrade():
    # whatsapp_provider: 'meta' ou 'evolution' (default evolution — restaurantes existentes não quebram)
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS whatsapp_provider VARCHAR(20) DEFAULT 'evolution'")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS meta_phone_number_id VARCHAR(100)")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS meta_access_token TEXT")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS meta_waba_id VARCHAR(100)")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS meta_app_secret VARCHAR(200)")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS meta_webhook_verify_token VARCHAR(100)")

    # Index para lookup por meta_phone_number_id (webhook Meta identifica restaurante por este campo)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_config_meta_phone ON bot_config (meta_phone_number_id)")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_bot_config_meta_phone")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS meta_webhook_verify_token")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS meta_app_secret")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS meta_waba_id")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS meta_access_token")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS meta_phone_number_id")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS whatsapp_provider")
