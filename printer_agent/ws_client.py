# printer_agent/ws_client.py

"""
Cliente WebSocket com reconexão exponencial.
Conecta ao endpoint /ws/printer/{restaurante_id}?token={jwt}
"""

import json
import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger("printer_agent.ws")


class WebSocketClient:
    """Cliente WebSocket com backoff exponencial para o printer agent."""

    def __init__(
        self,
        server_url: str,
        restaurante_id: int,
        token: str,
        on_message: Callable[[dict], None],
        on_connect: Optional[Callable[[], None]] = None,
        on_disconnect: Optional[Callable[[], None]] = None,
    ):
        self.server_url = server_url
        self.restaurante_id = restaurante_id
        self.token = token
        self.on_message = on_message
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect

        self._ws = None
        self._running = False
        self._tentativas = 0
        self._max_backoff = 60  # segundos

    @property
    def url(self) -> str:
        return f"{self.server_url}/ws/printer/{self.restaurante_id}?token={self.token}"

    async def conectar(self):
        """Inicia loop de conexão com reconexão automática."""
        import websockets

        self._running = True
        while self._running:
            try:
                logger.info(f"Conectando ao WebSocket: {self.server_url}/ws/printer/{self.restaurante_id}")
                async with websockets.connect(
                    self.url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._tentativas = 0
                    logger.info("WebSocket conectado!")

                    if self.on_connect:
                        self.on_connect()

                    # Enviar status inicial
                    await self._enviar_status(online=True)

                    # Loop de recebimento
                    async for raw in ws:
                        try:
                            msg = json.loads(raw)
                            logger.debug(f"WS recebido: {msg.get('tipo', 'unknown')}")
                            self.on_message(msg)
                        except json.JSONDecodeError:
                            logger.warning(f"Mensagem inválida recebida: {raw[:100]}")

            except Exception as e:
                logger.warning(f"WebSocket desconectado: {e}")
                self._ws = None
                if self.on_disconnect:
                    self.on_disconnect()

            if not self._running:
                break

            # Backoff exponencial
            delay = min(2 ** self._tentativas, self._max_backoff)
            self._tentativas += 1
            logger.info(f"Reconectando em {delay}s (tentativa {self._tentativas})")
            await asyncio.sleep(delay)

    async def _enviar_status(self, online: bool = True):
        """Envia status do agent para o backend."""
        if self._ws:
            try:
                await self._ws.send(json.dumps({
                    "tipo": "status",
                    "dados": {"online": online},
                }))
            except Exception as e:
                logger.warning(f"Erro ao enviar status: {e}")

    async def enviar_ack(self, pedido_id: int, success: bool, error: Optional[str] = None):
        """Envia confirmação de impressão."""
        if self._ws:
            try:
                msg = {
                    "tipo": "print_ack",
                    "dados": {
                        "pedido_id": pedido_id,
                        "success": success,
                    },
                }
                if error:
                    msg["dados"]["error"] = error
                await self._ws.send(json.dumps(msg))
            except Exception as e:
                logger.warning(f"Erro ao enviar ACK: {e}")

    async def desconectar(self):
        """Para o loop de conexão."""
        self._running = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
