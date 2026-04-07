"""
wa_outreach_manual.py - Gerador de mensagens personalizadas para outreach manual via WhatsApp.
Ana gera mensagem curta e atraente baseada nos dados do lead no CRM.
O dono copia a msg e envia manualmente pelo WhatsApp Web.
"""
import os
import json
import logging
import urllib.parse

import httpx

from crm.database import obter_lead, obter_socios

log = logging.getLogger("wa_outreach")

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MODEL = os.environ.get("XAI_MODEL", "grok-3-mini")
WHATSAPP_ANA = os.environ.get("WHATSAPP_INBOUND_NUMBER", "351961330536")


def _extrair_nome_socio(lead: dict) -> str:
    """Extrai primeiro nome de um sócio do lead."""
    socios = obter_socios(lead["id"])
    if socios:
        for s in socios:
            nome = s.get("nome") or s.get("nome_socio") or ""
            if nome and len(nome) > 2:
                # Pegar primeiro nome (capitalizado)
                partes = nome.strip().split()
                if partes:
                    return partes[0].capitalize()
    return ""


def _extrair_nome_display(lead: dict) -> str:
    """Extrai nome para exibição: sócio > nome_fantasia > razão_social."""
    nome_socio = _extrair_nome_socio(lead)
    if nome_socio:
        return nome_socio

    nome = lead.get("nome_fantasia") or lead.get("razao_social") or ""
    if nome:
        # Limpar CNPJ/CPF do nome
        import re
        nome = re.sub(r'\d{2,}[\./\-]?\d+', '', nome).strip()
        if len(nome) > 2:
            return nome
    return ""


def _build_lead_context(lead: dict) -> str:
    """Monta contexto do lead para o prompt."""
    parts = []
    nome = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
    parts.append(f"Restaurante: {nome}")

    if lead.get("cidade"):
        parts.append(f"Cidade: {lead['cidade']}/{lead.get('uf', '')}")
    if lead.get("bairro"):
        parts.append(f"Bairro: {lead['bairro']}")

    # Delivery
    delivery = []
    if lead.get("tem_ifood"):
        delivery.append("iFood")
    if lead.get("tem_rappi"):
        delivery.append("Rappi")
    if lead.get("tem_99food"):
        delivery.append("99Food")
    if delivery:
        parts.append(f"Delivery atual: {', '.join(delivery)}")
    else:
        parts.append("Delivery: nenhum detectado")

    if lead.get("rating"):
        parts.append(f"Google: ★{lead['rating']} ({lead.get('total_reviews', 0)} avaliações)")
    if lead.get("ifood_rating"):
        parts.append(f"iFood: ★{lead['ifood_rating']}")
    if lead.get("ifood_categorias"):
        parts.append(f"Categorias: {lead['ifood_categorias']}")

    nome_socio = _extrair_nome_socio(lead)
    if nome_socio:
        parts.append(f"Nome sócio: {nome_socio}")

    return "\n".join(parts)


def gerar_mensagem_outreach_manual(lead_id: int) -> dict:
    """Gera mensagem personalizada pela Ana para enviar manualmente via WA Web.
    Retorna dict com mensagem, link wa.me e dados do lead."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    if not telefone:
        return {"erro": "Lead sem telefone"}

    nome_display = _extrair_nome_display(lead)
    lead_context = _build_lead_context(lead)

    # Link wa.me para a Ana
    wa_ana_text = "Olá Ana! Vi a mensagem sobre a Derekh Food e quero saber mais"
    wa_ana_link = f"https://wa.me/{WHATSAPP_ANA}?text={urllib.parse.quote(wa_ana_text)}"

    if not XAI_API_KEY:
        # Fallback sem IA — mensagem genérica
        msg = _gerar_msg_fallback(lead, nome_display, wa_ana_link)
        return _montar_resultado(lead, telefone, msg, wa_ana_link)

    system_prompt = f"""Você é Ana, vendedora da Derekh Food. Gere UMA mensagem curta para WhatsApp.

DADOS DO LEAD:
{lead_context}

REGRAS OBRIGATÓRIAS:
1. MÁXIMO 4 linhas — ninguém lê mensagem longa no WhatsApp
2. Cite o NOME DO SÓCIO se disponível, senão nome do restaurante
3. Mencione 1 dado REAL do lead (ex: rating, cidade, plataforma que usa)
4. Tom amigável, direto, como se fosse uma vendedora humana
5. NUNCA use "Prezado", "Estimado" ou formalidades mortas
6. Inclua o link do site: derekhfood.com.br
7. A ÚLTIMA linha DEVE ser: "Quer testar 15 dias grátis? Me chama aqui: [LINK_ANA]"
8. [LINK_ANA] será substituído automaticamente — use exatamente "[LINK_ANA]"
9. NÃO use emojis demais — máximo 2
10. NÃO mencione preços — só fale dos 15 dias grátis
11. A Derekh Food é sistema de delivery próprio, 0% comissão
12. Se tem iFood: "complemento sem comissão ao iFood"
13. Se não tem delivery: "começar delivery próprio sem depender de marketplace"
14. Gere APENAS o texto da mensagem, nada mais"""

    try:
        with httpx.Client(timeout=25) as client:
            resp = client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": XAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": "Gere a mensagem."},
                    ],
                    "temperature": 0.8,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        msg = data["choices"][0]["message"]["content"].strip()
        # Substituir placeholder pelo link real
        msg = msg.replace("[LINK_ANA]", wa_ana_link)

        return _montar_resultado(lead, telefone, msg, wa_ana_link)

    except Exception as e:
        log.warning(f"Erro gerando msg para lead {lead_id}: {e}")
        msg = _gerar_msg_fallback(lead, nome_display, wa_ana_link)
        return _montar_resultado(lead, telefone, msg, wa_ana_link)


def _gerar_msg_fallback(lead: dict, nome_display: str, wa_ana_link: str) -> str:
    """Mensagem fallback quando IA não está disponível."""
    saudacao = f"Oi {nome_display}!" if nome_display else "Oi!"
    cidade = lead.get("cidade") or ""
    cidade_str = f" em {cidade}" if cidade else ""

    if lead.get("tem_ifood"):
        gancho = f"Vi que o restaurante já está no iFood{cidade_str}. A Derekh Food é um complemento sem comissão — delivery próprio com a sua marca."
    else:
        gancho = f"Vi seu restaurante{cidade_str} e quero te apresentar a Derekh Food — delivery próprio, 0% comissão, setup em 48h."

    return (
        f"{saudacao} {gancho}\n\n"
        f"🌐 derekhfood.com.br\n\n"
        f"Quer testar 15 dias grátis? Me chama aqui: {wa_ana_link}"
    )


def _montar_resultado(lead: dict, telefone: str, msg: str, wa_ana_link: str) -> dict:
    """Monta resultado final com dados para a UI."""
    # Limpar telefone para wa.me link
    import re
    tel_limpo = re.sub(r'\D', '', telefone)
    if not tel_limpo.startswith("55") and len(tel_limpo) <= 11:
        tel_limpo = f"55{tel_limpo}"

    wa_enviar_link = f"https://wa.me/{tel_limpo}?text={urllib.parse.quote(msg)}"

    nome = lead.get("nome_fantasia") or lead.get("razao_social") or f"Lead #{lead['id']}"
    nome_socio = _extrair_nome_socio(lead)

    return {
        "sucesso": True,
        "lead_id": lead["id"],
        "nome": nome,
        "nome_socio": nome_socio,
        "telefone": telefone,
        "cidade": lead.get("cidade") or "",
        "uf": lead.get("uf") or "",
        "mensagem": msg,
        "wa_enviar_link": wa_enviar_link,
        "wa_ana_link": wa_ana_link,
        "tem_ifood": bool(lead.get("tem_ifood")),
    }
