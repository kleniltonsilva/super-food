# Substitua o arquivo completo streamlit_app/super_admin.py (validação robusta de senha: min 6 / max 72 caracteres + mensagem clara)
import streamlit as st
import requests
import os

st.set_page_config(page_title="Super Admin - Super Restaurante SaaS", layout="wide")

st.title("🔧 Painel Super Admin - Gerenciador de Entregas")

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.markdown("""
Este painel permite gerenciar todos os restaurantes da plataforma de forma simples e intuitiva.
- Liste restaurantes existentes
- Crie novos restaurantes com formulário completo (geocodificação automática via Mapbox no backend)
""")

# Função para carregar restaurantes
@st.cache_data(ttl=30)
def carregar_restaurantes():
    try:
        response = requests.get(f"{API_URL}/restaurantes/", timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Erro na API ao listar: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        st.error(f"Não foi possível conectar à API: {str(e)}")
        st.info("Verifique se o backend está rodando: uvicorn backend.app.main:app --reload")
        return []

# Botão para atualizar lista
if st.button("🔄 Atualizar Lista de Restaurantes"):
    st.cache_data.clear()
    st.rerun()

restaurantes = carregar_restaurantes()

if restaurantes:
    st.success(f"Encontrados {len(restaurantes)} restaurante(s)")
    for rest in restaurantes:
        with st.expander(f"🍕 {rest['nome_fantasia']} (ID: {rest['id']}) - Plano: {rest['plano'].upper()}"):
            st.write(f"📧 Email: {rest['email']}")
            st.write(f"📍 Endereço: {rest['endereco_completo']} (lat: {rest['lat']:.6f}, lon: {rest['lon']:.6f})")
            st.write(f"📞 Telefone: {rest['telefone']}")
            st.write(f"💰 Taxa de entrega: R$ {rest['taxa_entrega']:.2f}")
            st.write(f"⏱ Tempo médio preparo: {rest['tempo_medio_preparo']} min")
            st.write(f"🔑 Código de Acesso Motoboys: **{rest['codigo_acesso']}**")
            st.write(f"✅ Status: {'Ativo' if rest['ativo'] else 'Inativo'}")
            st.write(f"📅 Criado em: {rest['data_criacao']}")
else:
    st.info("Nenhum restaurante cadastrado ainda. Crie o primeiro abaixo!")

st.divider()

st.header("➕ Criar Novo Restaurante (Signup Completo)")

with st.form(key="novo_restaurante", clear_on_submit=True):
    st.subheader("Dados Principais")
    col1, col2 = st.columns(2)
    with col1:
        nome_fantasia = st.text_input("Nome Fantasia *", placeholder="Ex: Burguer King Lisboa")
        email = st.text_input("Email *", placeholder="exemplo@dominio.com")
        telefone = st.text_input("Telefone *", placeholder="Ex: 11999999999")
    with col2:
        razao_social = st.text_input("Razão Social (opcional)", placeholder="Ex: Empresa LTDA")
        cnpj = st.text_input("CNPJ (opcional)", placeholder="Ex: 12345678000199")

    st.subheader("Endereço e Operação")
    endereco_completo = st.text_area("Endereço Completo *", placeholder="Ex: Avenida Paulista 1000, São Paulo, SP, Brasil", height=100)
    
    col3, col4 = st.columns(2)
    with col3:
        taxa_entrega = st.number_input("Taxa de Entrega (R$)", min_value=0.0, value=5.0, step=0.5)
        tempo_medio_preparo = st.number_input("Tempo Médio de Preparo (min)", min_value=10, max_value=120, value=30)
    with col4:
        plano_options = ["basico (até 3 motoboys)", "medio (até 5 motoboys)", "premium (até 12 motoboys)"]
        plano_selecionado = st.selectbox("Plano *", plano_options)

    st.subheader("Senha de Acesso")
    senha = st.text_input("Senha do Restaurante *", type="password", help="Mínimo 6 caracteres, máximo 72 caracteres")
    confirmar_senha = st.text_input("Confirmar Senha *", type="password")

    submit = st.form_submit_button("🚀 Criar Restaurante")

    if submit:
        # Validações locais (inclui limite bcrypt 72 bytes ≈ 72 caracteres ASCII)
        if not all([nome_fantasia, email, telefone, endereco_completo, senha]):
            st.error("Campos obrigatórios (*) não preenchidos")
        elif senha != confirmar_senha:
            st.error("Senhas não coincidem")
        elif len(senha) < 6:
            st.error("Senha deve ter pelo menos 6 caracteres")
        elif len(senha) > 72:
            st.error("Senha muito longa (máximo 72 caracteres). Reduza para evitar erro de hash bcrypt.")
        else:
            plano_key = plano_selecionado.split()[0].lower()
            dados = {
                "nome_fantasia": nome_fantasia.strip(),
                "razao_social": razao_social.strip() or None,
                "cnpj": cnpj.strip() or None,
                "email": email.strip(),
                "telefone": telefone.strip(),
                "endereco_completo": endereco_completo.strip(),
                "taxa_entrega": float(taxa_entrega),
                "tempo_medio_preparo": int(tempo_medio_preparo),
                "senha": senha,
                "plano": plano_key
            }
            try:
                response = requests.post(f"{API_URL}/restaurantes/signup", json=dados, timeout=20)
                if response.status_code == 201:
                    try:
                        novo_rest = response.json()
                    except:
                        novo_rest = {"mensagem": "Criado com sucesso (resposta não JSON)"}
                    st.success("🍕 Restaurante criado com sucesso!")
                    st.balloons()
                    st.json(novo_rest, expanded=False)
                    if isinstance(novo_rest, dict):
                        st.info(f"🔑 Código de acesso para motoboys: **{novo_rest.get('codigo_acesso', 'N/A')}**")
                        st.info(f"ID do restaurante: {novo_rest.get('id', 'N/A')} → use no dashboard: ?id={novo_rest.get('id', '')}")
                    st.cache_data.clear()
                    st.rerun()
                else:
                    try:
                        erro = response.json()
                        msg_erro = erro.get("detail", str(erro))
                    except:
                        msg_erro = response.text or "Resposta vazia do servidor"
                    st.error(f"Erro {response.status_code} ao criar restaurante: {msg_erro}")
                    st.code(response.text, language="text")
            except requests.exceptions.Timeout:
                st.error("Timeout na API (geocodificação pode demorar >20s). Tente novamente ou simplifique o endereço.")
            except requests.exceptions.ConnectionError:
                st.error("Erro de conexão com a API. Verifique se o backend está rodando.")
            except Exception as e:
                st.error(f"Erro inesperado: {str(e)}")

st.caption("Validação adicionada: senha máxima 72 caracteres (limite técnico do bcrypt). Evita erro interno de hash.")
