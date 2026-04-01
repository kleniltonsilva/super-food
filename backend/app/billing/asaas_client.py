# backend/app/billing/asaas_client.py
"""
Cliente HTTP assíncrono para a API do Asaas.
Suporta sandbox e produção via ASAAS_ENVIRONMENT.
"""

import os
import logging
from typing import Optional
import httpx

logger = logging.getLogger("superfood.billing")

ASAAS_URLS = {
    "sandbox": "https://api-sandbox.asaas.com/v3",
    "production": "https://api.asaas.com/v3",
}


class AsaasClient:
    """Client assíncrono para API Asaas v3."""

    def __init__(self):
        self.api_key = os.getenv("ASAAS_API_KEY", "")
        env = os.getenv("ASAAS_ENVIRONMENT", "sandbox")
        self.base_url = ASAAS_URLS.get(env, ASAAS_URLS["sandbox"])
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "access_token": self.api_key,
                    "User-Agent": "derekh-food",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ─── Helpers ────────────────────────────────────────────

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        client = await self._get_client()
        resp = await client.request(method, path, **kwargs)
        if resp.status_code >= 400:
            logger.error(f"Asaas {method} {path} → {resp.status_code}: {resp.text[:500]}")
            resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            logger.error(f"Asaas {method} {path} → resposta não-JSON: {resp.text[:200]}")
            raise ValueError(f"Asaas retornou resposta não-JSON (status {resp.status_code})")

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        return await self._request("GET", path, params=params)

    async def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        return await self._request("POST", path, json=json_data)

    async def _put(self, path: str, json_data: Optional[dict] = None) -> dict:
        return await self._request("PUT", path, json=json_data)

    async def _delete(self, path: str) -> dict:
        return await self._request("DELETE", path)

    # ─── Customers ──────────────────────────────────────────

    async def criar_cliente(self, name: str, cpf_cnpj: str, email: str = "", phone: str = "") -> dict:
        payload = {"name": name, "cpfCnpj": cpf_cnpj}
        if email:
            payload["email"] = email
        if phone:
            payload["mobilePhone"] = phone
        return await self._post("/customers", payload)

    async def atualizar_cliente(self, customer_id: str, **kwargs) -> dict:
        payload = {}
        mapping = {"name": "name", "cpf_cnpj": "cpfCnpj", "email": "email", "phone": "mobilePhone"}
        for key, asaas_key in mapping.items():
            if key in kwargs and kwargs[key]:
                payload[asaas_key] = kwargs[key]
        return await self._put(f"/customers/{customer_id}", payload)

    # ─── Subscriptions ──────────────────────────────────────

    async def criar_assinatura(
        self,
        customer_id: str,
        billing_type: str,
        value: float,
        cycle: str,
        next_due_date: str,
        description: str = "",
    ) -> dict:
        payload = {
            "customer": customer_id,
            "billingType": billing_type,
            "value": value,
            "cycle": cycle,
            "nextDueDate": next_due_date,
        }
        if description:
            payload["description"] = description
        return await self._post("/subscriptions", payload)

    async def atualizar_assinatura(self, sub_id: str, **kwargs) -> dict:
        payload = {}
        mapping = {
            "billing_type": "billingType",
            "value": "value",
            "cycle": "cycle",
            "next_due_date": "nextDueDate",
            "status": "status",
        }
        for key, asaas_key in mapping.items():
            if key in kwargs and kwargs[key] is not None:
                payload[asaas_key] = kwargs[key]
        return await self._put(f"/subscriptions/{sub_id}", payload)

    async def cancelar_assinatura(self, sub_id: str) -> dict:
        return await self._delete(f"/subscriptions/{sub_id}")

    async def listar_pagamentos_assinatura(self, sub_id: str) -> dict:
        return await self._get(f"/subscriptions/{sub_id}/payments")

    # ─── Payments ───────────────────────────────────────────

    async def criar_cobranca_avulsa(
        self,
        customer_id: str,
        value: float,
        due_date: str,
        description: str = "",
        external_reference: str = "",
    ) -> dict:
        """Cria cobrança avulsa (PIX + Boleto) — POST /payments.
        billingType UNDEFINED permite PIX ou Boleto automaticamente."""
        payload = {
            "customer": customer_id,
            "billingType": "UNDEFINED",
            "value": value,
            "dueDate": due_date,
        }
        if description:
            payload["description"] = description
        if external_reference:
            payload["externalReference"] = external_reference
        return await self._post("/payments", payload)

    async def cancelar_cobranca(self, payment_id: str) -> dict:
        """Cancela/deleta cobrança avulsa — DELETE /payments/{id}."""
        return await self._delete(f"/payments/{payment_id}")

    async def get_pagamento(self, payment_id: str) -> dict:
        return await self._get(f"/payments/{payment_id}")

    async def get_pix_qr_code(self, payment_id: str) -> dict:
        return await self._get(f"/payments/{payment_id}/pixQrCode")

    async def listar_pagamentos(self, customer_id: str, status: Optional[str] = None) -> dict:
        params = {"customer": customer_id}
        if status:
            params["status"] = status
        return await self._get("/payments", params=params)


# Singleton
asaas_client = AsaasClient()
