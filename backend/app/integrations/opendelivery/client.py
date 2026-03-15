"""
Cliente Open Delivery (padrão ABRASEL).
Suporta 99Food, Keeta, Rappi e outros marketplaces que seguem o padrão.
Recebe pedidos via webhook (não polling).
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import httpx

from ..base import MarketplaceClient
from .mapper import opendelivery_order_to_pedido

logger = logging.getLogger(__name__)

# Mapeamento de status Open Delivery ↔ Derekh
DEREKH_TO_OD = {
    "em_preparo": "CONFIRMED",
    "pronto": "READY_FOR_PICKUP",
    "em_entrega": "DISPATCHED",
    "entregue": "CONCLUDED",
    "cancelado": "CANCELLED",
}

OD_TO_DEREKH = {
    "CREATED": "pendente",
    "PLACED": "pendente",
    "CONFIRMED": "em_preparo",
    "READY_FOR_PICKUP": "pronto",
    "DISPATCHED": "em_entrega",
    "CONCLUDED": "entregue",
    "CANCELLED": "cancelado",
}


class OpenDeliveryClient(MarketplaceClient):
    """Cliente para marketplaces que usam o padrão Open Delivery (ABRASEL)."""

    def __init__(self, integracao_id: int, restaurante_id: int, config: Dict[str, Any],
                 marketplace_name: str = "opendelivery"):
        super().__init__(integracao_id, restaurante_id, config)
        self.marketplace_name = marketplace_name
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.merchant_id = config.get("merchant_id", "")
        self.access_token = config.get("access_token")
        self.token_expires_at = config.get("token_expires_at")
        self.api_base_url = config.get("config_json", {}).get("api_base_url", "")
        self.webhook_secret = config.get("config_json", {}).get("webhook_secret", "")
        self._http: Optional[httpx.AsyncClient] = None
        # Webhook queue: pedidos recebidos via webhook ficam aqui até serem polled
        self._pending_events: List[Dict[str, Any]] = []

    async def start(self):
        self._running = True
        self._http = httpx.AsyncClient(timeout=30)
        self._log("info", f"Open Delivery client ({self.marketplace_name}) iniciado")

    async def stop(self):
        self._running = False
        if self._http:
            await self._http.aclose()
            self._http = None
        self._log("info", f"Open Delivery client ({self.marketplace_name}) parado")

    async def authenticate(self) -> bool:
        """Autenticar via OAuth2 (se marketplace suportar)."""
        if not self.api_base_url:
            # Webhook-only mode — não precisa autenticar
            self._running = True
            return True

        if not self._http:
            self._http = httpx.AsyncClient(timeout=30)

        # Verificar token válido
        if self.access_token and self.token_expires_at:
            if isinstance(self.token_expires_at, str):
                self.token_expires_at = datetime.fromisoformat(self.token_expires_at)
            if datetime.utcnow() < self.token_expires_at - timedelta(minutes=5):
                return True

        try:
            resp = await self._http.post(
                f"{self.api_base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                self._log("info", "Autenticado com sucesso")
                return True
            else:
                self._log("error", f"Falha auth: {resp.status_code}")
                return False
        except Exception as e:
            self._log("error", f"Erro ao autenticar: {e}")
            return False

    async def poll_orders(self) -> List[Dict[str, Any]]:
        """Retorna eventos acumulados via webhook.
        Open Delivery usa webhooks, então os eventos são acumulados
        pelo endpoint webhook e consumidos aqui pelo manager.
        """
        events = list(self._pending_events)
        self._pending_events.clear()
        return events

    def receive_webhook_event(self, event: Dict[str, Any]):
        """Chamado pelo endpoint webhook quando recebe um evento."""
        self._pending_events.append(event)
        self._log("info", f"Webhook event recebido: {event.get('type', event.get('event_type', '?'))}")

    async def acknowledge_events(self, event_ids: List[str]) -> bool:
        """Open Delivery não precisa de ACK — webhook já é fire-and-forget."""
        return True

    async def fetch_order_details(self, order_id: str) -> Optional[dict]:
        """Buscar detalhes do pedido via API (se disponível)."""
        if not self.api_base_url or not self.access_token:
            return None

        try:
            resp = await self._http.get(
                f"{self.api_base_url}/orders/{order_id}",
                headers={"Authorization": f"Bearer {self.access_token}"},
            )
            if resp.status_code == 200:
                return resp.json()
            return None
        except Exception as e:
            self._log("error", f"Erro ao buscar pedido: {e}")
            return None

    async def update_order_status(self, marketplace_order_id: str, new_status: str,
                                   reason: Optional[str] = None) -> bool:
        """Enviar atualização de status ao marketplace."""
        if not self.api_base_url or not self.access_token:
            self._log("warning", "Sem API base URL — status não enviado")
            return False

        try:
            body = {"status": new_status}
            if reason:
                body["reason"] = reason

            resp = await self._http.put(
                f"{self.api_base_url}/orders/{marketplace_order_id}/status",
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if resp.status_code in (200, 202, 204):
                self._log("info", f"Status {new_status} enviado para pedido {marketplace_order_id}")
                return True
            else:
                self._log("error", f"Erro status update: {resp.status_code}")
                return False
        except Exception as e:
            self._log("error", f"Erro ao enviar status: {e}")
            return False

    def map_order_to_pedido(self, marketplace_order: Dict[str, Any]) -> Dict[str, Any]:
        return opendelivery_order_to_pedido(marketplace_order, self.restaurante_id, self.marketplace_name)

    def map_status_to_marketplace(self, derekh_status: str) -> Optional[str]:
        return DEREKH_TO_OD.get(derekh_status)

    def map_status_from_marketplace(self, marketplace_status: str) -> Optional[str]:
        return OD_TO_DEREKH.get(marketplace_status)

    @staticmethod
    def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
        """Verificar assinatura HMAC do webhook."""
        if not secret:
            return True  # Se não tem secret configurado, aceitar
        expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
