"""
fish_tts.py — Fish Audio S2-Pro TTS para o Sales Bot (Ana).

TTS PRINCIPAL (async). Quando FISH_API_KEY não está configurada, retorna None
e o caller envia texto puro (sem fallback para Grok — economia).

API Reference:
  - POST https://api.fish.audio/v1/tts
  - Header: Authorization: Bearer {key}
  - Header: model: s2-pro
  - Body JSON: {text, reference_id, format, latency, mp3_bitrate, ...}
  - Response: chunked binary audio stream

Emotion tags S2-Pro: tags livres em colchetes — [amigável], [empolgado], etc.
"""
import os
import logging

logger = logging.getLogger("fish_tts")

try:
    import httpx as _httpx
except ImportError:
    _httpx = None

# ============================================================
# CONFIG
# ============================================================
FISH_API_URL = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2-pro"

# Mapeamento de emoções por contexto de venda (S2-Pro tags livres)
EMOTION_TAGS = {
    "abertura": "[amigável] [sorriso]",
    "apresentacao": "[profissional]",
    "beneficio": "[empolgado]",
    "objecao": "[compreensivo] [calmo]",
    "urgencia": "[empolgado] [confiante]",
    "fechamento": "[empolgado] [sorriso]",
    "followup": "[amigável]",
    "suporte": "[calmo] [paciente]",
    "preco": "[profissional] [confiante]",
    "trial": "[empolgado] [animado]",
    "despedida": "[amigável] [caloroso]",
    # Contextos genéricos
    "serio": "[sério]",
    "profissional": "[profissional]",
    "amigavel": "[amigável]",
    "empolgado": "[empolgado]",
    "alivio": "[aliviado]",
    "pausa": "[pausa curta]",
    "risinhos": "[risinhos]",
}

# Emoções compatíveis (para verificar se cache é reutilizável)
EMOCOES_COMPATIVEIS = {
    "abertura": {"amigavel", "followup", "despedida"},
    "amigavel": {"abertura", "followup", "despedida"},
    "empolgado": {"beneficio", "urgencia", "fechamento", "trial"},
    "beneficio": {"empolgado", "urgencia", "trial"},
    "objecao": {"suporte", "calmo"},
    "suporte": {"objecao", "calmo"},
    "profissional": {"preco", "apresentacao", "serio"},
    "preco": {"profissional", "apresentacao"},
}


# ============================================================
# PRONÚNCIA
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


def _preparar_texto_fish(texto: str, emocao: str = "") -> str:
    """Prepara texto para Fish Audio: pronúncia estática + aprendida + tag de emoção."""
    # 1. Regras estáticas (hardcoded)
    for escrita, pronuncia in _TTS_PRONUNCIA:
        texto = texto.replace(escrita, pronuncia)

    # 2. Regras aprendidas do banco de dados (auto-aprendizado)
    try:
        from crm.database import obter_pronuncias_aprendidas
        for escrita, pronuncia in obter_pronuncias_aprendidas():
            texto = texto.replace(escrita, pronuncia)
    except Exception:
        pass  # DB indisponível — usar apenas estáticas

    if emocao:
        tag = EMOTION_TAGS.get(emocao, f"[{emocao}]")
        texto = f"{tag} {texto}"

    return texto


def emocoes_sao_compativeis(emocao_cache: str, emocao_contexto: str) -> bool:
    """Verifica se duas emoções são compatíveis para reutilização de cache."""
    if not emocao_cache and not emocao_contexto:
        return True
    if emocao_cache == emocao_contexto:
        return True
    if not emocao_cache or not emocao_contexto:
        return False
    compativeis = EMOCOES_COMPATIVEIS.get(emocao_contexto, set())
    return emocao_cache in compativeis


def _get_fish_key() -> str:
    """Retorna FISH_API_KEY do ambiente ou config DB."""
    key = os.environ.get("FISH_API_KEY", "")
    if not key:
        try:
            from crm.database import obter_configuracao
            key = obter_configuracao("fish_api_key") or ""
        except Exception:
            pass
    return key


def _get_fish_voice() -> str:
    """Retorna voice/reference_id do Fish Audio."""
    voice = os.environ.get("FISH_VOICE_ID", "")
    if not voice:
        try:
            from crm.database import obter_configuracao
            voice = obter_configuracao("fish_voice_id") or ""
        except Exception:
            pass
    return voice


# ============================================================
# GERAÇÃO TTS — ASYNC (principal)
# ============================================================
async def gerar_audio_fish_async(texto: str, emocao: str = "") -> bytes | None:
    """Gera áudio via Fish Audio S2-Pro (async).

    Args:
        texto: Texto para converter em áudio (já com _preparar_texto_para_audio aplicado)
        emocao: Contexto emocional (chave de EMOTION_TAGS ou texto livre)

    Returns:
        bytes do MP3 ou None em caso de erro/sem API key.
    """
    fish_key = _get_fish_key()
    if not fish_key:
        logger.debug("FISH_API_KEY não configurada — fallback texto puro")
        return None

    if _httpx is None:
        logger.error("httpx não instalado para Fish Audio")
        return None

    texto_preparado = _preparar_texto_fish(texto, emocao)
    voice_id = _get_fish_voice()

    payload = {
        "text": texto_preparado,
        "format": "mp3",
        "latency": "balanced",
        "mp3_bitrate": 128,
    }
    if voice_id:
        payload["reference_id"] = voice_id

    try:
        async with _httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                FISH_API_URL,
                headers={
                    "Authorization": f"Bearer {fish_key}",
                    "Content-Type": "application/json",
                    "model": FISH_MODEL,
                },
                json=payload,
            )
            resp.raise_for_status()
            audio_bytes = resp.content

            if audio_bytes and len(audio_bytes) > 100:
                logger.info(f"Fish Audio TTS: {len(audio_bytes)} bytes, emocao={emocao or 'nenhuma'}")
                return audio_bytes
            else:
                logger.warning(f"Fish Audio: resposta muito pequena ({len(audio_bytes)} bytes)")
                return None

    except _httpx.TimeoutException:
        logger.warning("Fish Audio timeout (30s)")
        return None
    except Exception as e:
        logger.error(f"Erro Fish Audio: {e}")
        return None


# ============================================================
# GERAÇÃO TTS — SYNC (compatibilidade com fluxo existente)
# ============================================================
def gerar_audio_fish(texto: str, emocao: str = "") -> str | None:
    """Gera áudio via Fish Audio S2-Pro (sync — compatibilidade).
    Retorna path do arquivo .mp3 temporário ou None."""
    import tempfile
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Já dentro de event loop — criar task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            audio_bytes = pool.submit(
                asyncio.run, gerar_audio_fish_async(texto, emocao)
            ).result(timeout=35)
    else:
        audio_bytes = asyncio.run(gerar_audio_fish_async(texto, emocao))

    if not audio_bytes:
        return None

    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(audio_bytes)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.error(f"Erro ao salvar áudio Fish: {e}")
        return None
