# backend/app/billing/billing_tasks.py
"""
Task assíncrona periódica de billing.
Verifica trials, pagamentos vencidos, suspensões e cancelamentos.

Segue lógica do Asaas para compensação:
- Boleto: até 3 dias úteis para compensar
- Pix: instantâneo, mas sem desativação em finais de semana/feriados
- Contagem de inadimplência sempre em dias ÚTEIS (seg-sex, exceto feriados BR)
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal
from .billing_service import (
    suspender_por_inadimplencia,
    cancelar_por_inadimplencia,
    criar_recorrencia_addon,
    desativar_addon_por_inadimplencia,
    registrar_audit,
    asaas_client,
)

logger = logging.getLogger("superfood.billing")

INTERVALO_VERIFICACAO = 30 * 60  # 30 minutos
INTERVALO_POLLING_ASAAS = 6 * 60 * 60  # 6 horas
_ultimo_polling = datetime.utcnow()

# ─── Tolerância de inadimplência (em dias ÚTEIS) ──────────────────────────
ADDON_DIAS_UTEIS_TOLERANCIA = 1   # Humanoide: pausa após 1 dia útil vencido
ASSINATURA_DIAS_UTEIS_AVISO = 3   # Assinatura: aviso "será suspenso" após 3 dias úteis

# ─── Feriados nacionais brasileiros (fixos + móveis para o ano corrente) ──
def _feriados_br(ano: int) -> set:
    """Retorna set de feriados nacionais brasileiros para o ano.
    Inclui feriados fixos + Carnaval, Sexta-feira Santa, Corpus Christi (calculados via Páscoa)."""
    from datetime import date as _date

    fixos = {
        _date(ano, 1, 1),    # Confraternização Universal
        _date(ano, 4, 21),   # Tiradentes
        _date(ano, 5, 1),    # Dia do Trabalhador
        _date(ano, 9, 7),    # Independência
        _date(ano, 10, 12),  # Nossa Sra. Aparecida
        _date(ano, 11, 2),   # Finados
        _date(ano, 11, 15),  # Proclamação da República
        _date(ano, 12, 25),  # Natal
    }

    # Páscoa (algoritmo de Gauss)
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    pascoa = _date(ano, mes, dia)

    moveis = {
        pascoa - timedelta(days=47),  # Carnaval (segunda)
        pascoa - timedelta(days=48),  # Carnaval (terça — ponto facultativo mas Asaas respeita)
        pascoa - timedelta(days=2),   # Sexta-feira Santa
        pascoa + timedelta(days=60),  # Corpus Christi
    }

    return fixos | moveis


# Cache de feriados por ano
_cache_feriados: dict[int, set] = {}


def _eh_dia_util(d: date) -> bool:
    """Retorna True se o dia é útil (seg-sex e não feriado nacional BR)."""
    if d.weekday() >= 5:  # sábado=5, domingo=6
        return False
    ano = d.year
    if ano not in _cache_feriados:
        _cache_feriados[ano] = _feriados_br(ano)
    return d not in _cache_feriados[ano]


def dias_uteis_desde(data_ref: date, ate: date = None) -> int:
    """Conta quantos dias úteis se passaram de data_ref até ate (default=hoje).
    Não conta o dia de data_ref, conta o dia de ate."""
    if ate is None:
        ate = date.today()
    if ate <= data_ref:
        return 0
    count = 0
    d = data_ref + timedelta(days=1)
    while d <= ate:
        if _eh_dia_util(d):
            count += 1
        d += timedelta(days=1)
    return count


async def verificar_billing_periodico(ws_manager):
    """Task principal de billing — roda a cada 30 minutos."""
    global _ultimo_polling

    # Aguarda 60s antes da primeira execução para o app estabilizar
    await asyncio.sleep(60)

    while True:
        try:
            db = SessionLocal()
            try:
                config = db.query(models.ConfigBilling).first()
                if not config:
                    await asyncio.sleep(INTERVALO_VERIFICACAO)
                    continue

                agora = datetime.utcnow()

                # ── 1. Trials vencendo em ≤ dias_lembrete_antes ──
                await _verificar_trials_vencendo(db, config, agora, ws_manager)

                # ── 2. Trials vencidos sem plano → suspender ──
                await _verificar_trials_vencidos(db, agora)

                # ── 3. Overdue → aviso de suspensão iminente ──
                await _notificar_overdue_aviso(db, config, ws_manager)

                # ── 4. Overdue ≥ dias_suspensao → suspender ──
                await _verificar_overdue_suspensao(db, config)

                # ── 5. Suspended ≥ dias_cancelamento → cancelar ──
                await _verificar_suspended_cancelamento(db, config)

                # ── 6. Atualizar dias_vencido (1x/dia — só dias úteis) ──
                _atualizar_dias_vencido(db)

                # ── 7. Recorrência add-ons ──
                await _verificar_recorrencia_addons(db)

                # ── 7. Fallback polling Asaas (cada 6h) ──
                if (agora - _ultimo_polling).total_seconds() >= INTERVALO_POLLING_ASAAS:
                    await _polling_pagamentos_asaas(db)
                    _ultimo_polling = agora

            finally:
                db.close()
        except Exception as e:
            logger.error(f"Erro na task de billing: {e}")

        await asyncio.sleep(INTERVALO_VERIFICACAO)


async def _verificar_trials_vencendo(db: Session, config: models.ConfigBilling, agora: datetime, ws_manager):
    """Notifica restaurantes com trial prestes a vencer."""
    limite = agora + timedelta(days=config.dias_lembrete_antes)

    trials_vencendo = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "trial",
        models.Restaurante.trial_fim != None,
        models.Restaurante.trial_fim <= limite,
        models.Restaurante.trial_fim > agora,
    ).all()

    for rest in trials_vencendo:
        dias_restantes = max(0, (rest.trial_fim - agora).days)

        # Verificar se já notificou hoje
        hoje = agora.date()
        notificacao_existente = db.query(models.Notificacao).filter(
            models.Notificacao.restaurante_id == rest.id,
            models.Notificacao.tipo == "trial_expiring",
            models.Notificacao.data_criacao >= datetime(hoje.year, hoje.month, hoje.day),
        ).first()

        if not notificacao_existente:
            notif = models.Notificacao(
                restaurante_id=rest.id,
                tipo="trial_expiring",
                titulo="Período de teste terminando",
                mensagem=f"Seu período de teste termina em {dias_restantes} dia{'s' if dias_restantes != 1 else ''}. Escolha um plano para continuar.",
                dados_json={"dias_restantes": dias_restantes},
            )
            db.add(notif)

            # WebSocket broadcast
            try:
                await ws_manager.broadcast({
                    "tipo": "billing_alert",
                    "dados": {
                        "alert_type": "trial_expiring",
                        "dias_restantes": dias_restantes,
                    }
                }, rest.id)
            except Exception:
                pass

    db.commit()


async def _verificar_trials_vencidos(db: Session, agora: datetime):
    """Suspende restaurantes com trial vencido que não selecionaram plano."""
    trials_vencidos = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "trial",
        models.Restaurante.trial_fim != None,
        models.Restaurante.trial_fim <= agora,
    ).all()

    for rest in trials_vencidos:
        await suspender_por_inadimplencia(rest, db)
        logger.info(f"Trial vencido — restaurante {rest.id} suspenso")


async def _notificar_overdue_aviso(db: Session, config: models.ConfigBilling, ws_manager):
    """Notifica restaurantes com pagamento vencido sobre suspensão iminente.
    Envia aviso diário: 'Sua mensalidade está vencida. Sistemas serão suspensos em X dias.'"""
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "overdue",
    ).all()

    hoje = datetime.utcnow()
    hoje_date = hoje.date()

    for rest in restaurantes:
        dias_vencido = rest.dias_vencido or 0
        dias_para_suspensao = max(0, config.dias_suspensao - dias_vencido)

        # Verificar se já notificou hoje
        notificacao_existente = db.query(models.Notificacao).filter(
            models.Notificacao.restaurante_id == rest.id,
            models.Notificacao.tipo == "billing_overdue_warning",
            models.Notificacao.data_criacao >= datetime(hoje_date.year, hoje_date.month, hoje_date.day),
        ).first()

        if not notificacao_existente:
            if dias_para_suspensao <= 0:
                msg = "Sua mensalidade está vencida. Todos os sistemas serão suspensos a qualquer momento."
            elif dias_para_suspensao == 1:
                msg = "Sua mensalidade está vencida. Todos os sistemas serão suspensos amanhã se o pagamento não for confirmado."
            else:
                msg = f"Sua mensalidade está vencida há {dias_vencido} dia{'s' if dias_vencido != 1 else ''}. Todos os sistemas serão suspensos em {dias_para_suspensao} dia{'s' if dias_para_suspensao != 1 else ''} se o pagamento não for confirmado."

            notif = models.Notificacao(
                restaurante_id=rest.id,
                tipo="billing_overdue_warning",
                titulo="Mensalidade vencida",
                mensagem=msg,
                dados_json={
                    "dias_vencido": dias_vencido,
                    "dias_para_suspensao": dias_para_suspensao,
                    "severity": "critical" if dias_para_suspensao <= 1 else "warning",
                },
            )
            db.add(notif)

            # WebSocket para exibir banner em tempo real
            try:
                await ws_manager.broadcast({
                    "tipo": "billing_alert",
                    "dados": {
                        "alert_type": "overdue_warning",
                        "dias_vencido": dias_vencido,
                        "dias_para_suspensao": dias_para_suspensao,
                        "mensagem": msg,
                    }
                }, rest.id)
            except Exception:
                pass

    if restaurantes:
        db.commit()


async def _verificar_overdue_suspensao(db: Session, config: models.ConfigBilling):
    """Suspende restaurantes overdue por mais de dias_suspensao dias (úteis).
    Não suspende em finais de semana/feriados — acompanha lógica Asaas."""
    hoje = date.today()
    if not _eh_dia_util(hoje):
        return  # Não suspende em dias não úteis — espera compensação

    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "overdue",
        models.Restaurante.dias_vencido >= config.dias_suspensao,
    ).all()

    for rest in restaurantes:
        await suspender_por_inadimplencia(rest, db)


async def _verificar_suspended_cancelamento(db: Session, config: models.ConfigBilling):
    """Cancela restaurantes suspensos por mais de dias_cancelamento dias."""
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status == "suspended_billing",
        models.Restaurante.dias_vencido >= config.dias_cancelamento,
    ).all()

    for rest in restaurantes:
        await cancelar_por_inadimplencia(rest, db)


def _atualizar_dias_vencido(db: Session):
    """Incrementa dias_vencido para restaurantes overdue/suspended.
    Só incrementa em dias úteis (seg-sex, exceto feriados BR) — acompanha lógica Asaas."""
    hoje = date.today()
    if not _eh_dia_util(hoje):
        return  # Não incrementa em finais de semana/feriados

    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.billing_status.in_(["overdue", "suspended_billing"]),
    ).all()

    for rest in restaurantes:
        rest.dias_vencido = (rest.dias_vencido or 0) + 1

    if restaurantes:
        db.commit()


async def _verificar_recorrencia_addons(db: Session):
    """Cria cobranças mensais para add-ons ativos + desativa inadimplentes."""
    from datetime import date

    hoje = date.today()

    # 1. Restaurantes com add-on ativo e vencimento <= hoje → criar nova cobrança
    restaurantes = db.query(models.Restaurante).filter(
        models.Restaurante.addon_bot_whatsapp == True,
        models.Restaurante.addon_bot_proximo_vencimento != None,
        models.Restaurante.addon_bot_proximo_vencimento <= hoje,
        models.Restaurante.billing_status.in_(["active", "overdue"]),
    ).all()

    for rest in restaurantes:
        # Verificar se já existe cobrança PENDING para este ciclo
        pendente = db.query(models.AddonCobranca).filter(
            models.AddonCobranca.restaurante_id == rest.id,
            models.AddonCobranca.addon == "bot_whatsapp",
            models.AddonCobranca.status == "PENDING",
        ).first()
        if not pendente:
            try:
                await criar_recorrencia_addon(rest.id, db)
            except Exception as e:
                logger.error(f"Erro ao criar recorrência addon para restaurante {rest.id}: {e}")

    # 2. Desativar add-ons com pagamento OVERDUE há mais de ADDON_DIAS_UTEIS_TOLERANCIA dias úteis
    #    Segue lógica Asaas: não desativa em feriados/fins de semana, dá tempo para boleto compensar
    vencidos = db.query(models.AddonCobranca).filter(
        models.AddonCobranca.status == "OVERDUE",
    ).all()

    restaurantes_desativados = set()
    for cob in vencidos:
        if cob.restaurante_id in restaurantes_desativados:
            continue
        # Contar dias úteis desde o vencimento
        if cob.data_vencimento:
            data_venc = cob.data_vencimento.date() if isinstance(cob.data_vencimento, datetime) else cob.data_vencimento
            du = dias_uteis_desde(data_venc)
            if du > ADDON_DIAS_UTEIS_TOLERANCIA:
                try:
                    await desativar_addon_por_inadimplencia(cob.restaurante_id, db)
                    restaurantes_desativados.add(cob.restaurante_id)
                    logger.info(f"Addon bot desativado — restaurante {cob.restaurante_id} ({du} dias úteis vencido)")
                except Exception as e:
                    logger.error(f"Erro ao desativar addon por inadimplência (rest {cob.restaurante_id}): {e}")


async def _polling_pagamentos_asaas(db: Session):
    """Polling de fallback — consulta Asaas por pagamentos recentes não processados."""
    if not asaas_client.configured:
        return

    clientes = db.query(models.AsaasCliente).all()
    for cli in clientes:
        try:
            result = await asaas_client.listar_pagamentos(cli.asaas_customer_id, status="RECEIVED")
            pagamentos = result.get("data", [])
            for pag in pagamentos:
                asaas_id = pag.get("id", "")
                existente = db.query(models.AsaasPagamento).filter(
                    models.AsaasPagamento.asaas_payment_id == asaas_id,
                    models.AsaasPagamento.status == "RECEIVED",
                ).first()
                if not existente:
                    from .billing_service import processar_pagamento_confirmado
                    await processar_pagamento_confirmado(pag, db)
                    logger.info(f"Polling: pagamento {asaas_id} processado para restaurante {cli.restaurante_id}")
        except Exception as e:
            logger.debug(f"Polling Asaas para customer {cli.asaas_customer_id}: {e}")
