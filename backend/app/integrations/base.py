"""
Base abstrata para clientes de marketplace.
Cada integração (iFood, Open Delivery) herda desta classe.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class MarketplaceClient(ABC):
    """Interface base para integração com marketplaces."""

    marketplace_name: str = ""

    def __init__(self, integracao_id: int, restaurante_id: int, config: Dict[str, Any]):
        self.integracao_id = integracao_id
        self.restaurante_id = restaurante_id
        self.config = config
        self._running = False

    @abstractmethod
    async def start(self):
        """Iniciar polling/listener do marketplace."""
        pass

    @abstractmethod
    async def stop(self):
        """Parar polling/listener."""
        pass

    @abstractmethod
    async def authenticate(self) -> bool:
        """Autenticar com o marketplace (OAuth2, API key, etc)."""
        pass

    @abstractmethod
    async def poll_orders(self) -> List[Dict[str, Any]]:
        """Buscar novos pedidos/eventos do marketplace."""
        pass

    @abstractmethod
    async def acknowledge_events(self, event_ids: List[str]) -> bool:
        """Confirmar recebimento de eventos."""
        pass

    @abstractmethod
    async def update_order_status(self, marketplace_order_id: str, new_status: str,
                                   reason: Optional[str] = None) -> bool:
        """Atualizar status de um pedido no marketplace."""
        pass

    @abstractmethod
    def map_order_to_pedido(self, marketplace_order: Dict[str, Any]) -> Dict[str, Any]:
        """Converter pedido do marketplace para o formato interno do Derekh Food."""
        pass

    @abstractmethod
    def map_status_to_marketplace(self, derekh_status: str) -> Optional[str]:
        """Converter status Derekh → status marketplace."""
        pass

    @abstractmethod
    def map_status_from_marketplace(self, marketplace_status: str) -> Optional[str]:
        """Converter status marketplace → status Derekh."""
        pass

    @property
    def is_running(self) -> bool:
        return self._running

    def _log(self, level: str, msg: str, **kwargs):
        prefix = f"[{self.marketplace_name}|rest:{self.restaurante_id}]"
        getattr(logger, level)(f"{prefix} {msg}", **kwargs)
