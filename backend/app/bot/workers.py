"""
Workers periódicos do Bot WhatsApp:
1. Detectar atrasos em pedidos e notificar cliente (a cada 5 min)
2. Enviar avaliação pós-entrega (a cada 2 min, verifica pedidos entregues)
3. Reset tokens diários (meia-noite)
4. Impressão automática: ao criar pedido, WebSocket já dispara no atendente.py
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal

logger = logging.getLogger("superfood.bot.workers")


async def bot_workers_loop(ws_manager):
    """Loop principal dos workers do bot. Roda em background."""
    while True:
        try:
            await asyncio.sleep(120)  # A cada 2 minutos

            db = SessionLocal()
            try:
                await _verificar_avaliacoes_pendentes(db)
                await _verificar_atrasos(db, ws_manager)
                _reset_tokens_diarios(db)
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("Bot workers encerrados")
            break
        except Exception as e:
            logger.error(f"Erro nos workers do bot: {e}")
            await asyncio.sleep(60)


async def _verificar_avaliacoes_pendentes(db: Session):
    """Envia mensagem de avaliação para pedidos entregues recentemente."""
    # Buscar pedidos entregues há mais de X minutos que ainda não têm avaliação
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
        models.BotConfig.avaliacao_ativa == True,
    ).all()

    for config in bot_configs:
        delay_min = config.delay_avaliacao_min or 10
        limite = datetime.utcnow() - timedelta(minutes=delay_min)
        limite_max = datetime.utcnow() - timedelta(hours=2)  # Não mandar para entregas muito antigas

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

            # Enviar mensagem via bot
            telefone = pedido.cliente_telefone
            if telefone and config.evolution_instance:
                from . import evolution_client
                nome = pedido.cliente_nome or "cliente"
                texto = f"Oi {nome}! 😊 Tudo bem com o pedido #{pedido.comanda}? De 1 a 5, como foi a experiência?"
                try:
                    await evolution_client.enviar_texto(
                        telefone, texto,
                        config.evolution_instance,
                        config.evolution_api_url,
                        config.evolution_api_key,
                    )
                    logger.info(f"Avaliação enviada para {telefone[:8]}*** pedido #{pedido.comanda}")
                except Exception as e:
                    logger.error(f"Erro enviando avaliação: {e}")

        db.commit()


async def _verificar_atrasos(db: Session, ws_manager):
    """Detecta pedidos atrasados e notifica cliente proativamente."""
    bot_configs = db.query(models.BotConfig).filter(
        models.BotConfig.bot_ativo == True,
    ).all()

    for config in bot_configs:
        # Buscar pedidos em rota com tempo excedido
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

            # Config do restaurante
            config_rest = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == config.restaurante_id
            ).first()

            tempo_estimado = config_rest.tempo_medio_preparo if config_rest else 30
            tolerancia = config_rest.tolerancia_atraso_min if config_rest else 10

            if minutos_decorridos > (tempo_estimado + tolerancia):
                # Verificar se já notificou (check BotProblema)
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

                # Notificar cliente
                telefone = pedido.cliente_telefone
                if telefone and config.evolution_instance:
                    from . import evolution_client
                    nome = pedido.cliente_nome or "cliente"
                    texto = f"Oi {nome}, peço desculpas pelo atraso no pedido #{pedido.comanda}. A equipe está finalizando e já sai! 🙏"
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
