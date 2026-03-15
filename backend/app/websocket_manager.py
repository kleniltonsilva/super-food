# backend/app/websocket_manager.py

"""
WebSocket Manager com suporte a Redis Pub/Sub
Para multi-worker (Gunicorn) funcionar com WebSocket
Fallback: sem Redis, funciona como in-memory (single worker)

Suporta channel_prefix para isolar managers (admin vs printer).
"""

import json
import asyncio
import logging
import os
from typing import Dict, List
from fastapi.websockets import WebSocket

logger = logging.getLogger("superfood.websocket")


class ConnectionManager:
    """Manager in-memory (single worker) - mantido como fallback"""

    def __init__(self, channel_prefix: str = "ws:restaurante"):
        self.active_connections: Dict[int, List[WebSocket]] = {}
        self.channel_prefix = channel_prefix

    async def connect(self, websocket: WebSocket, restaurante_id: int):
        await websocket.accept()
        self.active_connections.setdefault(restaurante_id, []).append(websocket)
        logger.debug(f"WS conectado ({self.channel_prefix}): restaurante={restaurante_id}")

    def disconnect(self, websocket: WebSocket, restaurante_id: int):
        if restaurante_id in self.active_connections:
            try:
                self.active_connections[restaurante_id].remove(websocket)
            except ValueError:
                pass
        logger.debug(f"WS desconectado ({self.channel_prefix}): restaurante={restaurante_id}")

    async def broadcast(self, message: dict, restaurante_id: int):
        dead = []
        for ws in self.active_connections.get(restaurante_id, []):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.active_connections[restaurante_id].remove(ws)
            except (ValueError, KeyError):
                pass

    def has_connections(self, restaurante_id: int) -> bool:
        return bool(self.active_connections.get(restaurante_id))


class RedisConnectionManager(ConnectionManager):
    """Manager com Redis Pub/Sub para multi-worker"""

    def __init__(self, channel_prefix: str = "ws:restaurante"):
        super().__init__(channel_prefix)
        self._pubsub_task = None
        self._redis_available = False

    async def _setup_redis(self):
        """Inicializa subscriber Redis em background"""
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.info(f"WS Manager ({self.channel_prefix}): Redis nao configurado, usando in-memory")
            return

        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            await self._redis.ping()
            self._redis_available = True
            self._pubsub = self._redis.pubsub()
            logger.info(f"WS Manager ({self.channel_prefix}): Redis Pub/Sub ativo")
        except Exception as e:
            logger.warning(f"WS Manager ({self.channel_prefix}): Redis indisponivel ({e}), usando in-memory")
            self._redis_available = False

    async def start(self):
        """Inicia listener Redis Pub/Sub"""
        await self._setup_redis()
        if self._redis_available:
            self._pubsub_task = asyncio.create_task(self._listen_redis())

    async def stop(self):
        """Para listener"""
        if self._pubsub_task:
            self._pubsub_task.cancel()

    async def connect(self, websocket: WebSocket, restaurante_id: int):
        await super().connect(websocket, restaurante_id)
        if self._redis_available:
            channel = f"{self.channel_prefix}:{restaurante_id}"
            await self._pubsub.subscribe(channel)

    async def broadcast(self, message: dict, restaurante_id: int):
        # Envia para conexoes locais
        await super().broadcast(message, restaurante_id)

        # Publica no Redis para outros workers
        if self._redis_available:
            try:
                channel = f"{self.channel_prefix}:{restaurante_id}"
                await self._redis.publish(channel, json.dumps(message))
            except Exception as e:
                logger.warning(f"Redis publish erro: {e}")

    async def _listen_redis(self):
        """Loop que escuta mensagens de outros workers via Redis"""
        try:
            async for msg in self._pubsub.listen():
                if msg["type"] != "message":
                    continue
                try:
                    channel = msg["channel"]
                    # Extrai restaurante_id do channel "{prefix}:123"
                    parts = channel.rsplit(":", 1)
                    if len(parts) == 2:
                        rid = int(parts[1])
                        data = json.loads(msg["data"])
                        # Envia para conexoes locais deste worker
                        dead = []
                        for ws in self.active_connections.get(rid, []):
                            try:
                                await ws.send_text(json.dumps(data))
                            except Exception:
                                dead.append(ws)
                        for ws in dead:
                            try:
                                self.active_connections[rid].remove(ws)
                            except (ValueError, KeyError):
                                pass
                except Exception as e:
                    logger.warning(f"Redis subscribe erro: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Redis listener erro fatal: {e}")


def create_manager(channel_prefix: str = "ws:restaurante") -> ConnectionManager:
    """Factory: cria manager com Redis se disponivel"""
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return RedisConnectionManager(channel_prefix)
    return ConnectionManager(channel_prefix)
