# streamlit_app/restaurante_app.py
"""
restaurante_app.py - Dashboard Principal do Restaurante
Sistema completo e integrado para gestão do restaurante
Versão 2.1 com Rotas Inteligentes - TOTALMENTE MIGRADO PARA SQLAlchemy
Mantém 100% da lógica original, UI, fluxos e todas as funções existentes
Apenas o acesso ao banco foi substituído por SQLAlchemy (sem remoção de código)

CORREÇÃO: Navegação via flag temporária para evitar conflito com widget key
"""

# ==================== IMPORT STREAMLIT PRIMEIRO ====================
import streamlit as st

# ==================== SET_PAGE_CONFIG DEVE SER SEGUNDO ====================
st.set_page_config(
    page_title="Dashboard Restaurante - Super Food",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== AGORA RESTO DOS IMPORTS ====================
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import time
import hashlib

# Configuração de path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Imports do projeto - SQLAlchemy
from database.session import get_db_session
from database.models import (
    Restaurante, ConfigRestaurante, Motoboy, MotoboySolicitacao,
    Pedido, Produto, Entrega, Caixa, MovimentacaoCaixa, Notificacao,
    CategoriaMenu, SiteConfig
)

from utils.mapbox_api import autocomplete_address, check_coverage_zone, autocomplete_endereco_restaurante
from utils.calculos import calcular_taxa_entrega, calcular_entrega_completa
from utils.motoboy_selector import (
    selecionar_motoboy_para_rota,
    atribuir_rota_motoboy,
    finalizar_entrega_motoboy,
    marcar_motoboy_disponivel,
    listar_motoboys_disponiveis,
    obter_estatisticas_motoboy,
)

# Módulo de despacho integrado
DESPACHO_DISPONIVEL = True


# ==================== FUNÇÕES DE DESPACHO ====================
def despachar_pedidos_automatico(session, restaurante_id: int) -> dict:
    """
    Despacha pedidos prontos para motoboys disponíveis usando seleção justa.
    """
    # Buscar pedidos prontos não despachados
    pedidos_prontos = session.query(Pedido).filter(
        Pedido.restaurante_id == restaurante_id,
        Pedido.status == 'pronto',
        Pedido.despachado == False,
        Pedido.tipo == 'Entrega'
    ).order_by(Pedido.data_criacao.asc()).all()

    if not pedidos_prontos:
        return {'sucesso': False, 'mensagem': 'Nenhum pedido pronto para despachar'}

    # Buscar config do restaurante
    config = session.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    max_por_rota = config.max_pedidos_por_rota if config else 5
    alertas = []
    rotas_criadas = 0

    # Agrupar pedidos em rotas
    pedidos_restantes = list(pedidos_prontos)

    while pedidos_restantes:
        # Selecionar motoboy
        motoboy = selecionar_motoboy_para_rota(
            restaurante_id,
            min(len(pedidos_restantes), max_por_rota),
            session
        )

        if not motoboy:
            alertas.append(f"⚠️ {len(pedidos_restantes)} pedido(s) aguardando motoboy disponível")
            break

        # Pegar pedidos para esta rota
        pedidos_rota = pedidos_restantes[:min(len(pedidos_restantes), max_por_rota)]
        pedidos_ids = [p.id for p in pedidos_rota]

        # Atribuir rota ao motoboy
        resultado = atribuir_rota_motoboy(motoboy['motoboy_id'], pedidos_ids, session)

        if resultado['sucesso']:
            rotas_criadas += 1
            pedidos_restantes = pedidos_restantes[len(pedidos_rota):]
        else:
            alertas.append(f"Erro ao atribuir rota: {resultado.get('erro', 'Desconhecido')}")
            break

    if rotas_criadas > 0:
        return {
            'sucesso': True,
            'mensagem': f'✅ {rotas_criadas} rota(s) despachada(s) com sucesso!',
            'rotas_criadas': rotas_criadas,
            'alertas': alertas
        }
    else:
        return {
            'sucesso': False,
            'mensagem': 'Não foi possível despachar pedidos',
            'alertas': alertas
        }


def calcular_capacidade_total_motoboys(session, restaurante_id: int) -> dict:
    """
    Calcula capacidade total de entrega dos motoboys.
    """
    motoboys = session.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).all()

    online = [m for m in motoboys if m.disponivel]
    em_rota = [m for m in motoboys if m.em_rota]

    capacidade_total = sum(m.capacidade_entregas or 3 for m in online)
    pedidos_em_rota = sum(m.entregas_pendentes or 0 for m in em_rota)
    capacidade_disponivel = capacidade_total - pedidos_em_rota

    return {
        'motoboys_online': len(online),
        'motoboys_em_rota': len(em_rota),
        'capacidade_total': capacidade_total,
        'pedidos_em_rota': pedidos_em_rota,
        'capacidade_disponivel': max(0, capacidade_disponivel)
    }

# ==================== FUNÇÕES HELPER SQLAlchemy ====================
def to_dict(obj):
    """Converte objeto SQLAlchemy para dict (compatível com código original)"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

def to_dict_list(objs):
    """Converte lista de objetos SQLAlchemy para lista de dicts"""
    return [to_dict(obj) for obj in objs if obj is not None]

# ==================== AUTENTICAÇÃO ====================
def verificar_login():
    """Inicializa estado de sessão do restaurante de forma segura"""
    # Inicialização defensiva - sempre garantir que todas as variáveis existem
    defaults = {
        'restaurante_logado': False,
        'restaurante_id': None,
        'restaurante_dados': None,
        'restaurante_config': None,
        'navegar_para': None,
        '_session_initialized': True
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def is_session_valid():
    """Verifica se a sessão está válida e inicializada"""
    return (
        hasattr(st, 'session_state') and
        st.session_state.get('_session_initialized', False) and
        st.session_state.get('restaurante_logado', False) and
        st.session_state.get('restaurante_id') is not None
    )

def fazer_login(email: str, senha: str) -> bool:
    """Login do restaurante usando SQLAlchemy (mantém lógica original)"""
    session = get_db_session()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        restaurante = session.query(Restaurante).filter(
            Restaurante.email == email,
            Restaurante.senha == senha_hash,
            Restaurante.ativo == True
        ).first()
        
        if not restaurante:
            return False
        
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante.id
        ).first()
        
        st.session_state.restaurante_logado = True
        st.session_state.restaurante_id = restaurante.id
        st.session_state.restaurante_dados = to_dict(restaurante)
        st.session_state.restaurante_config = to_dict(config) if config else None
        
        return True
    except Exception as e:
        st.error(f"Erro ao fazer login: {str(e)}")
        return False
    finally:
        session.close()

def fazer_logout():
    """Logout do restaurante de forma segura"""
    keys_to_clear = [
        'restaurante_logado', 'restaurante_id', 'restaurante_dados',
        'restaurante_config', 'navegar_para'
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            st.session_state[key] = None if key != 'restaurante_logado' else False

# ==================== TELA DE LOGIN ====================
def tela_login():
    """Interface de login (mantida idêntica à original)"""
    st.title("🍕 Super Food - Login Restaurante")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Acesse seu Dashboard")
        
        with st.form("form_login"):
            email = st.text_input("Email", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")
            
            if submit:
                if not email or not senha:
                    st.error("❌ Preencha todos os campos!")
                elif fazer_login(email, senha):
                    st.success("✅ Login realizado com sucesso!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Email ou senha incorretos!")
        
        st.markdown("---")
        st.info("💡 **Primeiro Acesso?** Use as credenciais fornecidas pelo Super Admin.")
        
        if os.getenv("DEBUG"):
            st.caption("🔧 Debug: teste@superfood.com / 123456")

# ==================== SIDEBAR ====================
def renderizar_sidebar():
    """Sidebar com menu e informações (lógica original preservada)"""
    # Verificação defensiva no início
    if not is_session_valid():
        return "🏠 Dashboard"  # Retorna valor padrão se sessão inválida

    with st.sidebar:
        rest = st.session_state.get('restaurante_dados')
        config = st.session_state.get('restaurante_config')

        # Se dados do restaurante não existem, retorna padrão
        if not rest:
            return "🏠 Dashboard"
        
        st.title(f"🍕 {rest['nome_fantasia']}")
        st.caption(f"Plano: **{rest['plano'].upper()}**")
        
        if config and config.get('status_atual') == 'aberto':
            st.success("🟢 **ABERTO**")
        else:
            st.error("🔴 **FECHADO**")
        
        st.markdown("---")
        st.subheader("📋 Menu Principal")
        
        # Se existe navegação pendente, força o valor
        valor_padrao_menu = None
        if st.session_state.get('navegar_para'):
            valor_padrao_menu = st.session_state.get('navegar_para')
            st.session_state.navegar_para = None  # Limpa flag
        
        menu = st.radio(
            "Navegação",
            [
                "🏠 Dashboard",
                "📦 Pedidos",
                "🏍️ Motoboys",
                "🍕 Gerenciar Cardápio",
                "💰 Caixa",
                "⚙️ Configurações",
                "🖨️ Impressão",
                "📊 Relatórios"
            ],
            key="menu_principal",
            index=[
                "🏠 Dashboard",
                "📦 Pedidos",
                "🏍️ Motoboys",
                "🍕 Gerenciar Cardápio",
                "💰 Caixa",
                "⚙️ Configurações",
                "🖨️ Impressão",
                "📊 Relatórios"
            ].index(valor_padrao_menu) if valor_padrao_menu else 0
        )
        
        st.markdown("---")

        # Verificação defensiva antes de acessar banco de dados
        if is_session_valid():
            session = get_db_session()
            try:
                notificacoes = session.query(Notificacao).filter(
                    Notificacao.restaurante_id == st.session_state.restaurante_id,
                    Notificacao.lida == False
                ).count()
                if notificacoes > 0:
                    st.warning(f"🔔 {notificacoes} notificação(ões)")
            except Exception:
                pass  # Ignora erros silenciosamente para não quebrar a UI
            finally:
                session.close()

        st.markdown("---")
        
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()
            st.rerun()
        
        st.caption(f"Código de Acesso: **{rest['codigo_acesso']}**")
        if rest.get('data_vencimento'):
            venc = datetime.fromisoformat(rest['data_vencimento'].isoformat())
            st.caption(f"Vencimento: {venc.strftime('%d/%m/%Y')}")
        
        return menu

# ==================== DASHBOARD ====================
def tela_dashboard():
    """Dashboard principal - lógica 100% original"""
    st.title("🏠 Dashboard")
    
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    
    try:
        config = session.query(ConfigRestaurante).filter(ConfigRestaurante.restaurante_id == rest_id).first()
        
        hoje = datetime.now().date()
        pedidos_hoje = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id,
            Pedido.data_criacao >= datetime.combine(hoje, datetime.min.time())
        ).all()
        
        caixa_aberto = session.query(Caixa).filter(
            Caixa.restaurante_id == rest_id,
            Caixa.status == 'aberto'
        ).first()
        
        motoboys_ativos = session.query(Motoboy).filter(
            Motoboy.restaurante_id == rest_id,
            Motoboy.status == 'ativo'
        ).count()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pedidos Hoje", len(pedidos_hoje))
        with col2:
            pendentes = len([p for p in pedidos_hoje if p.status in ['pendente', 'em_preparo']])
            st.metric("Pedidos Pendentes", pendentes)
        with col3:
            st.metric("Motoboys Ativos", motoboys_ativos)
        with col4:
            st.metric("Caixa", "🟢 ABERTO" if caixa_aberto else "🔴 FECHADO")
        
        st.markdown("---")
        st.subheader("⚡ Controles Rápidos")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if config and config.status_atual == 'fechado':
                if st.button("🟢 Abrir Restaurante", use_container_width=True, type="primary"):
                    config.status_atual = 'aberto'
                    session.commit()
                    st.success("Restaurante aberto!")
                    st.rerun()
            else:
                if st.button("🔴 Fechar Restaurante", use_container_width=True):
                    config.status_atual = 'fechado'
                    session.commit()
                    st.success("Restaurante fechado!")
                    st.rerun()
        
        with col2:
            if not caixa_aberto:
                if st.button("💰 Abrir Caixa", use_container_width=True):
                    st.session_state.modal_abrir_caixa = True
                    st.rerun()
            else:
                if st.button("💰 Ver Caixa", use_container_width=True):
                    st.session_state.navegar_para = "💰 Caixa"
                    st.rerun()
        
        with col3:
            if st.button("📦 Criar Pedido", use_container_width=True):
                st.session_state.navegar_para = "📦 Pedidos"
                st.rerun()
        
        with col4:
            solicitacoes = session.query(MotoboySolicitacao).filter(
                MotoboySolicitacao.restaurante_id == rest_id,
                MotoboySolicitacao.status == 'pendente'
            ).count()
            if solicitacoes > 0:
                if st.button(f"🔔 {solicitacoes} Solicitações", use_container_width=True, type="primary"):
                    st.session_state.navegar_para = "🏍️ Motoboys"
                    st.rerun()
        
        # Modal abrir caixa (lógica original completa)
        if st.session_state.get('modal_abrir_caixa'):
            with st.form("form_abrir_caixa"):
                st.subheader("💰 Abrir Caixa")
                valor_abertura = st.number_input("Valor de Abertura (Troco)", min_value=0.0, value=100.0, step=10.0)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Abrir Caixa", use_container_width=True):
                        caixa = Caixa(
                            restaurante_id=rest_id,
                            data_abertura=datetime.now(),
                            operador_abertura=st.session_state.restaurante_dados['email'],
                            valor_abertura=valor_abertura,
                            status='aberto'
                        )
                        session.add(caixa)
                        session.flush()
                        mov = MovimentacaoCaixa(
                            caixa_id=caixa.id,
                            tipo='abertura',
                            valor=valor_abertura,
                            descricao='Abertura de caixa',
                            data_hora=datetime.now()
                        )
                        session.add(mov)
                        session.commit()
                        st.success("✅ Caixa aberto!")
                        st.session_state.modal_abrir_caixa = False
                        st.rerun()
                with col2:
                    if st.form_submit_button("❌ Cancelar", use_container_width=True):
                        st.session_state.modal_abrir_caixa = False
                        st.rerun()
        
        st.markdown("---")
        st.subheader("📦 Últimos Pedidos")
        
        if pedidos_hoje:
            for pedido in pedidos_hoje[:5]:
                with st.expander(f"Comanda #{pedido.comanda} - {pedido.cliente_nome} - {pedido.status.upper()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Tipo:** {pedido.tipo}")
                        st.markdown(f"**Cliente:** {pedido.cliente_nome}")
                        st.markdown(f"**Telefone:** {pedido.cliente_telefone or 'N/A'}")
                    with col2:
                        st.markdown(f"**Status:** {pedido.status}")
                        st.markdown(f"**Horário:** {pedido.data_criacao.strftime('%H:%M')}")
                        st.markdown(f"**Valor:** R$ {pedido.valor_total:.2f}")
                    st.markdown(f"**Itens:** {pedido.itens}")
                    if pedido.observacoes:
                        st.markdown(f"**Observações:** {pedido.observacoes}")
        else:
            st.info("Nenhum pedido hoje.")
    
    finally:
        session.close()

# ==================== PEDIDOS ====================
def tela_pedidos():
    st.title("📦 Gerenciamento de Pedidos")
    tabs = st.tabs(["➕ Criar Pedido", "📋 Pedidos Ativos", "📜 Histórico"])
    with tabs[0]:
        criar_pedido_manual()
    with tabs[1]:
        listar_pedidos_ativos()
    with tabs[2]:
        historico_pedidos()

def criar_pedido_manual():
    st.subheader("➕ Criar Novo Pedido")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        ultimo_pedido = session.query(Pedido).filter(Pedido.restaurante_id == rest_id).order_by(Pedido.id.desc()).first()
        proxima_comanda = str(int(ultimo_pedido.comanda) + 1) if ultimo_pedido and ultimo_pedido.comanda.isdigit() else "1"
        
        with st.form("form_criar_pedido"):
            col1, col2 = st.columns(2)
            with col1:
                tipo_pedido = st.selectbox("Tipo de Pedido *", ["Entrega", "Retirada na loja", "Para mesa"])
            with col2:
                st.text_input("Comanda", value=proxima_comanda, disabled=True)
            
            st.markdown("### 👤 Dados do Cliente")
            col1, col2 = st.columns(2)
            with col1:
                cliente_nome = st.text_input("Nome do Cliente *")
            with col2:
                cliente_telefone = st.text_input("Telefone/WhatsApp")
            
            endereco_entrega = ""
            numero_mesa = ""
            lat_cliente = None
            lon_cliente = None
            validado_mapbox = False
            
            # Variáveis para taxa de entrega
            taxa_entrega_calculada = 0.0
            distancia_km_calculada = 0.0

            if tipo_pedido == "Entrega":
                st.markdown("### 📍 Endereço de Entrega")

                # Campo de busca de endereço
                endereco_busca = st.text_input(
                    "Digite o endereço",
                    placeholder="Ex: Rua Augusta, 123",
                    help="Digite pelo menos 3 caracteres para ver sugestões da sua cidade"
                )

                if endereco_busca and len(endereco_busca) >= 3:
                    # Usa autocomplete inteligente filtrado pela cidade do restaurante
                    sugestoes = autocomplete_endereco_restaurante(endereco_busca, rest_id, limite=5)

                    if sugestoes:
                        # Mostra opções com indicação de distância
                        opcoes_display = []
                        for s in sugestoes:
                            dist_info = f" ({s['distancia_km']} km)" if 'distancia_km' in s else ""
                            zona_icon = "✅" if s.get('dentro_zona', True) else "⚠️"
                            opcoes_display.append(f"{zona_icon} {s['place_name']}{dist_info}")

                        idx_selecionado = st.selectbox(
                            "Selecione o endereço correto:",
                            range(len(opcoes_display)),
                            format_func=lambda i: opcoes_display[i]
                        )

                        sug_selecionada = sugestoes[idx_selecionado]
                        endereco_entrega = sug_selecionada['place_name']
                        lat_cliente, lon_cliente = sug_selecionada['coordinates']
                        validado_mapbox = True

                        # Verificar zona e calcular taxa
                        config = session.query(ConfigRestaurante).filter(
                            ConfigRestaurante.restaurante_id == rest_id
                        ).first()

                        distancia_km_calculada = sug_selecionada.get('distancia_km', 0)
                        dentro_zona = sug_selecionada.get('dentro_zona', True)

                        if dentro_zona:
                            # Calcular taxa de entrega
                            resultado_taxa = calcular_taxa_entrega(rest_id, distancia_km_calculada, session)
                            taxa_entrega_calculada = resultado_taxa['taxa_total']

                            # Mostrar informações da entrega
                            col_info1, col_info2, col_info3 = st.columns(3)
                            with col_info1:
                                st.metric("📏 Distância", f"{distancia_km_calculada:.1f} km")
                            with col_info2:
                                st.metric("💰 Taxa de Entrega", f"R$ {taxa_entrega_calculada:.2f}")
                            with col_info3:
                                raio = config.raio_entrega_km if config else 10.0
                                st.metric("✅ Zona", f"Dentro ({raio} km)")

                            st.success(f"✅ Endereço válido! Taxa: R$ {taxa_entrega_calculada:.2f}")
                        else:
                            st.error(f"❌ Endereço fora da zona de entrega ({distancia_km_calculada:.1f} km)")
                            validado_mapbox = False
                    else:
                        st.warning("🔍 Nenhuma sugestão encontrada. Tente outro endereço.")
                elif endereco_busca:
                    st.info("💡 Digite pelo menos 3 caracteres para buscar")
            elif tipo_pedido == "Para mesa":
                numero_mesa = st.text_input("Número da Mesa *")
            
            st.markdown("### 🍕 Itens do Pedido")
            itens = st.text_area("Descreva os itens *", placeholder="Ex: 1x Pizza Grande Calabresa\n2x Refrigerante Lata")
            col1, col2 = st.columns(2)
            with col1:
                valor_total = st.number_input("Valor Total (R$)", min_value=0.0, value=0.0, step=1.0)
            with col2:
                tempo_estimado = st.number_input("Tempo Estimado (minutos)", min_value=5, value=45 if tipo_pedido == "Entrega" else 30, step=5)
            
            observacoes = st.text_area("Observações")
            forma_pagamento = st.selectbox("Forma de Pagamento", ["Dinheiro", "Cartão", "Pix", "Online"])
            if forma_pagamento == "Dinheiro":
                troco_para = st.number_input("Troco para", min_value=0.0, step=5.0)
            else:
                troco_para = None
            
            st.markdown("---")
            col_btn = st.columns([2, 1, 2])[1]
            with col_btn:
                submit = st.form_submit_button("✅ Criar Pedido", use_container_width=True, type="primary")
            
            if submit:
                erros = []
                if not cliente_nome or not itens:
                    erros.append("Nome do cliente e itens são obrigatórios")
                if tipo_pedido == "Entrega" and (not endereco_entrega or not validado_mapbox):
                    erros.append("Selecione um endereço válido da lista")
                if tipo_pedido == "Para mesa" and not numero_mesa:
                    erros.append("Número da mesa é obrigatório")
                
                if erros:
                    for erro in erros:
                        st.error(f"❌ {erro}")
                else:
                    # Calcular valor total com taxa de entrega
                    valor_total_com_taxa = valor_total
                    if tipo_pedido == "Entrega" and taxa_entrega_calculada > 0:
                        valor_total_com_taxa = valor_total + taxa_entrega_calculada

                    pedido = Pedido(
                        restaurante_id=rest_id,
                        comanda=proxima_comanda,
                        tipo=tipo_pedido,
                        cliente_nome=cliente_nome,
                        cliente_telefone=cliente_telefone,
                        endereco_entrega=endereco_entrega,
                        latitude_entrega=lat_cliente,
                        longitude_entrega=lon_cliente,
                        numero_mesa=numero_mesa,
                        itens=itens,
                        valor_total=valor_total_com_taxa,
                        observacoes=observacoes,
                        tempo_estimado=tempo_estimado,
                        validado_mapbox=validado_mapbox,
                        distancia_restaurante_km=distancia_km_calculada if tipo_pedido == "Entrega" else None,
                        status='pendente',
                        origem='manual',
                        forma_pagamento=forma_pagamento,
                        troco_para=troco_para,
                        data_criacao=datetime.now()
                    )
                    session.add(pedido)
                    session.commit()
                    st.success(f"✅ Pedido #{proxima_comanda} criado com sucesso!")
                    st.balloons()
                    time.sleep(2)
                    st.rerun()
    finally:
        session.close()

def listar_pedidos_ativos():
    st.subheader("📋 Pedidos Ativos")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        if DESPACHO_DISPONIVEL:
            col_d1, col_d2, col_d3 = st.columns([2, 1, 2])
            with col_d2:
                if st.button("🚀 Despachar Pedidos Prontos", use_container_width=True, type="primary"):
                    resultado = despachar_pedidos_automatico(session, rest_id)
                    if resultado['sucesso']:
                        st.success(resultado['mensagem'])
                        if resultado.get('alertas'):
                            for a in resultado['alertas']:
                                st.warning(a)
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(resultado['mensagem'])
            
            capacidade = calcular_capacidade_total_motoboys(session, rest_id)
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Motoboys Online", capacidade['motoboys_online'])
            with col2:
                st.metric("Capacidade Total", capacidade['capacidade_total'])
            with col3:
                st.metric("Em Rota", capacidade['pedidos_em_rota'])
            with col4:
                st.metric("Disponível", capacidade['capacidade_disponivel'])
            st.markdown("---")
        
        pedidos = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id,
            Pedido.status.notin_(['finalizado', 'cancelado', 'entregue'])
        ).order_by(Pedido.data_criacao.desc()).all()
        
        if not pedidos:
            st.info("Nenhum pedido ativo no momento.")
            return
        
        col1, col2 = st.columns(2)
        with col1:
            filtro_tipo = st.selectbox("Tipo", ["Todos", "Entrega", "Retirada na loja", "Para mesa"], key="filtro_tipo_ativo")
        with col2:
            filtro_status = st.selectbox("Status", ["Todos", "pendente", "em_preparo", "pronto", "saiu_entrega"], key="filtro_status_ativo")
        
        if filtro_tipo != "Todos":
            pedidos = [p for p in pedidos if p.tipo == filtro_tipo]
        if filtro_status != "Todos":
            pedidos = [p for p in pedidos if p.status == filtro_status]
        
        st.markdown(f"**{len(pedidos)} pedido(s) encontrado(s)**")
        st.markdown("---")
        
        for pedido in pedidos:
            with st.expander(f"🍕 Comanda #{pedido.comanda} - {pedido.cliente_nome} - {pedido.status.upper()}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Tipo:** {pedido.tipo}")
                    st.markdown(f"**Cliente:** {pedido.cliente_nome}")
                    st.markdown(f"**Telefone:** {pedido.cliente_telefone or 'N/A'}")
                    if pedido.tipo == "Entrega":
                        st.markdown(f"**Endereço:** {pedido.endereco_entrega}")
                    elif pedido.tipo == "Para mesa":
                        st.markdown(f"**Mesa:** {pedido.numero_mesa}")
                    st.markdown(f"**Pagamento:** {pedido.forma_pagamento}")
                    if pedido.troco_para:
                        st.markdown(f"**Troco para:** R$ {pedido.troco_para:.2f}")
                with col2:
                    st.markdown(f"**Status:** {pedido.status}")
                    st.markdown(f"**Horário:** {pedido.data_criacao.strftime('%H:%M')}")
                    st.markdown(f"**Tempo Estimado:** {pedido.tempo_estimado} min")
                    st.markdown(f"**Valor:** R$ {pedido.valor_total:.2f}")
                
                st.markdown(f"**Itens:**")
                st.text(pedido.itens)
                if pedido.observacoes:
                    st.markdown(f"**Observações:** {pedido.observacoes}")
                
                st.markdown("---")
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                with col_btn1:
                    if pedido.status == 'pendente':
                        if st.button("👨‍🍳 Iniciar Preparo", key=f"preparo_{pedido.id}"):
                            pedido.status = 'em_preparo'
                            session.commit()
                            st.success("Pedido em preparo!")
                            st.rerun()
                with col_btn2:
                    if pedido.status == 'em_preparo':
                        if st.button("✅ Pedido Pronto", key=f"pronto_{pedido.id}"):
                            pedido.status = 'pronto'
                            session.commit()
                            st.success("Pedido pronto!")
                            st.rerun()
                with col_btn3:
                    if pedido.status in ['pronto', 'saiu_entrega']:
                        if st.button("✅ Entregue/Finalizado", key=f"finalizar_{pedido.id}"):
                            pedido.status = 'entregue' if pedido.tipo == "Entrega" else 'finalizado'
                            session.commit()
                            st.success("Pedido finalizado!")
                            st.rerun()
                with col_btn4:
                    if st.button("❌ Cancelar", key=f"cancelar_{pedido.id}"):
                        pedido.status = 'cancelado'
                        session.commit()
                        st.warning("Pedido cancelado!")
                        st.rerun()
    finally:
        session.close()

def historico_pedidos():
    st.subheader("📜 Histórico de Pedidos")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data Início", value=datetime.now() - timedelta(days=30))
        with col2:
            data_fim = st.date_input("Data Fim", value=datetime.now())
        
        pedidos = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id,
            Pedido.data_criacao >= datetime.combine(data_inicio, datetime.min.time()),
            Pedido.data_criacao <= datetime.combine(data_fim, datetime.max.time())
        ).order_by(Pedido.data_criacao.desc()).all()
        
        if not pedidos:
            st.info("Nenhum pedido no período selecionado.")
            return
        
        total_pedidos = len(pedidos)
        total_vendas = sum(p.valor_total for p in pedidos)
        entregas = len([p for p in pedidos if p.tipo == "Entrega"])
        mesas = len([p for p in pedidos if p.tipo == "Para mesa"])
        retiradas = len([p for p in pedidos if p.tipo == "Retirada na loja"])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Pedidos", total_pedidos)
        with col2:
            st.metric("Total Vendas", f"R$ {total_vendas:.2f}")
        with col3:
            st.metric("Entregas", entregas)
        with col4:
            st.metric("Mesas + Retiradas", mesas + retiradas)
        
        st.markdown("---")
        
        for pedido in pedidos:
            with st.expander(f"Comanda #{pedido.comanda} - {pedido.cliente_nome} - {pedido.status.upper()} - R$ {pedido.valor_total:.2f}"):
                st.markdown(f"**Data:** {pedido.data_criacao.strftime('%d/%m/%Y %H:%M')}")
                st.markdown(f"**Tipo:** {pedido.tipo}")
                st.markdown(f"**Status:** {pedido.status}")
                st.markdown(f"**Itens:** {pedido.itens}")
                if pedido.observacoes:
                    st.markdown(f"**Observações:** {pedido.observacoes}")
                st.markdown(f"**Pagamento:** {pedido.forma_pagamento}")
                if pedido.troco_para:
                    st.markdown(f"**Troco para:** R$ {pedido.troco_para:.2f}")
    finally:
        session.close()

# ==================== MOTOBOYS ====================
def tela_motoboys():
    st.title("🏍️ Gerenciamento de Motoboys")
    tabs = st.tabs(["📋 Motoboys Ativos", "🆕 Solicitações", "➕ Cadastrar Manual"])
    with tabs[0]:
        listar_motoboys_ativos()
    with tabs[1]:
        listar_solicitacoes()
    with tabs[2]:
        cadastrar_motoboy_manual()

def listar_motoboys_ativos():
    st.subheader("📋 Motoboys Ativos")
    session = get_db_session()
    try:
        motoboys = session.query(Motoboy).filter(
            Motoboy.restaurante_id == st.session_state.restaurante_id,
            Motoboy.status == 'ativo'
        ).order_by(Motoboy.ordem_hierarquia.asc(), Motoboy.nome).all()

        if not motoboys:
            st.info("Nenhum motoboy ativo.")
            return

        # Resumo geral
        online = len([m for m in motoboys if m.disponivel])
        em_rota = len([m for m in motoboys if m.em_rota])
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Ativos", len(motoboys))
        with col2:
            st.metric("Online", online)
        with col3:
            st.metric("Em Rota", em_rota)
        with col4:
            st.metric("Disponíveis", online - em_rota)

        st.markdown("---")

        for motoboy in motoboys:
            # Status visual
            if motoboy.em_rota:
                status_icon = "🚴"
                status_text = "Em Rota"
            elif motoboy.disponivel:
                status_icon = "✅"
                status_text = "Disponível"
            else:
                status_icon = "⏸️"
                status_text = "Offline"

            with st.expander(f"{status_icon} {motoboy.nome} - {status_text} (Posição: #{motoboy.ordem_hierarquia or 0})"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"**Telefone:** {motoboy.telefone}")
                    st.markdown(f"**Usuário:** {motoboy.usuario}")
                    st.markdown(f"**Capacidade:** {motoboy.capacidade_entregas} entregas")
                with col2:
                    st.markdown(f"**Entregas Pendentes:** {motoboy.entregas_pendentes or 0}")
                    st.markdown(f"**Total Entregas:** {motoboy.total_entregas or 0}")
                    st.markdown(f"**Total KM:** {motoboy.total_km or 0:.1f} km")
                with col3:
                    st.markdown(f"**Ganhos Totais:** R$ {motoboy.total_ganhos or 0:.2f}")
                    if motoboy.ultima_entrega_em:
                        st.markdown(f"**Última Entrega:** {motoboy.ultima_entrega_em.strftime('%d/%m %H:%M')}")
                    if motoboy.ultima_rota_em:
                        st.markdown(f"**Última Rota:** {motoboy.ultima_rota_em.strftime('%d/%m %H:%M')}")

                st.markdown("---")

                # Botões de ação
                col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
                with col_btn1:
                    if motoboy.disponivel:
                        if st.button("⏸️ Marcar Offline", key=f"offline_{motoboy.id}"):
                            resultado = marcar_motoboy_disponivel(motoboy.id, False, session=session)
                            if resultado['sucesso']:
                                st.success("Motoboy marcado como offline!")
                                st.rerun()
                    else:
                        if st.button("✅ Marcar Online", key=f"online_{motoboy.id}"):
                            resultado = marcar_motoboy_disponivel(motoboy.id, True, session=session)
                            if resultado['sucesso']:
                                st.success("Motoboy marcado como online!")
                                st.rerun()
                with col_btn2:
                    if st.button("❌ Desativar", key=f"desativar_{motoboy.id}"):
                        motoboy.status = 'inativo'
                        motoboy.disponivel = False
                        motoboy.em_rota = False
                        session.commit()
                        st.success("Motoboy desativado!")
                        st.rerun()
                with col_btn3:
                    if st.button("🔄 Redefinir Senha", key=f"reset_senha_{motoboy.id}"):
                        motoboy.set_senha("123456")
                        session.commit()
                        st.success("Senha redefinida para: 123456")
                with col_btn4:
                    # Ver estatísticas detalhadas
                    stats = obter_estatisticas_motoboy(motoboy.id, session)
                    if stats:
                        st.metric("Hoje", f"R$ {stats['ganhos_hoje']:.2f}")
                        st.rerun()
    finally:
        session.close()

def listar_solicitacoes():
    st.subheader("🆕 Solicitações Pendentes")
    session = get_db_session()
    try:
        solicitacoes = session.query(MotoboySolicitacao).filter(
            MotoboySolicitacao.restaurante_id == st.session_state.restaurante_id,
            MotoboySolicitacao.status == 'pendente'
        ).order_by(MotoboySolicitacao.data_solicitacao.desc()).all()

        if not solicitacoes:
            st.info("Nenhuma solicitação pendente.")
            return
        
        for sol in solicitacoes:
            with st.container():
                st.markdown(f"**Nome:** {sol.nome}")
                st.markdown(f"**Usuário:** {sol.usuario}")
                st.markdown(f"**Telefone:** {sol.telefone}")
                st.markdown(f"**Data:** {sol.data_solicitacao.strftime('%d/%m/%Y %H:%M')}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Aprovar", key=f"aprovar_{sol.id}"):
                        motoboy = Motoboy(
                            restaurante_id=sol.restaurante_id,
                            nome=sol.nome,
                            usuario=sol.usuario,
                            telefone=sol.telefone,
                            senha=hashlib.sha256("123456".encode()).hexdigest(),
                            status='ativo',
                            capacidade_entregas=3,
                            data_cadastro=datetime.now()
                        )
                        session.add(motoboy)
                        sol.status = 'aprovado'
                        session.commit()
                        st.success("Motoboy aprovado! Senha inicial: 123456")
                        st.rerun()
                with col2:
                    if st.button("❌ Rejeitar", key=f"rejeitar_{sol.id}"):
                        sol.status = 'rejeitado'
                        session.commit()
                        st.warning("Solicitação rejeitada")
                        st.rerun()
                st.markdown("---")
    finally:
        session.close()

def cadastrar_motoboy_manual():
    st.subheader("➕ Cadastrar Motoboy Manualmente")
    with st.form("form_cadastro_manual"):
        nome = st.text_input("Nome Completo *")
        usuario = st.text_input("Usuário *")
        telefone = st.text_input("Telefone *")
        senha = st.text_input("Senha Inicial *", type="password", value="123456")

        if st.form_submit_button("✅ Cadastrar", use_container_width=True):
            erros = []
            if not nome or not usuario or not telefone or not senha:
                erros.append("Preencha todos os campos")
            
            if erros:
                for e in erros:
                    st.error(e)
            else:
                session = get_db_session()
                try:
                    existe = session.query(Motoboy).filter(
                        Motoboy.restaurante_id == st.session_state.restaurante_id,
                        Motoboy.usuario == usuario.lower()
                    ).first()
                    if existe:
                        st.error("Usuário já existe!")
                    else:
                        motoboy = Motoboy(
                            restaurante_id=st.session_state.restaurante_id,
                            nome=nome,
                            usuario=usuario.lower(),
                            telefone=telefone,
                            senha=hashlib.sha256(senha.encode()).hexdigest(),
                            status='ativo',
                            capacidade_entregas=3,
                            data_cadastro=datetime.now()
                        )
                        session.add(motoboy)
                        session.commit()
                        st.success("Motoboy cadastrado com sucesso!")
                        st.rerun()
                finally:
                    session.close()

# ==================== CAIXA ====================
def tela_caixa():
    st.title("💰 Gerenciamento de Caixa")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        caixa = session.query(Caixa).filter(
            Caixa.restaurante_id == rest_id,
            Caixa.status == 'aberto'
        ).first()

        if not caixa:
            st.warning("🔴 Caixa está FECHADO")
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                with st.form("form_abrir_caixa"):
                    st.subheader("Abrir Caixa")
                    valor_abertura = st.number_input("Valor de Abertura (Troco em R$)", min_value=0.0, value=100.0, step=10.0)
                    operador = st.text_input("Operador", value=st.session_state.restaurante_dados['email'])
                    if st.form_submit_button("✅ Abrir Caixa", use_container_width=True, type="primary"):
                        novo_caixa = Caixa(
                            restaurante_id=rest_id,
                            data_abertura=datetime.now(),
                            operador_abertura=operador,
                            valor_abertura=valor_abertura,
                            status='aberto'
                        )
                        session.add(novo_caixa)
                        session.flush()
                        mov = MovimentacaoCaixa(
                            caixa_id=novo_caixa.id,
                            tipo='abertura',
                            valor=valor_abertura,
                            descricao='Abertura de caixa',
                            data_hora=datetime.now()
                        )
                        session.add(mov)
                        session.commit()
                        st.success("Caixa aberto!")
                        st.rerun()
        else:
            st.success("🟢 Caixa está ABERTO")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Valor Abertura", f"R$ {caixa.valor_abertura:.2f}")
            with col2:
                st.metric("Total Vendas", f"R$ {caixa.total_vendas:.2f}")
            with col3:
                st.metric("Retiradas", f"R$ {caixa.valor_retiradas:.2f}")
            with col4:
                saldo = caixa.valor_abertura + caixa.total_vendas - caixa.valor_retiradas
                st.metric("Saldo Atual", f"R$ {saldo:.2f}")
            
            tabs = st.tabs(["💵 Fazer Retirada", "📜 Movimentações", "🔒 Fechar Caixa"])
            with tabs[0]:
                with st.form("form_retirada"):
                    valor = st.number_input("Valor da Retirada (R$)", min_value=0.01, step=10.0)
                    descricao = st.text_input("Descrição/Motivo *")
                    if st.form_submit_button("💸 Confirmar Retirada", use_container_width=True):
                        if not descricao:
                            st.error("Descrição obrigatória!")
                        else:
                            mov = MovimentacaoCaixa(
                                caixa_id=caixa.id,
                                tipo='retirada',
                                valor=valor,
                                descricao=descricao,
                                data_hora=datetime.now()
                            )
                            session.add(mov)
                            caixa.valor_retiradas += valor
                            session.commit()
                            st.success("Retirada registrada!")
                            st.rerun()
            
            with tabs[1]:
                movimentacoes = session.query(MovimentacaoCaixa).filter(
                    MovimentacaoCaixa.caixa_id == caixa.id
                ).order_by(MovimentacaoCaixa.data_hora.desc()).all()
                if movimentacoes:
                    for mov in movimentacoes:
                        icon = {"abertura": "🔓", "venda": "💰", "retirada": "💸", "fechamento": "🔒"}.get(mov.tipo, "📝")
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"{icon} **{mov.tipo.upper()}** - {mov.descricao}")
                            st.caption(mov.data_hora.strftime('%d/%m %H:%M'))
                        with col2:
                            cor = "green" if mov.tipo in ['abertura', 'venda'] else "red"
                            st.markdown(f"<h3 style='color:{cor}'>R$ {mov.valor:.2f}</h3>", unsafe_allow_html=True)
                        st.markdown("---")
                else:
                    st.info("Nenhuma movimentação.")
            
            with tabs[2]:
                config = session.query(ConfigRestaurante).filter(ConfigRestaurante.restaurante_id == rest_id).first()
                if config and config.status_atual != 'fechado':
                    st.error("⚠️ Feche o restaurante antes de fechar o caixa!")
                else:
                    saldo_esperado = caixa.valor_abertura + caixa.total_vendas - caixa.valor_retiradas
                    st.markdown(f"**Saldo Esperado:** R$ {saldo_esperado:.2f}")
                    with st.form("form_fechar_caixa"):
                        valor_contado = st.number_input("Valor Contado no Caixa (R$)", min_value=0.0, value=saldo_esperado, step=1.0)
                        operador_fechamento = st.text_input("Operador Fechamento", value=st.session_state.restaurante_dados['email'])
                        if st.form_submit_button("🔒 FECHAR CAIXA", use_container_width=True, type="primary"):
                            caixa.status = 'fechado'
                            caixa.data_fechamento = datetime.now()
                            caixa.operador_fechamento = operador_fechamento
                            caixa.valor_contado = valor_contado
                            caixa.diferenca = valor_contado - saldo_esperado
                            mov = MovimentacaoCaixa(
                                caixa_id=caixa.id,
                                tipo='fechamento',
                                valor=valor_contado,
                                descricao='Fechamento de caixa',
                                data_hora=datetime.now()
                            )
                            session.add(mov)
                            session.commit()
                            st.success("Caixa fechado com sucesso!")
                            st.balloons()
                            st.rerun()
    finally:
        session.close()

# ==================== CONFIGURAÇÕES ====================
def tela_configuracoes():
    st.title("⚙️ Configurações")
    tabs = st.tabs(["🕐 Horários", "📍 Endereço", "💰 Taxas", "🌐 Site do Cliente", "🔗 Integrações", "🔐 Segurança"])

    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest_id
        ).first()
        
        rest = session.get(Restaurante, rest_id)
        
        with tabs[0]:
            st.subheader("🕐 Horários de Funcionamento")
            with st.form("form_horarios_config"):
                col1, col2 = st.columns(2)
                with col1:
                    abertura = st.time_input("Horário de Abertura", value=datetime.strptime(config.horario_abertura, '%H:%M').time())
                with col2:
                    fechamento = st.time_input("Horário de Fechamento", value=datetime.strptime(config.horario_fechamento, '%H:%M').time())
                # Normalizar valores do banco para corresponder às opções
                opcoes_dias = ['segunda','terca','quarta','quinta','sexta','sabado','domingo']
                mapeamento_dias = {
                    'seg': 'segunda', 'ter': 'terca', 'qua': 'quarta', 'qui': 'quinta',
                    'sex': 'sexta', 'sab': 'sabado', 'dom': 'domingo'
                }
                dias_salvos = config.dias_semana_abertos.split(',') if config.dias_semana_abertos else []
                dias_normalizados = []
                for d in dias_salvos:
                    d_limpo = d.strip().lower()
                    if d_limpo in mapeamento_dias:
                        dias_normalizados.append(mapeamento_dias[d_limpo])
                    elif d_limpo in opcoes_dias:
                        dias_normalizados.append(d_limpo)
                # Filtrar apenas valores válidos
                dias_default = [d for d in dias_normalizados if d in opcoes_dias]
                dias = st.multiselect("Dias Abertos", opcoes_dias, default=dias_default)
                if st.form_submit_button("💾 Salvar Horários"):
                    config.horario_abertura = abertura.strftime('%H:%M')
                    config.horario_fechamento = fechamento.strftime('%H:%M')
                    config.dias_semana_abertos = ','.join(dias)
                    session.commit()
                    st.success("Horários salvos!")
                    st.rerun()
        
        with tabs[1]:
            st.subheader("📍 Endereço do Restaurante")
            with st.form("form_endereco_config"):
                novo_endereco = st.text_area("Endereço Completo", value=rest.endereco_completo, height=150)
                if st.form_submit_button("💾 Atualizar Endereço"):
                    rest.endereco_completo = novo_endereco
                    session.commit()
                    st.success("Endereço atualizado!")
                    st.rerun()
        
        with tabs[2]:
            st.subheader("💰 Taxas e Configurações de Entrega")
            with st.form("form_taxas_config"):
                st.markdown("#### 🚗 Taxa de Entrega (cobrada do cliente)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    taxa_entrega_base = st.number_input(
                        "Taxa Base (R$)",
                        value=config.taxa_entrega_base or 5.0,
                        step=1.0,
                        help="Valor cobrado até a distância base"
                    )
                with col2:
                    distancia_base = st.number_input(
                        "Distância Base (km)",
                        value=config.distancia_base_km or 3.0,
                        step=0.5,
                        help="Km incluídos na taxa base"
                    )
                with col3:
                    taxa_km_extra = st.number_input(
                        "Taxa por km Extra (R$)",
                        value=config.taxa_km_extra or 1.5,
                        step=0.1,
                        help="Valor cobrado por km adicional"
                    )

                st.markdown("---")
                st.markdown("#### 🏍️ Pagamento do Motoboy")
                col1, col2, col3 = st.columns(3)
                with col1:
                    valor_base_motoboy = st.number_input(
                        "Valor Base por Entrega (R$)",
                        value=config.valor_base_motoboy or 5.0,
                        step=0.5,
                        help="Valor pago ao motoboy até a distância base"
                    )
                with col2:
                    valor_km_extra_motoboy = st.number_input(
                        "Valor por km Extra (R$)",
                        value=config.valor_km_extra_motoboy or 1.0,
                        step=0.1,
                        help="Valor adicional por km para o motoboy"
                    )
                with col3:
                    taxa_diaria = st.number_input(
                        "Taxa Diária (R$)",
                        value=config.taxa_diaria or 0.0,
                        step=5.0,
                        help="Taxa fixa diária (opcional)"
                    )

                col1, col2 = st.columns(2)
                with col1:
                    valor_lanche = st.number_input(
                        "Valor Lanche (R$)",
                        value=config.valor_lanche or 0.0,
                        step=5.0,
                        help="Valor para alimentação (opcional)"
                    )
                with col2:
                    max_pedidos_rota = st.number_input(
                        "Máx. Pedidos por Rota",
                        value=config.max_pedidos_por_rota or 5,
                        min_value=1,
                        max_value=10,
                        step=1,
                        help="Quantos pedidos cada motoboy pode levar por vez"
                    )

                permitir_ver_saldo = st.checkbox(
                    "Permitir motoboys verem seu saldo",
                    value=config.permitir_ver_saldo_motoboy if config.permitir_ver_saldo_motoboy is not None else True,
                    help="Se marcado, motoboys podem ver quanto ganharam no dia"
                )

                st.markdown("---")
                st.markdown("#### 🗺️ Área de Entrega e Despacho")
                col1, col2 = st.columns(2)
                with col1:
                    raio_entrega = st.number_input(
                        "Raio de Entrega (km)",
                        value=config.raio_entrega_km or 10.0,
                        step=1.0,
                        help="Distância máxima para entregas"
                    )
                    despacho_auto = st.checkbox(
                        "Despacho Automático",
                        value=config.despacho_automatico
                    )
                with col2:
                    modo_despacho = st.selectbox(
                        "Modo de Despacho",
                        ["auto_economico", "auto_rapido", "manual"],
                        index=["auto_economico", "auto_rapido", "manual"].index(config.modo_despacho or "auto_economico")
                    )

                st.markdown("---")
                if st.form_submit_button("💾 Salvar Configurações", use_container_width=True, type="primary"):
                    # Taxa do cliente
                    config.taxa_entrega_base = taxa_entrega_base
                    config.distancia_base_km = distancia_base
                    config.taxa_km_extra = taxa_km_extra
                    # Pagamento motoboy
                    config.valor_base_motoboy = valor_base_motoboy
                    config.valor_km_extra_motoboy = valor_km_extra_motoboy
                    config.taxa_diaria = taxa_diaria
                    config.valor_lanche = valor_lanche
                    config.max_pedidos_por_rota = max_pedidos_rota
                    config.permitir_ver_saldo_motoboy = permitir_ver_saldo
                    # Área e despacho
                    config.raio_entrega_km = raio_entrega
                    config.despacho_automatico = despacho_auto
                    config.modo_despacho = modo_despacho

                    session.commit()
                    st.success("✅ Configurações salvas com sucesso!")
                    st.rerun()
        
        with tabs[3]:
            st.subheader("🌐 Configuração do Site do Cliente")
            site_config = session.query(SiteConfig).filter(SiteConfig.restaurante_id == rest_id).first()
            
            if not site_config:
                st.warning("🌐 Site não configurado. Solicite ao Super Admin.")
            else:
                with st.form("form_site_config"):
                    st.markdown("### 🎨 Aparência")
                    col1, col2 = st.columns(2)
                    with col1:
                        cor_primaria = st.color_picker("Cor Primária", value=site_config.tema_cor_primaria)
                        tempo_entrega = st.number_input("Tempo Entrega (min)", value=site_config.tempo_entrega_estimado, step=5)
                        pedido_minimo = st.number_input("Pedido Mínimo (R$)", value=site_config.pedido_minimo, step=5.0)
                    with col2:
                        cor_secundaria = st.color_picker("Cor Secundária", value=site_config.tema_cor_secundaria)
                        tempo_retirada = st.number_input("Tempo Retirada (min)", value=site_config.tempo_retirada_estimado, step=5)
                        site_ativo = st.checkbox("Site Ativo", value=site_config.site_ativo)
                    
                    st.markdown("### 📞 WhatsApp")
                    col1, col2 = st.columns(2)
                    with col1:
                        whatsapp = st.text_input("Número WhatsApp (com DDD)", value=site_config.whatsapp_numero or "", placeholder="11999999999")
                        whatsapp_ativo = st.checkbox("WhatsApp Ativo", value=site_config.whatsapp_ativo)
                    with col2:
                        whatsapp_msg = st.text_area("Mensagem Padrão", value=site_config.whatsapp_mensagem_padrao, height=100)
                    
                    st.markdown("### 💳 Formas de Pagamento")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        aceita_dinheiro = st.checkbox("💵 Dinheiro", value=site_config.aceita_dinheiro)
                    with col2:
                        aceita_cartao = st.checkbox("💳 Cartão", value=site_config.aceita_cartao)
                    with col3:
                        aceita_pix = st.checkbox("📱 PIX", value=site_config.aceita_pix)
                    with col4:
                        aceita_vale = st.checkbox("🎫 Vale Refeição", value=site_config.aceita_vale_refeicao)
                    
                    st.markdown("---")
                    if st.form_submit_button("💾 Salvar Configurações", use_container_width=True, type="primary"):
                        site_config.tema_cor_primaria = cor_primaria
                        site_config.tema_cor_secundaria = cor_secundaria
                        site_config.tempo_entrega_estimado = tempo_entrega
                        site_config.tempo_retirada_estimado = tempo_retirada
                        site_config.pedido_minimo = pedido_minimo
                        site_config.site_ativo = site_ativo
                        site_config.whatsapp_numero = whatsapp
                        site_config.whatsapp_ativo = whatsapp_ativo
                        site_config.whatsapp_mensagem_padrao = whatsapp_msg
                        site_config.aceita_dinheiro = aceita_dinheiro
                        site_config.aceita_cartao = aceita_cartao
                        site_config.aceita_pix = aceita_pix
                        site_config.aceita_vale_refeicao = aceita_vale
                        site_config.atualizado_em = datetime.utcnow()
                        session.commit()
                        st.success("✅ Configurações do site salvas!")
                        st.rerun()
                
                st.markdown("---")
                st.markdown("### 🔗 URL do Seu Site")
                url_site = f"http://seu-dominio.com/site/{rest.codigo_acesso}"
                st.code(url_site, language="text")
                st.markdown(f"[🌐 Abrir Site (após deploy)]({url_site})")
        
        with tabs[4]:
            st.info("🚧 Integrações em desenvolvimento...")
        
        with tabs[5]:
            st.subheader("🔐 Alterar Senha do Restaurante")
            with st.form("form_senha_config"):
                senha_atual = st.text_input("Senha Atual", type="password")
                nova_senha = st.text_input("Nova Senha", type="password")
                confirmar = st.text_input("Confirmar Nova Senha", type="password")
                if st.form_submit_button("🔑 Alterar Senha"):
                    if nova_senha != confirmar:
                        st.error("Senhas não coincidem")
                    elif not senha_atual or not nova_senha:
                        st.error("Preencha todos os campos")
                    else:
                        if rest.verificar_senha(senha_atual):
                            rest.set_senha(nova_senha)
                            session.commit()
                            st.success("Senha alterada com sucesso!")
                            st.rerun()
                        else:
                            st.error("Senha atual incorreta")

    finally:
        session.close()

# ==================== CARDÁPIO ====================
def tela_gerenciar_cardapio():
    st.title("🍕 Gerenciar Cardápio do Site")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        site_config = session.query(SiteConfig).filter(SiteConfig.restaurante_id == rest_id).first()
        if not site_config:
            st.warning("🌐 Site não configurado. Solicite ao Super Admin para criar seu site.")
            return

        tabs = st.tabs(["📂 Categorias", "🍕 Produtos", "🏷️ Promoções"])

        with tabs[0]:
            st.subheader("📂 Categorias do Cardápio")
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("➕ Nova Categoria", use_container_width=True):
                    st.session_state.modal_nova_categoria = True

            categorias = session.query(CategoriaMenu).filter(CategoriaMenu.restaurante_id == rest_id).order_by(CategoriaMenu.ordem_exibicao).all()

            if not categorias:
                st.info("Nenhuma categoria cadastrada.")
            else:
                for cat in categorias:
                    with st.expander(f"{cat.icone or '📁'} {cat.nome} (Ordem: {cat.ordem_exibicao})"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Descrição:** {cat.descricao or 'Sem descrição'}")
                            st.markdown(f"**Status:** {'✅ Ativa' if cat.ativo else '❌ Inativa'}")
                        with col2:
                            if st.button("✏️ Editar", key=f"edit_cat_{cat.id}"):
                                st.session_state.editar_categoria_id = cat.id
                                st.rerun()
                            if st.button("🗑️ Excluir", key=f"del_cat_{cat.id}"):
                                session.delete(cat)
                                session.commit()
                                st.success("Categoria excluída!")
                                st.rerun()

            if st.session_state.get("modal_nova_categoria"):
                with st.form("form_nova_categoria"):
                    st.subheader("➕ Nova Categoria")
                    nome = st.text_input("Nome *")
                    descricao = st.text_area("Descrição")
                    icone = st.text_input("Ícone (emoji)")
                    ordem = st.number_input("Ordem de Exibição", min_value=0, value=len(categorias) + 1, step=1)
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("✅ Salvar", use_container_width=True):
                            if not nome:
                                st.error("Nome obrigatório!")
                            else:
                                session.add(CategoriaMenu(
                                    restaurante_id=rest_id,
                                    nome=nome,
                                    descricao=descricao,
                                    icone=icone,
                                    ordem_exibicao=ordem,
                                    ativo=True
                                ))
                                session.commit()
                                st.success("Categoria criada!")
                                st.session_state.modal_nova_categoria = False
                                st.rerun()
                    with col2:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.modal_nova_categoria = False
                            st.rerun()

        with tabs[1]:
            st.subheader("🍕 Produtos do Cardápio")
            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("➕ Novo Produto", use_container_width=True):
                    st.session_state.modal_novo_produto = True

            categorias_filtro = session.query(CategoriaMenu).filter(CategoriaMenu.restaurante_id == rest_id).all()
            cat_selecionada = st.selectbox("Filtrar por Categoria", ["Todas"] + [f"{c.icone or ''} {c.nome}" for c in categorias_filtro])

            query_produtos = session.query(Produto).filter(Produto.restaurante_id == rest_id)
            if cat_selecionada != "Todas":
                cat_id = next((c.id for c in categorias_filtro if f"{c.icone or ''} {c.nome}" == cat_selecionada), None)
                if cat_id:
                    query_produtos = query_produtos.filter(Produto.categoria_id == cat_id)

            produtos = query_produtos.order_by(Produto.ordem_exibicao, Produto.nome).all()

            if not produtos:
                st.info("Nenhum produto cadastrado.")
            else:
                for produto in produtos:
                    with st.expander(f"{'⭐' if produto.destaque else ''} {'🔥' if produto.promocao else ''} {produto.nome} - R$ {produto.preco:.2f}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if produto.imagem_url:
                                st.image(produto.imagem_url, width=200)
                            st.markdown(f"**Descrição:** {produto.descricao or 'Sem descrição'}")
                            st.markdown(f"**Preço:** R$ {produto.preco:.2f}")
                            if produto.promocao and produto.preco_promocional:
                                st.markdown(f"**Preço Promocional:** R$ {produto.preco_promocional:.2f}")
                            st.markdown(f"**Status:** {'✅ Disponível' if produto.disponivel else '❌ Indisponível'}")
                        with col2:
                            if st.button("🗑️ Excluir", key=f"del_prod_{produto.id}"):
                                session.delete(produto)
                                session.commit()
                                st.success("Produto excluído!")
                                st.rerun()

            if st.session_state.get("modal_novo_produto"):
                with st.form("form_novo_produto"):
                    st.subheader("➕ Novo Produto")
                    nome = st.text_input("Nome *")
                    descricao = st.text_area("Descrição")
                    col1, col2 = st.columns(2)
                    with col1:
                        categoria_id = st.selectbox("Categoria *", [(c.id, f"{c.icone or ''} {c.nome}") for c in categorias_filtro], format_func=lambda x: x[1])[0]
                        preco = st.number_input("Preço (R$)", min_value=0.0)
                    with col2:
                        disponivel = st.checkbox("Disponível", value=True)
                        destaque = st.checkbox("Produto em Destaque")
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.form_submit_button("✅ Salvar", use_container_width=True):
                            session.add(Produto(
                                restaurante_id=rest_id,
                                categoria_id=categoria_id,
                                nome=nome,
                                descricao=descricao,
                                preco=preco,
                                disponivel=disponivel,
                                destaque=destaque,
                                ordem_exibicao=0
                            ))
                            session.commit()
                            st.success("Produto criado!")
                            st.session_state.modal_novo_produto = False
                            st.rerun()
                    with col_btn2:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state.modal_novo_produto = False
                            st.rerun()

        with tabs[2]:
            st.subheader("🏷️ Produtos em Promoção")
            produtos_promocao = session.query(Produto).filter(Produto.restaurante_id == rest_id, Produto.promocao.is_(True)).all()
            if not produtos_promocao:
                st.info("Nenhum produto em promoção.")
            else:
                for produto in produtos_promocao:
                    with st.expander(f"🔥 {produto.nome}"):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**Preço Normal:** ~~R$ {produto.preco:.2f}~~")
                            st.markdown(f"**Preço Promocional:** R$ {produto.preco_promocional:.2f}")
                        with col2:
                            if st.button("❌ Remover Promoção", key=f"rem_promo_{produto.id}"):
                                produto.promocao = False
                                produto.preco_promocional = None
                                session.commit()
                                st.success("Promoção removida!")
                                st.rerun()
    finally:
        session.close()

# ==================== IMPRESSÃO E RELATÓRIOS ====================
def tela_impressao():
    st.title("🖨️ Impressão de Comandas")
    st.info("🚧 Sistema de impressão em desenvolvimento...")

def tela_relatorios():
    st.title("📊 Relatórios")
    st.info("🚧 Relatórios detalhados em desenvolvimento...")

# ==================== MAIN ====================
def main():
    # Sempre inicializar sessão primeiro - evita erro "SessionInfo antes de sua inicialização"
    try:
        verificar_login()
    except Exception:
        # Se houver qualquer erro na inicialização, reinicializar
        st.session_state.clear()
        verificar_login()

    # Verificação segura do estado de login
    if not st.session_state.get('restaurante_logado', False):
        tela_login()
    elif not is_session_valid():
        # Sessão inválida - mostrar login novamente
        st.warning("Sessão expirada. Por favor, faça login novamente.")
        fazer_logout()
        st.rerun()
    else:
        menu = renderizar_sidebar()

        if menu == "🏠 Dashboard":
            tela_dashboard()
        elif menu == "📦 Pedidos":
            tela_pedidos()
        elif menu == "🏍️ Motoboys":
            tela_motoboys()
        elif menu == "🍕 Gerenciar Cardápio":
            tela_gerenciar_cardapio()
        elif menu == "💰 Caixa":
            tela_caixa()
        elif menu == "⚙️ Configurações":
            tela_configuracoes()
        elif menu == "🖨️ Impressão":
            tela_impressao()
        elif menu == "📊 Relatórios":
            tela_relatorios()


def safe_main():
    """
    Wrapper seguro para main() que captura erros de SessionInfo do Streamlit.
    O erro 'Tentou usar SessionInfo antes de sua inicialização' ocorre quando
    a conexão WebSocket do Streamlit expira ou fica dessincronizada.
    """
    try:
        main()
    except Exception as e:
        error_msg = str(e).lower()
        # Detectar erro específico de SessionInfo
        if 'sessioninfo' in error_msg or 'formato de mensagem' in error_msg:
            # Limpar estado e mostrar mensagem amigável
            try:
                st.session_state.clear()
            except Exception:
                pass
            st.error("⚠️ Sessão expirada devido a inatividade. Por favor, recarregue a página.")
            st.info("💡 Dica: Clique em F5 ou no botão de recarregar do navegador.")
            st.stop()
        else:
            # Re-raise outros erros
            raise


if __name__ == "__main__":
    safe_main()