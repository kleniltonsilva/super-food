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
from sqlalchemy import func
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

    .gps-status {
        padding: 5px 10px;
        border-radius: 5px;
        font-size: 12px;
        display: inline-block;
    }

    .gps-active {
        background-color: #00AA00;
        color: white;
    }

    .gps-inactive {
        background-color: #FF6600;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ==================== GPS EM TEMPO REAL ====================

def injetar_gps_tracker(motoboy_id: int, restaurante_id: int):
    """
    Injeta JavaScript para rastreamento GPS em tempo real.

    O script:
    1. Solicita permissão de geolocalização ao usuário
    2. Solicita permissão de notificações
    3. Obtém posição a cada 10 segundos
    4. Envia para a API /api/gps/update
    5. Atualiza indicador visual de status
    """
    # URL base da API (mesmo servidor, porta 8000)
    api_base = "http://localhost:8000"

    gps_script = f"""
    <div id="gps-status-container" style="
        position: fixed;
        bottom: 80px;
        right: 10px;
        z-index: 9999;
        padding: 8px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: bold;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 6px;
        background-color: #666;
        color: white;
        transition: all 0.3s ease;
        cursor: pointer;
    " onclick="window.requestGPSPermission && window.requestGPSPermission()">
        <span id="gps-icon">📍</span>
        <span id="gps-text">GPS...</span>
    </div>

    <script>
    (function() {{
        const MOTOBOY_ID = {motoboy_id};
        const RESTAURANTE_ID = {restaurante_id};
        const API_URL = '{api_base}/api/gps/update';
        const UPDATE_INTERVAL = 10000; // 10 segundos

        let watchId = null;
        let lastPosition = null;
        let isTracking = false;
        let permissionRequested = false;

        const statusContainer = document.getElementById('gps-status-container');
        const statusIcon = document.getElementById('gps-icon');
        const statusText = document.getElementById('gps-text');

        // Solicitar permissão de notificação no início
        async function requestNotificationPermission() {{
            if ('Notification' in window && Notification.permission === 'default') {{
                try {{
                    await Notification.requestPermission();
                }} catch (e) {{
                    console.log('Notificações não suportadas');
                }}
            }}
        }}

        function updateStatus(status, message) {{
            if (!statusContainer) return;

            switch(status) {{
                case 'active':
                    statusContainer.style.backgroundColor = '#00AA00';
                    statusIcon.textContent = '📍';
                    statusText.textContent = message || 'GPS Ativo';
                    break;
                case 'sending':
                    statusContainer.style.backgroundColor = '#0066CC';
                    statusIcon.textContent = '📡';
                    statusText.textContent = 'Enviando...';
                    break;
                case 'error':
                    statusContainer.style.backgroundColor = '#CC0000';
                    statusIcon.textContent = '⚠️';
                    statusText.textContent = message || 'Erro GPS';
                    break;
                case 'permission':
                    statusContainer.style.backgroundColor = '#FF6600';
                    statusIcon.textContent = '🔒';
                    statusText.textContent = message || 'Clique para permitir GPS';
                    break;
                default:
                    statusContainer.style.backgroundColor = '#666';
                    statusIcon.textContent = '📍';
                    statusText.textContent = message || 'GPS...';
            }}
        }}

        async function sendGPSUpdate(position) {{
            if (!position) return;

            updateStatus('sending');

            const data = {{
                motoboy_id: MOTOBOY_ID,
                restaurante_id: RESTAURANTE_ID,
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                velocidade: position.coords.speed || 0,
                precisao: position.coords.accuracy,
                heading: position.coords.heading
            }};

            try {{
                const response = await fetch(API_URL, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(data)
                }});

                if (response.ok) {{
                    const result = await response.json();
                    if (result.sucesso) {{
                        const speed = (position.coords.speed || 0) * 3.6; // m/s para km/h
                        updateStatus('active', speed > 1 ? speed.toFixed(0) + ' km/h' : 'GPS Ativo');
                    }} else {{
                        updateStatus('error', 'Offline');
                    }}
                }} else {{
                    updateStatus('error', 'Erro API');
                }}
            }} catch (error) {{
                console.error('Erro GPS:', error);
                updateStatus('error', 'Sem conexão');
            }}
        }}

        function onPositionUpdate(position) {{
            lastPosition = position;
            sendGPSUpdate(position);
        }}

        function onPositionError(error) {{
            console.error('Erro de geolocalização:', error);
            switch(error.code) {{
                case error.PERMISSION_DENIED:
                    updateStatus('permission', 'Clique para permitir');
                    break;
                case error.POSITION_UNAVAILABLE:
                    updateStatus('error', 'Indisponível');
                    break;
                case error.TIMEOUT:
                    updateStatus('error', 'Timeout');
                    break;
                default:
                    updateStatus('error', 'Erro GPS');
            }}
        }}

        // Função para solicitar permissão de GPS explicitamente
        window.requestGPSPermission = function() {{
            if (!navigator.geolocation) {{
                alert('Seu navegador não suporta GPS. Use um navegador moderno como Chrome ou Firefox.');
                return;
            }}

            updateStatus('default', 'Solicitando...');

            navigator.geolocation.getCurrentPosition(
                function(position) {{
                    onPositionUpdate(position);
                    startTracking();
                }},
                function(error) {{
                    if (error.code === error.PERMISSION_DENIED) {{
                        alert('Para receber entregas, você precisa permitir acesso à localização.\\n\\n' +
                              'Vá em Configurações do navegador > Permissões > Localização e permita para este site.');
                    }}
                    onPositionError(error);
                }},
                {{
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0
                }}
            );
        }};

        function startTracking() {{
            if (!navigator.geolocation) {{
                updateStatus('error', 'Não suportado');
                return;
            }}

            if (isTracking) return;
            isTracking = true;

            const options = {{
                enableHighAccuracy: true,
                timeout: 15000,
                maximumAge: 5000
            }};

            // Watch contínuo com alta precisão
            watchId = navigator.geolocation.watchPosition(
                onPositionUpdate,
                onPositionError,
                options
            );

            // Também enviar a cada 10 segundos (backup)
            setInterval(() => {{
                if (lastPosition) {{
                    sendGPSUpdate(lastPosition);
                }} else {{
                    navigator.geolocation.getCurrentPosition(
                        onPositionUpdate,
                        onPositionError,
                        options
                    );
                }}
            }}, UPDATE_INTERVAL);

            updateStatus('active', 'Iniciando...');
        }}

        // Verificar permissão atual de geolocalização
        async function checkAndRequestPermission() {{
            // Solicitar permissão de notificação
            await requestNotificationPermission();

            if (navigator.permissions && navigator.permissions.query) {{
                try {{
                    const result = await navigator.permissions.query({{ name: 'geolocation' }});

                    if (result.state === 'granted') {{
                        // Já tem permissão, iniciar rastreamento
                        startTracking();
                        navigator.geolocation.getCurrentPosition(onPositionUpdate, onPositionError, {{
                            enableHighAccuracy: true, timeout: 15000, maximumAge: 5000
                        }});
                    }} else if (result.state === 'prompt') {{
                        // Precisa solicitar - mostrar indicador clicável
                        updateStatus('permission', 'Clique para permitir');
                        // Tentar solicitar automaticamente
                        if (!permissionRequested) {{
                            permissionRequested = true;
                            navigator.geolocation.getCurrentPosition(
                                function(pos) {{
                                    onPositionUpdate(pos);
                                    startTracking();
                                }},
                                onPositionError,
                                {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }}
                            );
                        }}
                    }} else {{
                        // Negado
                        updateStatus('permission', 'GPS Negado');
                    }}

                    // Monitorar mudanças de permissão
                    result.addEventListener('change', function() {{
                        if (result.state === 'granted' && !isTracking) {{
                            startTracking();
                            navigator.geolocation.getCurrentPosition(onPositionUpdate, onPositionError);
                        }}
                    }});
                }} catch (e) {{
                    // Fallback para navegadores que não suportam permissions API
                    navigator.geolocation.getCurrentPosition(
                        function(pos) {{ onPositionUpdate(pos); startTracking(); }},
                        onPositionError,
                        {{ enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }}
                    );
                }}
            }} else {{
                // Navegador não suporta permissions API - tentar diretamente
                navigator.geolocation.getCurrentPosition(
                    function(pos) {{ onPositionUpdate(pos); startTracking(); }},
                    onPositionError,
                    {{ enableHighAccuracy: true, timeout: 15000, maximumAge: 5000 }}
                );
            }}
        }}

        // Iniciar verificação de permissão
        if (document.readyState === 'complete') {{
            checkAndRequestPermission();
        }} else {{
            window.addEventListener('load', checkAndRequestPermission);
        }}

        // Backup: também tentar após 1 segundo
        setTimeout(checkAndRequestPermission, 1000);
    }})();
    </script>
    """

    st.markdown(gps_script, unsafe_allow_html=True)


def salvar_gps_direto(motoboy_id: int, restaurante_id: int, latitude: float, longitude: float, velocidade: float = 0):
    """
    Salva posição GPS diretamente no banco (fallback se API não disponível).
    """
    session = get_db_session()
    try:
        # Criar registro GPS
        gps_record = GPSMotoboy(
            motoboy_id=motoboy_id,
            restaurante_id=restaurante_id,
            latitude=latitude,
            longitude=longitude,
            velocidade=velocidade,
            timestamp=datetime.now()
        )
        session.add(gps_record)

        # Atualizar motoboy
        motoboy = session.query(Motoboy).filter(Motoboy.id == motoboy_id).first()
        if motoboy:
            motoboy.latitude_atual = latitude
            motoboy.longitude_atual = longitude
            motoboy.ultima_atualizacao_gps = datetime.now()

        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()


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

# ==================== ENTREGAS ====================

def tocar_som_notificacao():
    """
    Injeta JavaScript para tocar som de notificação.
    Usa Web Audio API com resume automático para funcionar em PWA.
    Também tenta enviar notificação do sistema se permitido.
    """
    st.markdown("""
    <script>
    (function() {
        // Evitar tocar múltiplas vezes em reruns rápidos
        if (window.lastNotificationTime && (Date.now() - window.lastNotificationTime) < 2000) {
            return;
        }
        window.lastNotificationTime = Date.now();

        // Criar contexto de áudio
        let audioContext = window.audioContextGlobal;
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
            window.audioContextGlobal = audioContext;
        }

        // Resumir contexto se necessário (política de autoplay)
        if (audioContext.state === 'suspended') {
            audioContext.resume();
        }

        // Criar oscilador para som de notificação
        function playNotificationSound() {
            try {
                // Resumir novamente para garantir
                if (audioContext.state === 'suspended') {
                    audioContext.resume();
                }

                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();

                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);

                // Tom mais alto e audível
                oscillator.frequency.value = 880; // La4 (mais audível)
                oscillator.type = 'sine';

                // Volume mais alto
                gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.4);

                oscillator.start(audioContext.currentTime);
                oscillator.stop(audioContext.currentTime + 0.4);
            } catch (e) {
                console.error('Erro ao tocar som:', e);
            }
        }

        // Padrão de notificação: 3 toques rápidos
        playNotificationSound();
        setTimeout(playNotificationSound, 400);
        setTimeout(playNotificationSound, 800);

        // Tentar enviar notificação do sistema também
        if ('Notification' in window && Notification.permission === 'granted') {
            try {
                new Notification('Super Food - Nova Entrega!', {
                    body: 'Você recebeu uma nova entrega. Confira o app.',
                    icon: '/logo192.png',
                    tag: 'nova-entrega',
                    requireInteraction: true,
                    vibrate: [200, 100, 200, 100, 200]
                });
            } catch (e) {
                console.log('Notificação não suportada:', e);
            }
        }

        // Vibrar dispositivo se disponível
        if ('vibrate' in navigator) {
            navigator.vibrate([200, 100, 200, 100, 300]);
        }
    })();
    </script>
    """, unsafe_allow_html=True)


def tela_entregas():
    """Tela de entregas COM ORDEM OTIMIZADA e sistema sequencial"""
    st.title("📦 Suas Entregas")

    # Inicializar estados de forma segura para evitar erro removeChild
    if 'entregas_container_key' not in st.session_state:
        st.session_state.entregas_container_key = 0

    # Container principal com key estável para evitar erro de DOM
    main_container = st.container()

    session = get_db_session()
    try:
        # Buscar todas as entregas pendentes ou em rota
        entregas = session.query(Entrega).join(Pedido).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(['pendente', 'em_rota'])
        ).order_by(Entrega.posicao_rota_otimizada.asc()).all()

        # Contar entregas já finalizadas hoje para calcular posição na rota
        hoje = datetime.now().date()
        entregas_finalizadas_hoje = session.query(Entrega).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(['entregue', 'cliente_ausente', 'cancelado_cliente']),
            func.date(Entrega.entregue_em) == hoje
        ).count()

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
        # Para entregas isoladas (1 pedido), mostrar 1 de 1
        # Para rotas múltiplas, mostrar posição correta na rota atual
        if entregas_em_rota:
            entrega_atual = entregas_em_rota[0]
            # Calcular posição correta: finalizadas + 1, total = finalizadas + ativas
            pedido_atual = entregas_finalizadas_hoje + 1
            total_rota = entregas_finalizadas_hoje + total_entregas
            restantes = total_entregas - 1
            st.markdown(f"""
            <div class="status-ocupado">
                🏍️ EM ENTREGA - Pedido {pedido_atual} de {total_rota} ({restantes} restante{'s' if restantes != 1 else ''})
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

            # Botão grande para iniciar - key estável baseada no motoboy
            if st.button("🚀 INICIAR ENTREGAS", use_container_width=True, type="primary", key=f"btn_iniciar_{st.session_state.motoboy_id}"):
                try:
                    # Inicia a primeira entrega da fila
                    primeira = entregas_pendentes[0]
                    primeira.status = 'em_rota'
                    primeira.atribuido_em = datetime.now()
                    primeira.delivery_started_at = datetime.now()
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
            valor_cobrar = entrega_atual.pedido.valor_total or 0
            distancia_entrega = entrega_atual.distancia_km or entrega_atual.pedido.distancia_restaurante_km or 0

            # Calcular ganho estimado do motoboy se ainda não definido
            valor_ganho_motoboy = entrega_atual.valor_motoboy
            if not valor_ganho_motoboy:
                # Buscar config do restaurante para calcular
                config = session.query(ConfigRestaurante).filter(
                    ConfigRestaurante.restaurante_id == st.session_state.restaurante_id
                ).first()
                if config:
                    base = config.valor_base_motoboy or 5.0
                    km_extra = config.valor_km_extra_motoboy or 1.0
                    dist_base = config.distancia_base_km or 3.0
                    km_excedente = max(0, distancia_entrega - dist_base)
                    valor_ganho_motoboy = base + (km_excedente * km_extra)
                else:
                    valor_ganho_motoboy = entrega_atual.valor_entrega or 5.0

            st.markdown(f"""
            <div class="pedido-card" style="border-color: #00AA00; border-width: 3px;">
                <h3>📦 Comanda #{entrega_atual.pedido.comanda}</h3>
                <p><strong>👤 Cliente:</strong> {entrega_atual.pedido.cliente_nome}</p>
                <p><strong>📞 Telefone:</strong> {entrega_atual.pedido.cliente_telefone or 'Não informado'}</p>
                <p><strong>📍 Endereço:</strong> {entrega_atual.pedido.endereco_entrega}</p>
                <p><strong>📏 Distância:</strong> {distancia_entrega:.1f} km</p>
                <p style="font-size: 1.3em; color: #00AA00;"><strong>💵 VALOR A COBRAR DO CLIENTE: R$ {valor_cobrar:.2f}</strong></p>
                <p><strong>💰 Seu Ganho:</strong> R$ {valor_ganho_motoboy:.2f}</p>
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
                # Botão: Cheguei ao Destino - key estável
                if st.button("📍 CHEGUEI AO DESTINO", use_container_width=True, type="primary", key=f"cheguei_{entrega_atual.id}"):
                    st.session_state[f'estado_entrega_{entrega_atual.id}'] = 'no_destino'
                    st.rerun()

                # Ligar para cliente
                telefone = entrega_atual.pedido.cliente_telefone
                if telefone:
                    telefone_limpo = ''.join(filter(str.isdigit, telefone))
                    st.markdown(f"[📞 Ligar para Cliente](tel:{telefone_limpo})")

            elif estado_entrega == 'no_destino':
                st.success("📍 Você chegou ao destino!")
                valor_total = entrega_atual.pedido.valor_total or 0

                st.markdown(f"### 💵 Receber Pagamento: R$ {valor_total:.2f}")

                # Estado do pagamento
                pagamento_state = st.session_state.get(f'pagamento_{entrega_atual.id}', None)

                if not pagamento_state:
                    st.markdown("**Selecione a forma de pagamento:**")
                    col_pag1, col_pag2, col_pag3 = st.columns(3)

                    with col_pag1:
                        if st.button("💵 Dinheiro", use_container_width=True, key=f"pag_din_{entrega_atual.id}"):
                            st.session_state[f'pagamento_{entrega_atual.id}'] = 'dinheiro'
                            st.rerun()
                    with col_pag2:
                        if st.button("💳 Cartão/Pix", use_container_width=True, key=f"pag_cart_{entrega_atual.id}"):
                            st.session_state[f'pagamento_{entrega_atual.id}'] = 'cartao'
                            st.rerun()
                    with col_pag3:
                        if st.button("🔀 Misto", use_container_width=True, key=f"pag_misto_{entrega_atual.id}"):
                            st.session_state[f'pagamento_{entrega_atual.id}'] = 'misto'
                            st.rerun()

                elif pagamento_state == 'dinheiro':
                    st.info("💵 Pagamento em Dinheiro")
                    valor_recebido = st.number_input("Valor recebido do cliente (R$):", min_value=valor_total, value=valor_total, step=5.0, key=f"val_rec_{entrega_atual.id}")
                    troco = valor_recebido - valor_total
                    if troco > 0:
                        st.warning(f"💰 **TROCO A DAR: R$ {troco:.2f}**")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirmar", use_container_width=True, type="primary", key=f"conf_din_{entrega_atual.id}"):
                            st.session_state[f'pagamento_confirmado_{entrega_atual.id}'] = {
                                'forma': 'Dinheiro', 'valor_dinheiro': valor_total, 'valor_cartao': 0
                            }
                            st.rerun()
                    with col2:
                        if st.button("↩️ Voltar", use_container_width=True, key=f"volt_din_{entrega_atual.id}"):
                            del st.session_state[f'pagamento_{entrega_atual.id}']
                            st.rerun()

                elif pagamento_state == 'cartao':
                    st.info("💳 Pagamento em Cartão/Pix")
                    st.success(f"Valor: R$ {valor_total:.2f}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Pagamento Recebido", use_container_width=True, type="primary", key=f"conf_cart_{entrega_atual.id}"):
                            st.session_state[f'pagamento_confirmado_{entrega_atual.id}'] = {
                                'forma': 'Cartão/Pix', 'valor_dinheiro': 0, 'valor_cartao': valor_total
                            }
                            st.rerun()
                    with col2:
                        if st.button("↩️ Voltar", use_container_width=True, key=f"volt_cart_{entrega_atual.id}"):
                            del st.session_state[f'pagamento_{entrega_atual.id}']
                            st.rerun()

                elif pagamento_state == 'misto':
                    st.info("🔀 Pagamento Misto (Dinheiro + Cartão)")
                    valor_cartao = st.number_input("Valor em Cartão/Pix (R$):", min_value=0.0, max_value=valor_total, value=0.0, step=5.0, key=f"val_cart_{entrega_atual.id}")
                    valor_dinheiro = valor_total - valor_cartao
                    st.markdown(f"**💵 Restante em Dinheiro: R$ {valor_dinheiro:.2f}**")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Confirmar", use_container_width=True, type="primary", key=f"conf_misto_{entrega_atual.id}"):
                            st.session_state[f'pagamento_confirmado_{entrega_atual.id}'] = {
                                'forma': 'Misto', 'valor_dinheiro': valor_dinheiro, 'valor_cartao': valor_cartao
                            }
                            st.rerun()
                    with col2:
                        if st.button("↩️ Voltar", use_container_width=True, key=f"volt_misto_{entrega_atual.id}"):
                            del st.session_state[f'pagamento_{entrega_atual.id}']
                            st.rerun()

                # Após confirmação do pagamento, mostrar botão de finalizar
                pagamento_confirmado = st.session_state.get(f'pagamento_confirmado_{entrega_atual.id}')
                if pagamento_confirmado:
                    st.success(f"✅ Pagamento: {pagamento_confirmado['forma']}")
                    if pagamento_confirmado['valor_dinheiro'] > 0:
                        st.markdown(f"💵 Dinheiro: R$ {pagamento_confirmado['valor_dinheiro']:.2f}")
                    if pagamento_confirmado['valor_cartao'] > 0:
                        st.markdown(f"💳 Cartão/Pix: R$ {pagamento_confirmado['valor_cartao']:.2f}")

                    st.markdown("---")
                    if st.button("✅ FINALIZAR ENTREGA", use_container_width=True, type="primary", key=f"concluir_{entrega_atual.id}"):
                        try:
                            distancia_km = entrega_atual.distancia_km or entrega_atual.pedido.distancia_restaurante_km or 0

                            # Salvar forma de pagamento real no pedido
                            entrega_atual.pedido.forma_pagamento_real = pagamento_confirmado['forma']
                            entrega_atual.pedido.valor_pago_dinheiro = pagamento_confirmado['valor_dinheiro']
                            entrega_atual.pedido.valor_pago_cartao = pagamento_confirmado['valor_cartao']
                            session.commit()

                            resultado = finalizar_entrega_motoboy(
                                entrega_atual.id,
                                distancia_km if distancia_km else None,
                                session
                            )

                            if resultado['sucesso']:
                                valor_ganho = resultado.get('valor_ganho', 0)
                                st.success(f"✅ Entrega concluída! Ganho: R$ {valor_ganho:.2f}")

                                # Limpar estados
                                for key in [f'estado_entrega_{entrega_atual.id}', f'pagamento_{entrega_atual.id}', f'pagamento_confirmado_{entrega_atual.id}']:
                                    if key in st.session_state:
                                        del st.session_state[key]

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
                    if st.button("🚪 Cliente Ausente", use_container_width=True, key=f"ausente_{entrega_atual.id}"):
                        st.session_state.modal_ausente = True
                        st.rerun()

                with col_prob2:
                    if st.button("❌ Cliente Cancelou", use_container_width=True, key=f"cancelou_{entrega_atual.id}"):
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
    # Key estável baseada no ID do motoboy para evitar erro removeChild
    form_key = f"form_rejeitar_{st.session_state.motoboy_id}"
    with st.form(form_key):
        st.warning("⚠️ Cliente Cancelou/Recusou")
        st.markdown("Registre o motivo do cancelamento:")
        st.info("💰 Você receberá o valor da entrega normalmente, pois foi até o local.")

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
                    observacao_completa = f"{motivo}. {obs}" if obs else motivo
                    distancia_km = entrega.distancia_km or entrega.pedido.distancia_restaurante_km or 0

                    # Usar função atualizada que registra ganho do motoboy
                    resultado = finalizar_entrega_motoboy(
                        entrega.id,
                        distancia_km if distancia_km else None,
                        session,
                        motivo_finalizacao='cancelado_cliente',
                        observacao=observacao_completa
                    )

                    # Limpar estado
                    if f'estado_entrega_{entrega.id}' in st.session_state:
                        del st.session_state[f'estado_entrega_{entrega.id}']

                    if resultado['sucesso']:
                        valor_ganho = resultado.get('valor_ganho', 0)
                        st.success(f"✅ Registrado! Você ganhou R$ {valor_ganho:.2f}")
                    else:
                        st.warning(f"⚠️ Pedido cancelado. {resultado.get('erro', '')}")

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
    # Key estável baseada no ID do motoboy para evitar erro removeChild
    form_key = f"form_ausente_{st.session_state.motoboy_id}"
    with st.form(form_key):
        st.warning("🚪 Cliente Ausente")
        st.markdown("O que aconteceu?")
        st.info("💰 Você receberá o valor da entrega normalmente, pois foi até o local.")

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
                    observacao_completa = f"Cliente ausente - {acao}. {obs}" if obs else f"Cliente ausente - {acao}"
                    distancia_km = entrega.distancia_km or entrega.pedido.distancia_restaurante_km or 0

                    # Usar função atualizada que registra ganho do motoboy
                    resultado = finalizar_entrega_motoboy(
                        entrega.id,
                        distancia_km if distancia_km else None,
                        session,
                        motivo_finalizacao='cliente_ausente',
                        observacao=observacao_completa
                    )

                    # Limpar estado
                    if f'estado_entrega_{entrega.id}' in st.session_state:
                        del st.session_state[f'estado_entrega_{entrega.id}']

                    if resultado['sucesso']:
                        valor_ganho = resultado.get('valor_ganho', 0)
                        st.success(f"✅ Registrado! Você ganhou R$ {valor_ganho:.2f}")
                        st.info("O restaurante será notificado.")
                    else:
                        st.warning(f"⚠️ Registrado como ausente. {resultado.get('erro', '')}")

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

        # Status que geram pagamento ao motoboy (inclui cancelamentos onde ele foi até o local)
        status_pagos = ['entregue', 'cliente_ausente', 'cancelado_cliente']

        # Estatísticas totais (usa valor_motoboy - o ganho real do motoboy)
        total_entregas = session.query(Entrega).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(status_pagos)
        ).count()

        total_ganho = session.query(
            sa.func.coalesce(sa.func.sum(Entrega.valor_motoboy), 0)
        ).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(status_pagos)
        ).scalar()

        total_km = session.query(
            sa.func.coalesce(sa.func.sum(Entrega.distancia_km), 0)
        ).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(status_pagos)
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

        # Incluir todos os status que geram pagamento
        historico = session.query(Entrega).join(Pedido).filter(
            Entrega.motoboy_id == st.session_state.motoboy_id,
            Entrega.status.in_(status_pagos)
        ).order_by(Entrega.entregue_em.desc()).limit(20).all()

        if not historico:
            st.info("Nenhuma entrega realizada ainda.")
        else:
            for entrega in historico:
                # Usar valor_motoboy (ganho do motoboy) ao invés de valor_entrega (taxa do cliente)
                valor_ganho = entrega.valor_motoboy or 0

                # Indicador de status especial
                status_icon = "📦"
                status_texto = ""
                if entrega.status == 'cliente_ausente':
                    status_icon = "🚪"
                    status_texto = " (Ausente)"
                elif entrega.status == 'cancelado_cliente':
                    status_icon = "❌"
                    status_texto = " (Cancelado)"

                with st.expander(f"{status_icon} Comanda {entrega.pedido.comanda} - R$ {valor_ganho:.2f}{status_texto}"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Cliente:** {entrega.pedido.cliente_nome}")
                        st.markdown(f"**Distância:** {entrega.distancia_km or 0:.2f} km")
                        if entrega.status != 'entregue':
                            st.caption(f"Status: {entrega.status.replace('_', ' ').title()}")

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

        # Alterar Senha
        st.markdown("### 🔐 Alterar Senha")

        with st.expander("Clique para alterar sua senha"):
            senha_atual = st.text_input("Senha Atual", type="password", key="senha_atual")
            nova_senha = st.text_input("Nova Senha", type="password", key="nova_senha")
            confirmar_senha = st.text_input("Confirmar Nova Senha", type="password", key="confirmar_senha")

            if st.button("Salvar Nova Senha", type="primary"):
                if not senha_atual or not nova_senha or not confirmar_senha:
                    st.error("Preencha todos os campos")
                elif not motoboy.verificar_senha(senha_atual):
                    st.error("Senha atual incorreta")
                elif nova_senha != confirmar_senha:
                    st.error("As senhas não conferem")
                elif len(nova_senha) < 4:
                    st.error("A nova senha deve ter no mínimo 4 caracteres")
                else:
                    motoboy.set_senha(nova_senha)
                    session.commit()
                    st.success("Senha alterada com sucesso!")
                    time.sleep(1)
                    st.rerun()

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

    # Verificar se motoboy pode ver ganhos
    session = get_db_session()
    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == st.session_state.restaurante_id
        ).first()
        permitir_ver_saldo = config.permitir_ver_saldo_motoboy if config else True
    finally:
        session.close()

    # Menu simplificado com 3 opções (removido Mapa)
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📦\nEntregas", use_container_width=True, key="menu_entregas"):
            st.session_state.tela_atual = "entregas"
            st.rerun()

    with col2:
        if permitir_ver_saldo:
            if st.button("💰\nGanhos", use_container_width=True, key="menu_ganhos"):
                st.session_state.tela_atual = "ganhos"
                st.rerun()
        else:
            # Botão desabilitado com aparência apagada
            st.markdown("""
            <style>
            .btn-disabled {
                background-color: #ccc !important;
                color: #888 !important;
                cursor: not-allowed !important;
                opacity: 0.6;
            }
            </style>
            """, unsafe_allow_html=True)
            if st.button("💰\nGanhos", use_container_width=True, key="menu_ganhos", disabled=True):
                pass
            st.caption("🔒 Desabilitado")

    with col3:
        if st.button("👤\nPerfil", use_container_width=True, key="menu_perfil"):
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
        # Injetar GPS Tracker quando motoboy está online
        # O JavaScript roda em background e envia localização a cada 10 segundos
        motoboy_dados = st.session_state.get('motoboy_dados')
        if motoboy_dados and motoboy_dados.get('disponivel', False):
            injetar_gps_tracker(
                st.session_state.motoboy_id,
                st.session_state.restaurante_id
            )

        tela = st.session_state.tela_atual

        # Roteamento de telas (removido tela_mapa)
        if tela == "entregas":
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