"""add eh_pizza to produtos + fix cliente email unique constraint

Revision ID: 017_eh_pizza_email
Revises: 016_add_ingredientes_adicionais_pizza
Create Date: 2026-03-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '017_eh_pizza_email'
down_revision = '016_add_ingredientes_adicionais_pizza'
branch_labels = None
depends_on = None


def upgrade():
    # 1. Adicionar coluna eh_pizza ao produtos
    op.add_column('produtos', sa.Column('eh_pizza', sa.Boolean(), server_default=sa.text('false'), nullable=True))

    # 2. Fix constraint email cliente: remover unique global, adicionar unique por restaurante
    # Usar SQL puro com IF EXISTS — try/except NÃO funciona em PostgreSQL
    # (quando um statement falha, toda a transação é abortada)
    op.execute("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS uq_clientes_email")
    op.execute("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS clientes_email_key")
    op.execute("DROP INDEX IF EXISTS ix_clientes_email")

    # Recriar índice não-único + constraint único composto (email por restaurante)
    op.execute("CREATE INDEX IF NOT EXISTS ix_clientes_email ON clientes (email)")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_cliente_email_restaurante'
            ) THEN
                ALTER TABLE clientes ADD CONSTRAINT uq_cliente_email_restaurante UNIQUE (email, restaurante_id);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("ALTER TABLE clientes DROP CONSTRAINT IF EXISTS uq_cliente_email_restaurante")
    op.drop_column('produtos', 'eh_pizza')
