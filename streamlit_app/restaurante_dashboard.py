# Substitua o arquivo completo streamlit_app/restaurante_dashboard.py (melhor handling de erros de conexão API + mensagens claras)
import streamlit as st
import requests
import pandas as pd
import pydeck as pdk
from datetime import datetime
import os

# Adiciona a raiz do projeto ao caminho do Python (método seguro)
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import correto usando caminho absoluto
from utils.mapbox import geocode  # Para validar endereço (mantido caso precise no futuro)

st.set_page_config(page_title="Painel Restaurante - Realtime", layout="wide")

API_URL = "http://127.0.0.1:8000"  # Ajuste para produção se necessário
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

if not MAPBOX_TOKEN:
    st.error("Defina MAPBOX_TOKEN no .env e reinicie o Streamlit")
    st.stop()

# Pega ID da URL
query_params = st.query_params
restaurante_id = query_params.get("id", [None])[0]

if not restaurante_id:
    st.error("Acesse com ?id=NUMERO (ex: http://localhost:8501/?id=2)")
    st.stop()

try:
    restaurante_id = int(restaurante_id)
except:
    st.error("ID inválido")
    st.stop()

# Carrega dados do restaurante com handling robusto de erro
try:
    response = requests.get(f"{API_URL}/restaurantes/", timeout=10)
    response.raise_for_status()
    restaurantes = response.json()
except requests.exceptions.ConnectionError:
    st.error("🚨 Não foi possível conectar à API.")
    st.info("Verifique se o backend está rodando:")
    st.code("uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000")
    st.stop()
except requests.exceptions.Timeout:
    st.error("🚨 Timeout ao conectar à API (demorou mais de 10s)")
    st.info("Inicie o backend com o comando acima")
    st.stop()
except requests.exceptions.RequestException as e:
    st.error(f"🚨 Erro ao conectar à API: {str(e)}")
    st.info("Inicie o backend FastAPI primeiro")
    st.stop()
except Exception as e:
    st.error(f"Erro inesperado ao carregar restaurantes: {str(e)}")
    st.stop()

restaurante = next((r for r in restaurantes if r["id"] == restaurante_id), None)

if not restaurante:
    st.error("Restaurante não encontrado com este ID")
    st.stop()

st.title(f"🍕 {restaurante['nome']} - Dashboard Realtime")

# Menu superior fixo
tabs = st.tabs(["🏠 Dashboard", "📦 Criar Pedido", "⏱ Pedidos em Andamento", "👥 Motoboys", "⚙ Configurações de Tempo"])

limites = {"basico": 3, "medio": 5, "premium": 12}
limite_max = limites.get(restaurante["plano"], 3)

# Funções cacheadas para polling eficiente (dados estruturados) com handling de erro
@st.cache_data(ttl=10)
def load_motoboys(restaurante_id: int):
    try:
        resp = requests.get(f"{API_URL}/motoboys/{restaurante_id}", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except:
        return []

@st.cache_data(ttl=10)
def load_pedidos(restaurante_id: int):
    try:
        resp = requests.get(f"{API_URL}/pedidos/{restaurante_id}", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except:
        return []

@st.cache_data(ttl=10)
def load_gps_motoboys(restaurante_id: int):
    try:
        resp = requests.get(f"{API_URL}/motoboys/gps/{restaurante_id}", timeout=8)
        resp.raise_for_status()
        return resp.json()
    except:
        return []

motoboys = load_motoboys(restaurante_id)
pedidos = load_pedidos(restaurante_id)
motoboys_gps = load_gps_motoboys(restaurante_id)

with tabs[0]:  # Dashboard
    st.subheader(f"Plano: **{restaurante['plano'].upper()}** | Código de Acesso: **{restaurante['codigo_acesso']}**")
    st.write(f"Motoboys cadastrados: {len(motoboys)} / {limite_max}")

    st.subheader("🗺 Mapa Realtime (Restaurante • Pedidos • Motoboys)")

    layers = []

    # Ponto do restaurante
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=[{"lon": restaurante["lon"], "lat": restaurante["lat"], "nome": "Restaurante"}],
            get_position=["lon", "lat"],
            get_color=[255, 0, 0, 220],
            get_radius=300,
            pickable=True,
        )
    )

    # Pedidos pendentes/atribuidos
    if pedidos:
        pedidos_data = [
            {"lon": p["lon_cliente"], "lat": p["lat_cliente"], "nome": f"Pedido {p['comanda']} ({p['status']})"}
            for p in pedidos if p.get("lat_cliente") and p.get("lon_cliente")
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

    # Motoboys com posição atual (fallback para restaurante)
    if motoboys_gps:
        motoboys_map = []
        for m in motoboys_gps:
            lat = m.get("lat") or restaurante["lat"]
            lon = m.get("lng") or restaurante["lon"]
            motoboys_map.append({"lon": lon, "lat": lat, "nome": f"{m['nome']} ({m['status']})"})
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
            latitude=restaurante.get("lat", -23.5505),
            longitude=restaurante.get("lon", -46.6333),
            zoom=12,
            pitch=0,
        )
        deck = pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v10",
            initial_view_state=view_state,
            layers=layers,
            tooltip={"text": "{nome}"},
        )
        st.pydeck_chart(deck, use_container_width=True)
    else:
        st.info("Sem dados geográficos para exibir no mapa (aguardando pedidos ou GPS).")

    # Log realtime via WebSocket (push instantâneo)
    st.subheader("📡 Log de Eventos Realtime (atribuições, GPS, etc.)")

    log_placeholder = st.empty()
    log_html = """
    <div id="ws_log" style="height: 400px; overflow-y: scroll; background:#fafafa; padding:15px; border:1px solid #ddd; font-family:monospace; border-radius:8px;">
    <p><strong>Conectando ao WebSocket...</strong></p>
    </div>
    """
    log_placeholder.markdown(log_html, unsafe_allow_html=True)

    ws_script = f"""
    <script>
    let ws = null;
    function connect() {{
        if (ws) ws.close();
        ws = new WebSocket(`ws://127.0.0.1:8000/ws/{restaurante_id}`);
        ws.onopen = () => appendLog("<strong>✅ Conectado ao WebSocket (restaurante {restaurante_id})</strong>");
        ws.onmessage = (event) => {{
            try {{
                const data = JSON.parse(event.data);
                const time = new Date().toLocaleTimeString();
                let msg = `[${{time}}] <strong>{{data.type || 'evento'}}</strong><br>`;
                if (data.type === "nova_atribuicao") {{
                    msg += `Motoboy <strong>{{data.motoboy_nome}}</strong> recebeu {{data.total_pedidos}} pedido(s)<br>`;
                    msg += `Tempo estimado: {{data.tempo_estimado_min}} min | Distância: {{data.distancia_total_km}} km`;
                }} else {{
                    msg += JSON.stringify(data, null, 2).replace(/\\n/g, '<br>');
                }}
                appendLog(msg);
                if (data.type === "nova_atribuicao") {{
                    Streamlit.setComponentValue("rerun");
                }}
            }} catch {{ appendLog(`[${{new Date().toLocaleTimeString()}}] Raw: ${{event.data}}`); }}
        }};
        ws.onclose = () => {{
            appendLog("<strong>❌ Desconectado - reconectando em 5s...</strong>");
            setTimeout(connect, 5000);
        }};
        ws.onerror = () => appendLog("<strong>⚠️ Erro WebSocket</strong>");
    }}
    function appendLog(msg) {{
        const log = document.getElementById("ws_log");
        const p = document.createElement("p");
        p.innerHTML = msg;
        log.appendChild(p);
        log.scrollTop = log.scrollHeight;
    }}
    connect();
    </script>
    """
    st.markdown(ws_script, unsafe_allow_html=True)

with tabs[1]:  # Criar Pedido (mantido idêntico com pequeno ajuste no despacho)
    st.header("📦 Criar Novo Pedido")

    try:
        from db.database import DBManager
        db_temp = DBManager()
        db_temp.cursor.execute("SELECT MAX(CAST(comanda AS INTEGER)) FROM pedidos WHERE restaurante_id = ?", (restaurante_id,))
        ultimo = db_temp.cursor.fetchone()[0]
        proxima_comanda = str((int(ultimo) + 1) if ultimo else 1)
        db_temp.close()
    except:
        proxima_comanda = "1"

    with st.form("novo_pedido", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            tipo_pedido = st.selectbox("Tipo de Pedido", ["Entrega", "Retirada na loja", "Para mesa"])
        with col2:
            st.text_input("Comanda", value=proxima_comanda, disabled=True)

        cliente_nome = st.text_input("Nome do Cliente")
        cliente_telefone = st.text_input("Telefone (WhatsApp)")
        observacoes = st.text_area("Observações")

        endereco_entrega = ""
        numero_mesa = ""
        if tipo_pedido == "Entrega":
            endereco_entrega = st.text_area("Endereço completo (obrigatório)")
        elif tipo_pedido == "Para mesa":
            numero_mesa = st.text_input("Número da Mesa")

        itens = st.text_area("Itens do pedido")

        tempo_default = 45 if tipo_pedido == "Entrega" else 20 if tipo_pedido == "Para mesa" else 30
        tempo_estimado = st.number_input("Tempo estimado (minutos)", min_value=5, value=tempo_default)

        submitted = st.form_submit_button("Registrar Pedido")

        if submitted:
            if not cliente_nome or not itens:
                st.error("Nome do cliente e itens são obrigatórios")
            elif tipo_pedido == "Entrega" and not endereco_entrega:
                st.error("Endereço obrigatório para entrega")
            elif tipo_pedido == "Para mesa" and not numero_mesa:
                st.error("Número da mesa obrigatório")
            else:
                payload = {
                    "restaurante_id": restaurante_id,
                    "comanda": proxima_comanda,
                    "tipo": tipo_pedido,
                    "cliente_nome": cliente_nome,
                    "cliente_telefone": cliente_telefone,
                    "endereco_entrega": endereco_entrega,
                    "numero_mesa": numero_mesa,
                    "itens": itens,
                    "observacoes": observacoes,
                    "tempo_estimado": int(tempo_estimado)
                }
                try:
                    resp = requests.post(f"{API_URL}/pedidos/", json=payload, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    pedido_id = data.get("id")
                    st.success(f"Pedido {proxima_comanda} salvo com sucesso!")
                    st.balloons()

                    if tipo_pedido == "Entrega" and pedido_id:
                        desp_resp = requests.post(f"{API_URL}/pedidos/despachar/{pedido_id}", timeout=10)
                        if desp_resp.status_code == 200:
                            desp_data = desp_resp.json()
                            st.info(f"Despacho automático: Motoboy {desp_data.get('motoboy', 'N/A')} atribuído")
                        else:
                            st.info("Despacho automático pendente")
                    else:
                        st.info("Pedido registrado (não é entrega)")
                    st.cache_data.clear()
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"Erro ao comunicar com API: {str(e)}")
                except Exception as e:
                    st.error(f"Erro inesperado: {str(e)}")

with tabs[2]:  # Pedidos em Andamento
    st.header("⏱ Pedidos em Andamento")
    if pedidos:
        df = pd.DataFrame(pedidos)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhum pedido registrado ainda")

with tabs[3]:  # Motoboys
    st.header(f"👥 Motoboys Cadastrados ({len(motoboys)} / {limite_max})")
    if motoboys:
        for m in motoboys:
            status = m.get("status", "disponivel").upper()
            st.write(f"- **{m['nome']}** — Status: {status}")
    else:
        st.info("Nenhum motoboy cadastrado")

    if len(motoboys) >= limite_max:
        st.warning("Limite do plano atingido")

    st.header("➕ Cadastrar Novo Motoboy")
    with st.form("cadastro_motoboy"):
        nome = st.text_input("Nome do Motoboy")
        codigo = st.text_input("Código de Acesso", type="password")
        submitted = st.form_submit_button("Cadastrar")

        if submitted:
            if not nome.strip():
                st.error("Nome obrigatório")
            elif codigo != restaurante["codigo_acesso"]:
                st.error("Código inválido!")
            else:
                payload = {"restaurante_id": restaurante_id, "nome": nome.strip()}
                try:
                    resp = requests.post(f"{API_URL}/motoboys/", json=payload, timeout=10)
                    resp.raise_for_status()
                    st.success(f"Motoboy **{nome}** cadastrado!")
                    st.balloons()
                    st.cache_data.clear()
                    st.rerun()
                except requests.exceptions.RequestException as e:
                    st.error(f"Erro ao cadastrar motoboy: {str(e)}")

with tabs[4]:  # Configurações de Tempo
    st.header("⚙ Configurações de Tempo Estimado")
    st.write("Defina o tempo padrão para cada tipo de pedido")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.number_input("Tempo Entrega (minutos)", min_value=10, max_value=120, value=45)
    with col2:
        st.number_input("Tempo Para Mesa (minutos)", min_value=5, max_value=60, value=20)
    with col3:
        st.number_input("Tempo Retirada (minutos)", min_value=5, max_value=60, value=30)
    st.info("Esses tempos serão usados para contagem regressiva e alertas de atraso (implementação futura)")

st.caption(f"Última atualização dos dados: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Realtime via WebSocket ativo")
