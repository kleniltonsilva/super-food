"""
grok_email.py - Gerador de emails personalizados com inteligência competitiva.
Usa Grok (xAI) para gerar emails únicos baseados nos dados do lead + concorrentes.
Sem templates fixos — cada email é personalizado por IA.

Lógica:
1. Analisa lead com mais dados disponíveis
2. Busca concorrentes diretos (mesmo bairro/cidade)
3. Gera email comparando lead com concorrentes (entrega VALOR)
4. Personaliza tom, abordagem e CTA baseado no cenário
"""
import os
import json
import httpx
from typing import Optional

from crm.database import (
    get_conn, obter_lead, concorrentes_do_lead, leads_com_mais_dados,
)
from crm.competitor_service import dados_mercado_cidade, percentual_delivery_bairro
from crm.scoring import personalizar_abordagem

XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MODEL = os.environ.get("XAI_MODEL", "grok-3-fast")
XAI_BASE_URL = "https://api.x.ai/v1"


# ============================================================
# ANÁLISE DE CONCORRENTES PARA EMAIL
# ============================================================

def montar_contexto_competitivo(lead_id: int) -> dict:
    """Monta contexto competitivo completo para um lead.
    Retorna dict com dados do lead, concorrentes e mercado."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    # Dados do lead
    nome = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
    cidade = lead.get("cidade") or ""
    uf = lead.get("uf") or ""
    bairro = lead.get("bairro") or ""

    # Concorrentes diretos (mesmo bairro/cidade, com dados)
    concorrentes = concorrentes_do_lead(lead_id, limite=5)

    # Dados de mercado da cidade
    mercado = {}
    if cidade and uf:
        mercado = dados_mercado_cidade(cidade, uf)

    # Percentual delivery no bairro
    delivery_bairro = {}
    if bairro and cidade and uf:
        delivery_bairro = percentual_delivery_bairro(cidade, uf, bairro)

    # Personalização de abordagem (score-based)
    abordagem = personalizar_abordagem(lead)

    return {
        "lead": lead,
        "nome": nome,
        "cidade": cidade,
        "uf": uf,
        "bairro": bairro,
        "concorrentes": concorrentes,
        "mercado": mercado,
        "delivery_bairro": delivery_bairro,
        "abordagem": abordagem,
    }


def _formatar_concorrentes_para_prompt(concorrentes: list) -> str:
    """Formata dados dos concorrentes como texto para o prompt do Grok."""
    if not concorrentes:
        return "Nenhum concorrente encontrado na mesma região."

    linhas = []
    for i, c in enumerate(concorrentes[:5], 1):
        nome = c.get("nome") or c.get("nome_fantasia") or c.get("razao_social") or "Restaurante"
        bairro = c.get("bairro") or "—"

        # Ratings
        parts = []
        if c.get("ifood_rating"):
            parts.append(f"iFood: ★{c['ifood_rating']}")
            if c.get("ifood_reviews"):
                parts[-1] += f" ({c['ifood_reviews']} avaliações)"
        if c.get("rating"):
            parts.append(f"Google: ★{c['rating']}")
            if c.get("total_reviews"):
                parts[-1] += f" ({c['total_reviews']} avaliações)"

        # Delivery
        delivery = []
        if c.get("tem_ifood"):
            delivery.append("iFood")
        if c.get("tem_rappi"):
            delivery.append("Rappi")
        if c.get("tem_99food"):
            delivery.append("99Food")

        # Preço
        preco = c.get("ifood_preco") or ""

        rating_str = " · ".join(parts) if parts else "Sem avaliação pública"
        delivery_str = ", ".join(delivery) if delivery else "Sem delivery"

        linhas.append(
            f"  {i}. {nome} ({bairro})\n"
            f"     Avaliações: {rating_str}\n"
            f"     Delivery: {delivery_str}"
            + (f" · Preço: {preco}" if preco else "")
        )

    return "\n".join(linhas)


def _formatar_lead_para_prompt(lead: dict) -> str:
    """Formata dados do lead como texto para o prompt."""
    nome = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
    cidade = lead.get("cidade") or ""
    bairro = lead.get("bairro") or ""

    parts = [f"Nome: {nome}"]
    if cidade:
        parts.append(f"Cidade: {cidade}/{lead.get('uf', '')}")
    if bairro:
        parts.append(f"Bairro: {bairro}")

    # Rating
    if lead.get("ifood_rating"):
        parts.append(f"iFood: ★{lead['ifood_rating']} ({lead.get('ifood_reviews', 0)} avaliações)")
        if lead.get("ifood_categorias"):
            parts.append(f"Categorias iFood: {lead['ifood_categorias']}")
        if lead.get("ifood_preco"):
            parts.append(f"Faixa de preço: {lead['ifood_preco']}")
    if lead.get("rating"):
        parts.append(f"Google Maps: ★{lead['rating']} ({lead.get('total_reviews', 0)} avaliações)")

    # Delivery
    delivery = []
    if lead.get("tem_ifood"):
        delivery.append("iFood")
    if lead.get("tem_rappi"):
        delivery.append("Rappi")
    if lead.get("tem_99food"):
        delivery.append("99Food")
    parts.append(f"Delivery atual: {', '.join(delivery) if delivery else 'Nenhum'}")

    # Empresa
    if lead.get("porte"):
        parts.append(f"Porte: {lead['porte']}")
    if lead.get("capital_social") and lead["capital_social"] > 0:
        parts.append(f"Capital social: R${lead['capital_social']:,.0f}")

    return "\n".join(parts)


# ============================================================
# GERAÇÃO DE EMAIL COM GROK
# ============================================================

WHATSAPP_INBOUND_NUMBER = os.environ.get("WHATSAPP_INBOUND_NUMBER", "5511971765565")

SYSTEM_PROMPT_EMAIL = """Você é um consultor de vendas B2B da Derekh Food, especialista em delivery para restaurantes.

SOBRE A DEREKH FOOD:
- Sistema completo de delivery próprio para restaurantes (sem comissão, sem iFood)
- 7 apps integrados: Painel Admin, App Motoboy, KDS Cozinha, App Garçom, Site Cliente, Pix Online, WhatsApp Humanoide
- Planos: Básico R$169,90/mês · Essencial R$279,90/mês · Avançado R$329,90/mês · Premium R$527/mês
- WhatsApp Humanoide: incluso no Premium, nos demais planos +R$99,45/mês (atendimento IA 24h, conversa natural sem menus robotizados)
- Setup em 48h, sem taxa de adesão, PWA (sem app store)
- Diferencial: 0% comissão vs 27% do iFood

SUA MISSÃO: Gerar APENAS o corpo do email (parágrafos HTML). O wrapper (header, footer, botão WA, unsub) é adicionado automaticamente.

REGRAS:
1. SEMPRE em português brasileiro
2. Máximo 200 palavras
3. Tom consultivo e profissional, NUNCA agressivo
4. Incluir dados REAIS dos concorrentes (números, estrelas, plataformas)
5. Mostrar pelo menos 3 concorrentes quando disponíveis
6. Assunto curto (max 60 chars), intrigante, com dados reais
7. NÃO inventar dados — use APENAS o que foi fornecido
8. Incluir nome do dono quando disponível

FORMATO DE SAÍDA (JSON):
{
  "assunto": "...",
  "corpo_html": "<p>Saudação...</p><table>...concorrentes...</table><p>Insight...</p><p>CTA textual.</p><p>Assinatura — Equipe Derekh Food</p>"
}

IMPORTANTE sobre corpo_html:
- APENAS parágrafos (<p>), tabelas (<table>), listas (<ul>/<li>) e estilos inline
- NÃO incluir tags <html>, <head>, <body>, <footer>
- NÃO incluir botão WhatsApp nem link de descadastro (já existem no wrapper automático)
- Saudação personalizada com nome do dono se disponível
- Tabela/lista com dados dos concorrentes (estilizada, limpa)
- Parágrafo de insight + CTA textual ("Quer entender como funciona? Me chama no WhatsApp!")
- Assinatura: Equipe Derekh Food
"""


def gerar_email_competitivo(lead_id: int) -> dict:
    """Gera email personalizado com análise competitiva usando Grok.
    Retorna dict com assunto e corpo_html prontos para envio."""

    if not XAI_API_KEY:
        return {"erro": "XAI_API_KEY não configurada"}

    # Montar contexto
    ctx = montar_contexto_competitivo(lead_id)
    if "erro" in ctx:
        return ctx

    lead = ctx["lead"]
    concorrentes = ctx["concorrentes"]
    mercado = ctx["mercado"]
    abordagem = ctx["abordagem"]

    # Verificar se temos dados suficientes
    if not concorrentes and not mercado.get("total_restaurantes"):
        return {"erro": "Dados insuficientes para gerar email competitivo"}

    # Montar prompt do usuário
    user_prompt = f"""Gere um email de prospecção para este restaurante:

DADOS DO RESTAURANTE ALVO:
{_formatar_lead_para_prompt(lead)}

CONCORRENTES DIRETOS (mesma região):
{_formatar_concorrentes_para_prompt(concorrentes)}

DADOS DO MERCADO LOCAL ({ctx['cidade']}/{ctx['uf']}):
- Total restaurantes mapeados: {mercado.get('total_restaurantes', 0)}
- Com algum delivery: {mercado.get('com_algum_delivery', 0)} ({round(mercado.get('com_algum_delivery', 0) / max(mercado.get('total_restaurantes', 1), 1) * 100)}%)
- Sem delivery: {mercado.get('sem_delivery', 0)}
- Rating médio: {mercado.get('rating_medio', 0)}★
"""

    if ctx.get("delivery_bairro"):
        db = ctx["delivery_bairro"]
        user_prompt += f"""
BAIRRO ({ctx['bairro']}):
- {db.get('percentual', 0)}% dos restaurantes têm delivery
- {db.get('com_delivery', 0)} de {db.get('total', 0)} restaurantes
"""

    if abordagem.get("nome_dono"):
        user_prompt += f"\nNome do dono/administrador: {abordagem['nome_dono']}"

    # Cenário específico
    tem_delivery = (lead.get("tem_ifood") or 0) + (lead.get("tem_rappi") or 0) + (lead.get("tem_99food") or 0)
    if tem_delivery == 0:
        user_prompt += "\n\nCENÁRIO: Restaurante SEM delivery. Foco em mostrar que concorrentes já estão online."
    elif lead.get("ifood_rating") and lead["ifood_rating"] >= 4.5:
        user_prompt += "\n\nCENÁRIO: Restaurante com EXCELENTE nota no iFood. Foco em delivery próprio sem 27% de comissão."
    elif lead.get("tem_ifood"):
        user_prompt += "\n\nCENÁRIO: Restaurante JÁ no iFood. Foco em canal próprio complementar (sem comissão)."
    else:
        user_prompt += "\n\nCENÁRIO: Restaurante com delivery mas sem iFood. Foco em delivery próprio como canal direto."

    # Links para injetar no email
    import urllib.parse
    nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
    wa_text = f"Olá! Vi a análise do mercado de {ctx['cidade']} e quero saber mais sobre a Derekh Food para o {nome_rest}"
    link_whatsapp = f"https://wa.me/{WHATSAPP_INBOUND_NUMBER}?text={urllib.parse.quote(wa_text)}"

    user_prompt += "\n\nGere o JSON com assunto e corpo_html. Lembre: SÓ o corpo (parágrafos), sem html/head/body/footer/botão WA."

    system = SYSTEM_PROMPT_EMAIL

    # Chamar Grok
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                f"{XAI_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": XAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 2000,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        conteudo = data["choices"][0]["message"]["content"]

        # Parsear JSON da resposta
        # Limpar possíveis markdown code blocks
        conteudo = conteudo.strip()
        if conteudo.startswith("```"):
            conteudo = conteudo.split("\n", 1)[1] if "\n" in conteudo else conteudo[3:]
            if conteudo.endswith("```"):
                conteudo = conteudo[:-3]
            conteudo = conteudo.strip()

        resultado = json.loads(conteudo)

        return {
            "sucesso": True,
            "assunto": resultado.get("assunto", ""),
            "corpo_html": resultado.get("corpo_html", ""),
            "lead_id": lead_id,
            "concorrentes_usados": len(concorrentes),
        }

    except json.JSONDecodeError:
        # Tentar extrair mesmo sem JSON perfeito
        return {"erro": "Grok não retornou JSON válido", "raw": conteudo[:500]}
    except httpx.HTTPError as e:
        return {"erro": f"Erro API xAI: {e}"}
    except Exception as e:
        return {"erro": f"Erro inesperado: {e}"}


def gerar_emails_batch(cidade: str = None, limite: int = 10) -> list:
    """Gera emails para um batch de leads com mais dados.
    Prioriza leads com dados completos (iFood + Maps + RF)."""
    leads = leads_com_mais_dados(cidade=cidade, limite=limite)
    resultados = []

    for lead in leads:
        # Verificar se tem email
        if not lead.get("email") or not lead["email"].strip():
            continue

        # Verificar se já não recebeu email recentemente
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) as n FROM emails_enviados
                WHERE lead_id = %s AND horario_enviado >= NOW() - INTERVAL '7 days'
            """, (lead["id"],))
            if cur.fetchone()["n"] > 0:
                continue

        resultado = gerar_email_competitivo(lead["id"])
        resultado["lead_nome"] = lead.get("nome_fantasia") or lead.get("razao_social")
        resultado["lead_email"] = lead.get("email")
        resultados.append(resultado)

    return resultados


# ============================================================
# ENVIO DE EMAIL GERADO PELO GROK
# ============================================================

def enviar_email_grok(lead_id: int) -> dict:
    """Pipeline completo: gera email com Grok + envia via Resend."""
    # Gerar email
    email = gerar_email_competitivo(lead_id)
    if "erro" in email:
        return email

    # Enviar via email_service (que já tem tracking)
    from crm.email_service import enviar_email_personalizado
    resultado = enviar_email_personalizado(
        lead_id=lead_id,
        assunto=email["assunto"],
        corpo=email["corpo_html"],
    )

    if resultado.get("sucesso"):
        resultado["concorrentes_usados"] = email.get("concorrentes_usados", 0)
        resultado["metodo"] = "grok_competitivo"

    return resultado
