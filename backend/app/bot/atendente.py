"""
Atendente WhatsApp Humanoide — Lógica principal.
Fluxo: webhook → identificar restaurante → identificar cliente → montar contexto 3 camadas
→ chamar Grok com function calling → executar ações → validar guardrails → responder.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal
from . import evolution_client, groq_stt, xai_tts, xai_llm
from .context_builder import build_system_prompt, build_restaurant_context, build_client_context, build_conversation_history
from .function_calls import TOOLS, executar_funcao

logger = logging.getLogger("superfood.bot.atendente")

# Anti-spam: locks por número para evitar respostas duplicadas
_processing_locks: dict[str, float] = {}
_LOCK_TIMEOUT = 30  # segundos

# Cache de msg IDs processados (dedup webhook)
_processed_msg_ids: dict[str, float] = {}
_DEDUP_MAX = 500


async def processar_webhook(payload: dict) -> dict:
    """Processa webhook da Evolution API. Ponto de entrada principal."""
    event = payload.get("event")

    # Apenas processar mensagens recebidas
    if event != "messages.upsert":
        return {"status": "ignored", "event": event}

    data = payload.get("data", {})
    msg_key = data.get("key", {})
    msg_id = msg_key.get("id", "")
    from_me = msg_key.get("fromMe", False)
    remote_jid = msg_key.get("remoteJid", "")

    # Ignorar mensagens próprias e grupos
    if from_me or "@g.us" in remote_jid:
        return {"status": "ignored", "reason": "own_msg_or_group"}

    # Dedup
    if msg_id in _processed_msg_ids:
        return {"status": "dedup"}
    _processed_msg_ids[msg_id] = time.time()
    _limpar_cache_dedup()

    # Extrair número e conteúdo
    numero = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
    instance = payload.get("instance", "")

    message = data.get("message", {})
    texto = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "")
    audio_msg = message.get("audioMessage")

    if not texto and not audio_msg:
        return {"status": "ignored", "reason": "no_text_no_audio"}

    # Processar em background para resposta rápida ao webhook
    asyncio.create_task(_processar_mensagem(numero, texto, audio_msg, msg_id, instance))

    return {"status": "processing"}


async def _processar_mensagem(
    numero: str,
    texto: str,
    audio_msg: dict | None,
    msg_id: str,
    instance_origem: str,
):
    """Processa mensagem individual em background."""
    # Anti-spam lock
    agora = time.time()
    if numero in _processing_locks and (agora - _processing_locks[numero]) < _LOCK_TIMEOUT:
        logger.debug(f"Lock ativo para {numero[:8]}***, ignorando")
        return
    _processing_locks[numero] = agora

    db = SessionLocal()
    try:
        # 1. Identificar restaurante pelo número de destino ou pela instância
        bot_config = _identificar_restaurante(db, instance_origem)
        if not bot_config or not bot_config.bot_ativo:
            logger.debug(f"Bot não encontrado/inativo para instance={instance_origem}")
            return

        restaurante_id = bot_config.restaurante_id

        # 2. Transcrever áudio se necessário
        if audio_msg and bot_config.stt_ativo:
            audio_data = await evolution_client.baixar_audio(
                msg_id,
                bot_config.evolution_instance,
                bot_config.evolution_api_url,
                bot_config.evolution_api_key,
            )
            if audio_data:
                resultado_stt = await groq_stt.transcrever_audio(
                    audio_data["base64"],
                    bot_config.idioma[:2] if bot_config.idioma else "pt",
                )
                texto = resultado_stt.get("texto", "")
                # Delay simulando escuta
                duracao = resultado_stt.get("duracao_seg", 5)
                await asyncio.sleep(min(duracao / 1.5, 10))

        if not texto:
            return

        # 3. Buscar ou criar conversa
        conversa = _get_or_create_conversa(db, restaurante_id, numero)

        # 4. Registrar mensagem recebida
        msg_recebida = models.BotMensagem(
            conversa_id=conversa.id,
            direcao="recebida",
            tipo="audio" if audio_msg else "texto",
            conteudo=texto,
            duracao_audio_seg=audio_msg.get("seconds") if audio_msg else None,
        )
        db.add(msg_recebida)
        conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
        if audio_msg:
            conversa.usou_audio = True
        db.flush()

        # 5. Buscar cliente
        cliente = db.query(models.Cliente).filter(
            models.Cliente.restaurante_id == restaurante_id,
            models.Cliente.telefone.like(f"%{numero[-8:]}"),
        ).first()
        if cliente:
            conversa.cliente_id = cliente.id
            conversa.nome_cliente = cliente.nome

        # 6. Montar contexto 3 camadas
        system_prompt = build_system_prompt(bot_config)
        restaurant_context = build_restaurant_context(db, restaurante_id)
        client_context = build_client_context(db, restaurante_id, numero, conversa, cliente)

        # 7. Montar mensagens para o LLM
        messages = [
            {"role": "system", "content": f"{system_prompt}\n\n{restaurant_context}\n\n{client_context}"},
        ]

        # Adicionar histórico de conversa
        history = build_conversation_history(db, conversa.id, limit=15)
        messages.extend(history)

        # Mensagem atual
        messages.append({"role": "user", "content": texto})

        # 8. Chamar LLM com function calling (loop até 5 iterações)
        resposta_final = None
        total_tokens_in = 0
        total_tokens_out = 0
        function_calls_log = []

        for iteracao in range(5):
            resultado = await xai_llm.chat_completion(
                messages=messages,
                tools=TOOLS,
                temperature=0.6,
                max_tokens=400,
            )

            total_tokens_in += resultado.get("tokens_input", 0)
            total_tokens_out += resultado.get("tokens_output", 0)

            tool_calls = resultado.get("tool_calls")
            content = resultado.get("content")

            if not tool_calls:
                # Resposta final
                resposta_final = content
                break

            # Executar function calls
            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                logger.info(f"Function call: {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:100]})")

                resultado_fn = executar_funcao(
                    fn_name, fn_args, db, restaurante_id, bot_config, conversa
                )

                function_calls_log.append({"nome": fn_name, "args": fn_args, "resultado": resultado_fn[:200]})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": resultado_fn,
                })

        if not resposta_final:
            resposta_final = "Opa, me dá um segundo que estou verificando aqui..."

        # 9. Delay humanizado (1-3 seg)
        delay = _calcular_delay_humano(len(resposta_final))
        await asyncio.sleep(delay)

        # 10. Decidir se envia áudio ou texto
        enviar_audio = _deve_enviar_audio(conversa, bot_config)

        if enviar_audio and bot_config.tts_autonomo:
            audio_b64 = await xai_tts.gerar_audio(resposta_final, bot_config.voz_tts or "ara", bot_config.idioma or "pt-BR")
            if audio_b64:
                await evolution_client.enviar_audio_ptt(
                    numero, audio_b64,
                    bot_config.evolution_instance,
                    bot_config.evolution_api_url,
                    bot_config.evolution_api_key,
                )
            else:
                # Fallback para texto
                await evolution_client.enviar_texto(
                    numero, resposta_final,
                    bot_config.evolution_instance,
                    bot_config.evolution_api_url,
                    bot_config.evolution_api_key,
                )
        else:
            await evolution_client.enviar_texto(
                numero, resposta_final,
                bot_config.evolution_instance,
                bot_config.evolution_api_url,
                bot_config.evolution_api_key,
            )

        # 11. Registrar mensagem enviada
        msg_enviada = models.BotMensagem(
            conversa_id=conversa.id,
            direcao="enviada",
            tipo="audio" if enviar_audio else "texto",
            conteudo=resposta_final,
            tokens_input=total_tokens_in,
            tokens_output=total_tokens_out,
            modelo_usado=xai_llm.MODELO_PADRAO,
            function_calls=function_calls_log if function_calls_log else None,
            tempo_resposta_ms=resultado.get("tempo_ms", 0),
        )
        db.add(msg_enviada)
        conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1
        conversa.atualizado_em = datetime.utcnow()

        # Atualizar tokens
        bot_config.tokens_usados_hoje = (bot_config.tokens_usados_hoje or 0) + total_tokens_in + total_tokens_out

        db.commit()

        # 12. Notificar painel via WebSocket
        await _notificar_painel(restaurante_id, conversa, resposta_final, function_calls_log)

    except Exception as e:
        logger.error(f"Erro processando mensagem de {numero[:8]}***: {e}", exc_info=True)
    finally:
        db.close()
        _processing_locks.pop(numero, None)


def _identificar_restaurante(db: Session, instance: str) -> Optional[models.BotConfig]:
    """Identifica restaurante pela instância Evolution."""
    return db.query(models.BotConfig).filter(
        models.BotConfig.evolution_instance == instance,
        models.BotConfig.bot_ativo == True,
    ).first()


def _get_or_create_conversa(db: Session, restaurante_id: int, telefone: str) -> models.BotConversa:
    """Busca conversa ativa ou cria nova."""
    # Buscar conversa ativa recente (últimas 2h)
    limite = datetime.utcnow() - timedelta(hours=2)
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.restaurante_id == restaurante_id,
        models.BotConversa.telefone == telefone,
        models.BotConversa.status == "ativa",
        models.BotConversa.atualizado_em >= limite,
    ).first()

    if conversa:
        return conversa

    # Criar nova conversa
    conversa = models.BotConversa(
        restaurante_id=restaurante_id,
        telefone=telefone,
        status="ativa",
    )
    db.add(conversa)
    db.flush()
    return conversa


def _calcular_delay_humano(tamanho_resposta: int) -> float:
    """Simula tempo de digitação humana (1-3 seg)."""
    import random
    base = 1.0
    extra = min(tamanho_resposta / 200, 2.0)  # 200 chars = +1s, máx +2s
    return base + extra + random.uniform(0, 0.5)


def _deve_enviar_audio(conversa: models.BotConversa, bot_config: models.BotConfig) -> bool:
    """Decide se deve enviar áudio TTS ao invés de texto.
    Critérios:
    1. Cliente enviou áudio (reciprocidade)
    2. Conversa longa sem avanço (>=8 msgs)
    """
    if not bot_config.tts_autonomo:
        return False
    if conversa.usou_audio:
        return True
    if (conversa.msgs_recebidas or 0) >= 8:
        return True
    return False


async def _notificar_painel(restaurante_id: int, conversa: models.BotConversa, resposta: str, function_calls: list):
    """Notifica o painel do restaurante via WebSocket sobre atividade do bot."""
    try:
        from ..main import manager
        await manager.broadcast({
            "tipo": "bot_mensagem",
            "dados": {
                "conversa_id": conversa.id,
                "telefone": conversa.telefone,
                "nome_cliente": conversa.nome_cliente,
                "resposta": resposta[:200],
                "function_calls": [fc["nome"] for fc in function_calls] if function_calls else [],
                "pedido_criado": any(fc["nome"] == "criar_pedido" for fc in function_calls) if function_calls else False,
            },
        }, restaurante_id)
    except Exception as e:
        logger.debug(f"Erro notificando painel: {e}")


def _limpar_cache_dedup():
    """Limpa cache de dedup quando passa de _DEDUP_MAX."""
    global _processed_msg_ids
    if len(_processed_msg_ids) > _DEDUP_MAX:
        agora = time.time()
        _processed_msg_ids = {k: v for k, v in _processed_msg_ids.items() if agora - v < 300}
