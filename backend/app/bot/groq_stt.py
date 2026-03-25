"""
Groq Whisper STT — Transcrição de áudio grátis.
Mesmo serviço usado pelo Sales Autopilot.
Limite: 2000 requests/dia (free tier).
"""
import httpx
import base64
import tempfile
import logging
import os

logger = logging.getLogger("superfood.bot.stt")

GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


async def transcrever_audio(audio_base64: str, idioma: str = "pt") -> dict:
    """Transcreve áudio base64 usando Groq Whisper.

    Args:
        audio_base64: Áudio codificado em base64
        idioma: Código do idioma (pt, en, es, etc.)

    Returns:
        {"texto": str, "idioma": str, "duracao_seg": float}
    """
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_key:
        logger.warning("GROQ_API_KEY não configurada — STT desativado")
        return {"texto": "", "idioma": idioma, "duracao_seg": 0}

    try:
        audio_bytes = base64.b64decode(audio_base64)

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp.seek(0)

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {groq_key}"},
                    files={"file": ("audio.ogg", open(tmp.name, "rb"), "audio/ogg")},
                    data={
                        "model": "whisper-large-v3-turbo",
                        "language": idioma,
                        "response_format": "verbose_json",
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                texto = data.get("text", "").strip()
                duracao = data.get("duration", 0)
                idioma_detectado = data.get("language", idioma)

                logger.info(f"STT: {len(texto)} chars, {duracao:.1f}s, idioma={idioma_detectado}")
                return {
                    "texto": texto,
                    "idioma": idioma_detectado,
                    "duracao_seg": duracao,
                }

    except Exception as e:
        logger.error(f"Erro STT Groq: {e}")
        return {"texto": "", "idioma": idioma, "duracao_seg": 0}
