"""
xAI TTS — Text-to-Speech via Grok.
CRÍTICO: Endpoint correto é /v1/tts (NÃO /v1/audio/speech — retorna 403).
Vozes disponíveis: ara, eve, leo, rex, sal, una
"""
import httpx
import base64
import logging
import os

logger = logging.getLogger("superfood.bot.tts")

XAI_TTS_URL = "https://api.x.ai/v1/tts"

# Regras de pronúncia para TTS (NUNCA alterar texto escrito, só áudio)
_TTS_PRONUNCIA = [
    ("Derekh Food", "Dérikh Food"),
    ("Derekh", "Dérikh"),
    ("derekh", "dérikh"),
    ("DEREKH", "DÉRIKH"),
]


def _preparar_texto_tts(texto: str) -> str:
    """Substitui nomes para pronúncia correta SOMENTE no TTS.
    NUNCA alterar o texto enviado por escrito ao cliente."""
    for escrita, pronuncia in _TTS_PRONUNCIA:
        texto = texto.replace(escrita, pronuncia)
    return texto


async def gerar_audio(texto: str, voz: str = "ara", idioma: str = "pt-BR") -> str | None:
    """Gera áudio TTS via xAI e retorna base64 MP3.

    Args:
        texto: Texto para converter em áudio
        voz: Voz (ara, eve, leo, rex, sal, una)
        idioma: Idioma (pt-BR, en-US, etc.)

    Returns:
        Base64 MP3 string ou None em caso de erro
    """
    xai_key = os.environ.get("XAI_API_KEY", "")
    if not xai_key:
        logger.warning("XAI_API_KEY não configurada — TTS desativado")
        return None

    texto_pronuncia = _preparar_texto_tts(texto)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                XAI_TTS_URL,
                headers={
                    "Authorization": f"Bearer {xai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "text": texto_pronuncia,
                    "voice_id": voz,
                    "language": idioma,
                    "output_format": {
                        "codec": "mp3",
                        "sample_rate": 24000,
                        "bit_rate": 128000,
                    },
                },
            )
            resp.raise_for_status()
            audio_bytes = resp.content
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
            logger.info(f"TTS: {len(texto)} chars → {len(audio_bytes)} bytes, voz={voz}")
            return audio_b64

    except Exception as e:
        logger.error(f"Erro TTS xAI: {e}")
        return None
