"""
xAI Grok LLM — Chat completions com function calling.
Modelo padrão: grok-3-mini-fast (econômico, bom em português).
Modelo premium (CRM Sales): grok-3-fast (+ Fish Audio S2 TTS).
"""
import asyncio
import httpx
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("superfood.bot.llm")

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
MODELO_PADRAO = "grok-3-mini-fast"


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = MODELO_PADRAO,
    temperature: float = 0.4,
    max_tokens: int = 1000,
    tool_choice: str | dict = "auto",
) -> dict:
    """Chama xAI Grok com function calling.

    Args:
        messages: Lista de mensagens [{role, content}]
        tools: Definições de ferramentas para function calling
        model: Modelo a usar
        temperature: Criatividade (0.4 para precisão em pedidos)
        max_tokens: Máximo de tokens na resposta

    Returns:
        {
            "content": str | None,
            "tool_calls": list | None,
            "tokens_input": int,
            "tokens_output": int,
            "tempo_ms": int,
        }
    """
    xai_key = os.environ.get("XAI_API_KEY", "")
    if not xai_key:
        logger.error("XAI_API_KEY não configurada")
        return {"content": "Desculpa, estou com um probleminha técnico. Já volto!", "tool_calls": None, "tokens_input": 0, "tokens_output": 0, "tempo_ms": 0}

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    headers = {
        "Authorization": f"Bearer {xai_key}",
        "Content-Type": "application/json",
    }

    inicio = time.time()
    max_retries = 2
    erro_fallback = {"content": "Opa, me dá um segundo que tive um probleminha aqui. Já volto!", "tool_calls": None, "tokens_input": 0, "tokens_output": 0, "tempo_ms": 0}

    for tentativa in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(XAI_CHAT_URL, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

            tempo_ms = int((time.time() - inicio) * 1000)
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            usage = data.get("usage", {})

            return {
                "content": message.get("content"),
                "tool_calls": message.get("tool_calls"),
                "tokens_input": usage.get("prompt_tokens", 0),
                "tokens_output": usage.get("completion_tokens", 0),
                "tempo_ms": tempo_ms,
            }

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"xAI timeout tentativa {tentativa+1}/{max_retries}: {e}")
            if tentativa < max_retries - 1:
                await asyncio.sleep(2)
                continue
            logger.error(f"xAI falhou após {max_retries} tentativas (timeout)")
            return erro_fallback
        except httpx.HTTPStatusError as e:
            logger.error(f"Erro LLM xAI {e.response.status_code}: {e.response.text[:200]}")
            return erro_fallback
        except Exception as e:
            logger.error(f"Erro LLM xAI: {e}")
            return erro_fallback

    return erro_fallback
