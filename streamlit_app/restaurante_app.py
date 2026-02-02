# streamlit_app/restaurante_app.py
"""
restaurante_app.py - Dashboard Principal do Restaurante
Super Food SaaS - Versão 2.8 ESTÁVEL

Correções aplicadas:
- Menu estável seguindo padrão do super_admin.py
- Bug do motoboy "disponivel=False" corrigido
- Removido keep-alive JavaScript problemático
- Removidos st.rerun() desnecessários que causavam loops
- Estrutura simplificada seguindo boas práticas Streamlit
"""

import streamlit as st

# ==================== PAGE CONFIG (DEVE SER PRIMEIRO) ====================
st.set_page_config(
    page_title="Dashboard Restaurante - Super Food",
    page_icon="🍕",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== IMPORTS ====================
from datetime import datetime, timedelta
import os
import sys
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

from utils.mapbox_api import autocomplete_endereco_restaurante
from utils.calculos import calcular_taxa_entrega
from utils.motoboy_selector import (
    selecionar_motoboy_para_rota,
    atribuir_rota_motoboy,
    marcar_motoboy_disponivel,
    obter_estatisticas_motoboy,
)


# ==================== FUNÇÕES DE DESPACHO ====================
def despachar_pedidos_automatico(session, restaurante_id: int) -> dict:
    """Despacha pedidos prontos para motoboys disponíveis usando seleção justa."""
    # Buscar pedidos prontos não despachados
    pedidos_prontos = session.query(Pedido).filter(
        Pedido.restaurante_id == restaurante_id,
        Pedido.status == 'pronto',
        Pedido.despachado == False,
        Pedido.tipo == 'Entrega'
    ).order_by(Pedido.data_criacao.asc()).all()

    if not pedidos_prontos:
        return {'sucesso': False, 'mensagem': 'Nenhum pedido pronto para despachar'}

    # Verificar motoboys cadastrados
    motoboys_ativos = session.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).all()

    if not motoboys_ativos:
        return {'sucesso': False, 'mensagem': '❌ Nenhum motoboy cadastrado. Cadastre um motoboy primeiro.'}

    # Verificar motoboys online (disponivel=True)
    motoboys_online = [m for m in motoboys_ativos if m.disponivel == True]

    if not motoboys_online:
        # Mostrar info útil
        nomes = [f"{m.nome} (offline)" for m in motoboys_ativos]
        return {
            'sucesso': False,
            'mensagem': f'❌ Nenhum motoboy online.\n\n📱 Os motoboys precisam fazer login no App Motoboy para ficarem online e receberem entregas.\n\nMotoboys cadastrados: {", ".join(nomes)}'
        }

    # Buscar config do restaurante
    config = session.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    max_por_rota = config.max_pedidos_por_rota if config else 5
    alertas = []
    rotas_criadas = 0
    pedidos_despachados = 0
    pedidos_restantes = list(pedidos_prontos)

    while pedidos_restantes:
        # Primeiro, selecionar motoboy disponível (pedindo apenas 1 para verificar disponibilidade)
        motoboy = selecionar_motoboy_para_rota(restaurante_id, 1, session)

        if not motoboy:
            alertas.append(f"⏳ {len(pedidos_restantes)} pedido(s) aguardando motoboy disponível")
            break

        # Calcular quantos pedidos cabem na capacidade do motoboy
        capacidade_motoboy = motoboy['capacidade_restante']
        qtd_para_rota = min(len(pedidos_restantes), max_por_rota, capacidade_motoboy)

        if qtd_para_rota <= 0:
            alertas.append(f"⏳ {len(pedidos_restantes)} pedido(s) aguardando motoboy com capacidade")
            break

        # Pegar pedidos para esta rota (respeitando capacidade do motoboy)
        pedidos_rota = pedidos_restantes[:qtd_para_rota]
        pedidos_ids = [p.id for p in pedidos_rota]

        # Atribuir rota ao motoboy
        resultado = atribuir_rota_motoboy(motoboy['motoboy_id'], pedidos_ids, session)

        if resultado['sucesso']:
            rotas_criadas += 1
            pedidos_despachados += len(pedidos_ids)
            alertas.append(f"✅ {len(pedidos_ids)} pedido(s) → {motoboy['nome']}")
            pedidos_restantes = pedidos_restantes[len(pedidos_rota):]
        else:
            alertas.append(f"❌ Erro: {resultado.get('erro', 'Desconhecido')}")
            break

    if rotas_criadas > 0:
        msg = f'✅ {pedidos_despachados} pedido(s) despachado(s) em {rotas_criadas} rota(s)!'
        if pedidos_restantes:
            msg += f'\n⏳ {len(pedidos_restantes)} pedido(s) aguardando próximo motoboy disponível.'
        return {
            'sucesso': True,
            'mensagem': msg,
            'rotas_criadas': rotas_criadas,
            'pedidos_despachados': pedidos_despachados,
            'pedidos_aguardando': len(pedidos_restantes),
            'alertas': alertas
        }
    else:
        return {
            'sucesso': False,
            'mensagem': '❌ Não foi possível despachar. Verifique se há motoboys online com capacidade.',
            'alertas': alertas
        }


def calcular_capacidade_total_motoboys(session, restaurante_id: int) -> dict:
    """Calcula capacidade total de entrega dos motoboys."""
    motoboys = session.query(Motoboy).filter(
        Motoboy.restaurante_id == restaurante_id,
        Motoboy.status == 'ativo'
    ).all()

    online = [m for m in motoboys if m.disponivel == True]
    em_rota = [m for m in motoboys if m.em_rota == True]

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


# ==================== FUNÇÕES HELPER ====================
def to_dict(obj):
    """Converte objeto SQLAlchemy para dict"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


# ==================== INICIALIZAÇÃO DE SESSÃO ====================
def inicializar_sessao():
    """Inicializa variáveis de sessão de forma segura"""
    if 'restaurante_logado' not in st.session_state:
        st.session_state.restaurante_logado = False
    if 'restaurante_id' not in st.session_state:
        st.session_state.restaurante_id = None
    if 'restaurante_dados' not in st.session_state:
        st.session_state.restaurante_dados = None
    if 'restaurante_config' not in st.session_state:
        st.session_state.restaurante_config = None


def fazer_login(email: str, senha: str) -> bool:
    """Login do restaurante"""
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
    """Interface de login"""
    st.title("🍕 Super Food - Login Restaurante")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 Acesse seu Dashboard")

        with st.form("form_login"):
            email = st.text_input("Email", placeholder="seu@email.com")
            senha = st.text_input("Senha", type="password", placeholder="Sua senha")
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")

            if submit:
                if not email or not senha:
                    st.error("❌ Preencha todos os campos!")
                elif fazer_login(email, senha):
                    st.success("✅ Login realizado!")
                    st.rerun()
                else:
                    st.error("❌ Email ou senha incorretos!")

        st.markdown("---")
        st.info("💡 **Primeiro Acesso?** Use as credenciais fornecidas pelo Super Admin.")


# ==================== SIDEBAR ====================
def renderizar_sidebar():
    """Sidebar com menu - Padrão estável igual ao super_admin.py"""
    with st.sidebar:
        rest = st.session_state.get('restaurante_dados')
        config = st.session_state.get('restaurante_config')

        if not rest:
            return "🏠 Dashboard"

        st.title(f"🍕 {rest['nome_fantasia']}")
        st.caption(f"Plano: **{rest['plano'].upper()}**")

        if config and config.get('status_atual') == 'aberto':
            st.success("🟢 **ABERTO**")
        else:
            st.error("🔴 **FECHADO**")

        st.markdown("---")

        # Botão de logout
        if st.button("🚪 Sair", use_container_width=True):
            fazer_logout()
            st.rerun()

        st.markdown("---")

        # Menu lateral SIMPLES - sem key (padrão Streamlit estável)
        menu = st.radio(
            "Menu Principal",
            [
                "🏠 Dashboard",
                "📦 Pedidos",
                "🏍️ Motoboys",
                "🍕 Gerenciar Cardápio",
                "💰 Caixa",
                "⚙️ Configurações",
                "🖨️ Impressão",
                "📊 Relatórios"
            ]
        )

        st.markdown("---")
        st.caption(f"Código: **{rest['codigo_acesso']}**")

        return menu


# ==================== DASHBOARD ====================
def tela_dashboard():
    """Dashboard principal"""
    st.title("🏠 Dashboard")

    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest_id
        ).first()

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
            st.metric("Pendentes", pendentes)
        with col3:
            st.metric("Motoboys", motoboys_ativos)
        with col4:
            st.metric("Caixa", "🟢" if caixa_aberto else "🔴")

        st.markdown("---")
        st.subheader("⚡ Controles Rápidos")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if config and config.status_atual == 'fechado':
                if st.button("🟢 Abrir", use_container_width=True, type="primary"):
                    config.status_atual = 'aberto'
                    session.commit()
                    st.rerun()
            else:
                if st.button("🔴 Fechar", use_container_width=True):
                    if config:
                        config.status_atual = 'fechado'
                        session.commit()
                    st.rerun()

        with col2:
            if not caixa_aberto:
                if st.button("💰 Abrir Caixa", use_container_width=True):
                    st.session_state.modal_abrir_caixa = True

        with col3:
            solicitacoes = session.query(MotoboySolicitacao).filter(
                MotoboySolicitacao.restaurante_id == rest_id,
                MotoboySolicitacao.status == 'pendente'
            ).count()
            if solicitacoes > 0:
                st.warning(f"🔔 {solicitacoes} solicitação(ões)")

        # Modal abrir caixa
        if st.session_state.get('modal_abrir_caixa'):
            with st.form("form_abrir_caixa"):
                st.subheader("💰 Abrir Caixa")
                valor_abertura = st.number_input("Valor de Abertura", min_value=0.0, value=100.0, step=10.0)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("✅ Abrir", use_container_width=True):
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
                with st.expander(f"#{pedido.comanda} - {pedido.cliente_nome} - {pedido.status.upper()}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Tipo:** {pedido.tipo}")
                        st.markdown(f"**Cliente:** {pedido.cliente_nome}")
                    with col2:
                        st.markdown(f"**Status:** {pedido.status}")
                        st.markdown(f"**Valor:** R$ {pedido.valor_total:.2f}")
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
        ultimo_pedido = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id
        ).order_by(Pedido.id.desc()).first()

        proxima_comanda = str(int(ultimo_pedido.comanda) + 1) if ultimo_pedido and ultimo_pedido.comanda.isdigit() else "1"

        with st.form("form_criar_pedido"):
            col1, col2 = st.columns(2)
            with col1:
                tipo_pedido = st.selectbox("Tipo *", ["Entrega", "Retirada na loja", "Para mesa"])
            with col2:
                st.text_input("Comanda", value=proxima_comanda, disabled=True)

            st.markdown("### 👤 Cliente")
            col1, col2 = st.columns(2)
            with col1:
                cliente_nome = st.text_input("Nome *")
            with col2:
                cliente_telefone = st.text_input("Telefone")

            endereco_entrega = ""
            numero_mesa = ""
            lat_cliente = None
            lon_cliente = None
            validado_mapbox = False
            taxa_entrega_calculada = 0.0
            distancia_km_calculada = 0.0

            if tipo_pedido == "Entrega":
                st.markdown("### 📍 Endereço")
                endereco_busca = st.text_input("Digite o endereço", placeholder="Ex: Rua Augusta, 123")

                if endereco_busca and len(endereco_busca) >= 3:
                    sugestoes = autocomplete_endereco_restaurante(endereco_busca, rest_id, limite=5)

                    if sugestoes:
                        opcoes = [f"{s['place_name']} ({s.get('distancia_km', 0)} km)" for s in sugestoes]
                        idx = st.selectbox("Selecione:", range(len(opcoes)), format_func=lambda i: opcoes[i])

                        sug = sugestoes[idx]
                        endereco_entrega = sug['place_name']
                        lat_cliente, lon_cliente = sug['coordinates']
                        validado_mapbox = True
                        distancia_km_calculada = sug.get('distancia_km', 0)

                        config = session.query(ConfigRestaurante).filter(
                            ConfigRestaurante.restaurante_id == rest_id
                        ).first()

                        if sug.get('dentro_zona', True):
                            resultado_taxa = calcular_taxa_entrega(rest_id, distancia_km_calculada, session)
                            taxa_entrega_calculada = resultado_taxa['taxa_total']
                            st.success(f"✅ Taxa: R$ {taxa_entrega_calculada:.2f} ({distancia_km_calculada:.1f} km)")
                        else:
                            st.error(f"❌ Fora da zona ({distancia_km_calculada:.1f} km)")
                            validado_mapbox = False
                    else:
                        st.warning("Nenhuma sugestão encontrada.")

            elif tipo_pedido == "Para mesa":
                numero_mesa = st.text_input("Número da Mesa *")

            st.markdown("### 🍕 Itens")
            itens = st.text_area("Descreva os itens *", placeholder="1x Pizza Calabresa\n2x Refrigerante")

            col1, col2 = st.columns(2)
            with col1:
                valor_total = st.number_input("Valor (R$)", min_value=0.0, step=1.0)
            with col2:
                tempo_estimado = st.number_input("Tempo (min)", min_value=5, value=45, step=5)

            observacoes = st.text_area("Observações")
            forma_pagamento = st.selectbox("Pagamento", ["Dinheiro", "Cartão", "Pix", "Online"])

            troco_para = None
            if forma_pagamento == "Dinheiro":
                troco_para = st.number_input("Troco para", min_value=0.0, step=5.0)

            submit = st.form_submit_button("✅ Criar Pedido", use_container_width=True, type="primary")

            if submit:
                erros = []
                if not cliente_nome or not itens:
                    erros.append("Nome e itens são obrigatórios")
                if tipo_pedido == "Entrega" and not validado_mapbox:
                    erros.append("Selecione um endereço válido")
                if tipo_pedido == "Para mesa" and not numero_mesa:
                    erros.append("Número da mesa obrigatório")

                if erros:
                    for e in erros:
                        st.error(f"❌ {e}")
                else:
                    valor_final = valor_total + taxa_entrega_calculada if tipo_pedido == "Entrega" else valor_total

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
                        valor_total=valor_final,
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
                    st.success(f"✅ Pedido #{proxima_comanda} criado!")
                    st.balloons()
    finally:
        session.close()


def listar_pedidos_ativos():
    st.subheader("📋 Pedidos Ativos")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        # Botão de despacho
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🚀 Despachar Prontos", use_container_width=True, type="primary"):
                resultado = despachar_pedidos_automatico(session, rest_id)
                if resultado['sucesso']:
                    st.success(resultado['mensagem'])
                    if resultado.get('alertas'):
                        for a in resultado['alertas']:
                            st.info(a)
                else:
                    st.error(resultado['mensagem'])
                    if resultado.get('alertas'):
                        for a in resultado['alertas']:
                            st.warning(a)

        # Métricas de capacidade
        capacidade = calcular_capacidade_total_motoboys(session, rest_id)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Online", capacidade['motoboys_online'])
        with col2:
            st.metric("Capacidade", capacidade['capacidade_total'])
        with col3:
            st.metric("Em Rota", capacidade['pedidos_em_rota'])
        with col4:
            st.metric("Disponível", capacidade['capacidade_disponivel'])

        st.markdown("---")

        # Lista de pedidos
        pedidos = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id,
            Pedido.status.notin_(['finalizado', 'cancelado', 'entregue'])
        ).order_by(Pedido.data_criacao.desc()).all()

        if not pedidos:
            st.info("Nenhum pedido ativo.")
            return

        for pedido in pedidos:
            with st.expander(f"#{pedido.comanda} - {pedido.cliente_nome} - {pedido.status.upper()}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Tipo:** {pedido.tipo}")
                    st.markdown(f"**Cliente:** {pedido.cliente_nome}")
                    if pedido.tipo == "Entrega":
                        st.markdown(f"**Endereço:** {pedido.endereco_entrega}")
                with col2:
                    st.markdown(f"**Status:** {pedido.status}")
                    st.markdown(f"**Valor:** R$ {pedido.valor_total:.2f}")

                st.text(pedido.itens)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if pedido.status == 'pendente':
                        if st.button("👨‍🍳 Preparo", key=f"prep_{pedido.id}"):
                            pedido.status = 'em_preparo'
                            session.commit()
                            st.rerun()
                with col2:
                    if pedido.status == 'em_preparo':
                        if st.button("✅ Pronto", key=f"pronto_{pedido.id}"):
                            pedido.status = 'pronto'
                            session.commit()
                            st.rerun()
                with col3:
                    if pedido.status in ['pronto', 'saiu_entrega']:
                        if st.button("✅ Finalizar", key=f"fin_{pedido.id}"):
                            pedido.status = 'entregue' if pedido.tipo == "Entrega" else 'finalizado'
                            session.commit()
                            st.rerun()
                with col4:
                    if st.button("❌ Cancelar", key=f"canc_{pedido.id}"):
                        pedido.status = 'cancelado'
                        session.commit()
                        st.rerun()
    finally:
        session.close()


def historico_pedidos():
    st.subheader("📜 Histórico")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("De", value=datetime.now() - timedelta(days=7))
        with col2:
            data_fim = st.date_input("Até", value=datetime.now())

        pedidos = session.query(Pedido).filter(
            Pedido.restaurante_id == rest_id,
            Pedido.data_criacao >= datetime.combine(data_inicio, datetime.min.time()),
            Pedido.data_criacao <= datetime.combine(data_fim, datetime.max.time())
        ).order_by(Pedido.data_criacao.desc()).all()

        if pedidos:
            total = sum(p.valor_total for p in pedidos)
            st.metric("Total no período", f"R$ {total:.2f}")

            for p in pedidos:
                st.text(f"#{p.comanda} | {p.cliente_nome} | {p.status} | R$ {p.valor_total:.2f}")
        else:
            st.info("Nenhum pedido no período.")
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
            st.info("Nenhum motoboy ativo. Cadastre um motoboy na aba 'Cadastrar Manual'.")
            return

        # Resumo
        online = len([m for m in motoboys if m.disponivel == True])
        em_rota = len([m for m in motoboys if m.em_rota == True])

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(motoboys))
        with col2:
            st.metric("Online", online)
        with col3:
            st.metric("Em Rota", em_rota)
        with col4:
            st.metric("Livres", online - em_rota)

        st.markdown("---")

        for motoboy in motoboys:
            # Status visual
            if motoboy.em_rota:
                icon, status = "🚴", "Em Rota"
            elif motoboy.disponivel:
                icon, status = "✅", "Online"
            else:
                icon, status = "⏸️", "Offline"

            # Info adicional de último login
            ultimo_online = ""
            if motoboy.ultimo_status_online:
                ultimo_online = f" (Login: {motoboy.ultimo_status_online.strftime('%d/%m %H:%M')})"
            elif not motoboy.disponivel:
                ultimo_online = " (Nunca logou no App)"

            with st.expander(f"{icon} {motoboy.nome} - {status}{ultimo_online}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Telefone:** {motoboy.telefone}")
                    st.markdown(f"**Usuário:** {motoboy.usuario}")
                with col2:
                    st.markdown(f"**Entregas Pendentes:** {motoboy.entregas_pendentes or 0}")
                    st.markdown(f"**Total Entregas:** {motoboy.total_entregas or 0}")
                    st.markdown(f"**Ganhos:** R$ {motoboy.total_ganhos or 0:.2f}")

                st.markdown("---")

                # Configuração de Capacidade
                st.markdown("##### ⚙️ Configuração")
                col_cap1, col_cap2 = st.columns([2, 1])
                with col_cap1:
                    nova_capacidade = st.number_input(
                        "Capacidade de entregas",
                        min_value=1,
                        max_value=20,
                        value=motoboy.capacidade_entregas or 3,
                        step=1,
                        key=f"cap_{motoboy.id}",
                        help="Máximo de pedidos que este motoboy pode carregar por vez"
                    )
                with col_cap2:
                    if st.button("💾 Salvar", key=f"save_cap_{motoboy.id}"):
                        if nova_capacidade != motoboy.capacidade_entregas:
                            motoboy.capacidade_entregas = nova_capacidade
                            session.commit()
                            st.success(f"Capacidade: {nova_capacidade}")
                            st.rerun()

                st.markdown("---")

                # Botões de ação
                st.markdown("##### 🔧 Ações")
                col1, col2, col3 = st.columns(3)
                with col1:
                    if motoboy.disponivel:
                        if st.button("⏸️ Offline", key=f"off_{motoboy.id}"):
                            motoboy.disponivel = False
                            session.commit()
                            st.rerun()
                    else:
                        if st.button("✅ Online", key=f"on_{motoboy.id}"):
                            motoboy.disponivel = True
                            session.commit()
                            st.rerun()
                with col2:
                    if st.button("❌ Desativar", key=f"des_{motoboy.id}"):
                        motoboy.status = 'inativo'
                        motoboy.disponivel = False
                        motoboy.em_rota = False
                        session.commit()
                        st.rerun()
                with col3:
                    if st.button("🔄 Reset Senha", key=f"rst_{motoboy.id}"):
                        motoboy.set_senha("123456")
                        session.commit()
                        st.success("Senha: 123456")
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
            st.markdown(f"**{sol.nome}** - {sol.usuario} - {sol.telefone}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Aprovar", key=f"apr_{sol.id}"):
                    # Criar motoboy OFFLINE - fica online ao fazer login no App
                    motoboy = Motoboy(
                        restaurante_id=sol.restaurante_id,
                        nome=sol.nome,
                        usuario=sol.usuario,
                        telefone=sol.telefone,
                        senha=hashlib.sha256("123456".encode()).hexdigest(),
                        status='ativo',
                        disponivel=False,  # OFFLINE até fazer login no App
                        capacidade_entregas=3,
                        entregas_pendentes=0,
                        em_rota=False,
                        ordem_hierarquia=0,
                        data_cadastro=datetime.now()
                    )
                    session.add(motoboy)
                    sol.status = 'aprovado'
                    session.commit()
                    st.success("✅ Aprovado! Motoboy ficará online ao fazer login no App.")
                    st.info("📱 Senha padrão: **123456**")
                    st.rerun()
            with col2:
                if st.button("❌ Rejeitar", key=f"rej_{sol.id}"):
                    sol.status = 'rejeitado'
                    session.commit()
                    st.rerun()
            st.markdown("---")
    finally:
        session.close()


def cadastrar_motoboy_manual():
    st.subheader("➕ Cadastrar Motoboy")

    # Informação importante sobre o fluxo
    st.info("💡 O motoboy ficará **offline** até fazer login no App Motoboy. Após o login, ele será automaticamente marcado como **online** e poderá receber entregas.")

    with st.form("form_motoboy"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome Completo *")
            usuario = st.text_input("Usuário *")
        with col2:
            telefone = st.text_input("Telefone *")
            senha = st.text_input("Senha *", type="password", value="123456")

        capacidade = st.number_input(
            "Capacidade de Entregas",
            min_value=1,
            max_value=20,
            value=3,
            step=1,
            help="Quantidade máxima de pedidos que o motoboy pode levar por vez. Ex: moto=3, carro=8, bicicleta=2"
        )

        if st.form_submit_button("✅ Cadastrar", use_container_width=True):
            if not nome or not usuario or not telefone or not senha:
                st.error("Preencha todos os campos!")
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
                        # Motoboy SEMPRE começa offline
                        # Só fica online quando faz login no App Motoboy
                        motoboy = Motoboy(
                            restaurante_id=st.session_state.restaurante_id,
                            nome=nome,
                            usuario=usuario.lower(),
                            telefone=telefone,
                            senha=hashlib.sha256(senha.encode()).hexdigest(),
                            status='ativo',
                            disponivel=False,  # SEMPRE OFFLINE até fazer login
                            capacidade_entregas=capacidade,  # Capacidade configurável
                            entregas_pendentes=0,
                            em_rota=False,
                            ordem_hierarquia=0,
                            data_cadastro=datetime.now()
                        )
                        session.add(motoboy)
                        session.commit()
                        st.success(f"✅ Motoboy cadastrado! Capacidade: {capacidade} entregas")
                        st.info(f"📱 Credenciais: Usuário: **{usuario.lower()}** | Senha: **{senha}**")
                finally:
                    session.close()


# ==================== CAIXA ====================
def tela_caixa():
    st.title("💰 Caixa")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        caixa = session.query(Caixa).filter(
            Caixa.restaurante_id == rest_id,
            Caixa.status == 'aberto'
        ).first()

        if not caixa:
            st.warning("🔴 Caixa FECHADO")
            with st.form("form_abrir"):
                valor = st.number_input("Valor de Abertura", min_value=0.0, value=100.0)
                if st.form_submit_button("💰 Abrir Caixa", type="primary"):
                    novo = Caixa(
                        restaurante_id=rest_id,
                        data_abertura=datetime.now(),
                        operador_abertura=st.session_state.restaurante_dados['email'],
                        valor_abertura=valor,
                        status='aberto'
                    )
                    session.add(novo)
                    session.flush()
                    session.add(MovimentacaoCaixa(
                        caixa_id=novo.id, tipo='abertura',
                        valor=valor, descricao='Abertura', data_hora=datetime.now()
                    ))
                    session.commit()
                    st.rerun()
        else:
            st.success("🟢 Caixa ABERTO")
            saldo = caixa.valor_abertura + caixa.total_vendas - caixa.valor_retiradas

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Abertura", f"R$ {caixa.valor_abertura:.2f}")
            with col2:
                st.metric("Vendas", f"R$ {caixa.total_vendas:.2f}")
            with col3:
                st.metric("Retiradas", f"R$ {caixa.valor_retiradas:.2f}")
            with col4:
                st.metric("Saldo", f"R$ {saldo:.2f}")

            with st.form("form_retirada"):
                st.subheader("💸 Retirada")
                valor = st.number_input("Valor", min_value=0.01, step=10.0)
                desc = st.text_input("Motivo *")
                if st.form_submit_button("Retirar"):
                    if desc:
                        session.add(MovimentacaoCaixa(
                            caixa_id=caixa.id, tipo='retirada',
                            valor=valor, descricao=desc, data_hora=datetime.now()
                        ))
                        caixa.valor_retiradas += valor
                        session.commit()
                        st.rerun()
                    else:
                        st.error("Informe o motivo")

            st.markdown("---")
            if st.button("🔒 Fechar Caixa"):
                caixa.status = 'fechado'
                caixa.data_fechamento = datetime.now()
                session.commit()
                st.rerun()
    finally:
        session.close()


# ==================== CONFIGURAÇÕES ====================
def tela_configuracoes():
    st.title("⚙️ Configurações")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest_id
        ).first()

        if not config:
            st.error("Configuração não encontrada")
            return

        tabs = st.tabs(["💰 Taxas", "🕐 Horários", "📍 Endereço"])

        with tabs[0]:
            with st.form("form_taxas"):
                st.subheader("Taxa de Entrega (cliente)")
                col1, col2, col3 = st.columns(3)
                with col1:
                    taxa_base = st.number_input("Taxa Base (R$)", value=config.taxa_entrega_base or 5.0)
                with col2:
                    dist_base = st.number_input("Distância Base (km)", value=config.distancia_base_km or 3.0)
                with col3:
                    taxa_km = st.number_input("Taxa/km Extra (R$)", value=config.taxa_km_extra or 1.5)

                st.subheader("Pagamento Motoboy")
                col1, col2 = st.columns(2)
                with col1:
                    moto_base = st.number_input("Valor Base (R$)", value=config.valor_base_motoboy or 5.0)
                with col2:
                    moto_km = st.number_input("Valor/km Extra (R$)", value=config.valor_km_extra_motoboy or 1.0)

                raio = st.number_input("Raio de Entrega (km)", value=config.raio_entrega_km or 10.0)
                max_pedidos = st.number_input("Máx. Pedidos/Rota", value=config.max_pedidos_por_rota or 5, min_value=1, max_value=10)

                if st.form_submit_button("💾 Salvar", type="primary"):
                    config.taxa_entrega_base = taxa_base
                    config.distancia_base_km = dist_base
                    config.taxa_km_extra = taxa_km
                    config.valor_base_motoboy = moto_base
                    config.valor_km_extra_motoboy = moto_km
                    config.raio_entrega_km = raio
                    config.max_pedidos_por_rota = max_pedidos
                    session.commit()
                    st.success("✅ Salvo!")

        with tabs[1]:
            with st.form("form_horarios"):
                col1, col2 = st.columns(2)
                with col1:
                    abertura = st.time_input("Abertura", value=datetime.strptime(config.horario_abertura or "18:00", '%H:%M').time())
                with col2:
                    fechamento = st.time_input("Fechamento", value=datetime.strptime(config.horario_fechamento or "23:00", '%H:%M').time())

                if st.form_submit_button("💾 Salvar"):
                    config.horario_abertura = abertura.strftime('%H:%M')
                    config.horario_fechamento = fechamento.strftime('%H:%M')
                    session.commit()
                    st.success("✅ Salvo!")

        with tabs[2]:
            rest = session.get(Restaurante, rest_id)
            with st.form("form_endereco"):
                endereco = st.text_area("Endereço Completo", value=rest.endereco_completo or "")
                if st.form_submit_button("💾 Salvar"):
                    rest.endereco_completo = endereco
                    session.commit()
                    st.success("✅ Salvo!")

    finally:
        session.close()


# ==================== CARDÁPIO ====================
def tela_gerenciar_cardapio():
    st.title("🍕 Cardápio")
    st.info("🚧 Gerenciamento de cardápio em desenvolvimento...")


# ==================== IMPRESSÃO E RELATÓRIOS ====================
def tela_impressao():
    st.title("🖨️ Impressão")
    st.info("🚧 Em desenvolvimento...")


def tela_relatorios():
    st.title("📊 Relatórios")
    st.info("🚧 Em desenvolvimento...")


# ==================== MAIN ====================
def main():
    """Função principal - estrutura simples e estável"""
    # Inicializar sessão
    inicializar_sessao()

    # Verificar login
    if not st.session_state.restaurante_logado:
        tela_login()
        return

    # Renderizar sidebar e obter menu
    menu = renderizar_sidebar()

    # Roteamento de telas
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


if __name__ == "__main__":
    main()
