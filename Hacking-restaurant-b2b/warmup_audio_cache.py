"""
warmup_audio_cache.py — Pré-popular cache de áudio com respostas genéricas.

Gera 15+ respostas via LLM para perguntas frequentes, converte em áudio
via Fish Audio S2-Pro, classifica via audio_cache e salva no cache.

Uso:
    # Em produção (fly ssh):
    fly ssh console --app derekh-crm -C "python warmup_audio_cache.py"

    # Local (com .env e DATABASE_URL):
    python warmup_audio_cache.py

    # Dry-run (sem salvar no cache):
    python warmup_audio_cache.py --dry-run

    # Verificar cache após warmup:
    python warmup_audio_cache.py --stats
"""
import os
import sys
import time
import argparse
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("warmup_cache")

# Perguntas de warmup — 1 por intent_key relevante
WARMUP_PERGUNTAS = [
    {
        "intent_key": "saudacao_inicial",
        "pergunta": "Olá",
        "emocao": "abertura",
        "prompt_extra": "Responda a saudação de forma breve, se apresente como Ana da Derekh Food.",
    },
    {
        "intent_key": "teste_gratis",
        "pergunta": "Tem teste grátis?",
        "emocao": "trial",
        "prompt_extra": "Explique o teste grátis de 15 dias. NÃO mencione valores em R$.",
    },
    {
        "intent_key": "preco_planos",
        "pergunta": "Quanto custa o sistema?",
        "emocao": "preco",
        "prompt_extra": "Responda SEM mencionar valores. Diga apenas que tem 15 dias grátis e que depois o cliente escolhe o plano.",
    },
    {
        "intent_key": "como_contratar",
        "pergunta": "Como faço para contratar?",
        "emocao": "fechamento",
        "prompt_extra": "Explique que é só ativar o teste grátis de 15 dias. Peça nome do restaurante e cidade.",
    },
    {
        "intent_key": "funcionalidade_kds",
        "pergunta": "Como funciona a cozinha digital?",
        "emocao": "beneficio",
        "prompt_extra": "Explique o KDS com exemplo prático. Pedido aparece na tela da cozinha com timer.",
    },
    {
        "intent_key": "funcionalidade_garcom",
        "pergunta": "Tem app de garçom?",
        "emocao": "beneficio",
        "prompt_extra": "Explique o app garçom: comanda digital por mesa, sem papel, pedido vai direto pra cozinha.",
    },
    {
        "intent_key": "funcionalidade_motoboy",
        "pergunta": "Como funciona o app do motoboy?",
        "emocao": "beneficio",
        "prompt_extra": "Explique: app no celular do motoboy, recebe pedido, abre mapa com rota, vê ganhos do dia.",
    },
    {
        "intent_key": "funcionalidade_bridge",
        "pergunta": "Como captura pedido do iFood automaticamente?",
        "emocao": "empolgado",
        "prompt_extra": "Explique o Bridge: agente inteligente que captura cupom impresso do iFood/Rappi e transforma em pedido no sistema.",
    },
    {
        "intent_key": "diferencial_ifood",
        "pergunta": "Qual a diferença pra o iFood?",
        "emocao": "profissional",
        "prompt_extra": "Explique: iFood é vitrine, Derekh é marca própria. Complementam-se. Sem comissão no delivery próprio.",
    },
    {
        "intent_key": "diferencial_delivery_proprio",
        "pergunta": "Por que ter delivery próprio?",
        "emocao": "beneficio",
        "prompt_extra": "Fale da autonomia, sem comissão, fidelização do cliente, marca própria.",
    },
    {
        "intent_key": "explicacao_sistema",
        "pergunta": "O que é a Derekh Food?",
        "emocao": "apresentacao",
        "prompt_extra": "Explique em 2-3 frases: sistema completo de delivery para restaurantes. Site próprio, KDS, motoboy, tudo integrado.",
    },
    {
        "intent_key": "como_funciona_pedido",
        "pergunta": "Como o cliente faz pedido?",
        "emocao": "amigavel",
        "prompt_extra": "Explique: cliente acessa o site do restaurante, escolhe os produtos, faz o pedido e paga. Simples.",
    },
    {
        "intent_key": "formas_pagamento",
        "pergunta": "Aceita Pix?",
        "emocao": "amigavel",
        "prompt_extra": "Sim, aceita Pix, cartão na entrega, dinheiro. O cliente escolhe na hora do pedido.",
    },
    {
        "intent_key": "funcionalidade_geral",
        "pergunta": "O que o sistema faz?",
        "emocao": "apresentacao",
        "prompt_extra": "Resuma as funcionalidades principais com foco em benefícios práticos. Máximo 3 frases.",
    },
    {
        "intent_key": "integracao_ifood",
        "pergunta": "Integra com iFood?",
        "emocao": "profissional",
        "prompt_extra": "Sim, integra. Pedidos do iFood aparecem no mesmo painel que os do site próprio. Bridge captura automaticamente.",
    },
]


def _get_xai_key() -> str:
    key = os.environ.get("XAI_API_KEY", "")
    if not key:
        try:
            from crm.database import obter_configuracao
            key = obter_configuracao("xai_api_key") or ""
        except Exception:
            pass
    return key


def gerar_resposta_llm(pergunta: str, prompt_extra: str) -> str | None:
    """Gera resposta via Grok para a pergunta de warmup."""
    try:
        import httpx
    except ImportError:
        log.error("httpx não instalado")
        return None

    xai_key = _get_xai_key()
    if not xai_key:
        log.error("XAI_API_KEY não configurada")
        return None

    system = f"""Você é Ana, vendedora da Derekh Food. Responda a pergunta de forma breve e natural.
Máximo 2-3 frases curtas. Tom de WhatsApp, amigável mas profissional.
Português correto, sem abreviações. NUNCA mencione que é IA/bot.
{prompt_extra}"""

    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {xai_key}", "Content-Type": "application/json"},
            json={
                "model": "grok-3-mini-fast",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": pergunta},
                ],
                "max_tokens": 120,
                "temperature": 0.7,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        log.error(f"Erro LLM: {e}")
        return None


def gerar_audio(texto: str, emocao: str) -> bytes | None:
    """Gera áudio via Fish Audio S2-Pro."""
    try:
        from crm.fish_tts import gerar_audio_fish_async
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, gerar_audio_fish_async(texto, emocao)).result(timeout=35)
        else:
            return asyncio.run(gerar_audio_fish_async(texto, emocao))
    except Exception as e:
        log.error(f"Erro áudio: {e}")
        return None


def mostrar_stats():
    """Mostra estatísticas do cache."""
    try:
        from crm.audio_cache import stats_cache
        stats = stats_cache()
        log.info("=" * 50)
        log.info("ESTATÍSTICAS DO CACHE DE ÁUDIO")
        log.info(f"  Entradas ativas: {stats.get('ativos', 0)} / {stats.get('max_entradas', 500)}")
        log.info(f"  Total usos: {stats.get('total_usos', 0)}")
        log.info(f"  Tamanho: {stats.get('tamanho_total_mb', 0)} MB")
        log.info(f"  Duração média: {stats.get('duracao_media_s', 0)}s")
        if stats.get("top_intents"):
            log.info("  Top intents:")
            for ti in stats["top_intents"]:
                log.info(f"    {ti['intent']}: {ti['audios']} áudios, {ti['usos']} usos")
        log.info("=" * 50)
    except Exception as e:
        log.error(f"Erro ao obter stats: {e}")


def main():
    parser = argparse.ArgumentParser(description="Warmup do cache de áudio TTS")
    parser.add_argument("--dry-run", action="store_true",
                        help="Gerar respostas + áudio mas NÃO salvar no cache")
    parser.add_argument("--stats", action="store_true",
                        help="Apenas mostrar estatísticas do cache")
    parser.add_argument("--intent", default=None,
                        help="Gerar apenas para um intent_key específico")
    args = parser.parse_args()

    if args.stats:
        mostrar_stats()
        return 0

    log.info("=" * 60)
    log.info("WARMUP DO CACHE DE ÁUDIO — Fish Audio S2-Pro")
    log.info(f"Perguntas: {len(WARMUP_PERGUNTAS)} | Dry-run: {'SIM' if args.dry_run else 'NÃO'}")
    log.info("=" * 60)

    resultados = {"llm_ok": 0, "audio_ok": 0, "cache_ok": 0, "erros": 0}

    perguntas = WARMUP_PERGUNTAS
    if args.intent:
        perguntas = [p for p in perguntas if p["intent_key"] == args.intent]
        if not perguntas:
            log.error(f"Intent '{args.intent}' não encontrado")
            return 1

    for i, item in enumerate(perguntas, 1):
        intent = item["intent_key"]
        pergunta = item["pergunta"]
        emocao = item["emocao"]

        log.info(f"\n[{i}/{len(perguntas)}] intent={intent}")
        log.info(f"  Pergunta: {pergunta}")

        # 1. Gerar resposta LLM
        resposta = gerar_resposta_llm(pergunta, item["prompt_extra"])
        if not resposta:
            log.error(f"  FALHA LLM")
            resultados["erros"] += 1
            continue

        log.info(f"  Resposta: {resposta[:100]}...")
        resultados["llm_ok"] += 1

        # 2. Gerar áudio
        audio = gerar_audio(resposta, emocao)
        if not audio:
            log.error(f"  FALHA áudio")
            resultados["erros"] += 1
            continue

        kb = len(audio) / 1024
        log.info(f"  Áudio: {kb:.1f} KB")
        resultados["audio_ok"] += 1

        # 3. Classificar
        try:
            from crm.audio_cache import classificar_para_cache
            classificacao = classificar_para_cache(resposta)
            log.info(f"  Classificação: cacheavel={classificacao.get('cacheavel')}, "
                     f"intent={classificacao.get('intent_key')}")
        except ImportError:
            classificacao = {"cacheavel": True, "intent_key": intent}
            log.info(f"  Classificação: (forçada) intent={intent}")

        # 4. Salvar no cache
        if not args.dry_run:
            try:
                from crm.audio_cache import salvar_audio_cache
                cache_id = salvar_audio_cache(
                    texto=resposta,
                    audio_bytes=audio,
                    intent_key=intent,
                    emocao=emocao,
                    pergunta_exemplo=pergunta,
                )
                if cache_id:
                    log.info(f"  Cache salvo: id={cache_id}")
                    resultados["cache_ok"] += 1
                else:
                    log.warning(f"  Cache NÃO salvo (retornou None)")
            except Exception as e:
                log.error(f"  Erro salvar cache: {e}")
        else:
            log.info(f"  [DRY-RUN] Não salvou no cache")
            resultados["cache_ok"] += 1

        # Delay entre chamadas API
        time.sleep(1)

    log.info("\n" + "=" * 60)
    log.info("RESULTADO DO WARMUP:")
    log.info(f"  LLM geradas:  {resultados['llm_ok']}/{len(perguntas)}")
    log.info(f"  Áudios:       {resultados['audio_ok']}/{len(perguntas)}")
    log.info(f"  Cache salvos: {resultados['cache_ok']}/{len(perguntas)}")
    log.info(f"  Erros:        {resultados['erros']}")
    log.info("=" * 60)

    if not args.dry_run:
        log.info("\nVerificando cache final...")
        mostrar_stats()

    return 0 if resultados["erros"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
