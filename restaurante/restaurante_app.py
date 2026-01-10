"""
restaurante_app.py - Dashboard Principal do Restaurante
Sistema completo e integrado para gestão do restaurante
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Adicionar pasta raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database import get_db

# Configuração da página
st.set_page_config(
    page_title="Dashboard Restaurante - Super Food",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== AUTENTICAÇÃO ====================

def verificar_login():
    """Verifica se restaurante está logado"""
    if 'restaurante_logado' not in st.session_state:
        st.session_state.restaurante_logado = False
        st.session_state.restaurante_id = None
        st.session_state.restaurante_dados = None

def fazer_login(email: str, senha: str) -> bool:
    """Faz login do restaurante"""
    db = get_db()
    restaurante = db.verificar_login_restaurante(email, senha)
    
    if restaurante:
        st.session_state.restaurante_logado = True
        st.session_state.restaurante_id = restaurante['id']
        st.session_state.restaurante_dados = restaurante
        
        # Buscar configurações
        config = db.buscar_config_restaurante(restaurante['id'])
        st.session_state.restaurante_config = config
        
        return True
    return False

def fazer_logout():
    """Faz logout do restaurante"""
    st.session_state.restaurante_logado = False
    st.session_state.restaurante_id = None
    st.session_state.restaurante_dados = None
    st.session_state.restaurante_config = None

# ==================== TELA DE LOGIN ====================

def tela_login():
    """Interface de login do restaurante"""
    st.title("🍕 Super Food - Login Restaurante")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Acesse seu Dashboard")
        
        with st.form("form_login"):
            email = st.text_input(
                "Email",
                placeholder="seu@email.com"
            )
            senha = st.text_input(
                "Senha",
                type="password",
                placeholder="Sua senha"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")
            
            with col_btn2:
                if st.form_submit_button("❓ Esqueci a Senha", use_container_width=True):
                    st.info("Entre em contato com o Super Admin para recuperar sua senha.")
            
            if submit:
                if not email or not senha:
                    st.error("❌ Preencha todos os campos!")
                elif fazer_login(email, senha):
                    st.success("✅ Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Email ou senha incorretos!")
        
        st.markdown("---")
        st.info("💡 **Primeiro Acesso?** Entre em contato com o Super Admin para criar sua conta.")

# ==================== SIDEBAR ====================

def renderizar_sidebar():
    """Renderiza menu lateral"""
    with st.sidebar:
        # Informações do restaurante
        rest = st.session_state.restaurante_dados
        config = st.session_state.restaurante_config
        
        st.title(f"🍕 {rest['nome_fantasia']}")
        st.caption(f"Plano: **{rest['plano'].upper()}**")
        
        # Status do restaurante
        status_atual = config['status_atual']
        
        if status_atual == 'aberto':
            st.success("🟢 **ABERTO**")
        else:
            st.error("🔴 **FECHADO**")
        
        st.markdown("---")
        
        # Menu principal
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
        
        # Notificações
        db = get_db()
        notificacoes = db.listar_notificacoes(
            restaurante_id=st.session_state.restaurante_id,
            apenas_nao_lidas=True
        )
        
        if notificacoes:
            st.warning(f"🔔 {len(notificacoes)} notificação(ões)")
        
        st.markdown("---")
        
        # Botão de logout
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()
            st.rerun()
        
        # Informações adicionais
        st.caption(f"Código de Acesso: **{rest['codigo_acesso']}**")
        st.caption(f"Vencimento: {rest['data_vencimento'][:10]}")
        
        return menu

# ==================== DASHBOARD ====================

def tela_dashboard():
    """Dashboard principal com métricas e visão geral"""
    st.title("🏠 Dashboard")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    # Buscar dados
    config = db.buscar_config_restaurante(rest_id)
    pedidos_hoje = db.listar_pedidos(rest_id)
    pedidos_hoje = [p for p in pedidos_hoje if p['data_criacao'][:10] == datetime.now().strftime('%Y-%m-%d')]
    motoboys = db.listar_motoboys(rest_id)
    solicitacoes = db.listar_solicitacoes_pendentes(rest_id)
    caixa = db.buscar_caixa_aberto(rest_id)
    
    # Métricas superiores
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Pedidos Hoje", len(pedidos_hoje))
    
    with col2:
        pedidos_pendentes = [p for p in pedidos_hoje if p['status'] in ['pendente', 'em_preparo']]
        st.metric("Pedidos Pendentes", len(pedidos_pendentes))
    
    with col3:
        st.metric("Motoboys Ativos", len(motoboys))
    
    with col4:
        if caixa:
            st.metric("Caixa", "🟢 ABERTO")
        else:
            st.metric("Caixa", "🔴 FECHADO")
    
    st.markdown("---")
    
    # Controles rápidos
    st.subheader("⚡ Controles Rápidos")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if config['status_atual'] == 'fechado':
            if st.button("🟢 Abrir Restaurante", use_container_width=True, type="primary"):
                if db.abrir_restaurante(rest_id):
                    st.success("Restaurante aberto!")
                    st.rerun()
        else:
            if st.button("🔴 Fechar Restaurante", use_container_width=True):
                if db.fechar_restaurante(rest_id):
                    st.success("Restaurante fechado!")
                    st.rerun()
    
    with col2:
        if not caixa:
            if st.button("💰 Abrir Caixa", use_container_width=True):
                st.session_state.abrir_caixa_modal = True
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
        if solicitacoes:
            if st.button(f"🔔 {len(solicitacoes)} Solicitações", use_container_width=True, type="primary"):
                st.session_state.menu_principal = "🏍️ Motoboys"
                st.rerun()
    
    # Modal de abertura de caixa
    if st.session_state.get('abrir_caixa_modal'):
        modal_abrir_caixa()
    
    st.markdown("---")
    
    # Pedidos recentes
    st.subheader("📦 Últimos Pedidos")
    
    if pedidos_hoje:
        for pedido in pedidos_hoje[:5]:
            with st.expander(f"Comanda #{pedido['comanda']} - {pedido['cliente_nome']} - {pedido['status'].upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Tipo:** {pedido['tipo']}")
                    st.markdown(f"**Cliente:** {pedido['cliente_nome']}")
                    st.markdown(f"**Telefone:** {pedido['cliente_telefone']}")
                
                with col2:
                    st.markdown(f"**Status:** {pedido['status']}")
                    st.markdown(f"**Horário:** {pedido['data_criacao']}")
                    st.markdown(f"**Tempo Estimado:** {pedido['tempo_estimado']} min")
                
                st.markdown(f"**Itens:** {pedido['itens']}")
    else:
        st.info("Nenhum pedido hoje.")
    
    st.markdown("---")
    
    # Notificações
    st.subheader("🔔 Notificações")
    
    notificacoes = db.listar_notificacoes(restaurante_id=rest_id, apenas_nao_lidas=True)
    
    if notificacoes:
        for notif in notificacoes[:5]:
            with st.container():
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{notif['titulo']}**")
                    st.caption(notif['mensagem'])
                
                with col2:
                    if st.button("✅", key=f"marcar_lida_{notif['id']}"):
                        db.marcar_notificacao_lida(notif['id'])
                        st.rerun()
    else:
        st.info("Nenhuma notificação pendente.")

def modal_abrir_caixa():
    """Modal para abrir caixa"""
    with st.form("form_abrir_caixa"):
        st.subheader("💰 Abrir Caixa")
        
        valor_abertura = st.number_input(
            "Valor de Abertura (Troco)",
            min_value=0.0,
            value=100.0,
            step=10.0,
            format="%.2f"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("✅ Abrir Caixa", use_container_width=True):
                db = get_db()
                sucesso, msg, _ = db.abrir_caixa(
                    st.session_state.restaurante_id,
                    st.session_state.restaurante_dados['email'],
                    valor_abertura
                )
                
                if sucesso:
                    st.success(msg)
                    st.session_state.abrir_caixa_modal = False
                    st.rerun()
                else:
                    st.error(msg)
        
        with col2:
            if st.form_submit_button("❌ Cancelar", use_container_width=True):
                st.session_state.abrir_caixa_modal = False
                st.rerun()

# ==================== PEDIDOS ====================

def tela_pedidos():
    """Tela de gerenciamento de pedidos"""
    st.title("📦 Gerenciamento de Pedidos")
    
    tabs = st.tabs(["➕ Criar Pedido", "📋 Pedidos Ativos", "📜 Histórico"])
    
    with tabs[0]:
        criar_pedido_manual()
    
    with tabs[1]:
        listar_pedidos_ativos()
    
    with tabs[2]:
        historico_pedidos()

def criar_pedido_manual():
    """Interface para criar pedido manualmente"""
    st.subheader("➕ Criar Novo Pedido")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    # Gerar próxima comanda
    pedidos = db.listar_pedidos(rest_id)
    if pedidos:
        comandas = [int(p['comanda']) for p in pedidos if p['comanda'].isdigit()]
        proxima_comanda = str(max(comandas) + 1) if comandas else "1"
    else:
        proxima_comanda = "1"
    
    with st.form("form_criar_pedido"):
        col1, col2 = st.columns(2)
        
        with col1:
            tipo_pedido = st.selectbox(
                "Tipo de Pedido *",
                ["Entrega", "Retirada na loja", "Para mesa"]
            )
        
        with col2:
            st.text_input("Comanda", value=proxima_comanda, disabled=True)
        
        # Dados do cliente
        st.markdown("### 👤 Dados do Cliente")
        
        col1, col2 = st.columns(2)
        
        with col1:
            cliente_nome = st.text_input("Nome do Cliente *")
        
        with col2:
            cliente_telefone = st.text_input("Telefone/WhatsApp")
        
        # Campos específicos por tipo
        endereco_entrega = ""
        numero_mesa = ""
        
        if tipo_pedido == "Entrega":
            endereco_entrega = st.text_area("Endereço Completo de Entrega *")
        elif tipo_pedido == "Para mesa":
            numero_mesa = st.text_input("Número da Mesa *")
        
        # Itens do pedido
        st.markdown("### 🍕 Itens do Pedido")
        
        itens = st.text_area(
            "Descreva os itens *",
            placeholder="Ex: 1x Pizza Grande Calabresa\n2x Refrigerante Lata\n1x Batata Frita"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            valor_total = st.number_input("Valor Total (R$)", min_value=0.0, value=0.0, step=1.0)
        
        with col2:
            tempo_estimado = st.number_input(
                "Tempo Estimado (minutos)",
                min_value=5,
                value=45 if tipo_pedido == "Entrega" else 30,
                step=5
            )
        
        observacoes = st.text_area("Observações")
        
        st.markdown("---")
        
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
        
        with col_btn2:
            submit = st.form_submit_button("✅ Criar Pedido", use_container_width=True, type="primary")
        
        if submit:
            # Validações
            erros = []
            
            if not cliente_nome or not itens:
                erros.append("Nome do cliente e itens são obrigatórios")
            
            if tipo_pedido == "Entrega" and not endereco_entrega:
                erros.append("Endereço é obrigatório para entrega")
            
            if tipo_pedido == "Para mesa" and not numero_mesa:
                erros.append("Número da mesa é obrigatório")
            
            if erros:
                for erro in erros:
                    st.error(f"❌ {erro}")
            else:
                # Criar pedido
                dados = {
                    'restaurante_id': rest_id,
                    'comanda': proxima_comanda,
                    'tipo': tipo_pedido,
                    'cliente_nome': cliente_nome,
                    'cliente_telefone': cliente_telefone,
                    'endereco_entrega': endereco_entrega,
                    'numero_mesa': numero_mesa,
                    'itens': itens,
                    'valor_total': valor_total,
                    'observacoes': observacoes,
                    'tempo_estimado': tempo_estimado,
                    'origem': 'manual'
                }
                
                sucesso, msg, pedido_id = db.criar_pedido(dados)
                
                if sucesso:
                    st.success(f"✅ {msg}")
                    st.balloons()
                    
                    # Se for entrega, perguntar sobre despacho
                    if tipo_pedido == "Entrega":
                        st.info("📤 Pedido de entrega criado! Vá para a aba 'Pedidos Ativos' para despachar.")
                    
                    # Registrar no caixa se estiver aberto
                    caixa = db.buscar_caixa_aberto(rest_id)
                    if caixa and valor_total > 0:
                        st.info("💰 Não esqueça de registrar o pagamento no caixa!")
                    
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")

def listar_pedidos_ativos():
    """Lista pedidos em andamento"""
    st.subheader("📋 Pedidos Ativos")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    pedidos = db.listar_pedidos(rest_id)
    pedidos_ativos = [p for p in pedidos if p['status'] not in ['finalizado', 'cancelado', 'entregue']]
    
    if not pedidos_ativos:
        st.info("Nenhum pedido ativo no momento.")
        return
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_tipo = st.selectbox("Tipo", ["Todos", "Entrega", "Retirada na loja", "Para mesa"])
    
    with col2:
        filtro_status = st.selectbox("Status", ["Todos", "pendente", "em_preparo", "pronto", "em_entrega"])
    
    # Aplicar filtros
    if filtro_tipo != "Todos":
        pedidos_ativos = [p for p in pedidos_ativos if p['tipo'] == filtro_tipo]
    
    if filtro_status != "Todos":
        pedidos_ativos = [p for p in pedidos_ativos if p['status'] == filtro_status]
    
    st.markdown(f"**{len(pedidos_ativos)} pedido(s) encontrado(s)**")
    st.markdown("---")
    
    # Listar pedidos
    for pedido in pedidos_ativos:
        with st.expander(f"🍕 Comanda #{pedido['comanda']} - {pedido['cliente_nome']} - {pedido['status'].upper()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Tipo:** {pedido['tipo']}")
                st.markdown(f"**Cliente:** {pedido['cliente_nome']}")
                st.markdown(f"**Telefone:** {pedido['cliente_telefone']}")
                
                if pedido['tipo'] == "Entrega":
                    st.markdown(f"**Endereço:** {pedido['endereco_entrega']}")
                elif pedido['tipo'] == "Para mesa":
                    st.markdown(f"**Mesa:** {pedido['numero_mesa']}")
            
            with col2:
                st.markdown(f"**Status:** {pedido['status']}")
                st.markdown(f"**Horário:** {pedido['data_criacao']}")
                st.markdown(f"**Tempo Estimado:** {pedido['tempo_estimado']} min")
                st.markdown(f"**Valor:** R$ {pedido['valor_total']:.2f}")
            
            st.markdown(f"**Itens:**")
            st.text(pedido['itens'])
            
            if pedido['observacoes']:
                st.markdown(f"**Observações:** {pedido['observacoes']}")
            
            st.markdown("---")
            
            # Ações
            col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
            
            with col_btn1:
                if pedido['status'] == 'pendente':
                    if st.button("👨‍🍳 Iniciar Preparo", key=f"preparo_{pedido['id']}"):
                        db.atualizar_status_pedido(pedido['id'], 'em_preparo')
                        st.success("Pedido em preparo!")
                        st.rerun()
            
            with col_btn2:
                if pedido['status'] == 'em_preparo':
                    if st.button("✅ Pedido Pronto", key=f"pronto_{pedido['id']}"):
                        db.atualizar_status_pedido(pedido['id'], 'pronto')
                        st.success("Pedido pronto!")
                        st.rerun()
            
            with col_btn3:
                if pedido['tipo'] == "Entrega" and pedido['status'] == 'pronto' and not pedido['despachado']:
                    if st.button("📤 Despachar", key=f"despachar_{pedido['id']}"):
                        st.info("Função de despacho será implementada!")
            
            with col_btn4:
                if st.button("❌ Cancelar", key=f"cancelar_{pedido['id']}"):
                    db.atualizar_status_pedido(pedido['id'], 'cancelado')
                    st.warning("Pedido cancelado!")
                    st.rerun()

def historico_pedidos():
    """Histórico completo de pedidos"""
    st.subheader("📜 Histórico de Pedidos")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    pedidos = db.listar_pedidos(rest_id)
    
    if not pedidos:
        st.info("Nenhum pedido registrado.")
        return
    
    # Converter para DataFrame
    df = pd.DataFrame(pedidos)
    
    # Filtros
    col1, col2 = st.columns(2)
    
    with col1:
        data_inicio = st.date_input("Data Início", value=datetime.now() - timedelta(days=7))
    
    with col2:
        data_fim = st.date_input("Data Fim", value=datetime.now())
    
    # Aplicar filtro de data
    df['data'] = pd.to_datetime(df['data_criacao']).dt.date
    df_filtrado = df[(df['data'] >= data_inicio) & (df['data'] <= data_fim)]
    
    st.markdown(f"**{len(df_filtrado)} pedido(s) no período**")
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Pedidos", len(df_filtrado))
    
    with col2:
        total_vendas = df_filtrado['valor_total'].sum()
        st.metric("Total em Vendas", f"R$ {total_vendas:.2f}")
    
    with col3:
        ticket_medio = total_vendas / len(df_filtrado) if len(df_filtrado) > 0 else 0
        st.metric("Ticket Médio", f"R$ {ticket_medio:.2f}")
    
    with col4:
        entregas = len(df_filtrado[df_filtrado['tipo'] == 'Entrega'])
        st.metric("Entregas", entregas)
    
    st.markdown("---")
    
    # Tabela
    st.dataframe(
        df_filtrado[['comanda', 'tipo', 'cliente_nome', 'status', 'valor_total', 'data_criacao']],
        use_container_width=True
    )

# ==================== MOTOBOYS ====================

def tela_motoboys():
    """Tela de gerenciamento de motoboys"""
    st.title("🏍️ Gerenciamento de Motoboys")
    
    tabs = st.tabs([
        "👥 Motoboys Ativos",
        "📥 Solicitações Pendentes",
        "⚙️ Configurações Logística",
        "💰 Configurar Pagamentos",
        "💵 Pagar Motoboys",
        "🏆 Ranking"
    ])
    
    with tabs[0]:
        listar_motoboys_ativos()
    
    with tabs[1]:
        listar_solicitacoes()
    
    with tabs[2]:
        configurar_logistica()
    
    with tabs[3]:
        configurar_pagamentos()
    
    with tabs[4]:
        pagar_motoboys()
    
    with tabs[5]:
        ranking_motoboys()

def listar_motoboys_ativos():
    """Lista motoboys aprovados e ativos"""
    st.subheader("👥 Motoboys Ativos")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    rest = st.session_state.restaurante_dados
    
    motoboys = db.listar_motoboys(rest_id)
    
    st.markdown(f"**{len(motoboys)} / {rest['limite_motoboys']} motoboys cadastrados**")
    
    if not motoboys:
        st.info("Nenhum motoboy cadastrado ainda.")
        return
    
    for motoboy in motoboys:
        with st.expander(f"🏍️ {motoboy['nome']} - {motoboy['status'].upper()}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**Usuário:** {motoboy['usuario']}")
                st.markdown(f"**Telefone:** {motoboy['telefone']}")
                st.markdown(f"**Status:** {motoboy['status']}")
            
            with col2:
                st.markdown(f"**Total Entregas:** {motoboy['total_entregas']}")
                st.markdown(f"**Total Ganhos:** R$ {motoboy['total_ganhos']:.2f}")
                st.markdown(f"**Data Cadastro:** {motoboy['data_cadastro'][:10]}")
            
            if st.button(f"❌ Excluir Motoboy", key=f"excluir_{motoboy['id']}"):
                sucesso, msg = db.excluir_motoboy(motoboy['id'])
                if sucesso:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

def listar_solicitacoes():
    """Lista e gerencia solicitações de cadastro"""
    st.subheader("📥 Solicitações Pendentes")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    solicitacoes = db.listar_solicitacoes_pendentes(rest_id)
    
    if not solicitacoes:
        st.info("Nenhuma solicitação pendente.")
        return
    
    st.markdown(f"**{len(solicitacoes)} solicitação(ões) aguardando aprovação**")
    
    for sol in solicitacoes:
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"### 👤 {sol['nome']}")
                st.markdown(f"**Usuário:** {sol['usuario']}")
                st.markdown(f"**Telefone:** {sol['telefone']}")
                st.caption(f"Solicitado em: {sol['data_solicitacao']}")
            
            with col2:
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("✅", key=f"aprovar_{sol['id']}", help="Aprovar"):
                        sucesso, msg = db.aprovar_motoboy(sol['id'])
                        if sucesso:
                            st.success(msg)
                            # Criar notificação
                            db.criar_notificacao(
                                tipo='aprovacao',
                                titulo='Cadastro Aprovado!',
                                mensagem=f'Seu cadastro foi aprovado! Senha: 123456',
                                motoboy_id=sol['id']
                            )
                            st.rerun()
                        else:
                            st.error(msg)
                
                with col_btn2:
                    if st.button("❌", key=f"recusar_{sol['id']}", help="Recusar"):
                        sucesso, msg = db.recusar_motoboy(sol['id'], "Recusado pelo restaurante")
                        if sucesso:
                            st.warning(msg)
                            st.rerun()
                        else:
                            st.error(msg)
            
            st.markdown("---")

def configurar_logistica():
    """Configura modo de despacho de pedidos"""
    st.subheader("⚙️ Configurações de Logística de Entrega")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    config = db.buscar_config_restaurante(rest_id)
    
    st.markdown("""
    ### 📦 Modos de Despacho
    
    Escolha como os pedidos serão distribuídos para os motoboys:
    """)
    
    modo_atual = config['modo_despacho']
    
    modo = st.radio(
        "Selecione o Modo",
        [
            "auto_economico",
            "manual",
            "auto_ordem"
        ],
        index=0 if modo_atual == "auto_economico" else 1 if modo_atual == "manual" else 2,
        format_func=lambda x: {
            "auto_economico": "🧠 Automático Inteligente (Econômico)",
            "manual": "✋ Manual (Selecionar motoboy)",
            "auto_ordem": "⏰ Automático por Ordem de Saída"
        }[x]
    )
    
    st.markdown("---")
    
    # Explicação de cada modo
    if modo == "auto_economico":
        st.success("""
        ### 🧠 Modo Automático Inteligente (Econômico)
        
        O sistema cria **rotas otimizadas** para economizar tempo e combustível:
        - Agrupa pedidos próximos para o mesmo motoboy
        - Calcula a melhor ordem de entrega
        - Ignora a ordem de saída dos pedidos
        - Prioriza eficiência
        """)
    
    elif modo == "manual":
        st.info("""
        ### ✋ Modo Manual
        
        Você escolhe **manualmente** qual motoboy vai entregar cada pedido:
        - Total controle sobre as atribuições
        - Pode escolher baseado em preferências
        - Requer mais atenção
        """)
    
    else:
        st.warning("""
        ### ⏰ Modo Automático por Ordem de Saída
        
        O sistema despacha **automaticamente** baseado no horário:
        - Prioriza pedidos que saíram primeiro
        - Distribui entre motoboys disponíveis
        - Mantém ordem cronológica
        """)
    
    if st.button("💾 Salvar Configuração", use_container_width=True, type="primary"):
        if db.atualizar_config_restaurante(rest_id, {'modo_despacho': modo}):
            st.success("✅ Configuração salva!")
            st.rerun()

def configurar_pagamentos():
    """Configura valores de pagamento dos motoboys"""
    st.subheader("💰 Configurações de Pagamento dos Motoboys")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    config = db.buscar_config_restaurante(rest_id)
    
    st.markdown("""
    Configure os valores que serão usados para calcular o pagamento dos motoboys:
    """)
    
    with st.form("form_config_pagamentos"):
        col1, col2 = st.columns(2)
        
        with col1:
            taxa_diaria = st.number_input(
                "Taxa Diária (R$)",
                min_value=0.0,
                value=config['taxa_diaria'],
                step=5.0,
                help="Valor fixo pago por dia de trabalho"
            )
            
            valor_lanche = st.number_input(
                "Valor do Lanche (R$)",
                min_value=0.0,
                value=config['valor_lanche'],
                step=1.0,
                help="Auxílio alimentação"
            )
            
            taxa_entrega_base = st.number_input(
                "Taxa de Entrega Base (R$)",
                min_value=0.0,
                value=config['taxa_entrega_base'],
                step=0.5,
                help="Valor base por entrega (até a distância limite)"
            )
        
        with col2:
            distancia_base_km = st.number_input(
                "Distância Base (km)",
                min_value=0.0,
                value=config['distancia_base_km'],
                step=0.5,
                help="Até quantos km vale a taxa base"
            )
            
            taxa_km_extra = st.number_input(
                "Taxa por KM Extra (R$)",
                min_value=0.0,
                value=config['taxa_km_extra'],
                step=0.1,
                help="Valor adicional por km acima da distância base"
            )
            
            valor_km = st.number_input(
                "Valor por KM (R$)",
                min_value=0.0,
                value=config['valor_km'],
                step=0.1,
                help="Valor usado para cálculos gerais de distância"
            )
        
        st.markdown("---")
        
        st.markdown("""
        ### 💡 Exemplo de Cálculo
        
        Para uma entrega de **6 km**:
        - Taxa Base: R$ {:.2f} (até {} km)
        - Distância Extra: {} km
        - Taxa Extra: {} km × R$ {:.2f} = R$ {:.2f}
        - **Total da Entrega: R$ {:.2f}**
        
        Ganho do dia:
        - Taxa Diária: R$ {:.2f}
        - Valor Lanche: R$ {:.2f}
        - Total Entregas: R$ (soma de todas)
        """.format(
            taxa_entrega_base, distancia_base_km,
            max(0, 6 - distancia_base_km),
            max(0, 6 - distancia_base_km), taxa_km_extra,
            max(0, 6 - distancia_base_km) * taxa_km_extra,
            taxa_entrega_base + (max(0, 6 - distancia_base_km) * taxa_km_extra),
            taxa_diaria, valor_lanche
        ))
        
        if st.form_submit_button("💾 Salvar Configurações", use_container_width=True, type="primary"):
            dados = {
                'taxa_diaria': taxa_diaria,
                'valor_lanche': valor_lanche,
                'taxa_entrega_base': taxa_entrega_base,
                'distancia_base_km': distancia_base_km,
                'taxa_km_extra': taxa_km_extra,
                'valor_km': valor_km
            }
            
            if db.atualizar_config_restaurante(rest_id, dados):
                st.success("✅ Configurações salvas!")
                st.rerun()

def pagar_motoboys():
    """Interface para pagamento de motoboys"""
    st.subheader("💵 Pagar Motoboys")
    
    st.info("🚧 Funcionalidade em desenvolvimento...")
    
    # TODO: Implementar lógica de pagamento
    # - Listar motoboys com entregas pendentes de pagamento
    # - Calcular valor total a pagar
    # - Mostrar detalhamento (entregas, distâncias, valores)
    # - Botão para confirmar pagamento
    # - Registrar pagamento no banco

def ranking_motoboys():
    """Mostra ranking dos motoboys"""
    st.subheader("🏆 Ranking de Motoboys")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        ordem = st.selectbox(
            "Ordenar por",
            ["entregas", "ganhos", "velocidade"]
        )
    
    ranking = db.buscar_ranking_restaurante(rest_id, ordem)
    
    if not ranking:
        st.info("Nenhum dado de ranking disponível ainda.")
        return
    
    st.markdown("---")
    
    # Mostrar top 3 com destaque
    if len(ranking) >= 1:
        st.markdown("### 🥇 1º Lugar")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"**{ranking[0]['nome']}**")
        
        with col2:
            st.metric("Entregas", ranking[0]['total_entregas'])
        
        with col3:
            st.metric("Ganhos", f"R$ {ranking[0]['total_ganhos']:.2f}")
        
        with col4:
            tempo_medio = ranking[0].get('tempo_medio_entrega', 0)
            st.metric("Tempo Médio", f"{tempo_medio:.0f} min")
    
    if len(ranking) >= 2:
        st.markdown("### 🥈 2º Lugar")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"**{ranking[1]['nome']}**")
        
        with col2:
            st.metric("Entregas", ranking[1]['total_entregas'])
        
        with col3:
            st.metric("Ganhos", f"R$ {ranking[1]['total_ganhos']:.2f}")
        
        with col4:
            tempo_medio = ranking[1].get('tempo_medio_entrega', 0)
            st.metric("Tempo Médio", f"{tempo_medio:.0f} min")
    
    if len(ranking) >= 3:
        st.markdown("### 🥉 3º Lugar")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"**{ranking[2]['nome']}**")
        
        with col2:
            st.metric("Entregas", ranking[2]['total_entregas'])
        
        with col3:
            st.metric("Ganhos", f"R$ {ranking[2]['total_ganhos']:.2f}")
        
        with col4:
            tempo_medio = ranking[2].get('tempo_medio_entrega', 0)
            st.metric("Tempo Médio", f"{tempo_medio:.0f} min")
    
    st.markdown("---")
    
    # Tabela completa
    if len(ranking) > 3:
        st.markdown("### 📊 Ranking Completo")
        
        df_ranking = pd.DataFrame(ranking)
        df_ranking['posicao'] = range(1, len(df_ranking) + 1)
        
        st.dataframe(
            df_ranking[['posicao', 'nome', 'total_entregas', 'total_ganhos']],
            use_container_width=True
        )

# ==================== CAIXA ====================

def tela_caixa():
    """Tela de gerenciamento do caixa"""
    st.title("💰 Gerenciamento de Caixa")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    caixa = db.buscar_caixa_aberto(rest_id)
    
    if not caixa:
        st.warning("🔴 Caixa está FECHADO")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("form_abrir_caixa"):
                st.subheader("Abrir Caixa")
                
                valor_abertura = st.number_input(
                    "Valor de Abertura (Troco em R$)",
                    min_value=0.0,
                    value=100.0,
                    step=10.0
                )
                
                if st.form_submit_button("✅ Abrir Caixa", use_container_width=True, type="primary"):
                    sucesso, msg, _ = db.abrir_caixa(
                        rest_id,
                        st.session_state.restaurante_dados['email'],
                        valor_abertura
                    )
                    
                    if sucesso:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
    
    else:
        st.success("🟢 Caixa está ABERTO")
        
        # Métricas do caixa
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Valor Abertura", f"R$ {caixa['valor_abertura']:.2f}")
        
        with col2:
            st.metric("Total Vendas", f"R$ {caixa['total_vendas']:.2f}")
        
        with col3:
            st.metric("Retiradas", f"R$ {caixa['valor_retiradas']:.2f}")
        
        with col4:
            saldo_atual = caixa['valor_abertura'] + caixa['total_vendas'] - caixa['valor_retiradas']
            st.metric("Saldo Atual", f"R$ {saldo_atual:.2f}")
        
        st.markdown("---")
        
        # Tabs
        tabs = st.tabs(["💵 Fazer Retirada", "📜 Movimentações", "🔒 Fechar Caixa"])
        
        with tabs[0]:
            fazer_retirada(caixa)
        
        with tabs[1]:
            listar_movimentacoes(caixa)
        
        with tabs[2]:
            fechar_caixa_interface(caixa)

def fazer_retirada(caixa):
    """Interface para retirada de dinheiro"""
    st.subheader("💵 Fazer Retirada")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    
    with st.form("form_retirada"):
        valor = st.number_input(
            "Valor da Retirada (R$)",
            min_value=0.0,
            step=10.0
        )
        
        descricao = st.text_input("Descrição/Motivo")
        
        if st.form_submit_button("💸 Confirmar Retirada", use_container_width=True):
            if valor <= 0:
                st.error("Valor deve ser maior que zero!")
            elif not descricao:
                st.error("Descrição é obrigatória!")
            else:
                if db.registrar_retirada_caixa(
                    rest_id,
                    valor,
                    descricao,
                    st.session_state.restaurante_dados['email']
                ):
                    st.success("✅ Retirada registrada!")
                    st.rerun()
                else:
                    st.error("Erro ao registrar retirada!")

def listar_movimentacoes(caixa):
    """Lista movimentações do caixa"""
    st.subheader("📜 Movimentações do Caixa")
    
    db = get_db()
    movimentacoes = db.listar_movimentacoes_caixa(caixa['id'])
    
    if not movimentacoes:
        st.info("Nenhuma movimentação registrada.")
        return
    
    for mov in movimentacoes:
        tipo_icon = {
            'abertura': '🔓',
            'venda': '💰',
            'retirada': '💸',
            'fechamento': '🔒'
        }
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"{tipo_icon.get(mov['tipo'], '📝')} **{mov['tipo'].upper()}** - {mov['descricao']}")
                st.caption(mov['data_hora'])
            
            with col2:
                cor = 'green' if mov['tipo'] in ['abertura', 'venda'] else 'red'
                st.markdown(f"<h3 style='color: {cor};'>R$ {mov['valor']:.2f}</h3>", unsafe_allow_html=True)
            
            st.markdown("---")

def fechar_caixa_interface(caixa):
    """Interface para fechar o caixa"""
    st.subheader("🔒 Fechar Caixa")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    config = db.buscar_config_restaurante(rest_id)
    
    if config['status_atual'] != 'fechado':
        st.error("⚠️ O caixa só pode ser fechado quando o restaurante estiver FECHADO!")
        st.info("Vá para 'Configurações' e feche o restaurante primeiro.")
        return
    
    saldo_esperado = caixa['valor_abertura'] + caixa['total_vendas'] - caixa['valor_retiradas']
    
    st.markdown(f"""
    ### 📊 Resumo do Caixa
    
    - **Valor de Abertura:** R$ {caixa['valor_abertura']:.2f}
    - **Total em Vendas:** R$ {caixa['total_vendas']:.2f}
    - **Total em Retiradas:** R$ {caixa['valor_retiradas']:.2f}
    - **Saldo Esperado:** R$ {saldo_esperado:.2f}
    """)
    
    st.markdown("---")
    
    with st.form("form_fechar_caixa"):
        valor_contado = st.number_input(
            "Valor Contado no Caixa (R$)",
            min_value=0.0,
            value=saldo_esperado,
            step=1.0,
            help="Digite o valor real que está no caixa"
        )
        
        if st.form_submit_button("🔒 FECHAR CAIXA", use_container_width=True, type="primary"):
            sucesso, msg = db.fechar_caixa(
                rest_id,
                st.session_state.restaurante_dados['email'],
                valor_contado
            )
            
            if sucesso:
                st.success(msg)
                st.balloons()
                st.rerun()
            else:
                st.error(msg)

# ==================== CONFIGURAÇÕES ====================

def tela_configuracoes():
    """Tela de configurações gerais"""
    st.title("⚙️ Configurações")
    
    tabs = st.tabs(["🕐 Horários", "📍 Endereço", "🔗 Integrações", "🔐 Segurança"])
    
    with tabs[0]:
        configurar_horarios()
    
    with tabs[1]:
        configurar_endereco()
    
    with tabs[2]:
        configurar_integracoes()
    
    with tabs[3]:
        configurar_seguranca()

def configurar_horarios():
    """Configura horários de funcionamento"""
    st.subheader("🕐 Horários de Funcionamento")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    config = db.buscar_config_restaurante(rest_id)
    
    with st.form("form_horarios"):
        col1, col2 = st.columns(2)
        
        with col1:
            horario_abertura = st.time_input(
                "Horário de Abertura",
                value=datetime.strptime(config['horario_abertura'], '%H:%M').time()
            )
        
        with col2:
            horario_fechamento = st.time_input(
                "Horário de Fechamento",
                value=datetime.strptime(config['horario_fechamento'], '%H:%M').time()
            )
        
        dias_semana = st.multiselect(
            "Dias da Semana Abertos",
            ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado', 'domingo'],
            default=config['dias_semana_abertos'].split(',')
        )
        
        if st.form_submit_button("💾 Salvar Horários", use_container_width=True):
            dados = {
                'horario_abertura': horario_abertura.strftime('%H:%M'),
                'horario_fechamento': horario_fechamento.strftime('%H:%M'),
                'dias_semana_abertos': ','.join(dias_semana)
            }
            
            if db.atualizar_config_restaurante(rest_id, dados):
                st.success("✅ Horários salvos!")
                st.rerun()

def configurar_endereco():
    """Configura endereço do restaurante"""
    st.subheader("📍 Endereço do Restaurante")
    
    db = get_db()
    rest_id = st.session_state.restaurante_id
    rest = st.session_state.restaurante_dados
    
    st.info("⚠️ Alterar o endereço invalidará o cache de distâncias!")
    
    with st.form("form_endereco"):
        endereco_novo = st.text_area(
            "Endereço Completo",
            value=rest['endereco_completo'],
            height=100
        )
        
        if st.form_submit_button("💾 Atualizar Endereço", use_container_width=True):
            # TODO: Geocodificar endereço e salvar coordenadas
            # TODO: Invalidar cache de distâncias
            st.info("🚧 Funcionalidade em desenvolvimento...")

def configurar_integracoes():
    """Configura integrações (iFood, etc)"""
    st.subheader("🔗 Integrações")
    
    st.info("🚧 Integrações em desenvolvimento...")
    
    # TODO: Implementar integração com iFood
    # TODO: Configurar webhook
    # TODO: Testar conexão

def configurar_seguranca():
    """Configurações de segurança e senha"""
    st.subheader("🔐 Segurança")
    
    st.info("🚧 Alteração de senha em desenvolvimento...")
    
    # TODO: Implementar mudança de senha
    # TODO: Implementar 2FA

# ==================== IMPRESSÃO ====================

def tela_impressao():
    """Tela de impressão de comandas"""
    st.title("🖨️ Impressão de Comandas")
    
    st.info("🚧 Sistema de impressão em desenvolvimento...")
    
    # TODO: Implementar impressão de comandas
    # - Comanda para Cozinha
    # - Comanda para Balcão
    # - Comanda para Entrega

# ==================== RELATÓRIOS ====================

def tela_relatorios():
    """Tela de relatórios"""
    st.title("📊 Relatórios")
    
    st.info("🚧 Relatórios em desenvolvimento...")
    
    # TODO: Implementar relatórios
    # - Vendas por período
    # - Performance de motoboys
    # - Produtos mais vendidos
    # - Horários de pico

# ==================== MAIN ====================

def main():
    """Função principal"""
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