"""
Impressora Térmica Virtual para Windows — Derekh Food

Simula uma impressora térmica 80mm real no Windows, passando pelo spooler nativo.
Permite testar Bridge Agent e Printer Agent E2E sem hardware físico.

Uso:
    python -m virtual_printer server           # Inicia servidor TCP 9100
    python -m virtual_printer simulate         # Envia recibos pelo spooler
    python -m virtual_printer decode arq.bin   # Decodifica ESC/POS
    python -m virtual_printer list-printers    # Lista impressoras Windows
"""

__version__ = "1.0.0"
