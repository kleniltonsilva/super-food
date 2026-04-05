# printer_agent/main.py

"""
Derekh Food — Agente de Impressão de Comandas
Entry point e orquestrador principal.

Fluxo:
1. Carrega config
2. Se não configurado → abre janela de config
3. Inicia system tray icon
4. Conecta WebSocket ao backend
5. Recebe pedidos → busca dados via REST → enfileira → imprime
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Garantir que imports relativos funcionem quando rodando como script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from printer_agent.config import load_config, save_config, is_configured, get_printer_for_setor, has_multiple_printers, get_app_dir
from printer_agent.api_client import ApiClient
from printer_agent.ws_client import WebSocketClient
from printer_agent.print_queue import PrintQueue
from printer_agent.print_formatter import format_full_receipt, format_sector_receipt
from printer_agent.print_driver import imprimir_raw, IMPRESSORA_VIRTUAL
import printer_agent.print_driver as print_driver_mod


# ─── Logging ────────────────────────────────────────
def setup_logging():
    log_dir = get_app_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Auto-delete logs > 30 dias
    for f in log_dir.iterdir():
        if f.suffix == ".log":
            try:
                age_days = (time.time() - f.stat().st_mtime) / 86400
                if age_days > 30:
                    f.unlink()
            except Exception:
                pass

    log_file = log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


logger = logging.getLogger("printer_agent")


class PrinterAgent:
    """Orquestrador principal do agente de impressão."""

    def __init__(self, modo_teste: bool = False, silent: bool = False):
        self.modo_teste = modo_teste
        self.silent = silent
        if modo_teste:
            print_driver_mod.MODO_TESTE = True
        self.config = load_config()
        self.queue = PrintQueue()
        self.api: ApiClient = None  # type: ignore
        self.ws: WebSocketClient = None  # type: ignore
        self._tray = None
        self._print_thread = None
        self._running = False

    def iniciar(self):
        """Ponto de entrada principal."""
        setup_logging()
        logger.info("═" * 50)
        if self.modo_teste:
            logger.info("Derekh Food — Agente de Impressão [MODO TESTE]")
            logger.info("Comandas serão salvas como .txt e abertas no Notepad")
        else:
            logger.info("Derekh Food — Agente de Impressão iniciado")
        logger.info("═" * 50)

        # Se não configurado, abrir config
        if not is_configured(self.config):
            logger.info("Primeira execução — abrindo configuração")
            self._abrir_config()
            self.config = load_config()
            if not is_configured(self.config):
                logger.error("Configuração cancelada — encerrando")
                return
        else:
            # Já configurado — perguntar se deseja reconfigurar (exceto no auto-start/silent)
            if not self.silent and self._perguntar_reconfigurar():
                logger.info("Usuário solicitou reconfiguração")
                self._abrir_config()
                self.config = load_config()
                if not is_configured(self.config):
                    logger.error("Reconfiguração cancelada/limpa — encerrando")
                    return

        # Em modo teste, auto-configurar impressora virtual se necessário
        if self.modo_teste:
            impressoras = self.config.get("impressoras", {})
            if not impressoras.get("geral"):
                logger.info("[MODO TESTE] Auto-configurando impressora virtual")
                self.config["impressoras"]["geral"] = IMPRESSORA_VIRTUAL
                save_config(self.config)

        # Iniciar API client
        self.api = ApiClient(self.config["server_url"], self.config["token"])

        # Verificar token
        if not self.api.check_token():
            logger.warning("Token expirado — abrindo configuração para relogin")
            self._abrir_config()
            self.config = load_config()
            if not is_configured(self.config):
                return
            self.api = ApiClient(self.config["server_url"], self.config["token"])

        # Iniciar thread de processamento da fila
        self._running = True
        self._print_thread = threading.Thread(target=self._processar_fila_loop, daemon=True)
        self._print_thread.start()

        # Iniciar tray icon em thread separada
        tray_thread = threading.Thread(target=self._iniciar_tray, daemon=True)
        tray_thread.start()

        # Iniciar WebSocket (bloqueante com asyncio)
        try:
            asyncio.run(self._iniciar_ws())
        except KeyboardInterrupt:
            logger.info("Encerrado pelo usuário")
        finally:
            self._running = False
            self.queue.close()
            if self._tray:
                self._tray.parar()

    def _abrir_config(self):
        """Abre janela de configuração."""
        from printer_agent.ui.config_window import ConfigWindow
        window = ConfigWindow(on_save=lambda cfg: None)
        window.mostrar()
        self.config = load_config()

    def _perguntar_reconfigurar(self) -> bool:
        """Mostra dialog perguntando se o usuário deseja reconfigurar.
        Retorna True se sim, False se quer continuar com a config atual."""
        try:
            import tkinter as tk
            from tkinter import messagebox

            rest_id = self.config.get("restaurante_id", "?")
            impressora_geral = self.config.get("impressoras", {}).get("geral") or "(nenhuma)"
            server = self.config.get("server_url", "?")

            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)

            resposta = messagebox.askyesno(
                "Derekh Food — Agente de Impressão",
                f"Já está configurado!\n\n"
                f"Restaurante ID: {rest_id}\n"
                f"Impressora: {impressora_geral}\n"
                f"Servidor: {server}\n\n"
                f"Deseja RECONFIGURAR?\n"
                f"(Clique 'Não' para continuar com a configuração atual)",
                default=messagebox.NO,
            )
            root.destroy()
            return bool(resposta)
        except Exception as e:
            logger.warning(f"Não foi possível mostrar dialog de reconfiguração: {e}")
            return False

    def _iniciar_tray(self):
        """Inicia system tray icon."""
        try:
            from printer_agent.ui.tray_icon import TrayIcon
            self._tray = TrayIcon(
                on_config=lambda: threading.Thread(target=self._abrir_config, daemon=True).start(),
                on_quit=self._encerrar,
                modo_teste=self.modo_teste,
            )
            self._tray.iniciar()
        except Exception as e:
            logger.warning(f"Tray icon não disponível: {e}")

    async def _iniciar_ws(self):
        """Inicia conexão WebSocket."""
        self.ws = WebSocketClient(
            server_url=self.config["server_url"],
            restaurante_id=self.config["restaurante_id"],
            token=self.config["token"],
            on_message=self._on_ws_message,
            on_connect=lambda: self._atualizar_tray("conectado"),
            on_disconnect=lambda: self._atualizar_tray("desconectado"),
        )
        await self.ws.conectar()

    def _on_ws_message(self, msg: dict):
        """Callback quando recebe mensagem do WebSocket."""
        tipo = msg.get("tipo")
        dados = msg.get("dados", {})

        if tipo == "imprimir_pedido":
            pedido_id = dados.get("pedido_id")
            if pedido_id:
                logger.info(f"Recebido pedido para impressão: #{pedido_id}")
                self._processar_pedido(pedido_id, reimpressao=False)

        elif tipo == "reimprimir_pedido":
            pedido_id = dados.get("pedido_id")
            if pedido_id:
                logger.info(f"Reimpressão solicitada: #{pedido_id}")
                self._processar_pedido(pedido_id, reimpressao=True)

    def _processar_pedido(self, pedido_id: int, reimpressao: bool = False):
        """Busca dados do pedido e enfileira para impressão."""
        try:
            # Buscar dados do pedido via REST
            data = self.api.get_print_data(pedido_id)
            if not data:
                logger.error(f"Não foi possível obter dados do pedido #{pedido_id}")
                self._enviar_ack(pedido_id, False, "Erro ao buscar dados do pedido")
                return

            largura = self.config.get("largura_mm", 80)
            codepage = self.config.get("codepage", "CP860")

            if has_multiple_printers(self.config):
                # Split por setor
                itens = data.get("itens", [])
                setores: dict = {}
                for item in itens:
                    setor = item.get("setor_impressao", "geral")
                    setores.setdefault(setor, []).append(item)

                for setor, setor_itens in setores.items():
                    printer = get_printer_for_setor(self.config, setor)
                    if not printer:
                        continue
                    formatted = format_sector_receipt(data, setor, setor_itens, largura, codepage)
                    self.queue.enqueue(pedido_id, printer, {
                        "raw_bytes_hex": formatted.hex(),
                        "doc_name": f"Pedido_{data.get('comanda', pedido_id)}_{setor}",
                    }, reimpressao=reimpressao)
            else:
                # Uma impressora para tudo
                printer = get_printer_for_setor(self.config, "geral")
                if not printer:
                    logger.error("Nenhuma impressora configurada")
                    self._enviar_ack(pedido_id, False, "Nenhuma impressora configurada")
                    return
                formatted = format_full_receipt(data, largura, codepage)
                self.queue.enqueue(pedido_id, printer, {
                    "raw_bytes_hex": formatted.hex(),
                    "doc_name": f"Pedido_{data.get('comanda', pedido_id)}",
                }, reimpressao=reimpressao)

        except Exception as e:
            logger.error(f"Erro ao processar pedido #{pedido_id}: {e}")
            self._enviar_ack(pedido_id, False, str(e))

    def _processar_fila_loop(self):
        """Thread que processa a fila de impressão continuamente."""
        while self._running:
            try:
                job = self.queue.get_next()
                if not job:
                    time.sleep(0.5)
                    continue

                self._atualizar_tray("imprimindo")
                self.queue.mark_printing(job["id"])

                dados = json.loads(job["dados_json"])
                raw_bytes = bytes.fromhex(dados.get("raw_bytes_hex", ""))
                doc_name_raw = dados.get("doc_name", "Comanda")
                doc_name = f"Derekh_{doc_name_raw}" if not doc_name_raw.startswith("Derekh_") else doc_name_raw
                printer_name = job["impressora"]

                # Imprimir N cópias
                copias = self.config.get("copias", 1)
                success = True
                for c in range(copias):
                    if not imprimir_raw(printer_name, raw_bytes, doc_name):
                        success = False
                        break

                if success:
                    self.queue.mark_done(job["id"], job["pedido_id"], printer_name)
                    self._enviar_ack(job["pedido_id"], True)
                    logger.info(f"Pedido #{job['pedido_id']} impresso com sucesso em {printer_name}")
                else:
                    self.queue.mark_failed(job["id"])
                    self._enviar_ack(job["pedido_id"], False, f"Falha ao imprimir em {printer_name}")

                self._atualizar_tray("conectado")

            except Exception as e:
                logger.error(f"Erro no loop de impressão: {e}")
                time.sleep(1)

    def _enviar_ack(self, pedido_id: int, success: bool, error: str = None):
        """Envia ACK de impressão via WebSocket."""
        if self.ws:
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.ws.enviar_ack(pedido_id, success, error))
                loop.close()
            except Exception as e:
                logger.warning(f"Erro ao enviar ACK: {e}")

    def _atualizar_tray(self, status: str):
        """Atualiza ícone do tray."""
        if self._tray:
            try:
                self._tray.atualizar_status(status)
            except Exception:
                pass

    def _encerrar(self):
        """Encerra o agente."""
        logger.info("Encerrando agente de impressão...")
        self._running = False
        if self.ws:
            asyncio.run(self.ws.desconectar())
        if self._tray:
            self._tray.parar()
        sys.exit(0)


def main():
    modo_teste = "--modo-teste" in sys.argv or "--test" in sys.argv
    silent = "--silent" in sys.argv or "--auto-start" in sys.argv
    if modo_teste:
        print("\n" + "=" * 50)
        print("  MODO TESTE ATIVADO")
        print("  Comandas serão salvas como .txt")
        print("  Não é necessário impressora térmica")
        print("=" * 50 + "\n")

    agent = PrinterAgent(modo_teste=modo_teste, silent=silent)
    agent.iniciar()


if __name__ == "__main__":
    main()
