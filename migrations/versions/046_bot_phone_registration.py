"""Campos de registro self-service de telefone no bot_config

Revision ID: 046_bot_phone_registration
Revises: 045_bot_meta_provider
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa

revision = "046_bot_phone_registration"
down_revision = "045_bot_meta_provider"
branch_labels = None
depends_on = None


def upgrade():
    # Estado da máquina de registro: none → pending_code → verified → registered → active
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_registration_status VARCHAR(30) DEFAULT 'none'")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_display_name VARCHAR(200)")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_about TEXT")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_description TEXT")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_profile_photo_url VARCHAR(500)")
    op.execute("ALTER TABLE bot_config ADD COLUMN IF NOT EXISTS phone_registered_at TIMESTAMP")


def downgrade():
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_registered_at")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_profile_photo_url")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_description")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_about")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_display_name")
    op.execute("ALTER TABLE bot_config DROP COLUMN IF EXISTS phone_registration_status")
