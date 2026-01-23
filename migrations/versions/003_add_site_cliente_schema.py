"""add site cliente schema

Revision ID: 003_add_site_cliente_schema
Revises: 002_add_gps_motoboys_table
Create Date: 2026-01-18 14:00:00.000000

Adiciona schema completo para Site do Cliente (4ª cabeça do Super Food)
- site_config: Configuração visual/operacional do site por restaurante
- categorias_menu: Categorias do cardápio (Pizzas, Bebidas, etc)
- tipos_produto: Templates de produtos por tipo de restaurante
- variacoes_produto: Tamanhos, sabores, bordas, adicionais
- clientes: Cadastro de clientes finais
- enderecos_cliente: Múltiplos endereços por cliente
- carrinho: Carrinho de compras temporário
- Atualiza produtos: adiciona categoria_id, imagem, destaque, promoção
- Atualiza pedidos: adiciona cliente_id, carrinho_json, cupom_desconto
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision = '003_add_site_cliente_schema'
down_revision = '002_add_gps_motoboys_table'
branch_labels = None
depends_on = None


def upgrade():
    """Cria schema completo do Site do Cliente"""
    
    # ==================== SITE_CONFIG ====================
    op.create_table('site_config',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete='CASCADE'), unique=True, nullable=False),
        
        # Tipo e visual
        sa.Column('tipo_restaurante', sa.String(50), nullable=False, server_default='geral'),  # pizza, burger, japones, etc
        sa.Column('tema_cor_primaria', sa.String(7), server_default='#FF6B35'),
        sa.Column('tema_cor_secundaria', sa.String(7), server_default='#004E89'),
        sa.Column('logo_url', sa.String(500)),
        sa.Column('banner_principal_url', sa.String(500)),
        sa.Column('favicon_url', sa.String(500)),
        
        # WhatsApp
        sa.Column('whatsapp_numero', sa.String(20)),
        sa.Column('whatsapp_ativo', sa.Boolean(), server_default=sa.true()),
        sa.Column('whatsapp_mensagem_padrao', sa.Text(), server_default='Olá! Gostaria de fazer um pedido.'),
        
        # Operacional
        sa.Column('pedido_minimo', sa.Float(), server_default='0.0'),
        sa.Column('tempo_entrega_estimado', sa.Integer(), server_default='50'),  # minutos
        sa.Column('tempo_retirada_estimado', sa.Integer(), server_default='20'),  # minutos
        sa.Column('site_ativo', sa.Boolean(), server_default=sa.true()),
        sa.Column('aceita_agendamento', sa.Boolean(), server_default=sa.false()),
        
        # Pagamento
        sa.Column('aceita_dinheiro', sa.Boolean(), server_default=sa.true()),
        sa.Column('aceita_cartao', sa.Boolean(), server_default=sa.true()),
        sa.Column('aceita_pix', sa.Boolean(), server_default=sa.true()),
        sa.Column('aceita_vale_refeicao', sa.Boolean(), server_default=sa.false()),
        
        # SEO
        sa.Column('meta_title', sa.String(200)),
        sa.Column('meta_description', sa.Text()),
        sa.Column('meta_keywords', sa.Text()),
        
        # Timestamps
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.Index('idx_site_config_restaurante', 'restaurante_id')
    )
    
    # ==================== CATEGORIAS_MENU ====================
    op.create_table('categorias_menu',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('icone', sa.String(100)),  # emoji ou classe CSS
        sa.Column('imagem_url', sa.String(500)),
        sa.Column('ordem_exibicao', sa.Integer(), server_default='0'),
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
        
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        
        sa.Index('idx_categoria_restaurante', 'restaurante_id', 'ativo'),
        sa.Index('idx_categoria_ordem', 'restaurante_id', 'ordem_exibicao')
    )
    
    # ==================== TIPOS_PRODUTO ====================
    op.create_table('tipos_produto',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        
        sa.Column('tipo_restaurante', sa.String(50), nullable=False),  # pizza, burger, etc
        sa.Column('nome_template', sa.String(100), nullable=False),
        sa.Column('descricao', sa.Text()),
        
        # Configuração JSON
        sa.Column('config_json', sa.JSON(), nullable=False),
        # Ex: {"permite_tamanhos": true, "tamanhos_padrao": ["Broto", "Grande"], "permite_sabores": true, "max_sabores": 4}
        
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
        
        sa.Index('idx_tipo_produto', 'tipo_restaurante', 'ativo')
    )
    
    # ==================== VARIACOES_PRODUTO ====================
    op.create_table('variacoes_produto',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('produto_id', sa.Integer(), sa.ForeignKey('produtos.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('tipo_variacao', sa.String(50), nullable=False),  # tamanho, sabor, borda, adicional, ponto_carne
        sa.Column('nome', sa.String(100), nullable=False),
        sa.Column('descricao', sa.Text()),
        sa.Column('preco_adicional', sa.Float(), server_default='0.0'),
        sa.Column('ordem', sa.Integer(), server_default='0'),
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
        sa.Column('estoque_disponivel', sa.Boolean(), server_default=sa.true()),
        
        sa.Index('idx_variacao_produto', 'produto_id', 'tipo_variacao', 'ativo')
    )
    
    # ==================== CLIENTES ====================
    op.create_table('clientes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete='CASCADE'), nullable=False),
        
        # Dados pessoais
        sa.Column('nome', sa.String(200), nullable=False),
        sa.Column('email', sa.String(100), unique=True, index=True),
        sa.Column('telefone', sa.String(20), nullable=False),
        sa.Column('senha_hash', sa.String(256), nullable=False),
        
        # Documentos (opcionais)
        sa.Column('cpf', sa.String(11)),
        sa.Column('data_nascimento', sa.Date()),
        
        # Status
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
        sa.Column('email_verificado', sa.Boolean(), server_default=sa.false()),
        sa.Column('telefone_verificado', sa.Boolean(), server_default=sa.false()),
        
        # Timestamps
        sa.Column('data_cadastro', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('ultimo_acesso', sa.DateTime()),
        
        sa.Index('idx_cliente_email', 'email'),
        sa.Index('idx_cliente_restaurante', 'restaurante_id', 'ativo'),
        sa.Index('idx_cliente_telefone', 'restaurante_id', 'telefone')
    )
    
    # ==================== ENDERECOS_CLIENTE ====================
    op.create_table('enderecos_cliente',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE'), nullable=False),
        
        sa.Column('apelido', sa.String(50)),  # Casa, Trabalho, etc
        sa.Column('cep', sa.String(8)),
        sa.Column('endereco_completo', sa.Text(), nullable=False),
        sa.Column('numero', sa.String(10)),
        sa.Column('complemento', sa.String(200)),
        sa.Column('bairro', sa.String(100)),
        sa.Column('cidade', sa.String(100)),
        sa.Column('estado', sa.String(2)),
        sa.Column('referencia', sa.Text()),
        
        # Coordenadas (Mapbox)
        sa.Column('latitude', sa.Float()),
        sa.Column('longitude', sa.Float()),
        sa.Column('validado_mapbox', sa.Boolean(), server_default=sa.false()),
        
        # Flags
        sa.Column('padrao', sa.Boolean(), server_default=sa.false()),
        sa.Column('ativo', sa.Boolean(), server_default=sa.true()),
        
        sa.Column('criado_em', sa.DateTime(), server_default=sa.func.now()),
        
        sa.Index('idx_endereco_cliente', 'cliente_id', 'ativo')
    )
    
    # ==================== CARRINHO ====================
    op.create_table('carrinho',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('restaurante_id', sa.Integer(), sa.ForeignKey('restaurantes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('cliente_id', sa.Integer(), sa.ForeignKey('clientes.id', ondelete='CASCADE')),
        sa.Column('sessao_id', sa.String(100), index=True),  # Para não-logados
        
        # Conteúdo
        sa.Column('itens_json', sa.JSON(), nullable=False),
        # Ex: [{"produto_id": 1, "nome": "Pizza Grande", "variacoes": [...], "quantidade": 1, "preco_unitario": 45.0, "subtotal": 45.0}]
        
        sa.Column('valor_subtotal', sa.Float(), server_default='0.0'),
        sa.Column('valor_taxa_entrega', sa.Float(), server_default='0.0'),
        sa.Column('valor_desconto', sa.Float(), server_default='0.0'),
        sa.Column('valor_total', sa.Float(), server_default='0.0'),
        
        # Cupom
        sa.Column('cupom_codigo', sa.String(50)),
        
        # Timestamps
        sa.Column('data_criacao', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('data_atualizacao', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('data_expiracao', sa.DateTime()),  # TTL de 24h
        
        sa.Index('idx_carrinho_cliente', 'cliente_id'),
        sa.Index('idx_carrinho_sessao', 'sessao_id'),
        sa.Index('idx_carrinho_expiracao', 'data_expiracao')
    )
    
    # ==================== ATUALIZAR PRODUTOS ====================
    with op.batch_alter_table('produtos') as batch_op:
        batch_op.add_column(sa.Column('categoria_id', sa.Integer()))
        batch_op.add_column(sa.Column('tipo_produto_id', sa.Integer()))
        batch_op.add_column(sa.Column('imagem_url', sa.String(500)))
        batch_op.add_column(sa.Column('imagens_adicionais_json', sa.JSON()))
        batch_op.add_column(sa.Column('destaque', sa.Boolean(), server_default=sa.false()))
        batch_op.add_column(sa.Column('promocao', sa.Boolean(), server_default=sa.false()))
        batch_op.add_column(sa.Column('preco_promocional', sa.Float()))
        batch_op.add_column(sa.Column('ordem_exibicao', sa.Integer(), server_default='0'))
        batch_op.add_column(sa.Column('estoque_ilimitado', sa.Boolean(), server_default=sa.true()))
        batch_op.add_column(sa.Column('estoque_quantidade', sa.Integer(), server_default='0'))
        batch_op.create_index('idx_produto_categoria', ['categoria_id', 'disponivel'])
        batch_op.create_index('idx_produto_destaque', ['restaurante_id', 'destaque'])
        batch_op.create_foreign_key('fk_produtos_categoria_id', 'categorias_menu', ['categoria_id'], ['id'], ondelete='SET NULL')
        batch_op.create_foreign_key('fk_produtos_tipo_produto_id', 'tipos_produto', ['tipo_produto_id'], ['id'], ondelete='SET NULL')
    
    # ==================== ATUALIZAR PEDIDOS ====================
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.add_column(sa.Column('cliente_id', sa.Integer()))
        batch_op.add_column(sa.Column('carrinho_json', sa.JSON()))
        batch_op.add_column(sa.Column('cupom_desconto', sa.String(50)))
        batch_op.add_column(sa.Column('valor_desconto', sa.Float(), server_default='0.0'))
        batch_op.add_column(sa.Column('tipo_entrega', sa.String(20)))
        batch_op.add_column(sa.Column('agendado', sa.Boolean(), server_default=sa.false()))
        batch_op.add_column(sa.Column('data_agendamento', sa.DateTime()))
        batch_op.create_index('idx_pedido_cliente', ['cliente_id'])
        batch_op.create_foreign_key('fk_pedidos_cliente_id', 'clientes', ['cliente_id'], ['id'], ondelete='SET NULL')


def downgrade():
    """Remove schema do Site do Cliente"""
    
    # Remove índices e colunas de pedidos
    with op.batch_alter_table('pedidos') as batch_op:
        batch_op.drop_constraint('fk_pedidos_cliente_id', type_='foreignkey')
        batch_op.drop_index('idx_pedido_cliente')
        batch_op.drop_column('data_agendamento')
        batch_op.drop_column('agendado')
        batch_op.drop_column('tipo_entrega')
        batch_op.drop_column('valor_desconto')
        batch_op.drop_column('cupom_desconto')
        batch_op.drop_column('carrinho_json')
        batch_op.drop_column('cliente_id')
    
    # Remove índices e colunas de produtos
    with op.batch_alter_table('produtos') as batch_op:
        batch_op.drop_constraint('fk_produtos_tipo_produto_id', type_='foreignkey')
        batch_op.drop_constraint('fk_produtos_categoria_id', type_='foreignkey')
        batch_op.drop_index('idx_produto_destaque')
        batch_op.drop_index('idx_produto_categoria')
        batch_op.drop_column('estoque_quantidade')
        batch_op.drop_column('estoque_ilimitado')
        batch_op.drop_column('ordem_exibicao')
        batch_op.drop_column('preco_promocional')
        batch_op.drop_column('promocao')
        batch_op.drop_column('destaque')
        batch_op.drop_column('imagens_adicionais_json')
        batch_op.drop_column('imagem_url')
        batch_op.drop_column('tipo_produto_id')
        batch_op.drop_column('categoria_id')
    
    # Remove tabelas
    op.drop_table('carrinho')
    op.drop_table('enderecos_cliente')
    op.drop_table('clientes')
    op.drop_table('variacoes_produto')
    op.drop_table('tipos_produto')
    op.drop_table('categorias_menu')
    op.drop_table('site_config')