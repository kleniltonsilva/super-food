"""
Meta Cloud API Client — Envia mensagens via API oficial do WhatsApp Business.

Usado para:
1. Receber mensagem do cliente → responder com link para número ativo (Baileys)
2. Notificar cliente quando número muda (recovery pós-ban)

API: https://graph.facebook.com/v22.0/{phone_number_id}/messages
Auth: Bearer {access_token} (System User Token)
"""
import hashlib
import hmac
import logging
from typing import Optional

import httpx

logger = logging.getLogger("superfood.bot.meta_cloud")

META_API_BASE = "https://graph.facebook.com/v22.0"
_TIMEOUT = 15


async def enviar_template(
    numero_cliente: str,
    phone_number_id: str,
    access_token: str,
    template_name: str,
    params: list[str],
    language: str = "pt_BR",
) -> dict:
    """Envia template pré-aprovado via Meta Cloud API.

    Args:
        numero_cliente: Número do cliente (formato: 5511999999999)
        phone_number_id: ID do número na Meta
        access_token: System User Token
        template_name: Nome do template aprovado
        params: Lista de parâmetros ({{1}}, {{2}}, etc.)
        language: Código do idioma (pt_BR)
    """
    url = f"{META_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Montar componentes do template
    components = []
    if params:
        parameters = [{"type": "text", "text": p} for p in params]
        components.append({
            "type": "body",
            "parameters": parameters,
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": _normalizar_numero(numero_cliente),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Template '{template_name}' enviado para {numero_cliente[:8]}***")
        return data


async def enviar_texto_livre(
    numero_cliente: str,
    texto: str,
    phone_number_id: str,
    access_token: str,
) -> dict:
    """Envia texto livre via Meta Cloud API (dentro da janela de 24h).

    Só funciona se o cliente enviou mensagem nas últimas 24h.
    """
    url = f"{META_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": _normalizar_numero(numero_cliente),
        "type": "text",
        "text": {"body": texto},
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"Texto livre Meta enviado para {numero_cliente[:8]}***")
        return data


def verificar_webhook(
    mode: str,
    token: str,
    challenge: str,
    verify_token_esperado: str,
) -> Optional[str]:
    """Verifica webhook Meta (GET /webhooks/meta-whatsapp).

    Meta envia GET com hub.mode, hub.verify_token, hub.challenge.
    Se token bate, retorna challenge. Senão, None.
    """
    if mode == "subscribe" and hmac.compare_digest(token, verify_token_esperado):
        return challenge
    return None


def validar_webhook_signature(
    body: bytes,
    signature_header: str,
    app_secret: str,
) -> bool:
    """Valida assinatura HMAC-SHA256 do webhook Meta.

    Header: X-Hub-Signature-256: sha256=<hex>
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_sig = signature_header[7:]
    computed = hmac.new(
        app_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(computed, expected_sig)


async def enviar_redirect(
    numero_cliente: str,
    phone_number_id: str,
    access_token: str,
    nome_restaurante: str,
    numero_ativo: str,
    template_name: str = "redirect_atendimento",
) -> dict:
    """Envia template de redirecionamento para número ativo do bot.

    Template: "Olá! Que bom que entrou em contato com o {{1}}!
    Para atendimento rápido, mande uma mensagem aqui: {{2}}"
    """
    link = f"https://wa.me/{_normalizar_numero(numero_ativo)}"
    return await enviar_template(
        numero_cliente, phone_number_id, access_token,
        template_name, [nome_restaurante, link],
    )


async def enviar_recovery(
    numero_cliente: str,
    phone_number_id: str,
    access_token: str,
    nome_cliente: str,
    numero_novo: str,
    template_name: str = "numero_atualizado",
) -> dict:
    """Envia template de recuperação pós-ban com novo número.

    Template: "Oi {{1}}! Tivemos um probleminha técnico no WhatsApp.
    Vamos continuar por aqui: {{2}}"
    """
    link = f"https://wa.me/{_normalizar_numero(numero_novo)}"
    return await enviar_template(
        numero_cliente, phone_number_id, access_token,
        template_name, [nome_cliente, link],
    )


def _normalizar_numero(numero: str) -> str:
    """Remove caracteres não numéricos e garante formato correto."""
    limpo = "".join(c for c in numero if c.isdigit())
    if len(limpo) <= 11 and not limpo.startswith("55"):
        limpo = "55" + limpo
    return limpo
