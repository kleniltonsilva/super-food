"""
Workers periódicos do Bot WhatsApp:
1. Detectar atrasos em pedidos e notificar cliente (a cada 5 min)
2. Enviar avaliação pós-entrega — fluxo 2 etapas (a cada 2 min)
3. Reset tokens diários (meia-noite)
4. Repescagem inteligente de clientes inativos (a cada 1h)
5. Notificação proativa de mudança de status (a cada 1 min)
"""
import asyncio
import random
import string
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from .. import models
from ..database import SessionLocal

logger = logging.getLogger("superfood.bot.workers")


async def bot_workers_loop(ws_manager):
    """Loop principal dos workers do bot. Roda em background."""
    ciclo = 0
    while True:
        try:
            await asyncio.sleep(60)  # A cada 1 minuto
            ciclo += 1

            db = SessionLocal()
            try:
                # Notificação proativa a cada 60s
                await _notificar_mudancas_status(db)

                # Avaliações e atrasos a cada 2 min (ciclo par)
                if ciclo % 2 == 0:
                    await _verificar_avaliacoes_pendentes(db)
                    await _verificar_atrasos(db, ws_manager)
                    _reset_tokens_diarios(db)

                # Repescagem + lembretes a cada 60 ciclos (1h)
                if ciclo % 60 == 0:
                    await _verificar_clientes_inativos(db)
                    await _verificar_cupons_expirando(db)
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("Bot workers encerrados")
            break
        except Exception as e:
            logger.error(f"Erro nos workers do bot: {e}")
            await asyncio.sleep(60)


# ═══════════════════════════════════════════════════════════════
# WORKER 1: Avaliação pós-entrega — Fluxo 2 etapas
# ═══════════════════════════════════════════════════════════════

async def _verificar_avaliacoes_pendentes(db: Session):
    """Envia mensagem de avaliação 2 etapas: primeiro pergunta se houve problema."""
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
        models.BotConfig.avaliacao_ativa == True,
    ).all()

    for config in bot_configs:
        delay_min = config.delay_avaliacao_min or 20
        limite = datetime.utcnow() - timedelta(minutes=delay_min)
        limite_max = datetime.utcnow() - timedelta(hours=2)

        # Pedidos entregues pelo bot que ainda não têm avaliação
        pedidos = db.query(models.Pedido).filter(
            models.Pedido.restaurante_id == config.restaurante_id,
            models.Pedido.origem == "whatsapp_bot",
            models.Pedido.status == "entregue",
            models.Pedido.atualizado_em <= limite,
            models.Pedido.atualizado_em >= limite_max,
        ).all()

        for pedido in pedidos:
            # Verificar se já tem avaliação
            avaliacao_existente = db.query(models.BotAvaliacao).filter(
                models.BotAvaliacao.pedido_id == pedido.id,
            ).first()

            if avaliacao_existente:
                continue

            # Criar avaliação pendente
            avaliacao = models.BotAvaliacao(
                restaurante_id=config.restaurante_id,
                pedido_id=pedido.id,
                cliente_id=pedido.cliente_id,
                status="pendente",
            )
            db.add(avaliacao)

            # Enviar mensagem — Etapa 1: perguntar se houve problema
            telefone = pedido.cliente_telefone
            if telefone and config.evolution_instance:
                from . import evolution_client
                nome = pedido.cliente_nome or "cliente"

                if config.avaliacao_perguntar_problemas:
                    # Fluxo 2 etapas: primeiro perguntar se tudo ok
                    texto = f"Oi {nome}! 😊 Tudo certinho com o pedido #{pedido.comanda}? Teve algum probleminha?"
                else:
                    # Fluxo direto: pedir nota
                    texto = f"Oi {nome}! 😊 Tudo bem com o pedido #{pedido.comanda}? De 1 a 5, como foi a experiência?"

                try:
                    await evolution_client.enviar_texto(
                        telefone, texto,
                        config.evolution_instance,
                        config.evolution_api_url,
                        config.evolution_api_key,
                    )
                    logger.info(f"Avaliação enviada para {telefone[:8]}*** pedido #{pedido.comanda}")

                    # Marcar fase de avaliação na conversa ativa
                    conversa = db.query(models.BotConversa).filter(
                        models.BotConversa.restaurante_id == config.restaurante_id,
                        models.BotConversa.telefone.like(f"%{telefone[-8:]}"),
                        models.BotConversa.status == "ativa",
                    ).order_by(models.BotConversa.atualizado_em.desc()).first()

                    if conversa:
                        session_data = conversa.session_data or {}
                        session_data["fase_avaliacao"] = "aguardando_feedback"
                        session_data["avaliacao_pedido_id"] = pedido.id
                        conversa.session_data = session_data
                        from sqlalchemy.orm.attributes import flag_modified
                        flag_modified(conversa, "session_data")

                    # Registrar mensagem
                    msg_bot = models.BotMensagem(
                        conversa_id=conversa.id if conversa else None,
                        direcao="enviada",
                        tipo="texto",
                        conteudo=texto,
                    )
                    if conversa:
                        msg_bot.conversa_id = conversa.id
                        db.add(msg_bot)
                        conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1

                except Exception as e:
                    logger.error(f"Erro enviando avaliação: {e}")

        db.commit()


# ═══════════════════════════════════════════════════════════════
# WORKER 2: Detecção de atrasos (com políticas)
# ═══════════════════════════════════════════════════════════════

async def _verificar_atrasos(db: Session, ws_manager):
    """Detecta pedidos atrasados e notifica cliente com política configurada."""
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
    ).all()

    for config in bot_configs:
        pedidos = db.query(models.Pedido).filter(
            models.Pedido.restaurante_id == config.restaurante_id,
            models.Pedido.origem == "whatsapp_bot",
            models.Pedido.status.in_(["em_preparo", "pronto"]),
        ).all()

        for pedido in pedidos:
            if not pedido.data_criacao:
                continue

            agora = datetime.utcnow()
            minutos_decorridos = (agora - pedido.data_criacao).total_seconds() / 60

            config_rest = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == config.restaurante_id
            ).first()

            tempo_estimado = config_rest.tempo_medio_preparo if config_rest else 30
            tolerancia = config_rest.tolerancia_atraso_min if config_rest else 10

            if minutos_decorridos > (tempo_estimado + tolerancia):
                # Verificar se já notificou
                problema_existente = db.query(models.BotProblema).filter(
                    models.BotProblema.pedido_id == pedido.id,
                    models.BotProblema.tipo == "atraso",
                ).first()

                if problema_existente:
                    continue

                # Registrar problema
                problema = models.BotProblema(
                    restaurante_id=config.restaurante_id,
                    pedido_id=pedido.id,
                    cliente_id=pedido.cliente_id,
                    tipo="atraso",
                    descricao=f"Pedido #{pedido.comanda} atrasado {int(minutos_decorridos - tempo_estimado)} min além do estimado",
                )
                db.add(problema)

                # Aplicar política de atraso
                politica = config.politica_atraso or {}
                if isinstance(politica, str):
                    import json
                    try:
                        politica = json.loads(politica)
                    except Exception:
                        politica = {}

                acao = politica.get("acao", "desculpar")
                mensagem_extra = ""

                if acao in ("desconto_proximo", "cupom_fixo"):
                    desconto_pct = politica.get("desconto_pct", 0)
                    if desconto_pct > 0:
                        codigo = f"ATRASO{''.join(random.choices(string.digits, k=4))}"
                        try:
                            promo = models.Promocao(
                                restaurante_id=config.restaurante_id,
                                nome=f"Compensação atraso #{pedido.comanda}",
                                tipo_desconto="percentual",
                                valor_desconto=desconto_pct,
                                codigo_cupom=codigo,
                                ativo=True,
                                uso_limitado=True,
                                limite_usos=1,
                                usos_realizados=0,
                            )
                            db.add(promo)
                            problema.resolucao_tipo = "desconto_proximo"
                            problema.cupom_gerado = codigo
                            problema.desconto_pct = desconto_pct
                            problema.resolvido_automaticamente = True
                            problema.resolvido = True
                            problema.resolvido_em = datetime.utcnow()
                            mensagem_extra = f"\nPra compensar, use o cupom {codigo} para {desconto_pct:.0f}% no próximo pedido! 🎁"
                        except Exception as e:
                            logger.error(f"Erro gerando cupom atraso: {e}")

                # Notificar cliente
                telefone = pedido.cliente_telefone
                if telefone and config.evolution_instance:
                    from . import evolution_client
                    nome = pedido.cliente_nome or "cliente"
                    texto = f"Oi {nome}, peço desculpas pelo atraso no pedido #{pedido.comanda}. A equipe está finalizando e já sai! 🙏{mensagem_extra}"
                    try:
                        await evolution_client.enviar_texto(
                            telefone, texto,
                            config.evolution_instance,
                            config.evolution_api_url,
                            config.evolution_api_key,
                        )
                    except Exception as e:
                        logger.error(f"Erro notificando atraso: {e}")

                # Notificar painel
                try:
                    await ws_manager.broadcast({
                        "tipo": "bot_atraso_detectado",
                        "dados": {
                            "pedido_id": pedido.id,
                            "comanda": pedido.comanda,
                            "minutos_atraso": int(minutos_decorridos - tempo_estimado),
                        },
                    }, config.restaurante_id)
                except Exception:
                    pass

        db.commit()


# ═══════════════════════════════════════════════════════════════
# WORKER 3: Reset tokens diários
# ═══════════════════════════════════════════════════════════════

def _reset_tokens_diarios(db: Session):
    """Reset tokens usados diariamente à meia-noite."""
    agora = datetime.utcnow() - timedelta(hours=3)  # UTC-3

    configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
    ).all()

    for config in configs:
        ultimo_reset = config.tokens_reset_em
        if not ultimo_reset or ultimo_reset.date() < agora.date():
            config.tokens_usados_hoje = 0
            config.tokens_reset_em = datetime.utcnow()

    db.commit()


# ═══════════════════════════════════════════════════════════════
# WORKER 4: Repescagem inteligente de clientes inativos
# ═══════════════════════════════════════════════════════════════

async def _verificar_clientes_inativos(db: Session):
    """Detecta clientes inativos e envia repescagem com cupom."""
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
        models.BotConfig.repescagem_ativa == True,
    ).all()

    agora = datetime.utcnow()

    for config in bot_configs:
        # Limitar 1 execução por dia
        if config.repescagem_ultima_execucao:
            horas_desde = (agora - config.repescagem_ultima_execucao).total_seconds() / 3600
            if horas_desde < 20:  # Mínimo ~20h entre execuções
                continue

        candidatos = []

        if config.repescagem_usar_frequencia:
            # Modo inteligente: detectar frequência individual
            candidatos = _query_clientes_inativos_por_frequencia(db, config.restaurante_id)
        else:
            # Modo simples: dias fixos
            dias = config.repescagem_dias_inativo or 15
            limite = agora - timedelta(days=dias)
            candidatos = _query_clientes_inativos_simples(db, config.restaurante_id, limite)

        enviados = 0
        for candidato in candidatos[:10]:  # Max 10/dia por restaurante
            cliente_id = candidato["cliente_id"]
            telefone = candidato["telefone"]
            nome = candidato["nome"]

            # Verificar se já tem repescagem recente (30 dias)
            repescagem_recente = db.query(models.BotRepescagem).filter(
                models.BotRepescagem.cliente_id == cliente_id,
                models.BotRepescagem.restaurante_id == config.restaurante_id,
                models.BotRepescagem.criado_em >= agora - timedelta(days=30),
            ).first()

            if repescagem_recente:
                continue

            # Gerar cupom exclusivo: VOLTA-{primeiro_nome}-{5 chars}
            desconto = config.repescagem_desconto_pct or 10
            primeiro_nome = (nome or "cliente").split()[0].upper()
            codigo_unico = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            codigo = f"VOLTA-{primeiro_nome}-{codigo_unico}"

            # Garantir unicidade
            while db.query(models.Promocao).filter(
                models.Promocao.restaurante_id == config.restaurante_id,
                models.Promocao.codigo_cupom == codigo,
            ).first():
                codigo_unico = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
                codigo = f"VOLTA-{primeiro_nome}-{codigo_unico}"

            try:
                promo = models.Promocao(
                    restaurante_id=config.restaurante_id,
                    nome=f"Repescagem {nome}",
                    tipo_desconto="percentual",
                    valor_desconto=desconto,
                    codigo_cupom=codigo,
                    data_inicio=agora,
                    data_fim=agora + timedelta(days=7),
                    ativo=True,
                    uso_limitado=True,
                    limite_usos=1,
                    usos_realizados=0,
                    cliente_id=cliente_id,
                    tipo_cupom="repescagem",
                )
                db.add(promo)
                db.flush()
            except Exception:
                continue

            # Montar mensagem
            texto = (
                f"Oi {nome}! Faz tempo que não aparece por aqui, sentimos sua falta!\n"
                f"Pra te dar as boas-vindas de volta, preparei um cupom especial: "
                f"*{codigo}* com *{desconto:.0f}% de desconto*!\n"
                f"Válido por 7 dias. É só chamar quando quiser pedir!"
            )

            # Enviar
            if config.evolution_instance:
                from . import evolution_client
                try:
                    await evolution_client.enviar_texto(
                        telefone, texto,
                        config.evolution_instance,
                        config.evolution_api_url,
                        config.evolution_api_key,
                    )
                    enviados += 1
                except Exception as e:
                    logger.error(f"Erro enviando repescagem: {e}")
                    continue

            # Registrar repescagem
            repescagem = models.BotRepescagem(
                restaurante_id=config.restaurante_id,
                cliente_id=cliente_id,
                cupom_codigo=codigo,
                cupom_desconto_pct=desconto,
                mensagem_enviada=texto,
                cupom_validade_dias=7,
                canal="whatsapp",
                promocao_id=promo.id,
            )
            db.add(repescagem)

        # Atualizar última execução
        config.repescagem_ultima_execucao = agora
        from sqlalchemy.orm.attributes import flag_modified
        db.commit()

        if enviados > 0:
            logger.info(f"Repescagem: {enviados} mensagens enviadas para restaurante {config.restaurante_id}")


def _query_clientes_inativos_por_frequencia(db: Session, restaurante_id: int) -> list[dict]:
    """Detecta clientes inativos baseado na frequência individual de compra."""
    agora = datetime.utcnow()

    # Buscar clientes com ≥2 pedidos entregues
    from sqlalchemy import text
    resultado = db.execute(text("""
        SELECT
            c.id as cliente_id,
            c.nome,
            c.telefone,
            COUNT(p.id) as total_pedidos,
            MIN(p.data_criacao) as primeiro_pedido,
            MAX(p.data_criacao) as ultimo_pedido
        FROM clientes c
        JOIN pedidos p ON p.cliente_id = c.id
            AND p.restaurante_id = :rest_id
            AND p.status = 'entregue'
        WHERE c.restaurante_id = :rest_id
            AND c.telefone IS NOT NULL
            AND c.telefone != ''
        GROUP BY c.id, c.nome, c.telefone
        HAVING COUNT(p.id) >= 2
        ORDER BY MAX(p.data_criacao) ASC
    """), {"rest_id": restaurante_id}).fetchall()

    candidatos = []
    for row in resultado:
        cliente_id, nome, telefone, total, primeiro, ultimo = row
        if not primeiro or not ultimo or not telefone:
            continue

        dias_total = max(1, (ultimo - primeiro).days)
        media_intervalo = dias_total / max(1, total - 1)
        dias_inativo = (agora - ultimo).days

        # Se inativo > 115% do intervalo médio → candidato
        if dias_inativo > (media_intervalo * 1.15) and dias_inativo >= 3:
            candidatos.append({
                "cliente_id": cliente_id,
                "nome": nome or "Cliente",
                "telefone": telefone,
                "total_pedidos": total,
                "media_intervalo": round(media_intervalo, 1),
                "dias_inativo": dias_inativo,
            })

    return candidatos


def _query_clientes_inativos_simples(db: Session, restaurante_id: int, limite: datetime) -> list[dict]:
    """Detecta clientes inativos por dias fixos sem pedido."""
    from sqlalchemy import text
    resultado = db.execute(text("""
        SELECT
            c.id as cliente_id,
            c.nome,
            c.telefone,
            MAX(p.data_criacao) as ultimo_pedido
        FROM clientes c
        JOIN pedidos p ON p.cliente_id = c.id
            AND p.restaurante_id = :rest_id
            AND p.status = 'entregue'
        WHERE c.restaurante_id = :rest_id
            AND c.telefone IS NOT NULL
            AND c.telefone != ''
        GROUP BY c.id, c.nome, c.telefone
        HAVING MAX(p.data_criacao) < :limite
        ORDER BY MAX(p.data_criacao) ASC
    """), {"rest_id": restaurante_id, "limite": limite}).fetchall()

    return [
        {
            "cliente_id": row[0],
            "nome": row[1] or "Cliente",
            "telefone": row[2],
            "dias_inativo": (datetime.utcnow() - row[3]).days if row[3] else 0,
        }
        for row in resultado
    ]


# ═══════════════════════════════════════════════════════════════
# WORKER 4.5: Lembrete de cupons expirando (24h antes)
# ═══════════════════════════════════════════════════════════════

async def _verificar_cupons_expirando(db: Session):
    """Envia lembrete WA + email para cupons exclusivos/repescagem que expiram em 24h."""
    agora = datetime.utcnow()
    amanha = agora + timedelta(hours=24)

    # Buscar repescagens com cupom expirando nas próximas 24h e lembrete não enviado
    repescagens = db.query(models.BotRepescagem).filter(
        models.BotRepescagem.lembrete_enviado == False,
        models.BotRepescagem.retornou == False,
        models.BotRepescagem.promocao_id.isnot(None),
    ).all()

    for rep in repescagens:
        promo = db.query(models.Promocao).filter(
            models.Promocao.id == rep.promocao_id,
            models.Promocao.ativo == True,
        ).first()

        if not promo or not promo.data_fim:
            continue

        # Cupom expira nas próximas 24h?
        horas_restantes = (promo.data_fim - agora).total_seconds() / 3600
        if horas_restantes <= 0 or horas_restantes > 24:
            continue

        cliente = db.query(models.Cliente).filter(
            models.Cliente.id == rep.cliente_id,
        ).first()
        if not cliente:
            continue

        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.id == rep.restaurante_id,
        ).first()
        if not restaurante:
            continue

        nome = (cliente.nome or "Cliente").split()[0]
        desconto_str = f"{rep.cupom_desconto_pct:.0f}%" if rep.cupom_desconto_pct else "desconto"
        expira_str = promo.data_fim.strftime("%d/%m/%Y")

        # Enviar WA
        config = db.query(models.BotConfig).filter(
            models.BotConfig.restaurante_id == rep.restaurante_id,
            models.BotConfig.bot_ativo == True,
        ).first()

        if config and config.evolution_instance and cliente.telefone:
            texto = (
                f"Oi {nome}! Seu cupom *{rep.cupom_codigo}* de {desconto_str} "
                f"expira amanhã! Não perca essa oportunidade no {restaurante.nome_fantasia}."
            )
            try:
                from . import evolution_client
                await evolution_client.enviar_texto(
                    cliente.telefone, texto,
                    config.evolution_instance,
                    config.evolution_api_url,
                    config.evolution_api_key,
                )
            except Exception as e:
                logger.error(f"Erro lembrete WA cupom {rep.id}: {e}")

        # Enviar email
        if cliente.email:
            try:
                from ..email_service import enviar_email_lembrete_cupom
                await enviar_email_lembrete_cupom(
                    email_destino=cliente.email,
                    nome=nome,
                    codigo_cupom=rep.cupom_codigo,
                    desconto=desconto_str,
                    expira=expira_str,
                    nome_restaurante=restaurante.nome_fantasia,
                )
            except Exception as e:
                logger.error(f"Erro lembrete email cupom {rep.id}: {e}")

        rep.lembrete_enviado = True
        rep.lembrete_enviado_em = agora

    db.commit()


# ═══════════════════════════════════════════════════════════════
# WORKER 5: Notificação proativa de mudança de status
# ═══════════════════════════════════════════════════════════════

async def _notificar_mudancas_status(db: Session):
    """Notifica clientes proativamente quando status do pedido muda.
    Pedidos WhatsApp: entrega → motoboy chegou, retirada/balcão → pronto.
    Anti-spam: usa session_data da conversa para rastrear status já notificados.
    """
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
    ).all()

    for config in bot_configs:
        # Buscar conversas ativas recentes (últimas 4h)
        limite = datetime.utcnow() - timedelta(hours=4)
        conversas = db.query(models.BotConversa).filter(
            models.BotConversa.restaurante_id == config.restaurante_id,
            models.BotConversa.status == "ativa",
            models.BotConversa.atualizado_em >= limite,
            models.BotConversa.pedido_ativo_id.isnot(None),
        ).all()

        for conversa in conversas:
            pedido = db.query(models.Pedido).filter(
                models.Pedido.id == conversa.pedido_ativo_id,
                models.Pedido.restaurante_id == config.restaurante_id,
            ).first()

            if not pedido:
                continue

            # Obter status já notificados do session_data
            session_data = conversa.session_data or {}
            status_notificados = session_data.get("status_notificados", {})
            pedido_key = str(pedido.id)
            notificados_pedido = status_notificados.get(pedido_key, [])

            # Verificar se status atual já foi notificado
            if pedido.status in notificados_pedido:
                continue

            # Montar mensagem proativa baseada no status
            nome = conversa.nome_cliente or "cliente"
            mensagem = None

            if pedido.status == "em_preparo" and "em_preparo" not in notificados_pedido:
                mensagem = f"Oi {nome}! Seu pedido #{pedido.comanda} já está sendo preparado! 🍕"

            elif pedido.status == "pronto" and "pronto" not in notificados_pedido:
                # Se tipo retirada/balcão: notificar que está pronto para retirada
                if pedido.tipo_entrega in ("retirada", "balcao") or pedido.tipo == "retirada":
                    mensagem = f"{nome}, seu pedido #{pedido.comanda} está pronto pra retirada! Já pode vir buscar 🎉"
                else:
                    mensagem = f"{nome}, pedido #{pedido.comanda} pronto! Já já sai pra entrega 📦"

            elif pedido.status == "em_rota" and "em_rota" not in notificados_pedido:
                # Buscar nome do motoboy
                entrega = db.query(models.Entrega).filter(
                    models.Entrega.pedido_id == pedido.id,
                ).first()
                motoboy_nome = ""
                if entrega and entrega.motoboy_id:
                    motoboy = db.query(models.Motoboy).filter(models.Motoboy.id == entrega.motoboy_id).first()
                    if motoboy:
                        motoboy_nome = f" com o {motoboy.nome}"

                # Link de tracking
                restaurante = db.query(models.Restaurante).filter(
                    models.Restaurante.id == config.restaurante_id
                ).first()
                link = ""
                if restaurante and restaurante.codigo_acesso:
                    link = f"\nAcompanhe aqui: https://superfood-api.fly.dev/cliente/{restaurante.codigo_acesso}/pedido/{pedido.id}/tracking"

                mensagem = f"Pedido #{pedido.comanda} saiu{motoboy_nome}! 🛵{link}"

            elif pedido.status == "entregue" and "entregue" not in notificados_pedido:
                # Apenas confirmar entrega — NÃO pedir nota (o worker de avaliação faz isso depois)
                mensagem = f"Pedido #{pedido.comanda} entregue! Bom apetite! 😋"

            if not mensagem:
                continue

            # Enviar via Evolution
            telefone = conversa.telefone
            if telefone and config.evolution_instance:
                from . import evolution_client
                try:
                    await evolution_client.enviar_texto(
                        telefone, mensagem,
                        config.evolution_instance,
                        config.evolution_api_url,
                        config.evolution_api_key,
                    )
                    logger.info(f"Notificação proativa: pedido #{pedido.comanda} status={pedido.status} para {telefone[:8]}***")

                    # Registrar mensagem enviada
                    msg_bot = models.BotMensagem(
                        conversa_id=conversa.id,
                        direcao="enviada",
                        tipo="texto",
                        conteudo=mensagem,
                    )
                    db.add(msg_bot)
                    conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1

                    # Marcar status como notificado no session_data
                    notificados_pedido.append(pedido.status)
                    status_notificados[pedido_key] = notificados_pedido
                    session_data["status_notificados"] = status_notificados
                    conversa.session_data = session_data
                    # Forçar update do JSON (SQLAlchemy precisa detectar mudança)
                    from sqlalchemy.orm.attributes import flag_modified
                    flag_modified(conversa, "session_data")

                except Exception as e:
                    logger.error(f"Erro notificação proativa: {e}")

        db.commit()
