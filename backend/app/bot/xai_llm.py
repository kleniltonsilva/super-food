"""
xAI Grok LLM — Chat completions com function calling.
Modelo: grok-3-fast (rápido, barato, bom em português).
"""
import httpx
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger("superfood.bot.llm")

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
MODELO_PADRAO = "grok-3-fast"


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    model: str = MODELO_PADRAO,
    temperature: float = 0.6,
    max_tokens: int = 400,
) -> dict:
    """Chama xAI Grok com function calling.

    Args:
        messages: Lista de mensagens [{role, content}]
        tools: Definições de ferramentas para function calling
        model: Modelo a usar
        temperature: Criatividade (0.6 para precisão)
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
        payload["tool_call"] = "auto"

    headers = {
        "Authorization": f"Bearer {xai_key}",
        "Content-Type": "application/json",
    }

    inicio = time.time()
    try:
        async with httpx.AsyncClient(timeout=30) as client:
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

    except httpx.HTTPStatusError as e:
        logger.error(f"Erro LLM xAI {e.response.status_code}: {e.response.text[:200]}")
        return {"content": "Opa, me dá um segundo que tive um probleminha aqui. Já volto!", "tool_calls": None, "tokens_input": 0, "tokens_output": 0, "tempo_ms": 0}
    except Exception as e:
        logger.error(f"Erro LLM xAI: {e}")
        return {"content": "Opa, me dá um segundo que tive um probleminha aqui. Já volto!", "tool_calls": None, "tokens_input": 0, "tokens_output": 0, "tempo_ms": 0}
