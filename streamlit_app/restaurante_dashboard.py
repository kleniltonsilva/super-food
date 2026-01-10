"""
Dashboard do Restaurante - Sistema Super Food
Interface completa para gerenciamento de pedidos, motoboys e configurações
"""
import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime
import os
from dotenv import load_dotenv
import json
import plotly.express as px

# ============================================
# 🔧 CARREGAR VARIÁVEIS DE AMBIENTE
# ============================================
load_dotenv()

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

if not MAPBOX_TOKEN:
    st.error("⚠️ MAPBOX_TOKEN não configurado no .env")
    st.stop()

st.set_page_config(
    page_title="Dashboard Restaurante - Super Food",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================
# ✅ FUNÇÕES DE VALIDAÇÃO (NOVAS)
# ============================================

def validar_telefone(telefone: str) -> tuple[bool, str]:
    """
    Valida telefone antes de enviar para API.
    Retorna (é_válido, mensagem_erro)
    """
    telefone = telefone.strip()
    
    if not telefone:
        return True, ""  # Telefone é opcional em alguns casos
    
    if len(telefone) < 10:
        return False, "❌ Telefone deve ter no mínimo 10 caracteres (ex: 11999999999)"
    
    # Opcional: validar se contém apenas números
    telefone_limpo = telefone.replace("+", "").replace("-", "").replace(" ", "").replace("(", "").replace(")", "")
    if not telefone_limpo.isdigit():
        return False, "❌ Telefone deve conter apenas números (aceita +, -, espaços, parênteses)"
    
    return True, ""


def validar_senha_bytes(senha: str, campo_nome: str = "Senha") -> tuple[bool, str]:
    """
    Valida senha/código respeitando limite bcrypt de 72 bytes.
    Retorna (é_válido, mensagem_erro)
    """
    if not senha:
        return False, f"❌ {campo_nome} não pode estar vazio"
    
    tamanho_bytes = len(senha.encode("utf-8"))
    
    if tamanho_bytes > 72:
        return False, f"❌ {campo_nome} muito longa ({tamanho_bytes} bytes). Máximo 72 bytes (≈72 caracteres ASCII). Reduza o tamanho."
    
    if len(senha) < 6:
        return False, f"❌ {campo_nome} deve ter no mínimo 6 caracteres"
    
    return True, ""


# ============================================
# 🔐 FUNÇÕES DE AUTENTICAÇÃO
# ============================================

def fazer_login(email: str, senha: str) -> dict:
    """Autentica restaurante via API"""
    try:
        response = requests.post(
            f"{API_URL}/restaurantes/login",
            data={"username": email, "password": senha},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            erro = response.json().get("detail", "Erro desconhecido")
            return {"error": erro}
    except requests.exceptions.ConnectionError:
        return {"error": "Não foi possível conectar à API. Backend offline?"}
    except Exception as e:
        return {"error": f"Erro: {str(e)}"}


def buscar_dados_restaurante(token: str) -> dict:
    """Busca dados do restaurante autenticado"""
    try:
        response = requests.get(
            f"{API_URL}/restaurantes/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        return response.json() if response.status_code == 200 else None
    except:
        return None


def fazer_logout():
    """Limpa session e desloga"""
    st.session_state.clear()
    st.rerun()


# ============================================
# 🎨 TELA DE LOGIN
# ============================================

if "token" not in st.session_state or st.session_state.token is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.title("🍕 Super Food")
        st.subheader("Login Restaurante")
        
        with st.form("login_form"):
            email = st.text_input("📧 Email", placeholder="seu@email.com")
            senha = st.text_input("🔒 Senha", type="password")
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if submit:
                if not email or not senha:
                    st.error("Preencha todos os campos")
                else:
                    # ========== VALIDAÇÃO DE SENHA ANTES DO LOGIN ==========
                    senha_valida, erro_senha = validar_senha_bytes(senha, "Senha")
                    
                    if not senha_valida:
                        st.error(erro_senha)
                    else:
                        with st.spinner("Autenticando..."):
                            resultado = fazer_login(email, senha)
                            
                            if "error" in resultado:
                                st.error(f"❌ {resultado['error']}")
                            else:
                                st.session_state.token = resultado["access_token"]
                                st.session_state.restaurante_id = resultado["user_id"]
                                st.session_state.restaurante_nome = resultado["nome"]
                                st.success(f"✅ Bem-vindo, {resultado['nome']}!")
                                st.rerun()
        
        st.caption("💡 Não tem conta? Contate o administrador.")
    st.stop()


# ============================================
# 🎯 DASHBOARD AUTENTICADO
# ============================================

# Validar token
restaurante = buscar_dados_restaurante(st.session_state.token)

if not restaurante:
    st.error("🔐 Sessão expirada. Faça login novamente.")
    if st.button("Voltar ao Login"):
        fazer_logout()
    st.stop()

# Atualizar session
st.session_state.restaurante_id = restaurante["id"]
st.session_state.restaurante_nome = restaurante["nome_fantasia"]


# ============================================
# 📊 SIDEBAR - NAVEGAÇÃO E INFO
# ============================================

with st.sidebar:
    st.title(f"🍕 {restaurante['nome_fantasia']}")
    st.caption(f"📧 {restaurante['email']}")
    st.caption(f"📞 {restaurante['telefone']}")
    
    st.divider()
    
    # Informações do plano
    planos_info = {
        "basico": {"nome": "Básico", "motoboys": 3, "cor": "🟢"},
        "medio": {"nome": "Médio", "motoboys": 5, "cor": "🟡"},
        "premium": {"nome": "Premium", "motoboys": 12, "cor": "🟣"}
    }
    
    plano_atual = planos_info.get(restaurante["plano"], planos_info["basico"])
    st.info(f"{plano_atual['cor']} **Plano {plano_atual['nome']}**\nAté {plano_atual['motoboys']} motoboys")
    
    st.divider()
    
    # Código de acesso
    st.text("🔑 Código de Acesso Motoboys:")
    st.code(restaurante["codigo_acesso"], language=None)
    
    st.divider()
    
    if st.button("🚪 Sair", use_container_width=True):
        fazer_logout()


# ============================================
# 📍 FUNÇÕES DE CARREGAMENTO DE DADOS
# ============================================

@st.cache_data(ttl=10)
def load_pedidos(token: str):
    """Carrega pedidos do restaurante"""
    try:
        resp = requests.get(
            f"{API_URL}/pedidos/meus",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        return resp.json() if resp.status_code == 200 else []
    except:
        return []


@st.cache_data(ttl=10)
def load_motoboys(token: str, restaurante_id: int):
    """Carrega todos os motoboys"""
    try:
        resp = requests.get(
            f"{API_URL}/motoboys/{restaurante_id}",
            timeout=8
        )
        return resp.json() if resp.status_code == 200 else []
    except:
        return []


@st.cache_data(ttl=10)
def load_motoboys_pendentes(token: str, restaurante_id: int):
    """Carrega motoboys aguardando aprovação"""
    try:
        resp = requests.get(
            f"{API_URL}/motoboys/{restaurante_id}/pendentes",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8
        )
        return resp.json() if resp.status_code == 200 else []
    except:
        return []


@st.cache_data(ttl=10)
def load_gps_motoboys(restaurante_id: int):
    """Carrega GPS dos motoboys"""
    try:
        resp = requests.get(
            f"{API_URL}/motoboys/{restaurante_id}/gps",
            timeout=8
        )
        return resp.json() if resp.status_code == 200 else []
    except:
        return []


# Carregar dados
pedidos = load_pedidos(st.session_state.token)
motoboys = load_motoboys(st.session_state.token, restaurante["id"])
motoboys_pendentes = load_motoboys_pendentes(st.session_state.token, restaurante["id"])
motoboys_gps = load_gps_motoboys(restaurante["id"])


# ============================================
# 📍 TABS DO DASHBOARD
# ============================================

tabs = st.tabs([
    "🏠 Dashboard",
    "📦 Criar Pedido",
    "⏱ Pedidos em Andamento",
    "👥 Motoboys",
    "⚙️ Configurações"
])


# ============================================
# TAB 1: DASHBOARD PRINCIPAL
# ============================================

with tabs[0]:
    st.header("Dashboard Realtime")
    
    # Métricas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        pedidos_hoje = len([p for p in pedidos if p["status"] != "entregue"])
        st.metric("Pedidos Ativos", pedidos_hoje)
    
    with col2:
        motoboys_ativos = len([m for m in motoboys if m["status"] in ["disponivel", "ocupado"]])
        st.metric("Motoboys Ativos", motoboys_ativos)
    
    with col3:
        if motoboys_pendentes:
            st.metric("⚠️ Pendentes Aprovação", len(motoboys_pendentes))
        else:
            st.metric("Cadastros Pendentes", 0)
    
    with col4:
        modo_despacho_display = {
            "automatico_economico": "🚀 Econômico",
            "automatico_ordem": "⏰ Por Ordem",
            "manual": "👆 Manual"
        }
        st.metric("Modo Despacho", modo_despacho_display.get(restaurante["modo_despacho"], "Manual"))
    
    st.divider()
    
    # Mapa
    st.subheader("🗺 Mapa Realtime")
    
    layers = []
    
    # Restaurante
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=[{
                "lon": restaurante["lon"],
                "lat": restaurante["lat"],
                "nome": "🍕 Restaurante"
            }],
            get_position=["lon", "lat"],
            get_color=[255, 0, 0, 220],
            get_radius=300,
            pickable=True,
        )
    )
    
    # Pedidos
    if pedidos:
        pedidos_data = [
            {
                "lon": p["lon_cliente"],
                "lat": p["lat_cliente"],
                "nome": f"📦 Pedido #{p['comanda']}"
            }
            for p in pedidos
            if p.get("lat_cliente") and p.get("lon_cliente")
        ]
        if pedidos_data:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=pedidos_data,
                    get_position=["lon", "lat"],
                    get_color=[0, 120, 255, 200],
                    get_radius=200,
                )
            )
    
    # Motoboys
    if motoboys_gps:
        motoboys_map = [
            {
                "lon": m["lng"],
                "lat": m["lat"],
                "nome": f"🏍 {m['nome']}"
            }
            for m in motoboys_gps
        ]
        if motoboys_map:
            layers.append(
                pdk.Layer(
                    "ScatterplotLayer",
                    data=motoboys_map,
                    get_position=["lon", "lat"],
                    get_color=[0, 200, 0, 220],
                    get_radius=180,
                    pickable=True,
                )
            )
    
    if layers:
        view_state = pdk.ViewState(
            latitude=restaurante["lat"],
            longitude=restaurante["lon"],
            zoom=13,
            pitch=0,
        )
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=view_state,
            layers=layers,
            tooltip={"text": "{nome}"}
        ))


# ============================================
# TAB 2: CRIAR PEDIDO (COM VALIDAÇÃO DE TELEFONE)
# ============================================

with tabs[1]:
    st.header("📦 Criar Novo Pedido")
    
    # Seletor de modo de despacho
    modo_despacho_options = {
        "Usar padrão do restaurante": None,
        "🚀 Automático Econômico (menor distância)": "automatico_economico",
        "⏰ Automático por Ordem (FIFO)": "automatico_ordem",
        "👆 Manual (escolher motoboy depois)": "manual"
    }
    
    modo_selecionado_display = st.selectbox(
        "Modo de Despacho para Este Pedido",
        list(modo_despacho_options.keys()),
        help="Define como o pedido será atribuído a um motoboy"
    )
    modo_selecionado = modo_despacho_options[modo_selecionado_display]
    
    with st.form("novo_pedido", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            comanda = st.text_input("Comanda/Número *", placeholder="Ex: 001")
            cliente_nome = st.text_input("Nome do Cliente *")
            # ========== CAMPO TELEFONE COM VALIDAÇÃO ==========
            telefone = st.text_input("Telefone", placeholder="Ex: 11999999999", help="Mínimo 10 caracteres se informado")
            # ==================================================
        
        with col2:
            tipo = st.selectbox("Tipo *", ["Entrega", "Retirada na loja", "Para mesa"])
            valor_total = st.number_input("Valor Total (R$) *", min_value=0.0, value=0.0, step=0.5)
        
        if tipo == "Entrega":
            endereco = st.text_area("Endereço Completo *", placeholder="Rua, número, bairro, cidade")
            complemento = st.text_input("Complemento", placeholder="Apto, bloco, etc")
        elif tipo == "Para mesa":
            numero_mesa = st.text_input("Número da Mesa *")
        
        itens = st.text_area("Itens do Pedido *", placeholder="Ex: 2x Pizza Grande, 1x Refrigerante")
        observacoes = st.text_area("Observações")
        tempo_preparo = st.number_input("Tempo Estimado Preparo (min)", min_value=5, value=30)
        
        submit = st.form_submit_button("✅ Criar Pedido", use_container_width=True)
        
        if submit:
            # ========== VALIDAÇÃO DE TELEFONE ANTES DO POST ==========
            telefone_valido, erro_telefone = validar_telefone(telefone)
            
            # Validações
            if not all([comanda, cliente_nome, itens, valor_total > 0]):
                st.error("Preencha os campos obrigatórios (*)")
            elif not telefone_valido:
                st.error(erro_telefone)  # Exibe mensagem clara ANTES de enviar
            elif tipo == "Entrega" and not endereco:
                st.error("Endereço obrigatório para entrega")
            elif tipo == "Para mesa" and not numero_mesa:
                st.error("Número da mesa obrigatório")
            else:
                payload = {
                    "comanda": comanda,
                    "tipo": tipo,
                    "cliente_nome": cliente_nome,
                    "cliente_telefone": telefone.strip() or None,  # Envia limpo
                    "endereco_entrega": endereco if tipo == "Entrega" else None,
                    "complemento": complemento if tipo == "Entrega" else None,
                    "numero_mesa": numero_mesa if tipo == "Para mesa" else None,
                    "itens": itens,
                    "observacoes": observacoes or None,
                    "valor_total": float(valor_total),
                    "tempo_estimado_preparo": int(tempo_preparo),
                    "modo_despacho_override": modo_selecionado
                }
                
                try:
                    resp = requests.post(
                        f"{API_URL}/pedidos/",
                        json=payload,
                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                        timeout=15
                    )
                    
                    if resp.status_code == 201:
                        st.success("✅ Pedido criado com sucesso!")
                        pedido_criado = resp.json()
                        
                        if pedido_criado.get("motoboy_id"):
                            st.info(f"🏍 Pedido atribuído automaticamente")
                        elif tipo == "Entrega":
                            st.warning("⏳ Pedido pendente de atribuição (modo manual ou sem motoboys disponíveis)")
                        
                        st.balloons()
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        erro = resp.json().get("detail", resp.text)
                        st.error(f"Erro: {erro}")
                        
                except requests.exceptions.Timeout:
                    st.error("Timeout ao criar pedido (geocodificação demorada)")
                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")


# ============================================
# TAB 3: PEDIDOS EM ANDAMENTO
# ============================================

with tabs[2]:
    st.header("⏱ Pedidos em Andamento")
    
    if st.button("🔄 Atualizar Lista"):
        st.cache_data.clear()
        st.rerun()
    
    if pedidos:
        # Filtrar por status
        status_filter = st.multiselect(
            "Filtrar por Status",
            ["novo", "pendente", "atribuido", "em_preparo", "pronto", "em_rota", "entregue", "cancelado"],
            default=["novo", "pendente", "atribuido", "em_preparo", "pronto", "em_rota"]
        )
        
        pedidos_filtrados = [p for p in pedidos if p["status"] in status_filter]
        
        if pedidos_filtrados:
            df = pd.DataFrame(pedidos_filtrados)
            
            # Renomear colunas para exibição
            colunas_exibir = {
                "id": "ID",
                "comanda": "Comanda",
                "cliente_nome": "Cliente",
                "tipo": "Tipo",
                "status": "Status",
                "valor_total": "Valor (R$)",
                "data_criacao": "Criado em"
            }
            
            df_display = df[[col for col in colunas_exibir.keys() if col in df.columns]].rename(columns=colunas_exibir)
            st.dataframe(df_display, use_container_width=True)
            
            # Ações em pedidos pendentes (despacho manual)
            pedidos_pendentes = [p for p in pedidos_filtrados if p["status"] == "pendente" and p["tipo"] == "Entrega"]
            
            if pedidos_pendentes and restaurante["modo_despacho"] == "manual":
                st.divider()
                st.subheader("🚚 Despacho Manual de Pedidos Pendentes")
                
                for pedido in pedidos_pendentes:
                    with st.expander(f"Pedido #{pedido['comanda']} - {pedido['cliente_nome']}"):
                        st.write(f"**Endereço:** {pedido['endereco_entrega']}")
                        st.write(f"**Valor:** R$ {pedido['valor_total']:.2f}")
                        
                        # Motoboys disponíveis
                        motoboys_disponiveis = [
                            m for m in motoboys 
                            if m["status"] in ["disponivel", "ocupado"] and m["aprovado_por_admin"]
                        ]
                        
                        if motoboys_disponiveis:
                            motoboy_selecionado = st.selectbox(
                                "Escolher Motoboy",
                                options=[m["id"] for m in motoboys_disponiveis],
                                format_func=lambda x: next(
                                    f"{m['nome']} {m.get('sobrenome', '')} ({m['status']})"
                                    for m in motoboys_disponiveis if m["id"] == x
                                ),
                                key=f"motoboy_select_{pedido['id']}"
                            )
                            
                            if st.button(f"Atribuir", key=f"atribuir_{pedido['id']}"):
                                try:
                                    resp = requests.post(
                                        f"{API_URL}/pedidos/despachar-manual",
                                        json={
                                            "pedido_id": pedido["id"],
                                            "motoboy_id": motoboy_selecionado
                                        },
                                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                                        timeout=10
                                    )
                                    
                                    if resp.status_code == 200:
                                        st.success("✅ Pedido atribuído!")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(f"Erro: {resp.json().get('detail', 'Erro desconhecido')}")
                                except Exception as e:
                                    st.error(f"Erro: {str(e)}")
                        else:
                            st.warning("Nenhum motoboy disponível")
        else:
            st.info("Nenhum pedido encontrado com os filtros selecionados")
    else:
        st.info("📭 Nenhum pedido registrado ainda")


# ============================================
# TAB 4: MOTOBOYS
# ============================================

with tabs[3]:
    st.header("👥 Gestão de Motoboys")
    
    # Notificação de pendentes
    if motoboys_pendentes:
        st.warning(f"⚠️ **{len(motoboys_pendentes)} cadastro(s) aguardando aprovação!**")
    
    # Subtabs
    subtabs = st.tabs(["Lista de Motoboys", "Aprovações Pendentes", "Estatísticas"])
    
    # SUBTAB 1: Lista de Motoboys
    with subtabs[0]:
        if st.button("🔄 Atualizar", key="refresh_motoboys"):
            st.cache_data.clear()
            st.rerun()
        
        if motoboys:
            # Separar por status
            ativos = [m for m in motoboys if m["status"] in ["disponivel", "ocupado"]]
            inativos = [m for m in motoboys if m["status"] == "inativo"]
            
            st.subheader(f"✅ Motoboys Ativos ({len(ativos)})")
            
            for motoboy in ativos:
                with st.expander(
                    f"🏍 {motoboy['nome']} {motoboy.get('sobrenome', '')} - {motoboy['status'].upper()}"
                ):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write(f"**Username:** {motoboy['username']}")
                        st.write(f"**Telefone:** {motoboy.get('telefone', 'Não informado')}")
                        st.write(f"**Entregas hoje:** {motoboy['entregas_hoje']}")
                        st.write(f"**Total de entregas:** {motoboy['total_entregas']}")
                        st.write(f"**Limite concorrente:** {motoboy['max_pedidos_concorrentes']} pedidos")
                        st.write(f"**Cadastrado em:** {motoboy['data_cadastro'][:10]}")
                    
                    with col2:
                        if st.button("🗑️ Excluir", key=f"excluir_{motoboy['id']}", type="secondary"):
                            if st.session_state.get(f"confirmar_exclusao_{motoboy['id']}", False):
                                try:
                                    resp = requests.delete(
                                        f"{API_URL}/motoboys/{restaurante['id']}/excluir/{motoboy['id']}",
                                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                                        timeout=10
                                    )
                                    
                                    if resp.status_code == 200:
                                        st.success("✅ Motoboy excluído")
                                        st.cache_data.clear()
                                        st.rerun()
                                    else:
                                        st.error(f"Erro: {resp.json().get('detail')}")
                                except Exception as e:
                                    st.error(f"Erro: {str(e)}")
                            else:
                                st.session_state[f"confirmar_exclusao_{motoboy['id']}"] = True
                                st.warning("⚠️ Clique novamente para confirmar exclusão")
                                st.rerun()
            
            if inativos:
                st.divider()
                st.subheader(f"❌ Motoboys Excluídos ({len(inativos)})")
                for m in inativos:
                    st.caption(f"- {m['nome']} {m.get('sobrenome', '')} (excluído)")
        else:
            st.info("Nenhum motoboy cadastrado ainda")
    
    # SUBTAB 2: Aprovações Pendentes
    with subtabs[1]:
        if motoboys_pendentes:
            st.info(f"📋 **{len(motoboys_pendentes)} cadastro(s) aguardando aprovação**")
            
            for motoboy in motoboys_pendentes:
                with st.expander(f"🆕 {motoboy['nome']} {motoboy.get('sobrenome', '')}"):
                    st.write(f"**Username:** {motoboy['username']}")
                    st.write(f"**Telefone:** {motoboy.get('telefone', 'Não informado')}")
                    st.write(f"**CPF:** {motoboy.get('cpf', 'Não informado')}")
                    st.write(f"**Cadastrado em:** {motoboy['data_cadastro']}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("✅ Aprovar", key=f"aprovar_{motoboy['id']}", use_container_width=True):
                            try:
                                resp = requests.post(
                                    f"{API_URL}/motoboys/{restaurante['id']}/aprovar",
                                    json={
                                        "motoboy_id": motoboy["id"],
                                        "aprovado": True
                                    },
                                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                                    timeout=10
                                )
                                
                                if resp.status_code == 200:
                                    st.success("✅ Motoboy aprovado!")
                                    st.cache_data.clear()
                                    st.rerun()
                                else:
                                    st.error(f"Erro: {resp.json().get('detail')}")
                            except Exception as e:
                                st.error(f"Erro: {str(e)}")
                    
                    with col2:
                        if st.button("❌ Rejeitar", key=f"rejeitar_{motoboy['id']}", use_container_width=True):
                            try:
                                resp = requests.post(
                                    f"{API_URL}/motoboys/{restaurante['id']}/aprovar",
                                    json={
                                        "motoboy_id": motoboy["id"],
                                        "aprovado": False
                                    },
                                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                                    timeout=10
                                )
                                
                                if resp.status_code == 200:
                                    st.success("✅ Cadastro rejetado!")
                                    st.cache_data.clear()   
                                    st.rerun()
                                else:
                                    st.error(f"Erro: {resp.json().get('detail')}")
                            except Exception as e:
                                st.error(f"Erro: {str(e)}")
        else:
            st.info("Nenhum cadastro pendente de aprovação")    
    # SUBTAB 3: Estatísticas
    # SUBTAB 3: Estatísticas
with subtabs[2]:
    if motoboys:
        st.subheader("📊 Estatísticas de Entregas")
        
        df_stats = pd.DataFrame([
            {
                "Motoboy": f"{m['nome']} {m.get('sobrenome', '')}",
                "Status": m['status'],
                "Entregas Hoje": m['entregas_hoje'],
                "Total Entregas": m['total_entregas']
            }
            for m in motoboys if m['status'] != 'inativo'
        ])
        
        if not df_stats.empty:
            st.dataframe(df_stats, use_container_width=True)
            
            # Gráfico de entregas
            fig = px.bar(
                df_stats,
                x="Motoboy",
                y="Total Entregas",
                color="Status",
                title="Total de Entregas por Motoboy"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados para exibir")
    else:
        st.info("Nenhum motoboy cadastrado")


# ============================================
# TAB 5: CONFIGURAÇÕES (COM VALIDAÇÃO DE TELEFONE)
# ============================================
with tabs[4]:
    st.header("⚙️ Configurações do Restaurante")
# Subtabs de configuração
config_tabs = st.tabs(["Dados Básicos", "Modo de Despacho", "Código de Acesso"])

# CONFIG TAB 1: Dados Básicos (COM VALIDAÇÃO DE TELEFONE)
with config_tabs[0]:
    st.subheader("📝 Informações do Restaurante")
    
    with st.form("atualizar_dados"):
        nome = st.text_input("Nome Fantasia", value=restaurante["nome_fantasia"])
        # ========== CAMPO TELEFONE COM VALIDAÇÃO ==========
        telefone = st.text_input("Telefone *", value=restaurante["telefone"], help="Mínimo 10 caracteres")
        # ==================================================
        endereco = st.text_area("Endereço Completo", value=restaurante["endereco_completo"])
        
        col1, col2 = st.columns(2)
        with col1:
            taxa_entrega = st.number_input(
                "Taxa de Entrega (R$)",
                value=float(restaurante["taxa_entrega"]),
                min_value=0.0,
                step=0.5
            )
        with col2:
            tempo_preparo = st.number_input(
                "Tempo Médio de Preparo (min)",
                value=int(restaurante["tempo_medio_preparo"]),
                min_value=5
            )
        
        submit = st.form_submit_button("💾 Salvar Alterações")
        
        if submit:
            # ========== VALIDAÇÃO DE TELEFONE ANTES DO PATCH ==========
            telefone_valido, erro_telefone = validar_telefone(telefone)
            
            if not telefone_valido:
                st.error(erro_telefone)
            else:
                payload = {
                    "nome_fantasia": nome,
                    "telefone": telefone.strip(),
                    "endereco_completo": endereco,
                    "taxa_entrega": taxa_entrega,
                    "tempo_medio_preparo": tempo_preparo
                }
                
                try:
                    resp = requests.patch(
                        f"{API_URL}/restaurantes/me/config",
                        json=payload,
                        headers={"Authorization": f"Bearer {st.session_state.token}"},
                        timeout=15
                    )
                    
                    if resp.status_code == 200:
                        st.success("✅ Configurações atualizadas!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error(f"Erro: {resp.json().get('detail')}")
                except Exception as e:
                    st.error(f"Erro: {str(e)}")

# CONFIG TAB 2: Modo de Despacho
with config_tabs[1]:
    st.subheader("🚚 Modo de Despacho Padrão")
    
    st.info("""
    **Modos disponíveis:**
    - 🚀 **Automático Econômico**: Atribui ao motoboy mais próximo (menor distância)
    - ⏰ **Automático por Ordem**: Atribui por ordem de chegada (FIFO - primeiro a chegar, primeiro a sair)
    - 👆 **Manual**: Você escolhe qual motoboy para cada pedido
    """)
    
    modo_atual = restaurante["modo_despacho"]
    
    modos = {
        "🚀 Automático Econômico": "automatico_economico",
        "⏰ Automático por Ordem (FIFO)": "automatico_ordem",
        "👆 Manual": "manual"
    }
    
    modo_display = {v: k for k, v in modos.items()}
    
    modo_selecionado = st.radio(
        "Selecione o modo padrão:",
        list(modos.keys()),
        index=list(modos.values()).index(modo_atual)
    )
    
    if st.button("💾 Salvar Modo de Despacho"):
        try:
            resp = requests.patch(
                f"{API_URL}/restaurantes/me/modo-despacho",
                params={"modo": modos[modo_selecionado]},
                headers={"Authorization": f"Bearer {st.session_state.token}"},
                timeout=10
            )
            
            if resp.status_code == 200:
                st.success("✅ Modo de despacho atualizado!")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"Erro: {resp.json().get('detail')}")
        except Exception as e:
            st.error(f"Erro: {str(e)}")

# CONFIG TAB 3: Código de Acesso
with config_tabs[2]:
    st.subheader("🔑 Código de Acesso para Motoboys")
    
    st.info(f"**Código atual:** `{restaurante['codigo_acesso']}`")
    
    st.write("""
    Os motoboys usam este código para se cadastrarem no sistema.
    Se o código for comprometido, você pode gerar um novo.
    
    ⚠️ **Atenção:** Ao regenerar, o código antigo não funcionará mais.
    """)
    
    if st.button("🔄 Regenerar Código de Acesso"):
        if st.session_state.get("confirmar_regenerar", False):
            try:
                resp = requests.post(
                    f"{API_URL}/restaurantes/me/regenerar-codigo",
                    headers={"Authorization": f"Bearer {st.session_state.token}"},
                    timeout=10
                )
                
                if resp.status_code == 200:
                    novo_codigo = resp.json()["novo_codigo"]
                    st.success(f"✅ Novo código gerado: **{novo_codigo}**")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"Erro: {resp.json().get('detail')}")
            except Exception as e:
                st.error(f"Erro: {str(e)}")
            
            st.session_state.confirmar_regenerar = False
        else:
            st.session_state.confirmar_regenerar = True
            st.warning("⚠️ Clique novamente para confirmar")
            st.rerun()

st.divider()
st.caption(f"✅ Validações ativas: Telefone (min 10 chars) | Senha (6-72 bytes) | Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")