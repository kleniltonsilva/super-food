# database/models.py
""" 
Database Models - Derekh Food SaaS
Todos os models com suporte multi-tenant (tenant_id = restaurante_id)
VERSÃO 2.7: Adiciona schema completo do Site do Cliente (4ª cabeça)
"""
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index, JSON, Date, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
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
        """Gera hash SHA256 da senha. Aplica strip() para ignorar espaços acidentais."""
        self.senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()

    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta. Aplica strip() para consistência com set_senha."""
        senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()
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
    cidade = Column(String(100))  # Cidade do restaurante (para filtros de autocomplete)
    estado = Column(String(2))    # UF do estado
    cep = Column(String(10))      # CEP
    latitude = Column(Float)
    longitude = Column(Float)
    # Plano e limites
    plano = Column(String(50), nullable=False, default='basico')
    valor_plano = Column(Float, nullable=False, default=0.0)
    limite_motoboys = Column(Integer, nullable=False, default=3)
    codigo_acesso = Column(String(20), unique=True, nullable=False)
    # Status e datas
    ativo = Column(Boolean, default=True)
    status = Column(String(20), default='ativo')
    criado_em = Column(DateTime, default=datetime.utcnow)
    data_vencimento = Column(DateTime)
    # Relacionamentos
    config = relationship("ConfigRestaurante", back_populates="restaurante", uselist=False, cascade="all, delete-orphan")
    site_config = relationship("SiteConfig", back_populates="restaurante", uselist=False, cascade="all, delete-orphan")
    motoboys = relationship("Motoboy", back_populates="restaurante", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="restaurante", cascade="all, delete-orphan")
    produtos = relationship("Produto", back_populates="restaurante", cascade="all, delete-orphan")
    categorias_menu = relationship("CategoriaMenu", back_populates="restaurante", cascade="all, delete-orphan")
    clientes = relationship("Cliente", back_populates="restaurante", cascade="all, delete-orphan")
    carrinhos = relationship("Carrinho", back_populates="restaurante", cascade="all, delete-orphan")
    caixas = relationship("Caixa", back_populates="restaurante", cascade="all, delete-orphan")
    notificacoes = relationship("Notificacao", back_populates="restaurante", cascade="all, delete-orphan")
    solicitacoes_motoboy = relationship("MotoboySolicitacao", back_populates="restaurante", cascade="all, delete-orphan")
    rotas_otimizadas = relationship("RotaOtimizada", back_populates="restaurante", cascade="all, delete-orphan")
    combos = relationship("Combo", back_populates="restaurante", cascade="all, delete-orphan")
    __table_args__ = (
        Index('idx_restaurante_email', 'email'),
        Index('idx_restaurante_status', 'status', 'ativo'),
    )

    def gerar_codigo_acesso(self):
        """Gera código único de 8 caracteres"""
        self.codigo_acesso = secrets.token_hex(4).upper()

    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha. Aplica strip() para ignorar espaços acidentais."""
        self.senha = hashlib.sha256(senha.strip().encode()).hexdigest()

    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta. Aplica strip() para consistência com set_senha."""
        senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()
        return self.senha == senha_hash

# ==================== SITE CONFIG (NOVO) ====================
class SiteConfig(Base):
    """Configuração do Site do Cliente por restaurante"""
    __tablename__ = "site_config"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), unique=True, nullable=False)
    # Tipo e visual
    tipo_restaurante = Column(String(50), nullable=False, default='geral')
    tema_cor_primaria = Column(String(7), default='#FF6B35')
    tema_cor_secundaria = Column(String(7), default='#004E89')
    logo_url = Column(String(500))
    banner_principal_url = Column(String(500))
    favicon_url = Column(String(500))
    # WhatsApp
    whatsapp_numero = Column(String(20))
    whatsapp_ativo = Column(Boolean, default=True)
    whatsapp_mensagem_padrao = Column(Text, default='Olá! Gostaria de fazer um pedido.')
    # Operacional
    pedido_minimo = Column(Float, default=0.0)
    tempo_entrega_estimado = Column(Integer, default=50)
    tempo_retirada_estimado = Column(Integer, default=20)
    site_ativo = Column(Boolean, default=True)
    aceita_agendamento = Column(Boolean, default=False)
    # Pagamento
    aceita_dinheiro = Column(Boolean, default=True)
    aceita_cartao = Column(Boolean, default=True)
    aceita_pix = Column(Boolean, default=True)
    aceita_vale_refeicao = Column(Boolean, default=False)
    # SEO
    meta_title = Column(String(200))
    meta_description = Column(Text)
    meta_keywords = Column(Text)
    # Pizza — ingredientes adicionais globais [{nome: str, preco: float}, ...]
    ingredientes_adicionais_pizza = Column(JSON, nullable=True)
    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamento
    restaurante = relationship("Restaurante", back_populates="site_config")
    __table_args__ = (
        Index('idx_site_config_restaurante', 'restaurante_id'),
    )

# ==================== CATEGORIAS MENU (NOVO) ====================
class CategoriaMenu(Base):
    """Categorias do cardápio (Pizzas, Bebidas, Sobremesas, etc)"""
    __tablename__ = "categorias_menu"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    icone = Column(String(100))  # emoji ou classe CSS
    imagem_url = Column(String(500))
    ordem_exibicao = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    setor_impressao = Column(String(20), default='geral')  # geral, cozinha, bar, caixa
    criado_em = Column(DateTime, default=datetime.utcnow)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="categorias_menu")
    produtos = relationship("Produto", back_populates="categoria")
    __table_args__ = (
        Index('idx_categoria_restaurante', 'restaurante_id', 'ativo'),
        Index('idx_categoria_ordem', 'restaurante_id', 'ordem_exibicao'),
    )

# ==================== TIPOS PRODUTO (NOVO) ====================
class TipoProduto(Base):
    """Templates de produtos por tipo de restaurante (Pizza, Burger, etc)"""
    __tablename__ = "tipos_produto"
    id = Column(Integer, primary_key=True, index=True)
    tipo_restaurante = Column(String(50), nullable=False)
    nome_template = Column(String(100), nullable=False)
    descricao = Column(Text)
    config_json = Column(JSON, nullable=False)
    ativo = Column(Boolean, default=True)
    # Relacionamentos
    produtos = relationship("Produto", back_populates="tipo_produto")
    __table_args__ = (
        Index('idx_tipo_produto', 'tipo_restaurante', 'ativo'),
    )

# ==================== PRODUTOS (ATUALIZADO) ====================
class Produto(Base):
    """Produtos do cardápio - ATUALIZADO com campos do site"""
    __tablename__ = "produtos"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    categoria_id = Column(Integer, ForeignKey("categorias_menu.id", ondelete="SET NULL"))
    tipo_produto_id = Column(Integer, ForeignKey("tipos_produto.id", ondelete="SET NULL"))
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    preco = Column(Float, nullable=False)
    # Imagens
    imagem_url = Column(String(500))
    imagens_adicionais_json = Column(JSON)  # Array de URLs
    ingredientes_json = Column(JSON)  # ["Calabresa", "Cebola", "Molho de Tomate", "Mussarela"]
    # Destaque e promoção
    destaque = Column(Boolean, default=False)
    promocao = Column(Boolean, default=False)
    preco_promocional = Column(Float)
    ordem_exibicao = Column(Integer, default=0)
    # Estoque
    estoque_ilimitado = Column(Boolean, default=True)
    estoque_quantidade = Column(Integer, default=0)
    disponivel = Column(Boolean, default=True)
    eh_pizza = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="produtos")
    categoria = relationship("CategoriaMenu", back_populates="produtos")
    tipo_produto = relationship("TipoProduto", back_populates="produtos")
    variacoes = relationship("VariacaoProduto", back_populates="produto", cascade="all, delete-orphan")
    itens_pedido = relationship("ItemPedido", back_populates="produto")
    __table_args__ = (
        Index('idx_produto_restaurante', 'restaurante_id', 'disponivel'),
        Index('idx_produto_categoria', 'categoria_id', 'disponivel'),
        Index('idx_produto_destaque', 'restaurante_id', 'destaque'),
    )

# ==================== VARIACOES PRODUTO (NOVO) ====================
class VariacaoProduto(Base):
    """Variações de produto (tamanhos, sabores, bordas, adicionais)"""
    __tablename__ = "variacoes_produto"
    id = Column(Integer, primary_key=True, index=True)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    tipo_variacao = Column(String(50), nullable=False)  # tamanho, sabor, borda, adicional, ponto_carne
    nome = Column(String(100), nullable=False)
    descricao = Column(Text)
    preco_adicional = Column(Float, default=0.0)
    ordem = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    estoque_disponivel = Column(Boolean, default=True)
    max_sabores = Column(Integer, default=1)  # Máximo de sabores (para tipo=tamanho)
    # Relacionamento
    produto = relationship("Produto", back_populates="variacoes")
    __table_args__ = (
        Index('idx_variacao_produto', 'produto_id', 'tipo_variacao', 'ativo'),
    )

# ==================== CLIENTES (NOVO) ====================
class Cliente(Base):
    """Clientes finais do site"""
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    # Dados pessoais
    nome = Column(String(200), nullable=False)
    email = Column(String(100), index=True)
    telefone = Column(String(20), nullable=False)
    senha_hash = Column(String(256), nullable=False)
    # Documentos (opcionais)
    cpf = Column(String(11))
    data_nascimento = Column(Date)
    # Status
    ativo = Column(Boolean, default=True)
    email_verificado = Column(Boolean, default=False)
    telefone_verificado = Column(Boolean, default=False)
    # Timestamps
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    ultimo_acesso = Column(DateTime)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="clientes")
    enderecos = relationship("EnderecoCliente", back_populates="cliente", cascade="all, delete-orphan")
    pedidos = relationship("Pedido", back_populates="cliente")
    carrinhos = relationship("Carrinho", back_populates="cliente", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint('email', 'restaurante_id', name='uq_cliente_email_restaurante'),
        Index('idx_cliente_email', 'email'),
        Index('idx_cliente_restaurante', 'restaurante_id', 'ativo'),
        Index('idx_cliente_telefone', 'restaurante_id', 'telefone'),
    )

    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha. Aplica strip() para ignorar espaços acidentais."""
        self.senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()

    def verificar_senha(self, senha: str) -> bool:
        """Verifica se a senha está correta. Aplica strip() para consistência com set_senha."""
        senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()
        return self.senha_hash == senha_hash

# ==================== ENDERECOS CLIENTE (NOVO) ====================
class EnderecoCliente(Base):
    """Múltiplos endereços por cliente"""
    __tablename__ = "enderecos_cliente"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    apelido = Column(String(50))
    cep = Column(String(8))
    endereco_completo = Column(Text, nullable=False)
    numero = Column(String(10))
    complemento = Column(String(200))
    bairro = Column(String(100))
    cidade = Column(String(100))
    estado = Column(String(2))
    referencia = Column(Text)
    # Coordenadas
    latitude = Column(Float)
    longitude = Column(Float)
    validado_mapbox = Column(Boolean, default=False)
    # Flags
    padrao = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    # Relacionamento
    cliente = relationship("Cliente", back_populates="enderecos")
    __table_args__ = (
        Index('idx_endereco_cliente', 'cliente_id', 'ativo'),
    )

# ==================== CARRINHO (NOVO) ====================
class Carrinho(Base):
    """Carrinho de compras temporário"""
    __tablename__ = "carrinho"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"))
    sessao_id = Column(String(100), index=True)
    # Conteúdo JSON
    itens_json = Column(JSON, nullable=False)
    # Valores
    valor_subtotal = Column(Float, default=0.0)
    valor_taxa_entrega = Column(Float, default=0.0)
    valor_desconto = Column(Float, default=0.0)
    valor_total = Column(Float, default=0.0)
    # Cupom
    cupom_codigo = Column(String(50))
    # Timestamps
    data_criacao = Column(DateTime, default=datetime.utcnow)
    data_atualizacao = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    data_expiracao = Column(DateTime)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="carrinhos")
    cliente = relationship("Cliente", back_populates="carrinhos")
    __table_args__ = (
        Index('idx_carrinho_cliente', 'cliente_id'),
        Index('idx_carrinho_sessao', 'sessao_id'),
        Index('idx_carrinho_expiracao', 'data_expiracao'),
    )

# ==================== CONFIG RESTAURANTE ====================
class ConfigRestaurante(Base):
    """Configurações operacionais do restaurante"""
    __tablename__ = "config_restaurante"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), unique=True, nullable=False)
    status_atual = Column(String(20), default='fechado')
    modo_despacho = Column(String(50), default='auto_economico')
    raio_entrega_km = Column(Float, default=10.0)
    tempo_medio_preparo = Column(Integer, default=30)
    despacho_automatico = Column(Boolean, default=True)

    # Modo de prioridade de entrega (Melhoria v2.8.1)
    # rapido_economico: TSP por proximidade (padrão)
    # cronologico_inteligente: Agrupa por tempo, depois TSP
    # manual: Restaurante atribui manualmente
    modo_prioridade_entrega = Column(String(50), default='rapido_economico')
    # Taxas de entrega (cobradas do cliente)
    taxa_entrega_base = Column(Float, default=5.0)      # Taxa base até distancia_base_km
    distancia_base_km = Column(Float, default=3.0)      # Km incluídos na taxa base
    taxa_km_extra = Column(Float, default=1.5)          # Taxa por km adicional
    valor_km = Column(Float, default=2.0)               # Valor por km (legado)

    # Pagamento do motoboy
    valor_base_motoboy = Column(Float, default=5.0)     # Valor base por entrega
    valor_km_extra_motoboy = Column(Float, default=1.0) # Adicional por km extra
    taxa_diaria = Column(Float, default=0.0)            # Taxa diária (opcional)
    valor_lanche = Column(Float, default=0.0)           # Valor para lanche (opcional)

    # Configurações de rota
    max_pedidos_por_rota = Column(Integer, default=5)   # Máximo de pedidos por rota
    permitir_ver_saldo_motoboy = Column(Boolean, default=True)  # Motoboy pode ver seu saldo

    # Validação antifraude por localização (raio de 50m)
    permitir_finalizar_fora_raio = Column(Boolean, default=False)  # Se True, ranking não é antifraude
    distancia_base_motoboy_km = Column(Float, default=3.0)  # Km incluídos no valor base do motoboy
    # Pedidos do site — aceitar automaticamente após 1º pedido concluído
    aceitar_pedido_site_auto = Column(Boolean, default=False)
    # Tolerância de atraso em minutos (alerta quando entrega ultrapassa estimado + tolerância)
    tolerancia_atraso_min = Column(Integer, default=10)
    # Horários
    horario_abertura = Column(String(5), default='18:00')
    horario_fechamento = Column(String(5), default='23:00')
    dias_semana_abertos = Column(String(200), default='segunda,terca,quarta,quinta,sexta,sabado,domingo')
    # Modo de precificação para pizza com múltiplos sabores
    # "mais_caro" = cobra pelo sabor mais caro | "proporcional" = divide proporcionalmente
    modo_preco_pizza = Column(String(20), default='mais_caro')
    # Horários por dia da semana (JSON string)
    horarios_por_dia = Column(Text, default=None)
    # Controle de pedidos online
    pedidos_online_ativos = Column(Boolean, default=True)
    entregas_ativas = Column(Boolean, default=True)
    controle_pedidos_motivo = Column(String(200), default=None)
    controle_pedidos_ate = Column(DateTime, default=None)
    # Alerta mesa aberta
    tempo_alerta_mesa_min = Column(Integer, default=60)
    # Impressão de comandas
    impressao_automatica = Column(Boolean, default=False)
    largura_impressao = Column(Integer, default=80)  # 58 ou 80mm
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamento
    restaurante = relationship("Restaurante", back_populates="config")
    __table_args__ = (
        Index('idx_config_restaurante', 'restaurante_id'),
    )

# ==================== MOTOBOYS ====================
class Motoboy(Base):
    """Motoboy - Isolado por restaurante com suporte a seleção justa"""
    __tablename__ = "motoboys"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    usuario = Column(String(50), nullable=False)
    telefone = Column(String(20), nullable=False)
    senha = Column(String(256))
    status = Column(String(20), default='pendente')  # pendente, ativo, inativo, excluido
    capacidade_entregas = Column(Integer, default=5)
    ultimo_status_online = Column(DateTime)

    # Identificação (CPF preserva dados ao excluir)
    cpf = Column(String(11))  # CPF opcional - preserva histórico financeiro

    # GPS
    latitude_atual = Column(Float)
    longitude_atual = Column(Float)
    ultima_atualizacao_gps = Column(DateTime)

    # Estatísticas
    total_entregas = Column(Integer, default=0)
    total_ganhos = Column(Float, default=0.0)
    total_km = Column(Float, default=0.0)  # Total de km percorridos

    # Seleção Justa de Entregas
    ordem_hierarquia = Column(Integer, default=0)          # Posição na fila (rotação)
    disponivel = Column(Boolean, default=False)            # Disponível para receber entregas
    em_rota = Column(Boolean, default=False)               # Está em rota ativa
    entregas_pendentes = Column(Integer, default=0)        # Entregas não finalizadas
    ultima_entrega_em = Column(DateTime)                   # Quando finalizou última entrega
    ultima_rota_em = Column(DateTime)                      # Quando recebeu última rota

    # Timestamps
    data_cadastro = Column(DateTime, default=datetime.utcnow)
    data_solicitacao = Column(DateTime, default=datetime.utcnow)
    data_exclusao = Column(DateTime)  # Se excluído, pode reativar em até 30 dias

    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="motoboys")
    entregas = relationship("Entrega", back_populates="motoboy", cascade="all, delete-orphan")
    notificacoes = relationship("Notificacao", back_populates="motoboy", cascade="all, delete-orphan")
    rotas_otimizadas = relationship("RotaOtimizada", back_populates="motoboy", cascade="all, delete-orphan")
    __table_args__ = (
        Index('idx_motoboy_restaurante', 'restaurante_id', 'status'),
        Index('idx_motoboy_usuario', 'restaurante_id', 'usuario'),
        Index('idx_motoboy_disponivel', 'restaurante_id', 'disponivel', 'em_rota'),
        Index('idx_motoboy_hierarquia', 'restaurante_id', 'ordem_hierarquia'),
    )

    def set_senha(self, senha: str):
        """Gera hash SHA256 da senha. Aplica strip() para ignorar espaços acidentais."""
        self.senha = hashlib.sha256(senha.strip().encode()).hexdigest()

    def verificar_senha(self, senha: str) -> bool:
        """Verifica senha. Aplica strip() para consistência com set_senha."""
        if not self.senha:
            return False
        senha_hash = hashlib.sha256(senha.strip().encode()).hexdigest()
        return self.senha == senha_hash

# ==================== SOLICITAÇÕES MOTOBOY ====================
class MotoboySolicitacao(Base):
    """Solicitações de cadastro de motoboys"""
    __tablename__ = "motoboys_solicitacoes"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    usuario = Column(String(50), nullable=False)
    telefone = Column(String(20), nullable=False)
    codigo_acesso = Column(String(20), nullable=False)
    data_solicitacao = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(20), default='pendente', nullable=False)
    # Relacionamento
    restaurante = relationship("Restaurante", back_populates="solicitacoes_motoboy")
    __table_args__ = (
        Index('idx_solicitacao_restaurante_status', 'restaurante_id', 'status'),
        Index('idx_solicitacao_usuario', 'restaurante_id', 'usuario'),
        Index('idx_solicitacao_codigo', 'restaurante_id', 'codigo_acesso'),
    )

# ==================== PEDIDOS (ATUALIZADO) ====================
class Pedido(Base):
    """Pedidos - ATUALIZADO com cliente_id e carrinho_json"""
    __tablename__ = "pedidos"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="SET NULL"))
    comanda = Column(String(50), nullable=False)
    tipo = Column(String(50), nullable=False)
    origem = Column(String(50), default='manual')
    tipo_entrega = Column(String(20))  # entrega, retirada
    # Cliente
    cliente_nome = Column(String(200), nullable=False)
    cliente_telefone = Column(String(20))
    # Endereço
    endereco_entrega = Column(Text)
    latitude_entrega = Column(Float)
    longitude_entrega = Column(Float)
    # Mesa
    numero_mesa = Column(String(20))
    # Itens
    itens = Column(Text, nullable=False)
    carrinho_json = Column(JSON)  # Cópia dos itens do carrinho
    historico_status = Column(JSON)  # [{status, timestamp}, ...] — histórico de mudanças
    observacoes = Column(Text)
    # Valores
    valor_total = Column(Float, nullable=False, default=0.0)
    forma_pagamento = Column(String(50))
    troco_para = Column(Float)
    # Pagamento real (registrado pelo motoboy na entrega)
    forma_pagamento_real = Column(String(50))  # Dinheiro, Cartão/Pix, Misto
    valor_pago_dinheiro = Column(Float, default=0.0)
    valor_pago_cartao = Column(Float, default=0.0)
    cupom_desconto = Column(String(50))
    valor_desconto = Column(Float, default=0.0)
    valor_subtotal = Column(Float, default=0.0)
    valor_taxa_entrega = Column(Float, default=0.0)
    # Rotas
    distancia_restaurante_km = Column(Float)
    ordem_rota = Column(Integer)
    validado_mapbox = Column(Boolean, default=False)
    atrasado = Column(Boolean, default=False)
    # Agendamento
    agendado = Column(Boolean, default=False)
    data_agendamento = Column(DateTime)
    # Status
    status = Column(String(50), default='pendente')
    tempo_estimado = Column(Integer)
    despachado = Column(Boolean, default=False)
    # Tempo real
    tempo_preparo_real_min = Column(Integer)  # Tempo real de preparo calculado
    mesa_fechada_em = Column(DateTime)        # Quando mesa foi paga/fechada
    # Marketplace (iFood, 99Food, Rappi, Keeta)
    marketplace_source = Column(String(30))       # "ifood", "99food", "rappi", "keeta", None
    marketplace_order_id = Column(String(100))    # ID original do marketplace
    marketplace_display_id = Column(String(50))   # ID curto para exibição (ex: "iFood #A1B2")
    marketplace_raw_json = Column(JSON)           # Pedido original completo do marketplace
    # Timestamps
    data_criacao = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="pedidos")
    cliente = relationship("Cliente", back_populates="pedidos")
    itens_detalhados = relationship("ItemPedido", back_populates="pedido", cascade="all, delete-orphan")
    entrega = relationship("Entrega", back_populates="pedido", uselist=False, cascade="all, delete-orphan")
    __table_args__ = (
        Index('idx_pedido_restaurante_status', 'restaurante_id', 'status'),
        Index('idx_pedido_restaurante_data', 'restaurante_id', 'data_criacao'),
        Index('idx_pedido_comanda', 'restaurante_id', 'comanda'),
        Index('idx_pedido_cliente', 'cliente_id'),
        Index('idx_pedido_atrasado', 'restaurante_id', 'atrasado'),
        Index('idx_pedido_marketplace', 'restaurante_id', 'marketplace_source'),
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
    distancia_km = Column(Float)
    tempo_entrega = Column(Integer)
    posicao_rota_original = Column(Integer)
    posicao_rota_otimizada = Column(Integer)
    tempo_preparacao = Column(Integer)
    # Valores cobrados do cliente
    valor_entrega = Column(Float, default=0.0)          # Taxa total cobrada do cliente
    taxa_base = Column(Float, default=0.0)              # Parte base da taxa
    taxa_km_extra = Column(Float, default=0.0)          # Parte extra da taxa

    # Valores pagos ao motoboy
    valor_motoboy = Column(Float, default=0.0)          # Valor pago ao motoboy
    valor_base_motoboy = Column(Float, default=0.0)     # Parte base do pagamento
    valor_extra_motoboy = Column(Float, default=0.0)    # Parte extra do pagamento
    valor_lanche = Column(Float, default=0.0)           # Valor alimentação
    valor_diaria = Column(Float, default=0.0)           # Valor da taxa diária

    # Timestamps de entrega (para ranking)
    delivery_started_at = Column(DateTime)              # Início da entrega
    delivery_finished_at = Column(DateTime)             # Fim da entrega
    finalizado_fora_raio = Column(Boolean, default=False)  # Finalizou fora do raio de 50m

    status = Column(String(50), default='pendente')
    # Motivo de finalização (para entregas canceladas/cliente ausente)
    motivo_finalizacao = Column(String(50))  # 'entregue', 'cliente_ausente', 'cancelado_cliente', 'cancelado_restaurante'
    motivo_cancelamento = Column(Text)  # Detalhes do cancelamento
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

# ==================== ROTAS OTIMIZADAS ====================
class RotaOtimizada(Base):
    """Rotas otimizadas geradas pelo algoritmo TSP"""
    __tablename__ = "rotas_otimizadas"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    motoboy_id = Column(Integer, ForeignKey("motoboys.id", ondelete="CASCADE"), nullable=False)
    total_pedidos = Column(Integer, nullable=False)
    distancia_total_km = Column(Float, nullable=False)
    tempo_total_min = Column(Integer, nullable=False)
    ordem_entregas = Column(JSON, nullable=False)
    status = Column(String(20), default='pendente')
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
    """Controle de caixa diário"""
    __tablename__ = "caixa"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    data_abertura = Column(DateTime, nullable=False)
    operador_abertura = Column(String(100), nullable=False)
    valor_abertura = Column(Float, nullable=False, default=0.0)
    total_vendas = Column(Float, default=0.0)
    valor_retiradas = Column(Float, default=0.0)
    total_dinheiro = Column(Float, default=0.0)
    total_cartao = Column(Float, default=0.0)
    total_pix = Column(Float, default=0.0)
    total_vale = Column(Float, default=0.0)
    status = Column(String(20), default='aberto')
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

# ==================== MOVIMENTAÇÕES CAIXA ====================
class MovimentacaoCaixa(Base):
    """Movimentações detalhadas do caixa"""
    __tablename__ = "movimentacoes_caixa"
    id = Column(Integer, primary_key=True, index=True)
    caixa_id = Column(Integer, ForeignKey("caixa.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(50), nullable=False)
    valor = Column(Float, nullable=False)
    descricao = Column(Text)
    forma_pagamento = Column(String(50))
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"))
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
    tipo = Column(String(50), nullable=False)
    titulo = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    lida = Column(Boolean, default=False)
    dados_json = Column(JSON, nullable=True)  # Dados extras para notificação
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
    __table_args__ = (
        Index('idx_gps_motoboy_timestamp', 'motoboy_id', 'timestamp'),
        Index('idx_gps_restaurante', 'restaurante_id', 'timestamp'),
    )


# ==================== BAIRROS ENTREGA (SITE CLIENTE) ====================
class BairroEntrega(Base):
    """Bairros atendidos pelo restaurante com taxa e tempo de entrega"""
    __tablename__ = "bairros_entrega"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(100), nullable=False)
    taxa_entrega = Column(Float, nullable=False, default=0.0)
    tempo_estimado_min = Column(Integer, nullable=False, default=30)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        Index('idx_bairro_restaurante', 'restaurante_id', 'ativo'),
        Index('idx_bairro_nome', 'restaurante_id', 'nome'),
    )


# ==================== PONTOS FIDELIDADE (SITE CLIENTE) ====================
class PontosFidelidade(Base):
    """Saldo de pontos de fidelidade por cliente"""
    __tablename__ = "pontos_fidelidade"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), unique=True, nullable=False)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    pontos_total = Column(Integer, default=0, nullable=False)
    pontos_disponiveis = Column(Integer, default=0, nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamentos
    cliente = relationship("Cliente")
    __table_args__ = (
        Index('idx_pontos_cliente', 'cliente_id'),
        Index('idx_pontos_restaurante', 'restaurante_id'),
    )


# ==================== TRANSACOES FIDELIDADE (SITE CLIENTE) ====================
class TransacaoFidelidade(Base):
    """Historico de transacoes de pontos (ganhos/resgatados)"""
    __tablename__ = "transacoes_fidelidade"
    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"))
    tipo = Column(String(20), nullable=False)  # 'ganho' ou 'resgatado'
    pontos = Column(Integer, nullable=False)
    descricao = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    # Relacionamentos
    cliente = relationship("Cliente")
    pedido = relationship("Pedido")
    __table_args__ = (
        Index('idx_transacao_cliente', 'cliente_id'),
        Index('idx_transacao_restaurante', 'restaurante_id'),
        Index('idx_transacao_pedido', 'pedido_id'),
    )


# ==================== PREMIOS FIDELIDADE (SITE CLIENTE) ====================
class PremioFidelidade(Base):
    """Premios resgatáveis com pontos de fidelidade"""
    __tablename__ = "premios_fidelidade"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    custo_pontos = Column(Integer, nullable=False)
    tipo_premio = Column(String(50), nullable=False)  # 'desconto', 'item_gratis', 'brinde'
    valor_premio = Column(String(200))  # Valor do desconto ou nome do item
    ordem_exibicao = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        Index('idx_premio_restaurante', 'restaurante_id', 'ativo'),
    )


# ==================== PROMOCOES (SITE CLIENTE) ====================
class Promocao(Base):
    """Promocoes e cupons de desconto"""
    __tablename__ = "promocoes"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    tipo_desconto = Column(String(20), nullable=False)  # 'percentual' ou 'fixo'
    valor_desconto = Column(Float, nullable=False)
    valor_pedido_minimo = Column(Float, default=0.0)
    desconto_maximo = Column(Float)  # Para descontos percentuais
    codigo_cupom = Column(String(50))  # Código para digitar
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    uso_limitado = Column(Boolean, default=False)
    limite_usos = Column(Integer)
    usos_realizados = Column(Integer, default=0)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    __table_args__ = (
        Index('idx_promocao_restaurante', 'restaurante_id', 'ativo'),
        Index('idx_promocao_codigo', 'restaurante_id', 'codigo_cupom'),
        Index('idx_promocao_datas', 'restaurante_id', 'data_inicio', 'data_fim'),
    )


# ==================== COMBOS (NOVO) ====================
class Combo(Base):
    """Combos promocionais do restaurante"""
    __tablename__ = "combos"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    nome = Column(String(200), nullable=False)
    descricao = Column(Text)
    preco_combo = Column(Float, nullable=False)
    preco_original = Column(Float, nullable=False)
    imagem_url = Column(String(500))
    ativo = Column(Boolean, default=True)
    ordem_exibicao = Column(Integer, default=0)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    tipo_combo = Column(String(20), default='padrao')  # padrao | do_dia | kit_festa
    dia_semana = Column(Integer, nullable=True)         # 0=Seg...6=Dom (para do_dia)
    quantidade_pessoas = Column(Integer, nullable=True)  # Para kit_festa (ex: 10, 20, 50)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamentos
    restaurante = relationship("Restaurante", back_populates="combos")
    itens = relationship("ComboItem", back_populates="combo", cascade="all, delete-orphan")
    __table_args__ = (
        Index('idx_combo_restaurante', 'restaurante_id', 'ativo'),
        Index('idx_combo_datas', 'restaurante_id', 'data_inicio', 'data_fim'),
        Index('idx_combo_tipo', 'restaurante_id', 'tipo_combo', 'ativo'),
    )


class ComboItem(Base):
    """Itens que compõem um combo"""
    __tablename__ = "combo_itens"
    id = Column(Integer, primary_key=True, index=True)
    combo_id = Column(Integer, ForeignKey("combos.id", ondelete="CASCADE"), nullable=False)
    produto_id = Column(Integer, ForeignKey("produtos.id", ondelete="CASCADE"), nullable=False)
    quantidade = Column(Integer, nullable=False, default=1)
    # Relacionamentos
    combo = relationship("Combo", back_populates="itens")
    produto = relationship("Produto")
    __table_args__ = (
        Index('idx_combo_item_combo', 'combo_id'),
    )


# ==================== DOMINIOS PERSONALIZADOS ====================
class DominioPersonalizado(Base):
    """Dominio personalizado para restaurante (ex: pedidos.minhapizzaria.com.br)"""
    __tablename__ = "dominios_personalizados"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    dominio = Column(String(255), unique=True, nullable=False)
    tipo = Column(String(20), nullable=False, default='cname')  # cname ou subdomain
    verificado = Column(Boolean, default=False)
    dns_verificado_em = Column(DateTime)
    ssl_ativo = Column(Boolean, default=False)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamentos
    restaurante = relationship("Restaurante", backref="dominios_personalizados")
    __table_args__ = (
        Index('idx_dominio_restaurante', 'restaurante_id'),
        Index('idx_dominio_dominio', 'dominio', unique=True),
    )


# ==================== CREDENCIAIS PLATAFORMA (Super Admin) ====================
class CredencialPlataforma(Base):
    """Credencial da plataforma Derekh Food por marketplace (1 por marketplace, gerenciada pelo Super Admin)"""
    __tablename__ = "credenciais_plataforma"
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(30), unique=True, nullable=False)  # ifood, 99food, rappi, keeta
    client_id = Column(String(200))
    client_secret = Column(String(500))
    ativo = Column(Boolean, default=True)
    config_json = Column(JSON)  # configs extras por marketplace
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ==================== INTEGRAÇÃO MARKETPLACE (por restaurante) ====================
class IntegracaoMarketplace(Base):
    """Autorização de um restaurante em um marketplace (tokens por restaurante, credenciais na plataforma)"""
    __tablename__ = "integracoes_marketplace"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    marketplace = Column(String(30), nullable=False)  # ifood, 99food, rappi, keeta
    ativo = Column(Boolean, default=False)
    # Merchant ID no marketplace
    merchant_id = Column(String(200))
    # Status de autorização
    authorization_status = Column(String(20), default='pending')  # pending, authorized, revoked
    authorized_at = Column(DateTime)
    # Tokens POR RESTAURANTE (renovados automaticamente)
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime)
    # Configurações extras (JSON) — webhook_secret, api_base_url, etc
    config_json = Column(JSON)
    # Timestamps
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relacionamento
    restaurante = relationship("Restaurante")
    __table_args__ = (
        UniqueConstraint('restaurante_id', 'marketplace', name='uq_integracao_marketplace'),
        Index('idx_integracao_restaurante', 'restaurante_id', 'marketplace'),
        Index('idx_integracao_ativo', 'marketplace', 'ativo'),
    )


class MarketplaceEventLog(Base):
    """Log de eventos recebidos dos marketplaces (idempotência + debug)"""
    __tablename__ = "marketplace_event_log"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    marketplace = Column(String(30), nullable=False)
    event_type = Column(String(50), nullable=False)
    event_id = Column(String(200), unique=True, nullable=False)  # ID único do evento no marketplace
    payload_json = Column(JSON)
    processed = Column(Boolean, default=False)
    error_message = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    # Relacionamento
    restaurante = relationship("Restaurante")
    __table_args__ = (
        Index('idx_marketplace_event_id', 'event_id', unique=True),
        Index('idx_marketplace_event_rest', 'restaurante_id', 'marketplace', 'criado_em'),
    )


# ==================== ALERTAS DE ATRASO ====================
class AlertaAtraso(Base):
    """Alertas persistentes de atraso em pedidos"""
    __tablename__ = "alertas_atraso"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    pedido_id = Column(Integer, ForeignKey("pedidos.id", ondelete="SET NULL"))
    tipo_alerta = Column(String(30), nullable=False)  # atraso_entrega, atraso_retirada, atraso_mesa
    tipo_pedido = Column(String(20), nullable=False)   # entrega, retirada, mesa
    tempo_estimado_min = Column(Integer)
    tempo_real_min = Column(Integer)
    atraso_min = Column(Integer)
    resolvido = Column(Boolean, default=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    resolvido_em = Column(DateTime)
    # Relacionamentos
    restaurante = relationship("Restaurante")
    pedido = relationship("Pedido")
    __table_args__ = (
        Index('idx_alerta_atraso_rest_data', 'restaurante_id', 'criado_em'),
    )


# ==================== SUGESTÕES DE TEMPO ====================
class SugestaoTempo(Base):
    """Histórico de sugestões de ajuste de tempo aceitas/rejeitadas"""
    __tablename__ = "sugestoes_tempo"
    id = Column(Integer, primary_key=True, index=True)
    restaurante_id = Column(Integer, ForeignKey("restaurantes.id", ondelete="CASCADE"), nullable=False)
    tipo = Column(String(20), nullable=False)  # entrega, retirada, mesa
    valor_antes = Column(Integer)
    valor_sugerido = Column(Integer)
    aceita = Column(Boolean)
    motivo = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    respondido_em = Column(DateTime)
    # Relacionamentos
    restaurante = relationship("Restaurante")
    __table_args__ = (
        Index('idx_sugestao_tempo_rest_data', 'restaurante_id', 'criado_em'),
    )