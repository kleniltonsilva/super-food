# printer_agent/api_client.py

"""
Cliente REST para buscar dados de pedidos do backend.
Usa JWT do restaurante para autenticação.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("printer_agent.api")


class ApiClient:
    """Cliente HTTP para o backend Derekh Food."""

    def __init__(self, server_url: str, token: str):
        # Converte wss:// para https://
        self.base_url = server_url.replace("wss://", "https://").replace("ws://", "http://")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def get_print_data(self, pedido_id: int) -> Optional[dict]:
        """Busca dados completos do pedido para impressão."""
        try:
            url = f"{self.base_url}/painel/pedidos/{pedido_id}/print-data"
            resp = self.session.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 401:
                logger.error("Token expirado — necessário relogin")
                return None
            else:
                logger.error(f"Erro ao buscar print-data: {resp.status_code} {resp.text}")
                return None
        except requests.RequestException as e:
            logger.error(f"Erro de conexão ao buscar print-data: {e}")
            return None

    def login(self, email: str, senha: str) -> Optional[dict]:
        """Faz login e retorna {token, restaurante}."""
        try:
            url = f"{self.base_url}/auth/restaurante/login"
            resp = self.session.post(url, json={"email": email, "senha": senha}, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"Erro no login: {resp.status_code} {resp.text}")
                return None
        except requests.RequestException as e:
            logger.error(f"Erro de conexão no login: {e}")
            return None

    def check_token(self) -> bool:
        """Verifica se o token ainda é válido."""
        try:
            url = f"{self.base_url}/auth/restaurante/me"
            resp = self.session.get(url, timeout=10)
            return resp.status_code == 200
        except requests.RequestException:
            return False
