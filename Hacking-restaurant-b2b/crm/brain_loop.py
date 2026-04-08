"""
brain_loop.py — Orquestrador central do CRM Derekh Food.
Roda como background task a cada 10 minutos.

Fluxo do Brain Loop:
1. VALIDAR CONTATOS — Leads sem contato_validado_at → verificar WA + classificar email
2. ORQUESTRAR POR CANAL — Leads validados sem outreach → WA proativo ou email competitivo
3. MONITORAR CONVERSAS — Conversas WA com score alto → handoff para dono
4. FOLLOW-UP HANDOFF — Conversas em handoff sem resposta → sequência D+1/D+3/D+7
5. REENGAJAMENTO — Leads frios com potencial → nova abordagem
6. DESISTÊNCIA — Leads com 5+ tentativas sem resposta → frio_permanente
7. SCORE DECAY — Decaimento diário de scores inativos
8. MÉTRICAS — Logar stats de cada ciclo

O Brain Loop é o "cérebro" que conecta validação, outreach WA, email e handoff
de forma autônoma. Substitui a necessidade de orquestração manual.
"""

import asyncio
import logging
import random
import time

log = logging.getLogger("brain_loop")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[BRAIN-LOOP] %(message)s"))
    log.addHandler(_h)

# Limites por ciclo (guardrails anti-spam)
MAX_VALIDACOES_CICLO = 50
MAX_OUTREACH_CICLO = 20
MAX_REENGAJAMENTO_CICLO = 10
DELAY_ENTRE_WA_VERIFICACOES = 1.0  # segundos entre verificações WA
DELAY_ENTRE_OUTREACH = 2.0  # segundos entre ações de outreach
SCORE_HANDOFF_IMEDIATO = 80
SCORE_HANDOFF_QUENTE = 50
MAX_TENTATIVAS_DESISTENCIA = 5

# Controle decay (1x por dia)
_ultimo_decay_dia = None

# Controle alerta Evolution desconectada
_evolution_alerta_enviado_at = None  # timestamp do último alerta


async def ciclo_brain() -> dict:
    """Ciclo principal do Brain Loop. Chamado a cada 10 minutos.
    Retorna stats de operações executadas."""
    stats = {
        "validados": 0, "wa_encontrados": 0,
        "wa_iniciados": 0, "emails_enviados": 0,
        "handoffs": 0, "followups_handoff": 0,
        "reengajados": 0, "desistidos": 0,
        "decay_aplicado": 0, "erros": 0,
    }

    # Etapa 0: Health check Evolution API (verificação WA depende disto)
    try:
        result = await asyncio.to_thread(_etapa_evolution_health_check)
        stats["evolution_ok"] = result.get("alguma_online", False)
    except Exception as e:
        log.error(f"Etapa 0 (evolution health) falhou: {e}")

    # Etapa 1: Validar contatos pendentes
    try:
        result = await _etapa_validar_contatos(limite=MAX_VALIDACOES_CICLO)
        stats["validados"] = result.get("validados", 0)
        stats["wa_encontrados"] = result.get("wa_encontrados", 0)
    except Exception as e:
        log.error(f"Etapa 1 (validação) falhou: {e}")
        stats["erros"] += 1

    # Etapa 2: Orquestrar leads validados sem outreach
    try:
        result = await _etapa_orquestrar_leads(limite=MAX_OUTREACH_CICLO)
        stats["wa_iniciados"] = result.get("wa_iniciados", 0)
        stats["emails_enviados"] = result.get("emails_enviados", 0)
    except Exception as e:
        log.error(f"Etapa 2 (orquestração) falhou: {e}")
        stats["erros"] += 1

    # Etapa 3: Monitorar conversas WA ativas → handoff
    try:
        result = await _etapa_monitorar_handoff()
        stats["handoffs"] = result.get("handoffs", 0)
    except Exception as e:
        log.error(f"Etapa 3 (handoff) falhou: {e}")
        stats["erros"] += 1

    # Etapa 4: Follow-up pós-handoff automático (P2)
    try:
        result = await _etapa_followup_handoff()
        stats["followups_handoff"] = result.get("enviados", 0)
    except Exception as e:
        log.error(f"Etapa 4 (followup handoff) falhou: {e}")
        stats["erros"] += 1

    # Etapa 5: Reengajamento de leads frios (P3)
    try:
        result = await _etapa_reengajamento()
        stats["reengajados"] = result.get("reengajados", 0)
    except Exception as e:
        log.error(f"Etapa 5 (reengajamento) falhou: {e}")
        stats["erros"] += 1

    # Etapa 5.5: Retomar conversas sem resposta (leads no vácuo)
    try:
        result = await asyncio.to_thread(_etapa_retomar_conversas)
        stats["retomadas"] = result.get("retomadas", 0)
    except Exception as e:
        log.error(f"Etapa 5.5 (retomar conversas) falhou: {e}")
        stats["erros"] += 1

    # Etapa 5.6: Recontato agendado (conversas aguardando_horario)
    try:
        result = await asyncio.to_thread(_etapa_recontato_agendado)
        stats["recontatos"] = result.get("recontatos", 0)
    except Exception as e:
        log.error(f"Etapa 5.6 (recontato agendado) falhou: {e}")
        stats["erros"] += 1

    # Etapa 5.7: Follow-up outbound (conversas sem resposta do lead)
    try:
        result = await asyncio.to_thread(_etapa_followup_outbound)
        stats["followups_outbound"] = result.get("followups", 0)
    except Exception as e:
        log.error(f"Etapa 5.7 (followup outbound) falhou: {e}")
        stats["erros"] += 1

    # Etapa 6: Desistência de leads sem resposta (P3)
    try:
        result = await asyncio.to_thread(_etapa_desistencia)
        stats["desistidos"] = result.get("desistidos", 0)
    except Exception as e:
        log.error(f"Etapa 6 (desistência) falhou: {e}")
        stats["erros"] += 1

    # Etapa 7: Score decay diário (P4) — 1x por dia
    try:
        result = await asyncio.to_thread(_etapa_score_decay)
        stats["decay_aplicado"] = result.get("decaidos", 0)
    except Exception as e:
        log.error(f"Etapa 7 (score decay) falhou: {e}")
        stats["erros"] += 1

    # Etapa 8: Limpar filas outreach expiradas (>7 dias pendente)
    try:
        from crm.database import limpar_outreach_fila_expirados
        expirados = await asyncio.to_thread(limpar_outreach_fila_expirados, 7)
        if expirados > 0:
            log.info(f"Fila WA outreach: {expirados} itens expirados limpos")
    except Exception:
        pass

    try:
        from crm.database import limpar_email_fila_expirados
        expirados_email = await asyncio.to_thread(limpar_email_fila_expirados, 7)
        if expirados_email > 0:
            log.info(f"Fila Email outreach: {expirados_email} itens expirados limpos")
    except Exception:
        pass

    return stats


# ============================================================
# ETAPA 0: HEALTH CHECK EVOLUTION API
# ============================================================

def _etapa_evolution_health_check() -> dict:
    """Verifica se pelo menos uma instância Evolution está conectada.
    Se TODAS estão desconectadas, envia alerta Telegram para reconectar.
    Re-alerta a cada 1 hora se não reconectado."""
    global _evolution_alerta_enviado_at
    from crm.contact_validator import verificar_evolution_health, EVOLUTION_INSTANCES
    from crm.wa_sales_bot import _enviar_telegram

    health = verificar_evolution_health()
    online = [inst for inst, state in health.items() if state == "open"]
    offline = [inst for inst, state in health.items() if state != "open"]

    result = {"alguma_online": len(online) > 0, "online": online, "offline": offline}

    if online:
        # Pelo menos uma instância OK — resetar alerta
        if _evolution_alerta_enviado_at is not None:
            log.info(f"Evolution reconectada: {online}. Alerta cancelado.")
            _evolution_alerta_enviado_at = None
        if offline:
            log.info(f"Evolution parcial: {online} online, {offline} offline")
        return result

    # TODAS offline — enviar alerta Telegram
    agora = time.time()
    intervalo_realerta = 3600  # 1 hora

    deve_alertar = (
        _evolution_alerta_enviado_at is None
        or (agora - _evolution_alerta_enviado_at) >= intervalo_realerta
    )

    if deve_alertar:
        status_txt = "\n".join(f"  • {inst}: {state}" for inst, state in health.items())
        texto = (
            "⚠️ EVOLUTION API — TODAS DESCONECTADAS\n\n"
            f"Nenhuma instância Evolution está online.\n"
            f"A verificação de WhatsApp está PARADA.\n\n"
            f"Status:\n{status_txt}\n\n"
            f"🔧 Reconecte pelo menos uma:\n"
            f"https://derekh-evolution.fly.dev/manager\n\n"
            f"Se não reconectar em 1h, vou alertar novamente."
        )
        _enviar_telegram(texto)
        _evolution_alerta_enviado_at = agora
        log.warning(f"Evolution TODAS offline — alerta Telegram enviado. Status: {health}")
    else:
        minutos_restantes = int((intervalo_realerta - (agora - _evolution_alerta_enviado_at)) / 60)
        log.warning(f"Evolution TODAS offline — próximo alerta em ~{minutos_restantes}min")

    return result


# ============================================================
# ETAPA 1: VALIDAR CONTATOS PENDENTES
# ============================================================

async def _etapa_validar_contatos(limite: int) -> dict:
    """Valida WA + email de leads sem contato_validado_at.
    Usa versão async da verificação WA."""
    from crm.database import leads_pendentes_validacao
    from crm.contact_validator import validar_contatos_lead_async

    result = {"validados": 0, "wa_encontrados": 0, "erros": 0}

    leads = await asyncio.to_thread(leads_pendentes_validacao, limite)
    if not leads:
        return result

    log.info(f"Validando {len(leads)} leads pendentes...")

    for lead in leads:
        try:
            validacao = await validar_contatos_lead_async(lead["id"])
            if validacao.get("erro"):
                result["erros"] += 1
                continue

            result["validados"] += 1
            if validacao.get("wa_existe"):
                result["wa_encontrados"] += 1

            # Delay entre verificações WA
            await asyncio.sleep(DELAY_ENTRE_WA_VERIFICACOES)

        except Exception as e:
            log.warning(f"Erro validando lead {lead['id']}: {e}")
            result["erros"] += 1

    log.info(f"Validação: {result['validados']} validados, {result['wa_encontrados']} com WA")
    return result


# ============================================================
# ETAPA 2: ORQUESTRAR OUTREACH POR CANAL
# ============================================================

async def _etapa_orquestrar_leads(limite: int) -> dict:
    """Orquestra outreach para leads validados sem ações.
    - Lead com WA → iniciar conversa Ana (outbound proativo)
    - Lead sem WA mas com email → criar sequência email (outreach_engine)
    """
    from crm.database import leads_novos_sem_outreach_v2

    result = {"wa_iniciados": 0, "emails_enviados": 0, "erros": 0}

    leads = await asyncio.to_thread(leads_novos_sem_outreach_v2, limite)
    if not leads:
        return result

    log.info(f"Orquestrando {len(leads)} leads sem outreach...")

    for lead in leads:
        try:
            wa_existe = lead.get("wa_existe")
            tem_email = bool(lead.get("email") and lead["email"].strip())
            tem_telefone = bool(
                (lead.get("telefone1") and lead["telefone1"].strip())
                or (lead.get("telefone_proprietario") and lead["telefone_proprietario"].strip())
            )

            if wa_existe is True:
                # Canal WA disponível → iniciar conversa Ana
                sucesso = await _iniciar_wa_outbound(lead)
                if sucesso:
                    result["wa_iniciados"] += 1
                    await asyncio.sleep(DELAY_ENTRE_OUTREACH)

            elif tem_email:
                # Sem WA confirmado mas tem email → sequência email via outreach_engine
                sucesso = await _criar_sequencia_email(lead)
                if sucesso:
                    result["emails_enviados"] += 1

            elif tem_telefone and not lead.get("wa_verificado"):
                # Tem telefone não verificado → será pego na próxima etapa de validação
                pass

        except Exception as e:
            log.warning(f"Erro orquestrando lead {lead['id']}: {e}")
            result["erros"] += 1

    log.info(f"Orquestração: {result['wa_iniciados']} WA enfileirados, {result['emails_enviados']} emails")
    return result


async def _iniciar_wa_outbound(lead: dict) -> bool:
    """Gera mensagem WA personalizada e enfileira para envio manual pelo dono.
    NÃO envia diretamente — Meta cobra por mensagem outbound (Template Messages).
    O dono vê as mensagens pendentes em /wa-outreach-auto e envia via wa.me link.
    Retorna True se enfileirou com sucesso."""
    from crm.wa_outreach_manual import gerar_mensagem_outreach_manual
    from crm.database import inserir_outreach_fila

    try:
        result = await asyncio.to_thread(gerar_mensagem_outreach_manual, lead["id"])
        if result.get("erro"):
            if "sem telefone" in str(result["erro"]).lower():
                return False
            log.warning(f"WA outreach fila lead {lead['id']} falhou: {result['erro']}")
            return False

        fila_id = await asyncio.to_thread(
            inserir_outreach_fila,
            lead_id=lead["id"],
            mensagem=result["mensagem"],
            wa_enviar_link=result["wa_enviar_link"],
            wa_ana_link=result.get("wa_ana_link", ""),
            nome_lead=result.get("nome", ""),
            cidade=result.get("cidade", ""),
            uf=result.get("uf", ""),
            telefone=result.get("telefone", ""),
            tem_ifood=result.get("tem_ifood", False),
            lead_score=lead.get("lead_score", 0),
            gerado_por="brain_loop",
        )
        if fila_id:
            log.info(f"WA outreach ENFILEIRADO lead {lead['id']} ({lead.get('nome_fantasia', '?')}) → fila #{fila_id}")
            return True
        else:
            # Já existe pendente para este lead
            return False
    except Exception as e:
        log.warning(f"Erro WA outreach fila lead {lead['id']}: {e}")
        return False


async def _criar_sequencia_email(lead: dict) -> bool:
    """Cria sequência de outreach via email usando regras configuradas.
    Retorna True se criou ações. Roda em thread para não bloquear event loop."""
    from crm.outreach_engine import criar_sequencia_com_regras

    try:
        acoes = await asyncio.to_thread(criar_sequencia_com_regras, lead["id"], lead)
        return len(acoes) > 0
    except Exception as e:
        log.warning(f"Erro criando sequência email lead {lead['id']}: {e}")
        return False


# ============================================================
# ETAPA 3: MONITORAR CONVERSAS → HANDOFF
# ============================================================

async def _etapa_monitorar_handoff() -> dict:
    """Verifica conversas WA ativas com score alto → notificar dono.
    Score >= 80: handoff imediato
    Score >= 50: notificação quente

    GUARD ANTI-DUPLICATA (obrigatório por regra de negócio):
    - Só notifica se NUNCA foi notificado antes (handoff_notificado_em IS NULL)
    - OU se score aumentou DRASTICAMENTE (+15 pontos) desde última notificação
    - OU se tipo escalou (quente → imediato)
    """
    from crm.database import conversas_wa_quentes

    result = {"handoffs": 0, "notificacoes": 0, "suprimidos": 0}

    # Delta mínimo de score para re-notificar (aumento drástico)
    SCORE_DELTA_REFIRE = 15

    def _deve_notificar(conv: dict, tipo_atual: str) -> bool:
        """Retorna True se a notificação deve ser enviada."""
        notificado_em = conv.get("handoff_notificado_em")
        # Nunca notificado → enviar
        if not notificado_em:
            return True

        score_atual = conv.get("intent_score", 0) or 0
        score_anterior = conv.get("handoff_notificado_score", 0) or 0
        tipo_anterior = conv.get("handoff_notificado_tipo") or ""

        # Escalou de "quente" → "imediato" → re-notificar (mudança de urgência)
        if tipo_anterior == "quente" and tipo_atual == "imediato":
            return True

        # Score subiu drasticamente (+15) → re-notificar
        if (score_atual - score_anterior) >= SCORE_DELTA_REFIRE:
            return True

        # Caso contrário, suprimir (lead já notificado, sem mudança drástica)
        return False

    # Handoff imediato (score >= 80)
    conversas_hot = await asyncio.to_thread(conversas_wa_quentes, SCORE_HANDOFF_IMEDIATO)
    for conv in conversas_hot:
        try:
            if not _deve_notificar(conv, "imediato"):
                result["suprimidos"] += 1
                continue
            await asyncio.to_thread(_notificar_dono_handoff, conv, "imediato")
            result["handoffs"] += 1
        except Exception as e:
            log.warning(f"Erro handoff conversa {conv['id']}: {e}")

    # Notificação quente (score >= 50, < 80)
    conversas_warm = await asyncio.to_thread(conversas_wa_quentes, SCORE_HANDOFF_QUENTE)
    for conv in conversas_warm:
        if conv.get("intent_score", 0) < SCORE_HANDOFF_IMEDIATO:
            try:
                if not _deve_notificar(conv, "quente"):
                    result["suprimidos"] += 1
                    continue
                await asyncio.to_thread(_notificar_dono_handoff, conv, "quente")
                result["notificacoes"] += 1
            except Exception:
                pass

    if result["handoffs"] > 0 or result["notificacoes"] > 0 or result["suprimidos"] > 0:
        log.info(f"Handoff: {result['handoffs']} imediatos, "
                 f"{result['notificacoes']} quentes, "
                 f"{result['suprimidos']} suprimidos (já notificados)")

    return result


def _notificar_dono_handoff(conversa: dict, urgencia: str = "quente"):
    """Notifica o dono via Telegram sobre lead quente/hot.
    Marca conversa como notificada (handoff_notificado_em/score/tipo) após envio
    para evitar notificações duplicadas em ciclos subsequentes do brain_loop.
    """
    from datetime import datetime as _dt
    from crm.database import atualizar_conversa_wa
    from crm.wa_sales_bot import _enviar_telegram, _build_wa_chat_link

    nome_rest = conversa.get("nome_fantasia") or conversa.get("razao_social") or "Restaurante"
    cidade = conversa.get("cidade") or ""
    score = conversa.get("intent_score", 0) or 0
    intencao = conversa.get("intencao_detectada") or "interesse"
    numero_lead = conversa.get("numero_envio") or ""
    conversa_id = conversa.get("id")

    if urgencia == "imediato":
        emoji = "🔥"
        titulo = "LEAD HOT — HANDOFF IMEDIATO"
    else:
        emoji = "🟡"
        titulo = "LEAD QUENTE — Atenção"

    # Link wa.me clicável — dono abre conversa direto com o lead
    prefill = "Oi! Sou o Klenilton da Derekh Food. Vi que você tem interesse e quero te ajudar pessoalmente."
    wa_link = _build_wa_chat_link(numero_lead, prefill)

    linhas = [
        f"{emoji} {titulo}",
        f"",
        f"*{nome_rest}*" + (f" ({cidade})" if cidade else ""),
        f"Score: {score}/100 | Intenção: {intencao}",
        f"Número: {numero_lead}",
        f"Lead ID: {conversa.get('lead_id')}",
        f"",
        f"{'Esse lead precisa de atenção AGORA!' if urgencia == 'imediato' else 'Considere entrar em contato.'}",
    ]
    if wa_link:
        linhas.append("")
        linhas.append("👉 Clique para falar direto com o lead:")
        linhas.append(wa_link)

    texto = "\n".join(linhas)

    resultado = _enviar_telegram(texto)
    # Só marca como notificado se o envio foi bem sucedido (evita marcar em caso de falha)
    if resultado.get("sucesso") and conversa_id:
        try:
            atualizar_conversa_wa(
                conversa_id,
                handoff_notificado_em=_dt.now(),
                handoff_notificado_score=score,
                handoff_notificado_tipo=urgencia,
            )
        except Exception as e:
            log.warning(f"Falha ao marcar handoff_notificado conversa {conversa_id}: {e}")


# ============================================================
# ETAPA 4: FOLLOW-UP PÓS-HANDOFF AUTOMÁTICO (P2)
# ============================================================

async def _etapa_followup_handoff() -> dict:
    """Follow-up automático para conversas em handoff sem resposta do humano.
    D+1: mensagem de acompanhamento
    D+3: lembrete com link trial
    D+7: última chance com cupom"""
    from crm.database import conversas_handoff_sem_resposta, registrar_followup_handoff
    from crm.wa_sales_bot import _enviar_direto

    result = {"enviados": 0, "erros": 0}

    conversas = await asyncio.to_thread(conversas_handoff_sem_resposta, 24)
    if not conversas:
        return result

    log.info(f"Follow-up handoff: {len(conversas)} conversas pendentes")

    for conv in conversas:
        try:
            etapa_atual = conv.get("followup_handoff_etapa") or 0
            numero = conv.get("numero_envio")
            nome = conv.get("nome_fantasia") or conv.get("razao_social") or "amigo"
            lead_id = conv.get("lead_id")
            conversa_id = conv["id"]

            if not numero:
                continue

            # Calcular horas desde handoff
            handoff_at = conv.get("handoff_at")
            if not handoff_at:
                continue

            from datetime import datetime, timezone
            agora = datetime.now(timezone.utc)
            if handoff_at.tzinfo is None:
                from datetime import timezone as tz
                handoff_at = handoff_at.replace(tzinfo=tz.utc)
            horas_desde = (agora - handoff_at).total_seconds() / 3600

            texto = None
            nova_etapa = etapa_atual

            if etapa_atual == 0 and horas_desde >= 24:
                # D+1: acompanhamento
                texto = (
                    f"Oi {nome}! Nosso time já viu sua mensagem e vamos te retornar em breve. "
                    f"Qualquer dúvida é só chamar aqui! 😊"
                )
                nova_etapa = 1

            elif etapa_atual == 1 and horas_desde >= 72:
                # D+3: lembrete com link trial
                link = f"https://derekhfood.com.br/onboarding?ref={lead_id}&utm_source=followup_handoff"
                texto = (
                    f"Oi {nome}! Não esquecemos de você! "
                    f"Enquanto isso, já pode testar o sistema grátis por 15 dias:\n\n"
                    f"{link}\n\n"
                    f"Sem compromisso, sem cartão. Depois a gente conversa! 😉"
                )
                nova_etapa = 2

                # Marcar trial link enviado
                from crm.database import marcar_trial_link_enviado
                marcar_trial_link_enviado(lead_id)

            elif etapa_atual == 2 and horas_desde >= 168:
                # D+7: última chance com cupom
                texto = (
                    f"Oi {nome}! 🎁 Última chance: cupom *DESCONTO20* com 20% OFF no primeiro mês "
                    f"se ativar até sexta!\n\n"
                    f"https://derekhfood.com.br/onboarding?ref={lead_id}&utm_source=followup_cupom\n\n"
                    f"Qualquer dúvida estamos aqui! 💚"
                )
                nova_etapa = 3

            if texto:
                await asyncio.to_thread(_enviar_direto, numero, texto)
                await asyncio.to_thread(registrar_followup_handoff, conversa_id, nova_etapa)
                result["enviados"] += 1
                await asyncio.sleep(DELAY_ENTRE_OUTREACH)

        except Exception as e:
            log.warning(f"Erro followup handoff conversa {conv.get('id')}: {e}")
            result["erros"] += 1

    if result["enviados"] > 0:
        log.info(f"Follow-up handoff: {result['enviados']} enviados")

    return result


# ============================================================
# ETAPA 5: REENGAJAMENTO DE LEADS FRIOS (P3)
# ============================================================

async def _etapa_reengajamento() -> dict:
    """Reengaja leads frios com potencial (score > 40, sem contato há 30+ dias).
    Usa pattern_library para variar mensagens. Max 10 por ciclo."""
    from crm.database import leads_para_reengajamento, marcar_reengajamento, registrar_interacao

    result = {"reengajados": 0, "erros": 0}

    leads = await asyncio.to_thread(leads_para_reengajamento, MAX_REENGAJAMENTO_CICLO)
    if not leads:
        return result

    log.info(f"Reengajamento: {len(leads)} leads elegíveis")

    for lead in leads:
        try:
            lead_id = lead["id"]
            wa_existe = lead.get("wa_existe")
            tem_email = bool(lead.get("email") and lead["email"].strip())

            sucesso = False

            if wa_existe:
                # Reengajar via WA com nova abordagem
                sucesso = await _reengajar_via_wa(lead)
            elif tem_email:
                # Reengajar via email
                sucesso = _reengajar_via_email(lead)

            if sucesso:
                marcar_reengajamento(lead_id)
                registrar_interacao(lead_id, "reengajamento", "wa" if wa_existe else "email",
                                    "Reengajamento automático após 30+ dias", "enviado")
                result["reengajados"] += 1
                await asyncio.sleep(DELAY_ENTRE_OUTREACH)

        except Exception as e:
            log.warning(f"Erro reengajamento lead {lead.get('id')}: {e}")
            result["erros"] += 1

    if result["reengajados"] > 0:
        log.info(f"Reengajamento: {result['reengajados']} leads reativados")

    return result


async def _reengajar_via_wa(lead: dict) -> bool:
    """Reengaja lead via WA — enfileira mensagem personalizada para envio manual.
    Usa wa_outreach_manual para gerar msg com IA, salva na fila autônoma."""
    from crm.wa_outreach_manual import gerar_mensagem_outreach_manual
    from crm.database import inserir_outreach_fila

    try:
        result = await asyncio.to_thread(gerar_mensagem_outreach_manual, lead["id"])
        if result.get("erro"):
            return False

        fila_id = await asyncio.to_thread(
            inserir_outreach_fila,
            lead_id=lead["id"],
            mensagem=result["mensagem"],
            wa_enviar_link=result["wa_enviar_link"],
            wa_ana_link=result.get("wa_ana_link", ""),
            nome_lead=result.get("nome", ""),
            cidade=result.get("cidade", ""),
            uf=result.get("uf", ""),
            telefone=result.get("telefone", ""),
            tem_ifood=result.get("tem_ifood", False),
            lead_score=lead.get("lead_score", 0),
            gerado_por="reengajamento",
        )
        return fila_id > 0
    except Exception as e:
        log.warning(f"Erro reengajamento WA fila lead {lead.get('id')}: {e}")
        return False


def _reengajar_via_email(lead: dict) -> bool:
    """Reengaja lead via email com template 'saudade'."""
    from crm.outreach_engine import criar_sequencia_com_regras
    try:
        acoes = criar_sequencia_com_regras(lead["id"], lead)
        return len(acoes) > 0
    except Exception as e:
        log.warning(f"Erro reengajamento email lead {lead.get('id')}: {e}")
        return False


# ============================================================
# ETAPA 6: DESISTÊNCIA DE LEADS SEM RESPOSTA (P3)
# ============================================================

def _etapa_desistencia() -> dict:
    """Marca leads com 5+ tentativas sem resposta como 'frio_permanente'.
    Não deleta — pode ser reativado manualmente."""
    from crm.database import leads_para_desistencia, cancelar_outreach_lead

    result = {"desistidos": 0}

    leads = leads_para_desistencia(max_tentativas=MAX_TENTATIVAS_DESISTENCIA)
    if not leads:
        return result

    from crm.database import get_conn
    with get_conn() as conn:
        cur = conn.cursor()
        for lead in leads:
            lead_id = lead["id"]
            cur.execute("""
                UPDATE leads SET status_pipeline = 'perdido',
                                 motivo_perda = 'frio_permanente_auto'
                WHERE id = %s AND status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
            """, (lead_id,))
            if cur.rowcount > 0:
                cancelar_outreach_lead(lead_id)
                result["desistidos"] += 1

        conn.commit()

    if result["desistidos"] > 0:
        log.info(f"Desistência: {result['desistidos']} leads marcados frio_permanente")

    return result


# ============================================================
# ETAPA 5.5: RETOMAR CONVERSAS SEM RESPOSTA
# ============================================================

def _etapa_retomar_conversas() -> dict:
    """Retoma conversas onde o lead respondeu mas ficou sem resposta.
    Envia resposta preferencialmente por áudio."""
    from crm.wa_sales_bot import retomar_conversas_sem_resposta
    try:
        return retomar_conversas_sem_resposta(limite=10)
    except Exception as e:
        log.warning(f"Erro ao retomar conversas: {e}")
        return {"retomadas": 0, "erros": 1}


def _etapa_followup_outbound() -> dict:
    """Follow-up para conversas outbound sem resposta do lead.
    Envia mensagem de acompanhamento para quem não respondeu
    (pode ter respondido mas o webhook não recebeu).
    Envia preferencialmente por áudio para quebrar o gelo."""
    from crm.wa_sales_bot import followup_conversas_outbound
    try:
        return followup_conversas_outbound(limite=15)
    except Exception as e:
        log.warning(f"Erro ao fazer follow-up outbound: {e}")
        return {"followups": 0, "erros": 1}


# ============================================================
# ETAPA 5.6: RECONTATO AGENDADO (conversas aguardando_horario)
# ============================================================

def _etapa_recontato_agendado() -> dict:
    """Recontata leads cujas conversas estão em 'aguardando_horario'.
    Verifica se estamos dentro do horário comercial para recontatar."""
    from crm.database import get_conn
    from crm.wa_sales_bot import enviar_mensagem_wa, _limpar_nome_restaurante
    from datetime import datetime
    import re

    result = {"recontatos": 0}
    hora_atual = datetime.now().hour

    # Só recontatar em horário comercial (9h-18h)
    if hora_atual < 9 or hora_atual >= 18:
        return result

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id as conversa_id, c.lead_id, c.numero_envio, c.notas,
                   l.nome_fantasia, l.razao_social
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.status = 'aguardando_horario'
              AND l.opt_out_wa IS NOT TRUE
              AND l.status_pipeline NOT IN ('perdido', 'lead_falso')
            LIMIT 5
        """)
        rows = cur.fetchall()

    for row in rows:
        try:
            lead_id = row["lead_id"]
            conversa_id = row["conversa_id"]
            lead = {"nome_fantasia": row["nome_fantasia"], "razao_social": row["razao_social"]}
            nome_rest = _limpar_nome_restaurante(lead)

            # Reativar conversa
            from crm.database import atualizar_conversa_wa
            atualizar_conversa_wa(conversa_id, status="ativo")

            texto = (f"Oi! Sou a Ana da Derekh Food, entrei em contato ontem. "
                     f"Poderia falar com o responsável pelo {nome_rest}? "
                     f"Tenho algo que pode ajudar muito o negócio de vocês!")

            resultado = enviar_mensagem_wa(lead_id, texto, tom="recontato")
            if resultado.get("sucesso"):
                result["recontatos"] += 1
                log.info(f"Recontato agendado executado para lead {lead_id}")

            import time
            time.sleep(random.uniform(30, 60))

        except Exception as e:
            log.warning(f"Erro recontato lead {row.get('lead_id')}: {e}")

    return result


# ============================================================
# ETAPA 7: SCORE DECAY DIÁRIO (P4)
# ============================================================

def _etapa_score_decay() -> dict:
    """Aplica decaimento de scores 1x por dia."""
    global _ultimo_decay_dia
    from datetime import date

    hoje = date.today()
    if _ultimo_decay_dia == hoje:
        return {"decaidos": 0}  # Já rodou hoje

    from crm.scoring import aplicar_decaimento_scores
    result = aplicar_decaimento_scores()
    _ultimo_decay_dia = hoje

    return result
