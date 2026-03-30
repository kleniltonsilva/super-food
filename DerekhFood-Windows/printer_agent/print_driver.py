# printer_agent/print_driver.py

"""
Driver de impressão para Windows via win32print (RAW mode).
Envia bytes ESC/POS diretamente para a impressora.
Suporta --modo-teste: impressora virtual + salva em arquivo + abre Notepad.
"""

import logging
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("printer_agent.driver")

# Flag global — ativada por main.py quando --modo-teste
MODO_TESTE = False

IMPRESSORA_VIRTUAL = "Impressora Virtual (Teste)"


def _get_test_prints_dir() -> Path:
    """Retorna diretório para salvar impressões de teste."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", os.path.expanduser("~")))
    else:
        base = Path.home() / ".config"
    d = base / "DerekhFood" / "test_prints"
    d.mkdir(parents=True, exist_ok=True)
    return d


def listar_impressoras() -> List[str]:
    """Lista todas as impressoras instaladas no Windows."""
    if MODO_TESTE:
        logger.info("[MODO TESTE] Retornando impressora virtual")
        return [IMPRESSORA_VIRTUAL]

    if platform.system() != "Windows":
        logger.warning("Listagem de impressoras só funciona no Windows")
        return [IMPRESSORA_VIRTUAL]

    try:
        import win32print
        printers = []
        for flags, _, name, _ in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        ):
            printers.append(name)
        if not printers:
            logger.warning("Nenhuma impressora encontrada — use --modo-teste para testar sem impressora")
        return printers
    except ImportError:
        logger.error("pywin32 não instalado — execute: pip install pywin32")
        return []
    except Exception as e:
        logger.error(f"Erro ao listar impressoras: {e}")
        return []


def impressora_padrao() -> Optional[str]:
    """Retorna nome da impressora padrão do Windows."""
    if MODO_TESTE:
        return IMPRESSORA_VIRTUAL
    if platform.system() != "Windows":
        return None
    try:
        import win32print
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def imprimir_raw(printer_name: str, data: bytes, doc_name: str = "Derekh_Comanda") -> bool:
    """Envia dados RAW para a impressora (ESC/POS direto).

    Em modo teste: salva bytes como .txt legível + abre com programa padrão.

    Args:
        printer_name: Nome da impressora Windows
        data: Bytes ESC/POS formatados
        doc_name: Nome do documento no spooler

    Returns:
        True se imprimiu com sucesso
    """
    if MODO_TESTE or platform.system() != "Windows":
        return _imprimir_teste(printer_name, data, doc_name)

    try:
        import win32print

        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(handle, 1, (doc_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, data)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)

        logger.info(f"Impresso com sucesso: {doc_name} em {printer_name} ({len(data)} bytes)")
        return True

    except ImportError:
        logger.error("pywin32 não instalado")
        return False
    except Exception as e:
        logger.error(f"Erro ao imprimir em '{printer_name}': {e}")
        return False


def _imprimir_teste(printer_name: str, data: bytes, doc_name: str) -> bool:
    """Salva a comanda como arquivo de texto legível e abre com programa padrão."""
    try:
        test_dir = _get_test_prints_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = doc_name.replace(" ", "_").replace("/", "-")

        # Salvar bytes brutos (.bin)
        bin_path = test_dir / f"{safe_name}_{timestamp}.bin"
        with open(bin_path, "wb") as f:
            f.write(data)

        # Converter para texto legível (strip ESC/POS commands)
        texto = _escpos_to_text(data)
        txt_path = test_dir / f"{safe_name}_{timestamp}.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"{'=' * 48}\n")
            f.write(f"  MODO TESTE — Impressão Simulada\n")
            f.write(f"  Impressora: {printer_name}\n")
            f.write(f"  Documento: {doc_name}\n")
            f.write(f"  Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"  Tamanho: {len(data)} bytes\n")
            f.write(f"{'=' * 48}\n\n")
            f.write(texto)
            f.write(f"\n\n{'=' * 48}\n")
            f.write(f"  Arquivo salvo em: {txt_path}\n")
            f.write(f"{'=' * 48}\n")

        logger.info(f"[MODO TESTE] Comanda salva em {txt_path} ({len(data)} bytes)")

        # Abrir com programa padrão (Notepad no Windows)
        if platform.system() == "Windows":
            os.startfile(str(txt_path))
        else:
            logger.info(f"[MODO TESTE] Abra manualmente: {txt_path}")

        return True

    except Exception as e:
        logger.error(f"[MODO TESTE] Erro ao salvar comanda: {e}")
        return False


def _escpos_to_text(data: bytes) -> str:
    """Converte bytes ESC/POS para texto legível (remove comandos de controle)."""
    result = bytearray()
    i = 0
    length = len(data)

    while i < length:
        b = data[i]

        # ESC commands
        if b == 0x1B:
            i += 2
            if i < length and data[i - 1] in (0x21, 0x45, 0x47, 0x4D, 0x61):
                i += 1
            continue

        # GS commands
        if b == 0x1D:
            i += 2
            if i < length:
                cmd = data[i - 1]
                if cmd in (0x21, 0x42, 0x48, 0x66, 0x68, 0x77):
                    i += 1
                elif cmd == 0x6B:
                    if i < length:
                        n = data[i]
                        i += n + 1
                elif cmd == 0x28:
                    if i + 1 < length:
                        pL = data[i]
                        pH = data[i + 1]
                        param_len = pL + (pH << 8)
                        i += 2 + param_len
                elif cmd == 0x56:  # GS V — cut
                    i += 1
            continue

        # FS / DLE
        if b in (0x1C, 0x10):
            i += 2
            continue

        # Controle (exceto newline, CR, tab)
        if b < 0x20 and b not in (0x0A, 0x0D, 0x09):
            i += 1
            continue

        result.append(b)
        i += 1

    # Decodificar com fallback
    for cp in ("CP860", "utf-8", "latin-1"):
        try:
            return bytes(result).decode(cp)
        except (UnicodeDecodeError, LookupError):
            continue
    return bytes(result).decode("ascii", errors="replace")
