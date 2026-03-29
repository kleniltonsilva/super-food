# bridge_agent/bridge_client.py

"""
Cliente REST para comunicação com o backend Derekh Food.
Envia textos interceptados para parsing e criação de pedidos.
"""

import hashlib
import logging
import requests
from typing import Optional, Set

from .text_extractor import extrair_texto

logger = logging.getLogger("bridge_agent.client")


class BridgeClient:
    """Cliente para a Bridge API do Derekh Food."""

    def __init__(self, server_url: str, token: str, codepage: str = "CP860", auto_criar: bool = False):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.codepage = codepage
        self.auto_criar = auto_criar
        self._textos_enviados: Set[str] = set()  # Hash de textos já enviados (anti-duplicata local)
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        })

    def processar_job(self, impressora: str, raw_bytes: bytes) -> Optional[dict]:
        """Pipeline completo: extrai texto → parse → (opcional) criar pedido."""
        try:
            # 1. Extrair texto dos bytes
            texto = extrair_texto(raw_bytes, self.codepage)
            if not texto or len(texto.strip()) < 10:
                logger.warning(f"Texto muito curto ({len(texto)} chars) — ignorando")
                return None

            # Detectar se é comanda do próprio Derekh Food (não enviar ao servidor)
            # Bypass para simulador no modo teste
            if not impressora.startswith("Simulador_") and self._is_derekh_print(texto):
                logger.info(f"[{impressora}] Comanda do Derekh Food detectada — ignorando")
                return {"status": "ignorado", "motivo": "comanda_derekh"}

            # Anti-duplicata local: se já enviou texto idêntico, ignora
            # (bypass para simulador no modo teste — cada simulação é única por design)
            texto_hash = hashlib.md5(texto.encode()).hexdigest()
            is_simulador = impressora.startswith("Simulador_")
            if not is_simulador and texto_hash in self._textos_enviados:
                logger.info(f"[{impressora}] Texto duplicado (reimpressão) — ignorando")
                return {"status": "duplicata_local", "fonte": "cache"}
            self._textos_enviados.add(texto_hash)

            # Limpar cache se ficar muito grande
            if len(self._textos_enviados) > 5000:
                self._textos_enviados.clear()

            logger.info(f"[{impressora}] Texto extraído ({len(texto)} chars)")

            # 2. Enviar para parsing
            resp = self.session.post(
                f"{self.server_url}/painel/bridge/parse",
                json={
                    "texto_bruto": texto,
                    "impressora_origem": impressora,
                },
                timeout=30,
            )

            if resp.status_code == 401:
                logger.error("Token expirado ou inválido — refaça o login")
                return None

            resp.raise_for_status()
            parse_result = resp.json()
            logger.info(
                f"[{impressora}] Parse OK — plataforma={parse_result.get('plataforma')}, "
                f"fonte={parse_result.get('fonte')}, confiança={parse_result.get('confianca')}"
            )

            # 3. Se auto_criar e parse bem-sucedido → criar pedido
            if self.auto_criar and parse_result.get("status") == "pendente" and parse_result.get("dados_parseados"):
                return self._criar_pedido(parse_result["id"], impressora)

            return parse_result

        except requests.ConnectionError:
            logger.error(f"Sem conexão com {self.server_url}")
            return None
        except requests.HTTPError as e:
            logger.error(f"Erro HTTP: {e.response.status_code} — {e.response.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Erro inesperado ao processar job: {e}")
            return None

    def _criar_pedido(self, intercepted_order_id: int, impressora: str) -> Optional[dict]:
        """Cria pedido a partir de um intercepted_order."""
        try:
            resp = self.session.post(
                f"{self.server_url}/painel/bridge/orders",
                json={"intercepted_order_id": intercepted_order_id},
                timeout=15,
            )
            resp.raise_for_status()
            result = resp.json()
            logger.info(
                f"[{impressora}] Pedido criado! comanda={result.get('comanda')}, "
                f"cliente={result.get('cliente_nome')}, valor=R${result.get('valor_total', 0):.2f}"
            )
            return result
        except Exception as e:
            logger.error(f"Erro ao criar pedido: {e}")
            return None

    @staticmethod
    def _is_derekh_print(texto: str) -> bool:
        """Detecta se o texto é uma comanda impressa pelo próprio Derekh Food.
        Evita que comandas do site/painel sejam re-interceptadas pelo Bridge."""
        texto_lower = texto.lower()
        # Marcadores que o Derekh Food coloca nas comandas
        marcadores = [
            "derekh food",
            "derekh_",
            "superfood-api",
            "pedido online - comanda",
            "www.derekhfood",
        ]
        # Se 2+ marcadores casam, é muito provável ser do Derekh
        hits = sum(1 for m in marcadores if m in texto_lower)
        if hits >= 1:
            return True
        # Padrão específico: "Comanda #XXX" + "Derekh" na mesma impressão
        if "comanda #" in texto_lower and any(m in texto_lower for m in ["derekh", "super food"]):
            return True
        return False

    def testar_conexao(self) -> bool:
        """Testa se consegue conectar ao servidor."""
        try:
            resp = self.session.get(
                f"{self.server_url}/auth/restaurante/me",
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False
