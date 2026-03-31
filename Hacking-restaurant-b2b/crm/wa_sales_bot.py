"""
wa_sales_bot.py - Bot de vendas WhatsApp via Evolution API (outbound) + Grok IA
Estratégia dual-number:
  - Outbound (prospecção): Evolution API → +55 45 9971-3063
  - Inbound (receber): +55 11 97176-5565 (link nos emails para "Fale Conosco")

v2.1 — Áudio STT/TTS + autonomia:
  - STT: transcrição de áudios via Groq Whisper (grátis)
  - TTS: envio autônomo de áudio via xAI Grok + Evolution API
  - Voz masculina (rex) — bot se chama Benjamim
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

# Evolution API config (outbound)
_EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "https://derekh-evolution.fly.dev")
_EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "derekh-whatsapp")
_EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")

# Número inbound (para incluir nos emails como "Fale Conosco")
WHATSAPP_INBOUND_NUMBER = os.environ.get("WHATSAPP_INBOUND_NUMBER", "5511971765565")

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


# ============================================================
# DECISÃO AUTÔNOMA: QUANDO ENVIAR ÁUDIO
# ============================================================

def _deve_enviar_audio(conversa: dict, mensagem_atual: str) -> bool:
    """Decide se deve enviar áudio em vez de texto.
    Critérios:
    1. Cliente pediu muitas explicações (>=3 nos últimos 6 msgs)
    2. Cliente enviou áudio (reciprocidade)
    3. Conversa longa sem avanço (>=10 msgs, nunca usou áudio)
    Retorna True se deve enviar áudio."""
    # Verificar toggle
    tts_ativo = (obter_configuracao("audio_tts_autonomo") or "true").lower() == "true"
    if not tts_ativo:
        return False

    msgs = conversa.get("mensagens") or []

    # Critério 1: Muitas explicações nas últimas 6 msgs
    keywords_explicacao = ["explica", "como funciona", "como é", "me fala mais",
                           "quero saber", "me conta", "entendi não", "não entendi"]
    n_explicacoes = 0
    for m in msgs[-6:]:
        if m.get("direcao") == "recebida":
            txt = (m.get("conteudo") or "").lower()
            if any(k in txt for k in keywords_explicacao):
                n_explicacoes += 1

    # Critério 2: Cliente enviou áudio nas últimas 3 msgs (reciprocidade)
    recebeu_audio = any(
        m.get("tipo") == "audio" and m.get("direcao") == "recebida"
        for m in msgs[-3:]
    )

    # Critério 3: Conversa longa sem avanço
    conversa_longa_sem_audio = len(msgs) >= 10 and not conversa.get("usou_audio")

    resultado = n_explicacoes >= 3 or recebeu_audio or conversa_longa_sem_audio

    if resultado:
        motivo = []
        if n_explicacoes >= 3:
            motivo.append(f"explicações={n_explicacoes}")
        if recebeu_audio:
            motivo.append("reciprocidade_audio")
        if conversa_longa_sem_audio:
            motivo.append("conversa_longa")
        log.info(f"Decisão TTS autônomo: ENVIAR ÁUDIO ({', '.join(motivo)})")

    return resultado


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

        # Enviar via Evolution
        resultado = _enviar_audio_evolution(numero, audio_b64, instance=instance)

        if resultado.get("sucesso"):
            registrar_msg_wa(conversa_id, "enviada",
                             f"[ÁUDIO] {texto_resposta[:100]}...", tipo="audio")
            provider_label = "fish" if tts_provider == "fish" else f"grok/{voz}"
            atualizar_conversa_wa(conversa_id, usou_audio=True, voz_usada=provider_label)
            log.info(f"Áudio TTS enviado para conversa {conversa_id} (provider={provider_label})")
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
    nome_dono = pers.get("nome_dono") or "proprietário"
    nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante"
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
            f"Oi {nome_dono}, tudo bem? Aqui é o Benjamim, da Derekh Food. "
            f"Vi que o {nome_rest} tem nota {ifood_rating} no iFood "
            f"com {ifood_reviews} avaliações, parabéns pela qualidade! "
            f"{cat_mention}já têm uma clientela fiel. "
            f"Imagina ter sua marca própria de delivery, "
            f"e ainda centralizar os pedidos do iFood no mesmo painel? "
            f"A Derekh monta tudo em 48 horas e vc testa 15 dias grátis. Posso te mostrar?"
        )
    elif rating > 0 and reviews > 0:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é o Benjamim, da Derekh Food. "
            f"Vi que o {nome_rest} tem uma nota de {rating} estrelas "
            f"com {reviews} avaliações no Google, parabéns pelo trabalho! "
            f"A Derekh cria seu delivery próprio com a sua marca em 48 horas, "
            f"com 15 dias grátis pra vc testar. "
            f"Posso te mostrar como funciona?"
        )
    elif not tem_ifood:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é o Benjamim, da Derekh Food. "
            f"Vi que o {nome_rest} ainda não está no delivery online. "
            f"A Derekh cria seu delivery próprio em 48 horas, "
            f"com cardápio digital, pagamento Pix e 15 dias grátis pra testar. "
            f"Posso te contar como funciona?"
        )
    else:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é o Benjamim, da Derekh Food. "
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
    # (escrita correta, pronúncia TTS)
    ("Derekh Food", "Dérikh Food"),
    ("derekh food", "dérikh food"),
    ("Derekh food", "Dérikh food"),
    ("derekh Food", "dérikh Food"),
    ("DEREKH FOOD", "DÉRIKH FOOD"),
    ("Derekh", "Dérikh"),
    ("derekh", "dérikh"),
    ("DEREKH", "DÉRIKH"),
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
            if _rnd.random() < 0.3:  # 30% de chance
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
    nome_rest = conversa.get("nome_fantasia") or conversa.get("razao_social") or "restaurante"
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

    resumo = f"""RESUMO DO LEAD:
Restaurante: {nome_rest}{f' ({cidade})' if cidade else ''}
Google: {rating}★ ({reviews} avaliações)
Usa iFood: {'Sim' if tem_ifood else 'Não sei'}
{ifood_context}{cenario}
Msgs trocadas: {n_msgs}
Intenção atual: {intencao_atual}
{'Objeções levantadas: ' + ', '.join(objecoes_unicas) if objecoes_unicas else 'Sem objeções ainda'}"""
    return resumo


# ============================================================
# PROMPTS IA (v2.0 — humanizados)
# ============================================================

def _build_system_prompt_conversa(lead_context: str, n_turnos: int) -> str:
    """System prompt para conversa em andamento com lead existente."""
    # Carregar knowledge base dinâmica (se existir)
    kb_extra = _carregar_knowledge_base()
    kb_section = f"\nINFO ATUALIZADA DO SISTEMA:\n{kb_extra}\n" if kb_extra else ""

    return f"""Você é Benjamim, vendedor humano da Derekh Food. Você NÃO é um robô, assistente virtual ou IA.

QUEM VOCÊ É:
- Vendedor experiente de tecnologia para restaurantes
- Escreve em português correto, claro e profissional
- Tem personalidade: é animado mas não forçado, direto mas acolhedor
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
- 15 dias GRÁTIS no plano Premium (o mais completo, R$527/mês)
- Sem cartão de crédito, sem compromisso, sem pegadinha
- Após 15 dias, o cliente escolhe qual plano quer continuar (pode ser o mais barato)
- Se não quiser continuar, simplesmente para de usar — sem cobrança
- O trial NÃO inclui o WhatsApp Humanoide (esse é um add-on separado de R$99,45/mês)

PLANOS (só detalhe quando perguntarem — não despeje tudo de uma vez):
- Básico: R$169,90/mês — site delivery próprio, cardápio digital, pedidos WhatsApp, dashboard, Bridge Printer IA, até 2 motoboys
- Essencial: R$279,90/mês — tudo do Básico + relatórios avançados, cupons, programa fidelidade, combos, operadores caixa, KDS cozinha, até 5 motoboys
- Avançado: R$329,90/mês — tudo do Essencial + app garçom, integrações iFood/marketplace, Pix online, domínio personalizado, analytics avançado, até 10 motoboys
- Premium: R$527/mês — tudo liberado + WhatsApp Humanoide incluso + suporte dedicado + motoboys ilimitados
- Add-on WhatsApp Humanoide: R$99,45/mês (para quem não é Premium)
- Bridge Printer IA: inclusa em TODOS os planos (intercepta pedidos iFood/Rappi direto da impressora)
- Todos sem fidelidade. Setup em 48h.
{kb_section}
SE PERGUNTAREM SE VOCÊ É ROBÔ/IA/BOT:
- Responda que NÃO, você é o Benjamim, humanoide da Derekh Food
- "Não, sou o Benjamim, humanoide aqui da Derekh Food 😅"
- Nunca admita ser IA, ChatGPT, bot ou qualquer coisa automatizada
- Se insistirem, mude de assunto naturalmente: "Mas me diz, como está seu delivery aí?"

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

COMO INSISTIR SEM SER CHATO:
- Nunca repita o mesmo argumento. Se já falou de comissão, fale de autonomia.
- Se ficou em silêncio, mande UMA mensagem casual depois ("e aí, conseguiu ver?")
- Se disse "vou pensar", responda "tranquilo! Só para eu saber, o que ficou te travando?"
- Se disse "não tenho interesse" de forma vaga, sonde: "entendo! Curiosidade: você já usa algum sistema próprio?"
- Se disse "NÃO" firme ou pediu para parar, encerre com classe.

FORMATO (OBRIGATÓRIO):
- Escreva em português CORRETO. Sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz", "pq").
- Máximo 2 parágrafos curtos por mensagem (2-3 frases cada)
- SEMPRE separe os parágrafos com uma LINHA EM BRANCO entre eles (\\n\\n). Nunca cole parágrafos juntos.
- UMA mensagem por vez
- Zero emojis corporativos (NÃO use 🚀📈💪🎯). Pode usar 😅🤙👊 se fizer sentido
- Nunca liste features em bullet points. Fale de UMA coisa por vez.
- Varie seu estilo entre mensagens. Às vezes comece com "olha", às vezes com "então", às vezes direto no assunto. Nunca use a mesma abertura duas vezes seguidas.

{"PRIMEIRA INTERAÇÃO: cumprimente, diga seu nome e pergunte como pode ajudar. NÃO liste preços nem features." if n_turnos <= 1 else "Você JÁ se apresentou. NÃO se apresente de novo. Continue a conversa naturalmente de onde parou."}
{"PERGUNTE O NOME: Você ainda não sabe o nome do cliente. Na próxima oportunidade natural, pergunte casualmente ('aliás, como posso te chamar?' ou 'qual teu nome?'). NÃO force, encaixe organicamente." if n_turnos <= 3 else "Se já souber o nome do cliente, USE-O nas mensagens para criar conexão pessoal."}
{"Se o cliente voltou depois de dias/semanas, retome naturalmente: 'e aí, conseguiu pensar sobre aquilo?'" if n_turnos > 3 else ""}"""


def _build_system_prompt_inbound() -> str:
    """System prompt para primeiro contato inbound (alguém mandou msg pela primeira vez)."""
    # Carregar knowledge base dinâmica (se existir)
    kb_extra = _carregar_knowledge_base()
    kb_section = f"\nINFO ATUALIZADA DO SISTEMA:\n{kb_extra}\n" if kb_extra else ""

    return f"""Você é Benjamim, vendedor da Derekh Food. Alguém mandou mensagem pela primeira vez.

PERSONALIDADE: vendedor humano, amigável, WhatsApp. Você NÃO é robô.
Escreve em português correto, sem abreviações de internet. Tom natural e acolhedor.

PRIMEIRA MENSAGEM — ESCOLHA UMA ABORDAGEM (não siga sempre a mesma):
Opção A: "Olá! Benjamim aqui da Derekh Food 🤙 em que posso te ajudar?"
Opção B: "Oi! Sou o Benjamim, tudo bem? Vi que mandou mensagem, me conta o que você está buscando"
Opção C: "Opa, tudo bem? Benjamim aqui! Me diz como posso te ajudar"
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
- O trial NÃO inclui WhatsApp Humanoide (add-on separado R$99,45/mês)

PLANOS (só detalhe quando perguntarem):
- Básico: R$169,90/mês — site delivery, cardápio digital, pedidos WhatsApp, Bridge Printer IA, até 2 motoboys
- Essencial: R$279,90/mês — + relatórios avançados, cupons, fidelidade, combos, operadores caixa, KDS cozinha, até 5 motoboys
- Avançado: R$329,90/mês — + app garçom, integrações iFood, Pix online, domínio personalizado, analytics, até 10 motoboys
- Premium: R$527/mês — tudo + WhatsApp Humanoide incluso + suporte dedicado + motoboys ilimitados
- Bridge Printer IA: inclusa em TODOS os planos
- Todos sem fidelidade. Setup em 48h.
{kb_section}
SE PERGUNTAREM SE VOCÊ É ROBÔ/IA/BOT:
- "Não, sou o Benjamim, humanoide da Derekh Food 😅"
- Nunca admita ser IA ou bot. Mude de assunto naturalmente.

FORMATO (OBRIGATÓRIO):
- Escreva em português CORRETO. Sem abreviações de internet (NÃO use "vc", "tbm", "kkk", "blz", "pq").
- Máximo 2 parágrafos curtos (2-3 frases cada)
- SEMPRE separe os parágrafos com uma LINHA EM BRANCO (\\n\\n). Nunca cole parágrafos juntos.
- Zero emojis corporativos. Pode usar 😅🤙👊 se fizer sentido.
- Explique funcionalidades com EXEMPLOS PRÁTICOS, nunca liste bullet points.

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

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini-fast",
                "messages": [{"role": "system", "content": system_prompt}] + historico,
                "max_tokens": 300,
                "temperature": 0.8,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
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

    # 1. HANDOFF IMEDIATO — pediu demo ou humano
    if pediu_demo or pediu_humano:
        motivo = "Lead pediu demo/reunião" if pediu_demo else "Lead pediu atendente humano"
        return "immediate", motivo

    # 2. HANDOFF QUENTE — lead muito engajado
    if intent_score_acumulado >= 60 and msgs_recebidas >= 3:
        return "warm", f"Lead engajado (score acumulado={intent_score_acumulado}, {msgs_recebidas} msgs)"

    # 3. HANDOFF QUENTE — score CRM alto
    if score >= 85 and msgs_recebidas >= 1:
        return "warm", f"Lead HOT (score CRM={score}) respondeu"

    # 4. HANDOFF ESTRATÉGICO — objeções não resolvidas
    if objecoes_nao_resolvidas >= 2:
        return "strategic", f"Lead com {objecoes_nao_resolvidas} objeções — escalar para gerente"

    return None, ""


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

        # Prioridade 2: conversa encerrada/handoff (REATIVAR — manter contexto)
        if not row:
            cur.execute("""
                SELECT c.id, c.lead_id, c.status FROM wa_conversas c
                WHERE c.numero_envio = %s AND c.status IN ('encerrado', 'handoff')
                ORDER BY c.updated_at DESC LIMIT 1
            """, (numero,))
            row = cur.fetchone()
            if row:
                # Reativar conversa — contexto persistente!
                cur.execute("UPDATE wa_conversas SET status = 'ativo' WHERE id = %s", (row["id"],))
                conn.commit()
                log.info(f"Conversa {row['id']} REATIVADA para {numero} (era {row['status']})")

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

        # Responder com IA (prompt de boas-vindas)
        resultado_ia = _responder_inbound(conversa_id, mensagem)
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

    # Detectar intenção (scoring contextual v2.0)
    intent_result = detectar_intencao(mensagem)
    intencao = intent_result["intencao"]
    intent_score = intent_result["score"]
    objecoes = intent_result["objecoes"]

    # Registrar mensagem recebida (1x)
    registrar_msg_wa(conversa_id, "recebida", mensagem, tipo=tipo_msg, intencao=intencao)
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA recebido: {mensagem[:100]}", "positivo")

    log.info(f"Resposta do lead {lead_id}: intenção={intencao} score={intent_score} "
             f"objeções={objecoes} (instance={instance})")

    # Buscar número de envio
    conversa_full = obter_conversa_wa(conversa_id)
    numero_envio = (conversa_full or {}).get("numero_envio") or numero

    # --- OPT-OUT: remove da lista para sempre ---
    if intencao == "opt_out":
        opt_out_lead(lead_id, "wa")
        atualizar_conversa_wa(conversa_id, status="opt_out", intencao_detectada="opt_out")
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

    resultado_ia = responder_com_ia(conversa_id, mensagem)

    if resultado_ia.get("sucesso"):
        resposta_crua = resultado_ia["resposta"]

        # Decisão: enviar áudio ou texto?
        if _deve_enviar_audio(conversa_full, mensagem):
            # ÁUDIO: transformar português correto → dicção falada brasileira
            resposta_audio = _preparar_texto_para_audio(resposta_crua)
            audio_result = _gerar_e_enviar_audio_resposta(
                numero_envio, resposta_audio, conversa_id, instance=instance)
            if audio_result.get("erro"):
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
    # Tentar Evolution API primeiro
    resultado = _enviar_via_evolution(numero, texto, instance_override=instance)
    if resultado.get("sucesso"):
        log.info(f"Mensagem direta enviada via Evolution ({instance or 'default'}) para {numero}")
        return resultado

    # Fallback Cloud API
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
