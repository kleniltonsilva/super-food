# bridge_agent/spooler_monitor.py

"""
Monitor do Windows Print Spooler.
Detecta novos jobs de impressão e captura os bytes brutos.
Requer pywin32 no Windows.
"""

import threading
import time
import logging
from typing import Callable, Set, List, Optional

logger = logging.getLogger("bridge_agent.spooler")

try:
    import win32print
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False
    logger.warning("pywin32 não disponível — monitor de spooler desabilitado (apenas Windows)")


class SpoolerMonitor:
    """Monitora o spooler de impressão do Windows por polling."""

    def __init__(
        self,
        impressoras: List[str],
        ignorar_prefixo: str = "Derekh_",
        poll_interval: float = 2.0,
        on_job_captured: Optional[Callable[[str, bytes], None]] = None,
    ):
        self.impressoras = impressoras
        self.ignorar_prefixo = ignorar_prefixo
        self.poll_interval = poll_interval
        self.on_job_captured = on_job_captured
        self._seen_jobs: Set[str] = set()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia o monitor em thread daemon."""
        if not HAS_WIN32:
            logger.error("Não é possível iniciar monitor — pywin32 não instalado")
            return

        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(f"Monitor iniciado — {len(self.impressoras)} impressora(s)")

    def stop(self):
        """Para o monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Monitor parado")

    def _poll_loop(self):
        """Loop principal de polling do spooler."""
        while self._running:
            try:
                for printer_name in self.impressoras:
                    self._check_printer(printer_name)
            except Exception as e:
                logger.error(f"Erro no poll loop: {e}")
            time.sleep(self.poll_interval)

    def _check_printer(self, printer_name: str):
        """Verifica jobs de uma impressora específica."""
        try:
            handle = win32print.OpenPrinter(printer_name)
            try:
                jobs = win32print.EnumJobs(handle, 0, 100, 1)
                for job in jobs:
                    job_id = job.get("JobId", 0)
                    doc_name = job.get("pDocument", "") or ""
                    job_key = f"{printer_name}:{job_id}"

                    # Já processado?
                    if job_key in self._seen_jobs:
                        continue

                    self._seen_jobs.add(job_key)

                    # Ignorar impressões do próprio Derekh (printer_agent)
                    if self.ignorar_prefixo and doc_name.startswith(self.ignorar_prefixo):
                        logger.debug(f"Ignorando job do Derekh: {doc_name}")
                        continue

                    logger.info(f"Novo job detectado: [{printer_name}] #{job_id} '{doc_name}'")

                    # Capturar bytes brutos
                    raw_bytes = self._read_job_data(handle, job_id)
                    if raw_bytes and self.on_job_captured:
                        self.on_job_captured(printer_name, raw_bytes)

            finally:
                win32print.ClosePrinter(handle)

        except Exception as e:
            logger.debug(f"Erro ao verificar impressora '{printer_name}': {e}")

    def _read_job_data(self, handle, job_id: int) -> Optional[bytes]:
        """Tenta ler os dados brutos de um job de impressão."""
        try:
            # ReadPrinter lê bytes do spool file
            data = win32print.ReadPrinter(handle, 65536)
            if data:
                return data
        except Exception as e:
            logger.debug(f"Não foi possível ler dados do job #{job_id}: {e}")

        return None

    @property
    def is_running(self) -> bool:
        return self._running

    def limpar_historico(self):
        """Limpa set de jobs vistos (para evitar crescimento infinito)."""
        if len(self._seen_jobs) > 10000:
            self._seen_jobs.clear()
            logger.info("Histórico de jobs limpo")


def listar_impressoras() -> List[str]:
    """Lista todas as impressoras instaladas no Windows."""
    if not HAS_WIN32:
        return []

    try:
        printers = win32print.EnumPrinters(
            win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
            None, 1
        )
        return [p[2] for p in printers]
    except Exception as e:
        logger.error(f"Erro ao listar impressoras: {e}")
        return []
