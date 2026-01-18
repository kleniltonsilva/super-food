"""
restaurante_app.py - Dashboard Principal do Restaurante
Sistema completo e integrado para gestão do restaurante
Versão 2.1 com Rotas Inteligentes - TOTALMENTE MIGRADADO PARA SQLAlchemy
Mantém 100% da lógica original, UI, fluxos e todas as funções existentes
Apenas o acesso ao banco foi substituído por SQLAlchemy (sem remoção de código)
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
    Pedido, Produto, Entrega, Caixa, MovimentacaoCaixa, Notificacao
)

from utils.mapbox_api import autocomplete_address, check_coverage_zone

try:
    from backend.app.utils.despacho import (
        despachar_pedidos_automatico, 
        atribuir_pedido_manual,
        calcular_capacidade_total_motoboys
    )
    DESPACHO_DISPONIVEL = True
except ImportError as e:
    print(f"⚠️ Módulo de despacho não disponível: {e}")
    DESPACHO_DISPONIVEL = False

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
    """Inicializa estado de sessão do restaurante"""
    if 'restaurante_logado' not in st.session_state:
        st.session_state.restaurante_logado = False
        st.session_state.restaurante_id = None
        st.session_state.restaurante_dados = None
        st.session_state.restaurante_config = None

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
    """Logout do restaurante"""
    st.session_state.restaurante_logado = False
    st.session_state.restaurante_id = None
    st.session_state.restaurante_dados = None
    st.session_state.restaurante_config = None

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
        
        # Debug (apenas em desenvolvimento)
        if os.getenv("DEBUG"):
            st.caption("🔧 Debug: teste@superfood.com / 123456")

# ==================== SIDEBAR ====================

def renderizar_sidebar():
    """Sidebar com menu e informações (lógica original preservada)"""
    with st.sidebar:
        rest = st.session_state.restaurante_dados
        config = st.session_state.restaurante_config
        
        st.title(f"🍕 {rest['nome_fantasia']}")
        st.caption(f"Plano: **{rest['plano'].upper()}**")
        
        if config and config.get('status_atual') == 'aberto':
            st.success("🟢 **ABERTO**")
        else:
            st.error("🔴 **FECHADO**")
        
        st.markdown("---")
        st.subheader("📋 Menu Principal")
        
        menu = st.radio(
            "Navegação",
            [
                "🏠 Dashboard",
                "📦 Pedidos",
                "🏍️ Motoboys",
                "💰 Caixa",
                "⚙️ Configurações",
                "🖨️ Impressão",
                "📊 Relatórios"
            ],
            key="menu_principal"
        )
        
        st.markdown("---")
        
        session = get_db_session()
        try:
            notificacoes = session.query(Notificacao).filter(
                Notificacao.restaurante_id == st.session_state.restaurante_id,
                Notificacao.lida == False
            ).count()
            if notificacoes > 0:
                st.warning(f"🔔 {notificacoes} notificação(ões)")
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
                    st.session_state.menu_principal = "💰 Caixa"
                    st.rerun()
        
        with col3:
            if st.button("📦 Criar Pedido", use_container_width=True):
                st.session_state.menu_principal = "📦 Pedidos"
                st.rerun()
        
        with col4:
            solicitacoes = session.query(MotoboySolicitacao).filter(
                MotoboySolicitacao.restaurante_id == rest_id,
                MotoboySolicitacao.status == 'pendente'
            ).count()
            if solicitacoes > 0:
                if st.button(f"🔔 {solicitacoes} Solicitações", use_container_width=True, type="primary"):
                    st.session_state.menu_principal = "🏍️ Motoboys"
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
    """Criação de pedido manual - lógica original completa com autocomplete"""
    st.subheader("➕ Criar Novo Pedido")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        # Próxima comanda
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
            
            if tipo_pedido == "Entrega":
                st.markdown("### 📍 Endereço de Entrega")
                endereco_busca = st.text_input("Digite o endereço", placeholder="Ex: Rua Augusta, 123, São Paulo, SP")
                if endereco_busca and len(endereco_busca) > 5:
                    rest = session.query(Restaurante).get(rest_id)
                    proximity = (rest.latitude, rest.longitude) if rest and rest.latitude else None
                    sugestoes = autocomplete_address(endereco_busca, proximity)
                    if sugestoes:
                        opcoes = [s['place_name'] for s in sugestoes]
                        endereco_selecionado = st.selectbox("Selecione o endereço correto:", opcoes)
                        for sug in sugestoes:
                            if sug['place_name'] == endereco_selecionado:
                                endereco_entrega = sug['place_name']
                                lat_cliente, lon_cliente = sug['coordinates']
                                validado_mapbox = True
                                config = session.query(ConfigRestaurante).filter(ConfigRestaurante.restaurante_id == rest_id).first()
                                resultado_zona = check_coverage_zone(
                                    (rest.latitude, rest.longitude),
                                    (lat_cliente, lon_cliente),
                                    config.raio_entrega_km if config else 10.0
                                )
                                if resultado_zona['dentro_zona']:
                                    st.success(resultado_zona['mensagem'])
                                else:
                                    st.error(resultado_zona['mensagem'])
                                    validado_mapbox = False
                                break
                    else:
                        st.warning("Nenhuma sugestão encontrada")
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
                        valor_total=valor_total,
                        observacoes=observacoes,
                        tempo_estimado=tempo_estimado,
                        validado_mapbox=validado_mapbox,
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
    """Lista pedidos ativos com despacho automático - lógica original completa"""
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
    """Histórico completo - lógica original mantida"""
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
        
        # Métricas
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
        ).order_by(Motoboy.nome).all()
        
        if not motoboys:
            st.info("Nenhum motoboy ativo.")
            return
        
        for motoboy in motoboys:
            with st.expander(f"🏍️ {motoboy.nome} - {motoboy.usuario}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Telefone:** {motoboy.telefone}")
                    st.markdown(f"**Capacidade:** {motoboy.capacidade_entregas}")
                    st.markdown(f"**Cadastro:** {motoboy.data_cadastro.strftime('%d/%m/%Y') if motoboy.data_cadastro else 'N/A'}")
                with col2:
                    st.markdown(f"**Total Entregas:** {motoboy.total_entregas}")
                    st.markdown(f"**Ganhos Totais:** R$ {motoboy.total_ganhos:.2f}")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("❌ Desativar", key=f"desativar_{motoboy.id}"):
                        motoboy.status = 'inativo'
                        session.commit()
                        st.success("Motoboy desativado!")
                        st.rerun()
                with col_btn2:
                    if st.button("🔄 Redefinir Senha", key=f"reset_senha_{motoboy.id}"):
                        motoboy.senha = hashlib.sha256("123456".encode()).hexdigest()
                        session.commit()
                        st.success("Senha redefinida para 123456")
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
                    # Verifica se usuário já existe
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
    tabs = st.tabs(["🕐 Horários", "📍 Endereço", "💰 Taxas", "🔗 Integrações", "🔐 Segurança"])
    
    rest_id = st.session_state.restaurante_id
    session = get_db_session()
    try:
        config = session.query(ConfigRestaurante).filter(ConfigRestaurante.restaurante_id == rest_id).first()
        
        with tabs[0]:
            st.subheader("🕐 Horários de Funcionamento")
            with st.form("form_horarios"):
                col1, col2 = st.columns(2)
                with col1:
                    abertura = st.time_input("Horário de Abertura", value=datetime.strptime(config.horario_abertura, '%H:%M').time())
                with col2:
                    fechamento = st.time_input("Horário de Fechamento", value=datetime.strptime(config.horario_fechamento, '%H:%M').time())
                dias = st.multiselect("Dias Abertos", ['segunda','terca','quarta','quinta','sexta','sabado','domingo'],
                                      default=config.dias_semana_abertos.split(','))
                if st.form_submit_button("💾 Salvar Horários"):
                    config.horario_abertura = abertura.strftime('%H:%M')
                    config.horario_fechamento = fechamento.strftime('%H:%M')
                    config.dias_semana_abertos = ','.join(dias)
                    session.commit()
                    st.success("Horários salvos!")
                    st.rerun()
        
        with tabs[1]:
            st.subheader("📍 Endereço do Restaurante")
            rest = session.query(Restaurante).get(rest_id)
            st.info("Alterar o endereço pode afetar o cálculo de distâncias")
            novo_endereco = st.text_area("Endereço Completo", value=rest.endereco_completo, height=150)
            if st.button("💾 Atualizar Endereço"):
                rest.endereco_completo = novo_endereco
                session.commit()
                st.success("Endereço atualizado!")
                st.rerun()
        
        with tabs[2]:
            st.subheader("💰 Taxas e Configurações de Entrega")
            with st.form("form_taxas"):
                col1, col2 = st.columns(2)
                with col1:
                    taxa_diaria = st.number_input("Taxa Diária Motoboy", value=config.taxa_diaria, step=5.0)
                    taxa_entrega_base = st.number_input("Taxa Entrega Base", value=config.taxa_entrega_base, step=1.0)
                    distancia_base = st.number_input("Distância Base (km)", value=config.distancia_base_km, step=0.5)
                with col2:
                    taxa_km_extra = st.number_input("Taxa por km Extra", value=config.taxa_km_extra, step=0.1)
                    valor_km = st.number_input("Valor por km (motoboy)", value=config.valor_km, step=0.1)
                    raio_entrega = st.number_input("Raio de Entrega (km)", value=config.raio_entrega_km, step=1.0)
                
                despacho_auto = st.checkbox("Despacho Automático", value=config.despacho_automatico)
                modo_despacho = st.selectbox("Modo de Despacho", ["auto_economico", "auto_rapido", "manual"], index=["auto_economico", "auto_rapido", "manual"].index(config.modo_despacho))
                
                if st.form_submit_button("💾 Salvar Taxas"):
                    config.taxa_diaria = taxa_diaria
                    config.taxa_entrega_base = taxa_entrega_base
                    config.distancia_base_km = distancia_base
                    config.taxa_km_extra = taxa_km_extra
                    config.valor_km = valor_km
                    config.raio_entrega_km = raio_entrega
                    config.despacho_automatico = despacho_auto
                    config.modo_despacho = modo_despacho
                    session.commit()
                    st.success("Configurações salvas!")
                    st.rerun()
        
        with tabs[3]:
            st.info("🚧 Integrações em desenvolvimento...")
        with tabs[4]:
            st.subheader("🔐 Alterar Senha do Restaurante")
            with st.form("form_senha"):
                senha_atual = st.text_input("Senha Atual", type="password")
                nova_senha = st.text_input("Nova Senha", type="password")
                confirmar = st.text_input("Confirmar Nova Senha", type="password")
                if st.form_submit_button("🔑 Alterar Senha"):
                    if nova_senha != confirmar:
                        st.error("Senhas não coincidem")
                    elif not senha_atual or not nova_senha:
                        st.error("Preencha todos os campos")
                    else:
                        rest = session.query(Restaurante).get(rest_id)
                        if rest.verificar_senha(senha_atual):
                            rest.set_senha(nova_senha)
                            session.commit()
                            st.success("Senha alterada com sucesso!")
                            st.rerun()
                        else:
                            st.error("Senha atual incorreta")
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
    verificar_login()
    
    if not st.session_state.restaurante_logado:
        tela_login()
    else:
        menu = renderizar_sidebar()
        
        if menu == "🏠 Dashboard":
            tela_dashboard()
        elif menu == "📦 Pedidos":
            tela_pedidos()
        elif menu == "🏍️ Motoboys":
            tela_motoboys()
        elif menu == "💰 Caixa":
            tela_caixa()
        elif menu == "⚙️ Configurações":
            tela_configuracoes()
        elif menu == "🖨️ Impressão":
            tela_impressao()
        elif menu == "📊 Relatórios":
            tela_relatorios()

if __name__ == "__main__":
    main()