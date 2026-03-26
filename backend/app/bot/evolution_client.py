"""
Evolution API Client — Enviar/receber mensagens WhatsApp.
Reutiliza mesma integração do Sales Autopilot CRM.
"""
import httpx
import base64
import logging
import os
from typing import Optional

logger = logging.getLogger("superfood.bot.evolution")

# Timeout padrão para chamadas Evolution
_TIMEOUT = 15


async def enviar_texto(
    numero: str,
    texto: str,
    instance: str,
    api_url: str,
    api_key: str,
) -> dict:
    """Envia mensagem de texto via Evolution API."""
    url = f"{api_url.rstrip('/')}/message/sendText/{instance}"
    payload = {
        "number": _normalizar_numero(numero),
        "text": texto,
    }
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Texto enviado para {numero[:8]}*** via {instance}")
        return data


async def enviar_audio_ptt(
    numero: str,
    audio_base64: str,
    instance: str,
    api_url: str,
    api_key: str,
) -> dict:
    """Envia áudio como PTT nativo (bolinha verde) via Evolution API.
    IMPORTANTE: Usar sendWhatsAppAudio (NÃO sendMedia) para PTT nativo."""
    url = f"{api_url.rstrip('/')}/message/sendWhatsAppAudio/{instance}"
    payload = {
        "number": _normalizar_numero(numero),
        "audio": audio_base64,
        "encoding": True,
    }
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Áudio PTT enviado para {numero[:8]}*** via {instance}")
        return data


async def baixar_audio(
    msg_key_id: str,
    instance: str,
    api_url: str,
    api_key: str,
) -> Optional[dict]:
    """Baixa áudio de mensagem recebida via Evolution API.
    Retorna {'base64': str, 'mimetype': str} ou None."""
    url = f"{api_url.rstrip('/')}/chat/getBase64FromMediaMessage/{instance}"
    payload = {"message": {"key": {"id": msg_key_id}}}
    headers = {"apikey": api_key, "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            if data.get("base64"):
                return {"base64": data["base64"], "mimetype": data.get("mimetype", "audio/ogg")}
    except Exception as e:
        logger.error(f"Erro ao baixar áudio {msg_key_id}: {e}")
    return None


async def rejeitar_chamada(
    numero: str,
    instance: str,
    api_url: str,
    api_key: str,
    mensagem_texto: str = "Oi! Manda mensagem que é mais rápido pra eu te ajudar 😊",
) -> dict:
    """Rejeita chamada de voz/vídeo e envia texto pedindo mensagem."""
    return await enviar_texto(numero, mensagem_texto, instance, api_url, api_key)


def _normalizar_numero(numero: str) -> str:
    """Remove caracteres não numéricos e garante formato correto."""
    limpo = "".join(c for c in numero if c.isdigit())
    # Garante que tem código do país
    if len(limpo) <= 11 and not limpo.startswith("55"):
        limpo = "55" + limpo
    return limpo
