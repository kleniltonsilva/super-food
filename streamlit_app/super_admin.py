import streamlit as st
import requests

st.set_page_config(page_title="Super Admin - Gerenciador Motoboys", layout="wide")

st.title("🔧 Painel Super Admin - Gerenciador Motoboys")
st.markdown("Aqui você gerencia todos os restaurantes da plataforma")

API_URL = "http://127.0.0.1:8000"

# Função para carregar restaurantes
def carregar_restaurantes():
    try:
        response = requests.get(f"{API_URL}/restaurantes/")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro na API: {response.status_code}")
            return []
    except Exception as e:
        st.error("Não foi possível conectar à API. Verifique se o uvicorn está rodando.")
        st.error(str(e))
        return []

# Botão para atualizar
if st.button("🔄 Atualizar Lista de Restaurantes"):
    st.cache_data.clear()

restaurantes = carregar_restaurantes()

if restaurantes:
    st.success(f"Encontrados {len(restaurantes)} restaurante(s)")
    for rest in restaurantes:
        with st.expander(f"🍕 {rest['nome']} (ID: {rest['id']}) - Plano: {rest['plano'].upper()}"):
            st.write(f"📍 Endereço: {rest['endereco']}")
            st.write(f"🔑 Código de Acesso para Motoboys: **{rest['codigo_acesso']}**")
            st.write(f"✅ Status: {'Ativo' if rest['ativo'] else 'Inativo'}")
else:
    st.info("Nenhum restaurante cadastrado ainda. Crie o primeiro abaixo!")

st.divider()

st.header("➕ Criar Novo Restaurante")

with st.form(key="novo_restaurante"):
    nome = st.text_input("Nome do Restaurante", placeholder="Ex: Burguer King Lisboa")
    endereco = st.text_input("Endereço completo", placeholder="Ex: Avenida da Liberdade 123, Lisboa")
    plano_options = ["basico (até 3 motoboys)", "medio (até 5 motoboys)", "premium (até 12 motoboys)"]
    plano_selecionado = st.selectbox("Escolha o Plano", plano_options)
    
    submit = st.form_submit_button("Criar Restaurante")

    if submit:
        if not nome or not endereco:
            st.error("Nome e endereço são obrigatórios!")
        else:
            # Extrai a chave do plano (basico, medio, premium)
            plano_key = plano_selecionado.split()[0].replace("(", "").lower()
            dados = {
                "nome": nome,
                "endereco": endereco,
                "plano": plano_key
            }
            try:
                response = requests.post(f"{API_URL}/restaurantes/", json=dados)
                if response.status_code == 200:
                    novo_rest = response.json()
                    st.success("Restaurante criado com sucesso!")
                    st.balloons()
                    st.json(novo_rest)
                    st.info(f"Código de acesso para motoboys: **{novo_rest['codigo_acesso']}**")
                    st.cache_data.clear()  # Atualiza a lista
                else:
                    st.error(f"Erro ao criar: {response.text}")
            except Exception as e:
                st.error(f"Erro de conexão: {str(e)}")
