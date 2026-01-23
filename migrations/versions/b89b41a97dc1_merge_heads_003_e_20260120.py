# migrations/script.py.mako

"""merge heads 003 e 20260120

Revision ID: b89b41a97dc1
Revises: 003_add_site_cliente_schema, 20260120
Create Date: 2026-01-20 23:48:47.311113

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'b89b41a97dc1'
down_revision = ('003_add_site_cliente_schema', '20260120')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass