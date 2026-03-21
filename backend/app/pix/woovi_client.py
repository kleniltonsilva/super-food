# backend/app/pix/woovi_client.py
"""
Cliente HTTP assincrono para a API Woovi/OpenPix.
Suporta sandbox e producao via WOOVI_ENVIRONMENT.

Auth: header Authorization com APP_ID (sem Bearer).
Split de pagamentos 100% para subconta do restaurante.
Saque parcial via vault workaround (API so suporta saque total).
"""

import os
import hmac
import hashlib
import logging
from typing import Optional

import httpx

logger = logging.getLogger("superfood.pix")

WOOVI_URLS = {
    "sandbox": "https://api.woovi-sandbox.com",
    "production": "https://api.openpix.com.br",
}


class WooviClient:
    """Client assincrono para API Woovi/OpenPix."""

    def __init__(self):
        self.app_id = os.getenv("WOOVI_APP_ID", "")
        env = os.getenv("WOOVI_ENVIRONMENT", "production")
        self.base_url = WOOVI_URLS.get(env, WOOVI_URLS["production"])
        self.webhook_secret = os.getenv("WOOVI_WEBHOOK_SECRET", "")
        self.vault_pix_key = os.getenv("WOOVI_VAULT_PIX_KEY", "")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def configured(self) -> bool:
        return bool(self.app_id)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": self.app_id,
                    "User-Agent": "derekh-food",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # --- Helpers --------------------------------------------------

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._get_client()
        resp = await client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            logger.error(f"Woovi {method} {path} -> {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            logger.error(f"Woovi {method} {path} -> resposta nao-JSON: {resp.text[:200]}")
            raise ValueError(f"Woovi retornou resposta nao-JSON (status {resp.status_code})")

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        return await self._request("POST", path, json=json_data)

    # --- Subcontas ------------------------------------------------

    async def criar_subconta(self, pix_key: str, name: str) -> dict:
        """POST /api/v1/subaccount - Cria subconta virtual para restaurante."""
        return await self._post("/api/v1/subaccount", {"pixKey": pix_key, "name": name})

    async def consultar_saldo(self, pix_key: str) -> dict:
        """GET /api/v1/subaccount/{pixKey} - Retorna saldo em centavos."""
        return await self._get(f"/api/v1/subaccount/{pix_key}")

    # --- Cobrancas ------------------------------------------------

    async def criar_cobranca(
        self,
        valor_centavos: int,
        correlation_id: str,
        pix_chave_restaurante: str,
        descricao: str = "",
    ) -> dict:
        """POST /api/v1/charge - Cobranca com split 100% para subconta do restaurante."""
        payload = {
            "correlationID": correlation_id,
            "value": valor_centavos,
            "comment": descricao or "Pedido Derekh Food",
            "splits": [
                {
                    "pixKey": pix_chave_restaurante,
                    "value": valor_centavos,
                    "splitType": "SPLIT_SUB_ACCOUNT",
                }
            ],
        }
        return await self._post("/api/v1/charge", payload)

    # --- Saques ---------------------------------------------------

    async def sacar_total(self, pix_key: str) -> dict:
        """POST /api/v1/subaccount/{pixKey}/withdraw - Saca saldo total da subconta."""
        return await self._post(f"/api/v1/subaccount/{pix_key}/withdraw")

    async def transferir(self, from_key: str, to_key: str, valor_centavos: int) -> dict:
        """POST /api/v1/subaccount/transfer - Transfere entre subcontas."""
        return await self._post(
            "/api/v1/subaccount/transfer",
            {
                "value": valor_centavos,
                "fromPixKey": from_key,
                "toPixKey": to_key,
            },
        )

    async def sacar_parcial(self, pix_key: str, valor_centavos: int, saldo_atual: int) -> dict:
        """
        Saque parcial via vault workaround.

        A API Woovi so suporta saque total. Para sacar um valor parcial:
        1. Transferir excedente para subconta vault (cofre Derekh)
        2. Sacar tudo (agora so tem o valor desejado)
        3. Devolver excedente do vault para a subconta original
        """
        if not self.vault_pix_key:
            raise ValueError("WOOVI_VAULT_PIX_KEY nao configurado para saque parcial")

        excedente = saldo_atual - valor_centavos
        if excedente <= 0:
            # Saque total - sem necessidade de vault
            return await self.sacar_total(pix_key)

        # 1. Transferir excedente para vault
        await self.transferir(pix_key, self.vault_pix_key, excedente)
        try:
            # 2. Sacar tudo (agora so tem o valor desejado)
            result = await self.sacar_total(pix_key)
            # 3. Devolver excedente do vault
            await self.transferir(self.vault_pix_key, pix_key, excedente)
            return result
        except Exception as e:
            # Se falhou, devolver excedente de volta
            try:
                await self.transferir(self.vault_pix_key, pix_key, excedente)
            except Exception:
                logger.error(
                    f"CRITICO: falha ao devolver {excedente} centavos do vault para {pix_key}"
                )
            raise e

    # --- Webhook --------------------------------------------------

    def validar_webhook(self, payload: bytes, signature: str) -> bool:
        """Valida HMAC-SHA256 do webhook Woovi."""
        if not self.webhook_secret:
            return True  # Sem secret configurado, aceita tudo (dev)
        expected = hmac.new(
            self.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


# Singleton
woovi_client = WooviClient()
