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
from database.models import Motoboy, Restaurante, GPSMotoboy, MotoboySolicitacao, Entrega, Pedido, ConfigRestaurante

# Import para eager loading
from sqlalchemy.orm import joinedload
import sqlalchemy as sa

# Import para cálculos de ganhos
from utils.calculos import obter_ganhos_dia_motoboy
# Imports de utils mantidos apenas os necessários
from utils.motoboy_selector import (
    finalizar_entrega_motoboy,
    marcar_motoboy_disponivel,
    obter_estatisticas_motoboy
)

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

def fazer_login_motoboy(codigo_restaurante: str, usuario: str, senha: str) -> dict:
    """
    Faz login do motoboy usando código do restaurante + usuário + senha.

    O código do restaurante é obrigatório para isolamento multi-tenant.
    Isso garante que motoboys com mesmo usuário em restaurantes diferentes
    não tenham conflito.

    Returns:
        dict com 'sucesso' (bool) e 'erro' (str) se falhou
    """
    session = get_db_session()
    try:
        # Primeiro, validar o código do restaurante
        restaurante = session.query(Restaurante).filter(
            Restaurante.codigo_acesso == codigo_restaurante.strip().upper(),
            Restaurante.ativo == True
        ).first()

        if not restaurante:
            return {'sucesso': False, 'erro': 'Código do restaurante inválido'}

        senha_hash = hashlib.sha256(senha.encode()).hexdigest()

        # Buscar motoboy filtrando por restaurante_id para isolamento
        motoboy = session.query(Motoboy).options(
            joinedload(Motoboy.restaurante)
        ).filter(
            Motoboy.restaurante_id == restaurante.id,  # ISOLAMENTO POR RESTAURANTE
            Motoboy.usuario == usuario.strip().lower(),
            Motoboy.senha == senha_hash,
            Motoboy.status == 'ativo'
        ).first()

        if not motoboy:
            return {'sucesso': False, 'erro': 'Usuário ou senha incorretos'}

        # Marcar motoboy como disponível ao fazer login
        motoboy.disponivel = True
        motoboy.ultimo_status_online = datetime.now()
        session.commit()

        # Converter ORM para dict para evitar DetachedInstanceError
        motoboy_dados = {
            'id': motoboy.id,
            'nome': motoboy.nome,
            'usuario': motoboy.usuario,
            'telefone': motoboy.telefone,
            'status': motoboy.status,
            'disponivel': motoboy.disponivel,
            'em_rota': motoboy.em_rota,
            'restaurante_id': motoboy.restaurante_id,
            'restaurante_nome': motoboy.restaurante.nome_fantasia if motoboy.restaurante else 'N/A',
            'restaurante_codigo': motoboy.restaurante.codigo_acesso if motoboy.restaurante else '',
            'capacidade_entregas': motoboy.capacidade_entregas or 3,
            'entregas_pendentes': motoboy.entregas_pendentes or 0,
            'total_entregas': motoboy.total_entregas or 0,
            'total_ganhos': motoboy.total_ganhos or 0,
            'total_km': motoboy.total_km or 0,
            'ordem_hierarquia': motoboy.ordem_hierarquia or 0,
        }

        st.session_state.motoboy_logado = True
        st.session_state.motoboy_id = motoboy.id
        st.session_state.motoboy_dados = motoboy_dados
        st.session_state.restaurante_id = motoboy.restaurante_id

        return {'sucesso': True}

    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}
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
                    # Validação do código do restaurante
                    restaurante = session.query(Restaurante).filter(
                        Restaurante.codigo_acesso == codigo_limpo,
                        Restaurante.ativo == True
                    ).first()

                    if not restaurante:
                        st.error("❌ Código de acesso inválido!")
                    else:
                        usuario_limpo = usuario.strip().lower()

                        # Verificar se usuário já existe como motoboy neste restaurante
                        motoboy_existente = session.query(Motoboy).filter(
                            Motoboy.restaurante_id == restaurante.id,
                            Motoboy.usuario == usuario_limpo
                        ).first()

                        if motoboy_existente:
                            st.error("❌ Este usuário já está cadastrado neste restaurante!")
                        else:
                            # Verificar se já existe solicitação pendente com mesmo usuário
                            solicitacao_existente = session.query(MotoboySolicitacao).filter(
                                MotoboySolicitacao.restaurante_id == restaurante.id,
                                MotoboySolicitacao.usuario == usuario_limpo,
                                MotoboySolicitacao.status == 'pendente'
                            ).first()

                            if solicitacao_existente:
                                st.warning("⚠️ Já existe uma solicitação pendente com este usuário. Aguarde a aprovação.")
                            else:
                                # Criar solicitação
                                solicitacao = MotoboySolicitacao(
                                    restaurante_id=restaurante.id,
                                    nome=nome.strip(),
                                    usuario=usuario_limpo,
                                    telefone=telefone_limpo,
                                    codigo_acesso=codigo_limpo,
                                    data_solicitacao=datetime.now(),
                                    status='pendente'
                                )
                                session.add(solicitacao)
                                session.commit()

                                st.success("✅ Solicitação enviada! Aguarde aprovação do restaurante.")
                                st.balloons()
                                st.info(f"💡 Quando aprovado, use:\n- **Código:** {codigo_limpo}\n- **Usuário:** {usuario_limpo}\n- **Senha:** 123456")
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
        codigo_restaurante = st.text_input(
            "Código do Restaurante *",
            placeholder="Ex: ABC12345",
            max_chars=8,
            help="Código de 8 dígitos fornecido pelo restaurante"
        )
        usuario = st.text_input("Usuário *", placeholder="Seu usuário")
        senha = st.text_input("Senha *", type="password", placeholder="Senha (padrão: 123456)")

        col1, col2 = st.columns(2)

        with col1:
            submit = st.form_submit_button("🚀 Entrar", use_container_width=True, type="primary")

        with col2:
            cadastro = st.form_submit_button("📝 Cadastrar", use_container_width=True)

        if submit:
            if not codigo_restaurante or not usuario or not senha:
                st.error("❌ Preencha todos os campos!")
            else:
                resultado = fazer_login_motoboy(codigo_restaurante, usuario, senha)
                if resultado['sucesso']:
                    st.success("✅ Login realizado!")
                    st.rerun()
                else:
                    st.error(f"❌ {resultado['erro']}")

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

    # Acessar como dict (não ORM) para evitar DetachedInstanceError
    st.markdown(f"### 👤 Olá, {motoboy['nome']}!")
    st.markdown(f"**Restaurante:** {motoboy['restaurante_nome']}")
    
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

def tocar_som_notificacao():
    """Injeta JavaScript para tocar som de notificação"""
    # Som de notificação usando Web Audio API (funciona em PWA)
    st.markdown("""
    <script>
    (function() {
        // Criar contexto de áudio
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // Criar oscilador para som de notificação
        function playNotificationSound() {
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);

            oscillator.frequency.value = 800;
            oscillator.type = 'sine';

            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        }

        // Tocar som 3 vezes com intervalo
        playNotificationSound();
        setTimeout(playNotificationSound, 600);
        setTimeout(playNotificationSound, 1200);
    })();
    </script>
    """, unsafe_allow_html=True)


def tela_entregas():
    """Tela de entregas COM ORDEM OTIMIZADA e sistema sequencial"""
    st.title("📦 Suas Entregas")

    session = get_db_session()
    try:
        # Buscar todas as entregas pendentes ou em rota
        entregas = session.query(Entrega).join(Pedido).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(['pendente', 'em_rota'])
        ).order_by(Entrega.posicao_rota_otimizada.asc()).all()

        # Verificar se há novas entregas para tocar som
        entregas_ids = [e.id for e in entregas]
        if 'ultimas_entregas_ids' not in st.session_state:
            st.session_state.ultimas_entregas_ids = []

        # Se há novas entregas, tocar som de notificação
        novas_entregas = [e for e in entregas_ids if e not in st.session_state.ultimas_entregas_ids]
        if novas_entregas and entregas:
            tocar_som_notificacao()
            st.toast(f"🔔 Nova(s) entrega(s) recebida(s)!", icon="🏍️")

        st.session_state.ultimas_entregas_ids = entregas_ids

        total_entregas = len(entregas)
        entregas_em_rota = [e for e in entregas if e.status == 'em_rota']
        entregas_pendentes = [e for e in entregas if e.status == 'pendente']

        # ==================== STATUS GERAL ====================
        if entregas_em_rota:
            entrega_atual = entregas_em_rota[0]
            posicao_atual = next((i+1 for i, e in enumerate(entregas) if e.id == entrega_atual.id), 1)
            st.markdown(f"""
            <div class="status-ocupado">
                🏍️ EM ENTREGA - Pedido {posicao_atual}/{total_entregas}
            </div>
            """, unsafe_allow_html=True)
        elif entregas_pendentes:
            st.markdown(f"""
            <div class="status-disponivel" style="background-color: #FFA500;">
                📦 {total_entregas} ENTREGA(S) ATRIBUÍDA(S)
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-disponivel">✅ DISPONÍVEL</div>', unsafe_allow_html=True)
            st.info("⏳ Aguardando pedidos do restaurante...")
            st.caption("💡 A tela atualiza automaticamente quando você receber novos pedidos.")
            return

        st.markdown("---")

        # ==================== BOTÃO INICIAR ENTREGAS (quando tem pendentes) ====================
        if entregas_pendentes and not entregas_em_rota:
            st.markdown(f"### 📦 {total_entregas} Entrega(s) na Fila")

            # Mostrar resumo das entregas
            for i, e in enumerate(entregas_pendentes[:4], 1):  # Mostra até 4
                st.markdown(f"**{i}.** {e.pedido.cliente_nome} - {e.pedido.endereco_entrega[:40]}...")

            if len(entregas_pendentes) > 4:
                st.caption(f"... e mais {len(entregas_pendentes) - 4} entrega(s)")

            st.markdown("---")

            # Botão grande para iniciar
            if st.button("🚀 INICIAR ENTREGAS", use_container_width=True, type="primary", key="btn_iniciar_todas"):
                try:
                    # Inicia a primeira entrega da fila
                    primeira = entregas_pendentes[0]
                    primeira.status = 'em_rota'
                    primeira.atribuido_em = datetime.now()
                    primeira.pedido.status = 'saiu_entrega'
                    session.commit()
                    st.success("✅ Rota iniciada! Siga para a primeira entrega.")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {str(e)}")
            return

        # ==================== ENTREGA ATUAL (em rota) ====================
        if entregas_em_rota:
            entrega_atual = entregas_em_rota[0]
            posicao_atual = next((i+1 for i, e in enumerate(entregas) if e.id == entrega_atual.id), 1)

            st.markdown(f"### 🎯 Entrega Atual ({posicao_atual}/{total_entregas})")

            # Card da entrega atual
            st.markdown(f"""
            <div class="pedido-card" style="border-color: #00AA00; border-width: 3px;">
                <h3>📦 Comanda #{entrega_atual.pedido.comanda}</h3>
                <p><strong>👤 Cliente:</strong> {entrega_atual.pedido.cliente_nome}</p>
                <p><strong>📞 Telefone:</strong> {entrega_atual.pedido.cliente_telefone or 'Não informado'}</p>
                <p><strong>📍 Endereço:</strong> {entrega_atual.pedido.endereco_entrega}</p>
                <p><strong>📏 Distância:</strong> {entrega_atual.distancia_km or entrega_atual.pedido.distancia_restaurante_km or 0:.1f} km</p>
                <p><strong>💰 Ganho Estimado:</strong> R$ {entrega_atual.valor_motoboy or entrega_atual.valor_entrega or 0:.2f}</p>
            </div>
            """, unsafe_allow_html=True)

            if entrega_atual.pedido.observacoes:
                st.warning(f"📝 **Observações:** {entrega_atual.pedido.observacoes}")

            # Forma de pagamento
            if entrega_atual.pedido.forma_pagamento:
                pagamento = entrega_atual.pedido.forma_pagamento
                troco = entrega_atual.pedido.troco_para
                if troco and pagamento == 'Dinheiro':
                    st.info(f"💵 Pagamento: {pagamento} - Troco para R$ {troco:.2f}")
                else:
                    st.info(f"💳 Pagamento: {pagamento}")

            st.markdown("---")

            # ==================== BOTÕES DE NAVEGAÇÃO GPS ====================
            st.markdown("### 🗺️ Navegação")

            endereco_encoded = entrega_atual.pedido.endereco_entrega.replace(' ', '+').replace('\n', '+')
            gmap_url = f"https://www.google.com/maps/dir/?api=1&destination={endereco_encoded}"
            waze_url = f"https://waze.com/ul?q={endereco_encoded}&navigate=yes"

            col_nav1, col_nav2 = st.columns(2)
            with col_nav1:
                st.markdown(f"""
                <a href="{gmap_url}" target="_blank" style="
                    display: block;
                    padding: 15px;
                    background-color: #4285F4;
                    color: white;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: bold;
                    text-align: center;
                ">📍 Google Maps</a>
                """, unsafe_allow_html=True)
            with col_nav2:
                st.markdown(f"""
                <a href="{waze_url}" target="_blank" style="
                    display: block;
                    padding: 15px;
                    background-color: #00D8FF;
                    color: white;
                    text-decoration: none;
                    border-radius: 10px;
                    font-weight: bold;
                    text-align: center;
                ">🚗 Waze</a>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # ==================== AÇÕES DA ENTREGA ====================
            st.markdown("### ⚡ Ações")

            # Verificar estado atual
            estado_entrega = st.session_state.get(f'estado_entrega_{entrega_atual.id}', 'em_rota')

            if estado_entrega == 'em_rota':
                # Botão: Cheguei ao Destino
                if st.button("📍 CHEGUEI AO DESTINO", use_container_width=True, type="primary"):
                    st.session_state[f'estado_entrega_{entrega_atual.id}'] = 'no_destino'
                    st.rerun()

                # Ligar para cliente
                telefone = entrega_atual.pedido.cliente_telefone
                if telefone:
                    telefone_limpo = ''.join(filter(str.isdigit, telefone))
                    st.markdown(f"[📞 Ligar para Cliente](tel:{telefone_limpo})")

            elif estado_entrega == 'no_destino':
                st.success("📍 Você chegou ao destino!")

                # Botão principal: Entrega Concluída
                if st.button("✅ ENTREGA CONCLUÍDA", use_container_width=True, type="primary"):
                    try:
                        distancia_km = entrega_atual.distancia_km or entrega_atual.pedido.distancia_restaurante_km or 0

                        resultado = finalizar_entrega_motoboy(
                            entrega_atual.id,
                            distancia_km if distancia_km else None,
                            session
                        )

                        if resultado['sucesso']:
                            valor_ganho = resultado.get('valor_ganho', 0)
                            st.success(f"✅ Entrega concluída! Ganho: R$ {valor_ganho:.2f}")

                            # Limpar estado
                            if f'estado_entrega_{entrega_atual.id}' in st.session_state:
                                del st.session_state[f'estado_entrega_{entrega_atual.id}']

                            # Verificar se há mais entregas
                            proximas = [e for e in entregas if e.id != entrega_atual.id and e.status == 'pendente']
                            if proximas:
                                st.info(f"📦 Ainda há {len(proximas)} entrega(s) restante(s)!")
                            else:
                                st.balloons()
                                st.success("🎉 Todas as entregas concluídas!")

                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Erro: {resultado.get('erro', 'Desconhecido')}")
                    except Exception as e:
                        session.rollback()
                        st.error(f"Erro: {str(e)}")

                st.markdown("---")

                # Opções de problema
                st.markdown("##### ⚠️ Problemas com a entrega?")
                col_prob1, col_prob2 = st.columns(2)

                with col_prob1:
                    if st.button("🚪 Cliente Ausente", use_container_width=True):
                        st.session_state.modal_ausente = True
                        st.rerun()

                with col_prob2:
                    if st.button("❌ Cliente Cancelou", use_container_width=True):
                        st.session_state.modal_rejeitar = True
                        st.rerun()

            # Modals
            if st.session_state.get('modal_rejeitar'):
                modal_rejeitar_pedido(entrega_atual, session)

            if st.session_state.get('modal_ausente'):
                modal_cliente_ausente(entrega_atual, session)

        # ==================== PRÓXIMAS ENTREGAS ====================
        proximas_entregas = [e for e in entregas if e.status == 'pendente']
        if proximas_entregas:
            st.markdown("---")
            st.markdown(f"### 📋 Próximas Entregas ({len(proximas_entregas)})")

            for i, entrega in enumerate(proximas_entregas, 1):
                posicao = i + 1 if entregas_em_rota else i
                with st.expander(f"#{posicao} - {entrega.pedido.cliente_nome} - {entrega.distancia_km or 0:.1f} km"):
                    st.markdown(f"**Comanda:** #{entrega.pedido.comanda}")
                    st.markdown(f"**Endereço:** {entrega.pedido.endereco_entrega}")
                    st.markdown(f"**Telefone:** {entrega.pedido.cliente_telefone or 'Não informado'}")
                    if entrega.pedido.observacoes:
                        st.markdown(f"**Obs:** {entrega.pedido.observacoes}")
    finally:
        session.close()

def modal_rejeitar_pedido(entrega, session):
    with st.form("form_rejeitar"):
        st.warning("⚠️ Cliente Cancelou/Recusou")
        st.markdown("Registre o motivo do cancelamento:")

        motivo = st.selectbox(
            "Motivo:",
            [
                "Cliente cancelou o pedido",
                "Cliente recusou receber",
                "Pedido errado",
                "Problema com pagamento",
                "Outro motivo"
            ]
        )

        obs = st.text_area("Observações adicionais", placeholder="Detalhes...")

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("❌ Confirmar Cancelamento", use_container_width=True):
                try:
                    entrega.status = 'cancelado'
                    entrega.motivo_cancelamento = f"{motivo}. {obs}" if obs else motivo
                    entrega.entregue_em = datetime.now()

                    # Atualizar pedido
                    entrega.pedido.status = 'cancelado'

                    # Atualizar motoboy - decrementar entregas pendentes
                    motoboy = session.query(Motoboy).filter(
                        Motoboy.id == entrega.motoboy_id
                    ).first()
                    if motoboy:
                        motoboy.entregas_pendentes = max(0, (motoboy.entregas_pendentes or 1) - 1)
                        if motoboy.entregas_pendentes == 0:
                            motoboy.em_rota = False

                    session.commit()

                    # Limpar estado
                    if f'estado_entrega_{entrega.id}' in st.session_state:
                        del st.session_state[f'estado_entrega_{entrega.id}']

                    st.warning("⚠️ Pedido cancelado e registrado!")
                    st.session_state.modal_rejeitar = False
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {str(e)}")

        with col2:
            if st.form_submit_button("🔙 Voltar", use_container_width=True):
                st.session_state.modal_rejeitar = False
                st.rerun()


def modal_cliente_ausente(entrega, session):
    with st.form("form_ausente"):
        st.warning("🚪 Cliente Ausente")
        st.markdown("O que aconteceu?")

        acao = st.radio(
            "Ação tomada:",
            [
                "Tentei ligar e não atendeu",
                "Toquei campainha/bati na porta",
                "Aguardei no local por mais de 5 minutos",
                "Vizinho informou que não está em casa"
            ]
        )

        obs = st.text_area("Observações adicionais")

        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("✅ Registrar Ausência", use_container_width=True):
                try:
                    motivo = f"Cliente ausente - {acao}. {obs}" if obs else f"Cliente ausente - {acao}"
                    entrega.status = 'cancelado'
                    entrega.motivo_cancelamento = motivo
                    entrega.entregue_em = datetime.now()

                    # Atualizar pedido para cliente_ausente
                    entrega.pedido.status = 'cliente_ausente'

                    # Atualizar motoboy
                    motoboy = session.query(Motoboy).filter(
                        Motoboy.id == entrega.motoboy_id
                    ).first()
                    if motoboy:
                        motoboy.entregas_pendentes = max(0, (motoboy.entregas_pendentes or 1) - 1)
                        if motoboy.entregas_pendentes == 0:
                            motoboy.em_rota = False

                    session.commit()

                    # Limpar estado
                    if f'estado_entrega_{entrega.id}' in st.session_state:
                        del st.session_state[f'estado_entrega_{entrega.id}']

                    st.warning("⚠️ Registrado como cliente ausente! O restaurante será notificado.")
                    st.session_state.modal_ausente = False
                    time.sleep(2)
                    st.rerun()
                except Exception as e:
                    session.rollback()
                    st.error(f"Erro: {str(e)}")

        with col2:
            if st.form_submit_button("🔙 Voltar", use_container_width=True):
                st.session_state.modal_ausente = False
                st.rerun()

# ==================== GANHOS ====================

def tela_ganhos():
    session = get_db_session()
    try:
        # Buscar motoboy para obter restaurante_id
        motoboy = session.query(Motoboy).filter(
            Motoboy.id == st.session_state.motoboy_id
        ).first()

        if not motoboy:
            st.error("Motoboy não encontrado")
            return

        # Verificar se restaurante permite ver saldo
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == motoboy.restaurante_id
        ).first()

        # Por padrão permite ver saldo se não houver config
        permitir_ver_saldo = config.permitir_ver_saldo_motoboy if config else True

        if not permitir_ver_saldo:
            st.warning("⚠️ O restaurante não habilitou a visualização de saldo para motoboys.")
            st.info("Entre em contato com o gerente para mais informações.")
            return

        # Buscar ganhos do dia usando a nova função
        ganhos_hoje = obter_ganhos_dia_motoboy(st.session_state.motoboy_id, session=session)

        # Estatísticas totais (usa valor_motoboy - o ganho real do motoboy)
        total_entregas = session.query(Entrega).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status == 'entregue'
        ).count()

        total_ganho = session.query(
            sa.func.coalesce(sa.func.sum(Entrega.valor_motoboy), 0)
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

        # Exibir ganhos do dia em destaque
        st.subheader("💰 Ganhos de Hoje")
        col_hoje1, col_hoje2, col_hoje3 = st.columns(3)

        with col_hoje1:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #00AA00, #008800);">
                <h2 style="color: white;">R$ {ganhos_hoje['total_ganhos']:.2f}</h2>
                <p style="color: #DDD;">Ganho Hoje</p>
            </div>
            """, unsafe_allow_html=True)

        with col_hoje2:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #0066CC, #004488);">
                <h2 style="color: white;">{ganhos_hoje['total_entregas']}</h2>
                <p style="color: #DDD;">Entregas Hoje</p>
            </div>
            """, unsafe_allow_html=True)

        with col_hoje3:
            st.markdown(f"""
            <div class="metric-card" style="background: linear-gradient(135deg, #FF6600, #CC4400);">
                <h2 style="color: white;">{ganhos_hoje['total_km']:.1f} km</h2>
                <p style="color: #DDD;">Percorridos Hoje</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Estatísticas totais
        st.subheader("📊 Estatísticas Gerais")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <h2>{total_entregas}</h2>
                <p>Total Entregas</p>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <h2>R$ {total_ganho:.2f}</h2>
                <p>Total Ganho</p>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <h2>{total_km:.1f} km</h2>
                <p>Total Percorrido</p>
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
                # Usar valor_motoboy (ganho do motoboy) ao invés de valor_entrega (taxa do cliente)
                valor_ganho = entrega.valor_motoboy or 0
                with st.expander(f"📦 Comanda {entrega.pedido.comanda} - R$ {valor_ganho:.2f}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Cliente:** {entrega.pedido.cliente_nome}")
                        st.markdown(f"**Distância:** {entrega.distancia_km or 0:.2f} km")

                    with col2:
                        st.markdown(f"**Ganho:** R$ {valor_ganho:.2f}")
                        if entrega.valor_base_motoboy and entrega.valor_extra_motoboy:
                            st.caption(f"Base: R$ {entrega.valor_base_motoboy:.2f} + Extra: R$ {entrega.valor_extra_motoboy:.2f}")
                        st.markdown(f"**Data:** {entrega.entregue_em.strftime('%d/%m %H:%M') if entrega.entregue_em else 'N/A'}")
    finally:
        session.close()

# ==================== PERFIL ====================

def tela_perfil():
    st.title("👤 Meu Perfil")

    session = get_db_session()
    try:
        # Buscar dados atualizados do motoboy
        motoboy = session.query(Motoboy).filter(
            Motoboy.id == st.session_state.motoboy_id
        ).options(joinedload(Motoboy.restaurante)).first()

        if not motoboy:
            st.error("Motoboy não encontrado")
            return

        st.markdown(f"### {motoboy.nome}")
        st.markdown(f"**Usuário:** {motoboy.usuario}")
        st.markdown(f"**Telefone:** {motoboy.telefone or 'Não informado'}")
        st.markdown(f"**Restaurante:** {motoboy.restaurante.nome_fantasia}")

        st.markdown("---")

        # Toggle de disponibilidade
        st.markdown("### 🟢 Status de Disponibilidade")

        col_status1, col_status2 = st.columns(2)

        with col_status1:
            if motoboy.disponivel:
                st.success("✅ ONLINE - Disponível para entregas")
                if st.button("⏸️ Ficar Offline", use_container_width=True, type="secondary"):
                    resultado = marcar_motoboy_disponivel(motoboy.id, False, session=session)
                    if resultado['sucesso']:
                        st.warning("Você está offline agora")
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("⏸️ OFFLINE - Não recebendo entregas")
                if st.button("✅ Ficar Online", use_container_width=True, type="primary"):
                    resultado = marcar_motoboy_disponivel(motoboy.id, True, session=session)
                    if resultado['sucesso']:
                        st.success("Você está online agora!")
                        time.sleep(1)
                        st.rerun()

        with col_status2:
            if motoboy.em_rota:
                st.info(f"🏍️ Em Rota - {motoboy.entregas_pendentes or 0} entrega(s) pendente(s)")
            else:
                st.info("📍 Sem rota ativa")

        st.markdown("---")

        # Estatísticas
        st.markdown("### 📊 Estatísticas")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Entregas", motoboy.total_entregas or 0)
        with col2:
            st.metric("Total Ganho", f"R$ {motoboy.total_ganhos or 0:.2f}")
        with col3:
            st.metric("Total KM", f"{motoboy.total_km or 0:.1f}")

        # Estatísticas do dia
        stats = obter_estatisticas_motoboy(motoboy.id, session)
        if stats:
            st.markdown("#### Hoje")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Entregas Hoje", stats['entregas_hoje'])
            with col2:
                st.metric("Ganho Hoje", f"R$ {stats['ganhos_hoje']:.2f}")
            with col3:
                st.metric("KM Hoje", f"{stats['km_hoje']:.1f}")

        st.markdown("---")

        # Posição na hierarquia
        st.markdown(f"**Posição na fila de entregas:** #{motoboy.ordem_hierarquia or 0}")
        st.caption("Quanto menor o número, mais cedo você receberá a próxima rota.")

        st.markdown("---")

        if st.button("🚪 Sair", use_container_width=True, type="primary"):
            # Marcar como offline ao sair
            marcar_motoboy_disponivel(motoboy.id, False, session=session)
            fazer_logout()
            st.rerun()

    finally:
        session.close()

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