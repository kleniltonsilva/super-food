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
from . import whatsapp_client as _wa
try:
    from . import fish_tts as _fish_tts
except ImportError:
    _fish_tts = None
from .context_builder import build_system_prompt, build_restaurant_context, build_client_context, build_conversation_history
from .function_calls import TOOLS, executar_funcao
from . import phone_pool as _phone_pool

logger = logging.getLogger("superfood.bot.atendente")

# Anti-spam: serializar processamento por número (NUNCA descarta mensagens)
_number_locks: dict[str, asyncio.Lock] = {}
_MAX_NUMBER_LOCKS = 200

# Cache de msg IDs processados (dedup webhook)
_processed_msg_ids: dict[str, float] = {}
_DEDUP_MAX = 500


def _get_number_lock(numero: str) -> asyncio.Lock:
    """Retorna lock asyncio por número. Serializa processamento sem descartar mensagens."""
    if len(_number_locks) > _MAX_NUMBER_LOCKS:
        _number_locks.clear()
    if numero not in _number_locks:
        _number_locks[numero] = asyncio.Lock()
    return _number_locks[numero]


# ============================================================
# PREPARAÇÃO DE TEXTO PARA ÁUDIO (DICÇÃO BRASILEIRA)
# O LLM gera português correto. Para TEXTO, envia direto.
# Para ÁUDIO, transforma em dicção falada brasileira natural.
# ============================================================
import re as _re

# ============================================================
# DICÇÃO BRASILEIRA PARA ÁUDIO — Abordagem 70/30
# 70% formal + 30% informal = som humano sem parecer analfabeto.
# Proporção: OBRIGATÓRIAS sempre, PERMITIDAS com espaçamento.
# PROIBIDO: você→cê, não→num, porque→purque, verbos -ER/-IR drop.
# ============================================================

# OBRIGATÓRIAS — tão universais que todo brasileiro fala assim
_DICCAO_OBRIGATORIAS = [
    (r'\bnão é\b', 'né'), (r'\bNão é\b', 'Né'),
    (r'\bpara o\b', 'pro'), (r'\bpara os\b', 'pros'),
    (r'\bpara a\b', 'pra'), (r'\bpara as\b', 'pras'),
    (r'\bpara\b', 'pra'), (r'\bPara\b', 'Pra'),
    (r'\bestou\b', 'tô'), (r'\bEstou\b', 'Tô'),
    (r'\bestá\b', 'tá'), (r'\bEstá\b', 'Tá'),
    (r'\bestão\b', 'tão'), (r'\bestamos\b', 'tamo'),
    (r'\bestava\b', 'tava'), (r'\bEstava\b', 'Tava'),
    (r'\bestavam\b', 'tavam'),
]

# PERMITIDAS — verbos -AR que podem perder o R (com controle de espaçamento)
_VERBOS_AR_DROP = {
    'falar', 'explicar', 'mandar', 'pagar', 'ajudar', 'mostrar', 'usar',
    'cobrar', 'achar', 'deixar', 'passar', 'ligar', 'chamar', 'precisar',
    'conversar', 'retornar', 'testar', 'cancelar', 'contar', 'gostar',
    'adicionar', 'confirmar', 'verificar', 'preparar', 'entregar', 'buscar',
}


def _preparar_texto_para_audio(texto: str) -> str:
    """Transforma português correto do LLM → dicção falada brasileira para TTS.

    Abordagem 70/30: maioria formal, contrações apenas nas mais universais.
    NUNCA transforma: você, não, porque, verbos -ER/-IR, plurais.
    Pronúncia de marcas (Derekh→Dérikh) é feita pelo TTS module.
    """
    # 1. Contrações OBRIGATÓRIAS (universais — todo brasileiro fala)
    for pattern, repl in _DICCAO_OBRIGATORIAS:
        texto = _re.sub(pattern, repl, texto)

    # 2. R-drop CONTROLADO — apenas verbos -AR, com espaçamento de 8 palavras
    palavras = texto.split()
    ultima_conversao_pos = -10  # posição da última conversão permitida
    for i, palavra in enumerate(palavras):
        # Limpar pontuação para checagem
        limpa = _re.sub(r'[.,!?;:]+$', '', palavra).lower()
        if limpa in _VERBOS_AR_DROP and palavra.endswith(('ar', 'ar.', 'ar!', 'ar?', 'ar,')):
            # Respeitar espaçamento: mínimo 8 palavras entre conversões permitidas
            if i - ultima_conversao_pos >= 8 and i > 0:
                # Preservar pontuação original
                sufixo = palavra[len(limpa):]
                palavras[i] = palavra[:-(len('ar') + len(sufixo))] + 'á' + sufixo
                ultima_conversao_pos = i
    texto = ' '.join(palavras)

    # 3. Encerramento casual — "obrigado" → "brigado" APENAS na última frase
    if texto.rstrip().endswith(('obrigado!', 'obrigada!', 'obrigado.', 'obrigada.')):
        texto = _re.sub(r'\bobrigado\b', 'brigado', texto, count=0, flags=_re.IGNORECASE)
    elif texto.rstrip().endswith(('obrigado', 'obrigada')):
        texto = _re.sub(r'\b(O|o)brigad(o|a)\s*$', lambda m: ('B' if m.group(1) == 'O' else 'b') + 'rigad' + m.group(2), texto)

    # 4. Risadas → remover
    texto = _re.sub(r'\bk{3,}\b', '', texto, flags=_re.IGNORECASE)
    texto = _re.sub(r'\bha{3,}h?\b', '', texto, flags=_re.IGNORECASE)
    texto = _re.sub(r'\brs{2,}\b', '', texto, flags=_re.IGNORECASE)
    texto = _re.sub(r'\bhehe\b', '', texto, flags=_re.IGNORECASE)

    # 5. Remover elementos visuais (URLs, markdown, emojis)
    texto = _re.sub(r'https?://\S+', '', texto)
    texto = _re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', texto)
    texto = _re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)
    texto = _re.sub(
        r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
        r'\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF'
        r'\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002600-\U000026FF'
        r'\U0000FE00-\U0000FE0F\U0000200D]', '', texto
    )

    # 6. Limpeza final
    texto = _re.sub(r'  +', ' ', texto)
    texto = _re.sub(r'\s+([.,!?])', r'\1', texto)
    return texto.strip()


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

    # Extrair número — WhatsApp pode usar @lid (Linked ID) em vez de @s.whatsapp.net
    if "@lid" in remote_jid:
        # @lid usa ID interno; número real está em remoteJidAlt
        alt_jid = msg_key.get("remoteJidAlt", "")
        numero = alt_jid.split("@")[0] if "@" in alt_jid else remote_jid.split("@")[0]
        logger.info(f"LID detectado: {remote_jid} → número real: {numero}")
    else:
        numero = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
    instance = payload.get("instance", "")

    message = data.get("message", {})
    texto = message.get("conversation") or message.get("extendedTextMessage", {}).get("text", "")
    audio_msg = message.get("audioMessage")

    # Se não é texto nem áudio, tratar como mensagem de mídia
    if not texto and not audio_msg:
        # Verificar se é imagem, vídeo, sticker, documento ou localização
        if message.get("imageMessage") or message.get("videoMessage") or message.get("stickerMessage") or message.get("documentMessage"):
            texto = "[cliente enviou mídia que não consigo processar]"
        elif message.get("locationMessage"):
            loc = message.get("locationMessage", {})
            texto = f"[cliente compartilhou localização: lat={loc.get('degreesLatitude')}, lng={loc.get('degreesLongitude')}]"
        elif message.get("contactMessage") or message.get("contactsArrayMessage"):
            texto = "[cliente enviou um contato]"
        else:
            return {"status": "ignored", "reason": "no_text_no_audio"}

    # Processar em background para resposta rápida ao webhook
    asyncio.create_task(_processar_mensagem(numero, texto, audio_msg, msg_id, instance))

    return {"status": "processing"}


async def processar_webhook_meta(payload: dict) -> dict:
    """Processa webhook da Meta Cloud API. Ponto de entrada para provider 'meta'.
    Extrai mensagens do payload Meta e despacha para _processar_mensagem_meta()."""
    entries = payload.get("entry", [])
    if not entries:
        return {"status": "ignored", "reason": "no_entry"}

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            if value.get("messaging_product") != "whatsapp":
                continue

            # Ignorar status updates (delivered, read, etc.)
            statuses = value.get("statuses")
            if statuses:
                continue

            messages = value.get("messages", [])
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id", "")

            if not phone_number_id or not messages:
                continue

            for msg in messages:
                numero = msg.get("from", "")
                msg_id = msg.get("id", "")
                msg_type = msg.get("type", "")

                if not numero or not msg_id:
                    continue

                # Dedup
                if msg_id in _processed_msg_ids:
                    continue
                _processed_msg_ids[msg_id] = time.time()
                _limpar_cache_dedup()
            
                # Extrair texto ou áudio
                texto = ""
                audio_meta = None

                if msg_type == "text":
                    texto = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    # Botão interativo ou lista
                    interactive = msg.get("interactive", {})
                    btn_reply = interactive.get("button_reply", {})
                    list_reply = interactive.get("list_reply", {})
                    texto = btn_reply.get("title", "") or list_reply.get("title", "")
                elif msg_type == "audio":
                    audio_meta = msg.get("audio", {})
                elif msg_type in ("image", "video", "sticker", "document"):
                    texto = "[cliente enviou mídia que não consigo processar]"
                elif msg_type == "location":
                    lat = msg.get("location", {}).get("latitude")
                    lng = msg.get("location", {}).get("longitude")
                    texto = f"[cliente compartilhou localização: lat={lat}, lng={lng}]"
                elif msg_type == "contacts":
                    texto = "[cliente enviou um contato]"
                elif msg_type == "reaction":
                    continue  # Reações não precisam de resposta
                else:
                    continue

                if not texto and not audio_meta:
                    continue

                # Processar em background
                asyncio.create_task(
                    _processar_mensagem_meta(numero, texto, audio_meta, msg_id, phone_number_id)
                )

    return {"status": "processing"}


async def _processar_mensagem_meta(
    numero: str,
    texto: str,
    audio_meta: dict | None,
    msg_id: str,
    phone_number_id: str,
):
    """Processa mensagem Meta em background. Identifica restaurante por phone_number_id."""
    # Serializar por número — nunca descartar mensagens
    lock = _get_number_lock(numero)
    await lock.acquire()

    db = SessionLocal()
    try:
        # 1. Identificar restaurante pelo meta_phone_number_id
        bot_config = db.query(models.BotConfig).filter(
            models.BotConfig.meta_phone_number_id == phone_number_id,
            models.BotConfig.bot_ativo == True,
        ).first()

        if not bot_config:
            logger.debug(f"Bot Meta não encontrado para phone_number_id={phone_number_id}")
            return

        restaurante_id = bot_config.restaurante_id

        # 1.5. Mark as read imediatamente
        await _wa.marcar_lida(msg_id, bot_config)

        # 2. Transcrever áudio se necessário
        if audio_meta:
            if bot_config.stt_ativo:
                media_id = audio_meta.get("id", "")
                if media_id:
                    audio_data = await _wa.baixar_audio(media_id, bot_config)
                    if audio_data:
                        resultado_stt = await groq_stt.transcrever_audio(
                            audio_data["base64"],
                            bot_config.idioma[:2] if bot_config.idioma else "pt",
                        )
                        texto = resultado_stt.get("texto", "")
                        duracao = resultado_stt.get("duracao_seg", 5)
                        await asyncio.sleep(min(duracao / 1.5, 10))
                    else:
                        logger.warning(f"Download áudio Meta falhou para {numero[:8]}***")
            else:
                logger.warning(f"STT desativado — áudio de {numero[:8]}*** não transcrito")

            # Áudio recebido mas transcrição falhou → registrar no BD + avisar cliente
            if not texto:
                logger.warning(f"Áudio sem transcrição de {numero[:8]}*** (Meta) — enviando fallback")
                conversa = _get_or_create_conversa(db, restaurante_id, numero, pool_entry=None, bot_config=bot_config)
                msg_recebida = models.BotMensagem(
                    conversa_id=conversa.id,
                    direcao="recebida",
                    tipo="audio",
                    conteudo="[áudio não transcrito]",
                    duracao_audio_seg=audio_meta.get("duration"),
                )
                db.add(msg_recebida)
                conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
                conversa.usou_audio = True

                fallback = "Oi! Não consegui ouvir seu áudio direito 😅 Pode mandar por texto?"
                await _wa.enviar_texto(numero, fallback, bot_config)

                msg_fallback = models.BotMensagem(
                    conversa_id=conversa.id,
                    direcao="enviada",
                    tipo="texto",
                    conteudo=fallback,
                )
                db.add(msg_fallback)
                conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1
                conversa.atualizado_em = datetime.utcnow()
                db.commit()
                return

        if not texto:
            return

        # 3. Buscar ou criar conversa (pool_entry=None para Meta — sem pool)
        conversa = _get_or_create_conversa(db, restaurante_id, numero, pool_entry=None, bot_config=bot_config)

        # 3.5 Se conversa em handoff, apenas registrar
        if conversa.status == "handoff":
            msg_recebida = models.BotMensagem(
                conversa_id=conversa.id,
                direcao="recebida",
                tipo="audio" if audio_meta else "texto",
                conteudo=texto,
                duracao_audio_seg=audio_meta.get("duration") if audio_meta else None,
            )
            db.add(msg_recebida)
            conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
            conversa.atualizado_em = datetime.utcnow()
            db.commit()
            logger.info(f"Conversa {conversa.id} em handoff (Meta) — msg registrada, bot não responde")
            return

        # 4. Registrar mensagem recebida
        msg_recebida = models.BotMensagem(
            conversa_id=conversa.id,
            direcao="recebida",
            tipo="audio" if audio_meta else "texto",
            conteudo=texto,
            duracao_audio_seg=audio_meta.get("duration") if audio_meta else None,
        )
        db.add(msg_recebida)
        conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
        if audio_meta:
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
        history = build_conversation_history(db, conversa.id, limit=15)
        messages.extend(history)
        messages.append({"role": "user", "content": texto})

        # 7.5. Typing indicator
        await _wa.enviar_typing(numero, bot_config)

        # 8. Chamar LLM com function calling (loop até 5 iterações)
        resposta_final = None
        total_tokens_in = 0
        total_tokens_out = 0
        function_calls_log = []

        for iteracao in range(5):
            resultado = await xai_llm.chat_completion(
                messages=messages,
                tools=TOOLS,
                temperature=0.4,
                max_tokens=1000,
            )

            total_tokens_in += resultado.get("tokens_input", 0)
            total_tokens_out += resultado.get("tokens_output", 0)

            tool_calls = resultado.get("tool_calls")
            content = resultado.get("content")

            if not tool_calls:
                resposta_final = content
                break

            messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

            for tc in tool_calls:
                fn_name = tc["function"]["name"]
                fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                logger.info(f"Function call (Meta): {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:100]})")

                resultado_fn = await executar_funcao(
                    fn_name, fn_args, db, restaurante_id, bot_config, conversa
                )

                function_calls_log.append({"nome": fn_name, "args": fn_args, "resultado": resultado_fn[:200]})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": resultado_fn,
                })

        if not resposta_final:
            logger.warning(f"Loop function calling esgotou 5 iterações (Meta, tel={numero})")
            resposta_final = "Desculpa a demora! Estou aqui sim. Em que posso te ajudar?"

        # 8.5 SAFETY NET (mesma lógica do Evolution)
        chamou_criar_pedido = any(fc["nome"] == "criar_pedido" for fc in function_calls_log)
        criou_pedido_pix = any(
            fc["nome"] == "criar_pedido" and "pix_online" in fc.get("resultado", "")
            for fc in function_calls_log
        )
        if resposta_final and not chamou_criar_pedido and not criou_pedido_pix and bot_config.pode_criar_pedido:
            _PHANTOM_PATTERNS = [
                "pedido confirmado", "pedido criado", "seu pedido já",
                "comanda #", "comanda wa", "já vou preparar",
                "encaminhei pra cozinha", "mandei pra cozinha",
                "enviei pra cozinha", "anotei seu pedido",
                "tá feito", "pedido registrado", "confirmei seu pedido",
                "pedido foi criado", "seu pedido foi", "pedido anotado",
            ]
            texto_lower = resposta_final.lower()
            phantom = any(p in texto_lower for p in _PHANTOM_PATTERNS)

            has_order_context = False
            if conversa and conversa.session_data:
                has_order_context = bool(conversa.session_data.get("endereco_validado"))
            if not has_order_context:
                has_order_context = any(
                    fc["nome"] in ("validar_endereco", "confirmar_endereco_validado")
                    for fc in function_calls_log
                )

            if phantom and has_order_context:
                logger.warning(f"SAFETY NET (Meta): LLM disse 'confirmado' sem chamar criar_pedido")

                messages.append({"role": "assistant", "content": resposta_final})
                messages.append({
                    "role": "user",
                    "content": (
                        "SISTEMA INTERNO: Você disse que o pedido foi confirmado/criado, mas NÃO chamou a função criar_pedido. "
                        "O pedido NÃO existe no sistema. Chame criar_pedido AGORA com os dados desta conversa. "
                        "Use produto_id do cardápio fornecido no contexto do restaurante."
                    ),
                })

                try:
                    resultado_force = await xai_llm.chat_completion(
                        messages=messages,
                        tools=TOOLS,
                        temperature=0.3,
                        max_tokens=1000,
                        tool_choice={"type": "function", "function": {"name": "criar_pedido"}},
                    )

                    total_tokens_in += resultado_force.get("tokens_input", 0)
                    total_tokens_out += resultado_force.get("tokens_output", 0)

                    force_tool_calls = resultado_force.get("tool_calls")
                    if force_tool_calls:
                        messages.append({
                            "role": "assistant",
                            "content": resultado_force.get("content"),
                            "tool_calls": force_tool_calls,
                        })

                        for tc in force_tool_calls:
                            fn_name = tc["function"]["name"]
                            fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                            logger.info(f"SAFETY NET FC (Meta): {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})")

                            resultado_fn = await executar_funcao(fn_name, fn_args, db, restaurante_id, bot_config, conversa)
                            function_calls_log.append({"nome": fn_name, "args": fn_args, "resultado": resultado_fn[:200]})

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": resultado_fn,
                            })

                        resultado_final2 = await xai_llm.chat_completion(
                            messages=messages,
                            tools=TOOLS,
                            temperature=0.4,
                            max_tokens=1000,
                        )
                        total_tokens_in += resultado_final2.get("tokens_input", 0)
                        total_tokens_out += resultado_final2.get("tokens_output", 0)

                        if resultado_final2.get("content"):
                            resposta_final = resultado_final2["content"]
                            logger.info("SAFETY NET (Meta): criar_pedido forçado com sucesso")

                except Exception as e:
                    logger.error(f"SAFETY NET (Meta) erro: {e}", exc_info=True)

        # 9. Delay humanizado
        delay = _calcular_delay_humano(len(resposta_final))
        await asyncio.sleep(delay)

        # 10. Enviar resposta (texto ou áudio)
        enviar_audio = _deve_enviar_audio(conversa, bot_config)

        envio_ok = False
        try:
            if enviar_audio and bot_config.tts_autonomo:
                resposta_audio = _preparar_texto_para_audio(resposta_final)

                audio_b64 = None
                tts_provider = getattr(bot_config, "tts_provider", "") or ""
                if tts_provider.lower() == "fish" and _fish_tts:
                    audio_b64 = await _fish_tts.gerar_audio(
                        resposta_audio,
                        voz=bot_config.voz_tts or "",
                        idioma=bot_config.idioma or "pt-BR",
                    )
                    if audio_b64:
                        logger.info("TTS via Fish Audio S2-Pro (Meta)")
                if not audio_b64:
                    audio_b64 = await xai_tts.gerar_audio(resposta_audio, bot_config.voz_tts or "ara", bot_config.idioma or "pt-BR")
                if audio_b64:
                    try:
                        await _wa.enviar_presenca_conversa(numero, bot_config, presenca="recording", delay_ms=3000)
                        await _wa.enviar_audio_ptt(numero, audio_b64, bot_config)
                    except Exception as audio_err:
                        logger.warning(f"Áudio Meta falhou, enviando texto: {audio_err}")
                        await _wa.enviar_texto(numero, resposta_final, bot_config)
                else:
                    await _wa.enviar_texto(numero, resposta_final, bot_config)
            else:
                await _wa.enviar_texto(numero, resposta_final, bot_config)
            envio_ok = True

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem Meta para {numero[:8]}***: {e}")

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

        bot_config.tokens_usados_hoje = (bot_config.tokens_usados_hoje or 0) + total_tokens_in + total_tokens_out

        try:
            db.commit()
        except Exception as commit_err:
            logger.error(f"Commit final falhou (Meta msg/tokens): {commit_err}")
            try:
                db.rollback()
            except Exception:
                pass

        # 12. Notificar painel via WebSocket
        await _notificar_painel(restaurante_id, conversa, resposta_final, function_calls_log)

    except Exception as e:
        logger.error(f"Erro processando mensagem Meta de {numero[:8]}***: {e}", exc_info=True)
    finally:
        db.close()
        lock.release()


async def _processar_mensagem(
    numero: str,
    texto: str,
    audio_msg: dict | None,
    msg_id: str,
    instance_origem: str,
):
    """Processa mensagem individual em background."""
    # Serializar por número — nunca descartar mensagens
    lock = _get_number_lock(numero)
    await lock.acquire()

    db = SessionLocal()
    try:
        # 1. Identificar restaurante pelo número de destino ou pela instância
        bot_config = _identificar_restaurante(db, instance_origem)
        if not bot_config or not bot_config.bot_ativo:
            logger.debug(f"Bot não encontrado/inativo para instance={instance_origem}")
            return

        restaurante_id = bot_config.restaurante_id

        # 1.5. Verificar pool de números (retorna entry ativa ou None → usa BotConfig direto)
        pool_entry = _phone_pool.get_active_number(db, restaurante_id)

        # 2. Transcrever áudio se necessário
        if audio_msg:
            if bot_config.stt_ativo:
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
                else:
                    logger.warning(f"Download áudio Evolution falhou para {numero[:8]}***")
            else:
                logger.warning(f"STT desativado — áudio de {numero[:8]}*** não transcrito")

            # Áudio recebido mas transcrição falhou → registrar no BD + avisar cliente
            if not texto:
                logger.warning(f"Áudio sem transcrição de {numero[:8]}*** (Evolution) — enviando fallback")
                conversa = _get_or_create_conversa(db, restaurante_id, numero, pool_entry, bot_config)
                msg_recebida = models.BotMensagem(
                    conversa_id=conversa.id,
                    direcao="recebida",
                    tipo="audio",
                    conteudo="[áudio não transcrito]",
                    duracao_audio_seg=audio_msg.get("seconds"),
                )
                db.add(msg_recebida)
                conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
                conversa.usou_audio = True

                _inst = pool_entry.evolution_instance if pool_entry else bot_config.evolution_instance
                _url = pool_entry.evolution_api_url if pool_entry else bot_config.evolution_api_url
                _key = pool_entry.evolution_api_key if pool_entry else bot_config.evolution_api_key
                fallback = "Oi! Não consegui ouvir seu áudio direito 😅 Pode mandar por texto?"
                await evolution_client.enviar_texto(numero, fallback, _inst, _url, _key)

                msg_fallback = models.BotMensagem(
                    conversa_id=conversa.id,
                    direcao="enviada",
                    tipo="texto",
                    conteudo=fallback,
                )
                db.add(msg_fallback)
                conversa.msgs_enviadas = (conversa.msgs_enviadas or 0) + 1
                conversa.atualizado_em = datetime.utcnow()
                db.commit()
                return

        if not texto:
            return

        # 3. Buscar ou criar conversa (grava numero_bot + phone_pool_id)
        conversa = _get_or_create_conversa(db, restaurante_id, numero, pool_entry, bot_config)

        # 3.5 Se conversa em handoff (admin controlando), NÃO responder — apenas registrar msg
        if conversa.status == "handoff":
            msg_recebida = models.BotMensagem(
                conversa_id=conversa.id,
                direcao="recebida",
                tipo="audio" if audio_msg else "texto",
                conteudo=texto,
                duracao_audio_seg=audio_msg.get("seconds") if audio_msg else None,
            )
            db.add(msg_recebida)
            conversa.msgs_recebidas = (conversa.msgs_recebidas or 0) + 1
            conversa.atualizado_em = datetime.utcnow()
            db.commit()
            logger.info(f"Conversa {conversa.id} em handoff — msg registrada, bot não responde")
            return

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

        # 7.5. Presença: ficar "online" + "digitando..." enquanto processa
        _pres_instance = pool_entry.evolution_instance if pool_entry else bot_config.evolution_instance
        _pres_url = pool_entry.evolution_api_url if pool_entry else bot_config.evolution_api_url
        _pres_key = pool_entry.evolution_api_key if pool_entry else bot_config.evolution_api_key
        await evolution_client.definir_presenca(_pres_instance, _pres_url, _pres_key, "available")
        await evolution_client.enviar_presenca_conversa(
            numero, _pres_instance, _pres_url, _pres_key,
            presenca="composing", delay_ms=15000,
        )

        # 8. Chamar LLM com function calling (loop até 5 iterações)
        resposta_final = None
        total_tokens_in = 0
        total_tokens_out = 0
        function_calls_log = []

        for iteracao in range(5):
            resultado = await xai_llm.chat_completion(
                messages=messages,
                tools=TOOLS,
                temperature=0.4,
                max_tokens=1000,
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

                resultado_fn = await executar_funcao(
                    fn_name, fn_args, db, restaurante_id, bot_config, conversa
                )

                function_calls_log.append({"nome": fn_name, "args": fn_args, "resultado": resultado_fn[:200]})

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": resultado_fn,
                })

        if not resposta_final:
            logger.warning(f"Loop function calling esgotou 5 iterações sem resposta final (tel={numero})")
            resposta_final = "Desculpa a demora! Estou aqui sim. Em que posso te ajudar?"

        # 8.5 SAFETY NET: Detectar "confirmação fantasma" — LLM diz confirmado sem chamar criar_pedido
        # Skip safety net se criar_pedido retornou pix_online (pedido aguardando pagamento, não vai pra cozinha)
        chamou_criar_pedido = any(fc["nome"] == "criar_pedido" for fc in function_calls_log)
        criou_pedido_pix = any(
            fc["nome"] == "criar_pedido" and "pix_online" in fc.get("resultado", "")
            for fc in function_calls_log
        )
        if resposta_final and not chamou_criar_pedido and not criou_pedido_pix and bot_config.pode_criar_pedido:
            _PHANTOM_PATTERNS = [
                "pedido confirmado", "pedido criado", "seu pedido já",
                "comanda #", "comanda wa", "já vou preparar",
                "encaminhei pra cozinha", "mandei pra cozinha",
                "enviei pra cozinha", "anotei seu pedido",
                "tá feito", "pedido registrado", "confirmei seu pedido",
                "pedido foi criado", "seu pedido foi", "pedido anotado",
            ]
            texto_lower = resposta_final.lower()
            phantom = any(p in texto_lower for p in _PHANTOM_PATTERNS)

            # Verificar se há contexto real de pedido (endereço validado OU itens no carrinho)
            # Evita falso positivo em conversas de consulta (horário, bairros, etc.)
            has_order_context = False
            if conversa and conversa.session_data:
                has_order_context = bool(conversa.session_data.get("endereco_validado"))
            if not has_order_context:
                # Checar se validar_endereco foi chamado nesta interação
                has_order_context = any(
                    fc["nome"] in ("validar_endereco", "confirmar_endereco_validado")
                    for fc in function_calls_log
                )

            if phantom and has_order_context:
                logger.warning(f"SAFETY NET: LLM disse 'confirmado' sem chamar criar_pedido — forçando function call")

                # Injetar mensagem de correção e forçar tool_choice
                messages.append({"role": "assistant", "content": resposta_final})
                messages.append({
                    "role": "user",
                    "content": (
                        "SISTEMA INTERNO: Você disse que o pedido foi confirmado/criado, mas NÃO chamou a função criar_pedido. "
                        "O pedido NÃO existe no sistema. Chame criar_pedido AGORA com os dados desta conversa. "
                        "Use produto_id do cardápio fornecido no contexto do restaurante."
                    ),
                })

                try:
                    resultado_force = await xai_llm.chat_completion(
                        messages=messages,
                        tools=TOOLS,
                        temperature=0.3,
                        max_tokens=1000,
                        tool_choice={"type": "function", "function": {"name": "criar_pedido"}},
                    )

                    total_tokens_in += resultado_force.get("tokens_input", 0)
                    total_tokens_out += resultado_force.get("tokens_output", 0)

                    force_tool_calls = resultado_force.get("tool_calls")
                    if force_tool_calls:
                        # Executar as function calls forçadas
                        messages.append({
                            "role": "assistant",
                            "content": resultado_force.get("content"),
                            "tool_calls": force_tool_calls,
                        })

                        for tc in force_tool_calls:
                            fn_name = tc["function"]["name"]
                            fn_args = json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]

                            logger.info(f"SAFETY NET FC: {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:200]})")

                            resultado_fn = await executar_funcao(fn_name, fn_args, db, restaurante_id, bot_config, conversa)
                            function_calls_log.append({"nome": fn_name, "args": fn_args, "resultado": resultado_fn[:200]})

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": resultado_fn,
                            })

                        # Obter resposta final com resultado real do criar_pedido
                        resultado_final2 = await xai_llm.chat_completion(
                            messages=messages,
                            tools=TOOLS,
                            temperature=0.4,
                            max_tokens=1000,
                        )
                        total_tokens_in += resultado_final2.get("tokens_input", 0)
                        total_tokens_out += resultado_final2.get("tokens_output", 0)

                        if resultado_final2.get("content"):
                            resposta_final = resultado_final2["content"]
                            logger.info("SAFETY NET: criar_pedido forçado com sucesso, resposta atualizada")

                except Exception as e:
                    logger.error(f"SAFETY NET erro: {e}", exc_info=True)
                    # Manter resposta original se safety net falhar

        # 9. Delay humanizado (1-3 seg)
        delay = _calcular_delay_humano(len(resposta_final))
        await asyncio.sleep(delay)

        # 10. Decidir se envia áudio ou texto
        enviar_audio = _deve_enviar_audio(conversa, bot_config)

        # Resolver credenciais de envio: pool_entry (se ativo) ou bot_config
        _send_instance = pool_entry.evolution_instance if pool_entry else bot_config.evolution_instance
        _send_url = pool_entry.evolution_api_url if pool_entry else bot_config.evolution_api_url
        _send_key = pool_entry.evolution_api_key if pool_entry else bot_config.evolution_api_key

        envio_ok = False
        try:
            if enviar_audio and bot_config.tts_autonomo:
                # ÁUDIO: transformar português correto → dicção falada brasileira
                resposta_audio = _preparar_texto_para_audio(resposta_final)

                # Dual-mode TTS: Fish Audio (se configurado) → fallback xAI Grok
                audio_b64 = None
                tts_provider = getattr(bot_config, "tts_provider", "") or ""
                if tts_provider.lower() == "fish" and _fish_tts:
                    audio_b64 = await _fish_tts.gerar_audio(
                        resposta_audio,
                        voz=bot_config.voz_tts or "",
                        idioma=bot_config.idioma or "pt-BR",
                    )
                    if audio_b64:
                        logger.info("TTS via Fish Audio S2-Pro")
                if not audio_b64:
                    audio_b64 = await xai_tts.gerar_audio(resposta_audio, bot_config.voz_tts or "ara", bot_config.idioma or "pt-BR")
                if audio_b64:
                    try:
                        await evolution_client.enviar_presenca_conversa(
                            numero, _send_instance, _send_url, _send_key,
                            presenca="recording", delay_ms=3000,
                        )
                        await evolution_client.enviar_audio_ptt(
                            numero, audio_b64, _send_instance, _send_url, _send_key,
                            delay_ms=3000,
                        )
                    except Exception as audio_err:
                        logger.warning(f"Áudio falhou, enviando texto: {audio_err}")
                        await evolution_client.enviar_texto(
                            numero, resposta_final, _send_instance, _send_url, _send_key,
                            delay_ms=1500,
                        )
                else:
                    await evolution_client.enviar_texto(
                        numero, resposta_final, _send_instance, _send_url, _send_key,
                        delay_ms=1500,
                    )
            else:
                await evolution_client.enviar_texto(
                    numero, resposta_final, _send_instance, _send_url, _send_key,
                    delay_ms=1500,
                )
            envio_ok = True

            # Incrementar contador de msgs no pool entry
            if pool_entry:
                pool_entry.mensagens_enviadas = (pool_entry.mensagens_enviadas or 0) + 1
                pool_entry.ultima_mensagem_em = datetime.utcnow()

        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para {numero[:8]}***: {e}")
            # Retry com rotação automática se pool disponível
            if pool_entry:
                try:
                    new_entry = _phone_pool.rotate_number(db, restaurante_id, "envio_falhou", str(e))
                    if new_entry:
                        logger.info(f"Rotação por falha de envio → {new_entry.whatsapp_numero}")
                        await evolution_client.enviar_texto(
                            numero, resposta_final,
                            new_entry.evolution_instance,
                            new_entry.evolution_api_url,
                            new_entry.evolution_api_key,
                            delay_ms=1500,
                        )
                        conversa.numero_bot = new_entry.whatsapp_numero
                        conversa.phone_pool_id = new_entry.id
                        envio_ok = True
                except Exception as retry_err:
                    logger.error(f"Retry pós-rotação também falhou: {retry_err}")

        # 11. Registrar mensagem enviada (salva mesmo se envio falhou)
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

        try:
            db.commit()
        except Exception as commit_err:
            logger.error(f"Commit final falhou (msg/tokens): {commit_err}")
            try:
                db.rollback()
            except Exception:
                pass

        # 12. Notificar painel via WebSocket
        await _notificar_painel(restaurante_id, conversa, resposta_final, function_calls_log)

    except Exception as e:
        logger.error(f"Erro processando mensagem de {numero[:8]}***: {e}", exc_info=True)
    finally:
        db.close()
        lock.release()


def _identificar_restaurante(db: Session, instance: str) -> Optional[models.BotConfig]:
    """Identifica restaurante pela instância Evolution (provider='evolution').
    Procura primeiro em BotConfig, depois em BotPhonePool (rotação de números).
    Nota: provider='meta' usa processar_webhook_meta() com lookup por meta_phone_number_id."""
    config = db.query(models.BotConfig).filter(
        models.BotConfig.evolution_instance == instance,
        models.BotConfig.bot_ativo == True,
    ).first()
    if config:
        return config

    # Fallback: procurar em BotPhonePool (número pode ter sido rotacionado mas
    # BotConfig já aponta para outro — ou instance pertence ao pool)
    pool_entry = db.query(models.BotPhonePool).filter(
        models.BotPhonePool.evolution_instance == instance,
        models.BotPhonePool.status == "ativo",
    ).first()
    if pool_entry:
        config = db.query(models.BotConfig).filter(
            models.BotConfig.restaurante_id == pool_entry.restaurante_id,
            models.BotConfig.bot_ativo == True,
        ).first()
        if config:
            return config

    return None


def _get_or_create_conversa(
    db: Session,
    restaurante_id: int,
    telefone: str,
    pool_entry: Optional[models.BotPhonePool] = None,
    bot_config: Optional[models.BotConfig] = None,
) -> models.BotConversa:
    """Busca conversa ativa ou cria nova. Grava numero_bot e phone_pool_id."""
    # Buscar conversa ativa recente (últimas 2h)
    limite = datetime.utcnow() - timedelta(hours=2)
    conversa = db.query(models.BotConversa).filter(
        models.BotConversa.restaurante_id == restaurante_id,
        models.BotConversa.telefone == telefone,
        models.BotConversa.status == "ativa",
        models.BotConversa.atualizado_em >= limite,
    ).first()

    if conversa:
        # Atualizar numero_bot se mudou (rotação)
        numero_atual = pool_entry.whatsapp_numero if pool_entry else (bot_config.whatsapp_numero if bot_config else None)
        if numero_atual and conversa.numero_bot != numero_atual:
            conversa.numero_bot = numero_atual
            conversa.phone_pool_id = pool_entry.id if pool_entry else None
        return conversa

    # Criar nova conversa
    numero_bot = pool_entry.whatsapp_numero if pool_entry else (bot_config.whatsapp_numero if bot_config else None)
    conversa = models.BotConversa(
        restaurante_id=restaurante_id,
        telefone=telefone,
        status="ativa",
        numero_bot=numero_bot,
        phone_pool_id=pool_entry.id if pool_entry else None,
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


