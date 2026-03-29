"""Solicitação de cadastro — landing page onboarding self-service

Revision ID: 042_solicitacao_cadastro
Revises: 041_addon_bot_whatsapp
Create Date: 2026-03-29
"""

from alembic import op
import sqlalchemy as sa

revision = "042_solicitacao_cadastro"
down_revision = "041_addon_bot_whatsapp"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_cadastro (
            id SERIAL PRIMARY KEY,
            nome_fantasia VARCHAR(200) NOT NULL,
            nome_responsavel VARCHAR(200) NOT NULL,
            email VARCHAR(200) NOT NULL,
            telefone VARCHAR(20) NOT NULL,
            cnpj VARCHAR(20),
            cidade VARCHAR(100),
            estado VARCHAR(5),
            tipo_restaurante VARCHAR(50) DEFAULT 'geral',
            mensagem TEXT,
            status VARCHAR(30) DEFAULT 'pendente',
            motivo_rejeicao TEXT,
            restaurante_id INTEGER REFERENCES restaurantes(id) ON DELETE SET NULL,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW(),
            ip_origem VARCHAR(50)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_solicitacao_status ON solicitacoes_cadastro (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_solicitacao_email ON solicitacoes_cadastro (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_solicitacao_criado ON solicitacoes_cadastro (criado_em DESC)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS solicitacoes_cadastro")
