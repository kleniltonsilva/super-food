"""
wa_sales_bot.py - Bot de vendas WhatsApp via Meta Cloud API + Grok IA
Envia mensagens, áudios TTS, processa respostas com IA.
Integração direta com WhatsApp Cloud API (sem Evolution API).
"""
import os
import re
import json
import hmac
import hashlib
import logging
import tempfile
import base64
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

# WhatsApp Cloud API base
_GRAPH_API = "https://graph.facebook.com/v21.0"


# ============================================================
# HELPERS
# ============================================================

def _get_wa_config() -> tuple:
    """Retorna (phone_number_id, access_token) do WhatsApp Cloud API."""
    phone_id = obter_configuracao("wa_phone_id") or os.environ.get("WHATSAPP_PHONE_ID", "")
    token = obter_configuracao("wa_access_token") or os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
    return phone_id, token


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


# ============================================================
# ENVIO DE MENSAGEM (WhatsApp Cloud API)
# ============================================================

def enviar_mensagem_wa(lead_id: int, texto: str, tom: str = "informal") -> dict:
    """Envia mensagem de texto via WhatsApp Cloud API.
    Cria conversa se não existir."""
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    if lead.get("opt_out_wa"):
        return {"erro": "Lead fez opt-out de WhatsApp"}

    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        return {"erro": "WhatsApp Cloud API não configurada (WHATSAPP_PHONE_ID / WHATSAPP_ACCESS_TOKEN)"}

    # Criar ou buscar conversa — usar numero_envio da conversa se existir
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

    # Enviar via WhatsApp Cloud API
    try:
        if httpx is None:
            return {"erro": "httpx não instalado (pip install httpx)"}

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
    except Exception as e:
        log.error(f"Erro WhatsApp Cloud API: {e}")
        registrar_msg_wa(conversa_id, "enviada", texto, intencao="erro_envio")
        return {"erro": f"Falha no envio: {e}"}

    # Registrar mensagem
    msg_id = registrar_msg_wa(conversa_id, "enviada", texto)

    # Registrar interação no CRM
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA enviado: {texto[:100]}...", "enviado")

    log.info(f"Mensagem enviada para lead {lead_id} ({numero})")
    return {"sucesso": True, "conversa_id": conversa_id, "msg_id": msg_id}


# ============================================================
# ÁUDIO TTS (Grok)
# ============================================================

def gerar_script_audio(lead: dict) -> str:
    """Gera script de áudio personalizado para o lead (~30s)."""
    pers = personalizar_abordagem(lead)
    nome_dono = pers.get("nome_dono") or "proprietário"
    nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante"
    rating = lead.get("rating") or 0
    reviews = lead.get("total_reviews") or 0

    if rating > 0 and reviews > 0:
        script = (
            f"Oi {nome_dono}, tudo bem? Aqui é da Derekh Food. "
            f"Vi que o {nome_rest} tem uma nota de {rating} estrelas "
            f"com {reviews} avaliações no Google, parabéns pelo trabalho! "
            f"O que falta é um delivery próprio, sem pagar comissão pro iFood. "
            f"A Derekh cria seu delivery por WhatsApp em 48 horas. "
            f"Posso te mostrar como funciona?"
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
# PROCESSAR RESPOSTAS (IA)
# ============================================================

# Palavras-chave de opt-out
_OPT_OUT_KEYWORDS = {"sair", "parar", "para", "cancelar", "não quero", "nao quero",
                      "remover", "desinscrever", "stop", "sai"}
_RECUSA_KEYWORDS = {"não", "nao", "sem interesse", "não preciso", "nao preciso",
                     "já tenho", "ja tenho"}
_INTERESSE_KEYWORDS = {"como funciona", "quanto custa", "me interessa", "quero saber",
                        "pode me", "falar mais", "demo", "teste", "ver"}


def detectar_intencao(mensagem: str) -> str:
    """Detecta intenção da mensagem por keywords.
    Retorna: opt_out|recusa|interesse|duvida|outro"""
    msg = mensagem.lower().strip()

    for kw in _OPT_OUT_KEYWORDS:
        if kw in msg:
            return "opt_out"

    for kw in _RECUSA_KEYWORDS:
        if kw in msg:
            return "recusa"

    for kw in _INTERESSE_KEYWORDS:
        if kw in msg:
            return "interesse"

    if "?" in msg:
        return "duvida"

    return "outro"


def responder_com_ia(conversa_id: int, mensagem_lead: str) -> dict:
    """Usa Grok IA para gerar resposta contextualizada."""
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return {"erro": "Conversa não encontrada"}

    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}

    if httpx is None:
        return {"erro": "httpx não instalado"}

    # Contexto do lead
    nome_rest = conversa.get("nome_fantasia") or conversa.get("razao_social") or "restaurante"
    rating = conversa.get("rating") or 0
    reviews = conversa.get("total_reviews") or 0

    # Histórico
    historico = []
    for msg in (conversa.get("mensagens") or [])[-10:]:
        role = "assistant" if msg["direcao"] == "enviada" else "user"
        historico.append({"role": role, "content": msg["conteudo"] or ""})

    historico.append({"role": "user", "content": mensagem_lead})

    system_prompt = f"""Você é um vendedor da Derekh Food, uma plataforma de delivery por WhatsApp para restaurantes.
Dados do restaurante: {nome_rest}, rating {rating}, {reviews} avaliações.

Benefícios do Derekh Food:
- Delivery próprio por WhatsApp, sem comissão (iFood cobra 27%)
- Atendimento automático por IA
- Setup em 48h
- Plano a partir de R$50/mês
- Pagamento PIX direto pro restaurante

Regras:
- Seja natural, informal e breve (max 3 parágrafos)
- Use dados reais do restaurante quando possível
- Se o lead pedir demo, ofereça agendar
- Se disser que não quer, respeite e se despeça educadamente
- Nunca invente dados. Se não sabe, diga que vai verificar
- Responda em português brasileiro"""

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-fast",
                "messages": [{"role": "system", "content": system_prompt}] + historico,
                "max_tokens": 300,
                "temperature": 0.7,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        resposta = data["choices"][0]["message"]["content"]
    except Exception as e:
        log.error(f"Erro Grok IA: {e}")
        return {"erro": f"Falha na IA: {e}"}

    # Registrar resposta
    registrar_msg_wa(conversa_id, "enviada", resposta, grok=True)

    return {"sucesso": True, "resposta": resposta}


def processar_resposta_wa(numero_remetente: str, mensagem: str) -> dict:
    """Processa mensagem recebida — de lead existente OU contato novo.
    Se não existir conversa, cria lead inbound + conversa e responde."""
    numero = _limpar_telefone(numero_remetente)

    # Buscar conversa ativa pelo número
    from crm.database import get_conn, criar_lead_inbound, criar_conversa_wa as _criar_conv
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.lead_id, c.status FROM wa_conversas c
            WHERE c.numero_envio = %s AND c.status = 'ativo'
            ORDER BY c.created_at DESC LIMIT 1
        """, (numero,))
        row = cur.fetchone()

    if not row:
        # --- NOVO: criar lead inbound + conversa + responder ---
        log.info(f"Novo contato inbound: {numero} — criando lead e conversa")
        lead_id = criar_lead_inbound(numero)
        conversa_id = _criar_conv(lead_id, numero, "consultivo")
        registrar_msg_wa(conversa_id, "recebida", mensagem, intencao="interesse")
        registrar_interacao(lead_id, "whatsapp", "whatsapp",
                            f"WA inbound: {mensagem[:100]}", "positivo")

        # Responder com IA (prompt de boas-vindas)
        resultado_ia = _responder_inbound(conversa_id, mensagem)
        if resultado_ia.get("sucesso"):
            _enviar_direto(numero, resultado_ia["resposta"])
            registrar_msg_wa(conversa_id, "enviada", resultado_ia["resposta"], grok=True)
            log.info(f"Resposta inbound enviada para {numero}")

        return {"processado": True, "inbound": True, "lead_id": lead_id}

    conversa_id = row["id"]
    lead_id = row["lead_id"]

    # Detectar intenção
    intencao = detectar_intencao(mensagem)

    # Registrar mensagem recebida
    registrar_msg_wa(conversa_id, "recebida", mensagem, intencao=intencao)
    registrar_interacao(lead_id, "whatsapp", "whatsapp",
                        f"WA recebido: {mensagem[:100]}", "positivo")

    log.info(f"Resposta do lead {lead_id}: intenção={intencao}")

    if intencao == "opt_out":
        opt_out_lead(lead_id, "wa")
        atualizar_conversa_wa(conversa_id, status="opt_out", intencao_detectada="opt_out")
        enviar_mensagem_wa(lead_id, "Entendido! Você foi removido da nossa lista. Desculpe o incômodo.")
        return {"processado": True, "intencao": "opt_out", "lead_id": lead_id}

    if intencao == "recusa":
        atualizar_conversa_wa(conversa_id, intencao_detectada="recusa")
        enviar_mensagem_wa(lead_id, "Sem problemas! Se mudar de ideia, estamos aqui. Sucesso!")
        atualizar_conversa_wa(conversa_id, status="encerrado")
        return {"processado": True, "intencao": "recusa", "lead_id": lead_id}

    # Interesse ou dúvida → IA responde
    atualizar_conversa_wa(conversa_id, intencao_detectada=intencao)
    resultado_ia = responder_com_ia(conversa_id, mensagem)

    if resultado_ia.get("sucesso"):
        # Enviar resposta da IA
        enviar_mensagem_wa(lead_id, resultado_ia["resposta"])

        # Avaliar handoff
        handoff, motivo = avaliar_handoff(conversa_id)
        if handoff:
            atualizar_conversa_wa(conversa_id, status="handoff",
                                  handoff_motivo=motivo)
            log.info(f"HANDOFF lead {lead_id}: {motivo}")

    return {"processado": True, "intencao": intencao, "lead_id": lead_id}


def _enviar_direto(numero: str, texto: str) -> dict:
    """Envia mensagem direta para um número (sem precisar de lead_id)."""
    phone_id, token = _get_wa_config()
    if not phone_id or not token:
        log.error("WhatsApp Cloud API não configurada")
        return {"erro": "WhatsApp não configurado"}
    try:
        resp = httpx.post(
            f"{_GRAPH_API}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"messaging_product": "whatsapp", "to": numero,
                  "type": "text", "text": {"body": texto}},
            timeout=15,
        )
        resp.raise_for_status()
        log.info(f"Mensagem direta enviada para {numero}")
        return {"sucesso": True}
    except Exception as e:
        log.error(f"Erro envio direto {numero}: {e}")
        return {"erro": str(e)}


def _responder_inbound(conversa_id: int, mensagem: str) -> dict:
    """Responde primeira mensagem de contato inbound (alguém do site/landing)."""
    xai_key = _get_xai_key()
    if not xai_key:
        return {"erro": "XAI_API_KEY não configurada"}
    if httpx is None:
        return {"erro": "httpx não instalado"}

    system_prompt = """Você é a atendente virtual da Derekh Food, uma plataforma de delivery por WhatsApp para restaurantes.

Alguém entrou em contato pelo WhatsApp — pode ser um dono de restaurante interessado em contratar, ou alguém com dúvida.

Seu objetivo:
- Cumprimentar de forma calorosa e profissional
- Entender o que a pessoa precisa
- Se for dono de restaurante: apresentar os benefícios do Derekh Food
- Se tiver dúvida: responder de forma clara e objetiva
- Se quiser contratar: coletar nome do restaurante, cidade e tipo de comida

Benefícios do Derekh Food:
- Delivery próprio por WhatsApp, sem comissão (iFood cobra 27%)
- Atendimento automático por IA 24h
- Setup em 48h
- Plano a partir de R$50/mês
- Pagamento PIX direto pro restaurante
- Cardápio digital, KDS para cozinha, app para garçom
- Sem fidelidade, cancela quando quiser

Regras:
- Seja natural, simpático e breve (max 2 parágrafos)
- Use emojis com moderação (1-2 por mensagem)
- Responda em português brasileiro
- Nunca invente dados. Se não sabe, diga que vai verificar com a equipe
- Se a pessoa pedir para falar com humano, diga que vai transferir"""

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
                "max_tokens": 250,
                "temperature": 0.7,
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


def avaliar_handoff(conversa_id: int) -> tuple:
    """Avalia se deve fazer handoff para humano.
    Retorna (bool, motivo)."""
    conversa = obter_conversa_wa(conversa_id)
    if not conversa:
        return False, ""

    msgs_recebidas = conversa.get("msgs_recebidas", 0)
    intencao = conversa.get("intencao_detectada", "")
    score = conversa.get("lead_score", 0)

    # Lead pediu demo
    for msg in (conversa.get("mensagens") or []):
        if msg["direcao"] == "recebida":
            txt = (msg.get("conteudo") or "").lower()
            if any(w in txt for w in ("demo", "agendar", "reunião", "reuniao", "amanhã", "amanha", "horário", "horario")):
                return True, "Lead pediu demo/reunião"

    # 3+ respostas com interesse
    if msgs_recebidas >= 3 and intencao == "interesse":
        return True, "Lead engajado (3+ respostas de interesse)"

    # Score muito alto
    if score >= 85 and msgs_recebidas >= 1:
        return True, f"Lead HOT (score={score}) respondeu"

    return False, ""
