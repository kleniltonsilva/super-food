"""Adicionar payment_link_url em pix_cobrancas

Revision ID: 040_pix_payment_link
Revises: 039_fix_promocoes_remaining_cols
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa

revision = '040_pix_payment_link'
down_revision = '039_fix_promocoes_remaining_cols'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE pix_cobrancas ADD COLUMN IF NOT EXISTS payment_link_url TEXT")


def downgrade():
    op.execute("ALTER TABLE pix_cobrancas DROP COLUMN IF EXISTS payment_link_url")
