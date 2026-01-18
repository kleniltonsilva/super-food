"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-01-17 12:00:00.000000

Schema completo do Super Food v2.1 com Rotas Inteligentes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Cria todas as tabelas do sistema"""
    
    # ==================== SUPER ADMIN ====================
    op.create_table('super_admin',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario', sa.String(length=50), nullable=False),
        sa.Column('senha_hash', sa.String(length=256), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('ativo', sa.Boolean(), nullable=True, default=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_super_admin_usuario', 'super_admin', ['usuario'], unique=True)
    
    # ==================== RESTAURANTES ====================
    op.create_table('restaurantes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('nome_fantasia', sa.String(length=200), nullable=False),
        sa.Column('razao_social', sa.String(length=200), nullable=True),
        sa.Column('cnpj', sa.String(length=14), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('senha', sa.String(length=256), nullable=False),
        sa.Column('telefone', sa.String(length=20), nullable=False),
        sa.Column('endereco_completo', sa.Text(), nullable=False),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('plano', sa.String(length=50), nullable=False, default='basico'),
        sa.Column('valor_plano', sa.Float(), nullable=False, default=0.0),
        sa.Column('limite_motoboys', sa.Integer(), nullable=False, default=3),
        sa.Column('codigo_acesso', sa.String(length=20), nullable=False),
        sa.Column('ativo', sa.Boolean(), nullable=True, default=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='ativo'),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.Column('data_vencimento', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_restaurantes_email', 'restaurantes', ['email'], unique=True)
    op.create_index('ix_restaurantes_cnpj', 'restaurantes', ['cnpj'], unique=True)
    op.create_index('ix_restaurantes_codigo_acesso', 'restaurantes', ['codigo_acesso'], unique=True)
    
    # ==================== CONFIG RESTAURANTE ====================
    op.create_table('config_restaurante',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('status_atual', sa.String(length=20), nullable=True, default='fechado'),
        sa.Column('modo_despacho', sa.String(length=50), nullable=True, default='auto_economico'),
        sa.Column('raio_entrega_km', sa.Float(), nullable=True, default=10.0),
        sa.Column('tempo_medio_preparo', sa.Integer(), nullable=True, default=30),
        sa.Column('despacho_automatico', sa.Boolean(), nullable=True, default=True),
        sa.Column('taxa_diaria', sa.Float(), nullable=True, default=50.0),
        sa.Column('valor_lanche', sa.Float(), nullable=True, default=15.0),
        sa.Column('taxa_entrega_base', sa.Float(), nullable=True, default=5.0),
        sa.Column('distancia_base_km', sa.Float(), nullable=True, default=3.0),
        sa.Column('taxa_km_extra', sa.Float(), nullable=True, default=1.5),
        sa.Column('valor_km', sa.Float(), nullable=True, default=2.0),
        sa.Column('horario_abertura', sa.String(length=5), nullable=True, default='18:00'),
        sa.Column('horario_fechamento', sa.String(length=5), nullable=True, default='23:00'),
        sa.Column('dias_semana_abertos', sa.String(length=200), nullable=True, default='segunda,terca,quarta,quinta,sexta,sabado,domingo'),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_config_restaurante_restaurante_id', 'config_restaurante', ['restaurante_id'], unique=True)
    
    # ==================== MOTOBOYS ====================
    op.create_table('motoboys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('usuario', sa.String(length=50), nullable=False),
        sa.Column('telefone', sa.String(length=20), nullable=False),
        sa.Column('senha', sa.String(length=256), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='pendente'),
        sa.Column('capacidade_entregas', sa.Integer(), nullable=True, default=3),
        sa.Column('ultimo_status_online', sa.DateTime(), nullable=True),
        sa.Column('latitude_atual', sa.Float(), nullable=True),
        sa.Column('longitude_atual', sa.Float(), nullable=True),
        sa.Column('ultima_atualizacao_gps', sa.DateTime(), nullable=True),
        sa.Column('total_entregas', sa.Integer(), nullable=True, default=0),
        sa.Column('total_ganhos', sa.Float(), nullable=True, default=0.0),
        sa.Column('data_cadastro', sa.DateTime(), nullable=True),
        sa.Column('data_solicitacao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_motoboys_restaurante_usuario', 'motoboys', ['restaurante_id', 'usuario'])
    
    # ==================== SOLICITAÇÕES MOTOBOY ====================
    op.create_table('motoboys_solicitacoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('usuario', sa.String(length=50), nullable=False),
        sa.Column('telefone', sa.String(length=20), nullable=False),
        sa.Column('codigo_acesso', sa.String(length=20), nullable=False),
        sa.Column('data_solicitacao', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='pendente'),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== PRODUTOS ====================
    op.create_table('produtos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=200), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('preco', sa.Float(), nullable=False),
        sa.Column('categoria', sa.String(length=100), nullable=True),
        sa.Column('disponivel', sa.Boolean(), nullable=True, default=True),
        sa.Column('criado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== PEDIDOS ====================
    op.create_table('pedidos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('comanda', sa.String(length=50), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('origem', sa.String(length=50), nullable=True, default='manual'),
        sa.Column('cliente_nome', sa.String(length=200), nullable=False),
        sa.Column('cliente_telefone', sa.String(length=20), nullable=True),
        sa.Column('endereco_entrega', sa.Text(), nullable=True),
        sa.Column('latitude_entrega', sa.Float(), nullable=True),
        sa.Column('longitude_entrega', sa.Float(), nullable=True),
        sa.Column('numero_mesa', sa.String(length=20), nullable=True),
        sa.Column('itens', sa.Text(), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('valor_total', sa.Float(), nullable=False, default=0.0),
        sa.Column('forma_pagamento', sa.String(length=50), nullable=True),
        sa.Column('troco_para', sa.Float(), nullable=True),
        sa.Column('distancia_restaurante_km', sa.Float(), nullable=True),
        sa.Column('ordem_rota', sa.Integer(), nullable=True),
        sa.Column('validado_mapbox', sa.Boolean(), nullable=True, default=False),
        sa.Column('atrasado', sa.Boolean(), nullable=True, default=False),
        sa.Column('status', sa.String(length=50), nullable=True, default='pendente'),
        sa.Column('tempo_estimado', sa.Integer(), nullable=True),
        sa.Column('despachado', sa.Boolean(), nullable=True, default=False),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.Column('atualizado_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pedidos_restaurante_status', 'pedidos', ['restaurante_id', 'status'])
    
    # ==================== ITENS PEDIDO ====================
    op.create_table('itens_pedido',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pedido_id', sa.Integer(), nullable=False),
        sa.Column('produto_id', sa.Integer(), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False, default=1),
        sa.Column('preco_unitario', sa.Float(), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== ENTREGAS ====================
    op.create_table('entregas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pedido_id', sa.Integer(), nullable=False),
        sa.Column('motoboy_id', sa.Integer(), nullable=True),
        sa.Column('distancia_km', sa.Float(), nullable=True),
        sa.Column('tempo_entrega', sa.Integer(), nullable=True),
        sa.Column('posicao_rota_original', sa.Integer(), nullable=True),
        sa.Column('posicao_rota_otimizada', sa.Integer(), nullable=True),
        sa.Column('tempo_preparacao', sa.Integer(), nullable=True),
        sa.Column('valor_entrega', sa.Float(), nullable=True, default=0.0),
        sa.Column('taxa_base', sa.Float(), nullable=True, default=0.0),
        sa.Column('taxa_km_extra', sa.Float(), nullable=True, default=0.0),
        sa.Column('status', sa.String(length=50), nullable=True, default='pendente'),
        sa.Column('atribuido_em', sa.DateTime(), nullable=True),
        sa.Column('entregue_em', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['motoboy_id'], ['motoboys.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_entregas_pedido_id', 'entregas', ['pedido_id'], unique=True)
    
    # ==================== ROTAS OTIMIZADAS ====================
    op.create_table('rotas_otimizadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('motoboy_id', sa.Integer(), nullable=False),
        sa.Column('total_pedidos', sa.Integer(), nullable=False),
        sa.Column('distancia_total_km', sa.Float(), nullable=False),
        sa.Column('tempo_total_min', sa.Integer(), nullable=False),
        sa.Column('ordem_entregas', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, default='pendente'),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.Column('data_inicio', sa.DateTime(), nullable=True),
        sa.Column('data_conclusao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['motoboy_id'], ['motoboys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== CAIXA ====================
    op.create_table('caixa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=False),
        sa.Column('data_abertura', sa.DateTime(), nullable=False),
        sa.Column('operador_abertura', sa.String(length=100), nullable=False),
        sa.Column('valor_abertura', sa.Float(), nullable=False, default=0.0),
        sa.Column('total_vendas', sa.Float(), nullable=True, default=0.0),
        sa.Column('valor_retiradas', sa.Float(), nullable=True, default=0.0),
        sa.Column('status', sa.String(length=20), nullable=True, default='aberto'),
        sa.Column('data_fechamento', sa.DateTime(), nullable=True),
        sa.Column('operador_fechamento', sa.String(length=100), nullable=True),
        sa.Column('valor_contado', sa.Float(), nullable=True),
        sa.Column('diferenca', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== MOVIMENTAÇÕES CAIXA ====================
    op.create_table('movimentacoes_caixa',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('caixa_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('valor', sa.Float(), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('data_hora', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['caixa_id'], ['caixa.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # ==================== NOTIFICAÇÕES ====================
    op.create_table('notificacoes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('restaurante_id', sa.Integer(), nullable=True),
        sa.Column('motoboy_id', sa.Integer(), nullable=True),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('lida', sa.Boolean(), nullable=True, default=False),
        sa.Column('data_criacao', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['motoboy_id'], ['motoboys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['restaurante_id'], ['restaurantes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    """Remove todas as tabelas"""
    op.drop_table('notificacoes')
    op.drop_table('movimentacoes_caixa')
    op.drop_table('caixa')
    op.drop_table('rotas_otimizadas')
    op.drop_table('entregas')
    op.drop_table('itens_pedido')
    op.drop_table('pedidos')
    op.drop_table('produtos')
    op.drop_table('motoboys_solicitacoes')
    op.drop_table('motoboys')
    op.drop_table('config_restaurante')
    op.drop_table('restaurantes')
    op.drop_table('super_admin')