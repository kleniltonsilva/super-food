# bridge_agent/main.py

"""
Derekh Food Bridge Agent — Orquestrador principal.
Intercepta impressões de plataformas externas (iFood, Rappi, etc.)
e cria pedidos no Derekh Food automaticamente.

Modo teste (--modo-teste): simula recibos de plataformas sem impressora real.
"""

import logging
import sys
import os
import time
import threading
from datetime import datetime

from .config import load_config, save_config, get_log_dir, get_config_path
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


def _simular_plataforma(client: BridgeClient, plataforma: str):
    """Gera recibo simulado e envia ao backend para parsing."""
    try:
        from .simulador import gerar_recibo
        texto = gerar_recibo(plataforma)
        logger.info(f"[SIMULAÇÃO] Recibo {plataforma} gerado ({len(texto)} chars)")
        logger.info(f"[SIMULAÇÃO] Conteúdo:\n{texto}")

        # Converter texto para bytes (como se viesse da impressora)
        raw_bytes = texto.encode("CP860", errors="replace")

        # Enviar para o pipeline do client
        result = client.processar_job(f"Simulador_{plataforma}", raw_bytes)
        if result:
            status = result.get("status", "desconhecido")
            plat_detectada = result.get("plataforma", "?")
            logger.info(f"[SIMULAÇÃO] Resultado: status={status}, plataforma_detectada={plat_detectada}")

            # Mostrar popup com resultado (se tkinter disponível)
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                msg = (
                    f"Recibo {plataforma} enviado com sucesso!\n\n"
                    f"Status: {status}\n"
                    f"Plataforma detectada: {plat_detectada}\n"
                    f"Fonte: {result.get('fonte', '?')}\n"
                    f"Confiança: {result.get('confianca', '?')}"
                )
                if result.get("dados_parseados"):
                    dados = result["dados_parseados"]
                    msg += f"\n\nCliente: {dados.get('cliente_nome', '?')}"
                    msg += f"\nItens: {len(dados.get('itens', []))}"
                    msg += f"\nTotal: R${dados.get('valor_total', 0):.2f}"
                messagebox.showinfo(f"Simulação {plataforma}", msg)
                root.destroy()
            except Exception:
                pass
        else:
            logger.warning(f"[SIMULAÇÃO] Sem resultado do backend")
    except Exception as e:
        logger.error(f"[SIMULAÇÃO] Erro ao simular {plataforma}: {e}")


def main():
    """Ponto de entrada principal do Bridge Agent."""
    modo_teste = "--modo-teste" in sys.argv or "--test" in sys.argv

    logger.info("=" * 50)
    if modo_teste:
        logger.info("Derekh Food Bridge Agent — [MODO TESTE]")
        logger.info("Simule recibos pelo menu da bandeja do sistema")
    else:
        logger.info("Derekh Food Bridge Agent — Iniciando")
    logger.info("=" * 50)

    # Carrega config
    config = load_config()

    if not config.get("token"):
        logger.error("Token não configurado. Execute a interface de configuração primeiro.")
        logger.info(f"Arquivo de config: {get_config_path()}")
        try:
            from .ui.config_window import abrir_config
            abrir_config()
            config = load_config()
            if not config.get("token"):
                return
        except Exception as e:
            logger.error(f"Erro ao abrir config: {e}")
            return

    # Em modo normal, exigir impressoras configuradas
    if not modo_teste and not config.get("impressoras_monitorar"):
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

    # ─── MODO TESTE ──────────────────────────────────
    if modo_teste:
        print("\n" + "=" * 50)
        print("  MODO TESTE — Bridge Agent")
        print("  Use o menu na bandeja do sistema para")
        print("  simular recibos de iFood, Rappi, etc.")
        print("=" * 50 + "\n")

        _running_flag = [True]

        # System tray com simuladores
        try:
            from pystray import Icon, MenuItem, Menu
            from PIL import Image, ImageDraw

            def criar_icone():
                img = Image.new("RGB", (64, 64), "#0f3460")
                draw = ImageDraw.Draw(img)
                draw.rectangle([8, 8, 56, 56], fill="#e94560", outline="#4ecca3", width=2)
                draw.text((18, 18), "T", fill="white")
                return img

            def on_quit(icon, item):
                _running_flag[0] = False
                icon.stop()

            def on_config(icon, item):
                try:
                    from .ui.config_window import abrir_config
                    threading.Thread(target=abrir_config, daemon=True).start()
                except Exception:
                    pass

            # Criar menu items para cada plataforma
            def make_sim_callback(plat):
                def callback(icon, item):
                    threading.Thread(
                        target=_simular_plataforma,
                        args=(client, plat),
                        daemon=True,
                    ).start()
                return callback

            menu_items = [
                MenuItem("*** MODO TESTE ***", lambda: None, enabled=False),
                MenuItem("Conectado" if client.testar_conexao() else "Desconectado", lambda: None, enabled=False),
                Menu.SEPARATOR,
                MenuItem("Simular iFood", make_sim_callback("iFood")),
                MenuItem("Simular Rappi", make_sim_callback("Rappi")),
                MenuItem("Simular 99Food", make_sim_callback("99Food")),
                MenuItem("Simular Uber Eats", make_sim_callback("Uber Eats")),
                Menu.SEPARATOR,
                MenuItem("Configurações", on_config),
                Menu.SEPARATOR,
                MenuItem("Sair", on_quit),
            ]

            icon = Icon(
                "DerekhBridge",
                criar_icone(),
                "Derekh Food Bridge [TESTE]",
                menu=Menu(*menu_items),
            )

            logger.info("System tray iniciado — clique no ícone para simular plataformas")
            logger.info("Plataformas disponíveis: iFood, Rappi, 99Food, Uber Eats")

            # Rodar tray (bloqueante)
            icon.run()

        except ImportError:
            logger.info("pystray/Pillow não disponível — usando modo console")
            logger.info("Comandos disponíveis: 1=iFood  2=Rappi  3=99Food  4=UberEats  q=Sair")

            while _running_flag[0]:
                try:
                    choice = input("\nSimular qual plataforma? (1-4, q=sair): ").strip()
                    plats = {"1": "iFood", "2": "Rappi", "3": "99Food", "4": "Uber Eats"}
                    if choice == "q":
                        break
                    plat = plats.get(choice)
                    if plat:
                        _simular_plataforma(client, plat)
                    else:
                        print("Opção inválida. Use 1-4 ou q.")
                except (KeyboardInterrupt, EOFError):
                    break

        logger.info("Bridge Agent [TESTE] encerrado")
        return

    # ─── MODO NORMAL ─────────────────────────────────

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
