"""
fish_tts.py — Fish Audio S2-Pro TTS para o Bot Restaurante.
Módulo dual-mode: funciona quando FISH_API_KEY está configurada,
caso contrário retorna None e o caller faz fallback para xai_tts.

Async — mesmo contrato do xai_tts.gerar_audio(): retorna base64 MP3.

Tags de emoção S2-Pro: [amigável], [empolgado], etc.
São tags livres (linguagem natural em colchetes), sem vocabulário fixo.

API Reference:
  - POST https://api.fish.audio/v1/tts
  - Header: Authorization: Bearer {key}
  - Header: model: s2-pro (obrigatório como header, NÃO no body)
  - Body JSON: {text, reference_id, format, latency, ...}
  - Response: chunked binary audio stream
"""
import os
import base64
import logging

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger("superfood.bot.fish_tts")

FISH_API_URL = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2-pro"

# Pronúncia (mesmas regras do xai_tts.py)
_TTS_PRONUNCIA = [
    ("Derekh Food", "Dérikh Food"),
    ("Derekh", "Dérikh"),
    ("derekh", "dérikh"),
    ("DEREKH", "DÉRIKH"),
]


def _preparar_texto_fish(texto: str, emocao: str = "") -> str:
    """Prepara texto para Fish Audio: pronúncia + tag de emoção opcional."""
    for escrita, pronuncia in _TTS_PRONUNCIA:
        texto = texto.replace(escrita, pronuncia)
    if emocao:
        texto = f"[{emocao}] {texto}"
    return texto


async def gerar_audio(texto: str, voz: str = "", idioma: str = "pt-BR",
                      emocao: str = "") -> str | None:
    """Gera áudio TTS via Fish Audio e retorna base64 MP3.

    Args:
        texto: Texto para converter em áudio
        voz: reference_id do Fish Audio (voice clone ou stock)
        idioma: Idioma (não usado diretamente, Fish detecta automaticamente)
        emocao: Tag de emoção livre (ex: "amigável", "empolgado")

    Returns:
        Base64 MP3 string ou None em caso de erro/sem API key.
    """
    fish_key = os.environ.get("FISH_API_KEY", "")
    if not fish_key:
        logger.debug("FISH_API_KEY não configurada — fallback para xAI")
        return None

    if httpx is None:
        logger.error("httpx não instalado")
        return None

    voice_id = voz or os.environ.get("FISH_VOICE_ID", "")
    texto_preparado = _preparar_texto_fish(texto, emocao)

    try:
        payload = {
            "text": texto_preparado,
            "format": "mp3",
            "latency": "balanced",
        }
        if voice_id:
            payload["reference_id"] = voice_id

        async with httpx.AsyncClient(timeout=30) as client:
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
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"Fish TTS: {len(texto)} chars → {len(audio_bytes)} bytes")
            return audio_b64

    except Exception as e:
        logger.error(f"Erro Fish Audio TTS: {e}")
        return None
