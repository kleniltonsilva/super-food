"""
outreach_engine.py - Motor de sequência automática de outreach
Importa leads, calcula tier, cria sequências, executa ações pendentes.
"""
import logging
from datetime import datetime, timedelta, timezone

from crm.database import (
    get_conn, leads_para_outreach, criar_outreach_acao,
    listar_outreach_pendentes, marcar_outreach_executado,
    emails_enviados_hoje, obter_configuracao, obter_lead,
    buscar_email_por_tracking, atualizar_tier_lead,
    obter_email_template, listar_email_templates,
)
from crm.scoring import calcular_tier, calcular_score
from crm.email_service import enviar_email
from crm.models import TIERS

log = logging.getLogger("outreach")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[OUTREACH] %(message)s"))
    log.addHandler(_h)


# ============================================================
# IMPORTAR LEADS
# ============================================================

def importar_leads_para_outreach(cidade: str = None, uf: str = None,
                                  score_min: int = 30, limite: int = 100) -> list:
    """Importa leads elegíveis para outreach, calcula tier e cria sequências.
    Retorna lista de leads importados com sequências criadas."""
    leads = leads_para_outreach(cidade, uf, score_min, limite)
    if not leads:
        log.info("Nenhum lead elegível encontrado.")
        return []

    resultados = []
    for lead in leads:
        score = lead.get("lead_score", 0)
        tier = calcular_tier(score)

        # Atualizar tier no banco
        atualizar_tier_lead(lead["id"], tier)
        lead["tier"] = tier

        # Criar sequência baseada no tier
        acoes = criar_sequencia_lead(lead["id"], tier, score)
        lead["acoes_criadas"] = len(acoes)
        resultados.append(lead)

    log.info(f"Importados {len(resultados)} leads para outreach.")
    return resultados


# ============================================================
# CRIAR SEQUÊNCIA
# ============================================================

def _escolher_template() -> int:
    """Escolhe o primeiro template ativo disponível. Retorna ID ou None."""
    templates = listar_email_templates()
    for t in templates:
        if t.get("ativo", True):
            return t["id"]
    return None


def criar_sequencia_lead(lead_id: int, tier: str, score: int) -> list:
    """Cria sequência de ações baseada no tier do lead.
    HOT (>=80): email imediato + follow-up D+2
    WARM (50-79): email D+0 + re-email D+3 + follow-up D+5
    COOL (30-49): email D+0 apenas
    COLD (<30): nenhuma ação
    Retorna lista de IDs das ações criadas."""
    if tier == "cold":
        return []

    agora = datetime.now(timezone.utc)
    template_id = _escolher_template()
    acoes_criadas = []

    if tier == "hot":
        # Email imediato
        aid = criar_outreach_acao(lead_id, "enviar_email", tier, agora, template_id)
        acoes_criadas.append(aid)
        # Follow-up D+2
        aid = criar_outreach_acao(lead_id, "followup", tier, agora + timedelta(days=2), template_id)
        acoes_criadas.append(aid)

    elif tier == "warm":
        # Email D+0
        aid = criar_outreach_acao(lead_id, "enviar_email", tier, agora, template_id)
        acoes_criadas.append(aid)
        # Re-email D+3 (se não abriu)
        aid = criar_outreach_acao(lead_id, "reenviar_email", tier, agora + timedelta(days=3), template_id)
        acoes_criadas.append(aid)
        # Follow-up D+5
        aid = criar_outreach_acao(lead_id, "followup", tier, agora + timedelta(days=5), template_id)
        acoes_criadas.append(aid)

    elif tier == "cool":
        # Apenas 1 email genérico
        aid = criar_outreach_acao(lead_id, "enviar_email", tier, agora, template_id)
        acoes_criadas.append(aid)

    log.info(f"Lead {lead_id}: tier={tier}, {len(acoes_criadas)} ações criadas.")
    return acoes_criadas


# ============================================================
# EXECUTAR AÇÕES PENDENTES
# ============================================================

def executar_acoes_pendentes() -> dict:
    """Executa ações de outreach pendentes (agendado_para <= NOW).
    Respeita guardrails: max emails/dia, opt_out.
    Retorna stats da execução."""
    stats = {
        "executadas": 0, "erros": 0,
        "pular_opt_out": 0, "pular_limite": 0,
        "pular_sem_email": 0, "pular_invalido": 0,
    }

    # Guardrail: max emails por dia
    max_email_dia = int(obter_configuracao("outreach_max_email_dia") or "20")
    enviados_hoje = emails_enviados_hoje()

    # Verificar se outreach está ativo
    outreach_ativo = (obter_configuracao("outreach_ativo") or "false").lower() == "true"
    if not outreach_ativo:
        log.info("Outreach desativado. Ative em configuracoes: outreach_ativo=true")
        return stats

    pendentes = listar_outreach_pendentes(50)
    if not pendentes:
        log.info("Nenhuma ação pendente.")
        return stats

    log.info(f"Processando {len(pendentes)} ações pendentes. Emails hoje: {enviados_hoje}/{max_email_dia}")

    for acao in pendentes:
        acao_tipo = acao["acao"]
        lead_id = acao["lead_id"]
        acao_id = acao["id"]

        # Guardrail: opt_out
        if acao.get("opt_out_email") and acao_tipo in ("enviar_email", "reenviar_email", "followup"):
            marcar_outreach_executado(acao_id, "pular_opt_out")
            stats["pular_opt_out"] += 1
            continue

        # Guardrail: sem email
        if not acao.get("email") or not acao["email"].strip():
            marcar_outreach_executado(acao_id, "erro", "Lead sem email")
            stats["pular_sem_email"] += 1
            continue

        # Guardrail: email invalido
        if acao.get("email_invalido"):
            marcar_outreach_executado(acao_id, "erro", "Email invalido")
            stats["pular_invalido"] += 1
            continue

        # Guardrail: limite diário
        if acao_tipo in ("enviar_email", "reenviar_email", "followup") and enviados_hoje >= max_email_dia:
            marcar_outreach_executado(acao_id, "pular_limite", f"Limite {max_email_dia}/dia atingido")
            stats["pular_limite"] += 1
            continue

        # Executar ação
        try:
            if acao_tipo in ("enviar_email", "followup"):
                resultado = _executar_enviar_email(acao)
                if resultado.get("sucesso"):
                    marcar_outreach_executado(acao_id, "enviado")
                    enviados_hoje += 1
                    stats["executadas"] += 1
                else:
                    marcar_outreach_executado(acao_id, "erro", resultado.get("erro", "Erro desconhecido"))
                    stats["erros"] += 1

            elif acao_tipo == "reenviar_email":
                resultado = _executar_reenviar_email(acao)
                if resultado.get("sucesso"):
                    marcar_outreach_executado(acao_id, "enviado")
                    enviados_hoje += 1
                    stats["executadas"] += 1
                elif resultado.get("pular"):
                    marcar_outreach_executado(acao_id, resultado["pular"])
                    stats["executadas"] += 1
                else:
                    marcar_outreach_executado(acao_id, "erro", resultado.get("erro", "Erro desconhecido"))
                    stats["erros"] += 1

            elif acao_tipo == "enviar_wa":
                resultado = _executar_enviar_wa(acao)
                if resultado.get("sucesso"):
                    marcar_outreach_executado(acao_id, "enviado")
                    stats["executadas"] += 1
                else:
                    marcar_outreach_executado(acao_id, "erro", resultado.get("erro", "Erro WA"))
                    stats["erros"] += 1

            elif acao_tipo == "enviar_audio":
                resultado = _executar_enviar_audio(acao)
                if resultado.get("sucesso"):
                    marcar_outreach_executado(acao_id, "enviado")
                    stats["executadas"] += 1
                else:
                    marcar_outreach_executado(acao_id, "erro", resultado.get("erro", "Erro áudio"))
                    stats["erros"] += 1

            else:
                marcar_outreach_executado(acao_id, "erro", f"Ação desconhecida: {acao_tipo}")
                stats["erros"] += 1

        except Exception as e:
            log.error(f"Erro ao executar ação {acao_id}: {e}")
            marcar_outreach_executado(acao_id, "erro", str(e)[:200])
            stats["erros"] += 1

    log.info(f"Execução concluída: {stats}")
    return stats


def _executar_enviar_email(acao: dict) -> dict:
    """Executa envio de email para uma ação de outreach."""
    lead_id = acao["lead_id"]
    template_id = acao.get("template_id")

    if not template_id:
        template_id = _escolher_template()
    if not template_id:
        return {"erro": "Nenhum template disponível"}

    resultado = enviar_email(lead_id, template_id)
    return resultado


def _executar_reenviar_email(acao: dict) -> dict:
    """Reenvia email se o lead não abriu o anterior.
    Se já abriu, pula (não reenvia)."""
    lead_id = acao["lead_id"]

    # Verificar se lead já abriu algum email recente
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT tracking_id, aberto FROM emails_enviados
            WHERE lead_id = %s
            ORDER BY horario_enviado DESC LIMIT 1
        """, (lead_id,))
        ultimo = cur.fetchone()

    if ultimo and ultimo.get("aberto"):
        # Lead já abriu → não reenviar, pular
        return {"pular": "ja_abriu"}

    # Lead não abriu → reenviar com template
    template_id = acao.get("template_id")
    if not template_id:
        template_id = _escolher_template()
    if not template_id:
        return {"erro": "Nenhum template disponível"}

    return enviar_email(lead_id, template_id)


def _executar_enviar_wa(acao: dict) -> dict:
    """Envia mensagem WhatsApp para uma ação de outreach."""
    from crm.wa_sales_bot import enviar_mensagem_wa
    from crm.scoring import personalizar_abordagem

    lead_id = acao["lead_id"]
    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    pers = personalizar_abordagem(lead)
    nome = pers.get("nome_dono") or "proprietário"
    nome_rest = lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante"

    texto = (
        f"Oi {nome}! Tudo bem?\n\n"
        f"Me chamo Klenilton da Derekh Food. "
        f"Vi que o *{nome_rest}* tem tudo para crescer com delivery próprio.\n\n"
        f"Sem comissão de 27% do iFood — seus clientes pedem direto com você.\n\n"
        f"Posso te mostrar como funciona em 5 minutos?"
    )
    return enviar_mensagem_wa(lead_id, texto)


def _executar_enviar_audio(acao: dict) -> dict:
    """Envia áudio TTS personalizado."""
    from crm.wa_sales_bot import enviar_audio_wa
    return enviar_audio_wa(acao["lead_id"])
