# backend/app/rate_limit.py

"""
Rate Limiting - Derekh Food API
Sliding window via Redis INCR + EXPIRE
Sem Redis = sem rate limiting (gracioso)
"""

import os
import time
import logging
from typing import Optional, Tuple
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger("superfood.ratelimit")

# Limites por prefixo de rota (requests por minuto)
RATE_LIMITS = {
    "/auth/": 10,          # Anti brute-force
    "/site/": 200,         # Endpoints publicos
    "/carrinho/": 60,      # Operacoes carrinho
    "/api/upload/": 20,    # Uploads
    "_default": 100,       # Tudo mais
}


def _get_limit_for_path(path: str) -> int:
    """Retorna limite de requests/min para o path"""
    for prefix, limit in RATE_LIMITS.items():
        if prefix != "_default" and path.startswith(prefix):
            return limit
    return RATE_LIMITS["_default"]


def _get_client_key(request: Request) -> str:
    """Identifica cliente por IP (ou header X-Forwarded-For se atras de proxy)"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting com Redis"""

    async def dispatch(self, request: Request, call_next):
        # Ignora health checks e metricas
        path = request.url.path
        if path in ("/health", "/health/ready", "/health/live", "/metrics"):
            return await call_next(request)

        # Ignora WebSocket
        if path.startswith("/ws/"):
            return await call_next(request)

        # Tenta aplicar rate limit
        remaining, limit = await self._check_rate_limit(request)

        if remaining is not None and remaining < 0:
            logger.warning(f"Rate limit excedido: {_get_client_key(request)} em {path}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Muitas requisicoes. Tente novamente em 1 minuto."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": "60",
                },
            )

        response = await call_next(request)

        # Adiciona headers informativos
        if remaining is not None:
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(remaining, 0))

        return response

    async def _check_rate_limit(self, request: Request) -> Tuple[Optional[int], int]:
        """Verifica e incrementa contador. Retorna (remaining, limit) ou (None, 0) se sem Redis"""
        from .cache import get_redis

        r = get_redis()
        if not r:
            return None, 0  # Sem Redis = sem rate limiting

        path = request.url.path
        limit = _get_limit_for_path(path)
        client_key = _get_client_key(request)

        # Key: ratelimit:{ip}:{path_prefix}:{minuto}
        minute = int(time.time() / 60)
        # Simplifica path prefix para agrupamento
        path_prefix = path.split("/")[1] if "/" in path[1:] else path
        key = f"ratelimit:{client_key}:{path_prefix}:{minute}"

        try:
            current = r.incr(key)
            if current == 1:
                r.expire(key, 120)  # Expira em 2 min (margem)
            remaining = limit - current
            return remaining, limit
        except Exception as e:
            logger.warning(f"Rate limit Redis erro: {e}")
            return None, 0
