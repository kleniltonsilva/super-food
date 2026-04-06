"""
Meta Phone Manager — Registro self-service de números WhatsApp Business.

Suporta dois fluxos:
1. **Embedded Signup** (novo): Restaurante conecta via popup Facebook → BISU token per-restaurante
2. **BSP/Global token** (legado): System User Token global + WABA compartilhada

API Reference: https://developers.facebook.com/docs/whatsapp/business-management-api
"""
import logging
import os
import secrets
from typing import Optional

import httpx

logger = logging.getLogger("superfood.bot.phone_manager")

META_API_BASE = "https://graph.facebook.com/v22.0"
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_WABA_ID = os.getenv("META_WABA_ID", "1486557139857851")
META_APP_ID = os.getenv("META_APP_ID", "874086172333541")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
_TIMEOUT = 20


class MetaApiError(Exception):
    """Erro da API Meta com detalhes estruturados."""

    def __init__(self, message: str, status_code: int = 0, error_code: int = 0, error_subcode: int = 0):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.error_subcode = error_subcode
        super().__init__(message)


def _headers(token: Optional[str] = None) -> dict:
    t = token or META_ACCESS_TOKEN
    return {
        "Authorization": f"Bearer {t}",
        "Content-Type": "application/json",
    }


def _raise_if_error(resp: httpx.Response, context: str = ""):
    """Levanta MetaApiError se resposta indica erro."""
    if resp.status_code >= 400:
        try:
            data = resp.json()
            err = data.get("error", {})
            msg = err.get("message", resp.text[:200])
            code = err.get("code", 0)
            subcode = err.get("error_subcode", 0)
        except Exception:
            msg = resp.text[:200]
            code = 0
            subcode = 0
        logger.error(f"Meta API error ({context}): {resp.status_code} - {msg}")
        raise MetaApiError(
            message=msg,
            status_code=resp.status_code,
            error_code=code,
            error_subcode=subcode,
        )


async def trocar_code_por_token(code: str) -> str:
    """Troca o authorization code do Embedded Signup por um BISU token permanente.

    GET /oauth/access_token?client_id={app_id}&client_secret={app_secret}&code={code}
    Retorna token de acesso per-restaurante (Business Integration System User).
    """
    url = f"{META_API_BASE}/oauth/access_token"
    params = {
        "client_id": META_APP_ID,
        "client_secret": META_APP_SECRET,
        "code": code,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params)
    _raise_if_error(resp, "trocar_code_por_token")

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise MetaApiError("Resposta OAuth não contém access_token", status_code=500)

    logger.info("BISU token obtido via Embedded Signup")
    return token


async def inscrever_app_na_waba(waba_id: str, token: str, callback_url: str, verify_token: str) -> bool:
    """Inscreve o app na WABA do restaurante e configura webhook override.

    1. POST /{waba_id}/subscribed_apps → subscribe
    2. POST /{waba_id}/subscribed_apps → override callback_url + verify_token
    """
    url = f"{META_API_BASE}/{waba_id}/subscribed_apps"

    # Passo 1: Subscribe
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, headers=_headers(token))
    _raise_if_error(resp, "inscrever_app_subscribe")

    # Passo 2: Override webhook
    body = {
        "override_callback_uri": callback_url,
        "verify_token": verify_token,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers(token))
    _raise_if_error(resp, "inscrever_app_webhook_override")

    logger.info(f"App inscrito na WABA {waba_id} com webhook override")
    return True


async def listar_telefones_waba(waba_id: str, token: str) -> list[dict]:
    """Lista números de telefone registrados em uma WABA.

    GET /{waba_id}/phone_numbers?fields=display_phone_number,verified_name,quality_rating
    """
    url = f"{META_API_BASE}/{waba_id}/phone_numbers"
    params = {"fields": "display_phone_number,verified_name,quality_rating"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers(token))
    _raise_if_error(resp, "listar_telefones_waba")

    data = resp.json()
    phones = data.get("data", [])
    logger.info(f"WABA {waba_id}: {len(phones)} telefone(s) encontrado(s)")
    return phones


async def registrar_numero(numero: str, display_name: str = "") -> dict:
    """Registra um número de telefone na WABA compartilhada.

    Args:
        numero: Número completo com código do país (ex: "5511999999999")
        display_name: Nome de exibição no WhatsApp Business

    Returns:
        dict com 'phone_number_id' e outros dados
    """
    # Separar código do país (assume BR = 55 se começa com 55)
    cc = "55"
    phone = numero
    if numero.startswith("55") and len(numero) > 10:
        cc = "55"
        phone = numero[2:]
    elif numero.startswith("+55"):
        cc = "55"
        phone = numero[3:]
    elif numero.startswith("+"):
        # Tenta extrair cc genérico (2 dígitos)
        cc = numero[1:3]
        phone = numero[3:]

    if not display_name:
        raise MetaApiError("verified_name (display_name) é obrigatório pela Meta API", status_code=400)

    url = f"{META_API_BASE}/{META_WABA_ID}/phone_numbers"
    body = {
        "cc": cc,
        "phone_number": phone,
        "migrate_phone_number": False,
        "verified_name": display_name,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers())
    _raise_if_error(resp, "registrar_numero")

    data = resp.json()
    logger.info(f"Número registrado na WABA: {numero} → phone_number_id={data.get('id')}")
    return {"phone_number_id": data.get("id"), "raw": data}


async def solicitar_codigo(phone_number_id: str, metodo: str = "SMS") -> bool:
    """Solicita código de verificação via SMS ou ligação.

    Args:
        phone_number_id: ID do número na Meta
        metodo: "SMS" ou "VOICE"
    """
    url = f"{META_API_BASE}/{phone_number_id}/request_code"
    body = {
        "code_method": metodo.upper(),
        "language": "pt_BR",
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers())
    _raise_if_error(resp, "solicitar_codigo")

    logger.info(f"Código solicitado via {metodo} para phone_number_id={phone_number_id}")
    return True


async def verificar_codigo(phone_number_id: str, codigo: str) -> bool:
    """Verifica o código de 6 dígitos recebido por SMS/ligação.

    Args:
        phone_number_id: ID do número na Meta
        codigo: Código de 6 dígitos
    """
    url = f"{META_API_BASE}/{phone_number_id}/verify_code"
    body = {"code": codigo.strip()}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers())
    _raise_if_error(resp, "verificar_codigo")

    logger.info(f"Código verificado com sucesso para phone_number_id={phone_number_id}")
    return True


async def registrar_cloud_api(phone_number_id: str, token: Optional[str] = None) -> bool:
    """Registra o número na Cloud API (habilita envio/recebimento de mensagens).

    Gera um PIN de 6 dígitos internamente (requisito da API).
    Se token fornecido, usa BISU token per-restaurante; senão, usa global.
    """
    pin = f"{secrets.randbelow(1000000):06d}"

    url = f"{META_API_BASE}/{phone_number_id}/register"
    body = {
        "messaging_product": "whatsapp",
        "pin": pin,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers(token))
    _raise_if_error(resp, "registrar_cloud_api")

    logger.info(f"Número registrado na Cloud API: phone_number_id={phone_number_id}")
    return True


async def atualizar_perfil(
    phone_number_id: str,
    about: str = "",
    description: str = "",
    vertical: str = "RESTAURANT",
    address: str = "",
    websites: Optional[list[str]] = None,
    token: Optional[str] = None,
) -> bool:
    """Atualiza perfil do WhatsApp Business.

    Args:
        phone_number_id: ID do número
        about: Texto "Sobre" (max 139 chars)
        description: Descrição do negócio (max 512 chars)
        vertical: Categoria do negócio
        address: Endereço (opcional)
        websites: Lista de URLs (opcional, max 2)
        token: BISU token per-restaurante (opcional, usa global como fallback)
    """
    url = f"{META_API_BASE}/{phone_number_id}/whatsapp_business_profile"
    body: dict = {"messaging_product": "whatsapp"}

    if about:
        body["about"] = about[:139]
    if description:
        body["description"] = description[:512]
    if vertical:
        body["vertical"] = vertical
    if address:
        body["address"] = address
    if websites:
        body["websites"] = websites[:2]

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers(token))
    _raise_if_error(resp, "atualizar_perfil")

    logger.info(f"Perfil atualizado para phone_number_id={phone_number_id}")
    return True


async def upload_foto_perfil(
    phone_number_id: str, image_bytes: bytes, content_type: str = "image/jpeg", token: Optional[str] = None,
) -> bool:
    """Faz upload de foto de perfil para o WhatsApp Business.

    Passo 1: Upload da imagem como media
    Passo 2: Definir como foto de perfil
    """
    t = token or META_ACCESS_TOKEN

    # Passo 1: Upload media
    upload_url = f"{META_API_BASE}/{phone_number_id}/media"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            upload_url,
            headers={"Authorization": f"Bearer {t}"},
            data={"messaging_product": "whatsapp", "type": content_type},
            files={"file": ("profile.jpg", image_bytes, content_type)},
        )
    _raise_if_error(resp, "upload_media")
    media_id = resp.json().get("id")

    if not media_id:
        raise MetaApiError("Upload de imagem não retornou media_id", status_code=500)

    # Passo 2: Definir como foto de perfil
    profile_url = f"{META_API_BASE}/{phone_number_id}/whatsapp_business_profile"
    body = {
        "messaging_product": "whatsapp",
        "profile_picture_handle": media_id,
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(profile_url, json=body, headers=_headers(token))
    _raise_if_error(resp, "set_profile_photo")

    logger.info(f"Foto de perfil atualizada para phone_number_id={phone_number_id}")
    return True


async def obter_perfil(phone_number_id: str, token: Optional[str] = None) -> dict:
    """Obtém perfil atual do número WhatsApp Business."""
    url = f"{META_API_BASE}/{phone_number_id}/whatsapp_business_profile"
    params = {"fields": "about,address,description,vertical,websites,profile_picture_url"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params=params, headers=_headers(token))
    _raise_if_error(resp, "obter_perfil")

    data = resp.json().get("data", [{}])
    return data[0] if data else {}


async def desvincular_numero(phone_number_id: str, token: Optional[str] = None) -> bool:
    """Desvincula/desregistra um número da Cloud API."""
    url = f"{META_API_BASE}/{phone_number_id}/deregister"
    body = {"messaging_product": "whatsapp"}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=body, headers=_headers(token))
    _raise_if_error(resp, "desvincular_numero")

    logger.info(f"Número desvinculado da Cloud API: phone_number_id={phone_number_id}")
    return True
