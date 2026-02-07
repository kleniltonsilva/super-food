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
import time
import io
import pandas as pd

# Configuração de path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

# Imports do projeto - SQLAlchemy
from database.session import get_db_session
from database.models import (
    Restaurante, ConfigRestaurante, Motoboy, MotoboySolicitacao,
    Pedido, Produto, Entrega, Caixa, MovimentacaoCaixa, Notificacao,
    CategoriaMenu, SiteConfig, GPSMotoboy, VariacaoProduto,
    BairroEntrega, PremioFidelidade, Promocao, TipoProduto
)

from utils.mapbox_api import autocomplete_endereco_restaurante
from utils.calculos import calcular_taxa_entrega, atualizar_coordenadas_restaurante
from utils.motoboy_selector import (
    selecionar_motoboy_para_rota,
    atribuir_rota_motoboy,
    marcar_motoboy_disponivel,
    obter_estatisticas_motoboy,
)


# ==================== FUNÇÕES DE DESPACHO ====================
def despachar_pedidos_automatico(session, restaurante_id: int) -> dict:
    """
    Despacha pedidos prontos para motoboys disponíveis usando seleção justa.

    Suporta 3 modos de prioridade de entrega:
    - rapido_economico: TSP por proximidade (padrão)
    - cronologico_inteligente: Agrupa por tempo, depois TSP
    - manual: Não despacha automaticamente
    """
    # Buscar config do restaurante
    config = session.query(ConfigRestaurante).filter(
        ConfigRestaurante.restaurante_id == restaurante_id
    ).first()

    # Verificar modo de despacho
    modo_prioridade = config.modo_prioridade_entrega if config else 'rapido_economico'

    if modo_prioridade == 'manual':
        return {
            'sucesso': False,
            'mensagem': '⚙️ Modo Manual ativo. Atribua os pedidos manualmente aos motoboys.',
            'modo': 'manual'
        }

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

    max_por_rota = config.max_pedidos_por_rota if config else 5
    alertas = []
    rotas_criadas = 0
    pedidos_despachados = 0
    pedidos_restantes = list(pedidos_prontos)

    # Otimizar ordem dos pedidos conforme modo selecionado
    from utils.tsp_optimizer import otimizar_rota_por_modo

    # Buscar restaurante para coordenadas de origem
    restaurante = session.query(Restaurante).filter(
        Restaurante.id == restaurante_id
    ).first()

    if restaurante and restaurante.latitude and restaurante.longitude:
        origem = (restaurante.latitude, restaurante.longitude)

        # Preparar destinos para otimização
        destinos = []
        for p in pedidos_restantes:
            if p.latitude_entrega and p.longitude_entrega:
                destinos.append({
                    'pedido_id': p.id,
                    'lat': p.latitude_entrega,
                    'lon': p.longitude_entrega,
                    'data_criacao': p.data_criacao
                })

        if destinos:
            # Otimizar ordem
            destinos_otimizados = otimizar_rota_por_modo(origem, destinos, modo_prioridade)

            # Reordenar pedidos_restantes conforme otimização
            id_para_pedido = {p.id: p for p in pedidos_restantes}
            pedidos_otimizados = []
            for d in destinos_otimizados:
                if d['pedido_id'] in id_para_pedido:
                    pedidos_otimizados.append(id_para_pedido[d['pedido_id']])

            # Adicionar pedidos sem coordenadas ao final
            pedidos_sem_coord = [p for p in pedidos_restantes if p.id not in [d['pedido_id'] for d in destinos_otimizados]]
            pedidos_restantes = pedidos_otimizados + pedidos_sem_coord

            alertas.append(f"📍 Modo: {modo_prioridade.replace('_', ' ').title()}")

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

        if not rest:
            return "🏠 Dashboard"

        st.title(f"🍕 {rest['nome_fantasia']}")
        st.caption(f"Plano: **{rest['plano'].upper()}**")

        # Buscar status ATUAL do banco (não do session_state cache)
        session = get_db_session()
        try:
            config = session.query(ConfigRestaurante).filter(
                ConfigRestaurante.restaurante_id == rest['id']
            ).first()

            if config and config.status_atual == 'aberto':
                st.success("🟢 **ABERTO**")
            else:
                st.error("🔴 **FECHADO**")
        finally:
            session.close()

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
                    # Usar toast para mensagem temporária que desaparece após 3 segundos
                    st.toast(resultado['mensagem'], icon="✅")
                    if resultado.get('alertas'):
                        for a in resultado['alertas']:
                            st.toast(a, icon="📋")
                    # Forçar rerun para atualizar lista de pedidos
                    time.sleep(1)
                    st.rerun()
                else:
                    st.toast(resultado['mensagem'], icon="❌")
                    if resultado.get('alertas'):
                        for a in resultado['alertas']:
                            st.toast(a, icon="⚠️")

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
                            # Atualizar caixa
                            caixa = session.query(Caixa).filter(
                                Caixa.restaurante_id == rest_id,
                                Caixa.status == 'aberto'
                            ).first()
                            if caixa and pedido.valor_total:
                                caixa.total_vendas = (caixa.total_vendas or 0) + pedido.valor_total
                                session.add(MovimentacaoCaixa(
                                    caixa_id=caixa.id,
                                    tipo='venda',
                                    valor=pedido.valor_total,
                                    descricao=f"Pedido #{pedido.comanda}",
                                    data_hora=datetime.now()
                                ))
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
                # Status da entrega
                status_entrega = p.status.upper()
                if p.entrega:
                    if p.entrega.motivo_finalizacao:
                        status_entrega = p.entrega.motivo_finalizacao.upper().replace('_', ' ')

                with st.expander(f"#{p.comanda} - {p.cliente_nome} - {status_entrega}"):
                    st.markdown(f"**Tipo:** {p.tipo}")
                    st.markdown(f"**Cliente:** {p.cliente_nome}")
                    st.markdown(f"**Endereço:** {p.endereco_entrega or 'N/A'}")
                    st.markdown(f"**Status:** {status_entrega}")
                    st.markdown(f"**Valor:** R$ {p.valor_total:.2f}")

                    # Forma de pagamento detalhada (registrada pelo motoboy)
                    if p.forma_pagamento_real:
                        st.markdown("---")
                        st.markdown("**💳 Forma de Pagamento ao Motoboy:**")
                        st.markdown(f"  • Método: {p.forma_pagamento_real}")
                        if p.valor_pago_dinheiro and p.valor_pago_dinheiro > 0:
                            st.markdown(f"  • 💵 Dinheiro: R$ {p.valor_pago_dinheiro:.2f}")
                        if p.valor_pago_cartao and p.valor_pago_cartao > 0:
                            st.markdown(f"  • 💳 Cartão/Pix: R$ {p.valor_pago_cartao:.2f}")
                    elif p.forma_pagamento:
                        st.markdown(f"**Pagamento previsto:** {p.forma_pagamento}")
        else:
            st.info("Nenhum pedido no período.")
    finally:
        session.close()


# ==================== MOTOBOYS ====================
def tela_motoboys():
    st.title("🏍️ Gerenciamento de Motoboys")
    tabs = st.tabs(["📋 Motoboys Ativos", "🏆 Ranking", "💸 Pagamentos", "🗺️ Mapa", "🆕 Solicitações", "➕ Cadastrar"])

    with tabs[0]:
        listar_motoboys_ativos()
    with tabs[1]:
        ranking_motoboys()
    with tabs[2]:
        pagamento_motoboys()
    with tabs[3]:
        mapa_motoboys_tempo_real()
    with tabs[4]:
        listar_solicitacoes()
    with tabs[5]:
        cadastrar_motoboy_manual()


def mapa_motoboys_tempo_real():
    """Mapa em tempo real com localização dos motoboys online - Atualiza a cada 10 segundos"""
    st.subheader("🗺️ Mapa em Tempo Real")

    # Controles de atualização
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 1, 2])
    with col_ctrl1:
        auto_refresh = st.checkbox("🔄 Atualização automática (10s)", value=True, key="auto_refresh_mapa")
    with col_ctrl2:
        if st.button("🔄 Atualizar Agora", key="btn_refresh_mapa"):
            st.rerun()
    with col_ctrl3:
        st.caption(f"⏰ Última: {datetime.now().strftime('%H:%M:%S')}")

    # Auto-refresh via JavaScript
    if auto_refresh:
        st.markdown("""
        <script>
        (function() {
            // Auto-refresh a cada 10 segundos
            const REFRESH_INTERVAL = 10000;

            // Evitar múltiplos intervalos
            if (window.mapRefreshInterval) {
                clearInterval(window.mapRefreshInterval);
            }

            window.mapRefreshInterval = setInterval(() => {
                // Verificar se ainda estamos na página do mapa
                const mapElement = document.querySelector('[data-testid="stVerticalBlock"]');
                if (mapElement) {
                    // Simular clique no botão de refresh ou recarregar
                    const refreshBtn = document.querySelector('[data-testid="baseButton-secondary"]');
                    if (refreshBtn && refreshBtn.innerText.includes('Atualizar')) {
                        refreshBtn.click();
                    } else {
                        // Fallback: recarregar página
                        window.parent.postMessage({type: 'streamlit:rerun'}, '*');
                    }
                }
            }, REFRESH_INTERVAL);
        })();
        </script>
        """, unsafe_allow_html=True)

    st.markdown("---")

    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        # Buscar restaurante para coordenadas centrais
        restaurante = session.query(Restaurante).filter(
            Restaurante.id == rest_id
        ).first()

        # Buscar motoboys online
        motoboys_online = session.query(Motoboy).filter(
            Motoboy.restaurante_id == rest_id,
            Motoboy.status == 'ativo',
            Motoboy.disponivel == True
        ).all()

        if not motoboys_online:
            st.info("📍 Nenhum motoboy online no momento.")
            st.caption("Quando os motoboys fizerem login no App, eles aparecerão no mapa.")
            st.markdown("""
            **💡 Dica:** Os motoboys precisam:
            1. Fazer login no App Motoboy
            2. Permitir acesso à localização no navegador
            3. Manter o App aberto para enviar GPS
            """)
            return

        # Coletar posições GPS dos motoboys
        motoboys_com_gps = []
        motoboys_sem_gps = []

        for motoboy in motoboys_online:
            # Buscar última posição GPS (dos últimos 5 minutos)
            from datetime import timedelta
            limite_tempo = datetime.now() - timedelta(minutes=5)

            gps = session.query(GPSMotoboy).filter(
                GPSMotoboy.motoboy_id == motoboy.id,
                GPSMotoboy.timestamp >= limite_tempo
            ).order_by(GPSMotoboy.timestamp.desc()).first()

            if gps:
                motoboys_com_gps.append({
                    'id': motoboy.id,
                    'nome': motoboy.nome,
                    'lat': gps.latitude,
                    'lon': gps.longitude,
                    'velocidade': gps.velocidade or 0,
                    'ultima_atualizacao': gps.timestamp,
                    'em_rota': motoboy.em_rota,
                    'entregas_pendentes': motoboy.entregas_pendentes or 0,
                    'gps_recente': True
                })
            elif motoboy.latitude_atual and motoboy.longitude_atual:
                # Fallback para coordenada salva no motoboy
                motoboys_com_gps.append({
                    'id': motoboy.id,
                    'nome': motoboy.nome,
                    'lat': motoboy.latitude_atual,
                    'lon': motoboy.longitude_atual,
                    'velocidade': 0,
                    'ultima_atualizacao': motoboy.ultima_atualizacao_gps,
                    'em_rota': motoboy.em_rota,
                    'entregas_pendentes': motoboy.entregas_pendentes or 0,
                    'gps_recente': False
                })
            else:
                motoboys_sem_gps.append(motoboy.nome)

        # Métricas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🟢 Online", len(motoboys_online))
        with col2:
            st.metric("📍 Com GPS", len(motoboys_com_gps))
        with col3:
            em_rota = len([m for m in motoboys_com_gps if m['em_rota']])
            st.metric("🏍️ Em Rota", em_rota)
        with col4:
            st.metric("⚠️ Sem GPS", len(motoboys_sem_gps))

        # Alertar sobre motoboys sem GPS
        if motoboys_sem_gps:
            st.warning(f"⚠️ Motoboys sem localização GPS: **{', '.join(motoboys_sem_gps)}**")
            st.caption("Eles precisam permitir acesso à localização no navegador.")

        st.markdown("---")

        if not motoboys_com_gps:
            st.warning("⚠️ Nenhum motoboy com localização GPS disponível.")
            st.caption("Os motoboys precisam permitir acesso à localização no App.")
            return

        # Criar mapa com folium
        try:
            import folium
            from streamlit_folium import st_folium

            # Centro do mapa: restaurante ou média das posições
            if restaurante and restaurante.latitude and restaurante.longitude:
                centro = [restaurante.latitude, restaurante.longitude]
            else:
                lat_media = sum(m['lat'] for m in motoboys_com_gps) / len(motoboys_com_gps)
                lon_media = sum(m['lon'] for m in motoboys_com_gps) / len(motoboys_com_gps)
                centro = [lat_media, lon_media]

            # Criar mapa com estilo escuro para melhor visualização
            mapa = folium.Map(
                location=centro,
                zoom_start=14,
                tiles='cartodbpositron'  # Estilo mais clean
            )

            # Adicionar marcador do restaurante
            if restaurante and restaurante.latitude and restaurante.longitude:
                folium.Marker(
                    [restaurante.latitude, restaurante.longitude],
                    popup=f"<b>🏪 {restaurante.nome_fantasia}</b><br>Seu restaurante",
                    icon=folium.Icon(color='red', icon='home', prefix='fa'),
                    tooltip="🏪 Restaurante"
                ).add_to(mapa)

            # Adicionar marcadores dos motoboys
            for m in motoboys_com_gps:
                # Cor baseada no status
                if m['em_rota']:
                    cor = 'orange'
                    icone = 'motorcycle'
                    status_txt = '🏍️ Em Rota'
                elif m['gps_recente']:
                    cor = 'green'
                    icone = 'user'
                    status_txt = '✅ Disponível'
                else:
                    cor = 'gray'
                    icone = 'user'
                    status_txt = '📍 GPS antigo'

                # Tempo desde última atualização
                if m['ultima_atualizacao']:
                    delta = datetime.now() - m['ultima_atualizacao']
                    if delta.seconds < 60:
                        tempo_txt = f"{delta.seconds}s atrás"
                    elif delta.seconds < 3600:
                        tempo_txt = f"{delta.seconds // 60}min atrás"
                    else:
                        tempo_txt = m['ultima_atualizacao'].strftime('%H:%M')
                else:
                    tempo_txt = 'N/A'

                popup_html = f"""
                <div style="font-family: Arial; min-width: 150px;">
                    <b style="font-size: 14px;">🏍️ {m['nome']}</b><br>
                    <hr style="margin: 5px 0;">
                    <b>Status:</b> {status_txt}<br>
                    <b>Entregas:</b> {m['entregas_pendentes']}<br>
                    <b>Velocidade:</b> {m['velocidade']:.1f} km/h<br>
                    <b>Atualizado:</b> {tempo_txt}
                </div>
                """

                folium.Marker(
                    [m['lat'], m['lon']],
                    popup=folium.Popup(popup_html, max_width=250),
                    icon=folium.Icon(color=cor, icon=icone, prefix='fa'),
                    tooltip=f"{m['nome']} - {status_txt}"
                ).add_to(mapa)

            # Renderizar mapa (chave única baseada no timestamp para forçar refresh)
            map_key = f"mapa_motoboys_{datetime.now().strftime('%H%M%S')}"
            st_folium(mapa, width=700, height=450, key=map_key)

        except ImportError:
            st.error("❌ Biblioteca 'folium' ou 'streamlit-folium' não instalada.")
            st.code("pip install folium streamlit-folium")

            # Fallback: mostrar lista de posições
            st.markdown("### 📍 Posições dos Motoboys")
            for m in motoboys_com_gps:
                status = "🏍️ Em Rota" if m['em_rota'] else "✅ Disponível"
                st.markdown(f"**{m['nome']}** - {status}")
                st.caption(f"📍 {m['lat']:.6f}, {m['lon']:.6f} | Velocidade: {m['velocidade']:.1f} km/h")

        # Lista de motoboys
        st.markdown("---")
        st.markdown("### 📋 Detalhes dos Motoboys Online")
        for m in motoboys_com_gps:
            status_icon = "🏍️" if m['em_rota'] else "✅"
            with st.expander(f"{status_icon} {m['nome']} - {m['entregas_pendentes']} entrega(s)"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Status:** {'Em Rota' if m['em_rota'] else 'Disponível'}")
                    st.markdown(f"**Entregas:** {m['entregas_pendentes']}")
                with col2:
                    st.markdown(f"**Coordenadas:** {m['lat']:.6f}, {m['lon']:.6f}")
                    st.markdown(f"**Velocidade:** {m['velocidade']:.1f} km/h")
                if m['ultima_atualizacao']:
                    st.caption(f"Última atualização: {m['ultima_atualizacao'].strftime('%d/%m/%Y %H:%M:%S')}")

    finally:
        session.close()


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
            cpf = st.text_input("CPF (opcional)", help="Com CPF: dados financeiros preservados ao excluir. Sem CPF: dados descartados.")
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
                            cpf=cpf.strip() if cpf else None,
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


def ranking_motoboys():
    """Ranking de motoboys com estatísticas e valores"""
    st.subheader("🏆 Ranking de Motoboys")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest_id
        ).first()

        # Aviso de antifraude
        if config and config.permitir_finalizar_fora_raio:
            st.warning("⚠️ **Ranking sem validação antifraude por localização** - Motoboys podem finalizar entregas fora do raio de 50m do endereço.")
        else:
            st.success("✅ **Ranking com validação antifraude** - Motoboys só podem finalizar entregas dentro do raio de 50m do endereço de entrega.")

        # Filtro de período
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            data_inicio = st.date_input("De", value=datetime.now().replace(day=1))
        with col2:
            data_fim = st.date_input("Até", value=datetime.now())
        with col3:
            st.markdown("")
            st.markdown("")
            atualizar = st.button("🔄 Atualizar", use_container_width=True)

        st.markdown("---")

        # Buscar motoboys com estatísticas
        from sqlalchemy import func
        from sqlalchemy.orm import joinedload

        motoboys = session.query(Motoboy).filter(
            Motoboy.restaurante_id == rest_id,
            Motoboy.status == 'ativo'
        ).all()

        if not motoboys:
            st.info("Nenhum motoboy ativo.")
            return

        ranking_data = []
        for motoboy in motoboys:
            # Buscar entregas no período
            entregas = session.query(Entrega).join(Pedido).filter(
                Pedido.restaurante_id == rest_id,
                Entrega.motoboy_id == motoboy.id,
                Entrega.status == 'entregue',
                Entrega.entregue_em >= datetime.combine(data_inicio, datetime.min.time()),
                Entrega.entregue_em <= datetime.combine(data_fim, datetime.max.time())
            ).all()

            total_entregas = len(entregas)
            valor_entregas = sum(e.valor_motoboy or 0 for e in entregas)
            valor_extras = sum(e.valor_extra_motoboy or 0 for e in entregas)
            valor_lanche = sum(e.valor_lanche or 0 for e in entregas)
            valor_diaria = sum(e.valor_diaria or 0 for e in entregas)
            valor_total = valor_entregas + valor_extras + valor_lanche + valor_diaria

            # Tempo médio de entrega
            tempos = []
            for e in entregas:
                if e.delivery_started_at and e.delivery_finished_at:
                    delta = (e.delivery_finished_at - e.delivery_started_at).total_seconds() / 60
                    if delta > 0:
                        tempos.append(delta)

            tempo_medio = sum(tempos) / len(tempos) if tempos else 0

            # Entregas fora do raio
            fora_raio = len([e for e in entregas if e.finalizado_fora_raio])

            ranking_data.append({
                'id': motoboy.id,
                'nome': motoboy.nome,
                'cpf': motoboy.cpf,
                'total_entregas': total_entregas,
                'tempo_medio': tempo_medio,
                'valor_entregas': valor_entregas,
                'valor_extras': valor_extras,
                'valor_lanche': valor_lanche,
                'valor_diaria': valor_diaria,
                'valor_total': valor_total,
                'fora_raio': fora_raio,
                'disponivel': motoboy.disponivel,
                'em_rota': motoboy.em_rota
            })

        # Ordenar por total de entregas (desc)
        ranking_data.sort(key=lambda x: x['total_entregas'], reverse=True)

        # Exibir ranking
        for i, m in enumerate(ranking_data, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else f"#{i}"))
            status = "🟢" if m['disponivel'] else "⚫"

            with st.expander(f"{medal} {m['nome']} - {m['total_entregas']} entregas | R$ {m['valor_total']:.2f}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("**📊 Estatísticas**")
                    st.markdown(f"Entregas: **{m['total_entregas']}**")
                    st.markdown(f"Tempo médio: **{m['tempo_medio']:.0f} min**")
                    if m['fora_raio'] > 0:
                        st.markdown(f"⚠️ Fora do raio: **{m['fora_raio']}**")
                with col2:
                    st.markdown("**💰 Valores**")
                    st.markdown(f"Base entregas: R$ {m['valor_entregas']:.2f}")
                    st.markdown(f"Extras km: R$ {m['valor_extras']:.2f}")
                    st.markdown(f"Alimentação: R$ {m['valor_lanche']:.2f}")
                    st.markdown(f"Diárias: R$ {m['valor_diaria']:.2f}")
                with col3:
                    st.markdown("**💵 Total**")
                    st.metric("", f"R$ {m['valor_total']:.2f}")
                    if m['cpf']:
                        st.caption(f"CPF: {m['cpf'][:3]}.***.***-{m['cpf'][-2:]}")
                    else:
                        st.caption("⚠️ Sem CPF (dados não preservados)")

    finally:
        session.close()


def pagamento_motoboys():
    """Aba de pagamento dos motoboys"""
    st.subheader("💸 Realizar Pagamento dos Motoboys")
    rest_id = st.session_state.restaurante_id
    session = get_db_session()

    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest_id
        ).first()

        # Filtro de período
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Período de", value=datetime.now().replace(day=1), key="pag_inicio")
        with col2:
            data_fim = st.date_input("Até", value=datetime.now(), key="pag_fim")

        st.markdown("---")

        # Buscar motoboys
        motoboys = session.query(Motoboy).filter(
            Motoboy.restaurante_id == rest_id,
            Motoboy.status == 'ativo'
        ).order_by(Motoboy.nome).all()

        if not motoboys:
            st.info("Nenhum motoboy ativo.")
            return

        # Seleção de motoboys
        st.markdown("### Selecionar Motoboys")
        motoboys_selecionados = st.multiselect(
            "Escolha os motoboys para pagamento:",
            options=[(m.id, m.nome) for m in motoboys],
            format_func=lambda x: x[1]
        )

        if not motoboys_selecionados:
            st.info("Selecione pelo menos um motoboy.")
            return

        st.markdown("---")

        # Para cada motoboy selecionado, exibir detalhes
        total_geral = 0
        for motoboy_id, motoboy_nome in motoboys_selecionados:
            entregas = session.query(Entrega).join(Pedido).filter(
                Pedido.restaurante_id == rest_id,
                Entrega.motoboy_id == motoboy_id,
                Entrega.status == 'entregue',
                Entrega.entregue_em >= datetime.combine(data_inicio, datetime.min.time()),
                Entrega.entregue_em <= datetime.combine(data_fim, datetime.max.time())
            ).all()

            valor_base = sum(e.valor_base_motoboy or 0 for e in entregas)
            valor_extras = sum(e.valor_extra_motoboy or 0 for e in entregas)
            valor_lanche = sum(e.valor_lanche or 0 for e in entregas)
            valor_diaria = sum(e.valor_diaria or 0 for e in entregas)
            valor_total = valor_base + valor_extras + valor_lanche + valor_diaria
            total_geral += valor_total

            with st.expander(f"📋 {motoboy_nome} - {len(entregas)} entregas | R$ {valor_total:.2f}", expanded=True):
                # Resumo de valores
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Taxa Base", f"R$ {valor_base:.2f}", help="Valor base por entrega")
                with col2:
                    st.metric("Extras km", f"R$ {valor_extras:.2f}", help="Adicional por km excedente")
                with col3:
                    st.metric("Alimentação", f"R$ {valor_lanche:.2f}", help="Valor para lanche")
                with col4:
                    st.metric("Diárias", f"R$ {valor_diaria:.2f}", help="Taxa diária fixa")

                st.markdown(f"**💵 TOTAL A PAGAR: R$ {valor_total:.2f}**")

                # Lista de entregas
                if st.checkbox("📜 Ver lista de entregas", key=f"lista_{motoboy_id}"):
                    if entregas:
                        for e in entregas:
                            pedido = e.pedido
                            data_str = e.entregue_em.strftime('%d/%m %H:%M') if e.entregue_em else 'N/A'
                            st.markdown(f"- **#{pedido.comanda}** | {data_str} | {e.distancia_km or 0:.1f}km | R$ {e.valor_motoboy or 0:.2f}")
                    else:
                        st.info("Nenhuma entrega no período.")

                # Exportar relatório CSV
                if entregas:
                    dados_csv = []
                    for e in entregas:
                        pedido = e.pedido
                        dados_csv.append({
                            'Data': e.entregue_em.strftime('%d/%m/%Y %H:%M') if e.entregue_em else 'N/A',
                            'Pedido': f'#{pedido.comanda}',
                            'Distancia_km': round(e.distancia_km or 0, 1),
                            'Valor_Base': round(e.valor_base_motoboy or 0, 2),
                            'Valor_Extra': round(e.valor_extra_motoboy or 0, 2),
                            'Valor_Lanche': round(e.valor_lanche or 0, 2),
                            'Valor_Diaria': round(e.valor_diaria or 0, 2),
                            'Valor_Total': round(e.valor_motoboy or 0, 2),
                        })
                    df = pd.DataFrame(dados_csv)
                    # Linha de totais
                    totais = pd.DataFrame([{
                        'Data': 'TOTAL', 'Pedido': f'{len(entregas)} entregas',
                        'Distancia_km': '', 'Valor_Base': valor_base,
                        'Valor_Extra': valor_extras, 'Valor_Lanche': valor_lanche,
                        'Valor_Diaria': valor_diaria, 'Valor_Total': valor_total,
                    }])
                    df_export = pd.concat([df, totais], ignore_index=True)
                    csv_data = df_export.to_csv(index=False, sep=';', decimal=',')
                    nome_arquivo = f"pagamento_{motoboy_nome.replace(' ','_')}_{data_inicio.strftime('%d%m%Y')}_{data_fim.strftime('%d%m%Y')}.csv"
                    st.download_button(
                        "📥 Exportar CSV",
                        data=csv_data, file_name=nome_arquivo,
                        mime='text/csv', key=f"csv_{motoboy_id}"
                    )

        # Total geral
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col2:
            st.metric("💰 TOTAL GERAL", f"R$ {total_geral:.2f}")

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

            # Caixa pode ser aberto independente do status do restaurante
            st.info("💡 O caixa pode ser aberto mesmo com o restaurante fechado.")

            with st.form("form_abrir"):
                valor = st.number_input("Valor de Abertura (R$)", min_value=0.0, value=100.0, step=10.0)
                if st.form_submit_button("💰 Abrir Caixa", type="primary", use_container_width=True):
                    novo = Caixa(
                        restaurante_id=rest_id,
                        data_abertura=datetime.now(),
                        operador_abertura=st.session_state.restaurante_dados['email'],
                        valor_abertura=valor,
                        total_vendas=0.0,
                        valor_retiradas=0.0,
                        status='aberto'
                    )
                    session.add(novo)
                    session.flush()
                    session.add(MovimentacaoCaixa(
                        caixa_id=novo.id, tipo='abertura',
                        valor=valor, descricao='Abertura de caixa', data_hora=datetime.now()
                    ))
                    session.commit()
                    st.toast("✅ Caixa aberto com sucesso!", icon="💰")
                    st.rerun()
        else:
            st.success("🟢 Caixa ABERTO")
            st.caption(f"Aberto em: {caixa.data_abertura.strftime('%d/%m/%Y %H:%M')}")

            # Calcular totais
            valor_abertura = caixa.valor_abertura or 0.0
            total_vendas = caixa.total_vendas or 0.0
            valor_retiradas = caixa.valor_retiradas or 0.0
            saldo = valor_abertura + total_vendas - valor_retiradas

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Abertura", f"R$ {valor_abertura:.2f}")
            with col2:
                st.metric("Vendas", f"R$ {total_vendas:.2f}")
            with col3:
                st.metric("Retiradas", f"R$ {valor_retiradas:.2f}")
            with col4:
                st.metric("Saldo", f"R$ {saldo:.2f}")

            st.markdown("---")

            # Formulário de retirada melhorado
            st.subheader("💸 Fazer Retirada")

            # Usar session_state para manter valores do formulário
            if 'valor_retirada' not in st.session_state:
                st.session_state.valor_retirada = 10.0
            if 'motivo_retirada' not in st.session_state:
                st.session_state.motivo_retirada = ""

            with st.form("form_retirada", clear_on_submit=True):
                col_ret1, col_ret2 = st.columns([1, 2])
                with col_ret1:
                    valor_ret = st.number_input(
                        "Valor (R$)",
                        min_value=0.01,
                        max_value=float(saldo) if saldo > 0 else 10000.0,
                        value=10.0,
                        step=10.0,
                        key="input_valor_retirada"
                    )
                with col_ret2:
                    motivo = st.text_input(
                        "Motivo da retirada *",
                        placeholder="Ex: Pagamento fornecedor, Troco, etc.",
                        key="input_motivo_retirada"
                    )

                submitted = st.form_submit_button("💸 Confirmar Retirada", type="primary", use_container_width=True)

                if submitted:
                    if not motivo or len(motivo.strip()) < 3:
                        st.error("❌ Informe o motivo da retirada (mínimo 3 caracteres)")
                    elif valor_ret > saldo:
                        st.error(f"❌ Valor maior que o saldo disponível (R$ {saldo:.2f})")
                    else:
                        # Registrar retirada
                        mov = MovimentacaoCaixa(
                            caixa_id=caixa.id,
                            tipo='retirada',
                            valor=valor_ret,
                            descricao=motivo.strip(),
                            data_hora=datetime.now()
                        )
                        session.add(mov)
                        caixa.valor_retiradas = (caixa.valor_retiradas or 0.0) + valor_ret
                        session.commit()
                        st.toast(f"✅ Retirada de R$ {valor_ret:.2f} registrada!", icon="💸")
                        time.sleep(0.5)
                        st.rerun()

            st.markdown("---")

            # Histórico de movimentações do dia
            with st.expander("📋 Movimentações do Caixa"):
                movimentacoes = session.query(MovimentacaoCaixa).filter(
                    MovimentacaoCaixa.caixa_id == caixa.id
                ).order_by(MovimentacaoCaixa.data_hora.desc()).limit(20).all()

                if movimentacoes:
                    for mov in movimentacoes:
                        tipo_icon = "💰" if mov.tipo == 'abertura' else ("💸" if mov.tipo == 'retirada' else "📦")
                        sinal = "-" if mov.tipo == 'retirada' else "+"
                        st.markdown(f"{tipo_icon} {mov.data_hora.strftime('%H:%M')} | {sinal}R$ {mov.valor:.2f} | {mov.descricao}")
                else:
                    st.info("Nenhuma movimentação registrada.")

            st.markdown("---")

            # Fechamento de caixa com valor contado
            st.subheader("🔒 Fechar Caixa")
            with st.form("form_fechar_caixa"):
                valor_contado = st.number_input(
                    "Valor em dinheiro contado (R$)",
                    min_value=0.0, value=round(saldo, 2), step=10.0,
                    help="Conte o dinheiro físico no caixa e informe aqui"
                )
                if st.form_submit_button("🔒 Confirmar Fechamento", type="primary", use_container_width=True):
                    diferenca = round(valor_contado - saldo, 2)
                    caixa.status = 'fechado'
                    caixa.data_fechamento = datetime.now()
                    caixa.valor_contado = valor_contado
                    caixa.diferenca = diferenca
                    caixa.operador_fechamento = st.session_state.restaurante_dados['email']
                    session.add(MovimentacaoCaixa(
                        caixa_id=caixa.id, tipo='fechamento',
                        valor=valor_contado,
                        descricao=f'Fechamento | Diferença: R$ {diferenca:+.2f}',
                        data_hora=datetime.now()
                    ))
                    session.commit()
                    if diferenca != 0:
                        st.warning(f"⚠️ Diferença de R$ {diferenca:+.2f} registrada!")
                    else:
                        st.toast("✅ Caixa fechado sem diferença!", icon="🔒")
                    time.sleep(0.5)
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

        tabs = st.tabs(["💰 Taxas", "🏍️ Motoboys", "🚀 Modo de Despacho", "🕐 Horários", "📍 Endereço"])

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
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    moto_base = st.number_input("Valor Base (R$)", value=config.valor_base_motoboy or 5.0, help="Valor fixo pago ao motoboy por entrega até a distância base")
                with col2:
                    moto_km = st.number_input("Valor/km Extra (R$)", value=config.valor_km_extra_motoboy or 1.0, help="Valor adicional por km acima da distância base")
                with col3:
                    moto_diaria = st.number_input("Taxa Diária (R$)", value=config.taxa_diaria or 0.0, help="Valor diário fixo pago ao motoboy (pode ser zero)")
                with col4:
                    moto_lanche = st.number_input("Alimentação (R$)", value=config.valor_lanche or 0.0, help="Valor adicional para lanche/alimentação")

                permitir_ver_saldo = st.checkbox(
                    "Motoboys podem ver saldo acumulado",
                    value=config.permitir_ver_saldo_motoboy if config.permitir_ver_saldo_motoboy is not None else True,
                    help="Quando desmarcado, os motoboys não poderão visualizar seus ganhos e estatísticas no app"
                )

                permitir_fora_raio = st.checkbox(
                    "Permitir finalizar entrega fora do raio de 50m",
                    value=config.permitir_finalizar_fora_raio if config.permitir_finalizar_fora_raio is not None else False,
                    help="Quando ativado, motoboys podem finalizar entregas mesmo fora do raio de 50m do endereço. ATENÇÃO: O ranking não será atestado como antifraude por localização."
                )
                if permitir_fora_raio:
                    st.warning("⚠️ O ranking de motoboys não será atestado como antifraude por localização")

                raio = st.number_input("Raio de Entrega (km)", value=config.raio_entrega_km or 10.0)
                max_pedidos = st.number_input("Máx. Pedidos/Rota", value=config.max_pedidos_por_rota or 5, min_value=1, max_value=10)

                if st.form_submit_button("💾 Salvar", type="primary"):
                    config.taxa_entrega_base = taxa_base
                    config.distancia_base_km = dist_base
                    config.taxa_km_extra = taxa_km
                    config.valor_base_motoboy = moto_base
                    config.valor_km_extra_motoboy = moto_km
                    config.taxa_diaria = moto_diaria
                    config.valor_lanche = moto_lanche
                    config.permitir_ver_saldo_motoboy = permitir_ver_saldo
                    config.permitir_finalizar_fora_raio = permitir_fora_raio
                    config.raio_entrega_km = raio
                    config.max_pedidos_por_rota = max_pedidos
                    session.commit()
                    st.success("✅ Salvo!")

        with tabs[1]:
            st.subheader("🚀 Modo de Prioridade de Entrega")

            st.markdown("""
            Escolha como os pedidos serão organizados para entrega:
            """)

            modo_atual = config.modo_prioridade_entrega or 'rapido_economico'

            # Explicação dos modos
            col_exp1, col_exp2, col_exp3 = st.columns(3)

            with col_exp1:
                st.markdown("#### 🏎️ Rápido Econômico")
                st.markdown("""
                - Otimiza por proximidade (TSP)
                - Menor km percorrido
                - Ideal para delivery denso
                """)
                if modo_atual == 'rapido_economico':
                    st.success("✅ Ativo")

            with col_exp2:
                st.markdown("#### ⏰ Cronológico Inteligente")
                st.markdown("""
                - Agrupa pedidos próximos em tempo
                - Respeita ordem de chegada
                - Ideal para alto volume
                """)
                if modo_atual == 'cronologico_inteligente':
                    st.success("✅ Ativo")

            with col_exp3:
                st.markdown("#### 🖐️ Manual")
                st.markdown("""
                - Você atribui cada pedido
                - Controle total
                - Ideal para operações especiais
                """)
                if modo_atual == 'manual':
                    st.success("✅ Ativo")

            st.markdown("---")

            with st.form("form_modo_despacho"):
                opcoes_modo = {
                    'rapido_economico': '🏎️ Rápido Econômico (TSP por proximidade)',
                    'cronologico_inteligente': '⏰ Cronológico Inteligente (Agrupa por tempo)',
                    'manual': '🖐️ Manual (Você atribui cada pedido)'
                }

                modo_selecionado = st.radio(
                    "Selecione o modo:",
                    list(opcoes_modo.keys()),
                    format_func=lambda x: opcoes_modo[x],
                    index=list(opcoes_modo.keys()).index(modo_atual)
                )

                if st.form_submit_button("💾 Salvar Modo", type="primary", use_container_width=True):
                    config.modo_prioridade_entrega = modo_selecionado
                    session.commit()
                    st.success(f"✅ Modo alterado para: {opcoes_modo[modo_selecionado]}")
                    st.rerun()

        with tabs[2]:
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

        with tabs[3]:
            rest = session.get(Restaurante, rest_id)
            with st.form("form_endereco"):
                endereco = st.text_area("Endereço Completo", value=rest.endereco_completo or "")

                # Mostrar coordenadas atuais
                if rest.latitude and rest.longitude:
                    st.caption(f"📍 Coordenadas atuais: {rest.latitude:.6f}, {rest.longitude:.6f}")
                else:
                    st.warning("⚠️ Coordenadas não definidas. Salve o endereço para geocodificar.")

                if st.form_submit_button("💾 Salvar e Geocodificar"):
                    if endereco != rest.endereco_completo:
                        # Endereço mudou - atualizar coordenadas via geocodificação
                        resultado = atualizar_coordenadas_restaurante(rest_id, endereco, session)
                        if resultado['sucesso']:
                            st.success(f"✅ Endereço salvo! Coordenadas: {resultado['latitude']:.6f}, {resultado['longitude']:.6f}")
                            if resultado.get('cidade'):
                                st.info(f"📍 {resultado.get('cidade')}, {resultado.get('estado', '')}")
                        else:
                            # Salvar endereço mesmo sem coordenadas
                            rest.endereco_completo = endereco
                            session.commit()
                            st.warning(f"⚠️ Endereço salvo, mas não foi possível geocodificar: {resultado.get('erro', 'Erro desconhecido')}")
                    else:
                        # Endereço não mudou - só confirmar
                        st.info("ℹ️ Endereço não foi alterado.")

    finally:
        session.close()


# ==================== CARDÁPIO ====================
def tela_gerenciar_cardapio():
    st.title("🍕 Gerenciamento de Cardápio")
    rest_id = st.session_state.restaurante_id

    tab_cat, tab_prod, tab_var, tab_bairro, tab_promo, tab_fidel, tab_config = st.tabs([
        "📂 Categorias", "🍽️ Produtos", "🔧 Variações",
        "📍 Bairros", "🎫 Promoções", "⭐ Fidelidade", "⚙️ Config Site"
    ])

    # ==================== TAB CATEGORIAS ====================
    with tab_cat:
        _tab_categorias(rest_id)

    # ==================== TAB PRODUTOS ====================
    with tab_prod:
        _tab_produtos(rest_id)

    # ==================== TAB VARIAÇÕES ====================
    with tab_var:
        _tab_variacoes(rest_id)

    # ==================== TAB BAIRROS ====================
    with tab_bairro:
        _tab_bairros(rest_id)

    # ==================== TAB PROMOÇÕES ====================
    with tab_promo:
        _tab_promocoes(rest_id)

    # ==================== TAB FIDELIDADE ====================
    with tab_fidel:
        _tab_fidelidade(rest_id)

    # ==================== TAB CONFIG SITE ====================
    with tab_config:
        _tab_config_site(rest_id)


# ==================== SUB-FUNÇÕES DO CARDÁPIO ====================

def _tab_categorias(rest_id):
    """Gestão de categorias do cardápio"""
    st.subheader("📂 Categorias do Cardápio")
    session = get_db_session()
    try:
        categorias = session.query(CategoriaMenu).filter(
            CategoriaMenu.restaurante_id == rest_id
        ).order_by(CategoriaMenu.ordem_exibicao).all()

        # Botão carregar padrão
        site_cfg = session.query(SiteConfig).filter(SiteConfig.restaurante_id == rest_id).first()
        tipo_rest = site_cfg.tipo_restaurante if site_cfg else "geral"

        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("📥 Carregar Categorias Padrão", key="btn_cat_padrao"):
                from backend.app.utils.menu_templates import criar_categorias_padrao
                criar_categorias_padrao(rest_id, tipo_rest, session)
                session.commit()
                st.success("Categorias padrão carregadas!")
                st.rerun()

        # Formulário nova categoria
        with st.expander("➕ Nova Categoria", expanded=False):
            with st.form("form_nova_cat", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nome = c1.text_input("Nome", placeholder="Ex: 🍕 Pizzas Salgadas")
                icone = c2.text_input("Ícone (emoji)", placeholder="🍕")
                descricao = st.text_input("Descrição (opcional)")
                ordem = st.number_input("Ordem de exibição", min_value=0, value=len(categorias) + 1)
                if st.form_submit_button("Salvar Categoria"):
                    if nome:
                        nova = CategoriaMenu(
                            restaurante_id=rest_id, nome=nome, icone=icone,
                            descricao=descricao, ordem_exibicao=ordem, ativo=True
                        )
                        session.add(nova)
                        session.commit()
                        st.success(f"Categoria '{nome}' criada!")
                        st.rerun()
                    else:
                        st.warning("Nome é obrigatório.")

        # Listar categorias
        if not categorias:
            st.info("Nenhuma categoria cadastrada. Clique em 'Carregar Categorias Padrão' para começar.")
            return

        for cat in categorias:
            cols = st.columns([0.5, 3, 1, 1, 1, 1])
            cols[0].write(f"**{cat.ordem_exibicao}**")
            cols[1].write(f"{cat.icone or ''} {cat.nome}")
            cols[2].write("✅ Ativo" if cat.ativo else "❌ Inativo")

            # Mover ordem
            if cols[3].button("⬆️", key=f"cat_up_{cat.id}"):
                if cat.ordem_exibicao > 1:
                    anterior = session.query(CategoriaMenu).filter(
                        CategoriaMenu.restaurante_id == rest_id,
                        CategoriaMenu.ordem_exibicao == cat.ordem_exibicao - 1
                    ).first()
                    if anterior:
                        anterior.ordem_exibicao += 1
                    cat.ordem_exibicao -= 1
                    session.commit()
                    st.rerun()

            # Ativar/desativar
            label_ativo = "Desativar" if cat.ativo else "Ativar"
            if cols[4].button(label_ativo, key=f"cat_tog_{cat.id}"):
                cat.ativo = not cat.ativo
                session.commit()
                st.rerun()

            # Editar
            if cols[5].button("✏️", key=f"cat_edit_{cat.id}"):
                st.session_state[f"edit_cat_{cat.id}"] = True

            if st.session_state.get(f"edit_cat_{cat.id}", False):
                with st.form(f"form_edit_cat_{cat.id}"):
                    e1, e2 = st.columns(2)
                    novo_nome = e1.text_input("Nome", value=cat.nome, key=f"en_{cat.id}")
                    novo_icone = e2.text_input("Ícone", value=cat.icone or "", key=f"ei_{cat.id}")
                    nova_desc = st.text_input("Descrição", value=cat.descricao or "", key=f"ed_{cat.id}")
                    nova_ordem = st.number_input("Ordem", value=cat.ordem_exibicao, key=f"eo_{cat.id}")
                    if st.form_submit_button("Atualizar"):
                        cat.nome = novo_nome
                        cat.icone = novo_icone
                        cat.descricao = nova_desc
                        cat.ordem_exibicao = nova_ordem
                        session.commit()
                        st.session_state[f"edit_cat_{cat.id}"] = False
                        st.success("Categoria atualizada!")
                        st.rerun()
    finally:
        session.close()


def _tab_produtos(rest_id):
    """Gestão de produtos do cardápio"""
    st.subheader("🍽️ Produtos")
    session = get_db_session()
    try:
        categorias = session.query(CategoriaMenu).filter(
            CategoriaMenu.restaurante_id == rest_id, CategoriaMenu.ativo == True
        ).order_by(CategoriaMenu.ordem_exibicao).all()

        if not categorias:
            st.warning("Cadastre categorias primeiro na aba 'Categorias'.")
            return

        # Filtro por categoria
        cat_opcoes = {c.nome: c.id for c in categorias}
        cat_selecionada = st.selectbox("Filtrar por categoria", list(cat_opcoes.keys()), key="filtro_cat_prod")
        cat_id = cat_opcoes[cat_selecionada]

        produtos = session.query(Produto).filter(
            Produto.restaurante_id == rest_id,
            Produto.categoria_id == cat_id
        ).order_by(Produto.ordem_exibicao).all()

        # Formulário novo produto
        with st.expander("➕ Novo Produto", expanded=False):
            with st.form("form_novo_prod", clear_on_submit=True):
                p1, p2 = st.columns(2)
                nome = p1.text_input("Nome do produto")
                preco = p2.number_input("Preço (R$)", min_value=0.0, step=0.5, format="%.2f")
                descricao = st.text_area("Descrição", height=80)
                imagem_url = st.text_input("URL da imagem (opcional)")
                pc1, pc2, pc3 = st.columns(3)
                destaque = pc1.checkbox("Destaque")
                promo = pc2.checkbox("Em promoção")
                preco_promo = pc3.number_input("Preço promocional", min_value=0.0, step=0.5, format="%.2f") if promo else 0.0
                ec1, ec2 = st.columns(2)
                estoque_ilim = ec1.checkbox("Estoque ilimitado", value=True)
                estoque_qtd = ec2.number_input("Quantidade em estoque", min_value=0, value=0) if not estoque_ilim else 0
                ordem = st.number_input("Ordem de exibição", min_value=0, value=len(produtos) + 1)

                if st.form_submit_button("Salvar Produto"):
                    if nome and preco > 0:
                        novo = Produto(
                            restaurante_id=rest_id, categoria_id=cat_id,
                            nome=nome, descricao=descricao, preco=preco,
                            imagem_url=imagem_url or None, destaque=destaque,
                            promocao=promo, preco_promocional=preco_promo if promo else None,
                            estoque_ilimitado=estoque_ilim, estoque_quantidade=estoque_qtd,
                            ordem_exibicao=ordem, disponivel=True
                        )
                        session.add(novo)
                        session.commit()
                        st.success(f"Produto '{nome}' criado!")
                        st.rerun()
                    else:
                        st.warning("Nome e preço são obrigatórios.")

        # Listar produtos
        if not produtos:
            st.info("Nenhum produto nesta categoria.")
            return

        for prod in produtos:
            with st.container():
                cols = st.columns([3, 1, 1, 1, 1])
                nome_display = f"{'⭐ ' if prod.destaque else ''}{prod.nome}"
                if prod.promocao and prod.preco_promocional:
                    cols[0].write(f"**{nome_display}** — ~~R$ {prod.preco:.2f}~~ R$ {prod.preco_promocional:.2f}")
                else:
                    cols[0].write(f"**{nome_display}** — R$ {prod.preco:.2f}")

                cols[1].write("✅" if prod.disponivel else "❌")

                if cols[2].button("✏️", key=f"prod_edit_{prod.id}"):
                    st.session_state[f"edit_prod_{prod.id}"] = True

                label_disp = "Indisponível" if prod.disponivel else "Disponível"
                if cols[3].button(label_disp, key=f"prod_tog_{prod.id}"):
                    prod.disponivel = not prod.disponivel
                    session.commit()
                    st.rerun()

                if cols[4].button("🗑️", key=f"prod_del_{prod.id}"):
                    session.delete(prod)
                    session.commit()
                    st.success("Produto removido!")
                    st.rerun()

                # Formulário editar
                if st.session_state.get(f"edit_prod_{prod.id}", False):
                    with st.form(f"form_edit_prod_{prod.id}"):
                        ep1, ep2 = st.columns(2)
                        novo_nome = ep1.text_input("Nome", value=prod.nome, key=f"epn_{prod.id}")
                        novo_preco = ep2.number_input("Preço", value=prod.preco, step=0.5, format="%.2f", key=f"epp_{prod.id}")
                        nova_desc = st.text_area("Descrição", value=prod.descricao or "", key=f"epd_{prod.id}")
                        nova_img = st.text_input("URL imagem", value=prod.imagem_url or "", key=f"epi_{prod.id}")
                        epc1, epc2 = st.columns(2)
                        novo_dest = epc1.checkbox("Destaque", value=prod.destaque, key=f"epdt_{prod.id}")
                        nova_promo = epc2.checkbox("Promoção", value=prod.promocao, key=f"eppr_{prod.id}")
                        novo_preco_promo = st.number_input("Preço promo", value=prod.preco_promocional or 0.0, format="%.2f", key=f"eppp_{prod.id}") if nova_promo else None
                        nova_cat = st.selectbox("Categoria", list(cat_opcoes.keys()),
                            index=list(cat_opcoes.values()).index(prod.categoria_id) if prod.categoria_id in cat_opcoes.values() else 0,
                            key=f"epc_{prod.id}")
                        nova_ordem = st.number_input("Ordem", value=prod.ordem_exibicao, key=f"epo_{prod.id}")
                        if st.form_submit_button("Atualizar Produto"):
                            prod.nome = novo_nome
                            prod.preco = novo_preco
                            prod.descricao = nova_desc
                            prod.imagem_url = nova_img or None
                            prod.destaque = novo_dest
                            prod.promocao = nova_promo
                            prod.preco_promocional = novo_preco_promo
                            prod.categoria_id = cat_opcoes[nova_cat]
                            prod.ordem_exibicao = nova_ordem
                            session.commit()
                            st.session_state[f"edit_prod_{prod.id}"] = False
                            st.success("Produto atualizado!")
                            st.rerun()
                st.divider()
    finally:
        session.close()


def _tab_variacoes(rest_id):
    """Gestão de variações por produto"""
    st.subheader("🔧 Variações de Produto")
    session = get_db_session()
    try:
        produtos = session.query(Produto).filter(
            Produto.restaurante_id == rest_id, Produto.disponivel == True
        ).order_by(Produto.nome).all()

        if not produtos:
            st.warning("Cadastre produtos primeiro.")
            return

        prod_opcoes = {p.nome: p.id for p in produtos}
        prod_selecionado = st.selectbox("Selecione o produto", list(prod_opcoes.keys()), key="sel_prod_var")
        prod_id = prod_opcoes[prod_selecionado]

        TIPOS_VARIACAO = ["tamanho", "sabor", "borda", "adicional", "ponto_carne"]
        tabs_var = st.tabs([t.capitalize() for t in TIPOS_VARIACAO])

        for i, tipo in enumerate(TIPOS_VARIACAO):
            with tabs_var[i]:
                variacoes = session.query(VariacaoProduto).filter(
                    VariacaoProduto.produto_id == prod_id,
                    VariacaoProduto.tipo_variacao == tipo
                ).order_by(VariacaoProduto.ordem).all()

                # Novo
                with st.expander(f"➕ Novo {tipo.capitalize()}", expanded=False):
                    with st.form(f"form_var_{tipo}_{prod_id}", clear_on_submit=True):
                        v1, v2 = st.columns(2)
                        nome = v1.text_input("Nome", key=f"vn_{tipo}_{prod_id}")
                        preco_ad = v2.number_input("Preço adicional (R$)", min_value=0.0, step=0.5, format="%.2f", key=f"vp_{tipo}_{prod_id}")
                        desc = st.text_input("Descrição (opcional)", key=f"vd_{tipo}_{prod_id}")
                        ordem = st.number_input("Ordem", min_value=0, value=len(variacoes) + 1, key=f"vo_{tipo}_{prod_id}")
                        if st.form_submit_button("Salvar"):
                            if nome:
                                nova = VariacaoProduto(
                                    produto_id=prod_id, tipo_variacao=tipo,
                                    nome=nome, descricao=desc, preco_adicional=preco_ad,
                                    ordem=ordem, ativo=True
                                )
                                session.add(nova)
                                session.commit()
                                st.success(f"{tipo.capitalize()} '{nome}' adicionado!")
                                st.rerun()

                # Listar
                if not variacoes:
                    st.info(f"Nenhum {tipo} cadastrado para este produto.")
                    continue

                for v in variacoes:
                    vc = st.columns([3, 1, 1, 1])
                    vc[0].write(f"**{v.nome}** — +R$ {v.preco_adicional:.2f}")
                    vc[1].write("✅" if v.ativo else "❌")
                    tog_label = "Desativar" if v.ativo else "Ativar"
                    if vc[2].button(tog_label, key=f"vtog_{v.id}"):
                        v.ativo = not v.ativo
                        session.commit()
                        st.rerun()
                    if vc[3].button("🗑️", key=f"vdel_{v.id}"):
                        session.delete(v)
                        session.commit()
                        st.rerun()

        # Botão carregar variações padrão
        st.divider()
        site_cfg = session.query(SiteConfig).filter(SiteConfig.restaurante_id == rest_id).first()
        tipo_rest = site_cfg.tipo_restaurante if site_cfg else "geral"
        if st.button("📥 Carregar variações padrão do template", key="btn_var_padrao"):
            from backend.app.utils.menu_templates import get_template
            tmpl = get_template(tipo_rest)
            cfg = tmpl.get("config_produto", {})
            count = 0
            # Tamanhos
            for t in cfg.get("tamanhos_padrao", []):
                session.add(VariacaoProduto(
                    produto_id=prod_id, tipo_variacao="tamanho",
                    nome=t["nome"], preco_adicional=t.get("preco_base", 0), ordem=count, ativo=True
                ))
                count += 1
            # Bordas
            for b in cfg.get("bordas_padrao", []):
                session.add(VariacaoProduto(
                    produto_id=prod_id, tipo_variacao="borda",
                    nome=b["nome"], preco_adicional=b.get("preco", 0), ordem=count, ativo=True
                ))
                count += 1
            # Adicionais
            for a in cfg.get("adicionais_padrao", []):
                session.add(VariacaoProduto(
                    produto_id=prod_id, tipo_variacao="adicional",
                    nome=a["nome"], preco_adicional=a.get("preco", 0), ordem=count, ativo=True
                ))
                count += 1
            # Ponto carne
            for pc in cfg.get("pontos_carne", []):
                session.add(VariacaoProduto(
                    produto_id=prod_id, tipo_variacao="ponto_carne",
                    nome=pc, preco_adicional=0, ordem=count, ativo=True
                ))
                count += 1
            session.commit()
            st.success(f"{count} variações padrão carregadas para '{prod_selecionado}'!")
            st.rerun()
    finally:
        session.close()


def _tab_bairros(rest_id):
    """Gestão de bairros de entrega"""
    st.subheader("📍 Bairros de Entrega")
    st.caption("Opcional: o sistema também calcula taxa por km. Use bairros para taxas fixas por região.")
    session = get_db_session()
    try:
        bairros = session.query(BairroEntrega).filter(
            BairroEntrega.restaurante_id == rest_id
        ).order_by(BairroEntrega.nome).all()

        with st.expander("➕ Novo Bairro", expanded=False):
            with st.form("form_novo_bairro", clear_on_submit=True):
                b1, b2, b3 = st.columns(3)
                nome = b1.text_input("Nome do bairro")
                taxa = b2.number_input("Taxa de entrega (R$)", min_value=0.0, step=0.5, format="%.2f")
                tempo = b3.number_input("Tempo estimado (min)", min_value=5, value=30)
                if st.form_submit_button("Salvar Bairro"):
                    if nome:
                        session.add(BairroEntrega(
                            restaurante_id=rest_id, nome=nome,
                            taxa_entrega=taxa, tempo_estimado_min=tempo, ativo=True
                        ))
                        session.commit()
                        st.success(f"Bairro '{nome}' adicionado!")
                        st.rerun()

        if not bairros:
            st.info("Nenhum bairro cadastrado.")
            return

        for b in bairros:
            bc = st.columns([3, 1, 1, 1])
            bc[0].write(f"**{b.nome}** — R$ {b.taxa_entrega:.2f} | {b.tempo_estimado_min} min")
            bc[1].write("✅" if b.ativo else "❌")
            tog = "Desativar" if b.ativo else "Ativar"
            if bc[2].button(tog, key=f"btog_{b.id}"):
                b.ativo = not b.ativo
                session.commit()
                st.rerun()
            if bc[3].button("🗑️", key=f"bdel_{b.id}"):
                session.delete(b)
                session.commit()
                st.rerun()
    finally:
        session.close()


def _tab_promocoes(rest_id):
    """Gestão de promoções e cupons"""
    st.subheader("🎫 Promoções e Cupons")
    session = get_db_session()
    try:
        promos = session.query(Promocao).filter(
            Promocao.restaurante_id == rest_id
        ).order_by(Promocao.criado_em.desc()).all()

        with st.expander("➕ Nova Promoção", expanded=False):
            with st.form("form_nova_promo", clear_on_submit=True):
                nome = st.text_input("Nome da promoção")
                descricao = st.text_area("Descrição", height=60)
                pr1, pr2 = st.columns(2)
                tipo = pr1.selectbox("Tipo de desconto", ["percentual", "fixo"])
                valor = pr2.number_input("Valor do desconto", min_value=0.0, step=0.5, format="%.2f")
                pr3, pr4 = st.columns(2)
                pedido_min = pr3.number_input("Pedido mínimo (R$)", min_value=0.0, format="%.2f")
                desc_max = pr4.number_input("Desconto máximo (R$)", min_value=0.0, format="%.2f", help="Para desconto percentual")
                codigo = st.text_input("Código do cupom (opcional)", placeholder="EX: PROMO10")
                dt1, dt2 = st.columns(2)
                data_ini = dt1.date_input("Data início")
                data_fim = dt2.date_input("Data fim")
                uso_lim = st.checkbox("Limitar número de usos")
                limite = st.number_input("Limite de usos", min_value=1, value=100) if uso_lim else None

                if st.form_submit_button("Salvar Promoção"):
                    if nome and valor > 0:
                        session.add(Promocao(
                            restaurante_id=rest_id, nome=nome, descricao=descricao,
                            tipo_desconto=tipo, valor_desconto=valor,
                            valor_pedido_minimo=pedido_min, desconto_maximo=desc_max or None,
                            codigo_cupom=codigo.upper() if codigo else None,
                            data_inicio=datetime.combine(data_ini, datetime.min.time()),
                            data_fim=datetime.combine(data_fim, datetime.max.time()),
                            uso_limitado=uso_lim, limite_usos=limite, ativo=True
                        ))
                        session.commit()
                        st.success(f"Promoção '{nome}' criada!")
                        st.rerun()

        if not promos:
            st.info("Nenhuma promoção cadastrada.")
            return

        for p in promos:
            with st.container():
                pc = st.columns([3, 1, 1, 1])
                tipo_txt = f"{p.valor_desconto}%" if p.tipo_desconto == "percentual" else f"R$ {p.valor_desconto:.2f}"
                cupom_txt = f" | Cupom: {p.codigo_cupom}" if p.codigo_cupom else ""
                pc[0].write(f"**{p.nome}** — {tipo_txt}{cupom_txt}")
                pc[1].write("✅" if p.ativo else "❌")
                tog = "Desativar" if p.ativo else "Ativar"
                if pc[2].button(tog, key=f"ptog_{p.id}"):
                    p.ativo = not p.ativo
                    session.commit()
                    st.rerun()
                if pc[3].button("🗑️", key=f"pdel_{p.id}"):
                    session.delete(p)
                    session.commit()
                    st.rerun()
                if p.usos_realizados:
                    st.caption(f"Usos: {p.usos_realizados}" + (f"/{p.limite_usos}" if p.uso_limitado else ""))
                st.divider()
    finally:
        session.close()


def _tab_fidelidade(rest_id):
    """Gestão de prêmios de fidelidade"""
    st.subheader("⭐ Prêmios de Fidelidade")
    session = get_db_session()
    try:
        premios = session.query(PremioFidelidade).filter(
            PremioFidelidade.restaurante_id == rest_id
        ).order_by(PremioFidelidade.ordem_exibicao).all()

        with st.expander("➕ Novo Prêmio", expanded=False):
            with st.form("form_novo_premio", clear_on_submit=True):
                nome = st.text_input("Nome do prêmio")
                descricao = st.text_area("Descrição", height=60)
                fp1, fp2, fp3 = st.columns(3)
                tipo = fp1.selectbox("Tipo", ["desconto", "item_gratis", "brinde"])
                custo = fp2.number_input("Custo em pontos", min_value=1, value=100)
                valor = fp3.text_input("Valor/Item", placeholder="10% desconto ou Nome do item")
                ordem = st.number_input("Ordem exibição", min_value=0, value=len(premios) + 1)
                if st.form_submit_button("Salvar Prêmio"):
                    if nome:
                        session.add(PremioFidelidade(
                            restaurante_id=rest_id, nome=nome, descricao=descricao,
                            tipo_premio=tipo, custo_pontos=custo, valor_premio=valor,
                            ordem_exibicao=ordem, ativo=True
                        ))
                        session.commit()
                        st.success(f"Prêmio '{nome}' criado!")
                        st.rerun()

        if not premios:
            st.info("Nenhum prêmio cadastrado.")
            return

        for pr in premios:
            prc = st.columns([3, 1, 1, 1])
            prc[0].write(f"**{pr.nome}** — {pr.custo_pontos} pts | {pr.tipo_premio}")
            prc[1].write("✅" if pr.ativo else "❌")
            tog = "Desativar" if pr.ativo else "Ativar"
            if prc[2].button(tog, key=f"frtog_{pr.id}"):
                pr.ativo = not pr.ativo
                session.commit()
                st.rerun()
            if prc[3].button("🗑️", key=f"frdel_{pr.id}"):
                session.delete(pr)
                session.commit()
                st.rerun()
    finally:
        session.close()


def _tab_config_site(rest_id):
    """Configuração do site do cliente"""
    st.subheader("⚙️ Configuração do Site")
    session = get_db_session()
    try:
        config = session.query(SiteConfig).filter(SiteConfig.restaurante_id == rest_id).first()

        if not config:
            st.warning("Site não configurado. Criando configuração padrão...")
            if st.button("Criar configuração padrão"):
                from backend.app.utils.menu_templates import criar_site_config_padrao
                criar_site_config_padrao(rest_id, "geral", {}, session)
                session.commit()
                st.success("Configuração criada!")
                st.rerun()
            return

        with st.form("form_config_site"):
            TIPOS = ["pizzaria", "hamburgueria", "japones", "churrascaria", "la_carte", "acai", "marmitex", "geral"]
            tipo_idx = TIPOS.index(config.tipo_restaurante) if config.tipo_restaurante in TIPOS else len(TIPOS) - 1
            tipo = st.selectbox("Tipo de restaurante", TIPOS, index=tipo_idx)

            st.markdown("**Visual**")
            vc1, vc2 = st.columns(2)
            cor_pri = vc1.color_picker("Cor primária", value=config.tema_cor_primaria or "#FF6B35")
            cor_sec = vc2.color_picker("Cor secundária", value=config.tema_cor_secundaria or "#004E89")
            logo = st.text_input("URL do logo", value=config.logo_url or "")
            banner = st.text_input("URL do banner", value=config.banner_principal_url or "")

            st.markdown("**WhatsApp**")
            wc1, wc2 = st.columns(2)
            whats_num = wc1.text_input("Número WhatsApp", value=config.whatsapp_numero or "")
            whats_ativo = wc2.checkbox("WhatsApp ativo", value=config.whatsapp_ativo)

            st.markdown("**Operacional**")
            oc1, oc2, oc3 = st.columns(3)
            ped_min = oc1.number_input("Pedido mínimo (R$)", value=config.pedido_minimo or 0.0, format="%.2f")
            t_entrega = oc2.number_input("Tempo entrega (min)", value=config.tempo_entrega_estimado or 50)
            t_retirada = oc3.number_input("Tempo retirada (min)", value=config.tempo_retirada_estimado or 20)
            site_ativo = st.checkbox("Site ativo", value=config.site_ativo)

            st.markdown("**Formas de Pagamento**")
            pgc1, pgc2, pgc3, pgc4 = st.columns(4)
            ac_din = pgc1.checkbox("Dinheiro", value=config.aceita_dinheiro)
            ac_cart = pgc2.checkbox("Cartão", value=config.aceita_cartao)
            ac_pix = pgc3.checkbox("PIX", value=config.aceita_pix)
            ac_vale = pgc4.checkbox("Vale Refeição", value=config.aceita_vale_refeicao)

            if st.form_submit_button("💾 Salvar Configuração"):
                config.tipo_restaurante = tipo
                config.tema_cor_primaria = cor_pri
                config.tema_cor_secundaria = cor_sec
                config.logo_url = logo or None
                config.banner_principal_url = banner or None
                config.whatsapp_numero = whats_num or None
                config.whatsapp_ativo = whats_ativo
                config.pedido_minimo = ped_min
                config.tempo_entrega_estimado = t_entrega
                config.tempo_retirada_estimado = t_retirada
                config.site_ativo = site_ativo
                config.aceita_dinheiro = ac_din
                config.aceita_cartao = ac_cart
                config.aceita_pix = ac_pix
                config.aceita_vale_refeicao = ac_vale
                session.commit()
                st.success("Configuração salva!")
                st.rerun()

        # Link de preview
        restaurante = session.query(Restaurante).filter(Restaurante.id == rest_id).first()
        if restaurante and restaurante.codigo_acesso:
            st.markdown(f"**Preview do site:** `/cliente/{restaurante.codigo_acesso}`")
    finally:
        session.close()


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
