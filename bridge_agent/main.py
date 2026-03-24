# bridge_agent/main.py

"""
Derekh Food Bridge Agent — Orquestrador principal.
Intercepta impressões de plataformas externas (iFood, Rappi, etc.)
e cria pedidos no Derekh Food automaticamente.
"""

import logging
import sys
import os
import time
import threading
from datetime import datetime

from .config import load_config, get_log_dir, get_config_path
from .spooler_monitor import SpoolerMonitor, HAS_WIN32
from .bridge_client import BridgeClient

# Logging
log_dir = get_log_dir()
log_file = os.path.join(log_dir, f"bridge_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger("bridge_agent")


def main():
    """Ponto de entrada principal do Bridge Agent."""
    logger.info("=" * 50)
    logger.info("Derekh Food Bridge Agent — Iniciando")
    logger.info("=" * 50)

    # Carrega config
    config = load_config()

    if not config.get("token"):
        logger.error("Token não configurado. Execute a interface de configuração primeiro.")
        logger.info(f"Arquivo de config: {get_config_path()}")
        # Tenta abrir janela de config
        try:
            from .ui.config_window import abrir_config
            abrir_config()
        except Exception as e:
            logger.error(f"Erro ao abrir config: {e}")
        return

    if not config.get("impressoras_monitorar"):
        logger.error("Nenhuma impressora configurada para monitorar.")
        return

    # Cria cliente REST
    client = BridgeClient(
        server_url=config["server_url"],
        token=config["token"],
        codepage=config.get("codepage", "CP860"),
        auto_criar=config.get("auto_criar_pedido", False),
    )

    # Testa conexão
    logger.info(f"Testando conexão com {config['server_url']}...")
    if client.testar_conexao():
        logger.info("Conexão OK!")
    else:
        logger.warning("Falha na conexão — verifique token e URL. Continuando mesmo assim...")

    # Callback quando um job é capturado
    def on_job_captured(printer_name: str, raw_bytes: bytes):
        logger.info(f"Job capturado de [{printer_name}] — {len(raw_bytes)} bytes")
        result = client.processar_job(printer_name, raw_bytes)
        if result:
            logger.info(f"Resultado: {result.get('status', 'desconhecido')}")

    # Inicia monitor do spooler
    monitor = SpoolerMonitor(
        impressoras=config["impressoras_monitorar"],
        ignorar_prefixo=config.get("ignorar_prefixo", "Derekh_"),
        poll_interval=config.get("poll_interval", 2.0),
        on_job_captured=on_job_captured,
    )

    if not HAS_WIN32:
        logger.error("pywin32 não instalado — Bridge Agent requer Windows com pywin32")
        return

    monitor.start()
    logger.info(f"Monitorando {len(config['impressoras_monitorar'])} impressora(s):")
    for p in config["impressoras_monitorar"]:
        logger.info(f"  - {p}")
    logger.info("Pressione Ctrl+C para parar.")

    # Tenta iniciar system tray (se disponível)
    tray_thread = None
    try:
        from pystray import Icon, MenuItem, Menu
        from PIL import Image, ImageDraw

        def criar_icone():
            img = Image.new("RGB", (64, 64), "#1a1a2e")
            draw = ImageDraw.Draw(img)
            draw.rectangle([8, 8, 56, 56], fill="#e94560", outline="#0f3460", width=2)
            draw.text((18, 18), "DF", fill="white")
            return img

        def on_quit(icon, item):
            monitor.stop()
            icon.stop()

        def on_config(icon, item):
            try:
                from .ui.config_window import abrir_config
                threading.Thread(target=abrir_config, daemon=True).start()
            except Exception:
                pass

        icon = Icon(
            "DerekhBridge",
            criar_icone(),
            "Derekh Food Bridge",
            menu=Menu(
                MenuItem("Status: Monitorando", lambda: None, enabled=False),
                MenuItem("Configurações", on_config),
                MenuItem("Sair", on_quit),
            ),
        )

        tray_thread = threading.Thread(target=icon.run, daemon=True)
        tray_thread.start()
        logger.info("System tray iniciado")
    except ImportError:
        logger.info("pystray/Pillow não disponível — rodando sem system tray")

    # Loop principal
    try:
        while monitor.is_running:
            time.sleep(1)
            # Limpa histórico de jobs periodicamente
            monitor.limpar_historico()
    except KeyboardInterrupt:
        logger.info("Ctrl+C recebido — encerrando...")
        monitor.stop()

    logger.info("Bridge Agent encerrado")


if __name__ == "__main__":
    main()
