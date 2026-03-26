# backend/app/email_service.py
"""
Serviço de email transacional via Resend.
Reutilizável para boas-vindas, notificações, etc.
"""

import os
import logging
import resend

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
FROM_EMAIL = os.getenv("DEREKH_FROM_EMAIL", "noreply@derekhfood.com.br")
BASE_URL = os.getenv("BASE_URL", "https://superfood-api.fly.dev")


def _configurar_resend():
    """Configura a API key do Resend. Retorna True se configurado."""
    if not RESEND_API_KEY:
        logger.warning("RESEND_API_KEY não configurada — emails desabilitados")
        return False
    resend.api_key = RESEND_API_KEY
    return True


async def enviar_email_boas_vindas(
    email_destino: str,
    nome_fantasia: str,
    codigo_acesso: str,
    senha_padrao: str,
    link_painel: str,
    link_onboarding: str,
) -> dict:
    """Envia email de boas-vindas com credenciais ao novo restaurante."""
    if not _configurar_resend():
        return {"erro": "RESEND_API_KEY não configurada", "enviado": False}

    from .email_templates import gerar_email_boas_vindas

    assunto, html = gerar_email_boas_vindas(
        nome_fantasia=nome_fantasia,
        codigo_acesso=codigo_acesso,
        senha_padrao=senha_padrao,
        link_painel=link_painel,
        link_onboarding=link_onboarding,
    )

    try:
        params: resend.Emails.SendParams = {
            "from": f"Derekh Food <{FROM_EMAIL}>",
            "to": [email_destino],
            "subject": assunto,
            "html": html,
        }
        resultado = resend.Emails.send(params)
        email_id = resultado.get("id", "n/a") if isinstance(resultado, dict) else getattr(resultado, "id", "n/a")
        logger.info(f"Email boas-vindas enviado para {email_destino} — id={email_id}")
        return {"enviado": True, "id": email_id}
    except Exception as e:
        logger.error(f"Erro ao enviar email para {email_destino}: {e}")
        return {"erro": str(e), "enviado": False}


async def enviar_email_generico(
    email_destino: str,
    assunto: str,
    corpo_html: str,
) -> dict:
    """Envia um email genérico via Resend."""
    if not _configurar_resend():
        return {"erro": "RESEND_API_KEY não configurada", "enviado": False}

    try:
        params: resend.Emails.SendParams = {
            "from": f"Derekh Food <{FROM_EMAIL}>",
            "to": [email_destino],
            "subject": assunto,
            "html": corpo_html,
        }
        resultado = resend.Emails.send(params)
        email_id = resultado.get("id", "n/a") if isinstance(resultado, dict) else getattr(resultado, "id", "n/a")
        return {"enviado": True, "id": email_id}
    except Exception as e:
        logger.error(f"Erro ao enviar email genérico para {email_destino}: {e}")
        return {"erro": str(e), "enviado": False}


async def enviar_email_verificacao(email_destino: str, nome: str, codigo: str) -> dict:
    """Envia email com código OTP de verificação de email."""
    if not _configurar_resend():
        return {"erro": "RESEND_API_KEY não configurada", "enviado": False}

    from .email_templates import gerar_email_verificacao
    assunto, html = gerar_email_verificacao(nome=nome, codigo=codigo)

    try:
        params: resend.Emails.SendParams = {
            "from": f"Derekh Food <{FROM_EMAIL}>",
            "to": [email_destino],
            "subject": assunto,
            "html": html,
        }
        resultado = resend.Emails.send(params)
        email_id = resultado.get("id", "n/a") if isinstance(resultado, dict) else getattr(resultado, "id", "n/a")
        logger.info(f"Email verificação enviado para {email_destino} — id={email_id}")
        return {"enviado": True, "id": email_id}
    except Exception as e:
        logger.error(f"Erro ao enviar email verificação para {email_destino}: {e}")
        return {"erro": str(e), "enviado": False}


async def enviar_email_reset_senha(email_destino: str, nome: str, codigo: str) -> dict:
    """Envia email com código OTP de redefinição de senha."""
    if not _configurar_resend():
        return {"erro": "RESEND_API_KEY não configurada", "enviado": False}

    from .email_templates import gerar_email_reset_senha
    assunto, html = gerar_email_reset_senha(nome=nome, codigo=codigo)

    try:
        params: resend.Emails.SendParams = {
            "from": f"Derekh Food <{FROM_EMAIL}>",
            "to": [email_destino],
            "subject": assunto,
            "html": html,
        }
        resultado = resend.Emails.send(params)
        email_id = resultado.get("id", "n/a") if isinstance(resultado, dict) else getattr(resultado, "id", "n/a")
        logger.info(f"Email reset senha enviado para {email_destino} — id={email_id}")
        return {"enviado": True, "id": email_id}
    except Exception as e:
        logger.error(f"Erro ao enviar email reset senha para {email_destino}: {e}")
        return {"erro": str(e), "enviado": False}


async def enviar_email_lembrete_cupom(
    email_destino: str,
    nome: str,
    codigo_cupom: str,
    desconto: str,
    expira: str,
    nome_restaurante: str,
) -> dict:
    """Envia email de lembrete de cupom expirando."""
    if not _configurar_resend():
        return {"erro": "RESEND_API_KEY não configurada", "enviado": False}

    from .email_templates import gerar_email_lembrete_cupom
    assunto, html = gerar_email_lembrete_cupom(
        nome=nome, codigo_cupom=codigo_cupom,
        desconto=desconto, expira=expira,
        nome_restaurante=nome_restaurante,
    )

    try:
        params: resend.Emails.SendParams = {
            "from": f"Derekh Food <{FROM_EMAIL}>",
            "to": [email_destino],
            "subject": assunto,
            "html": html,
        }
        resultado = resend.Emails.send(params)
        email_id = resultado.get("id", "n/a") if isinstance(resultado, dict) else getattr(resultado, "id", "n/a")
        logger.info(f"Email lembrete cupom enviado para {email_destino} — id={email_id}")
        return {"enviado": True, "id": email_id}
    except Exception as e:
        logger.error(f"Erro ao enviar email lembrete cupom para {email_destino}: {e}")
        return {"erro": str(e), "enviado": False}
