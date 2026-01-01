import streamlit as st
import requests
from datetime import datetime, timedelta

import sys
import os

# Adiciona a raiz do projeto ao caminho do Python (método seguro)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import correto usando caminho absoluto
from utils.mapbox import geocode  # Para validar endereço

st.set_page_config(page_title="Painel Restaurante", layout="wide")

API_URL = "http://127.0.0.1:8000"

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

# Carrega dados do restaurante
response = requests.get(f"{API_URL}/restaurantes/")
if response.status_code != 200:
    st.error("Erro ao conectar API")
    st.stop()

restaurantes = response.json()
restaurante = next((r for r in restaurantes if r["id"] == restaurante_id), None)

if not restaurante:
    st.error("Restaurante não encontrado")
    st.stop()

st.title(f"🍕 {restaurante['nome']}")

# Menu superior fixo
tabs = st.tabs(["🏠 Dashboard", "📦 Criar Pedido", "⏱ Pedidos em Andamento", "👥 Motoboys", "⚙ Configurações de Tempo"])

limites = {"basico": 3, "medio": 5, "premium": 12}
limite_max = limites.get(restaurante["plano"], 3)

# Carrega motoboys
resp_motoboys = requests.get(f"{API_URL}/motoboys/{restaurante_id}")
motoboys = resp_motoboys.json() if resp_motoboys.status_code == 200 else []

with tabs[0]:  # Dashboard
    st.subheader(f"Plano: **{restaurante['plano'].upper()}** | Código de Acesso: **{restaurante['codigo_acesso']}**")
    st.write(f"Motoboys cadastrados: {len(motoboys)} / {limite_max}")

    st.subheader("🗺 Mapa Realtime da Frota")

    gps_resp = requests.get(f"{API_URL}/motoboys/gps/{restaurante_id}")
    if gps_resp.status_code == 200:
        motoboys_gps = gps_resp.json()
        if motoboys_gps:
            import pandas as pd
            df = pd.DataFrame(motoboys_gps)
            df = df.rename(columns={"lat": "latitude", "lng": "longitude"})
            st.map(df)

            st.write("Motoboys no mapa:")
            for m in motoboys_gps:
                status_icon = "🟢" if m["status"] == "disponivel" else "🔴"
                st.write(f"{status_icon} **{m['nome']}** — {m['status'].upper()}")
        else:
            st.info("Nenhum motoboy com posição GPS no momento (aguardando app motoboy enviar dados)")
    else:
        st.warning("Erro ao carregar posições GPS da API")

with tabs[1]:  # Criar Pedido
    st.header("📦 Criar Novo Pedido")

    # Comanda automática
    try:
        from db.database import DBManager
        db_temp = DBManager()
        db_temp.cursor.execute("SELECT MAX(CAST(comanda AS INTEGER)) FROM pedidos WHERE restaurante_id = ?", (restaurante_id,))
        ultimo = db_temp.cursor.fetchone()[0]
        proxima_comanda = str((int(ultimo) + 1) if ultimo else 1)
        db_temp.close()
    except:
        proxima_comanda = "1"

    with st.form("novo_pedido", clear_on_submit=True):  # ← IMPORTANTE: limpa o form após submit
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

        # Tempo estimado
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
                    resp = requests.post(f"{API_URL}/pedidos/", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        pedido_id = data.get("id")
                        st.success(f"Pedido {proxima_comanda} salvo com sucesso!")
                        st.balloons()

                        if tipo_pedido == "Entrega":
                            if pedido_id:
                                desp_resp = requests.post(f"{API_URL}/pedidos/despachar/{pedido_id}")
                                if desp_resp.status_code == 200:
                                    desp_data = desp_resp.json()
                                    st.info(f"Despacho automático: Motoboy ID {desp_data['motoboy_id']} atribuído")
                                else:
                                    st.info("Despacho automático em desenvolvimento – em breve motoboy será atribuído")
                            else:
                                st.info("Despacho automático em desenvolvimento – em breve motoboy será atribuído")
                        else:
                            st.info("Pedido registrado (não é entrega – sem despacho automático)")
                    else:
                        st.error("Erro ao salvar pedido")
                except:
                    st.error("API não está respondendo")

with tabs[2]:  # Pedidos em Andamento
    st.header("⏱ Pedidos em Andamento")
    resp_pedidos = requests.get(f"{API_URL}/pedidos/{restaurante_id}")
    if resp_pedidos.status_code == 200:
        pedidos = resp_pedidos.json()
        if pedidos:
            for p in pedidos:
                st.write(f"Comanda {p['comanda']} - {p['tipo']} - Cliente: {p['cliente']} - Status: {p['status'].upper()}")
        else:
            st.info("Nenhum pedido registrado ainda")
    else:
        st.error("Erro ao carregar pedidos")

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
                    resp = requests.post(f"{API_URL}/motoboys/", json=payload)
                    if resp.status_code == 200:
                        st.success(f"Motoboy **{nome}** cadastrado!")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(resp.json().get("detail", "Erro"))
                except:
                    st.error("Falha na conexão com API")

with tabs[4]:  # Configurações de Tempo
    st.header("⚙ Configurações de Tempo Estimado")
    st.write("Defina o tempo padrão para cada tipo de pedido (pode alterar a qualquer momento)")

    col1, col2, col3 = st.columns(3)
    with col1:
        tempo_entrega = st.number_input("Tempo Entrega (minutos)", min_value=10, max_value=120, value=45)
    with col2:
        tempo_mesa = st.number_input("Tempo Para Mesa (minutos)", min_value=5, max_value=60, value=20)
    with col3:
        tempo_retirada = st.number_input("Tempo Retirada (minutos)", min_value=5, max_value=60, value=30)

    st.info("Esses tempos serão usados para contagem regressiva e alertas de atraso")