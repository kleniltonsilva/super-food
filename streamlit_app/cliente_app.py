# streamlit_app/cliente_app.py

"""
cliente_app.py - Site de Pedidos Online para Clientes
4ª Cabeça do Super Food SaaS

Funcionalidades:
- Acesso via slug único do restaurante (?restaurante=slug)
- Visualização do cardápio por categoria
- Carrinho de compras persistente na sessão
- Autocomplete de endereço com validação de zona de cobertura
- Cálculo de taxa de entrega em tempo real
- Checkout com forma de pagamento
- Acompanhamento do pedido em tempo real
"""

import streamlit as st
import sys
import os
from datetime import datetime
from typing import Optional, Dict, List

# Adicionar pasta raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar session e models do banco SQLAlchemy
from database.session import get_db_session
from database.models import (
    Restaurante, CategoriaMenu, Produto, Pedido, ItemPedido,
    ConfigRestaurante, Entrega, SiteConfig
)

# Imports para cálculos
from utils.calculos import calcular_taxa_entrega
from utils.mapbox_api import (
    autocomplete_endereco_restaurante,
    geocode_address,
    check_coverage_zone
)

# Configuração da página
st.set_page_config(
    page_title="Pedido Online - Super Food",
    page_icon="🍔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS customizado para visual atrativo
st.markdown("""
<style>
    /* Reset e base */
    .main {
        padding: 0 !important;
    }

    /* Header do restaurante */
    .restaurant-header {
        background: linear-gradient(135deg, #FF6B35, #F7931E);
        padding: 20px;
        border-radius: 0 0 20px 20px;
        text-align: center;
        color: white;
        margin-bottom: 20px;
    }

    .restaurant-header h1 {
        margin: 0;
        font-size: 28px;
    }

    .restaurant-header p {
        margin: 5px 0 0;
        opacity: 0.9;
    }

    /* Cards de produto */
    .product-card {
        background: white;
        border-radius: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        padding: 15px;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }

    .product-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 15px rgba(0,0,0,0.15);
    }

    .product-name {
        font-size: 18px;
        font-weight: bold;
        color: #333;
        margin-bottom: 5px;
    }

    .product-description {
        font-size: 14px;
        color: #666;
        margin-bottom: 10px;
    }

    .product-price {
        font-size: 20px;
        font-weight: bold;
        color: #00AA00;
    }

    /* Carrinho flutuante */
    .cart-badge {
        position: fixed;
        bottom: 80px;
        right: 20px;
        background: #FF6B35;
        color: white;
        border-radius: 50%;
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        box-shadow: 0 4px 15px rgba(255,107,53,0.4);
        z-index: 1000;
        cursor: pointer;
    }

    /* Categoria */
    .category-title {
        background: linear-gradient(90deg, #FF6B35, transparent);
        padding: 10px 20px;
        border-radius: 10px;
        color: white;
        font-size: 18px;
        font-weight: bold;
        margin: 20px 0 10px;
    }

    /* Botões */
    .stButton button {
        border-radius: 10px;
    }

    /* Resumo do pedido */
    .order-summary {
        background: #f8f9fa;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
    }

    /* Status do pedido */
    .status-badge {
        padding: 8px 16px;
        border-radius: 20px;
        font-weight: bold;
        text-align: center;
    }

    .status-pending { background: #FFF3CD; color: #856404; }
    .status-preparing { background: #CCE5FF; color: #004085; }
    .status-ready { background: #D4EDDA; color: #155724; }
    .status-delivering { background: #D1ECF1; color: #0C5460; }
    .status-delivered { background: #D4EDDA; color: #155724; }
</style>
""", unsafe_allow_html=True)


# ==================== FUNÇÕES DE SESSÃO ====================

def init_session_state():
    """Inicializa variáveis de sessão"""
    if 'carrinho' not in st.session_state:
        st.session_state.carrinho = []
    if 'restaurante_id' not in st.session_state:
        st.session_state.restaurante_id = None
    if 'restaurante_dados' not in st.session_state:
        st.session_state.restaurante_dados = None
    if 'tela_atual' not in st.session_state:
        st.session_state.tela_atual = 'cardapio'
    if 'pedido_finalizado_id' not in st.session_state:
        st.session_state.pedido_finalizado_id = None
    if 'endereco_cliente' not in st.session_state:
        st.session_state.endereco_cliente = {}
    if 'taxa_entrega' not in st.session_state:
        st.session_state.taxa_entrega = 0.0


def carregar_restaurante(codigo_ou_id):
    """Carrega dados do restaurante pelo codigo_acesso ou ID"""
    session = get_db_session()
    try:
        # Tenta primeiro como ID numérico
        if str(codigo_ou_id).isdigit():
            restaurante = session.query(Restaurante).filter(
                Restaurante.id == int(codigo_ou_id),
                Restaurante.ativo == True
            ).first()
        else:
            # Tenta como codigo_acesso
            restaurante = session.query(Restaurante).filter(
                Restaurante.codigo_acesso == codigo_ou_id,
                Restaurante.ativo == True
            ).first()

        if restaurante:
            # Carregar config operacional
            config = session.query(ConfigRestaurante).filter(
                ConfigRestaurante.restaurante_id == restaurante.id
            ).first()

            # Carregar config do site (onde está pedido_minimo)
            site_config = session.query(SiteConfig).filter(
                SiteConfig.restaurante_id == restaurante.id
            ).first()

            st.session_state.restaurante_id = restaurante.id
            st.session_state.restaurante_dados = {
                'id': restaurante.id,
                'nome': restaurante.nome_fantasia,
                'endereco': restaurante.endereco_completo,
                'latitude': restaurante.latitude,
                'longitude': restaurante.longitude,
                'telefone': restaurante.telefone,
                'cidade': restaurante.cidade,
                'estado': restaurante.estado,
                'logo': getattr(restaurante, 'logo_url', None),
                'config': {
                    'raio_entrega_km': config.raio_entrega_km if config else 15.0,
                    'taxa_base': config.taxa_entrega_base if config else 5.0,
                    'distancia_base_km': config.distancia_base_km if config else 3.0,
                    'taxa_km_extra': config.taxa_km_extra if config else 1.5,
                    'pedido_minimo': site_config.pedido_minimo if site_config else 20.0,
                } if config else None
            }
            return True
        return False
    finally:
        session.close()


# ==================== CARRINHO ====================

def adicionar_ao_carrinho(produto_id: int, quantidade: int = 1, observacao: str = ""):
    """Adiciona produto ao carrinho"""
    session = get_db_session()
    try:
        produto = session.query(Produto).filter(Produto.id == produto_id).first()
        if not produto:
            return False

        # Verificar se já existe no carrinho
        for item in st.session_state.carrinho:
            if item['produto_id'] == produto_id and item.get('observacao', '') == observacao:
                item['quantidade'] += quantidade
                return True

        # Adicionar novo item
        st.session_state.carrinho.append({
            'produto_id': produto_id,
            'nome': produto.nome,
            'preco': float(produto.preco),
            'quantidade': quantidade,
            'observacao': observacao
        })
        return True
    finally:
        session.close()


def remover_do_carrinho(index: int):
    """Remove item do carrinho pelo índice"""
    if 0 <= index < len(st.session_state.carrinho):
        st.session_state.carrinho.pop(index)


def calcular_total_carrinho() -> float:
    """Calcula total do carrinho"""
    return sum(item['preco'] * item['quantidade'] for item in st.session_state.carrinho)


def quantidade_itens_carrinho() -> int:
    """Retorna quantidade total de itens no carrinho"""
    return sum(item['quantidade'] for item in st.session_state.carrinho)


# ==================== TELAS ====================

def tela_cardapio():
    """Exibe o cardápio do restaurante"""
    rest = st.session_state.restaurante_dados

    # Header do restaurante
    st.markdown(f"""
    <div class="restaurant-header">
        <h1>🍽️ {rest['nome']}</h1>
        <p>📍 {rest['endereco']}</p>
    </div>
    """, unsafe_allow_html=True)

    # Mostrar carrinho se tiver itens
    qtd_carrinho = quantidade_itens_carrinho()
    if qtd_carrinho > 0:
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button(f"🛒 Carrinho ({qtd_carrinho})", type="primary", use_container_width=True):
                st.session_state.tela_atual = 'carrinho'
                st.rerun()

    # Buscar categorias e produtos
    session = get_db_session()
    try:
        categorias = session.query(CategoriaMenu).filter(
            CategoriaMenu.restaurante_id == st.session_state.restaurante_id,
            CategoriaMenu.ativo == True
        ).order_by(CategoriaMenu.ordem_exibicao).all()

        if not categorias:
            st.info("📋 Este restaurante ainda não cadastrou produtos no cardápio.")
            return

        # Tabs por categoria
        tab_names = [cat.nome for cat in categorias]
        tabs = st.tabs(tab_names)

        for i, categoria in enumerate(categorias):
            with tabs[i]:
                produtos = session.query(Produto).filter(
                    Produto.categoria_id == categoria.id,
                    Produto.disponivel == True
                ).order_by(Produto.ordem_exibicao, Produto.nome).all()

                if not produtos:
                    st.info(f"Nenhum produto disponível em {categoria.nome}")
                    continue

                # Grid de produtos (2 colunas)
                for j in range(0, len(produtos), 2):
                    cols = st.columns(2)
                    for k, col in enumerate(cols):
                        if j + k < len(produtos):
                            produto = produtos[j + k]
                            with col:
                                with st.container():
                                    st.markdown(f"**{produto.nome}**")
                                    if produto.descricao:
                                        st.caption(produto.descricao[:100] + "..." if len(produto.descricao or '') > 100 else produto.descricao)

                                    col_preco, col_btn = st.columns([1, 1])
                                    with col_preco:
                                        st.markdown(f"**R$ {produto.preco:.2f}**")
                                    with col_btn:
                                        if st.button("➕ Adicionar", key=f"add_{produto.id}", use_container_width=True):
                                            adicionar_ao_carrinho(produto.id)
                                            st.toast(f"✅ {produto.nome} adicionado!")

                                    st.markdown("---")
    finally:
        session.close()


def tela_carrinho():
    """Exibe o carrinho de compras"""
    st.markdown("## 🛒 Seu Carrinho")

    if st.button("⬅️ Voltar ao Cardápio"):
        st.session_state.tela_atual = 'cardapio'
        st.rerun()

    if not st.session_state.carrinho:
        st.info("Seu carrinho está vazio. Adicione produtos do cardápio!")
        return

    # Listar itens do carrinho
    for i, item in enumerate(st.session_state.carrinho):
        with st.container():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{item['nome']}**")
                if item.get('observacao'):
                    st.caption(f"Obs: {item['observacao']}")

            with col2:
                st.write(f"R$ {item['preco']:.2f}")

            with col3:
                nova_qtd = st.number_input(
                    "Qtd",
                    min_value=1,
                    max_value=99,
                    value=item['quantidade'],
                    key=f"qtd_{i}",
                    label_visibility="collapsed"
                )
                if nova_qtd != item['quantidade']:
                    st.session_state.carrinho[i]['quantidade'] = nova_qtd
                    st.rerun()

            with col4:
                if st.button("🗑️", key=f"del_{i}"):
                    remover_do_carrinho(i)
                    st.rerun()

        st.markdown("---")

    # Resumo
    subtotal = calcular_total_carrinho()
    st.markdown(f"**Subtotal:** R$ {subtotal:.2f}")

    # Verificar pedido mínimo
    config = st.session_state.restaurante_dados.get('config', {})
    pedido_minimo = config.get('pedido_minimo', 0) if config else 0

    if subtotal < pedido_minimo:
        st.warning(f"⚠️ Pedido mínimo: R$ {pedido_minimo:.2f}. Faltam R$ {pedido_minimo - subtotal:.2f}")
    else:
        if st.button("🚀 Finalizar Pedido", type="primary", use_container_width=True):
            st.session_state.tela_atual = 'checkout'
            st.rerun()


def tela_checkout():
    """Tela de finalização do pedido"""
    st.markdown("## 📝 Finalizar Pedido")

    if st.button("⬅️ Voltar ao Carrinho"):
        st.session_state.tela_atual = 'carrinho'
        st.rerun()

    rest = st.session_state.restaurante_dados
    config = rest.get('config', {})

    # Formulário de entrega
    st.subheader("📍 Endereço de Entrega")

    # Autocomplete de endereço
    endereco_input = st.text_input(
        "Digite seu endereço",
        placeholder="Ex: Rua das Flores, 123",
        key="endereco_autocomplete"
    )

    endereco_selecionado = None
    taxa_calculada = 0.0
    dentro_zona = False

    if endereco_input and len(endereco_input) >= 3:
        # Buscar sugestões
        sugestoes = autocomplete_endereco_restaurante(
            endereco_input,
            st.session_state.restaurante_id
        )

        if sugestoes:
            opcoes = [s['place_name'] for s in sugestoes]
            idx = st.selectbox(
                "Selecione seu endereço:",
                range(len(opcoes)),
                format_func=lambda x: opcoes[x],
                key="endereco_select"
            )
            endereco_selecionado = sugestoes[idx]

            # Calcular taxa em tempo real
            coords_cliente = endereco_selecionado['coordinates']
            coords_rest = (rest['latitude'], rest['longitude'])
            raio_km = config.get('raio_entrega_km', 15.0)

            # Verificar cobertura
            cobertura = check_coverage_zone(coords_rest, coords_cliente, raio_km)
            dentro_zona = cobertura['dentro_zona']

            if dentro_zona:
                # Calcular taxa
                distancia_km = cobertura['distancia_km']
                taxa_calculada = calcular_taxa_entrega(
                    st.session_state.restaurante_id,
                    distancia_km
                )

                st.success(f"✅ {cobertura['mensagem']}")
                st.info(f"🚚 Taxa de entrega: **R$ {taxa_calculada:.2f}** ({distancia_km:.1f} km)")
            else:
                st.error(f"❌ {cobertura['mensagem']}")
                st.warning("Infelizmente não entregamos neste endereço.")

    # Complemento
    complemento = st.text_input("Complemento (apto, bloco, referência)")

    st.markdown("---")

    # Dados do cliente
    st.subheader("👤 Seus Dados")
    col1, col2 = st.columns(2)
    with col1:
        nome_cliente = st.text_input("Nome completo *")
    with col2:
        telefone_cliente = st.text_input("Telefone (WhatsApp) *")

    st.markdown("---")

    # Forma de pagamento
    st.subheader("💳 Forma de Pagamento")
    forma_pagamento = st.radio(
        "Como deseja pagar?",
        ["Dinheiro", "PIX", "Cartão de Crédito (na entrega)", "Cartão de Débito (na entrega)"],
        horizontal=True
    )

    troco_para = None
    if forma_pagamento == "Dinheiro":
        troco_para = st.number_input(
            "Troco para (deixe 0 se não precisar)",
            min_value=0.0,
            step=10.0
        )

    st.markdown("---")

    # Observações
    observacao_pedido = st.text_area("Observações do pedido (opcional)")

    st.markdown("---")

    # Resumo final
    st.subheader("📋 Resumo do Pedido")

    subtotal = calcular_total_carrinho()
    total = subtotal + taxa_calculada

    for item in st.session_state.carrinho:
        st.write(f"• {item['quantidade']}x {item['nome']} - R$ {item['preco'] * item['quantidade']:.2f}")

    st.markdown("---")
    st.write(f"**Subtotal:** R$ {subtotal:.2f}")
    st.write(f"**Taxa de entrega:** R$ {taxa_calculada:.2f}")
    st.markdown(f"### Total: R$ {total:.2f}")

    # Botão de finalizar
    pode_finalizar = (
        endereco_selecionado and
        dentro_zona and
        nome_cliente and
        telefone_cliente and
        len(st.session_state.carrinho) > 0
    )

    if not pode_finalizar:
        st.warning("⚠️ Preencha todos os campos obrigatórios e selecione um endereço válido.")

    if st.button("✅ Confirmar Pedido", type="primary", use_container_width=True, disabled=not pode_finalizar):
        # Criar pedido no banco
        pedido_id = criar_pedido(
            cliente_nome=nome_cliente,
            cliente_telefone=telefone_cliente,
            endereco_completo=endereco_selecionado['place_name'],
            complemento=complemento,
            latitude=endereco_selecionado['coordinates'][0],
            longitude=endereco_selecionado['coordinates'][1],
            forma_pagamento=forma_pagamento,
            troco_para=troco_para,
            observacao=observacao_pedido,
            taxa_entrega=taxa_calculada,
            subtotal=subtotal,
            total=total
        )

        if pedido_id:
            st.session_state.pedido_finalizado_id = pedido_id
            st.session_state.carrinho = []  # Limpar carrinho
            st.session_state.tela_atual = 'acompanhamento'
            st.success("🎉 Pedido enviado com sucesso!")
            st.rerun()
        else:
            st.error("❌ Erro ao enviar pedido. Tente novamente.")


def criar_pedido(**kwargs) -> Optional[int]:
    """Cria o pedido no banco de dados"""
    session = get_db_session()
    try:
        # Gerar comanda única
        from datetime import datetime
        import random
        import json
        comanda = f"{datetime.now().strftime('%H%M')}{random.randint(100, 999)}"

        # Montar string de itens e carrinho_json
        itens_str = []
        carrinho_data = []
        for item in st.session_state.carrinho:
            itens_str.append(f"{item['quantidade']}x {item['nome']}")
            carrinho_data.append({
                'produto_id': item['produto_id'],
                'nome': item['nome'],
                'quantidade': item['quantidade'],
                'preco': item['preco'],
                'observacao': item.get('observacao', '')
            })

        # Montar endereço completo com complemento
        endereco = kwargs['endereco_completo']
        if kwargs.get('complemento'):
            endereco += f" - {kwargs['complemento']}"

        # Montar observações incluindo taxa de entrega
        obs_parts = []
        if kwargs.get('observacao'):
            obs_parts.append(kwargs['observacao'])
        obs_parts.append(f"Taxa de entrega: R$ {kwargs['taxa_entrega']:.2f}")
        observacoes = " | ".join(obs_parts)

        # Criar pedido
        pedido = Pedido(
            restaurante_id=st.session_state.restaurante_id,
            comanda=comanda,
            tipo='delivery',  # Campo obrigatório
            tipo_entrega='entrega',
            cliente_nome=kwargs['cliente_nome'],
            cliente_telefone=kwargs['cliente_telefone'],
            endereco_entrega=endereco,
            latitude_entrega=kwargs['latitude'],
            longitude_entrega=kwargs['longitude'],
            forma_pagamento=kwargs['forma_pagamento'],
            troco_para=kwargs.get('troco_para'),
            observacoes=observacoes,
            itens=", ".join(itens_str),  # Campo obrigatório
            carrinho_json=carrinho_data,
            valor_total=kwargs['total'],
            valor_desconto=0.0,
            status='pendente',
            origem='site',
            data_criacao=datetime.now()
        )
        session.add(pedido)
        session.flush()  # Para obter o ID

        # Criar itens do pedido
        for item in st.session_state.carrinho:
            item_pedido = ItemPedido(
                pedido_id=pedido.id,
                produto_id=item['produto_id'],
                quantidade=item['quantidade'],
                preco_unitario=item['preco'],
                observacoes=item.get('observacao', '')
            )
            session.add(item_pedido)

        session.commit()
        return pedido.id
    except Exception as e:
        session.rollback()
        st.error(f"Erro: {e}")
        return None
    finally:
        session.close()


def tela_acompanhamento():
    """Tela de acompanhamento do pedido"""
    pedido_id = st.session_state.pedido_finalizado_id

    if not pedido_id:
        st.warning("Nenhum pedido para acompanhar.")
        if st.button("Ver Cardápio"):
            st.session_state.tela_atual = 'cardapio'
            st.rerun()
        return

    session = get_db_session()
    try:
        pedido = session.query(Pedido).filter(Pedido.id == pedido_id).first()

        if not pedido:
            st.error("Pedido não encontrado.")
            return

        st.markdown("## 📦 Acompanhe seu Pedido")
        st.markdown(f"### Comanda: #{pedido.comanda}")

        # Status visual
        status_map = {
            'pendente': ('⏳ Aguardando confirmação', 'status-pending'),
            'confirmado': ('✅ Pedido confirmado', 'status-preparing'),
            'preparando': ('👨‍🍳 Preparando seu pedido', 'status-preparing'),
            'pronto': ('🍽️ Pedido pronto!', 'status-ready'),
            'em_entrega': ('🏍️ Saiu para entrega', 'status-delivering'),
            'entregue': ('✅ Pedido entregue!', 'status-delivered'),
            'cancelado': ('❌ Pedido cancelado', 'status-pending'),
        }

        status_info = status_map.get(pedido.status, ('📋 Processando', 'status-pending'))
        st.markdown(f"""
        <div class="status-badge {status_info[1]}">
            {status_info[0]}
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Timeline do pedido
        st.subheader("📊 Timeline")

        etapas = ['pendente', 'confirmado', 'preparando', 'pronto', 'em_entrega', 'entregue']
        etapas_labels = ['Recebido', 'Confirmado', 'Preparando', 'Pronto', 'Saiu', 'Entregue']

        try:
            status_idx = etapas.index(pedido.status)
        except ValueError:
            status_idx = 0

        cols = st.columns(len(etapas))
        for i, (etapa, label) in enumerate(zip(etapas, etapas_labels)):
            with cols[i]:
                if i <= status_idx:
                    st.markdown(f"✅ **{label}**")
                else:
                    st.markdown(f"⬜ {label}")

        st.markdown("---")

        # Detalhes do pedido
        st.subheader("📝 Detalhes")
        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Cliente:** {pedido.cliente_nome}")
            st.write(f"**Telefone:** {pedido.cliente_telefone}")
            st.write(f"**Endereço:** {pedido.endereco_entrega}")

        with col2:
            st.write(f"**Total:** R$ {pedido.valor_total:.2f}")
            st.write(f"**Pagamento:** {pedido.forma_pagamento}")
            if pedido.itens:
                st.write(f"**Itens:** {pedido.itens}")

        # Buscar entrega se existir
        entrega = session.query(Entrega).filter(Entrega.pedido_id == pedido.id).first()
        if entrega and entrega.motoboy_id:
            from database.models import Motoboy
            motoboy = session.query(Motoboy).filter(Motoboy.id == entrega.motoboy_id).first()
            if motoboy:
                st.markdown("---")
                st.subheader("🏍️ Entregador")
                st.write(f"**Nome:** {motoboy.nome}")
                if motoboy.telefone:
                    st.write(f"**Telefone:** {motoboy.telefone}")

        # Botão de atualizar
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Atualizar Status", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("🏠 Novo Pedido", use_container_width=True):
                st.session_state.pedido_finalizado_id = None
                st.session_state.tela_atual = 'cardapio'
                st.rerun()

    finally:
        session.close()


def tela_restaurante_nao_encontrado():
    """Exibe mensagem quando restaurante não é encontrado"""
    st.markdown("""
    <div style="text-align: center; padding: 50px;">
        <h1>🍔 Super Food</h1>
        <h3>Restaurante não encontrado</h3>
        <p>O restaurante que você está procurando não existe ou está temporariamente indisponível.</p>
        <p style="color: #666; font-size: 14px;">
            Acesse usando: <code>?restaurante=CODIGO</code> onde CODIGO é o código de acesso do restaurante.
        </p>
    </div>
    """, unsafe_allow_html=True)


# ==================== MAIN ====================

def main():
    init_session_state()

    # Obter parâmetro do restaurante via query string
    params = st.query_params
    restaurante_param = params.get("restaurante") or params.get("r") or params.get("id")

    if not restaurante_param:
        tela_restaurante_nao_encontrado()
        return

    # Carregar restaurante se ainda não carregado
    if st.session_state.restaurante_id is None:
        if not carregar_restaurante(restaurante_param):
            tela_restaurante_nao_encontrado()
            return

    # Roteamento de telas
    tela = st.session_state.tela_atual

    if tela == 'cardapio':
        tela_cardapio()
    elif tela == 'carrinho':
        tela_carrinho()
    elif tela == 'checkout':
        tela_checkout()
    elif tela == 'acompanhamento':
        tela_acompanhamento()
    else:
        tela_cardapio()


if __name__ == "__main__":
    main()
