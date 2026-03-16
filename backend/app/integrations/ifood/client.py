"""
Cliente iFood — Merchant API v2.
OAuth2 client_credentials (plataforma) + authorization_code (restaurante) + polling de eventos a cada 30s.

Fluxo de autorização:
1. Plataforma gera userCode via POST /authentication/v1.0/oauth/userCode
2. Restaurante digita userCode no Portal do Parceiro iFood
3. Plataforma faz polling com authorizationCodeVerifier
4. Quando autorizado, troca por access_token + refresh_token via authorization_code grant
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import httpx

from ..base import MarketplaceClient
from .mapper import ifood_order_to_pedido
from .status_machine import (
    DEREKH_TO_IFOOD,
    IFOOD_TO_DEREKH,
)

logger = logging.getLogger(__name__)

IFOOD_API_BASE = "https://merchant-api.ifood.com.br"
IFOOD_AUTH_URL = f"{IFOOD_API_BASE}/authentication/v1.0/oauth/token"
IFOOD_USER_CODE_URL = f"{IFOOD_API_BASE}/authentication/v1.0/oauth/userCode"
IFOOD_EVENTS_URL = f"{IFOOD_API_BASE}/order/v1.0/events:polling"
IFOOD_ACK_URL = f"{IFOOD_API_BASE}/order/v1.0/events/acknowledgment"
IFOOD_ORDER_URL = f"{IFOOD_API_BASE}/order/v1.0/orders"


class IFoodClient(MarketplaceClient):
    """Cliente para integração com iFood Merchant API."""

    marketplace_name = "ifood"

    def __init__(self, integracao_id: int, restaurante_id: int, config: Dict[str, Any]):
        super().__init__(integracao_id, restaurante_id, config)
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.merchant_id = config.get("merchant_id", "")
        self.access_token = config.get("access_token")
        self.token_expires_at = config.get("token_expires_at")
        self._http: Optional[httpx.AsyncClient] = None

    async def start(self):
        self._running = True
        self._http = httpx.AsyncClient(timeout=30)
        self._log("info", "iFood client iniciado")

    async def stop(self):
        self._running = False
        if self._http:
            await self._http.aclose()
            self._http = None
        self._log("info", "iFood client parado")

    async def authenticate(self) -> bool:
        """Autenticar via refresh_token (merchant) ou client_credentials (plataforma)."""
        if not self.client_id or not self.client_secret:
            self._log("error", "client_id ou client_secret não configurados")
            return False

        if not self._http:
            self._http = httpx.AsyncClient(timeout=30)

        # Verificar se token ainda é válido
        if self.access_token and self.token_expires_at:
            if isinstance(self.token_expires_at, str):
                self.token_expires_at = datetime.fromisoformat(self.token_expires_at)
            if datetime.utcnow() < self.token_expires_at - timedelta(minutes=5):
                self._log("debug", "Token ainda válido, reutilizando")
                return True

        # Se tem refresh_token, usar refresh_token grant (token de merchant — acesso completo)
        if self.config.get("refresh_token"):
            if await self._refresh_merchant_token():
                return True
            # Se refresh falhou, tentar client_credentials como fallback

        # Fallback: client_credentials (token de plataforma — acesso limitado)
        return await self._authenticate_client_credentials()

    async def _refresh_merchant_token(self) -> bool:
        """Renovar token do merchant via refresh_token grant."""
        try:
            resp = await self._http.post(IFOOD_AUTH_URL, data={
                "grantType": "refresh_token",
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
                "refreshToken": self.config.get("refresh_token"),
            })

            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("accessToken")
                expires_in = data.get("expiresIn", 3600)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                # Atualizar refresh_token se retornar um novo
                if data.get("refreshToken"):
                    self.config["refresh_token"] = data["refreshToken"]

                await self._save_token(data)
                self._log("info", f"Token merchant renovado via refresh_token (expira em {expires_in}s)")
                return True
            else:
                self._log("warning", f"Falha refresh_token: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            self._log("error", f"Erro ao renovar token merchant: {e}")
            return False

    async def _authenticate_client_credentials(self) -> bool:
        """Autenticar via OAuth2 client_credentials (token de plataforma)."""
        try:
            resp = await self._http.post(IFOOD_AUTH_URL, data={
                "grantType": "client_credentials",
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
            })

            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data.get("accessToken")
                expires_in = data.get("expiresIn", 3600)
                self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

                await self._save_token(data)
                self._log("info", f"Autenticado via client_credentials (expira em {expires_in}s)")
                return True
            else:
                self._log("error", f"Falha auth client_credentials: {resp.status_code} - {resp.text}")
                return False

        except Exception as e:
            self._log("error", f"Erro ao autenticar client_credentials: {e}")
            return False

    async def _save_token(self, token_data: dict = None):
        """Persiste o token no banco de dados."""
        from ...database import SessionLocal
        from database import models
        db = SessionLocal()
        try:
            integ = db.query(models.IntegracaoMarketplace).filter(
                models.IntegracaoMarketplace.id == self.integracao_id
            ).first()
            if integ:
                integ.access_token = self.access_token
                integ.token_expires_at = self.token_expires_at
                # Persistir novo refresh_token se disponível
                if token_data and token_data.get("refreshToken"):
                    integ.refresh_token = token_data["refreshToken"]
                db.commit()
        except Exception as e:
            db.rollback()
            self._log("error", f"Erro ao salvar token: {e}")
        finally:
            db.close()

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def poll_orders(self) -> List[Dict[str, Any]]:
        """Buscar eventos pendentes via polling."""
        if not self._running or not self.access_token:
            return []

        # Re-autenticar se token expirado
        if self.token_expires_at:
            if isinstance(self.token_expires_at, str):
                self.token_expires_at = datetime.fromisoformat(self.token_expires_at)
            if datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5):
                auth_ok = await self.authenticate()
                if not auth_ok:
                    return []

        try:
            resp = await self._http.get(
                IFOOD_EVENTS_URL,
                headers=self._auth_headers(),
            )

            if resp.status_code == 200:
                events = resp.json()
                if events:
                    self._log("info", f"Recebidos {len(events)} eventos")
                return events if isinstance(events, list) else []
            elif resp.status_code == 204:
                # Sem eventos novos
                return []
            elif resp.status_code == 401:
                self._log("warning", "Token expirado, re-autenticando...")
                await self.authenticate()
                return []
            elif resp.status_code == 429:
                self._log("warning", "Rate limit atingido, aguardando...")
                await asyncio.sleep(10)
                return []
            else:
                self._log("error", f"Erro polling: {resp.status_code}")
                return []

        except Exception as e:
            self._log("error", f"Erro ao fazer polling: {e}")
            return []

    async def acknowledge_events(self, event_ids: List[str]) -> bool:
        """Confirmar recebimento de eventos no iFood."""
        if not event_ids:
            return True

        try:
            resp = await self._http.post(
                IFOOD_ACK_URL,
                headers=self._auth_headers(),
                json=[{"id": eid} for eid in event_ids],
            )
            if resp.status_code in (200, 202):
                self._log("debug", f"ACK de {len(event_ids)} eventos")
                return True
            else:
                self._log("error", f"Erro ACK: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            self._log("error", f"Erro ao enviar ACK: {e}")
            return False

    async def fetch_order_details(self, order_id: str) -> Optional[dict]:
        """Buscar detalhes completos de um pedido no iFood."""
        try:
            resp = await self._http.get(
                f"{IFOOD_ORDER_URL}/{order_id}",
                headers=self._auth_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
            else:
                self._log("error", f"Erro ao buscar pedido {order_id}: {resp.status_code}")
                return None
        except Exception as e:
            self._log("error", f"Erro ao buscar pedido: {e}")
            return None

    async def update_order_status(self, marketplace_order_id: str, new_status: str,
                                   reason: Optional[str] = None) -> bool:
        """Atualizar status de um pedido no iFood."""
        endpoint_map = {
            "CONFIRM": f"{IFOOD_ORDER_URL}/{marketplace_order_id}/confirm",
            "DISPATCH": f"{IFOOD_ORDER_URL}/{marketplace_order_id}/dispatch",
            "READY_TO_PICKUP": f"{IFOOD_ORDER_URL}/{marketplace_order_id}/readyToPickup",
            "CANCEL": f"{IFOOD_ORDER_URL}/{marketplace_order_id}/cancel",
        }

        url = endpoint_map.get(new_status)
        if not url:
            self._log("warning", f"Status iFood não mapeado: {new_status}")
            return False

        try:
            body = {}
            if new_status == "CANCEL" and reason:
                body["reason"] = reason
                body["cancellationCode"] = "501"  # Merchant-requested cancellation

            resp = await self._http.post(url, headers=self._auth_headers(), json=body)
            if resp.status_code in (200, 202):
                self._log("info", f"Status {new_status} enviado ao iFood para pedido {marketplace_order_id}")
                return True
            else:
                self._log("error", f"Erro ao enviar status {new_status}: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            self._log("error", f"Erro ao atualizar status: {e}")
            return False

    async def generate_user_code(self) -> Optional[Dict[str, Any]]:
        """Gerar userCode para fluxo de autorização do restaurante.
        Retorna: userCode, verificationUrl, verificationUrlComplete, authorizationCodeVerifier, expiresIn
        """
        if not self.client_id or not self.client_secret:
            self._log("error", "client_id ou client_secret não configurados para gerar userCode")
            return None

        if not self._http:
            self._http = httpx.AsyncClient(timeout=30)

        try:
            resp = await self._http.post(IFOOD_USER_CODE_URL, data={
                "clientId": self.client_id,
            })

            if resp.status_code == 200:
                data = resp.json()
                self._log("info", f"userCode gerado: {data.get('userCode')}")
                return data
            else:
                self._log("error", f"Falha ao gerar userCode: {resp.status_code} - {resp.text}")
                return None

        except Exception as e:
            self._log("error", f"Erro ao gerar userCode: {e}")
            return None

    async def exchange_authorization_code(self, user_code: str, authorization_code_verifier: str) -> Optional[Dict[str, Any]]:
        """Trocar userCode + authorizationCodeVerifier por access_token + refresh_token.
        No device flow do iFood, authorizationCode = userCode (código curto que o restaurante digita).
        Retorna: accessToken, refreshToken, expiresIn, merchantId (se disponível)
        """
        if not self.client_id or not self.client_secret:
            self._log("error", "client_id ou client_secret não configurados")
            return None

        if not self._http:
            self._http = httpx.AsyncClient(timeout=30)

        try:
            resp = await self._http.post(IFOOD_AUTH_URL, data={
                "grantType": "authorization_code",
                "clientId": self.client_id,
                "clientSecret": self.client_secret,
                "authorizationCode": user_code,
                "authorizationCodeVerifier": authorization_code_verifier,
            })

            if resp.status_code == 200:
                data = resp.json()
                self._log("info", "authorization_code trocado por token com sucesso")
                return data
            elif resp.status_code == 400:
                # Ainda não autorizado pelo restaurante
                return None
            else:
                self._log("debug", f"Troca authorization_code: {resp.status_code}")
                return None

        except Exception as e:
            self._log("error", f"Erro ao trocar authorization_code: {e}")
            return None

    async def confirm_order(self, order_id: str) -> bool:
        """Confirmar recebimento de um pedido no iFood."""
        return await self.update_order_status(order_id, "CONFIRM")

    def map_order_to_pedido(self, marketplace_order: Dict[str, Any]) -> Dict[str, Any]:
        """Converter pedido iFood → formato interno Derekh."""
        return ifood_order_to_pedido(marketplace_order, self.restaurante_id)

    def map_status_to_marketplace(self, derekh_status: str) -> Optional[str]:
        return DEREKH_TO_IFOOD.get(derekh_status)

    def map_status_from_marketplace(self, marketplace_status: str) -> Optional[str]:
        return IFOOD_TO_DEREKH.get(marketplace_status)
