"""
fish_tts.py — Fish Audio S2-Pro TTS para o Sales Bot (Benjamim).
Módulo dual-mode: funciona quando FISH_API_KEY está configurada,
caso contrário retorna None e o caller faz fallback para Grok.

Usa SDK oficial: pip install fish-audio-sdk
Fallback para API raw (httpx) se SDK não estiver instalado.

Tags de emoção S2-Pro: [amigável], [empolgado], [profissional], etc.
São tags livres (linguagem natural em colchetes), sem vocabulário fixo.

API Reference:
  - POST https://api.fish.audio/v1/tts
  - Header: Authorization: Bearer {key}
  - Header: model: s2-pro (obrigatório como header, NÃO no body)
  - Body JSON: {text, reference_id, format, latency, ...}
  - Response: chunked binary audio stream
"""
import os
import tempfile
import logging

logger = logging.getLogger("fish_tts")

# Tentar importar SDK oficial
try:
    from fishaudio import FishAudio
    _HAS_SDK = True
    logger.info("fish-audio-sdk importado com sucesso")
except ImportError:
    _HAS_SDK = False
    logger.info("fish-audio-sdk não instalado — usando API raw (httpx)")

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
    "abertura": "[amigável e caloroso]",
    "apresentacao": "[profissional e confiante]",
    "beneficio": "[empolgado]",
    "objecao": "[compreensivo e paciente]",
    "urgencia": "[entusiasmado]",
    "fechamento": "[confiante e animado]",
    "followup": "[simpático e casual]",
    "suporte": "[prestativo e calmo]",
}


# ============================================================
# PRONÚNCIA (mesmas regras do Grok TTS)
# ============================================================
_TTS_PRONUNCIA = [
    ("Derekh Food", "Dérikh Food"),
    ("derekh food", "dérikh food"),
    ("Derekh food", "Dérikh food"),
    ("derekh Food", "dérikh Food"),
    ("DEREKH FOOD", "DÉRIKH FOOD"),
    ("Derekh", "Dérikh"),
    ("derekh", "dérikh"),
    ("DEREKH", "DÉRIKH"),
]


def _preparar_texto_fish(texto: str, emocao: str = "") -> str:
    """Prepara texto para Fish Audio: pronúncia + tag de emoção opcional.
    Se emocao não fornecida, não adiciona tag (voz natural sem emoção forçada)."""
    # Pronúncia
    for escrita, pronuncia in _TTS_PRONUNCIA:
        texto = texto.replace(escrita, pronuncia)

    # Tag de emoção (S2-Pro suporta tags livres em colchetes)
    if emocao:
        tag = EMOTION_TAGS.get(emocao, f"[{emocao}]")
        texto = f"{tag} {texto}"

    return texto


def _get_fish_key() -> str:
    """Retorna FISH_API_KEY do ambiente."""
    return os.environ.get("FISH_API_KEY", "")


def _get_fish_voice() -> str:
    """Retorna voice/reference_id do Fish Audio.
    Pode ser um ID de voz clonada ou voz stock."""
    return os.environ.get("FISH_VOICE_ID", "")


# ============================================================
# GERAÇÃO TTS — SDK (convert retorna bytes diretamente)
# ============================================================
def _gerar_via_sdk(texto: str, voice_id: str) -> bytes | None:
    """Gera áudio via SDK oficial fish-audio-sdk.
    SDK: client.tts.convert() retorna bytes diretamente."""
    if not _HAS_SDK:
        return None

    try:
        client = FishAudio(api_key=_get_fish_key())

        kwargs = {"text": texto, "format": "mp3"}
        if voice_id:
            kwargs["reference_id"] = voice_id

        result = client.tts.convert(**kwargs)

        # convert() retorna bytes; stream() retorna iterator
        if isinstance(result, (bytes, bytearray)):
            return bytes(result)

        # Fallback: se a API mudar e retornar iterator
        if hasattr(result, '__iter__'):
            chunks = []
            for chunk in result:
                if isinstance(chunk, (bytes, bytearray)):
                    chunks.append(chunk)
            audio = b"".join(chunks)
            return audio if audio else None

        return None

    except Exception as e:
        logger.error(f"Erro Fish Audio SDK: {e}")
        return None


# ============================================================
# GERAÇÃO TTS — API RAW (fallback se SDK não instalado)
# ============================================================
def _gerar_via_api(texto: str, voice_id: str) -> bytes | None:
    """Gera áudio via API REST direta (httpx).
    IMPORTANTE: 'model' é header, NÃO campo do body."""
    if _httpx is None:
        logger.error("httpx não instalado para Fish Audio API raw")
        return None

    fish_key = _get_fish_key()
    if not fish_key:
        return None

    try:
        payload = {
            "text": texto,
            "format": "mp3",
            "latency": "balanced",
        }
        if voice_id:
            payload["reference_id"] = voice_id

        resp = _httpx.post(
            FISH_API_URL,
            headers={
                "Authorization": f"Bearer {fish_key}",
                "Content-Type": "application/json",
                "model": FISH_MODEL,
            },
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.content

    except Exception as e:
        logger.error(f"Erro Fish Audio API raw: {e}")
        return None


# ============================================================
# FUNÇÃO PRINCIPAL — mesmo contrato do gerar_audio_tts()
# ============================================================
def gerar_audio_fish(texto: str, emocao: str = "") -> str | None:
    """Gera áudio via Fish Audio S2-Pro.

    Args:
        texto: Texto para converter em áudio
        emocao: Contexto emocional (chave de EMOTION_TAGS ou texto livre)

    Returns:
        Path do arquivo .mp3 temporário ou None em caso de erro/sem API key.
        Caller é responsável por deletar o arquivo após uso.
    """
    fish_key = _get_fish_key()
    if not fish_key:
        logger.debug("FISH_API_KEY não configurada — fallback para provider padrão")
        return None

    # Preparar texto com pronúncia + emoção
    texto_preparado = _preparar_texto_fish(texto, emocao)
    voice_id = _get_fish_voice()

    # Tentar SDK primeiro, fallback para API raw
    audio_bytes = None
    if _HAS_SDK:
        audio_bytes = _gerar_via_sdk(texto_preparado, voice_id)
    if audio_bytes is None:
        audio_bytes = _gerar_via_api(texto_preparado, voice_id)

    if not audio_bytes:
        logger.warning("Fish Audio: nenhum áudio gerado")
        return None

    # Salvar em arquivo temporário (mesmo padrão do Grok TTS)
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(audio_bytes)
        tmp.close()
        logger.info(f"Fish Audio TTS: {tmp.name} ({len(audio_bytes)} bytes, "
                     f"emocao={emocao or 'nenhuma'})")
        return tmp.name
    except Exception as e:
        logger.error(f"Erro ao salvar áudio Fish: {e}")
        return None
