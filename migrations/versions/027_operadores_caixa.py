"""Operadores de caixa por restaurante

Revision ID: 027_operadores_caixa
Revises: 026_billing_asaas
Create Date: 2026-03-18

- Cria tabela operadores_caixa (nome, senha_hash, ativo, por restaurante)
- Index composto restaurante_id + ativo
- Unique constraint restaurante_id + nome
"""
from alembic import op
import sqlalchemy as sa

revision = '027_operadores_caixa'
down_revision = '026_billing_asaas'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS operadores_caixa (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            nome VARCHAR(100) NOT NULL,
            senha_hash VARCHAR(256) NOT NULL,
            ativo BOOLEAN DEFAULT TRUE,
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_operador_caixa_restaurante ON operadores_caixa (restaurante_id, ativo)")
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_operador_nome_restaurante') THEN
                ALTER TABLE operadores_caixa ADD CONSTRAINT uq_operador_nome_restaurante UNIQUE (restaurante_id, nome);
            END IF;
        END $$;
    """)


def downgrade():
    op.execute("DROP TABLE IF EXISTS operadores_caixa")
