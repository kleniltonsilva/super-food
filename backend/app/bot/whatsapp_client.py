"""
Cliente unificado WhatsApp — despacha para Meta Cloud API ou Evolution API
baseado no whatsapp_provider do BotConfig.

Uso:
    from .whatsapp_client import enviar_texto, enviar_audio_ptt, ...
    await enviar_texto(numero, texto, bot_config, pool_entry=None)

Regras:
- provider='meta'      → Meta Cloud API oficial (sem ban, sem pool)
- provider='evolution'  → Evolution API Baileys (comportamento atual inalterado)
- Se pool_entry é fornecido E provider='evolution' → usa credenciais do pool
"""
import asyncio
import logging
import subprocess
import tempfile
from typing import Optional

import httpx

from . import evolution_client
from .. import models

logger = logging.getLogger("superfood.bot.wa_client")

META_API_BASE = "https://graph.facebook.com/v21.0"
_META_TIMEOUT = 20


# ============================================================
# HELPERS — resolver credenciais
# ============================================================

def _evo_creds(bot_config: models.BotConfig, pool_entry: Optional[models.BotPhonePool] = None):
    """Retorna (instance, api_url, api_key) para Evolution."""
    if pool_entry:
        return pool_entry.evolution_instance, pool_entry.evolution_api_url, pool_entry.evolution_api_key
    return bot_config.evolution_instance, bot_config.evolution_api_url, bot_config.evolution_api_key


def _meta_headers(bot_config: models.BotConfig) -> dict:
    """Headers Authorization para Meta Cloud API."""
    return {
        "Authorization": f"Bearer {bot_config.meta_access_token}",
        "Content-Type": "application/json",
    }


def _normalizar_numero(numero: str) -> str:
    """Remove caracteres não numéricos e garante formato correto."""
    limpo = "".join(c for c in numero if c.isdigit())
    if len(limpo) <= 11 and not limpo.startswith("55"):
        limpo = "55" + limpo
    return limpo


# ============================================================
# ENVIAR TEXTO
# ============================================================

async def enviar_texto(
    numero: str,
    texto: str,
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
    delay_ms: int = 1500,
) -> dict:
    """Envia texto para o cliente."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        return await _meta_enviar_texto(numero, texto, bot_config)
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        return await evolution_client.enviar_texto(numero, texto, inst, url, key, delay_ms=delay_ms)


async def _meta_enviar_texto(numero: str, texto: str, bot_config: models.BotConfig) -> dict:
    """Envia texto via Meta Cloud API."""
    url = f"{META_API_BASE}/{bot_config.meta_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalizar_numero(numero),
        "type": "text",
        "text": {"body": texto},
    }
    async with httpx.AsyncClient(timeout=_META_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=_meta_headers(bot_config))
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Meta texto enviado para {numero[:8]}***")
        return data


# ============================================================
# ENVIAR ÁUDIO PTT
# ============================================================

async def enviar_audio_ptt(
    numero: str,
    audio_b64: str,
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
    delay_ms: int = 3000,
) -> dict:
    """Envia áudio PTT (bolinha verde). Meta exige OGG/Opus."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        return await _meta_enviar_audio_ptt(numero, audio_b64, bot_config)
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        return await evolution_client.enviar_audio_ptt(numero, audio_b64, inst, url, key, delay_ms=delay_ms)


async def _meta_enviar_audio_ptt(numero: str, audio_b64: str, bot_config: models.BotConfig) -> dict:
    """Meta: converte MP3→OGG/Opus, faz upload, envia com voice:true."""
    import base64

    mp3_bytes = base64.b64decode(audio_b64)

    # Converter MP3 → OGG/Opus (requisito Meta para PTT)
    ogg_bytes = await _mp3_to_ogg_opus(mp3_bytes)
    if not ogg_bytes:
        # Fallback: enviar como texto se conversão falhar
        logger.warning("Conversão MP3→OGG falhou, áudio Meta ignorado")
        raise RuntimeError("Conversão MP3→OGG/Opus falhou (ffmpeg indisponível?)")

    # 1. Upload media
    upload_url = f"{META_API_BASE}/{bot_config.meta_phone_number_id}/media"
    headers_auth = {"Authorization": f"Bearer {bot_config.meta_access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        files = {
            "file": ("audio.ogg", ogg_bytes, "audio/ogg"),
            "messaging_product": (None, "whatsapp"),
            "type": (None, "audio/ogg"),
        }
        resp = await client.post(upload_url, files=files, headers=headers_auth)
        resp.raise_for_status()
        media_id = resp.json().get("id")

    if not media_id:
        raise RuntimeError("Upload de áudio Meta falhou — sem media_id")

    # 2. Enviar áudio com voice: true (bolinha verde)
    msg_url = f"{META_API_BASE}/{bot_config.meta_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalizar_numero(numero),
        "type": "audio",
        "audio": {"id": media_id, "voice": True},
    }
    async with httpx.AsyncClient(timeout=_META_TIMEOUT) as client:
        resp = await client.post(msg_url, json=payload, headers=_meta_headers(bot_config))
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Meta áudio PTT enviado para {numero[:8]}***")
        return data


# ============================================================
# TYPING INDICATOR
# ============================================================

async def enviar_typing(
    numero: str,
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
    presenca: str = "composing",
    delay_ms: int = 15000,
):
    """Envia indicador de digitação/gravação."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        await _meta_enviar_typing(numero, bot_config)
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        await evolution_client.enviar_presenca_conversa(numero, inst, url, key, presenca=presenca, delay_ms=delay_ms)


async def _meta_enviar_typing(numero: str, bot_config: models.BotConfig):
    """Meta: typing_indicator (dura 25s, precisa re-enviar se processo demorar mais)."""
    url = f"{META_API_BASE}/{bot_config.meta_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalizar_numero(numero),
        "type": "typing_indicator",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=_meta_headers(bot_config))
            resp.raise_for_status()
    except Exception as e:
        logger.debug(f"Meta typing indicator falhou: {e}")


# ============================================================
# MARK AS READ
# ============================================================

async def marcar_lida(
    msg_id: str,
    bot_config: models.BotConfig,
):
    """Marca mensagem como lida. Só funciona no Meta (Evolution faz auto)."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider != "meta":
        return  # Evolution marca automaticamente

    url = f"{META_API_BASE}/{bot_config.meta_phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": msg_id,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload, headers=_meta_headers(bot_config))
            resp.raise_for_status()
    except Exception as e:
        logger.debug(f"Meta mark as read falhou: {e}")


# ============================================================
# DEFINIR PRESENÇA (ONLINE/OFFLINE)
# ============================================================

async def definir_presenca(
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
    presenca: str = "available",
):
    """Define presença (online/offline). Meta não suporta — noop."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        return  # Meta não tem setPresence
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        await evolution_client.definir_presenca(inst, url, key, presenca)


# ============================================================
# ENVIAR PRESENÇA NA CONVERSA (recording/composing)
# ============================================================

async def enviar_presenca_conversa(
    numero: str,
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
    presenca: str = "composing",
    delay_ms: int = 3000,
):
    """Envia indicador de presença na conversa (composing/recording)."""
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        # Meta não diferencia composing/recording — usa typing_indicator
        await _meta_enviar_typing(numero, bot_config)
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        await evolution_client.enviar_presenca_conversa(numero, inst, url, key, presenca=presenca, delay_ms=delay_ms)


# ============================================================
# BAIXAR ÁUDIO (mensagem recebida do cliente)
# ============================================================

async def baixar_audio(
    media_id_or_msg_key: str,
    bot_config: models.BotConfig,
    pool_entry: Optional[models.BotPhonePool] = None,
) -> Optional[dict]:
    """Baixa áudio de mensagem recebida.
    Meta: media_id → GET URL → GET binary
    Evolution: msg_key_id → getBase64FromMediaMessage
    Retorna {'base64': str, 'mimetype': str} ou None.
    """
    provider = getattr(bot_config, "whatsapp_provider", "") or "evolution"

    if provider == "meta":
        return await _meta_baixar_audio(media_id_or_msg_key, bot_config)
    else:
        inst, url, key = _evo_creds(bot_config, pool_entry)
        return await evolution_client.baixar_audio(media_id_or_msg_key, inst, url, key)


async def _meta_baixar_audio(media_id: str, bot_config: models.BotConfig) -> Optional[dict]:
    """Meta: 2 passos — GET media URL → GET binary."""
    import base64

    headers = {"Authorization": f"Bearer {bot_config.meta_access_token}"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Obter URL do media
            resp = await client.get(f"{META_API_BASE}/{media_id}", headers=headers)
            resp.raise_for_status()
            media_url = resp.json().get("url")
            mimetype = resp.json().get("mime_type", "audio/ogg")

            if not media_url:
                logger.error(f"Meta baixar_audio: sem URL para media_id={media_id}")
                return None

            # 2. Download binary
            resp2 = await client.get(media_url, headers=headers)
            resp2.raise_for_status()

            audio_b64 = base64.b64encode(resp2.content).decode()
            logger.info(f"Meta áudio baixado: {len(resp2.content)} bytes, {mimetype}")
            return {"base64": audio_b64, "mimetype": mimetype}

    except Exception as e:
        logger.error(f"Erro baixando áudio Meta {media_id}: {e}")
        return None


# ============================================================
# CONVERSÃO MP3 → OGG/Opus (requisito Meta para PTT voice:true)
# ============================================================

async def _mp3_to_ogg_opus(mp3_bytes: bytes) -> Optional[bytes]:
    """Converte MP3 → OGG/Opus via ffmpeg em memória (stdin/stdout).
    Retorna bytes OGG ou None se ffmpeg não disponível."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-i", "pipe:0",
            "-c:a", "libopus", "-b:a", "64k",
            "-f", "ogg", "pipe:1",
            "-loglevel", "error",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(input=mp3_bytes), timeout=15)

        if proc.returncode != 0:
            logger.error(f"ffmpeg erro: {stderr.decode()[:200]}")
            return None

        if len(stdout) < 100:
            logger.error("ffmpeg output muito pequeno — conversão falhou")
            return None

        logger.debug(f"MP3→OGG/Opus: {len(mp3_bytes)}→{len(stdout)} bytes")
        return stdout

    except FileNotFoundError:
        logger.warning("ffmpeg não encontrado — áudio Meta PTT indisponível")
        return None
    except asyncio.TimeoutError:
        logger.error("ffmpeg timeout (15s)")
        return None
    except Exception as e:
        logger.error(f"Erro conversão MP3→OGG: {e}")
        return None
