"""
wa_sales_bot.py - Bot de vendas WhatsApp via Evolution API (outbound) + Grok IA
Estratégia dual-number:
  - Outbound (prospecção): Evolution API → +55 45 9971-3063
  - Inbound (receber): +55 11 97176-5565 (link nos emails para "Fale Conosco")

v2.0 — Reestruturação completa:
  - Prompts humanizados (gírias, abreviações, tom oral)
  - Intent scoring contextual (não mais keywords binárias)
  - Handoff gradual (imediato / quente / estratégico)
  - Delay variável para parecer humano
  - Contexto resumido do lead no prompt
"""
import os
import re
import json
import hmac
import hashlib
import logging
import tempfile
import base64
import random
import time as _time
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

from crm.database import (
    obter_lead, obter_configuracao, criar_conversa_wa,
    registrar_msg_wa, obter_conversa_wa, obter_conversa_wa_por_lead,
    atualizar_conversa_wa, opt_out_lead, registrar_interacao,
)
from crm.scoring import personalizar_abordagem

log = logging.getLogger("wa_bot")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[WA-BOT] %(message)s"))
    log.addHandler(_h)

# Evolution API config (outbound)
_EVOLUTION_API_URL = os.environ.get("EVOLUTION_API_URL", "https://derekh-evolution.fly.dev")
_EVOLUTION_INSTANCE = os.environ.get("EVOLUTION_INSTANCE", "derekh-whatsapp")
_EVOLUTION_API_KEY = os.environ.get("EVOLUTION_API_KEY", "")

# Número inbound (para incluir nos emails como "Fale Conosco")
WHATSAPP_INBOUND_NUMBER = os.environ.get("WHATSAPP_INBOUND_NUMBER", "5511971765565")

# Fallback: WhatsApp Cloud API (Meta) — mantido para compatibilidade
_GRAPH_API = "https://graph.facebook.com/v21.0"


# ============================================================
# HELPERS
# ============================================================

def _get_evolution_config() -> tuple:
    """Retorna (api_url, instance, api_key) da Evolution API."""
    url = obter_configuracao("evolution_api_url") or _EVOLUTION_API_URL
    instance = obter_configuracao("evolution_instance") or _EVOLUTION_INSTANCE
    key = obter_configuracao("evolution_api_key") or _EVOLUTION_API_KEY
    return url, instance, key


def _get_wa_config() -> tuple:
    """Retorna (phone_number_id, access_token) do WhatsApp Cloud API (fallback)."""
    phone_id = obter_configuracao("wa_phone_id") or os.environ.get("WHATSAPP_PHONE_ID", "")
    token = obter_configuracao("wa_access_token") or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    return phone_id, token


def get_inbound_wa_link(texto: str = "Olá! Gostaria de saber mais sobre a Derekh Food") -> str:
    """Retorna link wa.me para o número inbound (Fale Conosco)."""
    import urllib.parse
    return f"https://wa.me/{WHATSAPP_INBOUND_NUMBER}?text={urllib.parse.quote(texto)}"


def _get_xai_key() -> str:
    """Retorna API key do xAI/Grok."""
    return obter_configuracao("xai_api_key") or os.environ.get("XAI_API_KEY", "")


def _limpar_telefone(tel: str) -> str:
    """Remove caracteres não numéricos."""
    if not tel:
        return ""
    return re.sub(r"\D", "", tel)


def _formatar_numero_wa(telefone: str) -> str:
    """Formata telefone para formato WA internacional.
    Se já tem código de país (>11 dígitos), usa como está.
    Se parece brasileiro (10-11 dígitos sem código), adiciona 55."""
    num = _limpar_telefone(telefone)
    if not num:
        return ""
    # Já tem código de país (ex: 351xxx, 1xxx, 55xxx) — número longo
    if len(num) > 11:
        return num
    # Número brasileiro sem código de país (10-11 dígitos: DDD + número)
    if len(num) >= 10 and not num.startswith("55"):
        num = "55" + num
    return num


def verificar_webhook_meta(body: bytes, signature: str) -> bool:
    """Verifica assinatura HMAC-SHA256 do webhook Meta."""
    secret = os.environ.get("WHATSAPP_WEBHOOK_SECRET", "")
    if not secret:
        log.warning("WHATSAPP_WEBHOOK_SECRET não configurado — pulando verificação")
        return True
    esperado = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(esperado, signature)


def _calcular_delay_humano(mensagem_cliente: str) -> float:
    """Calcula delay variável para parecer humano.
    Mensagens longas = mais tempo 'lendo'. Mínimo 3s, máximo 15s."""
    n_palavras = len(mensagem_cliente.split())
    base = n_palavras * 0.8  # mais palavras = mais tempo "lendo"
    delay = random.uniform(3, max(8, min(base, 15)))
    return delay


# ============================================================
# ENVIO DE MENSAGEM (WhatsApp Cloud API)
# ============================================================

def _enviar_via_evolution(numero: str, texto: str, instance_override: str = "") -> dict:
    """Envia mensagem via Evolution API (outbound prioritário).
    Se instance_override fornecido, usa essa instância em vez da padrão."""
    url, instance, key = _get_evolution_config()
    if instance_override:
        instance = instance_override
    if not url or not key:
        return {"erro": "Evolution API não configurada"}

    try:
        resp = httpx.post(
            f"{url}/message/sendText/{instance}",
            headers={
                "apikey": key,
                "Content-Type": "application/json",
            },
            json={
                "number": numero,
                "text": texto,
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        msg_id = result.get("key", {}).get("id", "")
        log.info(f"Mensagem enviada via Evolution API: {msg_id}")
        return {"sucesso": True, "wa_msg_id": msg_id, "via": "evolution"}
    except Exception as e:
        log.error(f"Erro Evolution API: {e}")
        return {"erro": f"Evolution API: {e}"}


def _enviar_via_cloud_api(numero: str, texto: str) -> dict:
    """Fallback: envia via WhatsApp Cloud API (Meta)."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada"}

    try:
        resp = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "text",
                "text": {"body": texto},
            },
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        wa_msg_id = result.get("messages", [{}])[0].get("id", "")
        log.info(f"Mensagem enviada via Cloud API: wa_msg_id={wa_msg_id}")
        return {"sucesso": True, "wa_msg_id": wa_msg_id, "via": "cloud_api"}
    except Exception as e:
        log.error(f"Erro WhatsApp Cloud API: {e}")
        return {"erro": f"Cloud API: {e}"}


def enviar_mensagem_wa(lead_id: int, texto: str, tom: str = "informal") -> dict:
    """Envia mensagem de texto via WhatsApp.
    Prioridade: Evolution API → Cloud API (fallback).
    Cria conversa se não existir."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out de WhatsApp"}

    if httpx is None:
        return {"erro": "httpx não instalado (pip install httpx)"}

    # Criar ou buscar conversa
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa:
        conversa_id = conversa["id"]
        numero = conversa.get("numero_envio") or ""
    else:
        telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
        numero = _formatar_numero_wa(telefone)
        conversa_id = criar_conversa_wa(lead_id, numero, tom)

    if not numero:
        return {"erro": "Lead sem telefone válido"}

    # Enviar: Evolution API (prioritário, instância outbound) → Cloud API (fallback)
    resultado = _enviar_via_evolution(numero, texto)  # usa instância padrão (outbound)
    if resultado.get("erro"):
        log.warning(f"Evolution falhou, tentando Cloud API: {resultado['erro']}")
        resultado = _enviar_via_cloud_api(numero, texto)

    if resultado.get("erro"):
        registrar_msg_wa(conversa_id, "enviada", texto, intencao="erro_envio")
        return {"erro": resultado["erro"]}

    # Registrar mensagem
    msg_id = registrar_msg_wa(conversa_id, "enviada", texto)

    # Registrar interação no CRM
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA enviado ({resultado.get('via', '?')}): {texto[:100]}...", "enviado")

    log.info(f"Mensagem enviada para lead {lead_id} ({numero}) via {resultado.get('via')}")
    return {"sucesso": True, "conversa_id": conversa_id, "msg_id": msg_id,
            "via": resultado.get("via")}


# ============================================================
# ÁUDIO TTS (Grok)
# ============================================================

def gerar_script_audio(lead: dict) -> str:
    """Gera script de áudio personalizado para o lead (~30s).
    Usa dados iFood enriquecidos quando disponíveis."""
    pers = personalizar_abordagem(lead)
    nome_dono = pers.get("nome_dono") or "proprietário"
    nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante"
    rating = lead.get("rating") or 0
    reviews = lead.get("total_reviews") or 0
    ifood_rating = lead.get("ifood_rating") or 0
    ifood_reviews = lead.get("ifood_reviews") or 0
    ifood_categorias = lead.get("ifood_categorias") or ""
    tem_ifood = lead.get("tem_ifood") or 0

    # Prioridade: dados iFood > dados Google
    if tem_ifood and ifood_rating > 0 and ifood_reviews > 0:
        cat_mention = ""
        if ifood_categorias:
            primeira_cat = ifood_categorias.split(",")[0].strip()
            cat_mention = f"Vocês trabalham com {primeira_cat} e "
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é da Derekh Food. "
            f"Vi que o {nome_rest} tem nota {ifood_rating} no iFood "
            f"com {ifood_reviews} avaliações, parabéns pela qualidade! "
            f"{cat_mention}já têm uma clientela fiel. "
            f"Imagina ter delivery próprio, sem pagar os 27 por cento de comissão? "
            f"A Derekh monta tudo em 48 horas. Posso te mostrar?"
        )
    elif rating > 0 and reviews > 0:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é da Derekh Food. "
            f"Vi que o {nome_rest} tem uma nota de {rating} estrelas "
            f"com {reviews} avaliações no Google, parabéns pelo trabalho! "
            f"O que falta é um delivery próprio, sem pagar comissão pro iFood. "
            f"A Derekh cria seu delivery por WhatsApp em 48 horas. "
            f"Posso te mostrar como funciona?"
        )
    elif not tem_ifood:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é da Derekh Food. "
            f"Vi que o {nome_rest} ainda não está no delivery online. "
            f"A Derekh cria seu delivery próprio em 48 horas, "
            f"com cardápio digital, pagamento Pix e zero comissão. "
            f"Posso te contar como funciona?"
        )
    else:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é da Derekh Food. "
            f"Trabalho com restaurantes e vi que o {nome_rest} "
            f"tem tudo para crescer com delivery próprio. "
            f"Sem comissão de 27 por cento, seus clientes pedem direto com você. "
            f"Posso te contar como funciona?"
        )
    return script


def gerar_audio_tts(texto: str, voz: str = "ara") -> Optional[str]:
    """Gera áudio via Grok TTS. Retorna path do arquivo .mp3 ou None."""
    xai_key = _get_xai_key()
    if not xai_key:
        log.error("XAI_API_KEY não configurada")
        return None

    if httpx is None:
        log.error("httpx não instalado")
        return None

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/audio/speech",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={"model": "grok-3-fast-tts", "input": texto, "voice": voz},
            timeout=30,
        )
        resp.raise_for_status()

        # Salvar áudio
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(resp.content)
        tmp.close()
        log.info(f"Áudio TTS gerado: {tmp.name} ({len(resp.content)} bytes)")
        return tmp.name

    except Exception as e:
        log.error(f"Erro Grok TTS: {e}")
        return None


def _upload_media_wa(audio_path: str) -> Optional[str]:
    """Upload de mídia para WhatsApp Cloud API. Retorna media_id ou None."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return None

    try:
        with open(audio_path, "rb") as f:
            resp = httpx.post(
                f"{_GRAPH_API}/{phone_id}/media",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": ("audio.mp3", f, "audio/mpeg")},
                data={"messaging_product": "whatsapp", "type": "audio/mpeg"},
                timeout=30,
            )
        resp.raise_for_status()
        media_id = resp.json().get("id")
        log.info(f"Media uploaded: {media_id}")
        return media_id
    except Exception as e:
        log.error(f"Erro upload media: {e}")
        return None


def enviar_audio_wa(lead_id: int, voz: str = "ara") -> dict:
    """Gera áudio personalizado e envia via WhatsApp Cloud API."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out"}

    telefone = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    numero = _formatar_numero_wa(telefone)
    if not numero:
        return {"erro": "Lead sem telefone"}

    # Gerar script e áudio
    script = gerar_script_audio(lead)
    audio_path = gerar_audio_tts(script, voz)
    if not audio_path:
        return {"erro": "Falha ao gerar áudio TTS"}

    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada"}

    # Criar/buscar conversa
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa:
        conversa_id = conversa["id"]
    else:
        conversa_id = criar_conversa_wa(lead_id, numero, voz=voz)

    # Upload áudio para Meta e enviar
    try:
        media_id = _upload_media_wa(audio_path)
        if not media_id:
            return {"erro": "Falha no upload do áudio para WhatsApp"}

        resp = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": numero,
                "type": "audio",
                "audio": {"id": media_id},
            },
            timeout=15,
        )
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Erro envio áudio: {e}")
        return {"erro": f"Falha no envio: {e}"}
    finally:
        try:
            os.unlink(audio_path)
        except Exception:
            pass

    # Registrar
    msg_id = registrar_msg_wa(conversa_id, "enviada", f"[ÁUDIO] {script[:100]}...", tipo="audio")
    atualizar_conversa_wa(conversa_id, usou_audio=True, voz_usada=voz)
    registrar_interacao(lead_id, "whatsapp", "whatsapp", f"Áudio WA enviado (voz: {voz})", "enviado")

    log.info(f"Áudio enviado para lead {lead_id}")
    return {"sucesso": True, "conversa_id": conversa_id, "msg_id": msg_id}


# ============================================================
# INTENT SCORING (substitui keywords binárias)
# ============================================================

INTENT_PATTERNS = {
    # Alta intenção (score +30 cada)
    "high_intent": [
        "quanto custa", "qual o preço", "qual o preco", "como contrato", "quero contratar",
        "me manda proposta", "quero testar", "teste grátis", "teste gratis", "trial",
        "demo", "como funciona o plano", "aceita pix", "quero fechar", "me passa o link",
        "como assino", "quero assinar", "período grátis", "periodo gratis",
        "15 dias", "experimentar",
    ],
    # Média intenção (score +15 cada)
    "medium_intent": [
        "como funciona", "me interessa", "me explica", "quero saber mais",
        "tem site", "é app", "e app", "quanto tempo pra instalar", "pode me",
        "falar mais", "ver", "quero saber",
    ],
    # Sinais de uso de concorrente (score +20 — DOR pra explorar)
    "competitor_pain": [
        "ifood", "rappi", "uber eats", "comissão", "comissao", "taxa",
        "tô pagando muito", "to pagando muito", "delivery tá caro",
        "delivery ta caro", "27%", "27 por cento",
    ],
    # Objeção (NÃO é negativo — é oportunidade de contornar)
    "objection": [
        "caro", "não sei", "nao sei", "vou pensar", "já tenho sistema", "ja tenho sistema",
        "não é o momento", "nao e o momento", "depois", "sem grana", "sem dinheiro",
        "tá difícil", "ta dificil", "não preciso", "nao preciso",
    ],
    # Opt-out real (encerra DEFINITIVAMENTE — nunca mais contata)
    "opt_out": [
        "sair", "parar", "cancelar", "não quero mais", "nao quero mais", "remover",
        "stop", "para de mandar", "não me mande mais", "nao me mande mais",
        "desinscrever", "me tira dessa lista",
    ],
    # Recusa firme (encerra conversa com classe, mas pode reativar se voltar)
    "hard_no": [
        "não tenho interesse nenhum", "nao tenho interesse nenhum",
        "já disse que não", "ja disse que nao", "chega", "não enche", "nao enche",
        "sem interesse", "não quero", "nao quero",
    ],
}


def detectar_intencao(mensagem: str) -> dict:
    """Detecta intenção por scoring contextual.
    Retorna dict com: intencao (str), score (int), matches (list), objecoes (list)."""
    msg = mensagem.lower().strip()
    score = 0
    matches = []
    objecoes = []

    # Opt-out tem prioridade absoluta
    for kw in INTENT_PATTERNS["opt_out"]:
        if kw in msg:
            return {"intencao": "opt_out", "score": 0, "matches": [kw], "objecoes": []}

    # Recusa firme
    for kw in INTENT_PATTERNS["hard_no"]:
        if kw in msg:
            return {"intencao": "hard_no", "score": 0, "matches": [kw], "objecoes": []}

    # Scoring: alta intenção (+30)
    for kw in INTENT_PATTERNS["high_intent"]:
        if kw in msg:
            score += 30
            matches.append(kw)

    # Scoring: média intenção (+15)
    for kw in INTENT_PATTERNS["medium_intent"]:
        if kw in msg:
            score += 15
            matches.append(kw)

    # Scoring: dor de concorrente (+20)
    for kw in INTENT_PATTERNS["competitor_pain"]:
        if kw in msg:
            score += 20
            matches.append(kw)

    # Objeções (não reduzem score, são oportunidades)
    for kw in INTENT_PATTERNS["objection"]:
        if kw in msg:
            objecoes.append(kw)

    # Pergunta = curiosidade (+10)
    if "?" in msg:
        score += 10

    # Classificar
    if score >= 30:
        intencao = "interesse_alto" if score >= 50 else "interesse"
    elif objecoes:
        intencao = "objecao"
    elif "?" in msg:
        intencao = "duvida"
    else:
        intencao = "outro"

    return {"intencao": intencao, "score": score, "matches": matches, "objecoes": objecoes}


# ============================================================
# CONTEXTO DO LEAD (resumo para o prompt)
# ============================================================

def _build_lead_context(conversa: dict, lead: dict) -> str:
    """Monta resumo contextual do lead para injetar no prompt."""
    nome_rest = conversa.get("nome_fantasia") or conversa.get("razao_social") or "restaurante"
    cidade = (lead or {}).get("cidade") or ""
    rating = conversa.get("rating") or 0
    reviews = conversa.get("total_reviews") or 0

    # Dados iFood
    tem_ifood = (lead or {}).get("tem_ifood") or 0
    ifood_rating = (lead or {}).get("ifood_rating") or 0
    ifood_reviews = (lead or {}).get("ifood_reviews") or 0
    ifood_categorias = (lead or {}).get("ifood_categorias") or ""
    ifood_preco = (lead or {}).get("ifood_preco") or ""

    # Bloco iFood
    ifood_context = ""
    if tem_ifood and (ifood_rating or ifood_categorias):
        parts = []
        if ifood_rating:
            s = f"Rating iFood: {ifood_rating}"
            if ifood_reviews:
                s += f" ({ifood_reviews} avaliações)"
            parts.append(s)
        if ifood_categorias:
            parts.append(f"Categorias: {ifood_categorias}")
        if ifood_preco:
            parts.append(f"Faixa: {ifood_preco}")
        ifood_context = "\nDados iFood: " + " · ".join(parts)

    # Cenário
    cenario = ""
    if not tem_ifood:
        cenario = "\nCenário: restaurante SEM delivery online — oportunidade pura."
    elif ifood_rating and ifood_rating >= 4.5:
        cenario = f"\nCenário: nota excelente no iFood ({ifood_rating}★) — merece canal próprio sem comissão."
    elif ifood_reviews and ifood_reviews >= 500:
        cenario = f"\nCenário: restaurante popular ({ifood_reviews} avaliações) — falta canal direto."

    # Histórico de interações
    msgs = conversa.get("mensagens") or []
    n_msgs = len([m for m in msgs if m["direcao"] == "recebida"])
    intencao_atual = conversa.get("intencao_detectada") or "desconhecida"

    # Objeções levantadas anteriormente
    objecoes_anteriores = []
    for m in msgs:
        if m["direcao"] == "recebida":
            det = detectar_intencao(m.get("conteudo") or "")
            objecoes_anteriores.extend(det.get("objecoes", []))
    objecoes_unicas = list(set(objecoes_anteriores))

    resumo = f"""RESUMO DO LEAD:
Restaurante: {nome_rest}{f' ({cidade})' if cidade else ''}
Google: {rating}★ ({reviews} avaliações)
Usa iFood: {'Sim' if tem_ifood else 'Não sei'}
{ifood_context}{cenario}
Msgs trocadas: {n_msgs}
Intenção atual: {intencao_atual}
{'Objeções levantadas: ' + ', '.join(objecoes_unicas) if objecoes_unicas else 'Sem objeções ainda'}"""
    return resumo


# ============================================================
# PROMPTS IA (v2.0 — humanizados)
# ============================================================

def _build_system_prompt_conversa(lead_context: str, n_turnos: int) -> str:
    """System prompt para conversa em andamento com lead existente."""
    return f"""Você é Klenilton, vendedor humano da Derekh Food. Você NÃO é um robô, assistente virtual ou IA.

QUEM VOCÊ É:
- Vendedor experiente de tecnologia para restaurantes
- Fala como gente real no WhatsApp: usa "kkk", "show", "massa", "dahora" quando natural
- Tem personalidade: é animado mas não forçado, direto mas acolhedor
- Às vezes erra digitação de propósito (tipo "tbm", "vc", "qdo")
- Manda áudio mental: escreve como se estivesse falando (frases curtas, tom oral)

{lead_context}

O QUE VOCÊ VENDE:
Derekh Food — sistema delivery próprio. 0% comissão (iFood cobra 27%).
7 apps integrados. Planos de R$169,90 a R$527/mês. Setup 48h, sem fidelidade.
WhatsApp Humanoide: incluso no Premium, nos demais +R$99,45/mês.
Site: https://superfood-api.fly.dev

ANTES DE CADA RESPOSTA, PENSE (não escreva isso pro cliente):
1. FASE DO LEAD: Curioso / Interessado / Comparando / Quase fechando / Esfriando / Voltou depois de sumir
2. EMOÇÃO: Animado / Desconfiado / Apressado / Entediado / Resistente
3. ESTRATÉGIA: O que dizer pra avançar ele pro próximo estágio?
4. GANCHO: Que dor específica DESTE restaurante eu posso cutucar?

TÁTICAS DE VENDA (use naturalmente, não como checklist):
- ESPELHAMENTO: repita palavras que o cliente usou ("vc falou que tá cansado do iFood, né?")
- DOR ESPECÍFICA: se tem iFood, calcule quanto perde em comissão ("com essas avaliações, quanto vc fatura no iFood? só de comissão deve ir uns R$X mil/mês embora")
- ESCASSEZ REAL: "tô com agenda apertada essa semana mas consigo encaixar uma demo"
- PROVA SOCIAL: mencione que "um restaurante aqui da região" já usa (sem inventar nomes)
- MICRO-COMPROMISSOS: não peça pra fechar, peça pra "dar uma olhada de 5 min"
- REATIVAÇÃO: se sumiu e voltou, "e aí, conseguiu pensar sobre aquilo?"
- OBJEÇÃO = OPORTUNIDADE: "caro" → "quanto vc paga de comissão no iFood por mês?"

COMO INSISTIR SEM SER CHATO:
- Nunca repita o mesmo argumento. Se já falou de comissão, fale de autonomia.
- Se o cara ficou em silêncio, mande UMA mensagem casual depois ("e aí, conseguiu ver?")
- Se disse "vou pensar", responda "tranquilo! só pra eu saber, o que ficou te travando?"
- Se disse "não tenho interesse" de forma vaga, sonde: "entendo! curiosidade: vc já usa algum sistema próprio?"
- Se disse "NÃO" firme ou pediu pra parar, encerre com classe.

FORMATO:
- Máximo 2-3 frases por mensagem
- UMA mensagem por vez
- Zero emojis corporativos (NÃO use 🚀📈💪🎯). Pode usar 😅🤙👊 se fizer sentido
- Nunca liste features em bullet points. Fale de UMA coisa por vez.
- Varie seu estilo entre mensagens. Às vezes comece com "olha", às vezes com "então", às vezes direto no assunto. Nunca use a mesma abertura duas vezes seguidas.
- Ocasionalmente (1 em cada 5 msgs), use uma abreviação ou gíria: "pô", "mano", "tlgd", "blz"

{"PRIMEIRA INTERAÇÃO: cumprimente, diga seu nome e pergunte como pode ajudar. NÃO liste preços nem features." if n_turnos <= 1 else "Você JÁ se apresentou. NÃO se apresente de novo. Continue a conversa naturalmente de onde parou."}
{"Se o cliente voltou depois de dias/semanas, retome naturalmente: 'e aí, conseguiu pensar sobre aquilo?'" if n_turnos > 3 else ""}"""


def _build_system_prompt_inbound() -> str:
    """System prompt para primeiro contato inbound (alguém mandou msg pela primeira vez)."""
    return """Você é Klenilton, vendedor da Derekh Food. Alguém mandou mensagem pela primeira vez.

PERSONALIDADE: vendedor humano, informal, WhatsApp. Você NÃO é robô.
Fala como gente: "e aí", "beleza", "show", "massa". Às vezes abrevia: "vc", "tbm", "qdo".

PRIMEIRA MENSAGEM — ESCOLHA UMA ABORDAGEM (não siga sempre a mesma):
Opção A: "E aí! Klenilton aqui da Derekh Food 🤙 em que posso te ajudar?"
Opção B: "Fala! Sou o Klenilton, tudo bem? Vi que mandou msg, conta pra mim o que vc tá buscando"
Opção C: "Opa, beleza? Klenilton aqui! Me diz como posso te ajudar"
(Varie entre elas, não use sempre a mesma)

REGRA DE OURO: na primeira msg NÃO fale preço, features, nada. Só cumprimente e pergunte.

DEPOIS DA PRIMEIRA:
- Faça perguntas pra entender a DOR antes de oferecer solução
- "Vc tem delivery próprio ou usa iFood/Rappi?"
- "Qual o maior perrengue do seu delivery hoje?"
- Só fale do sistema quando souber o que o cara precisa

COLETA NATURAL (não faça formulário):
Ao longo da conversa, tente descobrir: nome do restaurante, cidade, tipo de comida.
Mas de forma orgânica, não "qual seu nome? qual sua cidade?"

SOBRE A DEREKH FOOD (use só quando perguntarem):
- Sistema delivery próprio — 0% comissão (iFood cobra 27%)
- 7 apps integrados
- Planos: Básico R$169,90 · Essencial R$279,90 · Avançado R$329,90 · Premium R$527/mês
- WhatsApp Humanoide: incluso no Premium, nos demais +R$99,45/mês
- Setup em 48h, sem fidelidade
- Site: https://superfood-api.fly.dev

SE PEDIR HUMANO: "Show, vou te passar pro time agora!"
PORTUGUÊS BRASILEIRO. Nunca invente dados."""


# ============================================================
# RESPONDER COM IA (v2.0)
# ============================================================

def responder_com_ia(conversa_id: int, mensagem_lead: str) -> dict:
    """Usa Grok IA para gerar resposta contextualizada.
    NÃO salva a resposta no banco — o chamador é responsável por salvar/enviar."""
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return {"erro": "Conversa não encontrada"}

    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}

    if httpx is None:
        return {"erro": "httpx não instalado"}

    # Contexto completo do lead
    lead_completo = obter_lead(conversa.get("lead_id")) if conversa.get("lead_id") else {}
    lead_context = _build_lead_context(conversa, lead_completo)

    # Histórico da conversa (últimas 30 msgs — contexto persistente)
    historico = []
    for msg in (conversa.get("mensagens") or [])[-30:]:
        role = "assistant" if msg["direcao"] == "enviada" else "user"
        conteudo = msg["conteudo"] or ""
        if conteudo:
            historico.append({"role": role, "content": conteudo})

    historico.append({"role": "user", "content": mensagem_lead})

    # Contar turnos para adaptar comportamento
    n_turnos = len([m for m in historico if m["role"] == "user"])

    system_prompt = _build_system_prompt_conversa(lead_context, n_turnos)

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-fast",
                "messages": [{"role": "system", "content": system_prompt}] + historico,
                "max_tokens": 150,
                "temperature": 0.8,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
    except Exception as e:
        log.error(f"Erro Grok IA: {e}")
        return {"erro": f"Falha na IA: {e}"}

    return {"sucesso": True, "resposta": resposta}


# ============================================================
# HANDOFF GRADUAL (v2.0)
# ============================================================

def avaliar_handoff(conversa_id: int) -> tuple:
    """Avalia se deve fazer handoff para humano — escalonamento gradual.
    Retorna (tipo_handoff, motivo).
    tipo_handoff: None | "immediate" | "warm" | "strategic" """
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return None, ""

    msgs_recebidas = conversa.get("msgs_recebidas", 0)
    score = conversa.get("lead_score", 0)

    # Coletar dados das mensagens
    pediu_demo = False
    pediu_humano = False
    objecoes_nao_resolvidas = 0
    intent_score_acumulado = 0

    for msg in (conversa.get("mensagens") or []):
        if msg["direcao"] == "recebida":
            txt = (msg.get("conteudo") or "").lower()

            # Pediu demo/reunião?
            if any(w in txt for w in ("demo", "agendar", "reunião", "reuniao",
                                       "amanhã", "amanha", "horário", "horario",
                                       "quero ver", "me mostra")):
                pediu_demo = True

            # Pediu humano?
            if any(w in txt for w in ("falar com alguém", "falar com alguem",
                                       "atendente", "humano", "pessoa real",
                                       "gerente", "responsável", "responsavel")):
                pediu_humano = True

            # Contar objeções
            det = detectar_intencao(txt)
            if det.get("objecoes"):
                objecoes_nao_resolvidas += 1
            intent_score_acumulado += det.get("score", 0)

    # 1. HANDOFF IMEDIATO — pediu demo ou humano
    if pediu_demo or pediu_humano:
        motivo = "Lead pediu demo/reunião" if pediu_demo else "Lead pediu atendente humano"
        return "immediate", motivo

    # 2. HANDOFF QUENTE — lead muito engajado
    if intent_score_acumulado >= 60 and msgs_recebidas >= 3:
        return "warm", f"Lead engajado (score acumulado={intent_score_acumulado}, {msgs_recebidas} msgs)"

    # 3. HANDOFF QUENTE — score CRM alto
    if score >= 85 and msgs_recebidas >= 1:
        return "warm", f"Lead HOT (score CRM={score}) respondeu"

    # 4. HANDOFF ESTRATÉGICO — objeções não resolvidas
    if objecoes_nao_resolvidas >= 2:
        return "strategic", f"Lead com {objecoes_nao_resolvidas} objeções — escalar para gerente"

    return None, ""


# ============================================================
# PROCESSAR RESPOSTAS (PRINCIPAL)
# ============================================================

def processar_resposta_wa(numero_remetente: str, mensagem: str, instance: str = "") -> dict:
    """Processa mensagem recebida — de lead existente OU contato novo.
    Se não existir conversa, cria lead inbound + conversa e responde.
    Se existir conversa encerrada/handoff, REATIVA (contexto persistente).
    IMPORTANTE: cada mensagem é salva UMA VEZ e enviada UMA VEZ.
    instance: nome da instância Evolution de onde veio a msg (para responder pelo mesmo número)."""
    numero = _limpar_telefone(numero_remetente)

    # Buscar conversa pelo número — primeiro ativa, depois qualquer status (exceto opt_out)
    from crm.database import get_conn, criar_lead_inbound, criar_conversa_wa as _criar_conv
    with get_conn() as conn:
        cur = conn.cursor()
        # Prioridade 1: conversa ativa
        cur.execute("""
            SELECT c.id, c.lead_id, c.status FROM wa_conversas c
            WHERE c.numero_envio = %s AND c.status = 'ativo'
            ORDER BY c.created_at DESC LIMIT 1
        """, (numero,))
        row = cur.fetchone()

        # Prioridade 2: conversa encerrada/handoff (REATIVAR — manter contexto)
        if not row:
            cur.execute("""
                SELECT c.id, c.lead_id, c.status FROM wa_conversas c
                WHERE c.numero_envio = %s AND c.status IN ('encerrado', 'handoff')
                ORDER BY c.updated_at DESC LIMIT 1
            """, (numero,))
            row = cur.fetchone()
            if row:
                # Reativar conversa — contexto persistente!
                cur.execute("UPDATE wa_conversas SET status = 'ativo' WHERE id = %s", (row["id"],))
                conn.commit()
                log.info(f"Conversa {row['id']} REATIVADA para {numero} (era {row['status']})")

    if not row:
        # --- NOVO CONTATO (nunca conversou antes): criar lead + conversa ---
        log.info(f"Novo contato inbound: {numero} (instance={instance}) — criando lead e conversa")
        lead_id = criar_lead_inbound(numero)
        conversa_id = _criar_conv(lead_id, numero, "consultivo")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="interesse")
        registrar_interacao(lead_id, "whatsapp", "whatsapp",
                            f"WA inbound: {mensagem[:100]}", "positivo")

        # Delay humano antes de responder
        delay = _calcular_delay_humano(mensagem)
        log.info(f"Delay humano: {delay:.1f}s antes de responder inbound")
        _time.sleep(delay)

        # Responder com IA (prompt de boas-vindas)
        resultado_ia = _responder_inbound(conversa_id, mensagem)
        if resultado_ia.get("sucesso"):
            enviado = _enviar_direto(numero, resultado_ia["resposta"], instance=instance)
            registrar_msg_wa(conversa_id, "enviada", resultado_ia["resposta"], grok=True)
            if enviado.get("sucesso"):
                log.info(f"Resposta inbound enviada para {numero} via {instance or 'default'}")
            else:
                log.warning(f"Falha envio inbound {numero}: {enviado.get('erro')}")

        return {"processado": True, "inbound": True, "lead_id": lead_id}

    conversa_id = row["id"]
    lead_id = row["lead_id"]

    # Detectar intenção (scoring contextual v2.0)
    intent_result = detectar_intencao(mensagem)
    intencao = intent_result["intencao"]
    intent_score = intent_result["score"]
    objecoes = intent_result["objecoes"]

    # Registrar mensagem recebida (1x)
    registrar_msg_wa(conversa_id, "recebida", mensagem, intencao=intencao)
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA recebido: {mensagem[:100]}", "positivo")

    log.info(f"Resposta do lead {lead_id}: intenção={intencao} score={intent_score} "
             f"objeções={objecoes} (instance={instance})")

    # Buscar número de envio
    conversa_full = obter_conversa_wa(conversa_id)
    numero_envio = (conversa_full or {}).get("numero_envio") or numero

    # --- OPT-OUT: remove da lista para sempre ---
    if intencao == "opt_out":
        opt_out_lead(lead_id, "wa")
        atualizar_conversa_wa(conversa_id, status="opt_out", intencao_detectada="opt_out")
        _enviar_e_salvar(conversa_id, numero_envio,
                         "Tranquilo, te tirei da lista. Desculpa o incômodo! 🤙",
                         instance=instance)
        return {"processado": True, "intencao": "opt_out", "lead_id": lead_id}

    # --- RECUSA FIRME: encerra com classe (mas pode reativar se voltar) ---
    if intencao == "hard_no":
        atualizar_conversa_wa(conversa_id, intencao_detectada="hard_no")
        # Delay humano
        _time.sleep(_calcular_delay_humano(mensagem))
        _enviar_e_salvar(conversa_id, numero_envio,
                         "De boa, entendo! Se um dia precisar de algo, tô por aqui. Sucesso! 🤙",
                         instance=instance)
        atualizar_conversa_wa(conversa_id, status="encerrado")
        return {"processado": True, "intencao": "hard_no", "lead_id": lead_id}

    # --- TUDO MAIS: IA responde (interesse, objeção, dúvida, outro) ---
    atualizar_conversa_wa(conversa_id, intencao_detectada=intencao)

    # Delay humano antes de responder
    delay = _calcular_delay_humano(mensagem)
    log.info(f"Delay humano: {delay:.1f}s antes de responder lead {lead_id}")
    _time.sleep(delay)

    resultado_ia = responder_com_ia(conversa_id, mensagem)

    if resultado_ia.get("sucesso"):
        # Enviar + salvar (1x cada)
        _enviar_e_salvar(conversa_id, numero_envio, resultado_ia["resposta"],
                         grok=True, instance=instance)

        # Avaliar handoff gradual
        handoff_tipo, motivo = avaliar_handoff(conversa_id)
        if handoff_tipo == "immediate":
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            # Notificar o dono
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF IMEDIATO lead {lead_id}: {motivo}")

        elif handoff_tipo == "warm":
            # Bot faz a transição naturalmente
            _time.sleep(random.uniform(2, 5))
            _enviar_e_salvar(conversa_id, numero_envio,
                             "Olha, deixa eu te passar pro time técnico que eles conseguem "
                             "te mostrar o sistema ao vivo, rapidinho. Já já alguém te chama!",
                             instance=instance)
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF QUENTE lead {lead_id}: {motivo}")

        elif handoff_tipo == "strategic":
            _time.sleep(random.uniform(2, 5))
            _enviar_e_salvar(conversa_id, numero_envio,
                             "Sabe o que, vou pedir pro meu gerente te dar um toque, "
                             "ele explica melhor essa parte. Pode ser?",
                             instance=instance)
            atualizar_conversa_wa(conversa_id, status="handoff", handoff_motivo=motivo)
            _notificar_handoff(lead_id, numero, motivo, instance)
            log.info(f"HANDOFF ESTRATÉGICO lead {lead_id}: {motivo}")

    return {"processado": True, "intencao": intencao, "score": intent_score, "lead_id": lead_id}


# ============================================================
# ENVIO HELPERS
# ============================================================

def _enviar_e_salvar(conversa_id: int, numero: str, texto: str, grok: bool = False, instance: str = ""):
    """Envia mensagem via Evolution/Cloud API e salva no banco UMA VEZ."""
    resultado = _enviar_direto(numero, texto, instance=instance)
    registrar_msg_wa(conversa_id, "enviada", texto, grok=grok)
    if not resultado.get("sucesso"):
        log.warning(f"Falha envio para {numero}: {resultado.get('erro')}")
    return resultado


def _enviar_direto(numero: str, texto: str, instance: str = "") -> dict:
    """Envia mensagem direta para um número (sem precisar de lead_id).
    Prioridade: Evolution API → Cloud API.
    Se instance fornecido, usa essa instância Evolution específica."""
    # Tentar Evolution API primeiro
    resultado = _enviar_via_evolution(numero, texto, instance_override=instance)
    if resultado.get("sucesso"):
        log.info(f"Mensagem direta enviada via Evolution ({instance or 'default'}) para {numero}")
        return resultado

    # Fallback Cloud API
    resultado = _enviar_via_cloud_api(numero, texto)
    if resultado.get("sucesso"):
        log.info(f"Mensagem direta enviada via Cloud API para {numero}")
        return resultado

    log.error(f"Falha envio direto {numero}: Evolution e Cloud API falharam")
    return resultado


def _responder_inbound(conversa_id: int, mensagem: str) -> dict:
    """Responde primeira mensagem de contato inbound (alguém do site/landing)."""
    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}
    if httpx is None:
        return {"erro": "httpx não instalado"}

    system_prompt = _build_system_prompt_inbound()

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-fast",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": mensagem},
                ],
                "max_tokens": 100,
                "temperature": 0.85,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
        return {"sucesso": True, "resposta": resposta}
    except Exception as e:
        log.error(f"Erro Grok IA inbound: {e}")
        return {"erro": f"Falha na IA: {e}"}


# ============================================================
# NOTIFICAÇÕES
# ============================================================

def _notificar_trial(lead_id: int, numero_lead: str, instance: str = ""):
    """Notifica o dono (Klenilton) quando lead pede teste grátis."""
    lead = obter_lead(lead_id)
    nome_rest = "Restaurante"
    cidade = ""
    if lead:
        nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
        cidade = lead.get("cidade") or ""

    # Número do dono: config ou env
    numero_dono = obter_configuracao("telefone_usuario") or os.environ.get("WA_SALES_NUMERO", "")
    numero_dono = _limpar_telefone(numero_dono)
    if not numero_dono:
        log.warning("Não há número do dono configurado para notificação de trial")
        return

    texto = (
        f"🔔 LEAD QUENTE!\n\n"
        f"*{nome_rest}*"
        + (f" ({cidade})" if cidade else "") +
        f" quer iniciar teste grátis de 15 dias!\n\n"
        f"Número: {numero_lead}\n"
        f"Lead ID: {lead_id}"
    )

    resultado = _enviar_direto(numero_dono, texto, instance=instance)
    if resultado.get("sucesso"):
        log.info(f"Notificação trial enviada ao dono para lead {lead_id}")
    else:
        log.warning(f"Falha ao notificar dono sobre trial lead {lead_id}: {resultado.get('erro')}")


def _notificar_handoff(lead_id: int, numero_lead: str, motivo: str, instance: str = ""):
    """Notifica o dono quando um lead precisa de atendimento humano."""
    lead = obter_lead(lead_id)
    nome_rest = "Restaurante"
    cidade = ""
    if lead:
        nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "Restaurante"
        cidade = lead.get("cidade") or ""

    numero_dono = obter_configuracao("telefone_usuario") or os.environ.get("WA_SALES_NUMERO", "")
    numero_dono = _limpar_telefone(numero_dono)
    if not numero_dono:
        log.warning("Não há número do dono configurado para notificação de handoff")
        return

    texto = (
        f"🔥 HANDOFF!\n\n"
        f"*{nome_rest}*"
        + (f" ({cidade})" if cidade else "") +
        f"\nMotivo: {motivo}\n\n"
        f"Número: {numero_lead}\n"
        f"Lead ID: {lead_id}\n\n"
        f"⚡ Esse lead precisa de atenção AGORA!"
    )

    resultado = _enviar_direto(numero_dono, texto, instance=instance)
    if resultado.get("sucesso"):
        log.info(f"Notificação handoff enviada ao dono para lead {lead_id}")
    else:
        log.warning(f"Falha ao notificar dono sobre handoff lead {lead_id}: {resultado.get('erro')}")
