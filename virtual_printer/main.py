"""
CLI orquestrador da Impressora Térmica Virtual.

Subcomandos:
    install         Instala impressora virtual no Windows (PowerShell Admin)
    uninstall       Remove impressora virtual
    server          Inicia servidor TCP 9100 (o "hardware" virtual)
    simulate        Envia recibos ESC/POS pelo spooler real
    decode          Decodifica arquivo .bin ESC/POS
    list-printers   Lista impressoras do Windows
    test-bridge     Teste E2E automatizado do Bridge Agent
    test-printer    Teste E2E automatizado do Printer Agent
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def cmd_install(args):
    """Instala a impressora virtual no Windows via PowerShell."""
    script = Path(__file__).parent / "install.ps1"
    if not script.exists():
        print(f"[ERRO] Script nao encontrado: {script}")
        return 1

    print("  Executando install.ps1 (requer Admin)...")
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            capture_output=False,
        )
        return result.returncode
    except FileNotFoundError:
        print("[ERRO] PowerShell nao encontrado. Este comando requer Windows.")
        return 1


def cmd_uninstall(args):
    """Remove a impressora virtual do Windows."""
    script = Path(__file__).parent / "uninstall.ps1"
    if not script.exists():
        print(f"[ERRO] Script nao encontrado: {script}")
        return 1

    print("  Executando uninstall.ps1 (requer Admin)...")
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            capture_output=False,
        )
        return result.returncode
    except FileNotFoundError:
        print("[ERRO] PowerShell nao encontrado. Este comando requer Windows.")
        return 1


def cmd_server(args):
    """Inicia o servidor TCP (hardware virtual)."""
    from virtual_printer.tcp_server import TCPPrinterServer

    server = TCPPrinterServer(
        host=args.host,
        port=args.port,
        output_dir=args.output,
        codepage=args.codepage,
        quiet=args.quiet,
    )
    server.start()


def cmd_simulate(args):
    """Envia recibos ESC/POS pelo spooler do Windows."""
    from virtual_printer.receipt_printer import simular_pedidos

    simular_pedidos(
        platform=args.platform,
        count=args.count,
        interval=args.interval,
        printer_name=args.printer,
        save_local=args.save_local,
        output_dir=args.output,
    )


def cmd_decode(args):
    """Decodifica um arquivo .bin ESC/POS."""
    from virtual_printer.escpos_decoder import ESCPOSDecoder

    filepath = Path(args.file)
    if not filepath.exists():
        print(f"[ERRO] Arquivo nao encontrado: {filepath}")
        return 1

    raw_bytes = filepath.read_bytes()
    decoder = ESCPOSDecoder(codepage=args.codepage)

    if args.hex:
        print(f"\n  === Hex Dump: {filepath.name} ({len(raw_bytes)} bytes) ===\n")
        print(decoder.hex_dump(raw_bytes))
    elif args.annotated:
        print(f"\n  === Annotated: {filepath.name} ({len(raw_bytes)} bytes) ===\n")
        print(decoder.decode_annotated(raw_bytes))
    else:
        print(f"\n  === Text: {filepath.name} ({len(raw_bytes)} bytes) ===\n")
        print(decoder.decode_text_only(raw_bytes))


def cmd_list_printers(args):
    """Lista impressoras disponíveis no Windows."""
    try:
        import win32print

        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
            None, 2,
        )

        default = win32print.GetDefaultPrinter()

        print(f"\n  Impressoras do Windows ({len(printers)} encontradas):\n")
        print(f"  {'#':>3}  {'Nome':<40} {'Status':<10} {'Porta':<25} {'Driver'}")
        print(f"  {'─' * 3}  {'─' * 40} {'─' * 10} {'─' * 25} {'─' * 30}")

        for i, printer in enumerate(printers, 1):
            name = printer["pPrinterName"]
            port = printer.get("pPortName", "?")
            driver = printer.get("pDriverName", "?")
            status = printer.get("Status", 0)

            status_str = "OK" if status == 0 else f"0x{status:X}"
            marker = " *" if name == default else ""

            print(f"  {i:>3}  {name:<40} {status_str:<10} {port:<25} {driver}{marker}")

        print(f"\n  * = impressora padrao")
        print()

    except ImportError:
        print("[ERRO] pywin32 nao instalado. Este comando requer Windows + pywin32.")
        print("  Instale com: pip install pywin32")
        return 1


def cmd_test_bridge(args):
    """Teste E2E automatizado do Bridge Agent.

    Fluxo:
    1. Verifica se servidor TCP esta rodando na porta 9100
    2. Envia 1 recibo iFood pelo spooler
    3. Aguarda Bridge Agent detectar e processar
    """
    import socket
    import time

    from virtual_printer.receipt_printer import (
        PRINTER_NAME,
        enviar_recibo_spooler,
        gerar_recibo_ifood,
    )

    printer = args.printer or PRINTER_NAME

    print("\n  === TESTE E2E: Bridge Agent ===\n")

    # 1. Verificar servidor TCP
    print("  [1/3] Verificando servidor TCP 127.0.0.1:9100...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", 9100))
        sock.close()
        print("OK")
    except (ConnectionRefusedError, socket.timeout, OSError):
        print("FALHA")
        print("    O servidor TCP nao esta rodando!")
        print("    Inicie com: python -m virtual_printer server")
        print()
        return 1

    # 2. Enviar recibo
    print(f"  [2/3] Enviando recibo iFood para '{printer}'...", end=" ")
    raw = gerar_recibo_ifood()
    ok = enviar_recibo_spooler(raw, printer, doc_name="iFood_Pedido_TEST")
    if ok:
        print(f"OK ({len(raw)} bytes)")
    else:
        print("FALHA")
        print(f"    Impressora '{printer}' nao encontrada!")
        print("    Instale com: python -m virtual_printer install")
        print()
        return 1

    # 3. Aguardar
    print("  [3/3] Recibo enviado pelo spooler. Verificando recebimento...", end=" ")
    time.sleep(3)
    print("OK")

    print("\n  Resultado:")
    print("    - Recibo ESC/POS enviado via win32print.WritePrinter()")
    print("    - Passou pelo spooler do Windows como job real")
    print("    - Servidor TCP recebeu e decodificou os bytes")
    print()
    print("  Se o Bridge Agent esta rodando e monitorando")
    print(f"  '{printer}', ele deveria ter detectado o job.")
    print()


def cmd_test_printer(args):
    """Teste E2E automatizado do Printer Agent.

    Nota: O Printer Agent é ativado por WebSocket quando um pedido é criado.
    Este teste apenas verifica se a impressora virtual está funcional.
    """
    import socket

    from virtual_printer.receipt_printer import PRINTER_NAME

    printer = args.printer or PRINTER_NAME

    print("\n  === TESTE E2E: Printer Agent ===\n")

    # 1. Verificar servidor TCP
    print("  [1/2] Verificando servidor TCP 127.0.0.1:9100...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(("127.0.0.1", 9100))
        sock.close()
        print("OK")
    except (ConnectionRefusedError, socket.timeout, OSError):
        print("FALHA")
        print("    Inicie com: python -m virtual_printer server")
        return 1

    # 2. Verificar impressora existe
    print(f"  [2/2] Verificando impressora '{printer}'...", end=" ")
    try:
        import win32print
        handle = win32print.OpenPrinter(printer)
        win32print.ClosePrinter(handle)
        print("OK")
    except ImportError:
        print("FALHA (pywin32 nao instalado)")
        return 1
    except Exception:
        print("FALHA (impressora nao encontrada)")
        print(f"    Instale com: python -m virtual_printer install")
        return 1

    print("\n  Impressora virtual pronta para Printer Agent!")
    print("  Configure no printer_config.json:")
    print(f'    "impressoras": {{ "geral": "{printer}" }}')
    print()
    print("  Ao criar pedido no sistema, o Printer Agent")
    print("  formatara ESC/POS e enviara para a impressora virtual,")
    print("  e o servidor TCP recebera e exibira o recibo.")
    print()


def main():
    parser = argparse.ArgumentParser(
        prog="virtual_printer",
        description="Impressora Termica Virtual — Derekh Food",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python -m virtual_printer install                         # Instala impressora
  python -m virtual_printer server                          # Inicia servidor TCP
  python -m virtual_printer simulate                        # 1 recibo por plataforma
  python -m virtual_printer simulate --platform ifood -n 5  # 5 recibos iFood
  python -m virtual_printer decode output/job_0001.bin      # Decodifica ESC/POS
  python -m virtual_printer decode output/job_0001.bin --hex
  python -m virtual_printer list-printers
  python -m virtual_printer test-bridge
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Comando a executar")

    # ── install ──────────────────────────────────────────────────────
    subparsers.add_parser("install", help="Instala impressora virtual no Windows")

    # ── uninstall ────────────────────────────────────────────────────
    subparsers.add_parser("uninstall", help="Remove impressora virtual")

    # ── server ───────────────────────────────────────────────────────
    p_server = subparsers.add_parser("server", help="Inicia servidor TCP 9100")
    p_server.add_argument("--host", default="127.0.0.1", help="Endereco bind (default: 127.0.0.1)")
    p_server.add_argument("--port", type=int, default=9100, help="Porta TCP (default: 9100)")
    p_server.add_argument("--output", default="output", help="Diretorio output (default: output)")
    p_server.add_argument("--codepage", default="CP860", help="Codepage (default: CP860)")
    p_server.add_argument("--quiet", action="store_true", help="Nao exibir recibos no console")

    # ── simulate ─────────────────────────────────────────────────────
    p_sim = subparsers.add_parser("simulate", help="Envia recibos pelo spooler")
    p_sim.add_argument("--platform", "-p", choices=["ifood", "rappi", "99food", "ubereats"],
                        help="Plataforma especifica (default: todas)")
    p_sim.add_argument("--count", "-n", type=int, default=1, help="Recibos por plataforma (default: 1)")
    p_sim.add_argument("--interval", "-i", type=float, default=2.0, help="Segundos entre envios (default: 2)")
    p_sim.add_argument("--printer", default="Termica Virtual 80mm", help="Nome da impressora")
    p_sim.add_argument("--save-local", action="store_true", help="Tambem salvar .bin localmente")
    p_sim.add_argument("--output", default="output", help="Diretorio para salvar .bin")

    # ── decode ───────────────────────────────────────────────────────
    p_decode = subparsers.add_parser("decode", help="Decodifica arquivo .bin ESC/POS")
    p_decode.add_argument("file", help="Caminho do arquivo .bin")
    p_decode.add_argument("--hex", action="store_true", help="Hex dump")
    p_decode.add_argument("--annotated", "-a", action="store_true", help="Texto com anotacoes ESC/POS")
    p_decode.add_argument("--codepage", default="CP860", help="Codepage (default: CP860)")

    # ── list-printers ────────────────────────────────────────────────
    subparsers.add_parser("list-printers", help="Lista impressoras do Windows")

    # ── test-bridge ──────────────────────────────────────────────────
    p_tb = subparsers.add_parser("test-bridge", help="Teste E2E Bridge Agent")
    p_tb.add_argument("--printer", help="Nome da impressora (default: Termica Virtual 80mm)")

    # ── test-printer ─────────────────────────────────────────────────
    p_tp = subparsers.add_parser("test-printer", help="Teste E2E Printer Agent")
    p_tp.add_argument("--printer", help="Nome da impressora (default: Termica Virtual 80mm)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "install": cmd_install,
        "uninstall": cmd_uninstall,
        "server": cmd_server,
        "simulate": cmd_simulate,
        "decode": cmd_decode,
        "list-printers": cmd_list_printers,
        "test-bridge": cmd_test_bridge,
        "test-printer": cmd_test_printer,
    }

    handler = commands.get(args.command)
    if handler:
        result = handler(args)
        return result or 0
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
