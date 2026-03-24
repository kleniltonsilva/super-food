"""
email_service.py - Integração com Resend API para envio de emails
Throttling: max 10 emails/segundo (respeitando rate limit Resend)
Tracking: pixel de abertura + link tracking + unsubscribe
"""
import os
import json
import time
import re
import uuid
from typing import Optional

import resend

from crm.database import (
    obter_lead, obter_email_template, registrar_interacao,
    atualizar_campanha_contadores, atualizar_status_campanha,
    buscar_leads_para_export, marcar_email_invalido,
    buscar_interacao_por_email_id,
    obter_configuracao, cidade_tem_delivery_verificado,
    criar_email_enviado, marcar_email_aberto, marcar_email_clique,
    marcar_email_bounce, buscar_email_por_resend_id,
    emails_enviados_hoje, opt_out_lead,
)
from crm.scoring import personalizar_abordagem
from crm.competitor_service import dados_mercado_cidade, concorrentes_bairro

resend.api_key = os.environ.get("RESEND_API_KEY", "")

FROM_EMAIL = os.environ.get("FROM_EMAIL", "contato@derekh.com.br")
FROM_NAME = os.environ.get("FROM_NAME", "Derekh Food")
BASE_URL = os.environ.get("CRM_BASE_URL", "http://localhost:8000")


# ============================================================
# VARIÁVEIS DE TEMPLATE
# ============================================================

def _extrair_variaveis(lead: dict) -> dict:
    """Extrai variáveis disponíveis para substituição em templates.
    Inclui dados de mercado e concorrentes para personalização."""
    personalizacao = personalizar_abordagem(lead)

    cidade = lead.get("cidade") or ""
    uf = lead.get("uf") or ""
    bairro = lead.get("bairro") or ""

    # Buscar nome_usuario das configurações
    nome_usuario = obter_configuracao("nome_usuario") or "Equipe Derekh"

    vars = {
        "nome_dono": personalizacao["nome_dono"] or "prezado(a)",
        "nome_restaurante": lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante",
        "nome_usuario": nome_usuario,
        "razao_social": lead.get("razao_social") or "",
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "rating": str(lead.get("rating") or ""),
        "total_avaliacoes": str(lead.get("total_reviews") or "0"),
        "capital_social": f"R$ {float(lead.get('capital_social') or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "porte": lead.get("porte") or "",
        "cnpj": lead.get("cnpj") or "",
    }

    # Dados de mercado da cidade
    if cidade and uf:
        try:
            # Verificar se delivery foi verificado antes de mostrar concorrentes
            delivery_verificado = cidade_tem_delivery_verificado(cidade, uf)

            mercado = dados_mercado_cidade(cidade, uf)
            vars["total_restaurantes_cidade"] = str(mercado.get("total_restaurantes", 0))
            vars["total_com_delivery_cidade"] = str(mercado.get("com_algum_delivery", 0))
            vars["total_sem_delivery_cidade"] = str(mercado.get("sem_delivery", 0))
            vars["total_ifood_cidade"] = str(mercado.get("com_ifood", 0))

            if delivery_verificado:
                # Concorrentes do bairro com delivery
                concorrentes = concorrentes_bairro(lead.get("id", 0), limite=5)
                if concorrentes:
                    lista_html = ""
                    for c in concorrentes:
                        nome = c.get("nome_fantasia") or c.get("razao_social") or "—"
                        plataformas = []
                        if c.get("tem_ifood"): plataformas.append("iFood")
                        if c.get("tem_rappi"): plataformas.append("Rappi")
                        if c.get("tem_99food"): plataformas.append("99Food")
                        rating_str = f" | {c['rating']}★" if c.get("rating") else ""
                        lista_html += f'<li style="padding:4px 0;color:#374151;">{nome} — {", ".join(plataformas)}{rating_str}</li>'
                    vars["concorrentes_html"] = f'<ul style="list-style:none;padding:0;margin:8px 0;">{lista_html}</ul>'
                    vars["total_concorrentes_delivery"] = str(len(concorrentes))
                else:
                    vars["concorrentes_html"] = '<p style="color:#6b7280;">Nenhum concorrente com delivery encontrado no bairro.</p>'
                    vars["total_concorrentes_delivery"] = "0"
            else:
                vars["concorrentes_html"] = '<p style="color:#6b7280;">Verificação de delivery pendente para esta cidade.</p>'
                vars["total_concorrentes_delivery"] = "—"
        except Exception:
            vars["total_restaurantes_cidade"] = "—"
            vars["total_com_delivery_cidade"] = "—"
            vars["total_sem_delivery_cidade"] = "—"
            vars["total_ifood_cidade"] = "—"
            vars["concorrentes_html"] = ""
            vars["total_concorrentes_delivery"] = "—"

    return vars


def _substituir_variaveis(texto: str, variaveis: dict) -> str:
    """Substitui {variavel} no texto pelos valores reais."""
    for chave, valor in variaveis.items():
        texto = texto.replace("{" + chave + "}", str(valor))
    return texto


# ============================================================
# TRACKING
# ============================================================

def gerar_tracking_id() -> str:
    """Gera UUID único para tracking de email."""
    return str(uuid.uuid4())


def gerar_pixel_url(tracking_id: str) -> str:
    """Gera URL do pixel de abertura (imagem 1x1 transparente)."""
    return f"{BASE_URL}/tracking/pixel/{tracking_id}"


def gerar_link_rastreado(url_destino: str, tracking_id: str, tipo: str) -> str:
    """Gera link wrapper que registra clique e redireciona.
    tipo: site|wa"""
    return f"{BASE_URL}/tracking/click/{tracking_id}/{tipo}?url={url_destino}"


def gerar_link_unsub(tracking_id: str) -> str:
    """Gera link de unsubscribe."""
    return f"{BASE_URL}/tracking/unsub/{tracking_id}"


def _extrair_corpo_html(html: str) -> str:
    """Extrai conteúdo do <body> se existir, senão retorna como está.
    Remove tags html/head/body para que o wrapper branded funcione."""
    import re
    # Se tem <body>, extrair conteúdo interno
    match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Se tem <html> mas sem body, extrair conteúdo
    match = re.search(r'<html[^>]*>(.*?)</html>', html, re.DOTALL | re.IGNORECASE)
    if match:
        inner = match.group(1).strip()
        # Remover <head>...</head> se existir
        inner = re.sub(r'<head[^>]*>.*?</head>', '', inner, flags=re.DOTALL | re.IGNORECASE)
        return inner.strip()
    return html


WHATSAPP_INBOUND = "5511971765565"
LANDING_URL_DEFAULT = "https://derekh.com.br/food"


def _envolver_email_branded(corpo_html: str, tracking_id: str) -> str:
    """Envolve QUALQUER corpo de email no template branded Derekh Food.
    Header verde + corpo + link site + botão WA + unsub + pixel tracking."""
    import urllib.parse

    # Se corpo já tem <html>, extrair apenas o body
    if '</html>' in corpo_html.lower() or '</body>' in corpo_html.lower():
        corpo_html = _extrair_corpo_html(corpo_html)

    pixel = gerar_pixel_url(tracking_id)
    unsub = gerar_link_unsub(tracking_id)
    landing = obter_configuracao("outreach_landing_url") or LANDING_URL_DEFAULT
    link_site = gerar_link_rastreado(landing, tracking_id, "site")
    wa_text = "Olá! Gostaria de saber mais sobre a Derekh Food"
    wa_link = f"https://wa.me/{WHATSAPP_INBOUND}?text={urllib.parse.quote(wa_text)}"
    link_wa = gerar_link_rastreado(wa_link, tracking_id, "wa")

    pixel_tag = f'<img src="{pixel}" width="1" height="1" style="display:none;" alt="" />'

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,0.08);">

<!-- HEADER -->
<tr><td style="background:linear-gradient(135deg,#00b894,#00d4aa);padding:20px 28px;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:22px;font-weight:800;color:#ffffff;font-family:'Segoe UI',Helvetica,sans-serif;">Derekh Food</td>
    <td align="right" style="font-size:11px;color:#ffffffcc;font-family:'Segoe UI',Helvetica,sans-serif;">Delivery sem comissão</td>
  </tr></table>
</td></tr>

<!-- CORPO -->
<tr><td style="padding:28px 28px 20px;font-size:14px;line-height:1.7;color:#374151;">
{corpo_html}
</td></tr>

<!-- DIVIDER -->
<tr><td style="padding:0 28px;"><div style="border-top:1px solid #e5e7eb;"></div></td></tr>

<!-- CTA: SITE + WHATSAPP -->
<tr><td style="padding:20px 28px;text-align:center;">
  <p style="margin:0 0 14px;font-size:13px;color:#6b7280;">Conheça a Derekh Food — delivery próprio para seu restaurante</p>
  <a href="{link_site}" style="display:inline-block;padding:10px 24px;background:#00d4aa;color:#ffffff;border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;margin-right:8px;">Visitar Site</a>
  <a href="{link_wa}" style="display:inline-block;padding:10px 24px;background:#25D366;color:#ffffff;border-radius:8px;font-weight:700;font-size:13px;text-decoration:none;">💬 Fale no WhatsApp</a>
</td></tr>

<!-- FOOTER -->
<tr><td style="padding:16px 28px;background:#f9fafb;text-align:center;font-size:11px;color:#9ca3af;">
  <p style="margin:0 0 4px;">Derekh Food · Delivery sem comissão para restaurantes</p>
  <p style="margin:0;"><a href="{unsub}" style="color:#6b7280;text-decoration:underline;">Cancelar inscrição</a></p>
</td></tr>

</table>
{pixel_tag}
</td></tr></table>
</body></html>"""


def _injetar_tracking(corpo_html: str, tracking_id: str, landing_url: str = None) -> str:
    """Envolve email no template branded Derekh Food com tracking completo."""
    return _envolver_email_branded(corpo_html, tracking_id)


# ============================================================
# ENVIO
# ============================================================

def enviar_email(lead_id: int, template_id: int, campanha_id: int = None) -> dict:
    """Envia email para um lead usando um template.
    Inclui pixel tracking + link unsub + registra em emails_enviados.
    Retorna dict com status e message_id."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    email_dest = lead.get("email")
    if not email_dest or not email_dest.strip():
        return {"erro": "Lead sem email"}

    if lead.get("email_invalido"):
        return {"erro": "Email marcado como inválido (bounced)"}

    if lead.get("opt_out_email"):
        return {"erro": "Lead fez opt-out de email"}

    template = obter_email_template(template_id)
    if not template:
        return {"erro": "Template não encontrado"}

    # Gerar tracking
    tracking_id = gerar_tracking_id()
    pixel_url = gerar_pixel_url(tracking_id)
    landing_url = obter_configuracao("outreach_landing_url") or "https://derekh.com.br/food"

    variaveis = _extrair_variaveis(lead)
    assunto = _substituir_variaveis(template["assunto"], variaveis)
    corpo = _substituir_variaveis(template["corpo_html"], variaveis)

    # Injetar tracking
    corpo = _injetar_tracking(corpo, tracking_id, landing_url)

    try:
        resultado = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [email_dest],
            "subject": assunto,
            "html": corpo,
        })

        message_id = resultado.get("id", "")

        # Registrar em emails_enviados (tracking)
        criar_email_enviado(
            lead_id=lead_id,
            template_id=template_id,
            assunto=assunto,
            tracking_id=tracking_id,
            pixel_url=pixel_url,
            resend_message_id=message_id,
            campanha_id=campanha_id,
        )

        # Registrar interação (compatibilidade com CRM existente)
        registrar_interacao(
            lead_id=lead_id,
            tipo="email",
            canal="email",
            conteudo=f"Assunto: {assunto}",
            resultado="enviado",
            email_message_id=message_id,
        )

        # Atualizar campanha se aplicável
        if campanha_id:
            atualizar_campanha_contadores(campanha_id, "total_enviados")

        return {"sucesso": True, "message_id": message_id, "tracking_id": tracking_id}

    except Exception as e:
        return {"erro": str(e)}


def enviar_email_personalizado(lead_id: int, assunto: str, corpo: str,
                               campanha_id: int = None) -> dict:
    """Envia email personalizado (gerado por pattern_library) para um lead.
    Inclui pixel tracking + link unsub. Fallback-free — corpo/assunto já vêm prontos."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    email_dest = lead.get("email")
    if not email_dest or not email_dest.strip():
        return {"erro": "Lead sem email"}

    if lead.get("email_invalido"):
        return {"erro": "Email marcado como inválido (bounced)"}

    if lead.get("opt_out_email"):
        return {"erro": "Lead fez opt-out de email"}

    # Gerar tracking
    tracking_id = gerar_tracking_id()
    pixel_url = gerar_pixel_url(tracking_id)

    # Injetar tracking no corpo
    corpo_final = _injetar_tracking(corpo, tracking_id)

    try:
        resultado = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [email_dest],
            "subject": assunto,
            "html": corpo_final,
        })

        message_id = resultado.get("id", "")

        criar_email_enviado(
            lead_id=lead_id,
            template_id=None,
            assunto=assunto,
            tracking_id=tracking_id,
            pixel_url=pixel_url,
            resend_message_id=message_id,
            campanha_id=campanha_id,
        )

        registrar_interacao(
            lead_id=lead_id,
            tipo="email",
            canal="email",
            conteudo=f"Assunto: {assunto} (personalizado 3F)",
            resultado="enviado",
            email_message_id=message_id,
        )

        if campanha_id:
            atualizar_campanha_contadores(campanha_id, "total_enviados")

        return {"sucesso": True, "message_id": message_id, "tracking_id": tracking_id}

    except Exception as e:
        return {"erro": str(e)}


def enviar_campanha(campanha_id: int, filtros: dict, template_id: int,
                    throttle_por_segundo: int = 10) -> dict:
    """Envia campanha para todos os leads que passam nos filtros.
    Throttle de N emails/segundo."""
    leads = buscar_leads_para_export(filtros)
    atualizar_status_campanha(campanha_id, "enviando")

    stats = {"enviados": 0, "erros": 0, "sem_email": 0}
    batch_start = time.time()
    batch_count = 0

    for lead in leads:
        if not lead.get("email") or lead.get("email_invalido"):
            stats["sem_email"] += 1
            continue

        resultado = enviar_email(lead["id"], template_id, campanha_id)

        if resultado.get("sucesso"):
            stats["enviados"] += 1
        else:
            stats["erros"] += 1

        batch_count += 1

        # Throttling
        if batch_count >= throttle_por_segundo:
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)
            batch_start = time.time()
            batch_count = 0

    atualizar_status_campanha(campanha_id, "concluida")
    return stats


# ============================================================
# WEBHOOK RESEND
# ============================================================

def processar_webhook_resend(payload: dict) -> dict:
    """Processa webhook do Resend (opened, clicked, bounced, complained).
    Usa emails_enviados para tracking preciso e interacoes para compatibilidade."""
    event_type = payload.get("type", "")
    data = payload.get("data", {})
    email_id = data.get("email_id", "")

    if not email_id:
        return {"ignorado": "sem email_id"}

    # Primeiro: tentar emails_enviados (sistema novo)
    email_reg = buscar_email_por_resend_id(email_id)

    if email_reg:
        lead_id = email_reg["lead_id"]
        tracking_id = str(email_reg["tracking_id"])

        if event_type == "email.opened":
            marcar_email_aberto(tracking_id)
            registrar_interacao(lead_id, "email", "email", "Email aberto (webhook)", "positivo")

        elif event_type == "email.clicked":
            marcar_email_clique(tracking_id, "site")
            registrar_interacao(lead_id, "email", "email", "Link clicado (webhook)", "positivo")

        elif event_type == "email.bounced":
            marcar_email_bounce(tracking_id)
            registrar_interacao(lead_id, "email", "email", "Email bounced", "negativo")

        elif event_type == "email.complained":
            opt_out_lead(lead_id, "email")
            registrar_interacao(lead_id, "email", "email", "Marcou como spam — opt-out", "negativo")

        return {"processado": event_type, "lead_id": lead_id, "tracking_id": tracking_id}

    # Fallback: sistema antigo (interacoes)
    interacao = buscar_interacao_por_email_id(email_id)
    if not interacao:
        return {"ignorado": "email não encontrado"}

    lead_id = interacao.get("lead_id") or interacao.get("lead_id_fk")

    if event_type == "email.bounced":
        marcar_email_invalido(lead_id)
        registrar_interacao(lead_id, "email", "email", "Email bounced", "negativo")
    elif event_type == "email.complained":
        opt_out_lead(lead_id, "email")
        registrar_interacao(lead_id, "email", "email", "Marcou como spam", "negativo")

    return {"processado": event_type, "lead_id": lead_id}


def preview_template(template_id: int, lead_id: int) -> dict:
    """Preview de template com variáveis de um lead real."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    template = obter_email_template(template_id)
    if not template:
        return {"erro": "Template não encontrado"}

    variaveis = _extrair_variaveis(lead)
    return {
        "assunto": _substituir_variaveis(template["assunto"], variaveis),
        "corpo_html": _substituir_variaveis(template["corpo_html"], variaveis),
        "variaveis_disponiveis": list(variaveis.keys()),
    }
