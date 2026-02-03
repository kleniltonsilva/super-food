"""
Super Admin - Super Food SaaS
Sistema de gerenciamento de restaurantes com SQLAlchemy
TODAS as funcionalidades originais mantidas intactas
"""

import streamlit as st
import re
from datetime import datetime, timedelta
import sys
import os

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Importar database SQLAlchemy
from database.session import get_db_session, init_db, criar_config_padrao_restaurante
from database.models import Restaurante, SuperAdmin, ConfigRestaurante

# Configuração da página
st.set_page_config(
    page_title="Super Admin - Super Food",
    page_icon="👑",
    layout="wide"
)

# ==================== FUNÇÕES DE VALIDAÇÃO ====================

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

# ==================== FUNÇÕES DE BANCO DE DADOS ====================

def criar_restaurante(dados):
    """
    Cria um novo restaurante no banco de dados
    Retorna: (sucesso: bool, mensagem: str)
    """
    db = get_db_session()
    try:
        # Verificar se email já existe
        existe = db.query(Restaurante).filter(
            Restaurante.email == dados['email']
        ).first()
        
        if existe:
            return False, "Este email já está cadastrado!"
        
        # ========== CORREÇÃO CIRÚRGICA 1: Verificar CNPJ duplicado ==========
        cnpj_limpo = dados.get('cnpj')
        if cnpj_limpo:  # Só verifica se CNPJ foi informado
            existe_cnpj = db.query(Restaurante).filter(
                Restaurante.cnpj == cnpj_limpo
            ).first()
            
            if existe_cnpj:
                return False, f"Este CNPJ já está cadastrado no restaurante '{existe_cnpj.nome_fantasia}'!"
        # ====================================================================
        
        # Calcular data de vencimento (30 dias)
        data_vencimento = datetime.now() + timedelta(days=30)
        
        # Gerar senha padrão (primeiros 6 dígitos do telefone)
        telefone_numeros = re.sub(r'\D', '', dados['telefone'])
        senha_padrao = telefone_numeros[:6] if len(telefone_numeros) >= 6 else "123456"
        
        # ========== CORREÇÃO CIRÚRGICA 2: CNPJ NULL se vazio ==========
        # Criar restaurante
        restaurante = Restaurante(
            nome=dados['nome_fantasia'],
            nome_fantasia=dados['nome_fantasia'],
            razao_social=dados.get('razao_social') or None,
            cnpj=cnpj_limpo or None,  # NULL se vazio (evita string vazia)
            email=dados['email'],
            telefone=dados['telefone'],
            endereco_completo=dados['endereco_completo'],
            plano=dados['plano'],
            valor_plano=dados['valor_plano'],
            limite_motoboys=dados['limite_motoboys'],
            ativo=True,
            status='ativo',
            data_vencimento=data_vencimento
        )
        # ================================================================
        
        # Gerar código de acesso único
        restaurante.gerar_codigo_acesso()
        
        # Setar senha
        restaurante.set_senha(senha_padrao)
        
        db.add(restaurante)
        db.flush()  # Para obter o ID
        
        # Criar configuração padrão
        criar_config_padrao_restaurante(restaurante.id)
        
        db.commit()
        
        return True, f"Restaurante criado com sucesso! Senha padrão: {senha_padrao}"
        
    except Exception as e:
        db.rollback()
        return False, f"Erro ao criar restaurante: {str(e)}"
    finally:
        db.close()

def listar_restaurantes():
    """Lista todos os restaurantes cadastrados"""
    db = get_db_session()
    try:
        restaurantes = db.query(Restaurante).order_by(Restaurante.criado_em.desc()).all()
        
        # Converter para dict para compatibilidade com código original
        resultado = []
        for r in restaurantes:
            resultado.append({
                'id': r.id,
                'nome_fantasia': r.nome_fantasia,
                'email': r.email,
                'telefone': r.telefone,
                'plano': r.plano,
                'valor_plano': r.valor_plano,
                'status': r.status,
                'data_vencimento': r.data_vencimento.strftime('%Y-%m-%d %H:%M:%S.%f') if r.data_vencimento else ''
            })
        
        return resultado
        
    except Exception as e:
        st.error(f"Erro ao listar restaurantes: {str(e)}")
        return []
    finally:
        db.close()

def buscar_restaurante_por_id(restaurante_id):
    """Busca restaurante por ID"""
    db = get_db_session()
    try:
        restaurante = db.query(Restaurante).filter(Restaurante.id == restaurante_id).first()
        
        if restaurante:
            return {
                'id': restaurante.id,
                'nome_fantasia': restaurante.nome_fantasia,
                'email': restaurante.email,
                'telefone': restaurante.telefone,
                'plano': restaurante.plano,
                'valor_plano': restaurante.valor_plano,
                'status': restaurante.status,
                'data_vencimento': restaurante.data_vencimento
            }
        return None
        
    except Exception as e:
        st.error(f"Erro ao buscar restaurante: {str(e)}")
        return None
    finally:
        db.close()

def atualizar_status_restaurante(restaurante_id, novo_status):
    """Atualiza status do restaurante (ativo/suspenso/cancelado)"""
    db = get_db_session()
    try:
        restaurante = db.query(Restaurante).filter(Restaurante.id == restaurante_id).first()
        
        if restaurante:
            restaurante.status = novo_status
            restaurante.ativo = (novo_status == 'ativo')
            db.commit()
            return True
        
        return False
        
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao atualizar status: {str(e)}")
        return False
    finally:
        db.close()

def renovar_assinatura(restaurante_id, valor_pago, forma_pagamento):
    """Renova assinatura do restaurante por mais 30 dias"""
    db = get_db_session()
    try:
        restaurante = db.query(Restaurante).filter(Restaurante.id == restaurante_id).first()
        
        if not restaurante:
            return False
        
        # Calcular nova data de vencimento
        data_atual_vencimento = restaurante.data_vencimento or datetime.now()
        
        if data_atual_vencimento < datetime.now():
            # Se vencido, renovar a partir de hoje
            nova_data_vencimento = datetime.now() + timedelta(days=30)
        else:
            # Se não vencido, adicionar 30 dias ao vencimento atual
            nova_data_vencimento = data_atual_vencimento + timedelta(days=30)
        
        # Atualizar restaurante
        restaurante.data_vencimento = nova_data_vencimento
        restaurante.status = 'ativo'
        restaurante.ativo = True
        
        db.commit()
        return True
        
    except Exception as e:
        db.rollback()
        st.error(f"Erro ao renovar assinatura: {str(e)}")
        return False
    finally:
        db.close()

# ==================== AUTENTICAÇÃO ====================

def verificar_login(usuario, senha):
    """Verifica credenciais do super admin"""
    db = get_db_session()
    try:
        admin = db.query(SuperAdmin).filter(
            SuperAdmin.usuario == usuario,
            SuperAdmin.ativo == True
        ).first()
        
        if admin and admin.verificar_senha(senha):
            return True
        
        return False
        
    except Exception as e:
        st.error(f"Erro ao verificar login: {str(e)}")
        return False
    finally:
        db.close()

# ==================== INTERFACE PRINCIPAL ====================

def main():
    # Inicializar banco de dados (se necessário)
    try:
        init_db()
    except:
        pass  # Tabelas já existem
    
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
            st.subheader("🌐 Bloco 4 - Configuração do Site do Cliente")

            criar_site = st.checkbox("Criar Site do Cliente Automaticamente", value=True, help="Cria site público para pedidos online")

            if criar_site:
                col1, col2 = st.columns(2)
    
                with col1:
                    tipo_restaurante = st.selectbox(
                        "Tipo de Restaurante *",
                        ["pizzaria", "hamburgueria", "japones", "churrascaria", "la_carte", "acai", "marmitex", "geral"],
                        format_func=lambda x: {
                            "pizzaria": "🍕 Pizzaria",
                            "hamburgueria": "🍔 Hamburgueria",
                            "japones": "🍣 Culinária Japonesa",
                            "churrascaria": "🥩 Churrascaria",
                            "la_carte": "🍽️ À La Carte",
                            "acai": "🍇 Açaí/Sorveteria",
                            "marmitex": "🍱 Marmitex",
                            "geral": "🍴 Geral"
                        }.get(x, x),
                        help="Define o tipo de cardápio e variações de produtos"
                    )
        
                    cor_primaria = st.color_picker("Cor Primária do Site", "#FF6B35", help="Cor principal (botões, destaques)")
        
                    whatsapp = st.text_input(
                         "WhatsApp (com DDD)",
                          placeholder="11999999999",
                          help="Aparecerá como botão flutuante na página inicial"
                  )
    
                with col2:
                    pedido_minimo = st.number_input(
                        "Pedido Mínimo (R$)",
                        min_value=0.0,
                        value=15.0,
                        step=5.0,
                        help="Valor mínimo para aceitar pedidos"
                    )
        
                    cor_secundaria = st.color_picker("Cor Secundária", "#004E89", help="Cor de apoio")
        
                    tempo_entrega = st.number_input(
                       "Tempo Estimado de Entrega (min)",
                        min_value=10,
                        max_value=180,
                        value=50,
                        step=5
                    )
        
                    tempo_retirada = st.number_input(
                       "Tempo Estimado para Retirada (min)",
                        min_value=5,
                        max_value=120,
                        value=20,
                        step=5
                    )
    
                st.info(f"💡 **Tipo selecionado: {tipo_restaurante.upper()}** - Categorias padrão serão criadas automaticamente")


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
                
                if criar_site and not whatsapp:
                    st.warning("⚠️ WhatsApp não informado. Site será criado sem botão flutuante de contato.")
                
                # Se houver erros, exibir
                if erros:
                    st.error("❌ Erros encontrados:")
                    for erro in erros:
                        st.error(f"  • {erro}")
                else:
                    # ========== CORREÇÃO CIRÚRGICA 3: Limpar CNPJ ==========
                    cnpj_limpo = re.sub(r'\D', '', cnpj) if cnpj and cnpj.strip() else None
                    # =======================================================
                    
                    # Criar restaurante
                    dados_restaurante = {
                        'nome_fantasia': nome_fantasia.strip(),
                        'razao_social': razao_social.strip() if razao_social and razao_social.strip() else None,
                        'cnpj': cnpj_limpo,
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
                        
                        # ========== NOVO: CRIAR SITE DO CLIENTE ==========
                        if criar_site:
                            session = get_db_session()
                            try:
                                # Busca o restaurante recém-criado
                                restaurante = session.query(Restaurante).filter(
                                    Restaurante.email == dados_restaurante['email']
                                ).first()
                                
                                if restaurante:
                                    # Importa funções do menu_templates
                                    from backend.app.utils.menu_templates import (
                                        criar_categorias_padrao,
                                        criar_site_config_padrao
                                    )
                                    
                                    # Cria SiteConfig
                                    dados_site = {
                                        "cor_primaria": cor_primaria,
                                        "cor_secundaria": cor_secundaria,
                                        "whatsapp": whatsapp,
                                        "pedido_minimo": pedido_minimo,
                                        "tempo_entrega": tempo_entrega,
                                        "tempo_retirada": tempo_retirada
                                    }
                                    
                                    criar_site_config_padrao(
                                        restaurante.id,
                                        tipo_restaurante,
                                        dados_site,
                                        session
                                    )
                                    
                                    # Cria categorias padrão
                                    categorias = criar_categorias_padrao(
                                        restaurante.id,
                                        tipo_restaurante,
                                        session
                                    )
                                    
                                    session.commit()
                                    
                                    st.success(f"🌐 Site criado com sucesso! Tipo: {tipo_restaurante.upper()}")
                                    st.success(f"✅ {len(categorias)} categorias criadas automaticamente")
                                    
                                    # Mostra URL do site
                                    url_site = f"http://seu-dominio.com/site/{restaurante.codigo_acesso}"
                                    st.markdown(f"### 🔗 URL do Site")
                                    st.code(url_site, language="text")
                                    st.markdown(f"[🌐 Abrir Site (após deploy)]({url_site})")
                                    
                            except Exception as e:
                                session.rollback()
                                st.error(f"❌ Erro ao criar site: {str(e)}")
                            finally:
                                session.close()
                        
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
                        
                        if restaurante['data_vencimento']:
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
                            if renovar_assinatura(
                                restaurante['id'],
                                restaurante['valor_plano'],
                                'Renovação Manual'
                            ):
                                st.success("Assinatura renovada!")
                                st.rerun()
                    
                    with col_btn2:
                        if restaurante['status'] == 'ativo':
                            if st.button(f"⏸️ Suspender", key=f"suspender_{restaurante['id']}"):
                                if atualizar_status_restaurante(restaurante['id'], 'suspenso'):
                                    st.success("Restaurante suspenso!")
                                    st.rerun()
                        else:
                            if st.button(f"▶️ Ativar", key=f"ativar_{restaurante['id']}"):
                                if atualizar_status_restaurante(restaurante['id'], 'ativo'):
                                    st.success("Restaurante ativado!")
                                    st.rerun()
                    
                    with col_btn3:
                        if st.button(f"❌ Cancelar", key=f"cancelar_{restaurante['id']}"):
                            if atualizar_status_restaurante(restaurante['id'], 'cancelado'):
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
                ativos = [r for r in restaurantes if r['status'] == 'ativo']
                ticket_medio = receita_mensal / len(ativos) if ativos else 0
                st.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}")
            
            st.markdown("---")
            
            # Alertas de vencimento
            st.subheader("⚠️ Alertas de Vencimento")
            
            alertas = []
            for r in restaurantes:
                if r['status'] == 'ativo' and r['data_vencimento']:
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