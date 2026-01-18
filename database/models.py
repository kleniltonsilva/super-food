# database/models.py

"""
Database Models - Super Food SaaS
Todos os models com suporte multi-tenant (tenant_id = restaurante_id)
ATUALIZAÇÃO: Sistema de Rotas Inteligentes com IA
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text, Index, JSON
)
from sqlalchemy.orm import relationship
from datetime import datetime
import secrets
import hashlib

from .base import Base


# ==================== SUPER ADMIN ====================

class SuperAdmin(Base):
    """Super Admin - Gerencia todos os restaurantes"""
    __tablename__ = "super_admin"
    
    id = Column(Integer, primary_key=True, index=True)
    usuario = Column(String(50), unique=True, nullable=False, index=True)
    senha_hash = Column(String(256), nullable=False)
    email = Column(String(100), unique=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha"""
        self.senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    
    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta"""
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return self.senha_hash == senha_hash


# ==================== RESTAURANTES (TENANTS) ====================

class Restaurante(Base):
    """Restaurante - Tenant principal do sistema SaaS"""
    __tablename__ = "restaurantes"
    
    # Identificação
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(200), nullable=False)
    nome_fantasia = Column(String(200), nullable=False, index=True)
    razao_social = Column(String(200))
    cnpj = Column(String(14), unique=True, index=True)
    
    # Contato
    email = Column(String(100), unique=True, nullable=False, index=True)
    senha = Column(String(256), nullable=False)  # Hash SHA256
    telefone = Column(String(20), nullable=False)
    
    # Localização
    endereco_completo = Column(Text, nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Plano e limites
    plano = Column(String(50), nullable=False, default='basico')  # basico, essencial, avancado, premium
    valor_plano = Column(Float, nullable=False, default=0.0)
    limite_motoboys = Column(Integer, nullable=False, default=3)
    codigo_acesso = Column(String(20), unique=True, nullable=False)  # Para motoboys se cadastrarem
    
    # Status e datas
    ativo = Column(Boolean, default=True)
    status = Column(String(20), default='ativo')  # ativo, suspenso, cancelado
    criado_em = Column(DateTime, default=datetime.utcnow)
    data_vencimento = Column(DateTime)
    
    # Relacionamentos
    config = relationship("ConfigRestaurante", back_populates="restaurante", uselist=False, cascade="all, delete-orphan")
    motoboys = relationship("Motoboy", back_populates="restaurante", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="restaurante", cascade="all, delete-orphan")
    produtos = relationship("Produto", back_populates="restaurante", cascade="all, delete-orphan")
    caixas = relationship("Caixa", back_populates="restaurante", cascade="all, delete-orphan")
    notificacoes = relationship("Notificacao", back_populates="restaurante", cascade="all, delete-orphan")
    solicitacoes_motoboy = relationship("MotoboySolicitacao", back_populates="restaurante", cascade="all, delete-orphan")
    rotas_otimizadas = relationship("RotaOtimizada", back_populates="restaurante", cascade="all, delete-orphan")
    
    # Índices compostos para performance
    __table_args__ = (
        Index('idx_restaurante_email', 'email'),
        Index('idx_restaurante_status', 'status', 'ativo'),
    )
    
    def gerar_codigo_acesso(self):
        """Gera código único de 8 caracteres"""
        self.codigo_acesso = secrets.token_hex(4).upper()
    
    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha"""
        self.senha = hashlib.sha256(senha.encode()).hexdigest()
    
    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta"""
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return self.senha == senha_hash


# ==================== CONFIGURAÇÕES DO RESTAURANTE ====================

class ConfigRestaurante(Base):
    """Configurações operacionais do restaurante"""
    __tablename__ = "config_restaurante"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    # Status operacional
    status_atual = Column(String(20), default='fechado')  # aberto, fechado
    
    # Modo de despacho
    modo_despacho = Column(String(50), default='auto_economico')  # auto_economico, manual, auto_ordem
    
    # ========== NOVOS CAMPOS - ROTAS INTELIGENTES ==========
    raio_entrega_km = Column(Float, default=10.0)  # Raio máximo de entrega (zona de cobertura)
    tempo_medio_preparo = Column(Integer, default=30)  # Tempo médio de preparo em minutos
    despacho_automatico = Column(Boolean, default=True)  # Ativa/desativa despacho automático
    # ======================================================
    
    # Taxas e valores para motoboys
    taxa_diaria = Column(Float, default=50.0)
    valor_lanche = Column(Float, default=15.0)
    taxa_entrega_base = Column(Float, default=5.0)
    distancia_base_km = Column(Float, default=3.0)
    taxa_km_extra = Column(Float, default=1.5)
    valor_km = Column(Float, default=2.0)
    
    # Horários de funcionamento
    horario_abertura = Column(String(5), default='18:00')
    horario_fechamento = Column(String(5), default='23:00')
    dias_semana_abertos = Column(String(200), default='segunda,terca,quarta,quinta,sexta,sabado,domingo')
    
    # Timestamps
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento
    restaurante = relationship("Restaurante", back_populates="config")
    
    __table_args__ = (
        Index('idx_config_restaurante', 'restaurante_id'),
    )


# ==================== MOTOBOYS ====================

class Motoboy(Base):
    """Motoboy - Isolado por restaurante (tenant_id)"""
    __tablename__ = "motoboys"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    # Dados pessoais
    nome = Column(String(100), nullable=False)
    usuario = Column(String(50), nullable=False)
    telefone = Column(String(20), nullable=False)
    senha = Column(String(256))  # Hash SHA256
    
    # Status
    status = Column(String(20), default='pendente')  # pendente, ativo, recusado, inativo
    
    # ========== NOVOS CAMPOS - ROTAS INTELIGENTES ==========
    capacidade_entregas = Column(Integer, default=3)  # Máximo de pedidos por rota
    ultimo_status_online = Column(DateTime)  # Última vez que ficou online/offline
    # ======================================================
    
    # Localização GPS atual
    latitude_atual = Column(Float)
    longitude_atual = Column(Float)
    ultima_atualizacao_gps = Column(DateTime)
    
    # Estatísticas
    total_entregas = Column(Integer, default=0)
    total_ganhos = Column(Float, default=0.0)
    
    # Timestamps
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="motoboys")
    entregas = relationship("Entrega", back_populates="motoboy", cascade="all, delete-orphan")
    notificacoes = relationship("Notificacao", back_populates="motoboy", cascade="all, delete-orphan")
    rotas_otimizadas = relationship("RotaOtimizada", back_populates="motoboy", cascade="all, delete-orphan")
    
    # Índices compostos - CRÍTICO para multi-tenant
    __table_args__ = (
        Index('idx_motoboy_restaurante', 'restaurante_id', 'status'),
        Index('idx_motoboy_usuario', 'restaurante_id', 'usuario'),
    )
    
    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha"""
        self.senha = hashlib.sha256(senha.encode()).hexdigest()
    
    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta"""
        if not self.senha:
            return False
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        return self.senha == senha_hash


# ==================== SOLICITAÇÕES DE MOTOBOY ====================

class MotoboySolicitacao(Base):
    """
    Solicitações de cadastro de motoboys (pendentes de aprovação)
    Usada pelo PWA/app motoboy antes da aprovação pelo restaurante
    """
    __tablename__ = "motoboys_solicitacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    nome = Column(String(100), nullable=False)
    usuario = Column(String(50), nullable=False)
    telefone = Column(String(20), nullable=False)
    codigo_acesso = Column(String(20), nullable=False)  # Código do restaurante informado pelo motoboy
    
    data_solicitacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default='pendente', nullable=False)  # pendente, aprovado, recusado
    
    # Relacionamento
    restaurante = relationship("Restaurante", back_populates="solicitacoes_motoboy")
    
    # Índices multi-tenant e buscas rápidas
    __table_args__ = (
        Index('idx_solicitacao_restaurante_status', 'restaurante_id', 'status'),
        Index('idx_solicitacao_usuario', 'restaurante_id', 'usuario'),
        Index('idx_solicitacao_codigo', 'restaurante_id', 'codigo_acesso'),
    )


# ==================== PRODUTOS ====================

class Produto(Base):
    """Produtos do cardápio - Isolado por restaurante"""
    __tablename__ = "produtos"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    categoria = Column(String(100))
    disponivel = Column(Boolean, default=True)
    
    criado_em = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="produtos")
    itens_pedido = relationship("ItemPedido", back_populates="produto")
    
    __table_args__ = (
        Index('idx_produto_restaurante', 'restaurante_id', 'disponivel'),
    )


# ==================== PEDIDOS ====================

class Pedido(Base):
    """Pedidos - Isolado por restaurante"""
    __tablename__ = "pedidos"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    # Identificação
    comanda = Column(String(50), nullable=False)
    tipo = Column(String(50), nullable=False)  # Entrega, Retirada na loja, Para mesa
    origem = Column(String(50), default='manual')  # manual, ifood, site
    
    # Cliente
    cliente_nome = Column(String(200), nullable=False)
    cliente_telefone = Column(String(20))
    
    # Endereço de entrega (se tipo = Entrega)
    endereco_entrega = Column(Text)
    latitude_entrega = Column(Float)
    longitude_entrega = Column(Float)
    
    # Mesa (se tipo = Para mesa)
    numero_mesa = Column(String(20))
    
    # Itens (texto temporário - usar ItemPedido depois)
    itens = Column(Text, nullable=False)
    observacoes = Column(Text)
    
    # Valores
    valor_total = Column(Float, nullable=False, default=0.0)
    forma_pagamento = Column(String(50))
    troco_para = Column(Float)
    
    # ========== NOVOS CAMPOS - ROTAS INTELIGENTES ==========
    distancia_restaurante_km = Column(Float)  # Distância do restaurante ao cliente
    ordem_rota = Column(Integer)  # Posição na rota do motoboy (1, 2, 3...)
    validado_mapbox = Column(Boolean, default=False)  # Endereço validado pela API Mapbox?
    atrasado = Column(Boolean, default=False)  # Pedido está atrasado?
    # ======================================================
    
    # Status e timing
    status = Column(String(50), default='pendente')  # pendente, em_preparo, pronto, saiu_entrega, entregue, cancelado
    tempo_estimado = Column(Integer)  # em minutos
    despachado = Column(Boolean, default=False)
    
    # Timestamps
    data_criacao = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="pedidos")
    itens_detalhados = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    entrega = relationship("Entrega", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    
    # Índices compostos - CRÍTICO
    __table_args__ = (
        Index('idx_pedido_restaurante_status', 'restaurante_id', 'status'),
        Index('idx_pedido_restaurante_data', 'restaurante_id', 'data_criacao'),
        Index('idx_pedido_comanda', 'restaurante_id', 'comanda'),
        Index('idx_pedido_atrasado', 'restaurante_id', 'atrasado'),  # Novo índice
    )


# ==================== ITENS DO PEDIDO ====================

class ItemPedido(Base):
    """Itens detalhados do pedido"""
    __tablename__ = "itens_pedido"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="SET NULL"))
    
    quantidade = Column(Integer, nullable=False, default=1)
    preco_unitario = Column(Float, nullable=False)
    observacoes = Column(Text)
    
    # Relacionamentos
    pedido = relationship("Pedido", back_populates="itens_detalhados")
    produto = relationship("Produto", back_populates="itens_pedido")
    
    __table_args__ = (
        Index('idx_item_pedido', 'pedido_id'),
    )


# ==================== ENTREGAS ====================

class Entrega(Base):
    """Entregas realizadas por motoboys"""
    __tablename__ = "entregas"
    
    id = Column(Integer, primary_key=True, index=True)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="CASCADE"), unique=True, nullable=False)
    motoboy_id = Column(Integer, ForeignKey("motoboys.id", ondelete="SET NULL"))
    
    # Distância e tempo
    distancia_km = Column(Float)
    tempo_entrega = Column(Integer)  # em minutos
    
    # ========== NOVOS CAMPOS - ROTAS INTELIGENTES ==========
    posicao_rota_original = Column(Integer)  # Ordem cronológica de saída (1, 2, 3...)
    posicao_rota_otimizada = Column(Integer)  # Ordem após otimização TSP (pode ser diferente)
    tempo_preparacao = Column(Integer)  # Minutos de preparo do pedido
    # ======================================================
    
    # Valores calculados
    valor_entrega = Column(Float, default=0.0)
    taxa_base = Column(Float, default=0.0)
    taxa_km_extra = Column(Float, default=0.0)
    
    # Status
    status = Column(String(50), default='pendente')  # pendente, em_rota, entregue, cancelado, recusado, cliente_ausente
    
    # Timestamps
    atribuido_em = Column(DateTime, default=datetime.utcnow)
    entregue_em = Column(DateTime)
    
    # Relacionamentos
    pedido = relationship("Pedido", back_populates="entrega")
    motoboy = relationship("Motoboy", back_populates="entregas")
    
    __table_args__ = (
        Index('idx_entrega_motoboy', 'motoboy_id', 'status'),
        Index('idx_entrega_pedido', 'pedido_id'),
    )


# ==================== NOVA TABELA - ROTAS OTIMIZADAS ====================

class RotaOtimizada(Base):
    """Rotas otimizadas geradas pelo algoritmo TSP"""
    __tablename__ = "rotas_otimizadas"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    motoboy_id = Column(Integer, ForeignKey("motoboys.id", ondelete="CASCADE"), nullable=False)
    
    # Informações da rota
    total_pedidos = Column(Integer, nullable=False)
    distancia_total_km = Column(Float, nullable=False)
    tempo_total_min = Column(Integer, nullable=False)
    
    # Ordem dos pedidos (JSON: [pedido_id1, pedido_id2, pedido_id3...])
    ordem_entregas = Column(JSON, nullable=False)  # Ex: [45, 23, 67, 12]
    
    # Status
    status = Column(String(20), default='pendente')  # pendente, iniciada, concluida, cancelada
    
    # Timestamps
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_inicio = Column(DateTime)
    data_conclusao = Column(DateTime)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="rotas_otimizadas")
    motoboy = relationship("Motoboy", back_populates="rotas_otimizadas")
    
    __table_args__ = (
        Index('idx_rota_restaurante', 'restaurante_id', 'status'),
        Index('idx_rota_motoboy', 'motoboy_id', 'status'),
    )


# ==================== CAIXA ====================

class Caixa(Base):
    """Controle de caixa diário do restaurante"""
    __tablename__ = "caixa"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    # Abertura
    data_abertura = Column(DateTime, nullable=False)
    operador_abertura = Column(String(100), nullable=False)
    valor_abertura = Column(Float, nullable=False, default=0.0)
    
    # Movimentações
    total_vendas = Column(Float, default=0.0)
    valor_retiradas = Column(Float, default=0.0)
    
    # Fechamento
    status = Column(String(20), default='aberto')  # aberto, fechado
    data_fechamento = Column(DateTime)
    operador_fechamento = Column(String(100))
    valor_contado = Column(Float)
    diferenca = Column(Float)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="caixas")
    movimentacoes = relationship("MovimentacaoCaixa", back_populates="caixa", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_caixa_restaurante_status', 'restaurante_id', 'status'),
        Index('idx_caixa_restaurante_data', 'restaurante_id', 'data_abertura'),
    )


# ==================== MOVIMENTAÇÕES DO CAIXA ====================

class MovimentacaoCaixa(Base):
    """Movimentações detalhadas do caixa"""
    __tablename__ = "movimentacoes_caixa"
    
    id = Column(Integer, primary_key=True, index=True)
    caixa_id = Column(Integer, ForeignKey("caixa.id", ondelete="CASCADE"), nullable=False)
    
    tipo = Column(String(50), nullable=False)  # abertura, venda, retirada, fechamento
    valor = Column(Float, nullable=False)
    descricao = Column(Text)
    data_hora = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamento
    caixa = relationship("Caixa", back_populates="movimentacoes")
    
    __table_args__ = (
        Index('idx_movimentacao_caixa', 'caixa_id', 'tipo'),
    )


# ==================== NOTIFICAÇÕES ====================

class Notificacao(Base):
    """Notificações para restaurantes e motoboys"""
    __tablename__ = "notificacoes"
    
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"))
    motoboy_id = Column(Integer, ForeignKey("motoboys.id", ondelete="CASCADE"))
    
    tipo = Column(String(50), nullable=False)  # aprovacao, pedido, pagamento, alerta_capacidade, etc
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    
    lida = Column(Boolean, default=False)
    data_criacao = Column(DateTime, default=datetime.utcnow)
    
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="notificacoes")
    motoboy = relationship("Motoboy", back_populates="notificacoes")
    
    __table_args__ = (
        Index('idx_notificacao_restaurante', 'restaurante_id', 'lida'),
        Index('idx_notificacao_motoboy', 'motoboy_id', 'lida'),
    )


# ==================== GPS MOTOBOYS ====================

class GPSMotoboy(Base):
    """Histórico de localização GPS dos motoboys"""
    __tablename__ = "gps_motoboys"
    
    id = Column(Integer, primary_key=True, index=True)
    motoboy_id = Column(Integer, ForeignKey("motoboys.id", ondelete="CASCADE"), nullable=False)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    velocidade = Column(Float, default=0.0)
    
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relacionamentos
    motoboy = relationship("Motoboy")
    restaurante = relationship("Restaurante")
    
    # Índices para queries rápidas
    __table_args__ = (
        Index('idx_gps_motoboy_timestamp', 'motoboy_id', 'timestamp'),
        Index('idx_gps_restaurante', 'restaurante_id', 'timestamp'),
    )