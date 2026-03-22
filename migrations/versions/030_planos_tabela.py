"""Tabela planos — preços editáveis pelo Super Admin

Revision ID: 030_planos_tabela
Revises: 029_kds_cozinha
Create Date: 2026-03-21
"""
from alembic import op
import sqlalchemy as sa

revision = '030_planos_tabela'
down_revision = '029_kds_cozinha'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Criar tabela planos
    op.execute("""
        CREATE TABLE IF NOT EXISTS planos (
            id SERIAL PRIMARY KEY,
            nome VARCHAR(50) UNIQUE NOT NULL,
            valor DOUBLE PRECISION NOT NULL,
            limite_motoboys INTEGER DEFAULT 2,
            descricao VARCHAR(200),
            destaque BOOLEAN DEFAULT false,
            ordem INTEGER DEFAULT 0,
            ativo BOOLEAN DEFAULT true,
            criado_em TIMESTAMP DEFAULT NOW(),
            atualizado_em TIMESTAMP DEFAULT NOW()
        )
    """)

    # Seed com os 4 planos padrão
    op.execute("""
        INSERT INTO planos (nome, valor, limite_motoboys, descricao, destaque, ordem)
        VALUES
            ('Básico', 169.90, 2, 'Ideal para começar', false, 1),
            ('Essencial', 279.90, 5, 'Para restaurantes em crescimento', false, 2),
            ('Avançado', 329.90, 10, 'Para operações maiores', true, 3),
            ('Premium', 527.00, 999, 'Sem limites', false, 4)
        ON CONFLICT (nome) DO UPDATE SET
            valor = EXCLUDED.valor,
            limite_motoboys = EXCLUDED.limite_motoboys,
            descricao = EXCLUDED.descricao,
            destaque = EXCLUDED.destaque,
            ordem = EXCLUDED.ordem
    """)

    # Atualizar restaurantes existentes com os novos valores
    op.execute("UPDATE restaurantes SET valor_plano = 169.90 WHERE plano = 'Básico'")
    op.execute("UPDATE restaurantes SET valor_plano = 279.90 WHERE plano = 'Essencial'")
    op.execute("UPDATE restaurantes SET valor_plano = 329.90 WHERE plano = 'Avançado'")
    op.execute("UPDATE restaurantes SET valor_plano = 527.00 WHERE plano = 'Premium'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS planos")
