"""
wa_sales_bot.py - Bot de vendas WhatsApp via Evolution API (outbound) + Grok IA
Estratégia dual-number:
  - Outbound (prospecção): Evolution API → +55 45 9971-3063
  - Inbound (receber): +55 11 97176-5565 (link nos emails para "Fale Conosco")

v2.1 — Áudio STT/TTS + autonomia:
  - STT: transcrição de áudios via Groq Whisper (grátis)
  - TTS: envio autônomo de áudio via xAI Grok / Fish Audio S2-Pro + Evolution API
  - Voz feminina — bot se chama Ana
  - Decisão inteligente de quando enviar áudio vs texto
  - Envio de áudio via Evolution API (sendMedia)
  - Toggles on/off via configurações

v2.0 — Reestruturação completa:
  - Prompts humanizados (gírias, abreviações, tom oral)
  - Intent scoring contextual (não mais keywords binárias)
  - Handoff gradual (imediato / quente / estratégico)
  - Delay variável para parecer humano
  - Contexto resumido do lead no prompt
"""
import os
import re
import json
import hmac
import hashlib
import logging
import tempfile
import base64
import random
import time as _time
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

from crm.database import (
    obter_lead, obter_configuracao, criar_conversa_wa,
    registrar_msg_wa, obter_conversa_wa, obter_conversa_wa_por_lead,
    atualizar_conversa_wa, opt_out_lead, registrar_interacao,
)
from crm.scoring import personalizar_abordagem

log = logging.getLogger("wa_bot")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[WA-BOT] %(message)s"))
    log.addHandler(_h)

# Decision log — registro estruturado de decisões do bot (Fix #7)
decision_log = logging.getLogger("wa_decision")
decision_log.setLevel(logging.DEBUG)
if not decision_log.handlers:
    try:
        _dh = logging.FileHandler("/tmp/wa_decisions.log", encoding="utf-8")
        _dh.setFormatter(logging.Formatter("%(asctime)s | %(message)s"))
        decision_log.addHandler(_dh)
    except Exception:
        pass  # fallback: sem arquivo de decisões

# Evolution API config (outbound)
_EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "https://derekh-evolution.fly.dev")
_EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "derekh-whatsapp")
_EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")

# Número inbound (para incluir nos emails como "Fale Conosco")
WHATSAPP_INBOUND_NUMBER = os.environ.get("WHATSAPP_INBOUND_NUMBER", "5511971765565")

# Números excluídos da prospecção (dono, bots, números internos)
_NUMEROS_EXCLUIDOS = {
    "351933358929",   # Klenilton (dono) — Portugal
    "554599713063",   # Bot outbound (derekh-whatsapp)
    "5511971765565",  # Bot inbound (derekh-inbound)
    "16465894168",    # Número teste
}

# Fallback: WhatsApp Cloud API (Meta) — mantido para compatibilidade
_GRAPH_API = "https://graph.facebook.com/v21.0"


# ============================================================
# HELPERS
# ============================================================

def _get_evolution_config() -> tuple:
    """Retorna (api_url, instance, api_key) da Evolution API."""
    url = obter_configuracao("evolution_api_url") or _EVOLUTION_API_URL
    instance = obter_configuracao("evolution_instance") or _EVOLUTION_INSTANCE
    key = obter_configuracao("evolution_api_key") or _EVOLUTION_API_KEY
    return url, instance, key


def _enviar_presenca(numero: str, presenca: str = "composing",
                     delay_ms: int = 3000, instance_override: str = "") -> None:
    """Envia indicador de presença para conversa (composing/recording).
    Faz o contato ver 'digitando...' ou 'gravando áudio...' antes da resposta."""
    url, inst, key = _get_evolution_config()
    if instance_override:
        inst = instance_override
    if not url or not key:
        return
    try:
        httpx.post(
            f"{url}/chat/sendPresence/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"number": numero, "delay": delay_ms, "presence": presenca},
            timeout=5,
        )
    except Exception:
        pass  # presença é cosmética, não bloquear envio


def _get_wa_config() -> tuple:
    """Retorna (phone_number_id, access_token) do WhatsApp Cloud API (fallback)."""
    phone_id = obter_configuracao("wa_phone_id") or os.environ.get("WHATSAPP_PHONE_ID", "")
    token = obter_configuracao("wa_access_token") or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    return phone_id, token


def get_inbound_wa_link(texto: str = "Olá! Gostaria de saber mais sobre a Derekh Food") -> str:
    """Retorna link wa.me para o número inbound (Fale Conosco)."""
    import urllib.parse
    return f"https://wa.me/{WHATSAPP_INBOUND_NUMBER}?text={urllib.parse.quote(texto)}"


def _get_xai_key() -> str:
    """Retorna API key do xAI/Grok."""
    return obter_configuracao("xai_api_key") or os.environ.get("XAI_API_KEY", "")


def _limpar_telefone(tel: str) -> str:
    """Remove caracteres não numéricos."""
    if not tel:
        return ""
    return re.sub(r"\D", "", tel)


def _formatar_numero_wa(telefone: str) -> str:
    """Formata telefone para formato WA internacional.
    Se já tem código de país (>11 dígitos), usa como está.
    Se parece brasileiro (10-11 dígitos sem código), adiciona 55."""
    num = _limpar_telefone(telefone)
    if not num:
        return ""
    # Já tem código de país (ex: 351xxx, 1xxx, 55xxx) — número longo
    if len(num) > 11:
        return num
    # Número brasileiro sem código de país (10-11 dígitos: DDD + número)
    if len(num) >= 10 and not num.startswith("55"):
        num = "55" + num
    return num


# ============================================================
# LIMPEZA DE NOME DO RESTAURANTE (Fix #2)
# ============================================================

def _limpar_nome_restaurante(lead: dict) -> str:
    """Extrai nome limpo do restaurante, filtrando CNPJ/CPF e padrões de razão social.
    Evita usar '34.462.490 WESLEY LOURENCA VIEIRA' como nome do restaurante."""
    nome = lead.get("nome_fantasia") or ""

    # Se nome_fantasia parece ser CNPJ+nome ou nome+CPF, descartar
    if re.search(r'\d{2}\.\d{3}\.\d{3}', nome) or re.search(r'\d{11}', nome):
        nome = ""

    # Se vazio, tentar razão social limpa
    if not nome:
        razao = lead.get("razao_social") or ""
        # Limpar CNPJ/CPF da razão social
        razao = re.sub(r'\d{2}\.\d{3}\.\d{3}[/.\-\d]*', '', razao).strip()
        razao = re.sub(r'\d{9,}', '', razao).strip()
        if razao and len(razao) > 3:
            nome = razao.title()

    if not nome:
        nome = "seu restaurante"

    return nome


# ============================================================
# DETECÇÃO DE AUTO-REPLY / BOT WHATSAPP BUSINESS (Fix #4)
# ============================================================

_AUTORESPOSTA_PATTERNS = [
    r"selecione uma (das )?opções",
    r"digite \d+ para",
    r"hor[áa]rio de atendimento",
    r"fora do (nosso )?hor[áa]rio",
    r"em breve (um )?atendente",
    r"n[ãa]o estamos (dispon[íi]veis|atendendo)",
    r"deixe sua mensagem",
    r"retornaremos (em breve|o mais r[áa]pido)",
    r"atendimento (autom[áa]tico|virtual)",
    r"bem[- ]vindo.*selecione",
    r"menu (principal|de opções)",
    r"resposta autom[áa]tica",
    r"nossa equipe (ir[áa]|vai) (te )?atender",
    r"aguarde.*(atendente|atendimento)",
    r"funcionamos de .*(segunda|seg).*(sexta|sex)",
    # Novos padrões detectados em produção (02/04)
    r"este n[úu]mero foi substitu[íi]do",
    r"este [ée] o (novo )?canal",
    r"canal de atendimento",
    r"ligue para.*(0800|\(\d{2}\))",
    r"(whatsapp|wpp|zap).*(atendimento|comercial|vendas).*\d{4}",
]


def _detectar_broadcast_promo(mensagem: str) -> bool:
    """Detecta se a mensagem é um broadcast promocional / copypaste do lead.
    Mensagens com múltiplos links de delivery, preços, ou templates de vendas."""
    msg_lower = mensagem.lower().strip()
    # Múltiplos links de delivery = broadcast
    delivery_links = sum(1 for p in ["ifood.com", "rappi.com", "99food", "keeta",
                                      "uber ?eats", "aiqfome"] if p in msg_lower)
    if delivery_links >= 2:
        return True
    # Link maps.google ou maps.app = autoresposta com endereço
    if "maps.google" in msg_lower or "maps.app" in msg_lower:
        if len(mensagem) > 200:  # Mensagem longa com mapa = template
            return True
    # Mensagem muito longa com vários preços = cardápio/template
    precos = re.findall(r'r\$\s?\d+', msg_lower)
    if len(precos) >= 3:
        return True
    return False


def _detectar_autoresposta(mensagem: str) -> bool:
    """Detecta se a mensagem é uma auto-reply de WhatsApp Business."""
    msg_lower = mensagem.lower().strip()
    for pattern in _AUTORESPOSTA_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False


def _extrair_horario_funcionamento(mensagem: str) -> str:
    """Extrai informação de horário de funcionamento da msg automática."""
    msg_lower = mensagem.lower()
    match = re.search(
        r'(segunda|seg).*?(sexta|sex|s[áa]bado|sab|domingo|dom).*?(\d{1,2}[h:]?\d{0,2}).*?(\d{1,2}[h:]?\d{0,2})',
        msg_lower
    )
    if match:
        return match.group(0)
    match2 = re.search(r'das?\s+(\d{1,2}[h:]\d{0,2})\s+(às|ate|a)\s+(\d{1,2}[h:]\d{0,2})', msg_lower)
    if match2:
        return match2.group(0)
    return ""


def _agendar_recontato(lead_id: int, conversa_id: int, horario_info: str):
    """Agenda recontato via brain_loop para o horário indicado."""
    from crm.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_conversas
            SET status = 'aguardando_horario',
                notas = COALESCE(notas, '') || %s
            WHERE id = %s
        """, (f"\n[AGENDAR] Recontato sugerido: {horario_info}", conversa_id))
        conn.commit()
    log.info(f"Recontato agendado para lead {lead_id}, conversa {conversa_id}: {horario_info}")


# ============================================================
# DETECÇÃO DE CONTADOR / INTERMEDIÁRIO (Fix #12)
# ============================================================

_CONTADOR_PATTERNS = [
    r"escrit[óo]rio (de )?contab",
    r"contabil",
    r"contabilidade",
    r"contador(a)?(\s|$|,|\.)",
    r"n[ãa]o sou (o )?(dono|propriet[áa]rio|s[óo]cio|respons[áa]vel)",
    r"aqui [ée] (escrit[óo]rio|contabilidade)",
    r"(sou|somos) (o |a )?(contador|contadora)",
    r"esse n[úu]mero [ée] (da |do )?(contabilidade|contador)",
    r"empresa (de )?contabilidade",
]

# Detecção de número errado / não pertence ao lead
_NUMERO_ERRADO_PATTERNS = [
    r"(esse|este) n[úu]mero n[ãa]o [ée] (dele|dela|do |da |meu|nosso)",
    r"n[úu]mero errado",
    r"n[ãa]o conhe[çc]o (essa|esta) pessoa",
    r"n[ãa]o [ée] (aqui|esse|desse|dono|propriet)",
    r"(mandou|enviou|ligou) (pro |para o? ?)n[úu]mero errado",
    r"n[ãa]o (tenho|tem) (nada|nenhuma) (a ver|relação|rela[çc][ãa]o)",
    r"pessoa errada",
    r"engano",
]


def _detectar_numero_errado(mensagem: str) -> bool:
    """Detecta se o lead indica que o número não pertence a ele / pessoa errada."""
    msg_lower = mensagem.lower().strip()
    for pattern in _NUMERO_ERRADO_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False


def _detectar_contador(mensagem: str) -> bool:
    """Detecta se a resposta indica que o número pertence a um contador."""
    msg_lower = mensagem.lower().strip()
    for pattern in _CONTADOR_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False


# ============================================================
# ENRIQUECIMENTO DE LEAD NA CONVERSA (Fix #13)
# ============================================================

def _enriquecer_lead_conversa(lead_id: int, conversa_id: int, mensagem: str):
    """Extrai informações da conversa e atualiza o lead no banco."""
    from crm.database import get_conn
    updates = {}
    msg_lower = mensagem.lower()

    # Detectar nome da pessoa (quando se apresenta)
    match_nome = re.search(
        r'(?:me chamo|meu nome [ée]|sou o|sou a|aqui [ée] o|aqui [ée] a)\s+'
        r'([A-ZÀ-Ú][a-zà-ú]+(?:\s+[A-ZÀ-Ú][a-zà-ú]+)?)',
        mensagem
    )
    if match_nome:
        nome = match_nome.group(1).strip()
        if len(nome) > 2:
            updates["nome_contato_wa"] = nome
            decision_log.info(f"ENRICH lead={lead_id} nome_contato={nome}")

    # Detectar tipo de comida
    tipos_comida = {
        "pizzaria": ["pizza", "pizzaria"],
        "hamburgueria": ["hambúrguer", "hamburger", "hamburgueria", "burger"],
        "japonesa": ["japonesa", "sushi", "temaki", "japa"],
        "açaí": ["açaí", "acai"],
        "padaria": ["padaria", "pão", "pao"],
        "lanchonete": ["lanchonete", "lanche", "x-burger"],
        "churrascaria": ["churrasco", "churrascaria"],
        "marmitaria": ["marmita", "marmitaria", "marmitex"],
        "doceria": ["doce", "doceria", "confeitaria", "bolo"],
        "restaurante": ["restaurante", "refeição", "almoço", "comida caseira"],
    }
    for tipo, keywords in tipos_comida.items():
        if any(kw in msg_lower for kw in keywords):
            updates["tipo_comida_detectado"] = tipo
            break

    # Detectar novo número (contato do dono fornecido pelo contador)
    if any(w in msg_lower for w in ("contato", "número", "whatsapp", "zap", "telefone")):
        match_tel = re.search(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}[-\s]?\d{4}', mensagem)
        if match_tel:
            novo_numero = re.sub(r'\D', '', match_tel.group(0))
            if len(novo_numero) >= 10:
                updates["telefone_dono_wa"] = novo_numero
                decision_log.info(f"ENRICH lead={lead_id} novo_telefone_dono={novo_numero}")

    if updates:
        try:
            with get_conn() as conn:
                cur = conn.cursor()
                notas_extra = json.dumps(updates, ensure_ascii=False)
                cur.execute("""
                    UPDATE leads SET notas = COALESCE(notas, '') || %s, updated_at = NOW()
                    WHERE id = %s
                """, (f"\n[ENRICH] {notas_extra}", lead_id))
                if "nome_contato_wa" in updates:
                    cur.execute("""
                        UPDATE wa_conversas SET notas = COALESCE(notas, '') || %s
                        WHERE id = %s
                    """, (f"\n[NOME] {updates['nome_contato_wa']}", conversa_id))
                conn.commit()
                log.info(f"Lead {lead_id} enriquecido pela conversa: {list(updates.keys())}")
        except Exception as e:
            log.warning(f"Erro ao enriquecer lead {lead_id}: {e}")


def _enviar_audio_abertura(lead_id: int, conversa_id: int, texto_base: str, instance: str = ""):
    """Envia áudio complementar na abertura outbound (Fix #6).
    Gera TTS do texto de abertura e envia como PTT."""
    tts_ativo = (obter_configuracao("audio_tts_autonomo") or "true").lower() == "true"
    if not tts_ativo or not conversa_id:
        return
    try:
        conversa = obter_conversa_wa(conversa_id)
        numero = (conversa or {}).get("numero_envio") or ""
        if not numero:
            return
        _time.sleep(random.uniform(2, 4))  # Delay natural entre texto e áudio
        # Preparar texto para TTS (pronúncia + dicção falada)
        audio_texto = _preparar_texto_para_audio(_preparar_texto_tts(texto_base))
        emocao = "animada"  # Abertura é sempre animada
        resultado = _gerar_e_enviar_audio_resposta(
            numero, audio_texto, conversa_id, instance=instance, emocao=emocao)
        if resultado.get("sucesso"):
            log.info(f"Áudio abertura enviado para lead {lead_id}")
            decision_log.info(f"AUDIO_ABERTURA lead={lead_id} conv={conversa_id}")
        else:
            log.warning(f"Falha áudio abertura lead {lead_id}: {resultado.get('erro')}")
    except Exception as e:
        log.warning(f"Erro áudio abertura lead {lead_id}: {e}")


# ============================================================
# DETECÇÃO DE NÃO-RESTAURANTE / LEAD FALSO (Novo requisito)
# ============================================================

_NAO_RESTAURANTE_PATTERNS = [
    r"n[ãa]o (tenho|temos) restaurante",
    r"n[ãa]o (sou|somos) (de )?restaurante",
    r"n[ãa]o (é|e) restaurante",
    r"n[ãa]o trabalh[oa] com (comida|aliment|restau|deliver)",
    r"(sou|somos|trabalh\w*)\s+(com |de |do |da )?(advogad|advocacia|escrit[óo]rio|consult[óo]ria|im[óo]vel|imobili[áa]ria|loja de roupa|sal[ãa]o|barbearia|farm[áa]cia|cl[íi]nica|consult[óo]rio|oficina|borracharia|posto|mercado|mercadinho|supermercado|atacad|constru[çc][ãa]o|material|funilaria|auto ?pe[çc]a|assist[eê]ncia|inform[áa]tica|academia|est[úu]dio|pet ?shop|veterin[áa]ri|cabeleirei)",
    r"(n[ãa]o|nunca) (trabalh|mexo|fa[çc]o|vend).*(comida|aliment|gastron|culin|delivery)",
    r"fechei o restaurante",
    r"restaurante (fechou|fechado|encerr)",
    r"n[ãa]o (existe|funciona) mais",
    r"cnpj.*(inativo|baixado|fechado|encerrado|suspenso)",
    r"empresa (encerr|fechou|baixou|inativ)",
]


def _detectar_nao_restaurante(mensagem: str) -> bool:
    """Detecta se o lead indica que NÃO é restaurante / negócio de alimentação."""
    msg_lower = mensagem.lower().strip()
    for pattern in _NAO_RESTAURANTE_PATTERNS:
        if re.search(pattern, msg_lower):
            return True
    return False


def _marcar_lead_falso(lead_id: int, conversa_id: int, motivo: str):
    """Marca lead como falso (não é restaurante) — sai do pipeline e de ações futuras."""
    from crm.database import get_conn
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE leads SET status_pipeline = 'lead_falso',
                                 motivo_perda = %s, updated_at = NOW()
                WHERE id = %s
            """, (f"lead_falso: {motivo}", lead_id))
            cur.execute("""
                UPDATE wa_conversas SET status = 'encerrado',
                                        notas = COALESCE(notas, '') || %s
                WHERE id = %s
            """, (f"\n[LEAD_FALSO] {motivo}", conversa_id))
            conn.commit()
        log.info(f"Lead {lead_id} marcado como FALSO: {motivo}")
        decision_log.info(f"LEAD_FALSO lead={lead_id} conv={conversa_id} motivo={motivo}")
    except Exception as e:
        log.warning(f"Erro ao marcar lead {lead_id} como falso: {e}")


def _verificar_restaurante_confirmado(conversa: dict) -> bool:
    """Verifica se nas mensagens da conversa o lead confirmou que é restaurante/food service.
    Retorna True se houver evidência de que é restaurante, False se ainda não confirmou."""
    msgs = conversa.get("mensagens") or []
    texto_recebido = " ".join(
        (m.get("conteudo") or "").lower()
        for m in msgs if m.get("direcao") == "recebida"
    )
    if not texto_recebido:
        return False

    # Palavras que indicam que é restaurante/food service
    indicadores_restaurante = [
        "restaurante", "pizzaria", "hamburgueria", "lanchonete", "padaria",
        "açaiteria", "acaiteria", "churrascaria", "marmitaria", "doceria",
        "confeitaria", "sushi", "temaki", "japonesa", "comida", "cozinha",
        "delivery", "entrega", "cardápio", "cardapio", "prato", "refeição",
        "refeicao", "almoço", "almoco", "janta", "jantar", "café", "cafe",
        "bar", "pub", "bistrô", "bistro", "cantina", "buffet", "self-service",
        "self service", "quentinha", "marmita", "marmitex", "food truck",
        "food", "gastronomia", "culinária", "culinaria", "forno", "churros",
        "pastel", "coxinha", "esfirra", "esfiha", "tapioca", "crepe",
        "sorvete", "sorveteria", "gelateria", "açaí", "acai",
        "pizza", "hambúrguer", "hamburger", "lanche", "hot dog",
        "ifood", "rappi", "99food", "uber eats",
        "pedido", "pedidos", "entregas por dia", "entrego", "entregamos",
    ]

    for indicador in indicadores_restaurante:
        if indicador in texto_recebido:
            return True

    # Se o lead respondeu positivamente sobre comida/tipo
    if re.search(r'(sim|é sim|isso mesmo|exato|exatamente|correto|isso|uhum|aham)', texto_recebido):
        # Verificar se alguma mensagem do bot perguntou sobre tipo de negócio
        texto_enviado = " ".join(
            (m.get("conteudo") or "").lower()
            for m in msgs if m.get("direcao") == "enviada"
        )
        if any(p in texto_enviado for p in ["tipo de comida", "tipo de restaurante",
                                              "pizzaria", "lanchonete", "delivery",
                                              "que tipo", "é restaurante"]):
            return True

    return False


def verificar_webhook_meta(body: bytes, signature: str) -> bool:
    """Verifica assinatura HMAC-SHA256 do webhook Meta."""
    secret = os.environ.get("WHATSAPP_WEBHOOK_SECRET", "")
    if not secret:
        log.warning("WHATSAPP_WEBHOOK_SECRET não configurado — pulando verificação")
        return True
    esperado = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperado, signature)


# ============================================================
# KNOWLEDGE BASE DINÂMICA (atualização sem redeploy)
# ============================================================

_KNOWLEDGE_BASE_PATH = os.path.join(os.path.dirname(__file__), "knowledge_base.txt")

def _carregar_knowledge_base() -> str:
    """Carrega knowledge base dinâmica do arquivo.
    Permite atualizar info do sistema sem alterar código/redeploy.
    O arquivo knowledge_base.txt pode ser editado a qualquer momento."""
    try:
        if os.path.exists(_KNOWLEDGE_BASE_PATH):
            with open(_KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
                conteudo = f.read().strip()
            if conteudo:
                return conteudo
    except Exception as e:
        log.warning(f"Erro ao carregar knowledge_base.txt: {e}")
    return ""


# ============================================================
# ANTI-SPAM: evitar respostas duplicadas quando user manda 2 msgs rápidas
# ============================================================

_processing_lock: dict[str, float] = {}  # numero -> timestamp início processamento
_LOCK_TIMEOUT = 30  # segundos — se está processando há mais de 30s, libera

def _adquirir_lock_resposta(numero: str) -> bool:
    """Tenta adquirir lock para responder a um número.
    Se já está processando uma resposta para esse número, retorna False."""
    agora = _time.time()
    if numero in _processing_lock:
        inicio = _processing_lock[numero]
        if agora - inicio < _LOCK_TIMEOUT:
            log.info(f"Lock ativo para {numero} — ignorando msg duplicada ({agora - inicio:.1f}s)")
            return False
    _processing_lock[numero] = agora
    return True

def _liberar_lock_resposta(numero: str):
    """Libera lock de resposta para um número."""
    _processing_lock.pop(numero, None)


def _agregar_mensagens_pendentes(conversa_id: int, mensagem_original: str) -> str:
    """Após delay humano, re-lê banco e concatena msgs 'enfileiradas' com a original.
    Marca as enfileiradas como 'agregada' para não reprocessar."""
    from crm.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, conteudo FROM wa_mensagens
            WHERE conversa_id = %s AND direcao = 'recebida' AND intencao = 'enfileirada'
            ORDER BY created_at
        """, (conversa_id,))
        pendentes = cur.fetchall()
        if not pendentes:
            return mensagem_original

        # Marcar como agregadas
        ids = [r["id"] for r in pendentes]
        cur.execute("""
            UPDATE wa_mensagens SET intencao = 'agregada'
            WHERE id = ANY(%s)
        """, (ids,))
        conn.commit()

    # Concatenar: msg_original + pendentes
    todas = [mensagem_original] + [r["conteudo"] for r in pendentes if r["conteudo"]]
    log.info(f"Debounce: {len(pendentes)} msgs agregadas com original")
    return "\n".join(todas)


def _calcular_delay_humano(mensagem_cliente: str) -> float:
    """Calcula delay variável para parecer humano.
    Mensagens longas = mais tempo 'lendo'. Mínimo 3s, máximo 15s."""
    n_palavras = len(mensagem_cliente.split())
    base = n_palavras * 0.8  # mais palavras = mais tempo "lendo"
    delay = random.uniform(3, max(8, min(base, 15)))
    return delay


# ============================================================
# ENVIO DE MENSAGEM (WhatsApp Cloud API)
# ============================================================

def _enviar_via_evolution(numero: str, texto: str, instance_override: str = "") -> dict:
    """Envia mensagem via Evolution API (outbound prioritário).
    Se instance_override fornecido, usa essa instância em vez da padrão."""
    url, instance, key = _get_evolution_config()
    if instance_override:
        instance = instance_override
    if not url or not key:
        return {"erro": "Evolution API não configurada"}

    # Indicador "digitando..." antes de enviar
    _enviar_presenca(numero, "composing", delay_ms=3000, instance_override=instance_override)

    try:
        resp = httpx.post(
            f"{url}/message/sendText/{instance}",
            headers={
                "apikey": key,
                "Content-Type": "application/json",
            },
            json={
                "number": numero,
                "text": texto,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        msg_id = result.get("key", {}).get("id", "")
        log.info(f"Mensagem enviada via Evolution API: {msg_id}")
        return {"sucesso": True, "wa_msg_id": msg_id, "via": "evolution"}
    except Exception as e:
        log.error(f"Erro Evolution API: {e}")
        return {"erro": f"Evolution API: {e}"}


def _enviar_via_cloud_api(numero: str, texto: str) -> dict:
    """Fallback: envia via WhatsApp Cloud API (Meta)."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada"}

    try:
        resp = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "text",
                "text": {"body": texto},
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        wa_msg_id = result.get("messages", [{}])[0].get("id", "")
        log.info(f"Mensagem enviada via Cloud API: wa_msg_id={wa_msg_id}")
        return {"sucesso": True, "wa_msg_id": wa_msg_id, "via": "cloud_api"}
    except Exception as e:
        log.error(f"Erro WhatsApp Cloud API: {e}")
        return {"erro": f"Cloud API: {e}"}


def enviar_mensagem_wa(lead_id: int, texto: str, tom: str = "informal") -> dict:
    """Envia mensagem de texto via WhatsApp.
    Prioridade: Evolution API → Cloud API (fallback).
    Cria conversa se não existir."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out de WhatsApp"}

    if httpx is None:
        return {"erro": "httpx não instalado (pip install httpx)"}

    # Criar ou buscar conversa
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa:
        conversa_id = conversa["id"]
        numero = conversa.get("numero_envio") or ""
    else:
        telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
        numero = _formatar_numero_wa(telefone)
        # Verificar número excluído ou inválido
        num_limpo = _limpar_telefone(numero)
        if num_limpo in _NUMEROS_EXCLUIDOS:
            return {"erro": f"Número excluído da prospecção: {num_limpo}"}
        if len(num_limpo) < 8:
            return {"erro": f"Telefone inválido: {telefone}"}
        conversa_id = criar_conversa_wa(lead_id, numero, tom)

    if not numero:
        return {"erro": "Lead sem telefone válido"}

    # Enviar: Evolution API (prioritário, instância outbound) → Cloud API (fallback)
    resultado = _enviar_via_evolution(numero, texto)  # usa instância padrão (outbound)
    if resultado.get("erro"):
        log.warning(f"Evolution falhou, tentando Cloud API: {resultado['erro']}")
        resultado = _enviar_via_cloud_api(numero, texto)

    if resultado.get("erro"):
        registrar_msg_wa(conversa_id, "enviada", texto, intencao="erro_envio")
        return {"erro": resultado["erro"]}

    # Registrar mensagem
    msg_id = registrar_msg_wa(conversa_id, "enviada", texto)

    # Registrar interação no CRM
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA enviado ({resultado.get('via', '?')}): {texto[:100]}...", "enviado")

    log.info(f"Mensagem enviada para lead {lead_id} ({numero}) via {resultado.get('via')}")
    return {"sucesso": True, "conversa_id": conversa_id, "msg_id": msg_id,
            "via": resultado.get("via")}


# ============================================================
# ÁUDIO TTS (Grok)
# ============================================================

# ============================================================
# ÁUDIO STT — Transcrição via Groq Whisper (GRÁTIS)
# ============================================================

def _get_groq_key() -> str:
    """Retorna API key do Groq."""
    return obter_configuracao("groq_api_key") or os.environ.get("GROQ_API_KEY", "")


def transcrever_audio(audio_base64: str, duracao_seg: int = 0) -> dict:
    """Transcreve áudio com Groq Whisper. GRÁTIS no free tier (2000 req/dia).
    Retorna {"texto": "...", "duracao": N} ou {"erro": "..."}."""
    groq_key = _get_groq_key()
    if not groq_key:
        log.error("GROQ_API_KEY não configurada")
        return {"erro": "GROQ_API_KEY não configurada"}

    if httpx is None:
        return {"erro": "httpx não instalado"}

    # Decodificar base64 → arquivo temp .ogg
    try:
        audio_bytes = base64.b64decode(audio_base64)
    except Exception as e:
        return {"erro": f"Base64 inválido: {e}"}

    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".ogg", delete=False)
        tmp.write(audio_bytes)
        tmp.close()
        tmp_path = tmp.name

        # POST para Groq Whisper
        with open(tmp_path, "rb") as f:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key}"},
                files={"file": ("audio.ogg", f, "audio/ogg")},
                data={
                    "model": "whisper-large-v3-turbo",
                    "language": "pt",
                    "response_format": "verbose_json",
                },
                timeout=30,
            )
        resp.raise_for_status()
        data = resp.json()
        texto = data.get("text", "").strip()
        dur = data.get("duration", duracao_seg) or duracao_seg

        log.info(f"Áudio transcrito: {len(texto)} chars, {dur}s")
        return {"texto": texto, "duracao": int(dur)}

    except Exception as e:
        log.error(f"Erro Groq Whisper: {e}")
        return {"erro": f"Groq Whisper: {e}"}
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def baixar_audio_evolution(msg_key_id: str, instance: str = "") -> dict:
    """Baixa áudio de mensagem via Evolution API getBase64FromMediaMessage.
    Retorna {"base64": "...", "mimetype": "..."} ou {"erro": "..."}."""
    url, inst, key = _get_evolution_config()
    if instance:
        inst = instance
    if not url or not key:
        return {"erro": "Evolution API não configurada"}

    try:
        resp = httpx.post(
            f"{url}/chat/getBase64FromMediaMessage/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={"message": {"key": {"id": msg_key_id}}, "convertToMp4": False},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        b64 = data.get("base64", "")
        mime = data.get("mimetype", "audio/ogg")
        if not b64:
            return {"erro": "Áudio vazio na resposta"}
        log.info(f"Áudio baixado: {len(b64)} chars base64, mime={mime}")
        return {"base64": b64, "mimetype": mime}
    except Exception as e:
        log.error(f"Erro ao baixar áudio Evolution: {e}")
        return {"erro": f"Download áudio: {e}"}


def _calcular_delay_audio(duracao_seg: int) -> float:
    """Calcula delay proporcional para simular escuta do áudio (1.5x speed).
    Mínimo 5s, máximo 120s."""
    if duracao_seg <= 0:
        return 8.0  # Default se não souber duração
    delay = duracao_seg / 1.5
    return max(5.0, min(delay, 120.0))


# ============================================================
# ENVIO DE ÁUDIO VIA EVOLUTION API
# ============================================================

def _enviar_audio_evolution(numero: str, audio_base64: str, instance: str = "",
                            mimetype: str = "audio/mpeg") -> dict:
    """Envia áudio como PTT nativo (bolinha verde) via Evolution API sendWhatsAppAudio."""
    url, inst, key = _get_evolution_config()
    if instance:
        inst = instance
    if not url or not key:
        return {"erro": "Evolution API não configurada"}

    # Indicador "gravando áudio..." antes de enviar
    _enviar_presenca(numero, "recording", delay_ms=5000, instance_override=instance)

    try:
        resp = httpx.post(
            f"{url}/message/sendWhatsAppAudio/{inst}",
            headers={"apikey": key, "Content-Type": "application/json"},
            json={
                "number": numero,
                "audio": audio_base64,
                "encoding": True,
            },
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        msg_id = result.get("key", {}).get("id", "")
        log.info(f"Áudio PTT enviado via Evolution: {msg_id}")
        return {"sucesso": True, "wa_msg_id": msg_id, "via": "evolution"}
    except Exception as e:
        log.error(f"Erro envio áudio Evolution: {e}")
        return {"erro": f"Envio áudio Evolution: {e}"}


def _enviar_audio_cloud_api(numero: str, audio_bytes: bytes) -> dict:
    """Fallback: envia áudio via WhatsApp Cloud API (Meta).
    Faz upload do áudio e envia como mensagem de áudio (não PTT)."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada para áudio"}

    try:
        # Upload do áudio para Meta
        import io
        resp_upload = httpx.post(
            f"{_GRAPH_API}/{phone_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("audio.mp3", io.BytesIO(audio_bytes), "audio/mpeg")},
            data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
            timeout=30,
        )
        resp_upload.raise_for_status()
        media_id = resp_upload.json().get("id")
        if not media_id:
            return {"erro": "Upload áudio Cloud API falhou (sem media_id)"}

        log.info(f"Áudio uploaded para Cloud API: media_id={media_id}")

        # Enviar mensagem de áudio
        resp_msg = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "audio",
                "audio": {"id": media_id},
            },
            timeout=15,
        )
        resp_msg.raise_for_status()
        wa_msg_id = (resp_msg.json().get("messages") or [{}])[0].get("id", "")
        log.info(f"Áudio enviado via Cloud API: wa_msg_id={wa_msg_id}")
        return {"sucesso": True, "wa_msg_id": wa_msg_id, "via": "cloud_api_audio"}
    except Exception as e:
        log.error(f"Erro envio áudio Cloud API: {e}")
        return {"erro": f"Cloud API áudio: {e}"}


# ============================================================
# DECISÃO AUTÔNOMA: QUANDO ENVIAR ÁUDIO
# ============================================================

def _deve_enviar_audio(conversa: dict, mensagem_atual: str) -> bool:
    """Decide se deve enviar áudio em vez de texto.
    Critérios:
    1. Cliente PEDIU áudio explicitamente — na msg atual OU nas últimas 6 msgs (preferência persistente)
    2. Cliente pediu muitas explicações (>=3 nos últimos 6 msgs)
    3. Cliente enviou áudio (reciprocidade)
    4. Conversa longa sem avanço (>=10 msgs, nunca usou áudio)
    Retorna True se deve enviar áudio."""
    # Verificar toggle
    tts_ativo = (obter_configuracao("audio_tts_autonomo") or "true").lower() == "true"
    if not tts_ativo:
        return False

    keywords_pediu_audio = [
        "áudio", "audio", "por voz", "manda áudio", "manda audio",
        "me explica por áudio", "me explica por audio", "quero ouvir",
        "prefiro áudio", "prefiro audio", "fala por áudio", "fala por audio",
        "pode mandar áudio", "pode mandar audio", "manda um áudio",
        "manda um audio", "por áudio", "por audio", "envia áudio",
        "envia audio", "grava um áudio", "grava um audio",
        "me manda um áudio", "me manda um audio",
    ]

    msg_lower = mensagem_atual.lower()
    pediu_audio_agora = any(k in msg_lower for k in keywords_pediu_audio)

    msgs = conversa.get("mensagens") or []

    # Critério 1 (PRIORITÁRIO): Cliente pediu áudio — verificar msg atual E últimas 6 msgs recebidas
    # Preferência de áudio persiste: se pediu 3 msgs atrás, ainda vale
    pediu_audio_historico = False
    for m in msgs[-6:]:
        if m.get("direcao") == "recebida":
            txt = (m.get("conteudo") or "").lower()
            if any(k in txt for k in keywords_pediu_audio):
                pediu_audio_historico = True
                break

    pediu_audio = pediu_audio_agora or pediu_audio_historico

    # Critério 2: Muitas explicações nas últimas 6 msgs
    keywords_explicacao = ["explica", "como funciona", "como é", "me fala mais",
                           "quero saber", "me conta", "entendi não", "não entendi"]
    n_explicacoes = 0
    for m in msgs[-6:]:
        if m.get("direcao") == "recebida":
            txt = (m.get("conteudo") or "").lower()
            if any(k in txt for k in keywords_explicacao):
                n_explicacoes += 1

    # Critério 3: Cliente enviou áudio nas últimas 3 msgs (reciprocidade)
    recebeu_audio = any(
        m.get("tipo") == "audio" and m.get("direcao") == "recebida"
        for m in msgs[-3:]
    )

    # Critério 4: Conversa longa sem avanço
    conversa_longa_sem_audio = len(msgs) >= 10 and not conversa.get("usou_audio")

    resultado = pediu_audio or n_explicacoes >= 3 or recebeu_audio or conversa_longa_sem_audio

    if resultado:
        motivo = []
        if pediu_audio_agora:
            motivo.append("cliente_pediu_audio_agora")
        elif pediu_audio_historico:
            motivo.append("cliente_pediu_audio_recente")
        if n_explicacoes >= 3:
            motivo.append(f"explicações={n_explicacoes}")
        if recebeu_audio:
            motivo.append("reciprocidade_audio")
        if conversa_longa_sem_audio:
            motivo.append("conversa_longa")
        log.info(f"Decisão TTS autônomo: ENVIAR ÁUDIO ({', '.join(motivo)})")

    return resultado


def _inferir_emocao_contexto(intencao: str, resposta: str, mensagem_cliente: str) -> str:
    """Infere a emoção S2-Pro baseada no contexto da conversa.

    Mapeia intenção do lead + conteúdo da resposta → tag de emoção Fish Audio.
    As tags são usadas pelo modelo S2-Pro para modular tom de voz.
    """
    resp_lower = resposta.lower()
    msg_lower = mensagem_cliente.lower()

    # 1. Detectar pelo conteúdo da RESPOSTA da Ana
    if any(w in resp_lower for w in ["teste grátis", "15 dias", "vou ativar", "vou liberar", "vou configurar"]):
        return "trial"
    if any(w in resp_lower for w in ["perfeito!", "ótimo!", "maravilha", "show!"]):
        return "fechamento"
    if any(w in resp_lower for w in ["entendo", "compreendo", "faz sentido", "com razão"]):
        return "objecao"
    if any(w in resp_lower for w in ["r$", "plano", "preço", "investimento", "valor"]):
        return "preco"
    if any(w in resp_lower for w in ["imagina", "funcionalidade", "o sistema", "bridge", "kds", "despacho"]):
        return "beneficio"
    if any(w in resp_lower for w in ["urgente", "vagas", "agenda", "essa semana"]):
        return "urgencia"
    if any(w in resp_lower for w in ["sucesso", "até mais", "qualquer coisa", "é só chamar"]):
        return "despedida"

    # 2. Detectar pela INTENÇÃO do lead
    mapa_intencao = {
        "interesse": "empolgado",
        "curiosidade": "amigavel",
        "objecao_preco": "objecao",
        "objecao_concorrente": "profissional",
        "objecao": "objecao",
        "duvida_tecnica": "profissional",
        "pediu_demo": "empolgado",
        "pediu_trial": "trial",
        "satisfeito": "fechamento",
        "hard_no": "despedida",
        "soft_no": "amigavel",
    }
    if intencao in mapa_intencao:
        return mapa_intencao[intencao]

    # 3. Detectar pela mensagem do CLIENTE
    if any(w in msg_lower for w in ["golpe", "confi", "quem é", "cnpj"]):
        return "profissional"
    if any(w in msg_lower for w in ["obrigad", "valeu", "agradeç"]):
        return "amigavel"
    if any(w in msg_lower for w in ["caro", "dinheiro", "grana", "preço"]):
        return "objecao"

    # 4. Default: abertura (amigável + sorriso)
    return "abertura"


def _gerar_e_enviar_audio_resposta(numero: str, texto_resposta: str,
                                    conversa_id: int, instance: str = "",
                                    emocao: str = "") -> dict:
    """Gera TTS do texto da resposta e envia via Evolution API.

    Se tts_provider="fish": usa _gerar_audio_com_cache (fila + cache inteligente).
    Senão: usa gerar_audio_tts (Grok TTS legado).

    Retorna sucesso/erro."""
    tts_provider = (obter_configuracao("tts_provider") or "grok").lower().strip()
    voz = obter_configuracao("audio_voz") or "rex"

    audio_bytes = None
    audio_path = None

    # --- Fish Audio com cache + fila ---
    if tts_provider == "fish":
        audio_bytes = _gerar_audio_com_cache(texto_resposta, conversa_id, emocao=emocao)
        if not audio_bytes:
            return {"erro": "Fish Audio falhou — fallback texto"}
    else:
        # --- Grok TTS legado ---
        audio_path = gerar_audio_tts(texto_resposta, voz=voz, emocao=emocao)
        if not audio_path:
            return {"erro": "Falha ao gerar áudio TTS"}
        try:
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
        except Exception as e:
            return {"erro": f"Erro leitura áudio: {e}"}

    try:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Verificar se Evolution está configurada
        evo_instance = (obter_configuracao("evolution_instance") or "").strip()
        if evo_instance:
            # Enviar via Evolution (PTT nativo)
            resultado = _enviar_audio_evolution(numero, audio_b64, instance=instance)
            # Fallback: Cloud API (áudio normal, não PTT)
            if not resultado.get("sucesso"):
                log.warning(f"Evolution áudio falhou, tentando Cloud API: {resultado.get('erro', '')}")
                resultado = _enviar_audio_cloud_api(numero, audio_bytes)
        else:
            # Evolution desabilitada — enviar direto via Cloud API
            resultado = _enviar_audio_cloud_api(numero, audio_bytes)

        if resultado.get("sucesso"):
            registrar_msg_wa(conversa_id, "enviada",
                             f"[ÁUDIO] {texto_resposta[:100]}...", tipo="audio")
            provider_label = "fish" if tts_provider == "fish" else f"grok/{voz}"
            via = resultado.get("via", "evolution")
            atualizar_conversa_wa(conversa_id, usou_audio=True, voz_usada=f"{provider_label}/{via}")
            log.info(f"Áudio TTS enviado para conversa {conversa_id} (provider={provider_label}, via={via})")
        return resultado

    except Exception as e:
        log.error(f"Erro gerar/enviar áudio TTS: {e}")
        return {"erro": str(e)}
    finally:
        if audio_path:
            try:
                os.unlink(audio_path)
            except Exception:
                pass


def gerar_script_audio(lead: dict) -> str:
    """Gera script de áudio personalizado para o lead (~30s).
    Usa dados iFood enriquecidos quando disponíveis."""
    pers = personalizar_abordagem(lead)
    nome_dono = pers.get("nome_dono") or ""
    if not nome_dono:
        nome_dono = _limpar_nome_restaurante(lead)
    nome_rest = _limpar_nome_restaurante(lead)
    rating = lead.get("rating") or 0
    reviews = lead.get("total_reviews") or 0
    ifood_rating = lead.get("ifood_rating") or 0
    ifood_reviews = lead.get("ifood_reviews") or 0
    ifood_categorias = lead.get("ifood_categorias") or ""
    tem_ifood = lead.get("tem_ifood") or 0

    # Prioridade: dados iFood > dados Google
    if tem_ifood and ifood_rating > 0 and ifood_reviews > 0:
        cat_mention = ""
        if ifood_categorias:
            primeira_cat = ifood_categorias.split(",")[0].strip()
            cat_mention = f"Vocês trabalham com {primeira_cat} e "
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é a Ana, da Derekh Food. "
            f"Vi que o {nome_rest} tem nota {ifood_rating} no iFood "
            f"com {ifood_reviews} avaliações, parabéns pela qualidade! "
            f"{cat_mention}já têm uma clientela fiel. "
            f"Imagina ter sua marca própria de delivery, "
            f"e ainda centralizar os pedidos do iFood no mesmo painel? "
            f"A Derekh monta tudo em 48 horas e vc testa 15 dias grátis. Posso te mostrar?"
        )
    elif rating > 0 and reviews > 0:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é a Ana, da Derekh Food. "
            f"Vi que o {nome_rest} tem uma nota de {rating} estrelas "
            f"com {reviews} avaliações no Google, parabéns pelo trabalho! "
            f"A Derekh cria seu delivery próprio com a sua marca em 48 horas, "
            f"com 15 dias grátis pra vc testar. "
            f"Posso te mostrar como funciona?"
        )
    elif not tem_ifood:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é a Ana, da Derekh Food. "
            f"Vi que o {nome_rest} ainda não está no delivery online. "
            f"A Derekh cria seu delivery próprio em 48 horas, "
            f"com cardápio digital, pagamento Pix e 15 dias grátis pra testar. "
            f"Posso te contar como funciona?"
        )
    else:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é a Ana, da Derekh Food. "
            f"Trabalho com restaurantes e vi que o {nome_rest} "
            f"tem tudo para crescer com delivery próprio, a sua marca. "
            f"Seus clientes pedem direto com você e vc testa 15 dias grátis. "
            f"Posso te contar como funciona?"
        )
    return script


# ============================================================
# PRONÚNCIA TTS — substitui marcas/nomes para pronúncia correta
# REGRA CRÍTICA: só altera texto para áudio, NUNCA para texto escrito
# ============================================================
_TTS_PRONUNCIA = [
    # Marca principal
    ("Derekh Food", "Dérikh Food"),
    ("derekh food", "dérikh food"),
    ("Derekh food", "Dérikh food"),
    ("derekh Food", "dérikh Food"),
    ("DEREKH FOOD", "DÉRIKH FOOD"),
    ("Derekh", "Dérikh"),
    ("derekh", "dérikh"),
    ("DEREKH", "DÉRIKH"),
    # Termos tech — pronúncia correta para TTS brasileiro
    ("iFood", "áiFud"),
    ("ifood", "áifud"),
    ("IFOOD", "ÁIFUD"),
    ("Rappi", "Rápi"),
    ("rappi", "rápi"),
    ("KDS", "cá dê ésse"),
    ("PWA", "pê dáblio ei"),
    ("QR Code", "quiú ár côde"),
    ("QR code", "quiú ár côde"),
    ("Bridge", "Bridji"),
    ("bridge", "bridji"),
    ("Setup", "Setáp"),
    ("setup", "setáp"),
]


def _preparar_texto_tts(texto: str) -> str:
    """Substitui nomes de marcas pela pronúncia correta para TTS.
    NUNCA usar em texto escrito — apenas antes de enviar ao TTS."""
    for escrita, pronuncia in _TTS_PRONUNCIA:
        texto = texto.replace(escrita, pronuncia)
    return texto


# ============================================================
# ENGENHARIA DE FALA NATURAL — Sistema Humanoide Ana
# Abordagem 70% formal + 30% informal = realismo humano.
# O LLM gera português correto. Para TEXTO, envia direto.
# Para ÁUDIO, transforma em dicção falada brasileira natural
# + tags de emoção para Fish Audio S2-Pro.
# ============================================================
import re as _re_audio

# ---------- CONVERSÕES OBRIGATÓRIAS (sempre aplicar) ----------
_DICCAO_OBRIGATORIAS = [
    (r'\bnão é\b', 'né'), (r'\bNão é\b', 'Né'),
    (r'\bpara o\b', 'pro'), (r'\bpara os\b', 'pros'),
    (r'\bpara a\b', 'pra'), (r'\bpara as\b', 'pras'),
    (r'\bpara\b', 'pra'), (r'\bPara\b', 'Pra'),
    (r'\bestou\b', 'tô'), (r'\bEstou\b', 'Tô'),
    (r'\bestá\b', 'tá'), (r'\bEstá\b', 'Tá'),
    (r'\bestão\b', 'tão'), (r'\bestamos\b', 'tamo'),
    (r'\bestava\b', 'tava'), (r'\bEstava\b', 'Tava'),
    (r'\bestavam\b', 'tavam'),
    (r'\bvamos\b', 'vamo'), (r'\bVamos\b', 'Vamo'),
    (r'\bestive\b', 'tive'), (r'\bEstive\b', 'Tive'),
]

# ---------- VERBOS -AR permitidos para R-drop (com espaçamento) ----------
_VERBOS_AR_DROP = {
    'falar', 'explicar', 'mandar', 'pagar', 'ajudar', 'mostrar', 'usar',
    'cobrar', 'achar', 'deixar', 'passar', 'ligar', 'chamar', 'precisar',
    'conversar', 'retornar', 'testar', 'cancelar', 'contar', 'gostar',
}

# ---------- CONVERSÕES PROIBIDAS (jamais aplicar) ----------
_PROIBIDO = {
    'cê', 'cês', 'num', 'purque', 'mermo', 'mió', 'muié', 'véi', 'vei',
    'fazê', 'tê', 'sê', 'podê', 'dizê', 'sabê', 'resolvê', 'conhecê',
    'querê', 'vê', 'entendê', 'parecê', 'acontecê', 'mantê', 'recebê',
    'consegui', 'senti', 'saí', 'pedi', 'decidi', 'assisti',
    'fizé', 'quisé', 'pudé', 'soubé', 'tivé', 'dissé', 'trouxé',
}

# ---------- EXPRESSÕES CONGELADAS (nunca alterar) ----------
_EXPRESSOES_CONGELADAS = [
    'tudo bem', 'tudo certo', 'com certeza', 'sem problema', 'por favor',
    'com licença', 'me desculpa', 'faz sentido', 'o que aconteceu',
    'na verdade', 'por exemplo', 'de qualquer forma', 'sendo assim',
    'com calma', 'sem compromisso', 'sem pressa', 'fica bom',
    'que acha', 'pode ficar tranquilo', 'a gente resolve',
]

# ---------- CONECTORES ORAIS disponíveis ----------
_CONECTORES = ['Então,', 'Ah,', 'Bom,', 'Ó,', 'Olha,', 'É o seguinte,']

# ---------- FINALIZADORES orais ----------
_FINALIZADORES = ['tá?', 'viu?', 'né?']

# ---------- FILLERS ORAIS naturais (inseridos em frases intermediárias) ----------
_FILLERS_ORAIS = [
    'olha,', 'sabe,', 'tipo,', 'na real,', 'ah,', 'bom,', 'ó,',
    'então olha,', 'é que assim,', 'vou te falá,',
]

# ---------- CONTEXTO EMOCIONAL (palavras-chave → nível) ----------
_CONTEXTO_KEYWORDS = {
    'serio': ['frustração', 'problema', 'desculpa', 'erro', 'valor', 'preço',
              'custo', 'orçamento', 'reclamação', 'não funciona', 'caiu'],
    'profissional': ['explicar', 'funciona', 'sistema', 'plano', 'demonstração',
                     'contato', 'apresentar'],
    'amigavel': ['tudo bem', 'novidades', 'como vai', 'passando pra',
                 'semana', 'números'],
    'empolgado': ['parabéns', 'boa notícia', 'aumentou', 'cresceu', 'fechou',
                  'bem-vindo', 'confiança', 'sucesso'],
}

# Limites por contexto: (max_permitidas, max_r_drop, max_finalizadores)
_CONTEXTO_LIMITES = {
    'serio': (0, 0, 1),
    'profissional': (2, 1, 1),
    'amigavel': (3, 2, 2),
    'empolgado': (3, 2, 2),
}

# ---------- RISADAS → tag de emoção ----------
_RISADAS_PARA_TAG = {
    'kkk': '[risinhos]', 'kkkk': '[risinhos]', 'kkkkk': '[risinhos]',
    'haha': '[risinhos]', 'hahaha': '[risinhos]',
    'rs': '[risinhos]', 'rsrs': '[risinhos]',
}

# ---------- TAGS DE EMOÇÃO Fish Audio S2 ----------
_TAGS_EMOCAO = {
    'abertura': '[amigável]',
    'serio': '[sério]',
    'profissional': '[profissional]',
    'amigavel': '[amigável]',
    'empolgado': '[empolgado]',
    'alivio': '[aliviado]',
    'pausa': '[pausa curta]',
}


def _detectar_contexto(texto: str) -> str:
    """Detecta contexto emocional do texto baseado em palavras-chave."""
    texto_lower = texto.lower()
    scores = {}
    for ctx, keywords in _CONTEXTO_KEYWORDS.items():
        scores[ctx] = sum(1 for kw in keywords if kw in texto_lower)
    best = max(scores, key=scores.get) if any(v > 0 for v in scores.values()) else 'profissional'
    return best


def _pode_converter_permitida(posicao: int, conversoes_feitas: list, total_palavras: int) -> bool:
    """Regra de espaçamento: máx 1 conversão permitida por janela de 8 palavras."""
    janela_inicio = max(0, posicao - 4)
    janela_fim = min(total_palavras, posicao + 4)
    return not any(janela_inicio <= pos <= janela_fim for pos in conversoes_feitas)


def _contem_expressao_congelada(texto: str, pos_inicio: int, pos_fim: int) -> bool:
    """Verifica se a posição está dentro de uma expressão congelada."""
    texto_lower = texto.lower()
    for expr in _EXPRESSOES_CONGELADAS:
        idx = texto_lower.find(expr)
        while idx != -1:
            expr_fim = idx + len(expr)
            if idx <= pos_inicio < expr_fim or idx < pos_fim <= expr_fim:
                return True
            idx = texto_lower.find(expr, idx + 1)
    return False


MAX_PALAVRAS_AUDIO = 75  # ~30 segundos a 150 palavras/min


def _truncar_para_audio(texto: str) -> tuple:
    """Se texto > 75 palavras, corta na última frase completa.
    Retorna (parte_audio, texto_complemento_ou_None)."""
    palavras = texto.split()
    if len(palavras) <= MAX_PALAVRAS_AUDIO:
        return texto, None
    cortado = ' '.join(palavras[:MAX_PALAVRAS_AUDIO])
    ultimo_ponto = max(cortado.rfind('.'), cortado.rfind('!'), cortado.rfind('?'))
    if ultimo_ponto > len(cortado) // 2:
        audio_part = cortado[:ultimo_ponto + 1]
    else:
        audio_part = cortado + '...'
    texto_complemento = texto[len(audio_part):].strip()
    return audio_part, texto_complemento if texto_complemento else None


_RE_NUMERICO = re.compile(r'R\$\s*[\d.,]+|\d+%|\d+ dias|https?://\S+')


def _extrair_dados_numericos(texto: str) -> str:
    """Extrai preços, %, URLs. Retorna resumo ou None se <2 dados."""
    matches = _RE_NUMERICO.findall(texto)
    if len(matches) < 2:
        return None
    return "Resumindo: " + " | ".join(matches)


def _preparar_texto_para_audio(texto: str) -> str:
    """Transforma português correto do LLM → dicção falada brasileira para TTS.

    Engenharia de Fala Natural — Proporção 70% formal + 30% informal.
    O segredo é transformar POUCO, nos lugares CERTOS, com ESPAÇAMENTO.

    Ordem das operações:
    1. Pronúncias especiais (Derekh → Dérikh) — feito pelo TTS module
    2. Remover elementos visuais (URLs, markdown, emojis sem som)
    3. Detectar contexto emocional → define nível de informalidade
    4. Converter risadas em tags
    5. Aplicar OBRIGATÓRIAS (pra, tô, tá, tava, né)
    6. Aplicar PERMITIDAS com espaçamento (R-drop verbos -AR)
    7. Encerramento casual (brigada) + finalizadores (tá?, viu?)
    8. Verificação de segurança (proibidos, plurais, subjuntivo)
    9. Adicionar tag de emoção de abertura
    """

    # --- 2. Remover elementos visuais ---
    texto = _re_audio.sub(r'https?://\S+', '', texto)
    texto = _re_audio.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)
    texto = _re_audio.sub(r'__(.+?)__', r'\1', texto)
    texto = _re_audio.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)
    # Remover caracteres visuais
    texto = _re_audio.sub(r'[•→←↓↑►▶✅❌⚠️📌🔥💡]', '', texto)
    # Emojis Unicode → remover (exceto os que viram tag)
    texto = _re_audio.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]', '', texto
    )

    # --- 3. Detectar contexto emocional ---
    contexto = _detectar_contexto(texto)
    max_permitidas, max_r_drop, max_finalizadores = _CONTEXTO_LIMITES.get(contexto, (2, 1, 1))

    # --- 4. Converter risadas em tags ---
    for riso, tag in _RISADAS_PARA_TAG.items():
        texto = _re_audio.sub(r'\b' + _re_audio.escape(riso) + r'\b', tag, texto, flags=_re_audio.IGNORECASE)

    # --- 5. Aplicar OBRIGATÓRIAS (sempre, sem limite) ---
    for pattern, repl in _DICCAO_OBRIGATORIAS:
        texto = _re_audio.sub(pattern, repl, texto)

    # --- 6. Aplicar PERMITIDAS com espaçamento (verbos -AR R-drop) ---
    palavras = texto.split()
    conversoes_feitas = []  # posições das conversões permitidas
    r_drops_feitos = 0

    for i, palavra in enumerate(palavras):
        if r_drops_feitos >= max_r_drop:
            break
        limpa = _re_audio.sub(r'[.,!?;:]+$', '', palavra).lower()
        if limpa in _VERBOS_AR_DROP and palavra.endswith(('ar', 'ar.', 'ar!', 'ar?', 'ar,')):
            # Não no início da frase, não antes de pausa longa
            if i == 0:
                continue
            if _pode_converter_permitida(i, conversoes_feitas, len(palavras)):
                sufixo = palavra[len(limpa):]
                palavras[i] = palavra[:-(len('ar') + len(sufixo))] + 'á' + sufixo
                conversoes_feitas.append(i)
                r_drops_feitos += 1

    texto = ' '.join(palavras)

    # --- 6.5 Fillers orais naturais (inserir no início de frases intermediárias) ---
    if contexto in ('amigavel', 'empolgado'):
        frases_filler = texto.split('. ')
        if len(frases_filler) >= 2:
            import random as _rnd_filler
            # Inserir filler na 2ª frase (35% chance)
            if _rnd_filler.random() < 0.35:
                filler = _rnd_filler.choice(_FILLERS_ORAIS)
                f2 = frases_filler[1]
                if f2:
                    frases_filler[1] = filler + ' ' + f2[0].lower() + f2[1:]
                texto = '. '.join(frases_filler)

    # --- 7. Encerramento casual + finalizadores ---
    # "obrigada" → "brigada" APENAS no final do áudio
    if _re_audio.search(r'\b[Oo]brigad[oa]\s*[!.]?\s*$', texto):
        texto = _re_audio.sub(r'\b([Oo])brigad([oa])\s*([!.]?)\s*$',
                              lambda m: ('B' if m.group(1) == 'O' else 'b') + 'rigad' + m.group(2) + m.group(3),
                              texto)

    # Adicionar finalizador (tá?, viu?) — max conforme contexto, NUNCA em frases < 8 palavras
    frases = _re_audio.split(r'(?<=[.!?])\s+', texto)
    finalizadores_usados = 0
    if max_finalizadores > 0 and len(frases) >= 2:
        ultima_frase = frases[-1]
        if len(ultima_frase.split()) >= 8 and not ultima_frase.rstrip().endswith(('?', 'né?')):
            import random as _rnd
            if _rnd.random() < 0.45:  # 45% de chance
                fin = _rnd.choice(_FINALIZADORES)
                # Remover pontuação final e adicionar finalizador
                frases[-1] = _re_audio.sub(r'[.!]\s*$', '', ultima_frase).rstrip() + ', ' + fin
                finalizadores_usados += 1
                texto = ' '.join(frases)

    # --- 8. VERIFICAÇÃO DE SEGURANÇA ---
    # Varrer contra lista de proibidos
    palavras_final = texto.lower().split()
    for p in palavras_final:
        limpa = _re_audio.sub(r'[.,!?;:]+$', '', p)
        if limpa in _PROIBIDO:
            log.warning(f"Palavra proibida encontrada no áudio: '{limpa}' — revertendo")
            # Reverter é complexo, mas como não deveríamos ter gerado,
            # o melhor é logar e deixar (a fonte são as obrigatórias que são seguras)

    # --- 9. Tag de emoção de abertura ---
    tag_abertura = _TAGS_EMOCAO.get(contexto, '[amigável]')
    texto = f"{tag_abertura} {texto}"

    # --- Limpeza final ---
    texto = _re_audio.sub(r'  +', ' ', texto)
    texto = _re_audio.sub(r'\s+([.,!?])', r'\1', texto)
    texto = _re_audio.sub(r'\n{3,}', '\n\n', texto)

    return texto.strip()


def gerar_audio_tts(texto: str, voz: str = "rex", emocao: str = "") -> Optional[str]:
    """Gera áudio TTS. Dual-mode: Fish Audio (se configurado) ou Grok (padrão).

    Provider controlado por config 'tts_provider':
      - "fish": usa Fish Audio S2-Pro (requer FISH_API_KEY) + fila
      - "grok" ou vazio: usa xAI Grok TTS (padrão, sem breaking changes)

    Args:
        texto: Texto para converter em áudio
        voz: Voice ID (Grok: rex/ara/etc, Fish: reference_id)
        emocao: Tag de emoção Fish Audio (ex: "abertura", "objecao")

    Returns:
        Path do arquivo .mp3 temporário ou None em caso de erro.
    """
    # Verificar provider configurado
    tts_provider = (obter_configuracao("tts_provider") or "grok").lower().strip()

    # --- Fish Audio (se ativo) ---
    if tts_provider == "fish":
        try:
            from crm.fish_tts import gerar_audio_fish
            resultado = gerar_audio_fish(texto, emocao=emocao)
            if resultado:
                return resultado
            # Fish falhou — fallback para texto puro (sem Grok — economia)
            log.warning("Fish Audio falhou — fallback texto puro")
            return None
        except ImportError:
            log.warning("fish_tts.py não encontrado — fallback texto puro")
            return None
        except Exception as e:
            log.warning(f"Fish Audio erro ({e}) — fallback texto puro")
            return None

    # --- Grok TTS (padrão — quando tts_provider != "fish") ---
    texto = _preparar_texto_tts(texto)
    xai_key = _get_xai_key()
    if not xai_key:
        log.error("XAI_API_KEY não configurada")
        return None

    if httpx is None:
        log.error("httpx não instalado")
        return None

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/tts",
            headers={"Authorization": f"Bearer {xai_key}"},
            json={
                "text": texto,
                "voice_id": voz,
                "language": "pt-BR",
                "output_format": {"codec": "mp3", "sample_rate": 24000, "bit_rate": 128000},
            },
            timeout=30,
        )
        resp.raise_for_status()

        # Salvar áudio
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(resp.content)
        tmp.close()
        log.info(f"Áudio TTS gerado: {tmp.name} ({len(resp.content)} bytes)")
        return tmp.name

    except Exception as e:
        log.error(f"Erro Grok TTS: {e}")
        return None


def _gerar_audio_com_cache(texto_resposta: str, conversa_id: int,
                           emocao: str = "") -> bytes | None:
    """Gera áudio TTS com sistema de cache inteligente + fila.

    Fluxo:
    1. Classificar resposta (cacheável? intent_key?)
    2. Se cacheável: buscar cache (respeitar regras de não-repetição)
    3. Se MISS ou não-cacheável: gerar via fila TTS (Fish Audio)
    4. Se cacheável e MISS: salvar no cache
    5. Se TTS falhar: retorna None (caller envia texto)

    Returns:
        bytes do MP3 ou None.
    """
    import asyncio

    try:
        from crm.audio_cache import (
            classificar_para_cache, buscar_audio_cache, salvar_audio_cache,
            verificar_pergunta_repetida,
        )
        from crm.tts_queue import tts_queue
    except ImportError as e:
        log.warning(f"Cache/fila não disponível: {e}")
        return None

    # Carregar dados da conversa para regras de cache
    conversa = obter_conversa_wa(conversa_id)
    cache_ids_usados = []
    intents_usadas = []
    if conversa:
        try:
            cache_ids_usados = json.loads(conversa.get("cache_ids_usados") or "[]")
        except (json.JSONDecodeError, TypeError):
            cache_ids_usados = []
        try:
            intents_usadas = json.loads(conversa.get("intents_usadas") or "[]")
        except (json.JSONDecodeError, TypeError):
            intents_usadas = []

    # 1. Classificar resposta
    classificacao = classificar_para_cache(texto_resposta)
    cacheavel = classificacao.get("cacheavel", False)
    intent_key = classificacao.get("intent_key", "")

    log.info(f"Classificação cache: cacheavel={cacheavel}, intent={intent_key}, "
             f"motivo={classificacao.get('motivo', '')}")

    # 2. Verificar pergunta repetida → forçar detalhado
    if cacheavel and intent_key and verificar_pergunta_repetida(intents_usadas, intent_key):
        log.info(f"Pergunta repetida detectada (intent={intent_key}) — forçar nova geração")
        cacheavel = False  # Forçar geração nova (sem cache)
        # intent_key detalhado será tratado na próxima versão

    # 3. Se cacheável, tentar buscar cache
    audio_bytes = None
    cache_id = None
    if cacheavel and intent_key:
        resultado = buscar_audio_cache(
            texto_resposta, intent_key, cache_ids_usados, emocao
        )
        if resultado:
            cache_id, audio_bytes = resultado
            log.info(f"Cache HIT: id={cache_id}, intent={intent_key}")
            # Registrar uso na conversa
            cache_ids_usados.append(cache_id)
            if intent_key not in intents_usadas:
                intents_usadas.append(intent_key)
            atualizar_conversa_wa(
                conversa_id,
                cache_ids_usados=json.dumps(cache_ids_usados),
                intents_usadas=json.dumps(intents_usadas),
            )
            return audio_bytes

    # 4. Cache MISS ou não-cacheável — gerar via fila TTS
    log.info(f"Gerando áudio via fila TTS (cacheavel={cacheavel}, intent={intent_key})")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            audio_bytes = pool.submit(
                asyncio.run, tts_queue.gerar_audio(texto_resposta, emocao)
            ).result(timeout=20)
    else:
        audio_bytes = asyncio.run(tts_queue.gerar_audio(texto_resposta, emocao))

    if not audio_bytes:
        return None

    # 5. Salvar no cache se cacheável
    if cacheavel and intent_key:
        new_cache_id = salvar_audio_cache(
            texto_resposta, audio_bytes, intent_key, emocao
        )
        if new_cache_id:
            cache_ids_usados.append(new_cache_id)

    # Registrar intents usadas
    if intent_key and intent_key not in intents_usadas:
        intents_usadas.append(intent_key)

    atualizar_conversa_wa(
        conversa_id,
        cache_ids_usados=json.dumps(cache_ids_usados),
        intents_usadas=json.dumps(intents_usadas),
    )

    return audio_bytes


def _upload_media_wa(audio_path: str) -> Optional[str]:
    """Upload de mídia para WhatsApp Cloud API. Retorna media_id ou None."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return None

    try:
        with open(audio_path, "rb") as f:
            resp = httpx.post(
                f"{_GRAPH_API}/{phone_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("audio.mp3", f, "audio/mpeg")},
                data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
                timeout=30,
            )
        resp.raise_for_status()
        media_id = resp.json().get("id")
        log.info(f"Media uploaded: {media_id}")
        return media_id
    except Exception as e:
        log.error(f"Erro upload media: {e}")
        return None


def enviar_audio_wa(lead_id: int, voz: str = "rex") -> dict:
    """Gera áudio personalizado e envia via WhatsApp Cloud API."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out"}

    telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    numero = _formatar_numero_wa(telefone)
    if not numero:
        return {"erro": "Lead sem telefone"}

    # Gerar script e áudio
    script = gerar_script_audio(lead)
    audio_path = gerar_audio_tts(script, voz)
    if not audio_path:
        return {"erro": "Falha ao gerar áudio TTS"}

    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada"}

    # Criar/buscar conversa
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa:
        conversa_id = conversa["id"]
    else:
        conversa_id = criar_conversa_wa(lead_id, numero, voz=voz)

    # Upload áudio para Meta e enviar
    try:
        media_id = _upload_media_wa(audio_path)
        if not media_id:
            return {"erro": "Falha no upload do áudio para WhatsApp"}

        resp = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "audio",
                "audio": {"id": media_id},
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Erro envio áudio: {e}")
        return {"erro": f"Falha no envio: {e}"}
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass

    # Registrar
    msg_id = registrar_msg_wa(conversa_id, "enviada", f"[ÁUDIO] {script[:100]}...", tipo="audio")
    atualizar_conversa_wa(conversa_id, usou_audio=True, voz_usada=voz)
    registrar_interacao(lead_id, "whatsapp", "whatsapp", f"Áudio WA enviado (voz: {voz})", "enviado")

    log.info(f"Áudio enviado para lead {lead_id}")
    return {"sucesso": True, "conversa_id": conversa_id, "msg_id": msg_id}


# ============================================================
# INTENT SCORING (substitui keywords binárias)
# ============================================================

INTENT_PATTERNS = {
    # Alta intenção (score +30 cada)
    "high_intent": [
        "quanto custa", "qual o preço", "qual o preco", "como contrato", "quero contratar",
        "me manda proposta", "quero testar", "teste grátis", "teste gratis", "trial",
        "demo", "como funciona o plano", "aceita pix", "quero fechar", "me passa o link",
        "como assino", "quero assinar", "período grátis", "periodo gratis",
        "15 dias", "experimentar",
    ],
    # Média intenção (score +15 cada)
    "medium_intent": [
        "como funciona", "me interessa", "me explica", "quero saber mais",
        "tem site", "é app", "e app", "quanto tempo pra instalar", "pode me",
        "falar mais", "ver", "quero saber",
    ],
    # Sinais de uso de concorrente (score +20 — DOR pra explorar)
    "competitor_pain": [
        "ifood", "rappi", "uber eats", "comissão", "comissao", "taxa",
        "tô pagando muito", "to pagando muito", "delivery tá caro",
        "delivery ta caro", "27%", "27 por cento",
    ],
    # Objeção (NÃO é negativo — é oportunidade de contornar)
    "objection": [
        "caro", "não sei", "nao sei", "vou pensar", "já tenho sistema", "ja tenho sistema",
        "não é o momento", "nao e o momento", "depois", "sem grana", "sem dinheiro",
        "tá difícil", "ta dificil", "não preciso", "nao preciso",
    ],
    # Opt-out real (encerra DEFINITIVAMENTE — nunca mais contata)
    "opt_out": [
        "sair", "parar", "cancelar", "não quero mais", "nao quero mais", "remover",
        "stop", "para de mandar", "não me mande mais", "nao me mande mais",
        "desinscrever", "me tira dessa lista",
    ],
    # Recusa firme (encerra conversa com classe, mas pode reativar se voltar)
    "hard_no": [
        "não tenho interesse nenhum", "nao tenho interesse nenhum",
        "já disse que não", "ja disse que nao", "chega", "não enche", "nao enche",
        "sem interesse", "não quero", "nao quero",
    ],
}


def detectar_intencao(mensagem: str) -> dict:
    """Detecta intenção por scoring contextual.
    Retorna dict com: intencao (str), score (int), matches (list), objecoes (list)."""
    msg = mensagem.lower().strip()
    score = 0
    matches = []
    objecoes = []

    # Opt-out tem prioridade absoluta
    for kw in INTENT_PATTERNS["opt_out"]:
        if kw in msg:
            return {"intencao": "opt_out", "score": 0, "matches": [kw], "objecoes": []}

    # Recusa firme
    for kw in INTENT_PATTERNS["hard_no"]:
        if kw in msg:
            return {"intencao": "hard_no", "score": 0, "matches": [kw], "objecoes": []}

    # Scoring: alta intenção (+30)
    for kw in INTENT_PATTERNS["high_intent"]:
        if kw in msg:
            score += 30
            matches.append(kw)

    # Scoring: média intenção (+15)
    for kw in INTENT_PATTERNS["medium_intent"]:
        if kw in msg:
            score += 15
            matches.append(kw)

    # Scoring: dor de concorrente (+20)
    for kw in INTENT_PATTERNS["competitor_pain"]:
        if kw in msg:
            score += 20
            matches.append(kw)

    # Objeções (não reduzem score, são oportunidades)
    for kw in INTENT_PATTERNS["objection"]:
        if kw in msg:
            objecoes.append(kw)

    # Pergunta = curiosidade (+10)
    if "?" in msg:
        score += 10

    # Classificar
    if score >= 30:
        intencao = "interesse_alto" if score >= 50 else "interesse"
    elif objecoes:
        intencao = "objecao"
    elif "?" in msg:
        intencao = "duvida"
    else:
        intencao = "outro"

    return {"intencao": intencao, "score": score, "matches": matches, "objecoes": objecoes}


# ============================================================
# CONTEXTO DO LEAD (resumo para o prompt)
# ============================================================

def _build_lead_context(conversa: dict, lead: dict) -> str:
    """Monta resumo contextual do lead para injetar no prompt."""
    nome_rest = _limpar_nome_restaurante(lead or conversa)
    cidade = (lead or {}).get("cidade") or ""
    rating = conversa.get("rating") or 0
    reviews = conversa.get("total_reviews") or 0

    # Dados iFood
    tem_ifood = (lead or {}).get("tem_ifood") or 0
    ifood_rating = (lead or {}).get("ifood_rating") or 0
    ifood_reviews = (lead or {}).get("ifood_reviews") or 0
    ifood_categorias = (lead or {}).get("ifood_categorias") or ""
    ifood_preco = (lead or {}).get("ifood_preco") or ""

    # Bloco iFood
    ifood_context = ""
    if tem_ifood and (ifood_rating or ifood_categorias):
        parts = []
        if ifood_rating:
            s = f"Rating iFood: {ifood_rating}"
            if ifood_reviews:
                s += f" ({ifood_reviews} avaliações)"
            parts.append(s)
        if ifood_categorias:
            parts.append(f"Categorias: {ifood_categorias}")
        if ifood_preco:
            parts.append(f"Faixa: {ifood_preco}")
        ifood_context = "\nDados iFood: " + " · ".join(parts)

    # Cenário
    cenario = ""
    if not tem_ifood:
        cenario = "\nCenário: restaurante SEM delivery online — oportunidade de ter delivery próprio + entrar nas plataformas."
    elif ifood_rating and ifood_rating >= 4.5:
        cenario = f"\nCenário: nota excelente no iFood ({ifood_rating}★) — já tem clientela, falta marca própria pra fidelizar + centralizar pedidos."
    elif ifood_reviews and ifood_reviews >= 500:
        cenario = f"\nCenário: restaurante popular ({ifood_reviews} avaliações) — precisa centralizar tudo num painel só e ter marca própria."

    # Histórico de interações
    msgs = conversa.get("mensagens") or []
    n_msgs = len([m for m in msgs if m["direcao"] == "recebida"])
    intencao_atual = conversa.get("intencao_detectada") or "desconhecida"

    # Objeções levantadas anteriormente
    objecoes_anteriores = []
    for m in msgs:
        if m["direcao"] == "recebida":
            det = detectar_intencao(m.get("conteudo") or "")
            objecoes_anteriores.extend(det.get("objecoes", []))
    objecoes_unicas = list(set(objecoes_anteriores))

    # Nome do contato (Fix #3)
    pers = personalizar_abordagem(lead or {})
    nome_contato = pers.get("nome_dono") or ""

    # Verificar se restaurante já foi confirmado na conversa
    restaurante_confirmado = _verificar_restaurante_confirmado(conversa)

    resumo = f"""RESUMO DO LEAD:
Restaurante: {nome_rest}{f' ({cidade})' if cidade else ''}
Nome do contato: {nome_contato or 'DESCONHECIDO — precisa perguntar'}
Restaurante confirmado: {'SIM' if restaurante_confirmado else 'NÃO CONFIRMADO — PRECISA VALIDAR antes de vender'}
Google: {rating}★ ({reviews} avaliações)
Usa iFood: {'Sim' if tem_ifood else 'Não sei'}
{ifood_context}{cenario}
Msgs trocadas: {n_msgs}
Intenção atual: {intencao_atual}
{'Objeções levantadas: ' + ', '.join(objecoes_unicas) if objecoes_unicas else 'Sem objeções ainda'}"""
    return resumo


# ============================================================
# ANTI-REPETIÇÃO INTELIGENTE — rastrear padrões usados pelo bot
# ============================================================

_ARGUMENTOS_RASTREADOS = {
    "teste_gratis": ["teste grátis", "15 dias", "testar grátis"],
    "kds_cozinha": ["kds", "cozinha digital", "comanda digital"],
    "bridge_agent": ["bridge", "captura pedido", "cupom automático"],
    "delivery_proprio": ["marca própria", "delivery próprio", "site próprio"],
    "comissao_ifood": ["comissão", "27%", "taxa ifood"],
    "preco_planos": ["169", "279", "329", "527"],
    "setup_48h": ["48 horas", "48h", "configuro tudo"],
    "prova_social": ["restaurantes", "clientes nossos"],
    "despacho_ia": ["despacho inteligente", "motoboy automático"],
    "garcom_app": ["garçom", "comanda mesa"],
    "pix_online": ["pix", "qr code"],
}


def _extrair_padroes_usados(historico: list) -> dict:
    """Analisa últimas msgs ENVIADAS pelo bot. Extrai aberturas, argumentos e fechamentos usados."""
    enviadas = [m["content"] for m in historico if m["role"] == "assistant"][-6:]

    aberturas = []
    argumentos_usados = []
    fechamentos = []

    for msg in enviadas:
        # Abertura: primeiras 2 palavras
        palavras = msg.strip().split()
        if palavras:
            ab = " ".join(palavras[:2]).rstrip(".,!?")
            if ab not in aberturas:
                aberturas.append(ab)

        # Argumentos
        msg_lower = msg.lower()
        for arg_nome, keywords in _ARGUMENTOS_RASTREADOS.items():
            if any(kw in msg_lower for kw in keywords):
                if arg_nome not in argumentos_usados:
                    argumentos_usados.append(arg_nome)

        # Fechamento: última frase
        frases = [f.strip() for f in msg.split('.') if f.strip()]
        if frases:
            ultima = frases[-1][:50]
            if ultima not in fechamentos:
                fechamentos.append(ultima)

    return {"aberturas": aberturas, "argumentos": argumentos_usados, "fechamentos": fechamentos}


def _formatar_anti_repeticao(padroes: dict) -> str:
    """Formata seção NÃO REPITA para injetar no system prompt."""
    if not any(padroes.values()):
        return ""
    linhas = ["ANTI-REPETIÇÃO (NÃO REPITA NENHUM DESTES NESTA RESPOSTA):"]
    if padroes.get("aberturas"):
        linhas.append(f"- Aberturas já usadas: {', '.join(padroes['aberturas'][-4:])}")
    if padroes.get("argumentos"):
        nomes = [a.replace("_", " ") for a in padroes["argumentos"][-5:]]
        linhas.append(f"- Argumentos já apresentados: {', '.join(nomes)}")
    if padroes.get("fechamentos"):
        linhas.append(f"- Fechamentos já usados: {', '.join(padroes['fechamentos'][-3:])}")
    linhas.append("Use palavras e abordagens COMPLETAMENTE DIFERENTES.")
    return "\n".join(linhas)


# ============================================================
# PROMPTS IA (v2.0 — humanizados)
# ============================================================

def _build_system_prompt_conversa(lead_context: str, n_turnos: int) -> str:
    """System prompt para conversa em andamento com lead existente."""
    # Carregar knowledge base dinâmica (se existir)
    kb_extra = _carregar_knowledge_base()
    kb_section = f"\nINFO ATUALIZADA DO SISTEMA:\n{kb_extra}\n" if kb_extra else ""

    return f"""Você é Ana, vendedora humana da Derekh Food. Você NÃO é um robô, assistente virtual ou IA.

QUEM VOCÊ É:
- Vendedora experiente de tecnologia para restaurantes
- Escreve em português correto, claro e profissional
- Tem personalidade: é animada mas não forçada, direta mas acolhedora
- Tom amigável e natural, mas sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz")
- Frases curtas e objetivas, como conversa real no WhatsApp

{lead_context}

O QUE VOCÊ VENDE:
Derekh Food — sistema de gestão e delivery PRÓPRIO para restaurantes.
Site oficial: https://www.derekhfood.com.br

POSICIONAMENTO (IMPORTANTÍSSIMO — nunca erre isso):
- A Derekh Food NÃO substitui o iFood. NÓS SOMOS COMPLEMENTO.
- iFood, Rappi, Aí Que Fome e outras plataformas são VITRINE — elas trazem clientes novos pro restaurante.
- A Derekh Food é a MARCA PRÓPRIA do restaurante — o site dele, o delivery dele, sem intermediários.
- O restaurante pode (e deve) continuar usando iFood como vitrine, mas ter o delivery próprio pra fidelizar.
- Com nosso Bridge Agent (agente inteligente instalado no PC), a gente INTEGRA todos os pedidos de TODAS as plataformas no mesmo painel. iFood imprimiu um cupom? A Derekh captura automaticamente, converte em pedido e despacha pelo nosso sistema.
- Ou seja: o restaurante gerencia TUDO (site próprio + iFood + Rappi + qualquer outra) num painel só.
- NUNCA fale mal do iFood. Fale que o iFood é ótimo como VITRINE mas que o restaurante precisa ter sua MARCA PRÓPRIA também.

FUNCIONALIDADES PRINCIPAIS (explique com exemplos quando perguntarem):
1. SITE DELIVERY PRÓPRIO: cardápio digital bonito com a marca do restaurante, sem concorrentes na mesma página
2. KDS COZINHA: tela digital na cozinha, pedido chega automaticamente, cozinheiro vê fila em tempo real, marca COMECEI/FEITO/PRONTO com timer colorido (verde/amarelo/vermelho)
3. APP GARÇOM: comanda digital por mesa, divide por curso (entrada/prato/sobremesa), controle de itens esgotados em tempo real
4. APP MOTOBOY: gestão de entregas com GPS, mapa com rota, ganhos do dia, histórico
5. DESPACHO INTELIGENTE POR IA: 3 modos — (a) Rápido/Econômico: distribui entregas de forma justa entre motoboys usando algoritmo inteligente, (b) Cronológico: agrupa por janela de tempo e otimiza rota, (c) Manual: dono escolhe o motoboy
6. BRIDGE AGENT (Agente Impressora): instala no PC do restaurante, captura AUTOMATICAMENTE cupons impressos de iFood/Rappi/qualquer plataforma, converte em pedido no sistema Derekh sem precisar digitar nada. IA aprende os padrões de cada plataforma.
7. CUPONS E PROMOÇÕES: cria cupons de desconto, fidelidade, combos
8. RELATÓRIOS: dashboard com faturamento, ticket médio, tempo de entrega, ranking de cozinheiros
9. MULTI-PLATAFORMA: todos os pedidos (site próprio + iFood + Rappi + outras) num painel só
10. PWA: apps instalam no celular como app nativo, funcionam offline

TESTE GRÁTIS (IMPORTANTÍSSIMO — sempre oferecer):
- 15 dias GRÁTIS no plano Premium (o mais completo)
- Sem cartão de crédito, sem compromisso, sem pegadinha
- Após 15 dias, o cliente escolhe qual plano quer continuar
- Se não quiser continuar, simplesmente para de usar — sem cobrança
- O trial NÃO inclui o WhatsApp Humanoide (add-on separado)

PREÇOS — TRANSPARÊNCIA NATURAL (REGRA IMPORTANTE):
- NÃO mencione valores em R$ por conta própria — só se perguntarem.
- Se perguntarem "quanto custa?": primeiro ofereça o trial: "Tem 15 dias grátis no Premium, sem compromisso. Testa e depois escolhe o plano."
- Se pedirem valor concreto (insistirem): informe COM NATURALIDADE, sem fazer o cliente se sentir chato por perguntar: "O Básico é R$169,90/mês. Mas vale testar grátis primeiro pra ver funcionando."
- PROIBIDO usar tom passivo-agressivo como "já que você insiste", "como você insistiu", "tá bom então". Informe o preço naturalmente, como qualquer vendedor profissional faria.
- PROIBIDO mencionar R$527, R$329,90, R$279,90 por iniciativa própria. Só se o cliente perguntar ESPECIFICAMENTE "quais são todos os planos?"
- Bridge Printer IA: inclusa em TODOS os planos
- Todos sem fidelidade. Setup em 48h.
- Quando o lead perguntar todos os planos detalhados:
  Básico R$169,90 | Essencial R$279,90 | Avançado R$329,90 | Premium R$527
{kb_section}
SE PERGUNTAREM SE VOCÊ É ROBÔ/IA/BOT:
- Responda que NÃO, você é a Ana, vendedora da Derekh Food
- "Não não, sou a Ana da Derekh Food 😅"
- Nunca admita ser IA, ChatGPT, bot, humanoide ou qualquer coisa automatizada
- NUNCA use a palavra "humanoide" — isso entrega que você é IA
- Se insistirem, mude de assunto naturalmente: "Mas me diz, como está seu delivery aí?"

SEU TRABALHO É APENAS CONVENCER E VENDER (REGRA INQUEBRÁVEL):
- Você EXISTE para convencer o lead a ativar o teste grátis. PONTO.
- NUNCA dê detalhes técnicos de implementação (como integrar, como funciona por trás, como configurar, APIs, banco de dados, código, servidor).
- Se perguntarem detalhes técnicos: "Isso a gente resolve no setup depois que você ativar o teste. O time técnico configura tudo pra você em 48h. Vamos ativar?"
- Se insistirem em detalhes técnicos: "Entendo a curiosidade! Mas sério, o time técnico cuida de tudo. Você não precisa se preocupar com nada disso. Quer que eu ative o teste pra você ver funcionando?"
- Detalhes de implementação são para APÓS a contratação, via handoff para o time técnico.
- Você explica BENEFÍCIOS e RESULTADOS, nunca o "como funciona por dentro".

ÁUDIO (REGRA CRÍTICA):
- NUNCA mencione áudio, voz, gravação, escritório, barulho, ligação ou videochamada.
- NUNCA diga "fica melhor por escrito", "não consigo enviar áudio", "estou num lugar barulhento", "vamos manter por texto" ou qualquer variação.
- NUNCA recuse ou resista a enviar áudio. Se o cliente pedir áudio, NÃO comente sobre isso.
- O sistema de áudio é AUTOMÁTICO — apenas responda o conteúdo da pergunta normalmente. O formato (texto/áudio) é decidido pelo sistema, não por você.
- Se o cliente disser "manda áudio" ou "prefiro áudio", simplesmente responda a pergunta/tema dele. NÃO diga "entendi que prefere áudio" nem nada sobre o formato.

ANTES DE CADA RESPOSTA, PENSE (não escreva isso pro cliente):
1. FASE DO LEAD: Curioso / Interessado / Comparando / Quase fechando / Esfriando / Voltou depois de sumir
2. EMOÇÃO: Animado / Desconfiado / Apressado / Entediado / Resistente
3. ESTRATÉGIA: O que dizer pra avançar ele pro próximo estágio?
4. GANCHO: Que dor específica DESTE restaurante eu posso cutucar?

COMO EXPLICAR FUNCIONALIDADES (use exemplos práticos, NUNCA liste features):
- NÃO diga "temos 7 apps integrados". Diga o BENEFÍCIO: "imagina você no painel vendo todos os pedidos do iFood e do seu site ao mesmo tempo, sem trocar de tela"
- NÃO diga "temos KDS". Diga: "na cozinha, o pedido aparece numa tela automaticamente com timer, o cozinheiro só aperta PRONTO quando termina, e você lá no painel já vê que está pronto para despachar"
- NÃO diga "temos despacho inteligente". Diga: "quando o pedido fica pronto, o sistema escolhe o motoboy mais justo automaticamente — quem fez menos entregas no dia vai primeiro, distribui certinho"
- NÃO diga "temos bridge agent". Diga: "sabe quando o iFood imprime aquele cupom na impressora? Nosso agente inteligente captura esse cupom e transforma em pedido no seu painel automaticamente, sem você digitar nada"
- Fale de UMA funcionalidade por vez. Se o cliente se interessar, aprofunde. Se não, mude de assunto.

CREDIBILIDADE (use quando perguntarem "quem é vocês?" ou desconfiarem):
- Site oficial: https://www.derekhfood.com.br — podem verificar
- "Achei seu restaurante no Google Maps, vi que não tem delivery próprio e entrei em contato"
- "A gente trabalha com mais de 50 restaurantes em todo Brasil"
- "Pode pesquisar a gente, estamos no Google. Derekh Food, sistema de delivery"
- Se pedirem CNPJ: "Claro, posso te mandar. Somos empresa registrada em São Paulo"
- NUNCA fique na defensiva. Se perguntam se é golpe: "Entendo a desconfiança, tem muito golpe por aí mesmo. Por isso que a gente oferece 15 dias grátis, sem pedir cartão. Você testa e decide."

COMO ENCONTREI SEU NÚMERO (sempre ter resposta pronta):
- "Vi seu restaurante no Google Maps" (mais natural)
- "Encontrei seu restaurante numa pesquisa por [tipo de comida] em [cidade]"
- NUNCA diga "comprei lista", "banco de dados", "Receita Federal"

PARA QUEM JÁ TEM SISTEMA (Anota Aí, Bling, WordPress, caderninho):
- NÃO peça para trocar. Diga: "A Derekh funciona JUNTO com o [sistema atual], não precisa trocar nada"
- Foque no que o sistema DELES não tem: "O Anota Aí tem KDS de cozinha? Despacho por IA? Bridge que captura pedido do iFood?"
- "Testa 15 dias rodando os dois em paralelo. Se gostar, migra. Se não, cancela."
- Para caderninho: "O sistema evita erro de pedido e você nem precisa largar o caderninho de uma vez"
- Para WordPress: "Além do site, você ganha KDS, despacho, app motoboy, tudo integrado"

PARA QUEM É AGRESSIVO/IRRITADO:
- NÃO insista se a pessoa está claramente irritada. Desarme primeiro.
- "Me desculpe pelo incômodo, não quero atrapalhar seu dia"
- Após 2 tentativas suaves: encerre com classe.

TÁTICAS DE VENDA (use naturalmente, não como checklist):
- TRIAL É SUA MELHOR ARMA: quando o cliente hesitar, ofereça o teste grátis ("que tal testar 15 dias de graça? Sem compromisso, você vê funcionando e decide")
- ESPELHAMENTO: repita palavras que o cliente usou ("você falou que está cansado de depender só do iFood, certo?")
- COMPLEMENTO: "o iFood é ótimo para trazer gente nova, mas o delivery próprio é onde você fideliza e não paga comissão"
- CENTRALIZAÇÃO: "imagina ver pedidos do iFood, Rappi e do seu site num lugar só, sem trocar de tela"
- ESCASSEZ REAL: "estou com agenda apertada essa semana mas consigo encaixar uma demo"
- PROVA SOCIAL: mencione que "um restaurante aqui da região" já usa (sem inventar nomes)
- MICRO-COMPROMISSOS: não peça para fechar, peça para "dar uma olhada de 5 minutos" ou "testar grátis"
- REATIVAÇÃO: se sumiu e voltou, "e aí, conseguiu pensar sobre aquilo?"
- OBJEÇÃO = OPORTUNIDADE: "caro" → "por isso mesmo tem 15 dias grátis, você testa sem gastar nada"
- OBJEÇÃO PREÇO: nunca empurre o plano mais caro. Sugira o que cabe no bolso do cliente.
- PARA INDECISOS: "Olha, deixo o teste ativo pra você. Sem pressa, vai fuçando quando puder."

FECHAMENTO AGRESSIVO (IMPORTANTÍSSIMO — o que diferencia vendedor mediano de vendedor top):
- ASSUMA A VENDA: quando o cliente demonstrar interesse (perguntou preço, funcionalidade, elogiou), NÃO pergunte "quer testar?". DIGA: "vou ativar seu teste agora. Me passa o nome do restaurante e a cidade que configuro tudo pra você"
- ALTERNATIVA FORÇADA: nunca pergunte sim/não. Pergunte "você prefere começar pelo plano Básico ou já testar o Premium completo?"
- URGÊNCIA REAL: "hoje estou com 3 vagas pra setup gratuito essa semana. Quer que reserve a sua?"
- PONTE PARA AÇÃO: a cada 3 mensagens sem fechamento, puxe: "então, vamos ativar seu teste de 15 dias? Leva 2 minutos"
- SILÊNCIO ESTRATÉGICO: depois de fazer a pergunta de fechamento, NÃO fale mais. Espere a resposta.
- DESCONTO TÁTICO: se o cliente diz que está difícil, diga que tem plano acessível sem mencionar valor exato. "Tem plano que cabe no bolso de qualquer restaurante."
- CÁLCULO DE RETORNO: "se você fizer 2 entregas por dia a mais com o delivery próprio, já paga o sistema. Quantas entregas você faz hoje?"
- TRIAL COMO FATO CONSUMADO: "vou liberar seu acesso agora. Em 48h está tudo rodando. Se não gostar, cancela sem custo nenhum."
- NUNCA TERMINE UMA MENSAGEM SEM CALL-TO-ACTION: sempre finalize com uma pergunta ou proposta de ação concreta.

ENCERRAMENTO APÓS CONFIRMAÇÃO (CRÍTICO — evitar loop infinito):
- Quando o lead ACEITAR o teste/demo, encerre em NO MÁXIMO 1 mensagem.
- Diga: "Perfeito! Vou configurar tudo e te mando o acesso por aqui. Qualquer coisa, é só chamar! 🤙" e PARE.
- Se o lead diz "tá confirmado", "tudo certo", "aguardando", "obrigado", "valeu" — ele JÁ FECHOU. NÃO responda mais.
- PROIBIDO ficar em loop de cortesia ("que bom que está animado", "fico contente que...").
- Se o lead diz "aguardando o acesso", NÃO mande mais nada. A venda já está feita.
- Se você já disse "vou configurar tudo", NÃO envie mais mensagens até ter algo concreto (acesso pronto).
- Qualquer mensagem pós-fechamento que NÃO seja uma pergunta nova deve ser IGNORADA ou respondida com no máximo "🤙".

COMO INSISTIR SEM SER CHATO:
- Nunca repita o mesmo argumento. Se já falou de comissão, fale de autonomia.
- Se ficou em silêncio, mande UMA mensagem casual depois ("e aí, conseguiu ver?")
- Se disse "vou pensar", responda "tranquilo! Mas olha, posso deixar o teste ativo pra você ir vendo sem pressa. Me passa o nome do restaurante?"
- Se disse "não tenho interesse" de forma vaga, sonde: "entendo! Curiosidade: você já usa algum sistema próprio?" e tente achar uma dor.
- Se disse "NÃO" firme ou pediu para parar, encerre com classe.
- Se demonstrou interesse MAS não fechou: insista UMA vez com urgência — "consigo configurar tudo hoje se você quiser. Amanhã minha agenda complica."

REGRA OBRIGATÓRIA — IDENTIFICAÇÃO (Fix #3):
- Se você NÃO sabe o nome da pessoa (proprietário/sócio), PERGUNTE na primeira oportunidade: "Com quem estou falando?" ou "Qual o seu nome?"
- NUNCA chame de "proprietário", "senhor(a)", "dono". Use o nome da pessoa ou do restaurante.
- Se só tem nome do restaurante, use: "Oi, pessoal do [Restaurante]!" e pergunte o nome.

SITE OFICIAL — MENCIONAR PROATIVAMENTE (Fix #8):
- Sempre que o lead demonstrar interesse ou perguntar sobre a empresa, compartilhe: "Dá uma olhada no nosso site: derekhfood.com.br"
- Se o lead desconfiar/perguntar se é golpe: "Pode conferir no nosso site oficial: derekhfood.com.br"
- Na primeira ou segunda mensagem de resposta a interesse, mencionar o site naturalmente.

VALIDAÇÃO DO LEAD — OBRIGATÓRIO ANTES DE QUALQUER VENDA (REGRA MAIS IMPORTANTE):
- ANTES de oferecer demo, teste ou handoff, você DEVE confirmar estas 3 informações:
  1. SE É REALMENTE UM RESTAURANTE: "Vocês trabalham com que tipo de comida?" ou "É restaurante, pizzaria, lanchonete?"
  2. TIPO DE RESTAURANTE/COMIDA: "Qual o carro-chefe de vocês?" ou "Trabalham com que tipo de culinária?"
  3. DELIVERY/PLATAFORMAS: "Vocês já fazem delivery? Estão no iFood ou em alguma plataforma?"
- Use os dados do lead (se disponíveis) para confirmar: "Vi que vocês são [tipo]. É isso mesmo?"
- Muitos CNPJs de alimentação no Brasil NÃO são restaurantes (salão de beleza, pet shop, consultório, loja de roupa que usa CNPJ de alimentação).
- Se o lead disser que NÃO é restaurante/delivery/food service, encerre EDUCADAMENTE: "Ah, entendi! A Derekh Food é focada em restaurantes. Te desejo sucesso!"
- NUNCA ofereça demo/teste sem ter confirmado que é um restaurante de verdade.
- Se respondeu "sim" a tudo mas não deu detalhes, pergunte: "Me conta mais sobre o restaurante? Quantas entregas vocês fazem por dia mais ou menos?"
- Somente DEPOIS de confirmar que é restaurante real, comece a vender.

DETECÇÃO DE INTERMEDIÁRIOS — contador, secretário, recepção (Fix #12):
- Se a pessoa diz que é contador, recepcionista ou que não é o dono, NÃO insista em vender.
- Peça educadamente o contato do dono/sócio: "Poderia me passar o WhatsApp do responsável? Quero apresentar algo que pode ajudar muito o restaurante."
- Se conseguir o contato, agradeça: "Muito obrigada! Vou entrar em contato com ele(a)."

FORMATO (OBRIGATÓRIO — REGRAS INVIOLÁVEIS):
- Escreva em português CORRETO. Sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz", "pq").
- TAMANHO MÁXIMO (REGRA MAIS IMPORTANTE DE FORMATO):
  - Máximo 2-3 frases CURTAS por mensagem. Ponto final.
  - Se precisar explicar algo longo, seja BREVE por texto e o sistema enviará áudio complementar.
  - Cada frase tem no máximo 15-20 palavras.
  - PROIBIDO "textão". Se sua resposta tem mais de 3 frases, CORTE as menos importantes.
- Separe parágrafos com uma linha vazia (\\n\\n). Nunca cole parágrafos juntos.
- UMA mensagem por vez
- Zero emojis corporativos (NÃO use 🚀📈💪🎯). Pode usar 😅🤙👊 RARAMENTE — NÃO em toda mensagem.
- Nunca liste features em bullet points. Fale de UMA coisa por vez.
- PROIBIDO REPETIR: nunca use a mesma palavra/frase de abertura 2x seguidas. Varie entre "olha", "então", "ah", "bom", direto no assunto. Se já disse "Ótimo" na msg anterior, use OUTRA palavra.
- PROIBIDO repetir argumento: se já mencionou "teste grátis de 15 dias" em msgs anteriores, NÃO repita ipsis litteris. Reformule ou não mencione de novo.
- NÃO termine TODA mensagem com "O que acha? 😊". Varie os fechamentos. Às vezes termine com afirmação, às vezes com pergunta diferente, às vezes sem emoji.

{"PRIMEIRA INTERAÇÃO: cumprimente, diga seu nome e pergunte como pode ajudar. NÃO liste preços nem features." if n_turnos <= 1 else "Você JÁ se apresentou. NÃO se apresente de novo. Continue a conversa naturalmente de onde parou."}
{"PERGUNTE O NOME: Você ainda não sabe o nome do cliente. Na próxima oportunidade natural, pergunte casualmente ('aliás, como posso te chamar?' ou 'qual teu nome?'). NÃO force, encaixe organicamente." if n_turnos <= 3 else "Se já souber o nome do cliente, USE-O nas mensagens para criar conexão pessoal."}
{"Se o cliente voltou depois de dias/semanas, retome naturalmente: 'e aí, conseguiu pensar sobre aquilo?'" if n_turnos > 3 else ""}"""


def _build_system_prompt_inbound() -> str:
    """System prompt para primeiro contato inbound (alguém mandou msg pela primeira vez)."""
    # Carregar knowledge base dinâmica (se existir)
    kb_extra = _carregar_knowledge_base()
    kb_section = f"\nINFO ATUALIZADA DO SISTEMA:\n{kb_extra}\n" if kb_extra else ""

    return f"""Você é Ana, vendedora da Derekh Food. Alguém mandou mensagem pela primeira vez.

PERSONALIDADE: vendedora humana, amigável, WhatsApp. Você NÃO é robô.
Escreve em português correto, sem abreviações de internet. Tom natural e acolhedor.

PRIMEIRA MENSAGEM — ESCOLHA UMA ABORDAGEM (não siga sempre a mesma):
Opção A: "Olá! Ana aqui da Derekh Food 🤙 em que posso te ajudar?"
Opção B: "Oi! Sou a Ana, tudo bem? Vi que mandou mensagem, me conta o que você está buscando"
Opção C: "Opa, tudo bem? Ana aqui! Me diz como posso te ajudar"
(Varie entre elas, não use sempre a mesma)

REGRA DE OURO: na primeira mensagem NÃO fale preço, features, nada. Só cumprimente e pergunte.

DEPOIS DA PRIMEIRA:
- Faça perguntas para entender a DOR antes de oferecer solução
- "Você tem delivery próprio ou usa iFood/Rappi?"
- "Qual o maior desafio do seu delivery hoje?"
- Só fale do sistema quando souber o que a pessoa precisa

COLETA NATURAL (não faça formulário):
- Na SEGUNDA ou TERCEIRA mensagem (nunca na primeira), pergunte o nome: "aliás, como posso te chamar?" ou "qual seu nome?" de forma casual
- Depois de saber o nome, USE-O nas mensagens seguintes (gera conexão)
- Ao longo da conversa, descubra: nome do restaurante, cidade, tipo de comida
- Mas de forma orgânica, não "qual seu nome? qual sua cidade?"

SOBRE A DEREKH FOOD (use só quando perguntarem):
- Sistema de gestão e delivery PRÓPRIO — a marca do restaurante
- NÃO substitui iFood. É COMPLEMENTO. iFood é vitrine, Derekh é a marca própria.
- Integra pedidos de TODAS as plataformas (iFood, Rappi, etc.) num painel só via Bridge Agent
- Site oficial: https://www.derekhfood.com.br

TESTE GRÁTIS (SEMPRE ofereça quando o lead hesitar ou perguntar sobre preço):
- 15 dias GRÁTIS no plano Premium (o mais completo)
- Sem cartão, sem compromisso. Depois escolhe o plano que quiser ou simplesmente para.
- O trial NÃO inclui WhatsApp Humanoide (add-on separado)

PREÇOS — TRANSPARÊNCIA NATURAL:
- NÃO mencione valores por conta própria — só se perguntarem.
- Se perguntarem "quanto custa?": "Tem 15 dias grátis no Premium, sem compromisso. Testa e depois escolhe."
- Se pedirem valor concreto: informe naturalmente: "O Básico é R$169,90/mês. Mas vale testar grátis primeiro."
- PROIBIDO tom passivo-agressivo ("já que insiste", "como insistiu"). Preço é informação normal.
- PROIBIDO mencionar R$527, R$329,90, R$279,90 por iniciativa própria.
- Bridge Printer IA: inclusa em TODOS os planos. Todos sem fidelidade. Setup em 48h.
- Só detalhe todos os planos se o lead perguntar ESPECIFICAMENTE:
  Básico R$169,90 | Essencial R$279,90 | Avançado R$329,90 | Premium R$527
{kb_section}
SE PERGUNTAREM SE VOCÊ É ROBÔ/IA/BOT:
- "Não não, sou a Ana da Derekh Food 😅"
- Nunca admita ser IA, bot ou humanoide. Mude de assunto naturalmente.
- NUNCA use a palavra "humanoide"

SEU TRABALHO É APENAS CONVENCER E VENDER:
- NUNCA dê detalhes técnicos de implementação (como integrar, APIs, banco de dados, configuração, servidor).
- Se perguntarem detalhes técnicos: "Isso a gente resolve no setup. O time técnico configura tudo em 48h. Vamos ativar seu teste?"
- Você explica BENEFÍCIOS e RESULTADOS, nunca o "como funciona por dentro".

ÁUDIO:
- NUNCA mencione áudio, voz, gravação, escritório, barulho, ligação ou videochamada.
- NÃO diga "fica melhor por escrito", "não consigo enviar áudio" ou variações.
- O sistema de áudio é automático — apenas responda normalmente por texto.

FORMATO (OBRIGATÓRIO):
- Escreva em português CORRETO. Sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz", "pq").
- Máximo 2 parágrafos curtos (2 frases cada)
- Separe parágrafos com uma linha vazia (\\n\\n). Nunca cole parágrafos juntos.
- Zero emojis corporativos. Pode usar 😅🤙👊 RARAMENTE.
- Explique funcionalidades com EXEMPLOS PRÁTICOS, nunca liste bullet points.
- NUNCA termine uma mensagem sem CALL-TO-ACTION.

FECHAMENTO (CRÍTICO):
- Se o lead demonstrou interesse, ASSUMA a venda: "vou ativar seu teste agora, me passa o nome do restaurante"
- Alternativa forçada: "prefere começar pelo Básico ou testar o Premium completo?"
- Trial como fato consumado: "vou liberar seu acesso. Em 48h está rodando."

SE PEDIR HUMANO: "Show, vou te passar pro time agora!"
PORTUGUÊS BRASILEIRO. Nunca invente dados."""


# ============================================================
# RESPONDER COM IA (v2.0)
# ============================================================

def responder_com_ia(conversa_id: int, mensagem_lead: str) -> dict:
    """Usa Grok IA para gerar resposta contextualizada.
    NÃO salva a resposta no banco — o chamador é responsável por salvar/enviar."""
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return {"erro": "Conversa não encontrada"}

    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}

    if httpx is None:
        return {"erro": "httpx não instalado"}

    # Contexto completo do lead
    lead_completo = obter_lead(conversa.get("lead_id")) if conversa.get("lead_id") else {}
    lead_context = _build_lead_context(conversa, lead_completo)

    # Histórico da conversa (últimas 30 msgs — contexto persistente)
    historico = []
    for msg in (conversa.get("mensagens") or [])[-30:]:
        role = "assistant" if msg["direcao"] == "enviada" else "user"
        conteudo = msg["conteudo"] or ""
        if conteudo:
            historico.append({"role": role, "content": conteudo})

    historico.append({"role": "user", "content": mensagem_lead})

    # Contar turnos para adaptar comportamento
    n_turnos = len([m for m in historico if m["role"] == "user"])

    system_prompt = _build_system_prompt_conversa(lead_context, n_turnos)

    # Injetar anti-repetição baseada no histórico
    padroes = _extrair_padroes_usados(historico)
    anti_rep = _formatar_anti_repeticao(padroes)
    if anti_rep:
        system_prompt += f"\n\n{anti_rep}"

    # P3.3: Adaptar tom por persona detectada
    persona = conversa.get("persona_detectada")
    if persona:
        _PERSONA_PROMPTS = {
            "tecnico": "\nTOM ADAPTADO (lead técnico): Seja mais detalhista nas funcionalidades. Mencione integrações, APIs, escalabilidade. Use termos como 'painel de controle', 'dashboard em tempo real', 'sistema integrado'. Menos emoção, mais dados concretos.",
            "apressado": "\nTOM ADAPTADO (lead apressado): Seja ULTRA direto. Frases curtas. Sem rodeios. Vá direto ao CTA. Máximo 2-3 frases por mensagem. Sem saudações longas. Foco: preço, resultado, ação.",
            "cauteloso": "\nTOM ADAPTADO (lead cauteloso): Transmita segurança. Mencione garantias: 'sem contrato', 'cancela quando quiser', 'sem cartão no trial'. Use provas sociais e referências. Sem pressão. Deixe o lead decidir no ritmo dele.",
            "entusiasta": "\nTOM ADAPTADO (lead entusiasta): Acompanhe a energia! Use exclamações (com moderação). Aproveite o entusiasmo para avançar rápido pro trial. Seja animada. 'Vai amar!', 'É exatamente isso!'",
        }
        prompt_persona = _PERSONA_PROMPTS.get(persona, "")
        if prompt_persona:
            system_prompt += prompt_persona

    # Fix #7: Log de decisão IA
    decision_log.info(f"IA_REQ conv={conversa_id} model=grok-3-mini-fast "
                      f"n_historico={len(historico)} persona={persona}")

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini-fast",
                "messages": [{"role": "system", "content": system_prompt}] + historico,
                "max_tokens": 150,
                "temperature": 0.8,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
        # Fix #7: Log da resposta IA
        usage = data.get("usage", {})
        decision_log.info(f"IA_RESP conv={conversa_id} resposta={resposta[:200]} "
                          f"tokens_in={usage.get('prompt_tokens')} "
                          f"tokens_out={usage.get('completion_tokens')}")
    except Exception as e:
        log.error(f"Erro Grok IA: {e}")
        return {"erro": f"Falha na IA: {e}"}

    return {"sucesso": True, "resposta": resposta}


# ============================================================
# HANDOFF GRADUAL (v2.0)
# ============================================================

def avaliar_handoff(conversa_id: int) -> tuple:
    """Avalia se deve fazer handoff para humano — escalonamento gradual.
    Retorna (tipo_handoff, motivo).
    tipo_handoff: None | "immediate" | "warm" | "strategic" """
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return None, ""

    msgs_recebidas = conversa.get("msgs_recebidas", 0)
    score = conversa.get("lead_score", 0)

    # Coletar dados das mensagens
    pediu_demo = False
    pediu_humano = False
    objecoes_nao_resolvidas = 0
    intent_score_acumulado = 0

    for msg in (conversa.get("mensagens") or []):
        if msg["direcao"] == "recebida":
            txt = (msg.get("conteudo") or "").lower()

            # Pediu demo/reunião?
            if any(w in txt for w in ("demo", "agendar", "reunião", "reuniao",
                                       "amanhã", "amanha", "horário", "horario",
                                       "quero ver", "me mostra")):
                pediu_demo = True

            # Pediu humano?
            if any(w in txt for w in ("falar com alguém", "falar com alguem",
                                       "atendente", "humano", "pessoa real",
                                       "gerente", "responsável", "responsavel")):
                pediu_humano = True

            # Contar objeções
            det = detectar_intencao(txt)
            if det.get("objecoes"):
                objecoes_nao_resolvidas += 1
            intent_score_acumulado += det.get("score", 0)

    # P2.1: Enviar trial link antes do handoff (se não enviou ainda)
    lead = obter_lead(conversa.get("lead_id")) if conversa.get("lead_id") else None
    trial_ja_enviado = bool(lead and lead.get("trial_link_enviado_at"))

    def _enviar_trial_link_se_necessario(conv, lead_data):
        """Envia link trial self-service se ainda não enviou."""
        if trial_ja_enviado or not lead_data:
            return
        numero = conv.get("numero_envio")
        if not numero:
            return
        lid = lead_data.get("id")
        link = f"https://derekhfood.com.br/onboarding?ref={lid}&utm_source=wa_bot"
        texto = (
            f"Enquanto nosso time prepara tudo, você já pode experimentar grátis por 15 dias:\n\n"
            f"{link}\n\nSem compromisso, sem cartão! 😊"
        )
        _enviar_direto(numero, texto)
        from crm.database import marcar_trial_link_enviado, registrar_interacao
        marcar_trial_link_enviado(lid)
        registrar_interacao(lid, "whatsapp", "whatsapp", "Trial link enviado (pré-handoff)", "enviado")
        log.info(f"Trial link enviado para lead {lid} (pré-handoff)")

    # P3.3: Detectar persona após 2+ mensagens
    if msgs_recebidas >= 2:
        _detectar_e_salvar_persona(conversa)

    # VALIDAÇÃO PRÉ-HANDOFF: Verificar se confirmou que é restaurante
    restaurante_confirmado = _verificar_restaurante_confirmado(conversa)

    # 0. HANDOFF IMEDIATO — lead aceitou/disse "sim" 2+ vezes (Conv 84 pattern)
    # Se lead responde afirmativamente sem dar detalhes, precisa de humano
    respostas_afirmativas = 0
    for msg in (conversa.get("mensagens") or []):
        if msg["direcao"] == "recebida":
            txt = (msg.get("conteudo") or "").lower().strip()
            if txt in ("sim", "quero", "pode ser", "vamos", "ok", "bora",
                        "com certeza", "claro", "vamos lá", "vamos la",
                        "pode", "aceito", "top", "fechou", "beleza"):
                respostas_afirmativas += 1
    if respostas_afirmativas >= 2:
        _enviar_trial_link_se_necessario(conversa, lead)
        return "warm", f"Lead aceitou {respostas_afirmativas}x — precisa de humano para converter"

    # 1. HANDOFF IMEDIATO — pediu demo ou humano
    if pediu_demo or pediu_humano:
        if not restaurante_confirmado and msgs_recebidas >= 2:
            log.info(f"Handoff adiado para conv {conversa_id} — restaurante não confirmado")
            return None, ""
        _enviar_trial_link_se_necessario(conversa, lead)
        motivo = "Lead pediu demo/reunião" if pediu_demo else "Lead pediu atendente humano"
        return "immediate", motivo

    # 2. HANDOFF QUENTE — lead muito engajado
    if intent_score_acumulado >= 60 and msgs_recebidas >= 3:
        _enviar_trial_link_se_necessario(conversa, lead)
        return "warm", f"Lead engajado (score acumulado={intent_score_acumulado}, {msgs_recebidas} msgs)"

    # 3. HANDOFF QUENTE — score CRM alto
    if score >= 85 and msgs_recebidas >= 1:
        _enviar_trial_link_se_necessario(conversa, lead)
        return "warm", f"Lead HOT (score CRM={score}) respondeu"

    # 4. HANDOFF ESTRATÉGICO — objeções não resolvidas
    if objecoes_nao_resolvidas >= 2:
        _enviar_trial_link_se_necessario(conversa, lead)
        return "strategic", f"Lead com {objecoes_nao_resolvidas} objeções — escalar para gerente"

    return None, ""


def _detectar_e_salvar_persona(conversa: dict):
    """P3.3: Detecta persona do lead via análise de mensagens recebidas.
    Classifica: tecnico, apressado, cauteloso, entusiasta.
    Salva em wa_conversas.persona_detectada (uma vez, sem recalcular)."""
    # Não recalcular se já detectado
    if conversa.get("persona_detectada"):
        return

    conversa_id = conversa.get("id")
    if not conversa_id:
        return

    msgs = [m for m in (conversa.get("mensagens") or []) if m.get("direcao") == "recebida"]
    if len(msgs) < 2:
        return

    textos = [(m.get("conteudo") or "").lower() for m in msgs]
    texto_concat = " ".join(textos)
    avg_len = sum(len(t) for t in textos) / max(len(textos), 1)

    # Pontuação por persona
    scores = {"tecnico": 0, "apressado": 0, "cauteloso": 0, "entusiasta": 0}

    # Técnico
    for kw in ("api", "integração", "integracao", "webhook", "como funciona",
               "feature", "funcionalidade", "tecnologia", "banco de dados",
               "migração", "migracao", "configurar", "suporte técnico"):
        if kw in texto_concat:
            scores["tecnico"] += 3

    # Apressado
    if avg_len < 30:
        scores["apressado"] += 3
    for kw in ("rápido", "rapido", "logo", "agora", "direto",
               "quanto custa", "preço", "valor", "resumo"):
        if kw in texto_concat:
            scores["apressado"] += 2
    # Msgs curtas (1-2 palavras) são indicador forte
    short_msgs = sum(1 for t in textos if len(t.split()) <= 3)
    if short_msgs >= 2:
        scores["apressado"] += 3

    # Cauteloso
    for kw in ("caro", "garantia", "contrato", "cancelar", "funciona mesmo",
               "dúvida", "duvida", "certeza", "confiável", "confiavel",
               "comprovante", "referência", "referencia", "golpe", "seguro",
               "não sei", "nao sei", "será que", "sera que", "fidelidade"):
        if kw in texto_concat:
            scores["cauteloso"] += 3

    # Entusiasta
    for kw in ("demais", "show", "top", "perfeito", "incrível", "incrivel",
               "gostei", "adorei", "uau", "legal", "maravilha", "genial",
               "sensacional", "excelente", "ótimo", "otimo", "massa"):
        if kw in texto_concat:
            scores["entusiasta"] += 3
    # Emojis indicam entusiasmo
    import re as _re
    emoji_count = len(_re.findall(r'[\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\U0001F900-\U0001F9FF\U00002702-\U000027B0\U0001FA00-\U0001FA6F]', texto_concat))
    if emoji_count >= 3:
        scores["entusiasta"] += 4

    # Determinar vencedor
    melhor = max(scores, key=scores.get)
    if scores[melhor] < 3:
        return  # Confiança muito baixa

    try:
        atualizar_conversa_wa(conversa_id, persona_detectada=melhor)
        log.info(f"Persona detectada: {melhor} para conversa {conversa_id} (scores: {scores})")
    except Exception as e:
        log.warning(f"Erro ao salvar persona: {e}")


def _verificar_msgs_novas_pos_ia(conversa_id: int, ts_inicio: float) -> list:
    """Verifica msgs recebidas APÓS timestamp. Retorna lista ou []."""
    from crm.database import get_conn
    import datetime
    dt = datetime.datetime.fromtimestamp(ts_inicio)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT conteudo FROM wa_mensagens
            WHERE conversa_id = %s AND direcao = 'recebida' AND created_at > %s
            ORDER BY created_at
        """, (conversa_id, dt))
        return [r["conteudo"] for r in cur.fetchall()]


# ============================================================
# PROCESSAR RESPOSTAS (PRINCIPAL)
# ============================================================

def processar_resposta_wa(numero_remetente: str, mensagem: str, instance: str = "",
                          tipo_msg: str = "texto") -> dict:
    """Processa mensagem recebida — de lead existente OU contato novo.
    Se não existir conversa, cria lead inbound + conversa e responde.
    Se existir conversa encerrada/handoff, REATIVA (contexto persistente).
    IMPORTANTE: cada mensagem é salva UMA VEZ e enviada UMA VEZ.
    instance: nome da instância Evolution de onde veio a msg (para responder pelo mesmo número).
    tipo_msg: 'texto' ou 'audio' (áudio transcrito pelo STT)."""
    numero = _limpar_telefone(numero_remetente)

    # Anti-spam: se já está processando resposta para este número, salvar msg mas não responder de novo
    if not _adquirir_lock_resposta(numero):
        log.info(f"Msg de {numero} enfileirada (já processando resposta anterior)")
        # Salvar a mensagem no histórico mesmo sem responder
        from crm.database import get_conn
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id FROM wa_conversas WHERE numero_envio = %s AND status = 'ativo'
                ORDER BY created_at DESC LIMIT 1
            """, (numero,))
            row_lock = cur.fetchone()
            if row_lock:
                registrar_msg_wa(row_lock["id"], "recebida", mensagem, intencao="enfileirada")
        return {"processado": True, "enfileirada": True}

    # Buscar conversa pelo número — primeiro ativa, depois qualquer status (exceto opt_out)
    from crm.database import get_conn, criar_lead_inbound, criar_conversa_wa as _criar_conv
    with get_conn() as conn:
        cur = conn.cursor()
        # Prioridade 1: conversa ativa
        cur.execute("""
            SELECT c.id, c.lead_id, c.status FROM wa_conversas c
            WHERE c.numero_envio = %s AND c.status = 'ativo'
            ORDER BY c.created_at DESC LIMIT 1
        """, (numero,))
        row = cur.fetchone()

        # Prioridade 2: conversa encerrada (REATIVAR — manter contexto)
        if not row:
            cur.execute("""
                SELECT c.id, c.lead_id, c.status FROM wa_conversas c
                WHERE c.numero_envio = %s AND c.status IN ('encerrado', 'handoff')
                ORDER BY c.updated_at DESC LIMIT 1
            """, (numero,))
            row = cur.fetchone()
            if row:
                old_status = row["status"]
                # Reativar conversa — contexto persistente!
                cur.execute("UPDATE wa_conversas SET status = 'ativo' WHERE id = %s", (row["id"],))
                conn.commit()
                log.info(f"Conversa {row['id']} REATIVADA para {numero} (era {old_status})")

                # Se era handoff, NÃO deixar o bot responder — notificar humano
                if old_status == "handoff":
                    registrar_msg_wa(row["id"], "recebida", mensagem, intencao="pos_handoff")
                    _notificar_handoff(row["lead_id"], numero,
                                       f"Lead respondeu após handoff: {mensagem[:80]}",
                                       instance)
                    log.info(f"Lead {row['lead_id']} respondeu pós-handoff — notificando humano, bot NÃO responde")
                    _liberar_lock_resposta(numero)
                    return {"processado": True, "pos_handoff": True, "lead_id": row["lead_id"]}

    if not row:
        # --- NOVO CONTATO (nunca conversou antes): criar lead + conversa ---
        log.info(f"Novo contato inbound: {numero} (instance={instance}) — criando lead e conversa")
        lead_id = criar_lead_inbound(numero)
        conversa_id = _criar_conv(lead_id, numero, "consultivo")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="interesse")
        registrar_interacao(lead_id, "whatsapp", "whatsapp",
                            f"WA inbound: {mensagem[:100]}", "positivo")

        # Delay humano antes de responder
        delay = _calcular_delay_humano(mensagem)
        log.info(f"Delay humano: {delay:.1f}s antes de responder inbound")
        _time.sleep(delay)

        # Debounce: agregar msgs que chegaram durante o delay
        mensagem_agregada = _agregar_mensagens_pendentes(conversa_id, mensagem)

        # Responder com IA (prompt de boas-vindas)
        resultado_ia = _responder_inbound(conversa_id, mensagem_agregada)
        if resultado_ia.get("sucesso"):
            # Inbound é sempre texto — LLM já gera português correto
            resposta = resultado_ia["resposta"]
            enviado = _enviar_direto(numero, resposta, instance=instance)
            registrar_msg_wa(conversa_id, "enviada", resposta, grok=True)
            if enviado.get("sucesso"):
                log.info(f"Resposta inbound enviada para {numero} via {instance or 'default'}")
            else:
                log.warning(f"Falha envio inbound {numero}: {enviado.get('erro')}")

        _liberar_lock_resposta(numero)
        return {"processado": True, "inbound": True, "lead_id": lead_id}

    conversa_id = row["id"]
    lead_id = row["lead_id"]

    # Buscar número de envio (precisamos antes das detecções)
    conversa_full = obter_conversa_wa(conversa_id)
    numero_envio = (conversa_full or {}).get("numero_envio") or numero

    # Fix #7: Log de decisão principal
    decision_log.info(f"RECV lead={lead_id} conv={conversa_id} num={numero} "
                      f"tipo={tipo_msg} msg={mensagem[:200]}")

    # Fix #4 + #10: Detecção de auto-reply ANTES do intent scoring
    if _detectar_autoresposta(mensagem) or _detectar_broadcast_promo(mensagem):
        is_broadcast = _detectar_broadcast_promo(mensagem)
        log.info(f"{'Broadcast' if is_broadcast else 'Auto-reply'} detectada de {numero}")
        decision_log.info(f"{'BROADCAST' if is_broadcast else 'AUTORESPOSTA'} conv={conversa_id} msg={mensagem[:200]}")
        registrar_msg_wa(conversa_id, "recebida", mensagem,
                         intencao="broadcast" if is_broadcast else "autoresposta")
        _time.sleep(_calcular_delay_humano(mensagem))

        if is_broadcast:
            resposta = ("Oi! Vi que vocês estão ativos no delivery, muito bom! "
                        "Sou a Ana da Derekh Food. Gostaria de conversar com o "
                        "responsável sobre uma forma de ter delivery próprio, "
                        "sem comissão de plataforma. Com quem estou falando?")
        else:
            horario_info = _extrair_horario_funcionamento(mensagem)
            if horario_info:
                resposta = (f"Entendi que o horário de atendimento é {horario_info}. "
                            f"Vou entrar em contato nesse horário então! "
                            f"Poderia me encaminhar para um responsável quando possível?")
                _agendar_recontato(lead_id, conversa_id, horario_info)
            else:
                resposta = ("Entendi! Poderia me encaminhar para um responsável? "
                            "Sou a Ana da Derekh Food, gostaria de apresentar algo "
                            "que pode ajudar o negócio de vocês.")

        _enviar_e_salvar(conversa_id, numero_envio, resposta, instance=instance)
        _liberar_lock_resposta(numero)
        return {"processado": True, "autoresposta": True, "lead_id": lead_id}

    # Detecção de número errado
    if _detectar_numero_errado(mensagem):
        log.info(f"Número errado detectado para lead {lead_id}")
        decision_log.info(f"NUMERO_ERRADO lead={lead_id} conv={conversa_id} msg={mensagem[:200]}")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="numero_errado")
        _time.sleep(_calcular_delay_humano(mensagem))
        resposta = ("Desculpa pelo incômodo! Deve ter sido um engano. "
                    "Se por acaso conhecer alguém com restaurante que precise "
                    "de um app de delivery, fico no aguardo! Boa semana! 🤙")
        _enviar_e_salvar(conversa_id, numero_envio, resposta, instance=instance)
        atualizar_conversa_wa(conversa_id, status="encerrado",
                              notas="\n[NUMERO_ERRADO] Lead informou que número não pertence a ele")
        _liberar_lock_resposta(numero)
        return {"processado": True, "numero_errado": True, "lead_id": lead_id}

    # Fix #12: Detecção de contador/intermediário
    if _detectar_contador(mensagem):
        log.info(f"Contador detectado para lead {lead_id} — pedindo contato do dono")
        decision_log.info(f"CONTADOR lead={lead_id} conv={conversa_id} msg={mensagem[:200]}")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="contador")
        _time.sleep(_calcular_delay_humano(mensagem))
        resposta = ("Ah, entendi! Desculpa o incômodo. "
                    "Poderia me passar o contato do responsável pelo restaurante? "
                    "Quero apresentar algo que pode ajudar bastante o negócio dele.")
        _enviar_e_salvar(conversa_id, numero_envio, resposta, instance=instance)
        atualizar_conversa_wa(conversa_id, status="aguardando_contato_dono")
        _liberar_lock_resposta(numero)
        return {"processado": True, "contador": True, "lead_id": lead_id}

    # Detecção de NÃO-RESTAURANTE / Lead falso
    if _detectar_nao_restaurante(mensagem):
        log.info(f"Lead {lead_id} NÃO é restaurante — marcando como lead_falso")
        decision_log.info(f"NAO_RESTAURANTE lead={lead_id} conv={conversa_id} msg={mensagem[:200]}")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="nao_restaurante")
        _time.sleep(_calcular_delay_humano(mensagem))
        resposta = ("Ah, entendi! Desculpa o incômodo então. "
                    "A Derekh Food é focada em restaurantes e delivery de comida. "
                    "Te desejo muito sucesso no seu negócio! 🤙")
        _enviar_e_salvar(conversa_id, numero_envio, resposta, instance=instance)
        _marcar_lead_falso(lead_id, conversa_id, f"Lead informou: {mensagem[:100]}")
        _liberar_lock_resposta(numero)
        return {"processado": True, "lead_falso": True, "lead_id": lead_id}

    # Detectar intenção (scoring contextual v2.0)
    intent_result = detectar_intencao(mensagem)
    intencao = intent_result["intencao"]
    intent_score = intent_result["score"]
    objecoes = intent_result["objecoes"]

    # Registrar mensagem recebida (1x)
    registrar_msg_wa(conversa_id, "recebida", mensagem, tipo=tipo_msg, intencao=intencao)
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA recebido: {mensagem[:100]}", "positivo")

    # P4.1: Event scoring — lead respondeu via WA
    try:
        from crm.scoring import atualizar_score_evento
        atualizar_score_evento(lead_id, "wa_respondeu")
    except Exception:
        pass  # Scoring não deve bloquear fluxo

    # Fix #7: Log de intenção
    decision_log.info(f"INTENT lead={lead_id} conv={conversa_id} intent={intencao} "
                      f"score={intent_score} objecoes={objecoes}")

    log.info(f"Resposta do lead {lead_id}: intenção={intencao} score={intent_score} "
             f"objeções={objecoes} (instance={instance})")

    # --- OPT-OUT: remove da lista para sempre ---
    if intencao == "opt_out":
        opt_out_lead(lead_id, "wa")
        atualizar_conversa_wa(conversa_id, status="opt_out", intencao_detectada="opt_out")
        # P4.1: Event scoring — opt_out
        try:
            from crm.scoring import atualizar_score_evento
            atualizar_score_evento(lead_id, "opt_out")
        except Exception:
            pass
        _enviar_e_salvar(conversa_id, numero_envio,
                         "Tranquilo, te tirei da lista. Desculpa o incômodo! 🤙",
                         instance=instance)
        _liberar_lock_resposta(numero)
        return {"processado": True, "intencao": "opt_out", "lead_id": lead_id}

    # --- RECUSA FIRME: encerra com classe (mas pode reativar se voltar) ---
    if intencao == "hard_no":
        atualizar_conversa_wa(conversa_id, intencao_detectada="hard_no")
        # Delay humano
        _time.sleep(_calcular_delay_humano(mensagem))
        _enviar_e_salvar(conversa_id, numero_envio,
                         "De boa, entendo! Se um dia precisar de algo, tô por aqui. Sucesso! 🤙",
                         instance=instance)
        atualizar_conversa_wa(conversa_id, status="encerrado")
        _liberar_lock_resposta(numero)
        return {"processado": True, "intencao": "hard_no", "lead_id": lead_id}

    # --- TUDO MAIS: IA responde (interesse, objeção, dúvida, outro) ---
    atualizar_conversa_wa(conversa_id, intencao_detectada=intencao)

    # Delay humano antes de responder
    delay = _calcular_delay_humano(mensagem)
    log.info(f"Delay humano: {delay:.1f}s antes de responder lead {lead_id}")
    _time.sleep(delay)

    # Debounce: agregar msgs que chegaram durante o delay
    mensagem_agregada = _agregar_mensagens_pendentes(conversa_id, mensagem)

    # Fix #13: Enriquecer lead com dados descobertos na conversa
    _enriquecer_lead_conversa(lead_id, conversa_id, mensagem_agregada)

    # Gerar resposta IA + verificação pré-envio
    ts_antes_ia = _time.time()
    resultado_ia = responder_com_ia(conversa_id, mensagem_agregada)

    if resultado_ia.get("sucesso"):
        # Verificar msgs novas durante geração IA (ex: "esquece", "para")
        msgs_novas = _verificar_msgs_novas_pos_ia(conversa_id, ts_antes_ia)
        if msgs_novas:
            log.info(f"Msgs novas durante IA: {len(msgs_novas)} — regenerando")
            msg_completa = mensagem_agregada + "\n" + "\n".join(msgs_novas)
            resultado_ia = responder_com_ia(conversa_id, msg_completa)  # Max 1 retry

    if resultado_ia.get("sucesso"):
        resposta_crua = resultado_ia["resposta"]

        # Decisão: enviar áudio ou texto?
        enviar_audio = _deve_enviar_audio(conversa_full, mensagem)
        decision_log.info(f"AUDIO_DECISION conv={conversa_id} resultado={enviar_audio}")
        if enviar_audio:
            # Truncar áudio para max ~30s
            audio_part, texto_extra = _truncar_para_audio(resposta_crua)
            # ÁUDIO: transformar português correto → dicção falada brasileira
            resposta_audio = _preparar_texto_para_audio(audio_part)
            # Inferir emoção S2-Pro pelo contexto da conversa
            emocao_ctx = _inferir_emocao_contexto(intencao, resposta_crua, mensagem)
            log.info(f"Emoção S2-Pro inferida: {emocao_ctx} (intenção={intencao})")
            # Presença "gravando..." antes do TTS (~5-15s)
            _enviar_presenca(numero_envio, "recording", delay_ms=15000, instance_override=instance)
            audio_result = _gerar_e_enviar_audio_resposta(
                numero_envio, resposta_audio, conversa_id,
                instance=instance, emocao=emocao_ctx)
            if audio_result.get("sucesso"):
                # Texto complementar (dados numéricos ou resto do texto)
                complemento = texto_extra or _extrair_dados_numericos(resposta_crua)
                if complemento:
                    _time.sleep(random.uniform(1.5, 3.0))
                    _enviar_e_salvar(conversa_id, numero_envio, complemento, instance=instance)
            else:
                # Fallback para texto (enviar direto — LLM já escreve correto)
                log.warning(f"Fallback texto (áudio falhou): {audio_result['erro']}")
                _enviar_e_salvar(conversa_id, numero_envio, resposta_crua,
                                 grok=True, instance=instance)
        else:
            # TEXTO: enviar direto — LLM já gera português correto
            _enviar_e_salvar(conversa_id, numero_envio, resposta_crua,
                             grok=True, instance=instance)

        # Avaliar handoff gradual
        handoff_tipo, motivo = avaliar_handoff(conversa_id)
        if handoff_tipo == "immediate":
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            # P4.1: Event scoring — lead pediu demo/reunião
            try:
                if "demo" in motivo.lower() or "reunião" in motivo.lower():
                    from crm.scoring import atualizar_score_evento
                    atualizar_score_evento(lead_id, "wa_pediu_demo")
            except Exception:
                pass
            # Notificar o dono
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF IMEDIATO lead {lead_id}: {motivo}")

        elif handoff_tipo == "warm":
            # Bot faz a transição naturalmente
            _time.sleep(random.uniform(2, 5))
            _enviar_e_salvar(conversa_id, numero_envio,
                             "Olha, deixa eu te passar pro time técnico que eles conseguem "
                             "te mostrar o sistema ao vivo, rapidinho. Já já alguém te chama!",
                             instance=instance)
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF QUENTE lead {lead_id}: {motivo}")

        elif handoff_tipo == "strategic":
            _time.sleep(random.uniform(2, 5))
            _enviar_e_salvar(conversa_id, numero_envio,
                             "Sabe o que, vou pedir pro meu gerente te dar um toque, "
                             "ele explica melhor essa parte. Pode ser?",
                             instance=instance)
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF ESTRATÉGICO lead {lead_id}: {motivo}")

    _liberar_lock_resposta(numero)
    return {"processado": True, "intencao": intencao, "score": intent_score, "lead_id": lead_id}


# ============================================================
# ENVIO HELPERS
# ============================================================

def _enviar_e_salvar(conversa_id: int, numero: str, texto: str, grok: bool = False, instance: str = ""):
    """Envia mensagem via Evolution/Cloud API e salva no banco UMA VEZ."""
    resultado = _enviar_direto(numero, texto, instance=instance)
    registrar_msg_wa(conversa_id, "enviada", texto, grok=grok)
    if not resultado.get("sucesso"):
        log.warning(f"Falha envio para {numero}: {resultado.get('erro')}")
    return resultado


def _enviar_direto(numero: str, texto: str, instance: str = "") -> dict:
    """Envia mensagem direta para um número (sem precisar de lead_id).
    Prioridade: Evolution API → Cloud API.
    Se instance fornecido, usa essa instância Evolution específica."""
    # Verificar se Evolution está configurada
    evo_instance = (obter_configuracao("evolution_instance") or "").strip()
    if evo_instance or instance:
        # Tentar Evolution API primeiro
        resultado = _enviar_via_evolution(numero, texto, instance_override=instance)
        if resultado.get("sucesso"):
            log.info(f"Mensagem direta enviada via Evolution ({instance or 'default'}) para {numero}")
            return resultado

    # Cloud API (direto se Evolution desabilitada, fallback se falhou)
    resultado = _enviar_via_cloud_api(numero, texto)
    if resultado.get("sucesso"):
        log.info(f"Mensagem direta enviada via Cloud API para {numero}")
        return resultado

    log.error(f"Falha envio direto {numero}: Evolution e Cloud API falharam")
    return resultado


def _responder_inbound(conversa_id: int, mensagem: str) -> dict:
    """Responde primeira mensagem de contato inbound (alguém do site/landing)."""
    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}
    if httpx is None:
        return {"erro": "httpx não instalado"}

    system_prompt = _build_system_prompt_inbound()

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini-fast",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensagem},
                ],
                "max_tokens": 120,
                "temperature": 0.85,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
        return {"sucesso": True, "resposta": resposta}
    except Exception as e:
        log.error(f"Erro Grok IA inbound: {e}")
        return {"erro": f"Falha na IA: {e}"}


# ============================================================
# NOTIFICAÇÕES
# ============================================================

def _notificar_trial(lead_id: int, numero_lead: str, instance: str = ""):
    """Notifica o dono quando lead pede teste grátis."""
    lead = obter_lead(lead_id)
    nome_rest = "Restaurante"
    cidade = ""
    if lead:
        nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
        cidade = lead.get("cidade") or ""

    # Número do dono: config ou env
    numero_dono = obter_configuracao("telefone_usuario") or os.environ.get("WA_SALES_NUMERO", "")
    numero_dono = _limpar_telefone(numero_dono)
    if not numero_dono:
        log.warning("Não há número do dono configurado para notificação de trial")
        return

    texto = (
        f"🔔 LEAD QUENTE!\n\n"
        f"*{nome_rest}*"
        + (f" ({cidade})" if cidade else "") +
        f" quer iniciar teste grátis de 15 dias!\n\n"
        f"Número: {numero_lead}\n"
        f"Lead ID: {lead_id}"
    )

    resultado = _enviar_direto(numero_dono, texto, instance=instance)
    if resultado.get("sucesso"):
        log.info(f"Notificação trial enviada ao dono para lead {lead_id}")
    else:
        log.warning(f"Falha ao notificar dono sobre trial lead {lead_id}: {resultado.get('erro')}")


def _notificar_handoff(lead_id: int, numero_lead: str, motivo: str, instance: str = ""):
    """Notifica o dono quando um lead precisa de atendimento humano."""
    lead = obter_lead(lead_id)
    nome_rest = "Restaurante"
    cidade = ""
    if lead:
        nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
        cidade = lead.get("cidade") or ""

    numero_dono = obter_configuracao("telefone_usuario") or os.environ.get("WA_SALES_NUMERO", "")
    numero_dono = _limpar_telefone(numero_dono)
    if not numero_dono:
        log.warning("Não há número do dono configurado para notificação de handoff")
        return

    texto = (
        f"🔥 HANDOFF!\n\n"
        f"*{nome_rest}*"
        + (f" ({cidade})" if cidade else "") +
        f"\nMotivo: {motivo}\n\n"
        f"Número: {numero_lead}\n"
        f"Lead ID: {lead_id}\n\n"
        f"⚡ Esse lead precisa de atenção AGORA!"
    )

    resultado = _enviar_direto(numero_dono, texto, instance=instance)
    if resultado.get("sucesso"):
        log.info(f"Notificação handoff enviada ao dono para lead {lead_id}")
    else:
        log.warning(f"Falha ao notificar dono sobre handoff lead {lead_id}: {resultado.get('erro')}")


# ============================================================
# CONVERSA OUTBOUND AUTÔNOMA — Brain Loop inicia conversa proativa
# ============================================================

def iniciar_conversa_outbound(lead_id: int) -> dict:
    """Inicia conversa WA proativa — Ana aborda o lead com abertura
    personalizada gerada por IA (Grok), baseada nos dados do lead.
    Diferente de enviar_mensagem_wa() que envia texto fixo:
    - Gera abertura via LLM (Grok) com contexto competitivo
    - Registra como interação outbound
    - Configura conversa para modo vendas ativo
    Retorna dict com sucesso/erro."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out de WhatsApp"}

    # Verificar se o telefone é um número excluído (dono, bots)
    telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    numero_limpo = _limpar_telefone(telefone)
    if numero_limpo in _NUMEROS_EXCLUIDOS:
        log.warning(f"Lead {lead_id} tem número excluído ({numero_limpo}) — não prospectar")
        return {"erro": f"Número excluído da prospecção: {numero_limpo}"}

    # Verificar telefone inválido (muito curto ou "0")
    if len(numero_limpo) < 8:
        log.warning(f"Lead {lead_id} tem telefone inválido ({telefone}) — não prospectar")
        return {"erro": f"Telefone inválido: {telefone}"}

    # Verificar se já tem conversa ativa (evitar duplicata)
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa and conversa.get("status") == "ativo":
        return {"erro": "Já existe conversa ativa para este lead"}

    # Gerar abertura personalizada via Grok
    abertura = _gerar_abertura_outbound(lead)
    if not abertura:
        # Fallback para mensagem fixa se Grok falhar (Fix #2 + #3)
        pers = personalizar_abordagem(lead)
        nome = pers.get("nome_dono") or ""
        nome_rest = _limpar_nome_restaurante(lead)
        if not nome:
            nome = nome_rest
        abertura = (
            f"Oi {nome}! Tudo bem?\n\n"
            f"Me chamo Ana, da Derekh Food. "
            f"Vi que o *{nome_rest}* tem potencial enorme para crescer com delivery próprio.\n\n"
            f"Sem comissão de plataforma — seus clientes pedem direto de você.\n\n"
            f"Posso te mostrar como funciona? São só 5 minutinhos!"
        )

    # Enviar via enviar_mensagem_wa() (cria conversa + envia)
    result = enviar_mensagem_wa(lead_id, abertura, tom="abertura_proativa")

    if result.get("sucesso"):
        log.info(f"Conversa outbound iniciada para lead {lead_id}")
        registrar_interacao(lead_id, "whatsapp", "whatsapp",
                            f"WA outbound Ana (Brain Loop): {abertura[:80]}...", "enviado")

        # Fix #6: Enviar áudio de apresentação complementar
        _enviar_audio_abertura(lead_id, result.get("conversa_id", 0), abertura)

    return result


def _gerar_abertura_outbound(lead: dict) -> str:
    """Gera mensagem de abertura personalizada via Grok com contexto do lead.
    Retorna texto da mensagem ou string vazia se falhar."""
    xai_key = _get_xai_key()
    if not xai_key or not httpx:
        return ""

    pers = personalizar_abordagem(lead)
    nome_dono = pers.get("nome_dono") or ""
    nome_rest = _limpar_nome_restaurante(lead)
    if not nome_dono:
        nome_dono = nome_rest  # Usa nome do restaurante quando não tem sócio
    cidade = lead.get("cidade") or ""
    tem_ifood = lead.get("tem_ifood") or 0
    tem_rappi = lead.get("tem_rappi") or 0

    # Contexto competitivo
    concorrentes_texto = ""
    try:
        from crm.competitor_service import concorrentes_bairro
        concorrentes = concorrentes_bairro(lead["id"], limite=3)
        if concorrentes:
            nomes = [c.get("nome_fantasia") or c.get("razao_social") or "?" for c in concorrentes]
            concorrentes_texto = f"Concorrentes próximos com delivery: {', '.join(nomes[:3])}"
    except Exception:
        pass

    # Cenário
    cenario = "sem delivery online — oportunidade de ter delivery próprio"
    if tem_ifood and tem_rappi:
        cenario = "já está no iFood e Rappi — pode fidelizar com marca própria sem comissão"
    elif tem_ifood:
        cenario = "está no iFood — pode complementar com delivery próprio sem 27% de comissão"

    system = """Você é Ana, vendedora da Derekh Food. Escreva UMA mensagem curta de WhatsApp (máx 4 linhas)
para abordar um restaurante pela primeira vez. Seja natural, sem parecer robô.
Regras:
- Se o nome do contato é DESCONHECIDO, cumprimente usando o nome do restaurante e pergunte com quem está falando
- Se tem nome do contato, cumprimente pelo nome
- Mencione algo específico dos dados (cidade, iFood, rating, concorrentes)
- Se apresente como Ana da Derekh Food
- Termine com pergunta aberta que gere curiosidade
- Tom amigável e direto, sem abreviações de internet
- NÃO mencione preços
- NÃO use emojis excessivos (máximo 1)
- Escreva SOMENTE o texto da mensagem, nada mais"""

    # Fix #11: Prompt enriquecido com mais dados do lead
    nome_contato_label = nome_dono if nome_dono != nome_rest else "DESCONHECIDO (pergunte o nome)"
    ifood_info = ""
    if lead.get("rating"):
        ifood_info += f"\nRating Google Maps: {lead['rating']}★"
        if lead.get("total_reviews"):
            ifood_info += f" ({lead['total_reviews']} avaliações)"
    if tem_ifood:
        ifood_info += f"\nNo iFood: Sim"
        if lead.get("ifood_categorias"):
            ifood_info += f" — {lead['ifood_categorias']}"
        if lead.get("ifood_preco"):
            ifood_info += f" {lead['ifood_preco']}"
    else:
        ifood_info += "\nNo iFood: Não encontrado"

    user = f"""Nome do contato: {nome_contato_label}
Restaurante: {nome_rest}
Cidade: {cidade}
Cenário delivery: {cenario}
{concorrentes_texto}{ifood_info}

OBRIGATÓRIO na mensagem:
- Se o nome do contato é DESCONHECIDO, cumprimente usando o nome do restaurante e pergunte com quem está falando
- Mencione algo específico dos dados acima (cidade, iFood, rating)
- Se apresente como Ana da Derekh Food
- Termine com pergunta aberta"""

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini-fast",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": 150,
                "temperature": 0.85,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        texto = data["choices"][0]["message"]["content"].strip()
        # Limpar aspas envolventes se a IA colocar
        if texto.startswith('"') and texto.endswith('"'):
            texto = texto[1:-1]
        return texto
    except Exception as e:
        log.warning(f"Erro Grok abertura outbound: {e}")
        return ""


# ============================================================
# RETOMAR CONVERSAS SEM RESPOSTA (Novo requisito)
# ============================================================

def retomar_conversas_sem_resposta(limite: int = 20) -> dict:
    """Analisa conversas ativas onde o lead respondeu mas ficou sem resposta do bot.
    Envia resposta por áudio para retomar o contato.
    Chamado pelo brain_loop para não deixar leads no 'vácuo'."""
    from crm.database import get_conn

    result = {"retomadas": 0, "erros": 0}

    with get_conn() as conn:
        cur = conn.cursor()
        # Buscar conversas onde a última msg é do lead (sem resposta do bot)
        # e não é opt_out, encerrado, handoff ou lead_falso
        cur.execute("""
            SELECT c.id as conversa_id, c.lead_id, c.numero_envio,
                   (SELECT m.conteudo FROM wa_mensagens m
                    WHERE m.conversa_id = c.id ORDER BY m.created_at DESC LIMIT 1) as ultima_msg,
                   (SELECT m.direcao FROM wa_mensagens m
                    WHERE m.conversa_id = c.id ORDER BY m.created_at DESC LIMIT 1) as ultima_direcao,
                   (SELECT m.created_at FROM wa_mensagens m
                    WHERE m.conversa_id = c.id ORDER BY m.created_at DESC LIMIT 1) as ultima_msg_at
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.status = 'ativo'
              AND l.status_pipeline NOT IN ('perdido', 'lead_falso')
              AND l.opt_out_wa IS NOT TRUE
            ORDER BY c.updated_at DESC
            LIMIT %s
        """, (limite * 3,))  # Buscar mais para filtrar
        rows = cur.fetchall()

    retomadas = 0
    for row in rows:
        if retomadas >= limite:
            break

        # Só retomar se a última mensagem é do lead (ficou sem resposta)
        if row["ultima_direcao"] != "recebida":
            continue

        # Verificar se a última msg não é muito antiga (máx 48h)
        if row.get("ultima_msg_at"):
            from datetime import datetime, timedelta
            try:
                agora = datetime.now()
                if hasattr(row["ultima_msg_at"], 'replace'):
                    delta = agora - row["ultima_msg_at"]
                    if delta > timedelta(hours=48):
                        continue  # Muito antigo, não retomar
            except Exception:
                pass

        conversa_id = row["conversa_id"]
        lead_id = row["lead_id"]
        numero = row["numero_envio"]
        ultima_msg = row["ultima_msg"] or ""

        try:
            log.info(f"Retomando conversa {conversa_id} (lead {lead_id}) — "
                     f"sem resposta: {ultima_msg[:80]}")
            decision_log.info(f"RETOMAR conv={conversa_id} lead={lead_id} "
                              f"ultima_msg={ultima_msg[:200]}")

            # Gerar resposta IA para a mensagem não respondida
            resultado_ia = responder_com_ia(conversa_id, ultima_msg)

            if resultado_ia.get("sucesso"):
                resposta = resultado_ia["resposta"]

                # Enviar delay humano
                _time.sleep(_calcular_delay_humano(ultima_msg))

                # Preferencialmente enviar por áudio
                audio_texto = _preparar_texto_para_audio(_preparar_texto_tts(resposta))
                emocao = "amigavel"
                audio_result = _gerar_e_enviar_audio_resposta(
                    numero, audio_texto, conversa_id, emocao=emocao)

                if audio_result.get("sucesso"):
                    # Texto complementar com dados numéricos
                    complemento = _extrair_dados_numericos(resposta)
                    if complemento:
                        _time.sleep(random.uniform(1.5, 3.0))
                        _enviar_e_salvar(conversa_id, numero, complemento)
                    log.info(f"Conversa {conversa_id} retomada por ÁUDIO")
                else:
                    # Fallback: enviar por texto
                    _enviar_e_salvar(conversa_id, numero, resposta, grok=True)
                    log.info(f"Conversa {conversa_id} retomada por TEXTO (áudio falhou)")

                retomadas += 1
                result["retomadas"] += 1

                # Delay entre retomadas para não parecer automático
                _time.sleep(random.uniform(30, 90))
            else:
                log.warning(f"Falha IA retomar conv {conversa_id}: {resultado_ia.get('erro')}")
                result["erros"] += 1

        except Exception as e:
            log.warning(f"Erro retomar conv {conversa_id}: {e}")
            result["erros"] += 1

    if result["retomadas"] > 0:
        log.info(f"Retomadas: {result['retomadas']} conversas sem resposta")

    return result


def followup_conversas_outbound(limite: int = 15) -> dict:
    """Envia follow-up para conversas outbound que ficaram sem resposta do lead.
    Conversas onde o bot enviou mensagem inicial mas o lead não respondeu
    (pode ter respondido mas o webhook não recebeu — Evolution desconectada).
    Envia preferencialmente por áudio para quebrar o gelo.
    Chamado pelo brain_loop."""
    from crm.database import get_conn

    result = {"followups": 0, "erros": 0}

    with get_conn() as conn:
        cur = conn.cursor()
        # Conversas ativas com msgs enviadas mas sem recebidas
        # Enviada entre 1h e 24h atrás (não muito cedo, não muito tarde)
        # Máximo 2 mensagens enviadas (não ficar mandando follow-up infinito)
        cur.execute("""
            SELECT c.id as conversa_id, c.lead_id, c.numero_envio,
                   c.msgs_enviadas,
                   l.nome_fantasia, l.razao_social,
                   (SELECT m.conteudo FROM wa_mensagens m
                    WHERE m.conversa_id = c.id ORDER BY m.created_at DESC LIMIT 1) as ultima_msg
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.status = 'ativo'
              AND c.msgs_recebidas = 0
              AND c.msgs_enviadas BETWEEN 1 AND 2
              AND c.updated_at < NOW() - INTERVAL '1 hour'
              AND c.updated_at > NOW() - INTERVAL '24 hours'
              AND l.opt_out_wa IS NOT TRUE
              AND l.status_pipeline NOT IN ('perdido', 'lead_falso')
            ORDER BY c.updated_at ASC
            LIMIT %s
        """, (limite,))
        rows = cur.fetchall()

    if not rows:
        return result

    log.info(f"Follow-up outbound: {len(rows)} conversas sem resposta do lead")

    for row in rows:
        conversa_id = row["conversa_id"]
        lead_id = row["lead_id"]
        numero = row["numero_envio"]

        # Pular números excluídos ou inválidos
        numero_limpo = _limpar_telefone(numero)
        if numero_limpo in _NUMEROS_EXCLUIDOS or len(numero_limpo) < 8:
            continue

        try:
            lead = {"nome_fantasia": row["nome_fantasia"], "razao_social": row["razao_social"]}
            nome_rest = _limpar_nome_restaurante(lead)

            # Gerar follow-up personalizado — curto e direto
            followup_templates = [
                (f"Oi! Sou a Ana da Derekh Food, mandei uma mensagem mais cedo. "
                 f"Queria te mostrar como o {nome_rest} pode ter delivery próprio "
                 f"sem pagar comissão de iFood. Posso te contar mais?"),
                (f"Oi! Ana da Derekh Food aqui. Mandei mensagem mais cedo sobre "
                 f"uma solução de delivery pra {nome_rest}. Quer dar uma olhada? "
                 f"Tem teste grátis de 15 dias!"),
                (f"Oi! Aqui é a Ana da Derekh Food. Vi que não consegui falar "
                 f"com vocês antes — queria apresentar algo bacana pro {nome_rest}. "
                 f"Posso explicar rapidinho?"),
            ]

            import random
            texto = random.choice(followup_templates)

            decision_log.info(f"FOLLOWUP_OUTBOUND conv={conversa_id} lead={lead_id} "
                              f"num={numero} msgs_env={row['msgs_enviadas']}")

            # Delay humano
            _time.sleep(_calcular_delay_humano(texto))

            # Tentar enviar áudio primeiro (quebrar gelo)
            audio_enviado = False
            tts_ativo = (obter_configuracao("audio_tts_autonomo") or "true").lower() == "true"
            if tts_ativo:
                try:
                    audio_texto = _preparar_texto_para_audio(_preparar_texto_tts(texto))
                    audio_result = _gerar_e_enviar_audio_resposta(
                        numero, audio_texto, conversa_id, emocao="amigavel")
                    if audio_result.get("sucesso"):
                        audio_enviado = True
                        log.info(f"Follow-up ÁUDIO conv {conversa_id} (lead {lead_id})")
                except Exception as e:
                    log.warning(f"Áudio follow-up falhou conv {conversa_id}: {e}")

            if not audio_enviado:
                # Fallback: enviar por texto
                _enviar_e_salvar(conversa_id, numero, texto)
                log.info(f"Follow-up TEXTO conv {conversa_id} (lead {lead_id})")

            result["followups"] += 1

            # Delay entre follow-ups (30-90s)
            _time.sleep(random.uniform(30, 90))

        except Exception as e:
            log.warning(f"Erro follow-up conv {conversa_id}: {e}")
            result["erros"] += 1

    if result["followups"] > 0:
        log.info(f"Follow-up outbound: {result['followups']} conversas contactadas")

    return result


def migrar_conversas_novo_numero(limite: int = 15) -> dict:
    """Migra conversas ativas para novo número.
    Lê o histórico de cada conversa, envia áudio explicando a troca de número
    e depois áudio sobre a Derekh Food. Cria nova conversa para cada lead.
    Chamado manualmente ou pelo brain_loop."""
    from crm.database import get_conn, criar_conversa_wa, registrar_msg_wa

    result = {"migrados": 0, "erros": 0, "pulados": 0}

    with get_conn() as conn:
        cur = conn.cursor()
        # Pegar conversas ativas que ainda não foram migradas
        # (conversas antigas — antes da migração de número)
        cur.execute("""
            SELECT c.id as conversa_id, c.lead_id, c.numero_envio,
                   c.msgs_enviadas, c.msgs_recebidas, c.status,
                   l.nome_fantasia, l.razao_social, l.telefone1, l.telefone2
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.status = 'ativo'
              AND (c.notas NOT LIKE '%%[MIGRADO]%%' OR c.notas IS NULL)
              AND l.opt_out_wa IS NOT TRUE
              AND l.status_pipeline NOT IN ('perdido', 'lead_falso')
            ORDER BY c.msgs_recebidas DESC, c.id ASC
            LIMIT %s
        """, (limite,))
        conversas = cur.fetchall()

    if not conversas:
        log.info("Migração: nenhuma conversa para migrar")
        return result

    log.info(f"Migração novo número: {len(conversas)} conversas")

    for conv in conversas:
        conversa_id = conv["conversa_id"]
        lead_id = conv["lead_id"]
        numero = conv["numero_envio"]
        nome_fantasia = conv["nome_fantasia"] or ""
        razao_social = conv["razao_social"] or ""

        numero_limpo = _limpar_telefone(numero)
        if numero_limpo in _NUMEROS_EXCLUIDOS or len(numero_limpo) < 8:
            result["pulados"] += 1
            continue

        try:
            lead = {"nome_fantasia": nome_fantasia, "razao_social": razao_social}
            nome_rest = _limpar_nome_restaurante(lead)

            # Ler histórico da conversa antiga para contexto
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT direcao, conteudo, tipo FROM wa_mensagens
                    WHERE conversa_id = %s ORDER BY created_at ASC
                """, (conversa_id,))
                historico = cur.fetchall()

            # Resumir contexto da conversa
            ultima_msg_lead = ""
            lead_respondeu = conv["msgs_recebidas"] > 0
            lead_interessado = False
            nome_contato = ""

            for msg in historico:
                if msg["direcao"] == "recebida":
                    ultima_msg_lead = msg["conteudo"] or ""
                    msg_lower = ultima_msg_lead.lower()
                    if any(w in msg_lower for w in ["sim", "quero", "interesse", "pode", "manda", "explica"]):
                        lead_interessado = True
                    # Tentar extrair nome
                    import re
                    match_nome = re.search(
                        r'(?:me chamo|meu nome|sou o|sou a|aqui é o|aqui é a)\s+([A-ZÀ-Ú][a-zà-ú]+)',
                        msg["conteudo"] or "")
                    if match_nome:
                        nome_contato = match_nome.group(1)

            # Gerar mensagem contextual de troca de número
            if lead_respondeu and lead_interessado:
                # Lead demonstrou interesse — mensagem quente
                saudacao = f"Oi{' ' + nome_contato if nome_contato else ''}! "
                texto_troca = (
                    f"{saudacao}Aqui é a Ana da Derekh Food! "
                    f"Tive um probleminha no outro número, mas agora podemos "
                    f"continuar nossa conversa por aqui. "
                    f"Você tinha demonstrado interesse no sistema pro {nome_rest} — "
                    f"vamos continuar de onde paramos?"
                )
            elif lead_respondeu:
                # Lead respondeu mas sem interesse claro
                saudacao = f"Oi{' ' + nome_contato if nome_contato else ''}! "
                texto_troca = (
                    f"{saudacao}Aqui é a Ana da Derekh Food. "
                    f"Desculpa, tive um probleminha no número anterior. "
                    f"Agora é por aqui! Posso te contar como o {nome_rest} "
                    f"pode ter delivery próprio sem pagar comissão?"
                )
            else:
                # Lead não respondeu — reapresentação
                texto_troca = (
                    f"Oi! Aqui é a Ana da Derekh Food. "
                    f"Mandei mensagem por outro número antes mas tive um probleminha. "
                    f"Agora é por aqui! Queria te mostrar como o {nome_rest} "
                    f"pode ter delivery próprio sem comissão de iFood. "
                    f"Posso te explicar rapidinho?"
                )

            decision_log.info(f"MIGRA_NUMERO conv={conversa_id} lead={lead_id} "
                              f"num={numero} respondeu={lead_respondeu} "
                              f"interessado={lead_interessado} nome={nome_contato}")

            # Delay humano (reduzido para migração)
            _time.sleep(random.uniform(2, 5))

            # Enviar áudio 1: explicando a troca de número
            audio_texto_troca = _preparar_texto_para_audio(_preparar_texto_tts(texto_troca))
            audio_ok = False
            try:
                audio_result = _gerar_e_enviar_audio_resposta(
                    numero, audio_texto_troca, conversa_id, emocao="amigavel")
                if audio_result.get("sucesso"):
                    audio_ok = True
                    log.info(f"Migração ÁUDIO troca conv {conversa_id} (lead {lead_id})")
            except Exception as e:
                log.warning(f"Áudio troca falhou conv {conversa_id}: {e}")

            if not audio_ok:
                # Fallback texto
                _enviar_e_salvar(conversa_id, numero, texto_troca)
                log.info(f"Migração TEXTO troca conv {conversa_id} (lead {lead_id})")

            # Delay entre áudios (3-5s)
            _time.sleep(random.uniform(3, 5))

            # Enviar áudio 2: sobre a Derekh Food (só se lead não respondeu ou demonstrou interesse)
            texto_derekh = (
                "A Derekh Food é uma plataforma completa de delivery "
                "feita pra restaurantes que querem vender mais e depender menos "
                "de marketplace. Você tem cardápio digital, gestão de pedidos, "
                "app próprio do motoboy e até atendente com inteligência artificial "
                "no WhatsApp. E o melhor: sem comissão por pedido! "
                "Tem teste grátis de 15 dias. Quer experimentar?"
            )
            audio_texto_derekh = _preparar_texto_para_audio(_preparar_texto_tts(texto_derekh))
            try:
                audio_result2 = _gerar_e_enviar_audio_resposta(
                    numero, audio_texto_derekh, conversa_id, emocao="entusiasmado")
                if audio_result2.get("sucesso"):
                    log.info(f"Migração ÁUDIO derekh conv {conversa_id} (lead {lead_id})")
            except Exception as e:
                log.warning(f"Áudio derekh falhou conv {conversa_id}: {e}")

            # Marcar conversa antiga como migrada
            with get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE wa_conversas
                    SET notas = COALESCE(notas, '') || %s
                    WHERE id = %s
                """, ("\n[MIGRADO] Número trocado — conversa continuada pelo novo número", conversa_id))
                conn.commit()

            result["migrados"] += 1

            # Delay entre leads (8-15s)
            _time.sleep(random.uniform(8, 15))

        except Exception as e:
            log.warning(f"Erro migração conv {conversa_id}: {e}")
            result["erros"] += 1

    log.info(f"Migração concluída: {result}")
    return result
