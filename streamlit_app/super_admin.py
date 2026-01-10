import streamlit as st
import sqlite3
import hashlib
import re
from datetime import datetime, timedelta
import os

# Configuração da página
st.set_page_config(
    page_title="Super Admin - Super Food",
    page_icon="👑",
    layout="wide"
)

# ==================== FUNÇÕES DE BANCO DE DADOS ====================

def get_db_connection():
    """Retorna conexão com o banco de dados SQLite"""
    db_path = os.path.join(os.path.dirname(__file__), 'super_food.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Inicializa as tabelas necessárias no banco de dados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Tabela de restaurantes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS restaurantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_fantasia TEXT NOT NULL,
            razao_social TEXT,
            cnpj TEXT,
            email TEXT NOT NULL UNIQUE,
            telefone TEXT NOT NULL,
            endereco_completo TEXT NOT NULL,
            plano TEXT NOT NULL,
            valor_plano REAL NOT NULL,
            limite_motoboys INTEGER NOT NULL,
            status TEXT DEFAULT 'ativo',
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_vencimento TIMESTAMP,
            senha_hash TEXT NOT NULL
        )
    ''')
    
    # Tabela de pagamentos/assinaturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assinaturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            restaurante_id INTEGER NOT NULL,
            data_pagamento TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            valor_pago REAL NOT NULL,
            forma_pagamento TEXT,
            status TEXT DEFAULT 'ativo',
            data_vencimento TIMESTAMP NOT NULL,
            FOREIGN KEY (restaurante_id) REFERENCES restaurantes (id)
        )
    ''')
    
    # Tabela de super admin (login do super admin)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS super_admin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL
        )
    ''')
    
    # Criar super admin padrão se não existir
    cursor.execute("SELECT * FROM super_admin WHERE usuario = 'superadmin'")
    if not cursor.fetchone():
        senha_padrao = hashlib.sha256("SuperFood2025!".encode()).hexdigest()
        cursor.execute(
            "INSERT INTO super_admin (usuario, senha_hash) VALUES (?, ?)",
            ("superadmin", senha_padrao)
        )
    
    conn.commit()
    conn.close()

def validar_cnpj(cnpj):
    """Valida formato do CNPJ (apenas números, 14 dígitos)"""
    if not cnpj:
        return True  # CNPJ é opcional
    cnpj_numeros = re.sub(r'\D', '', cnpj)
    return len(cnpj_numeros) == 14

def validar_telefone(telefone):
    """Valida telefone (mínimo 10 dígitos)"""
    telefone_numeros = re.sub(r'\D', '', telefone)
    return len(telefone_numeros) >= 10

def validar_email(email):
    """Valida formato de email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def criar_restaurante(dados):
    """
    Cria um novo restaurante no banco de dados
    Retorna: (sucesso: bool, mensagem: str)
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar se email já existe
        cursor.execute("SELECT id FROM restaurantes WHERE email = ?", (dados['email'],))
        if cursor.fetchone():
            conn.close()
            return False, "Este email já está cadastrado!"
        
        # Calcular data de vencimento (30 dias a partir de hoje)
        data_vencimento = datetime.now() + timedelta(days=30)
        
        # Gerar senha padrão (primeiros 6 dígitos do telefone)
        telefone_numeros = re.sub(r'\D', '', dados['telefone'])
        senha_padrao = telefone_numeros[:6] if len(telefone_numeros) >= 6 else "123456"
        senha_hash = hashlib.sha256(senha_padrao.encode()).hexdigest()
        
        # Inserir restaurante
        cursor.execute('''
            INSERT INTO restaurantes (
                nome_fantasia, razao_social, cnpj, email, telefone,
                endereco_completo, plano, valor_plano, limite_motoboys,
                data_vencimento, senha_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados['nome_fantasia'],
            dados.get('razao_social', ''),
            dados.get('cnpj', ''),
            dados['email'],
            dados['telefone'],
            dados['endereco_completo'],
            dados['plano'],
            dados['valor_plano'],
            dados['limite_motoboys'],
            data_vencimento,
            senha_hash
        ))
        
        restaurante_id = cursor.lastrowid
        
        # Criar primeiro registro de assinatura
        cursor.execute('''
            INSERT INTO assinaturas (
                restaurante_id, valor_pago, forma_pagamento,
                status, data_vencimento
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            restaurante_id,
            dados['valor_plano'],
            'Primeira Mensalidade',
            'ativo',
            data_vencimento
        ))
        
        conn.commit()
        conn.close()
        
        return True, f"Restaurante criado com sucesso! Senha padrão: {senha_padrao}"
        
    except Exception as e:
        return False, f"Erro ao criar restaurante: {str(e)}"

def listar_restaurantes():
    """Lista todos os restaurantes cadastrados"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nome_fantasia, email, telefone, plano, 
               valor_plano, status, data_vencimento
        FROM restaurantes
        ORDER BY data_criacao DESC
    ''')
    restaurantes = cursor.fetchall()
    conn.close()
    return restaurantes

def buscar_restaurante_por_id(restaurante_id):
    """Busca restaurante por ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM restaurantes WHERE id = ?", (restaurante_id,))
    restaurante = cursor.fetchone()
    conn.close()
    return restaurante

def atualizar_status_restaurante(restaurante_id, novo_status):
    """Atualiza status do restaurante (ativo/suspenso/cancelado)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE restaurantes SET status = ? WHERE id = ?",
        (novo_status, restaurante_id)
    )
    conn.commit()
    conn.close()

def renovar_assinatura(restaurante_id, valor_pago, forma_pagamento):
    """Renova assinatura do restaurante por mais 30 dias"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Buscar data de vencimento atual
    cursor.execute("SELECT data_vencimento FROM restaurantes WHERE id = ?", (restaurante_id,))
    resultado = cursor.fetchone()
    
    if resultado:
        data_atual_vencimento = datetime.strptime(resultado['data_vencimento'], '%Y-%m-%d %H:%M:%S.%f')
        # Se já venceu, renovar a partir de hoje, senão a partir do vencimento atual
        if data_atual_vencimento < datetime.now():
            nova_data_vencimento = datetime.now() + timedelta(days=30)
        else:
            nova_data_vencimento = data_atual_vencimento + timedelta(days=30)
        
        # Atualizar data de vencimento do restaurante
        cursor.execute(
            "UPDATE restaurantes SET data_vencimento = ?, status = 'ativo' WHERE id = ?",
            (nova_data_vencimento, restaurante_id)
        )
        
        # Registrar pagamento
        cursor.execute('''
            INSERT INTO assinaturas (
                restaurante_id, valor_pago, forma_pagamento,
                status, data_vencimento
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            restaurante_id,
            valor_pago,
            forma_pagamento,
            'ativo',
            nova_data_vencimento
        ))
        
        conn.commit()
    
    conn.close()

# ==================== AUTENTICAÇÃO ====================

def verificar_login(usuario, senha):
    """Verifica credenciais do super admin"""
    conn = get_db_connection()
    cursor = conn.cursor()
    senha_hash = hashlib.sha256(senha.encode()).hexdigest()
    cursor.execute(
        "SELECT * FROM super_admin WHERE usuario = ? AND senha_hash = ?",
        (usuario, senha_hash)
    )
    resultado = cursor.fetchone()
    conn.close()
    return resultado is not None

# ==================== INTERFACE PRINCIPAL ====================

def main():
    # Inicializar banco de dados
    init_database()
    
    # Sistema de autenticação
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    if not st.session_state.autenticado:
        st.title("🔐 Login Super Admin")
        st.markdown("### Sistema de Gerenciamento - Super Food")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            with st.form("login_form"):
                usuario = st.text_input("Usuário", placeholder="superadmin")
                senha = st.text_input("Senha", type="password", placeholder="SuperFood2025!")
                submit = st.form_submit_button("Entrar", use_container_width=True)
                
                if submit:
                    if verificar_login(usuario, senha):
                        st.session_state.autenticado = True
                        st.rerun()
                    else:
                        st.error("❌ Usuário ou senha incorretos!")
            
            st.info("💡 Credenciais padrão: **superadmin** / **SuperFood2025!**")
        
        return
    
    # Interface do Super Admin (autenticado)
    st.title("👑 Super Admin - Super Food")
    
    # Botão de logout
    if st.sidebar.button("🚪 Sair", use_container_width=True):
        st.session_state.autenticado = False
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Menu lateral
    menu = st.sidebar.radio(
        "Menu Principal",
        ["📊 Dashboard", "➕ Criar Restaurante", "🏪 Gerenciar Restaurantes", "💰 Assinaturas"]
    )
    
    # ==================== DASHBOARD ====================
    if menu == "📊 Dashboard":
        st.header("Dashboard Geral")
        
        restaurantes = listar_restaurantes()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total de Restaurantes", len(restaurantes))
        
        with col2:
            ativos = sum(1 for r in restaurantes if r['status'] == 'ativo')
            st.metric("Restaurantes Ativos", ativos)
        
        with col3:
            receita_mensal = sum(r['valor_plano'] for r in restaurantes if r['status'] == 'ativo')
            st.metric("Receita Mensal", f"R$ {receita_mensal:,.2f}")
        
        with col4:
            inativos = len(restaurantes) - ativos
            st.metric("Inativos/Suspensos", inativos)
        
        st.markdown("---")
        
        # Gráfico de planos
        if restaurantes:
            st.subheader("Distribuição por Plano")
            planos_count = {}
            for r in restaurantes:
                plano = r['plano']
                planos_count[plano] = planos_count.get(plano, 0) + 1
            
            st.bar_chart(planos_count)
    
    # ==================== CRIAR RESTAURANTE ====================
    elif menu == "➕ Criar Restaurante":
        st.header("Criar Novo Restaurante")
        
        with st.form("form_criar_restaurante", clear_on_submit=True):
            st.subheader("📋 Bloco 1 - Dados Básicos do Restaurante")
            
            col1, col2 = st.columns(2)
            
            with col1:
                nome_fantasia = st.text_input(
                    "Nome Fantasia *",
                    placeholder="Ex: Burger Elite",
                    help="Nome comercial que aparece no app"
                )
                razao_social = st.text_input(
                    "Razão Social (opcional)",
                    placeholder="Ex: Burger Elite LTDA"
                )
                cnpj = st.text_input(
                    "CNPJ (opcional)",
                    placeholder="00.000.000/0000-00",
                    help="Recomendado para emissão de nota fiscal"
                )
            
            with col2:
                email = st.text_input(
                    "Email Principal *",
                    placeholder="contato@burgerelite.com.br",
                    help="Será usado como login do dashboard"
                )
                telefone = st.text_input(
                    "Telefone/WhatsApp *",
                    placeholder="(11) 99999-9999",
                    help="Mínimo 10 dígitos"
                )
            
            st.markdown("---")
            st.subheader("📍 Bloco 2 - Endereço da Sede/Base")
            
            endereco_completo = st.text_area(
                "Endereço Completo *",
                placeholder="Rua Augusta 123, Bairro Centro, São Paulo, SP, Brasil, CEP 01000-000",
                help="Endereço completo com rua, número, bairro, cidade, estado e CEP"
            )
            
            st.markdown("---")
            st.subheader("💎 Bloco 3 - Plano de Assinatura")
            
            planos = {
                "Básico": {
                    "valor": 199.00,
                    "motoboys": 3,
                    "descricao": "Ideal para pequenos restaurantes - até 3 motoboys simultâneos"
                },
                "Essencial": {
                    "valor": 269.00,
                    "motoboys": 6,
                    "descricao": "Bom equilíbrio - até 6 motoboys simultâneos"
                },
                "Avançado": {
                    "valor": 360.00,
                    "motoboys": 12,
                    "descricao": "Para crescimento - até 12 motoboys simultâneos"
                },
                "Premium": {
                    "valor": 599.00,
                    "motoboys": 999,
                    "descricao": "Top: motoboys ilimitados + suporte prioritário"
                }
            }
            
            plano_selecionado = st.radio(
                "Escolha o Plano *",
                options=list(planos.keys()),
                format_func=lambda x: f"{x} - R$ {planos[x]['valor']:.2f}/mês - {planos[x]['descricao']}"
            )
            
            st.markdown("---")
            
            col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
            
            with col_btn2:
                submit_button = st.form_submit_button(
                    "✅ Criar Restaurante",
                    use_container_width=True,
                    type="primary"
                )
            
            # Processar formulário
            if submit_button:
                # Validações
                erros = []
                
                if not nome_fantasia or len(nome_fantasia.strip()) < 3:
                    erros.append("Nome Fantasia é obrigatório (mínimo 3 caracteres)")
                
                if not email or not validar_email(email):
                    erros.append("Email inválido")
                
                if not telefone or not validar_telefone(telefone):
                    erros.append("Telefone inválido (mínimo 10 dígitos)")
                
                if not endereco_completo or len(endereco_completo.strip()) < 10:
                    erros.append("Endereço completo é obrigatório")
                
                if cnpj and not validar_cnpj(cnpj):
                    erros.append("CNPJ inválido (deve ter 14 dígitos)")
                
                # Se houver erros, exibir
                if erros:
                    st.error("❌ Erros encontrados:")
                    for erro in erros:
                        st.error(f"  • {erro}")
                else:
                    # Criar restaurante
                    dados_restaurante = {
                        'nome_fantasia': nome_fantasia.strip(),
                        'razao_social': razao_social.strip() if razao_social else '',
                        'cnpj': re.sub(r'\D', '', cnpj) if cnpj else '',
                        'email': email.strip().lower(),
                        'telefone': re.sub(r'\D', '', telefone),
                        'endereco_completo': endereco_completo.strip(),
                        'plano': plano_selecionado,
                        'valor_plano': planos[plano_selecionado]['valor'],
                        'limite_motoboys': planos[plano_selecionado]['motoboys']
                    }
                    
                    sucesso, mensagem = criar_restaurante(dados_restaurante)
                    
                    if sucesso:
                        st.success(f"✅ {mensagem}")
                        st.balloons()
                        st.info(f"📧 Email de login: **{dados_restaurante['email']}**")
                        st.info(f"📱 O restaurante pode acessar o sistema com este email e a senha fornecida.")
                    else:
                        st.error(f"❌ {mensagem}")
    
    # ==================== GERENCIAR RESTAURANTES ====================
    elif menu == "🏪 Gerenciar Restaurantes":
        st.header("Gerenciar Restaurantes")
        
        restaurantes = listar_restaurantes()
        
        if not restaurantes:
            st.info("Nenhum restaurante cadastrado ainda.")
        else:
            # Filtros
            col1, col2, col3 = st.columns(3)
            
            with col1:
                filtro_status = st.selectbox(
                    "Filtrar por Status",
                    ["Todos", "ativo", "suspenso", "cancelado"]
                )
            
            with col2:
                filtro_plano = st.selectbox(
                    "Filtrar por Plano",
                    ["Todos", "Básico", "Essencial", "Avançado", "Premium"]
                )
            
            # Aplicar filtros
            restaurantes_filtrados = restaurantes
            
            if filtro_status != "Todos":
                restaurantes_filtrados = [r for r in restaurantes_filtrados if r['status'] == filtro_status]
            
            if filtro_plano != "Todos":
                restaurantes_filtrados = [r for r in restaurantes_filtrados if r['plano'] == filtro_plano]
            
            st.markdown(f"**{len(restaurantes_filtrados)} restaurante(s) encontrado(s)**")
            st.markdown("---")
            
            # Listar restaurantes
            for restaurante in restaurantes_filtrados:
                with st.expander(f"🏪 {restaurante['nome_fantasia']} - {restaurante['plano']} - {restaurante['status'].upper()}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**ID:** {restaurante['id']}")
                        st.markdown(f"**Email:** {restaurante['email']}")
                        st.markdown(f"**Telefone:** {restaurante['telefone']}")
                        st.markdown(f"**Plano:** {restaurante['plano']} (R$ {restaurante['valor_plano']:.2f}/mês)")
                    
                    with col2:
                        st.markdown(f"**Status:** {restaurante['status']}")
                        
                        data_venc = datetime.strptime(restaurante['data_vencimento'], '%Y-%m-%d %H:%M:%S.%f')
                        dias_restantes = (data_venc - datetime.now()).days
                        
                        st.markdown(f"**Vencimento:** {data_venc.strftime('%d/%m/%Y')}")
                        
                        if dias_restantes > 0:
                            st.markdown(f"**Dias restantes:** {dias_restantes} dias")
                        else:
                            st.markdown(f"**⚠️ VENCIDO há {abs(dias_restantes)} dias**")
                    
                    st.markdown("---")
                    
                    col_btn1, col_btn2, col_btn3 = st.columns(3)
                    
                    with col_btn1:
                        if st.button(f"🔄 Renovar", key=f"renovar_{restaurante['id']}"):
                            renovar_assinatura(
                                restaurante['id'],
                                restaurante['valor_plano'],
                                'Renovação Manual'
                            )
                            st.success("Assinatura renovada!")
                            st.rerun()
                    
                    with col_btn2:
                        if restaurante['status'] == 'ativo':
                            if st.button(f"⏸️ Suspender", key=f"suspender_{restaurante['id']}"):
                                atualizar_status_restaurante(restaurante['id'], 'suspenso')
                                st.success("Restaurante suspenso!")
                                st.rerun()
                        else:
                            if st.button(f"▶️ Ativar", key=f"ativar_{restaurante['id']}"):
                                atualizar_status_restaurante(restaurante['id'], 'ativo')
                                st.success("Restaurante ativado!")
                                st.rerun()
                    
                    with col_btn3:
                        if st.button(f"❌ Cancelar", key=f"cancelar_{restaurante['id']}"):
                            atualizar_status_restaurante(restaurante['id'], 'cancelado')
                            st.success("Restaurante cancelado!")
                            st.rerun()
    
    # ==================== ASSINATURAS ====================
    elif menu == "💰 Assinaturas":
        st.header("Gestão de Assinaturas")
        
        restaurantes = listar_restaurantes()
        
        if not restaurantes:
            st.info("Nenhum restaurante cadastrado ainda.")
        else:
            # Resumo financeiro
            col1, col2, col3 = st.columns(3)
            
            receita_mensal = sum(r['valor_plano'] for r in restaurantes if r['status'] == 'ativo')
            
            with col1:
                st.metric("Receita Mensal Recorrente", f"R$ {receita_mensal:,.2f}")
            
            with col2:
                receita_anual = receita_mensal * 12
                st.metric("Receita Anual Projetada", f"R$ {receita_anual:,.2f}")
            
            with col3:
                ticket_medio = receita_mensal / len([r for r in restaurantes if r['status'] == 'ativo']) if any(r['status'] == 'ativo' for r in restaurantes) else 0
                st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
            
            st.markdown("---")
            
            # Alertas de vencimento
            st.subheader("⚠️ Alertas de Vencimento")
            
            alertas = []
            for r in restaurantes:
                if r['status'] == 'ativo':
                    data_venc = datetime.strptime(r['data_vencimento'], '%Y-%m-%d %H:%M:%S.%f')
                    dias_restantes = (data_venc - datetime.now()).days
                    
                    if dias_restantes <= 7:
                        alertas.append((r, dias_restantes))
            
            if alertas:
                for restaurante, dias in sorted(alertas, key=lambda x: x[1]):
                    if dias < 0:
                        st.error(f"🔴 **{restaurante['nome_fantasia']}** - VENCIDO há {abs(dias)} dias")
                    elif dias == 0:
                        st.warning(f"🟡 **{restaurante['nome_fantasia']}** - Vence HOJE")
                    else:
                        st.warning(f"🟡 **{restaurante['nome_fantasia']}** - Vence em {dias} dia(s)")
            else:
                st.success("✅ Nenhum alerta de vencimento nos próximos 7 dias")

if __name__ == "__main__":
    main()