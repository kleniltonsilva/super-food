# printer_agent/print_driver.py

"""
Driver de impressão para Windows via win32print (RAW mode).
Envia bytes ESC/POS diretamente para a impressora.
"""

import logging
import platform
from typing import List, Optional

logger = logging.getLogger("printer_agent.driver")


def listar_impressoras() -> List[str]:
    """Lista todas as impressoras instaladas no Windows."""
    if platform.system() != "Windows":
        logger.warning("Listagem de impressoras só funciona no Windows")
        return ["Impressora Teste (simulada)"]

    try:
        import win32print
        printers = []
        for flags, _, name, _ in win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        ):
            printers.append(name)
        return printers
    except ImportError:
        logger.error("pywin32 não instalado — execute: pip install pywin32")
        return []
    except Exception as e:
        logger.error(f"Erro ao listar impressoras: {e}")
        return []


def impressora_padrao() -> Optional[str]:
    """Retorna nome da impressora padrão do Windows."""
    if platform.system() != "Windows":
        return None
    try:
        import win32print
        return win32print.GetDefaultPrinter()
    except Exception:
        return None


def imprimir_raw(printer_name: str, data: bytes, doc_name: str = "Derekh_Comanda") -> bool:
    """Envia dados RAW para a impressora (ESC/POS direto).

    Args:
        printer_name: Nome da impressora Windows
        data: Bytes ESC/POS formatados
        doc_name: Nome do documento no spooler

    Returns:
        True se imprimiu com sucesso
    """
    if platform.system() != "Windows":
        # Modo debug: salva em arquivo
        logger.info(f"[DEBUG] Imprimiria {len(data)} bytes em '{printer_name}'")
        debug_path = f"/tmp/comanda_{doc_name}.bin"
        try:
            with open(debug_path, "wb") as f:
                f.write(data)
            logger.info(f"[DEBUG] Dados salvos em {debug_path}")
        except Exception:
            pass
        return True

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
