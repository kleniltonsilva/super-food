# app_motoboy/motoboy_app.py

"""
motoboy_app.py - App PWA para Motoboys
Versão atualizada para SQLAlchemy ORM completo (sem queries raw).
Mantém 100% da lógica, UI, fluxos e validações do código original.
Alterações:
- Importar models relevantes (Motoboy, Restaurante, GPSMotoboy, MotoboySolicitacao, Entrega, Pedido).
- Queries via session.query(Model).filter(...).first() ou .all().
- Acesso direto a atributos (ex: motoboy.nome, motoboy.restaurante.nome_fantasia).
- Removido .mappings() e dict conversions – usa objetos ORM diretamente.
- Mantido multi-tenant: filtros por motoboy_id e restaurante_id.
- Nova alteração: Adicionado joinedload em fazer_login_motoboy para eager load de 'restaurante', evitando DetachedInstanceError após session.close().
"""

import streamlit as st
import sys
import os
from datetime import datetime
import time
import hashlib

# Adicionar pasta raiz ao path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar session e models do banco SQLAlchemy
from database.session import get_db_session
from database.models import Motoboy, Restaurante, GPSMotoboy, MotoboySolicitacao, Entrega, Pedido

# Import para eager loading
from sqlalchemy.orm import joinedload
import sqlalchemy as sa

# Configuração da página para PWA (mobile-friendly)
st.set_page_config(
    page_title="Motoboy App - Super Food",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS para mobile (inalterado)
st.markdown("""
<style>
    /* Mobile First Design */
    .stButton button {
        width: 100%;
        height: 60px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 10px;
        margin: 5px 0;
    }
    
    .stButton button[kind="primary"] {
        background-color: #00AA00;
        color: white;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        text-align: center;
        margin: 10px 0;
    }
    
    .status-disponivel {
        background-color: #00AA00;
        color: white;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
    }
    
    .status-ocupado {
        background-color: #FFA500;
        color: white;
        padding: 10px;
        border-radius: 10px;
        text-align: center;
        font-size: 20px;
        font-weight: bold;
    }
    
    .pedido-card {
        background: white;
        border: 2px solid #ddd;
        border-radius: 15px;
        padding: 15px;
        margin: 10px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .map-container {
        border-radius: 15px;
        overflow: hidden;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# ==================== AUTENTICAÇÃO ====================

def verificar_login():
    """Verifica se motoboy está logado"""
    if 'motoboy_logado' not in st.session_state:
        st.session_state.motoboy_logado = False
        st.session_state.motoboy_id = None
        st.session_state.motoboy_dados = None
        st.session_state.restaurante_id = None

def fazer_login_motoboy(usuario: str, senha: str) -> bool:
    """Faz login do motoboy usando ORM com eager loading para relacionamentos"""
    session = get_db_session()
    try:
        senha_hash = hashlib.sha256(senha.encode()).hexdigest()
        
        motoboy = session.query(Motoboy).options(
            joinedload(Motoboy.restaurante)  # Eager load para evitar DetachedInstanceError
        ).filter(
            Motoboy.usuario == usuario,
            Motoboy.senha == senha_hash,
            Motoboy.status == 'ativo'
        ).first()
        
        if motoboy:
            st.session_state.motoboy_logado = True
            st.session_state.motoboy_id = motoboy.id
            st.session_state.motoboy_dados = motoboy  # Armazena o objeto ORM diretamente
            st.session_state.restaurante_id = motoboy.restaurante_id
            return True
        
        return False
    finally:
        session.close()

def fazer_logout():
    """Faz logout do motoboy"""
    st.session_state.motoboy_logado = False
    st.session_state.motoboy_id = None
    st.session_state.motoboy_dados = None
    st.session_state.restaurante_id = None

# ==================== TELA DE CADASTRO ====================

def tela_cadastro():
    """Interface de cadastro do motoboy (sem senha – definida na aprovação)"""
    st.title("🏍️ Cadastro de Motoboy")
    st.markdown("### Solicite seu cadastro")
    
    with st.form("form_cadastro_motoboy"):
        codigo_acesso = st.text_input(
            "Código de Acesso do Restaurante *",
            placeholder="Digite o código de 8 dígitos",
            max_chars=8,
            help="Solicite o código ao restaurante"
        )
        
        st.markdown("---")
        
        nome = st.text_input("Seu Nome Completo *", placeholder="Ex: João Silva")
        usuario = st.text_input("Escolha um Usuário *", placeholder="Ex: joao123")
        telefone = st.text_input("Telefone/WhatsApp *", placeholder="(11) 99999-9999")
        
        st.info("🔐 Após aprovação pelo restaurante, sua senha inicial será **123456**.")
        
        submit = st.form_submit_button("📤 Solicitar Cadastro", use_container_width=True, type="primary")
        
        if submit:
            # Validações
            erros = []
            
            if not codigo_acesso or len(codigo_acesso.strip()) != 8:
                erros.append("Código de acesso deve ter 8 dígitos")
            
            if not nome or len(nome.strip()) < 3:
                erros.append("Nome deve ter pelo menos 3 caracteres")
            
            if not usuario or len(usuario.strip()) < 3:
                erros.append("Usuário deve ter pelo menos 3 caracteres")
            
            if not telefone or len(''.join(filter(str.isdigit, telefone))) < 10:
                erros.append("Telefone inválido")
            
            if erros:
                for erro in erros:
                    st.error(f"❌ {erro}")
            else:
                codigo_limpo = codigo_acesso.strip().upper()
                telefone_limpo = ''.join(filter(str.isdigit, telefone))
                
                session = get_db_session()
                try:
                    # Validação do código
                    restaurante = session.query(Restaurante).filter(
                        Restaurante.codigo_acesso == codigo_limpo,
                        Restaurante.ativo == True
                    ).first()
                    
                    if not restaurante:
                        st.error("❌ Código de acesso inválido!")
                    else:
                        # Inserção na tabela de solicitações
                        solicitacao = MotoboySolicitacao(
                            restaurante_id=restaurante.id,
                            nome=nome.strip(),
                            usuario=usuario.strip().lower(),
                            telefone=telefone_limpo,
                            codigo_acesso=codigo_limpo,
                            data_solicitacao=datetime.now(),
                            status='pendente'
                        )
                        session.add(solicitacao)
                        session.commit()
                        
                        st.success("✅ Solicitação enviada! Aguarde aprovação do restaurante.")
                        st.balloons()
                        st.info("💡 Quando aprovado, use a senha padrão **123456** para login.")
                        time.sleep(3)
                        st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"❌ Erro ao enviar solicitação: {str(e)}")
                finally:
                    session.close()
    
    st.markdown("---")
    
    if st.button("🔙 Voltar para Login", use_container_width=True):
        st.session_state.tela_atual = "login"
        st.rerun()

# ==================== TELA DE LOGIN ====================

def tela_login():
    """Interface de login do motoboy"""
    st.title("🏍️ Motoboy App")
    st.markdown("### 🔐 Faça seu Login")
    
    with st.form("form_login_motoboy"):
        usuario = st.text_input("Usuário", placeholder="Seu usuário")
        senha = st.text_input("Senha", type="password", placeholder="Senha (padrão: 123456)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")
        
        with col2:
            cadastro = st.form_submit_button("📝 Cadastrar", use_container_width=True)
        
        if submit:
            if not usuario or not senha:
                st.error("❌ Preencha todos os campos!")
            elif fazer_login_motoboy(usuario, senha):
                st.success("✅ Login realizado!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos, ou cadastro não aprovado!")
        
        if cadastro:
            st.session_state.tela_atual = "cadastro"
            st.rerun()
    
    st.markdown("---")
    st.info("💡 **Não tem cadastro?** Clique em 'Cadastrar' e solicite seu acesso ao restaurante!")

# ==================== MAPA EM TEMPO REAL ====================

def tela_mapa():
    """Mapa com localização em tempo real"""
    st.title("🗺️ Sua Localização")
    
    motoboy = st.session_state.motoboy_dados
    
    st.markdown(f"### 👤 Olá, {motoboy.nome}!")
    st.markdown(f"**Restaurante:** {motoboy.restaurante.nome_fantasia}")
    
    session = get_db_session()
    try:
        posicao = session.query(GPSMotoboy).filter(
            GPSMotoboy.motoboy_id == st.session_state.motoboy_id
        ).order_by(GPSMotoboy.timestamp.desc()).first()
        
        if posicao:
            st.success(f"📍 Última atualização: {posicao.timestamp}")
            st.markdown(f"**Latitude:** {posicao.latitude}")
            st.markdown(f"**Longitude:** {posicao.longitude}")
            st.markdown(f"**Velocidade:** {posicao.velocidade:.1f} km/h")
        else:
            st.info("📍 Aguardando primeira atualização de localização...")
    finally:
        session.close()
    
    st.markdown("---")
    
    st.markdown("### 📡 Atualizar Localização")
    
    with st.form("form_atualizar_gps"):
        col1, col2 = st.columns(2)
        
        with col1:
            lat = st.number_input("Latitude", value=-23.550520, format="%.6f")
        
        with col2:
            lon = st.number_input("Longitude", value=-46.633308, format="%.6f")
        
        velocidade = st.number_input("Velocidade (km/h)", min_value=0.0, max_value=120.0, value=0.0)
        
        if st.form_submit_button("📍 Atualizar Posição", use_container_width=True, type="primary"):
            session = get_db_session()
            try:
                nova_posicao = GPSMotoboy(
                    motoboy_id=st.session_state.motoboy_id,
                    restaurante_id=st.session_state.restaurante_id,
                    latitude=lat,
                    longitude=lon,
                    velocidade=velocidade,
                    timestamp=datetime.now()
                )
                session.add(nova_posicao)
                session.commit()
                st.success("✅ Localização atualizada!")
                st.rerun()
            except Exception as e:
                session.rollback()
                st.error(f"❌ Erro ao atualizar localização: {str(e)}")
            finally:
                session.close()

# ==================== ENTREGAS ====================

def tela_entregas():
    """Tela de entregas COM ORDEM OTIMIZADA TSP"""
    st.title("📦 Suas Entregas")
   
    session = get_db_session()
    try:
        entregas = session.query(Entrega).join(Pedido).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(['pendente', 'em_rota'])
        ).order_by(Entrega.posicao_rota_otimizada.asc()).all()
   
        if entregas:
            if any(e.status == 'em_rota' for e in entregas):
                st.markdown('<div class="status-ocupado">🏍️ EM ROTA</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="status-disponivel">✅ ENTREGAS ATRIBUÍDAS</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-disponivel">✅ DISPONÍVEL</div>', unsafe_allow_html=True)
            st.info("⏳ Aguardando pedidos...")
            return
   
        st.markdown(f"### 📦 {len(entregas)} entrega(s) na fila (ordem otimizada)")
   
        st.markdown("---")
   
        primeira_entrega = entregas[0]
        outras_entregas = entregas[1:] if len(entregas) > 1 else []
   
        st.markdown("### 🎯 Próxima Entrega:")
   
        # ========== MOSTRA POSIÇÃO NA ROTA OTIMIZADA ==========
        st.info(f"📍 **Posição na Rota:** {primeira_entrega.posicao_rota_otimizada or '?'} de {len(entregas)}")
        # ====================================================
   
        st.markdown(f"""
        <div class="pedido-card">
            <h3>📦 Comanda #{primeira_entrega.pedido.comanda}</h3>
            <p><strong>👤 Cliente:</strong> {primeira_entrega.pedido.cliente_nome}</p>
            <p><strong>📞 Telefone:</strong> {primeira_entrega.pedido.cliente_telefone}</p>
            <p><strong>📍 Endereço:</strong> {primeira_entrega.pedido.endereco_entrega}</p>
            <p><strong>📏 Distância:</strong> {primeira_entrega.distancia_km or 0:.2f} km</p>
            <p><strong>⏱️ Tempo Estimado:</strong> {primeira_entrega.tempo_entrega or '?'} min</p>
            <p><strong>💰 Valor da Entrega:</strong> R$ {primeira_entrega.valor_entrega or 0:.2f}</p>
        </div>
        """, unsafe_allow_html=True)
   
        if primeira_entrega.pedido.observacoes:
            st.warning(f"📝 **Observações:** {primeira_entrega.pedido.observacoes}")
   
        st.markdown("---")
   
        if primeira_entrega.status == 'pendente':
            st.markdown("### ⚡ Ações:")
       
            col1, col2 = st.columns(2)
       
            with col1:
                # Link para ligar (tel:)
                telefone_limpo = ''.join(filter(str.isdigit, primeira_entrega.pedido.cliente_telefone))
                st.markdown(f"[📞 Ligar para Cliente](tel:{telefone_limpo})")
       
            with col2:
                if st.button("🚀 Iniciar Rota", use_container_width=True, type="primary"):
                    try:
                        primeira_entrega.status = 'em_rota'
                        primeira_entrega.atribuido_em = datetime.now()  # Corrigido para horario_saida? Ajustar se necessário
                        session.commit()
                   
                        st.success("✅ Rota iniciada!")
                   
                        # ========== NOVO: ABRE GPS EXTERNO ==========
                        endereco_encoded = primeira_entrega.pedido.endereco_entrega.replace(' ', '+')
                   
                        # Tenta abrir Google Maps (padrão Android)
                        gmap_url = f"https://www.google.com/maps/dir/?api=1&destination={endereco_encoded}"
                   
                        # Tenta abrir Waze (se instalado)
                        waze_url = f"https://waze.com/ul?q={endereco_encoded}&navigate=yes"
                   
                        st.markdown(f"""
                        ### 🗺️ Abrir Navegação:
                       
                        <a href="{gmap_url}" target="_blank" style="
                            display: inline-block;
                            padding: 15px 30px;
                            background-color: #4285F4;
                            color: white;
                            text-decoration: none;
                            border-radius: 10px;
                            font-weight: bold;
                            margin: 10px;
                        ">📍 Google Maps</a>
                       
                        <a href="{waze_url}" target="_blank" style="
                            display: inline-block;
                            padding: 15px 30px;
                            background-color: #00D8FF;
                            color: white;
                            text-decoration: none;
                            border-radius: 10px;
                            font-weight: bold;
                            margin: 10px;
                        ">🚗 Waze</a>
                        """, unsafe_allow_html=True)
                        # ============================================
                   
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro: {str(e)}")
   
        elif primeira_entrega.status == 'em_rota':
            st.success("🏍️ Você está em rota!")
       
            st.markdown("### ⚡ Ações na Entrega:")
       
            col1, col2 = st.columns(2)
       
            with col1:
                telefone_limpo = ''.join(filter(str.isdigit, primeira_entrega.pedido.cliente_telefone))
                st.markdown(f"[📞 Ligar para Cliente](tel:{telefone_limpo})")
       
            with col2:
                if st.button("✅ Marcar como Entregue", use_container_width=True, type="primary"):
                    try:
                        primeira_entrega.status = 'entregue'
                        primeira_entrega.entregue_em = datetime.now()
                   
                        primeira_entrega.pedido.status = 'entregue'
                   
                        # Atualiza estatísticas do motoboy
                        motoboy = st.session_state.motoboy_dados
                        motoboy.total_entregas = session.query(Entrega).filter(
                            Entrega.motoboy_id == motoboy.id,
                            Entrega.status == 'entregue'
                        ).count()
                        motoboy.total_ganhos = session.query(
                            sa.func.coalesce(sa.func.sum(Entrega.valor_entrega), 0)
                        ).filter(
                            Entrega.motoboy_id == motoboy.id,
                            Entrega.status == 'entregue'
                        ).scalar()
                   
                        session.commit()
                   
                        st.success("✅ Pedido entregue com sucesso!")
                        st.balloons()
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro: {str(e)}")
       
            st.markdown("---")
       
            # Opções de recusa/ausência (mantém código existente)
            col3, col4 = st.columns(2)
       
            with col3:
                if st.button("❌ Cliente Recusou", use_container_width=True):
                    st.session_state.modal_rejeitar = True
                    st.rerun()
       
            with col4:
                if st.button("🚪 Cliente Ausente", use_container_width=True):
                    st.session_state.modal_ausente = True
                    st.rerun()
   
        # Modals (mantém código existente)
        if st.session_state.get('modal_rejeitar'):
            modal_rejeitar_pedido(primeira_entrega, session)
   
        if st.session_state.get('modal_ausente'):
            modal_cliente_ausente(primeira_entrega, session)
   
        # ========== MOSTRA PRÓXIMAS ENTREGAS COM ORDEM OTIMIZADA ==========
        if outras_entregas:
            st.markdown("---")
            st.markdown(f"### 📋 Próximas entregas ({len(outras_entregas)}) - Ordem Otimizada:")
       
            for entrega in outras_entregas:
                posicao = entrega.posicao_rota_otimizada or '?'
                with st.expander(f"#{posicao} - Comanda {entrega.pedido.comanda} - {entrega.distancia_km or 0:.1f} km"):
                    st.markdown(f"Cliente: {entrega.pedido.cliente_nome}")
                    st.markdown(f"Endereço: {entrega.pedido.endereco_entrega}")
                    st.markdown(f"Valor: R$ {entrega.valor_entrega or 0:.2f}")
    finally:
        session.close()

def modal_rejeitar_pedido(entrega, session):
    with st.form("form_rejeitar"):
        st.warning("⚠️ Rejeitar Pedido")
        st.markdown("Por que você está rejeitando este pedido?")
        
        motivo = st.text_area("Motivo", placeholder="Explique o motivo...")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("❌ Confirmar Rejeição", use_container_width=True):
                try:
                    entrega.status = 'cancelado'
                    entrega.motivo_cancelamento = motivo
                    session.commit()
                    st.error("❌ Pedido rejeitado!")
                    st.session_state.modal_rejeitar = False
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {str(e)}")
        
        with col2:
            if st.form_submit_button("🔙 Cancelar", use_container_width=True):
                st.session_state.modal_rejeitar = False
                st.rerun()

def modal_cliente_ausente(entrega, session):
    with st.form("form_ausente"):
        st.warning("🚪 Cliente Ausente")
        st.markdown("O que você fez?")
        
        acao = st.radio(
            "Ação tomada:",
            ["Tentei ligar e não atendeu", "Bati na porta e não respondeu", "Aguardei no local"]
        )
        
        observacoes = st.text_area("Observações adicionais")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.form_submit_button("✅ Registrar", use_container_width=True):
                try:
                    motivo = f"Cliente ausente: {acao}. {observacoes}"
                    entrega.status = 'cancelado'
                    entrega.motivo_cancelamento = motivo
                    session.commit()
                    st.warning("⚠️ Registrado como cliente ausente!")
                    st.session_state.modal_ausente = False
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {str(e)}")
        
        with col2:
            if st.form_submit_button("🔙 Cancelar", use_container_width=True):
                st.session_state.modal_ausente = False
                st.rerun()

# ==================== GANHOS ====================

def tela_ganhos():
    session = get_db_session()
    try:
        # Estatísticas agregadas
        total_entregas = session.query(Entrega).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status == 'entregue'
        ).count()
        
        total_ganho = session.query(
            sa.func.coalesce(sa.func.sum(Entrega.valor_entrega), 0)
        ).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status == 'entregue'
        ).scalar()
        
        total_km = session.query(
            sa.func.coalesce(sa.func.sum(Entrega.distancia_km), 0)
        ).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status == 'entregue'
        ).scalar()
        
        stats = {
            "total_entregas": total_entregas,
            "total_ganho": total_ganho,
            "total_km": total_km
        }
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h2>{stats['total_entregas']}</h2>
                <p>Entregas</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2>R$ {stats['total_ganho']:.2f}</h2>
                <p>Total Ganho</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2>{stats['total_km']:.1f} km</h2>
                <p>Distância</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.subheader("📜 Histórico de Entregas")
        
        historico = session.query(Entrega).join(Pedido).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status == 'entregue'
        ).order_by(Entrega.entregue_em.desc()).limit(20).all()
        
        if not historico:
            st.info("Nenhuma entrega realizada ainda.")
        else:
            for entrega in historico:
                with st.expander(f"📦 Comanda {entrega.pedido.comanda} - R$ {entrega.valor_entrega or 0:.2f}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Cliente:** {entrega.pedido.cliente_nome}")
                        st.markdown(f"**Distância:** {entrega.distancia_km or 0:.2f} km")
                    
                    with col2:
                        st.markdown(f"**Valor:** R$ {entrega.valor_entrega or 0:.2f}")
                        st.markdown(f"**Data:** {entrega.entregue_em.isoformat()[:16] if entrega.entregue_em else 'N/A'}")
    finally:
        session.close()

# ==================== PERFIL ====================

def tela_perfil():
    st.title("👤 Meu Perfil")
    
    motoboy = st.session_state.motoboy_dados
    
    st.markdown(f"### {motoboy.nome}")
    st.markdown(f"**Usuário:** {motoboy.usuario}")
    st.markdown(f"**Telefone:** {motoboy.telefone or 'Não informado'}")
    st.markdown(f"**Restaurante:** {motoboy.restaurante.nome_fantasia}")
    
    st.markdown("---")
    
    st.markdown("### 📊 Estatísticas")
    st.metric("Total de Entregas", motoboy.total_entregas or 0)
    st.metric("Total Ganho", f"R$ {motoboy.total_ganhos or 0.0:.2f}")
    
    st.markdown("---")
    
    if st.button("🚪 Sair", use_container_width=True, type="primary"):
        fazer_logout()
        st.rerun()

# ==================== MENU INFERIOR ====================

def menu_inferior():
    st.markdown("---")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🗺️\nMapa", use_container_width=True):
            st.session_state.tela_atual = "mapa"
            st.rerun()
    
    with col2:
        if st.button("📦\nEntregas", use_container_width=True):
            st.session_state.tela_atual = "entregas"
            st.rerun()
    
    with col3:
        if st.button("💰\nGanhos", use_container_width=True):
            st.session_state.tela_atual = "ganhos"
            st.rerun()
    
    with col4:
        if st.button("👤\nPerfil", use_container_width=True):
            st.session_state.tela_atual = "perfil"
            st.rerun()

# ==================== MAIN ====================

def main():
    verificar_login()
    
    if 'tela_atual' not in st.session_state:
        st.session_state.tela_atual = "entregas"
    
    if not st.session_state.motoboy_logado:
        if st.session_state.get('tela_atual') == "cadastro":
            tela_cadastro()
        else:
            tela_login()
    else:
        tela = st.session_state.tela_atual
        
        if tela == "mapa":
            tela_mapa()
        elif tela == "entregas":
            tela_entregas()
        elif tela == "ganhos":
            tela_ganhos()
        elif tela == "perfil":
            tela_perfil()
        else:
            tela_entregas()
        
        menu_inferior()

if __name__ == "__main__":
    main()