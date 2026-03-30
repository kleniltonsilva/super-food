"""
Servidor TCP porta 9100 — simula o "hardware" da impressora térmica virtual.

Protocolo RAW (JetDirect): cada conexão TCP = 1 job de impressão.
O cliente (spooler Windows) conecta, envia todos os bytes, e desconecta.
O servidor decodifica ESC/POS e exibe no console + salva arquivos.
"""

import os
import socket
import threading
import time
from pathlib import Path

from virtual_printer.escpos_decoder import ESCPOSDecoder


# Box drawing chars para exibição no console
BOX_TOP_LEFT = "╔"
BOX_TOP_RIGHT = "╗"
BOX_BOTTOM_LEFT = "╚"
BOX_BOTTOM_RIGHT = "╝"
BOX_HORIZONTAL = "═"
BOX_VERTICAL = "║"
BOX_SEP_LEFT = "╟"
BOX_SEP_RIGHT = "╢"
BOX_SEP_LINE = "─"

RECEIPT_WIDTH = 48  # Colunas padrão impressora 80mm


class TCPPrinterServer:
    """Servidor TCP que simula uma impressora térmica na porta 9100."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 9100,
        output_dir: str = "output",
        codepage: str = "CP860",
        quiet: bool = False,
    ):
        self.host = host
        self.port = port
        self.output_dir = Path(output_dir)
        self.codepage = codepage
        self.quiet = quiet
        self.decoder = ESCPOSDecoder(codepage=codepage)
        self._job_counter = 0
        self._running = False
        self._server_socket: socket.socket | None = None
        self._lock = threading.Lock()

    def start(self):
        """Inicia o servidor TCP (bloqueante)."""
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.settimeout(1.0)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self._running = True

        print(f"\n{'=' * 60}")
        print(f"  IMPRESSORA TERMICA VIRTUAL — TCP Server")
        print(f"  Escutando em {self.host}:{self.port}")
        print(f"  Output: {self.output_dir.resolve()}")
        print(f"  Codepage: {self.codepage}")
        print(f"{'=' * 60}")
        print(f"  Aguardando jobs de impressao... (Ctrl+C para parar)\n")

        try:
            while self._running:
                try:
                    conn, addr = self._server_socket.accept()
                    thread = threading.Thread(
                        target=self._handle_connection,
                        args=(conn, addr),
                        daemon=True,
                    )
                    thread.start()
                except socket.timeout:
                    continue
        except KeyboardInterrupt:
            print("\n  Servidor encerrado pelo usuario.")
        finally:
            self.stop()

    def stop(self):
        """Para o servidor."""
        self._running = False
        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

    def _handle_connection(self, conn: socket.socket, addr: tuple):
        """Processa uma conexão (1 job de impressão)."""
        chunks = []
        conn.settimeout(5.0)

        try:
            while True:
                try:
                    data = conn.recv(65536)
                    if not data:
                        break
                    chunks.append(data)
                except socket.timeout:
                    break
        except ConnectionResetError:
            pass
        finally:
            conn.close()

        if not chunks:
            return

        raw_bytes = b"".join(chunks)

        with self._lock:
            self._job_counter += 1
            job_num = self._job_counter

        # Decodificar
        text_only = self.decoder.decode_text_only(raw_bytes)
        annotated = self.decoder.decode_annotated(raw_bytes)

        # Salvar arquivos
        bin_path = self.output_dir / f"job_{job_num:04d}.bin"
        txt_path = self.output_dir / f"job_{job_num:04d}.txt"
        ann_path = self.output_dir / f"job_{job_num:04d}_annotated.txt"

        bin_path.write_bytes(raw_bytes)
        txt_path.write_text(text_only, encoding="utf-8")
        ann_path.write_text(annotated, encoding="utf-8")

        # Exibir no console
        if not self.quiet:
            self._display_receipt(job_num, raw_bytes, text_only, addr)

    def _display_receipt(self, job_num: int, raw_bytes: bytes, text: str, addr: tuple):
        """Exibe o recibo formatado no console com box Unicode."""
        timestamp = time.strftime("%H:%M:%S")
        w = RECEIPT_WIDTH + 4  # +4 para margens dentro do box

        header = f" Job #{job_num:04d} | {len(raw_bytes)} bytes | {addr[0]}:{addr[1]} | {timestamp} "

        lines = []
        lines.append("")
        lines.append(f"  {BOX_TOP_LEFT}{BOX_HORIZONTAL * w}{BOX_TOP_RIGHT}")

        # Header
        padded_header = header.center(w)
        lines.append(f"  {BOX_VERTICAL}{padded_header}{BOX_VERTICAL}")
        lines.append(f"  {BOX_SEP_LEFT}{BOX_SEP_LINE * w}{BOX_SEP_RIGHT}")

        # Conteúdo do recibo
        for text_line in text.split("\n"):
            # Trunca linhas longas
            display = text_line[:w]
            padded = f"  {display}".ljust(w)
            lines.append(f"  {BOX_VERTICAL}{padded}{BOX_VERTICAL}")

        lines.append(f"  {BOX_BOTTOM_LEFT}{BOX_HORIZONTAL * w}{BOX_BOTTOM_RIGHT}")

        # Arquivos salvos
        lines.append(f"  -> Salvo: job_{job_num:04d}.bin + .txt + _annotated.txt")
        lines.append("")

        print("\n".join(lines))
