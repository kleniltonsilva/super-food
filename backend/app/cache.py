# backend/app/cache.py

"""
Redis Cache - Derekh Food API
Best-effort: se Redis cair, app continua funcionando
"""

import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger("superfood.cache")

_redis_client = None
_redis_available = False


def get_redis():
    """Retorna cliente Redis ou None se indisponivel"""
    global _redis_client, _redis_available

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        _redis_available = False
        return None

    try:
        import redis
        _redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis conectado com sucesso")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis indisponivel: {e}")
        _redis_available = False
        return None


def cache_get(key: str) -> Optional[Any]:
    """Busca valor do cache. Retorna None se miss ou Redis indisponivel"""
    r = get_redis()
    if not r:
        return None
    try:
        value = r.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Cache get erro ({key}): {e}")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int = 300):
    """Grava valor no cache com TTL"""
    r = get_redis()
    if not r:
        return
    try:
        r.setex(key, ttl_seconds, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache set erro ({key}): {e}")


def cache_delete(key: str):
    """Remove uma chave do cache"""
    r = get_redis()
    if not r:
        return
    try:
        r.delete(key)
    except Exception as e:
        logger.warning(f"Cache delete erro ({key}): {e}")


def cache_delete_pattern(pattern: str):
    """Remove chaves por pattern (ex: 'cardapio:5:*')"""
    r = get_redis()
    if not r:
        return
    try:
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=100)
            if keys:
                r.delete(*keys)
            if cursor == 0:
                break
    except Exception as e:
        logger.warning(f"Cache delete pattern erro ({pattern}): {e}")


def invalidate_cardapio(restaurante_id: int):
    """Invalida todo cache do cardapio de um restaurante"""
    cache_delete_pattern(f"site:{restaurante_id}:*")
    cache_delete_pattern(f"cardapio:{restaurante_id}:*")
    logger.info(f"Cache invalidado: restaurante {restaurante_id}")


def invalidate_distancias(restaurante_id: int):
    """Invalida todo cache de distâncias de um restaurante (ex: mudou endereço ou config entrega)."""
    cache_delete_pattern(f"dist:{restaurante_id}:*")
    logger.info(f"Cache distâncias invalidado: restaurante {restaurante_id}")
