# printer_agent/print_queue.py

"""
Fila de impressão com SQLite para idempotência e retry.
Garante que pedidos não são impressos em duplicata.
"""

import sqlite3
import json
import time
import threading
import logging
from typing import Optional, List
from pathlib import Path

from .config import get_app_dir

logger = logging.getLogger("printer_agent.queue")

# Tempo em segundos para purgar registros antigos (7 dias)
PURGE_AGE_SECONDS = 7 * 24 * 3600
MAX_RETRIES = 3


class PrintQueue:
    """Fila de impressão persistente com SQLite."""

    def __init__(self):
        self._lock = threading.Lock()
        db_path = get_app_dir() / "print_queue.db"
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()
        self._purge_old()

    def _init_db(self):
        """Cria tabelas se não existirem."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS print_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                impressora TEXT NOT NULL,
                dados_json TEXT NOT NULL,
                status TEXT DEFAULT 'pendente',
                tentativas INTEGER DEFAULT 0,
                reimpressao INTEGER DEFAULT 0,
                criado_em REAL NOT NULL,
                UNIQUE(pedido_id, impressora) ON CONFLICT IGNORE
            );

            CREATE TABLE IF NOT EXISTS print_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pedido_id INTEGER NOT NULL,
                impressora TEXT NOT NULL,
                impresso_em REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status ON print_jobs(status);
            CREATE INDEX IF NOT EXISTS idx_history_pedido ON print_history(pedido_id, impressora);
        """)
        self._conn.commit()

    def _purge_old(self):
        """Remove registros com mais de 7 dias."""
        cutoff = time.time() - PURGE_AGE_SECONDS
        with self._lock:
            self._conn.execute("DELETE FROM print_jobs WHERE criado_em < ?", (cutoff,))
            self._conn.execute("DELETE FROM print_history WHERE impresso_em < ?", (cutoff,))
            self._conn.commit()
        logger.info("Registros antigos da fila purgados")

    def ja_impresso(self, pedido_id: int, impressora: str) -> bool:
        """Verifica se o pedido já foi impresso nesta impressora."""
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM print_history WHERE pedido_id = ? AND impressora = ?",
                (pedido_id, impressora)
            ).fetchone()
            return row is not None

    def enqueue(
        self,
        pedido_id: int,
        impressora: str,
        dados: dict,
        reimpressao: bool = False,
    ) -> bool:
        """Adiciona job na fila. Retorna True se adicionado, False se duplicata."""
        # Verificar idempotência (exceto reimpressão)
        if not reimpressao and self.ja_impresso(pedido_id, impressora):
            logger.info(f"Pedido {pedido_id} já impresso em {impressora} — ignorando")
            return False

        with self._lock:
            if reimpressao:
                # Remover job anterior se existir
                self._conn.execute(
                    "DELETE FROM print_jobs WHERE pedido_id = ? AND impressora = ?",
                    (pedido_id, impressora)
                )

            try:
                self._conn.execute(
                    "INSERT INTO print_jobs (pedido_id, impressora, dados_json, reimpressao, criado_em) VALUES (?, ?, ?, ?, ?)",
                    (pedido_id, impressora, json.dumps(dados), 1 if reimpressao else 0, time.time())
                )
                self._conn.commit()
                logger.info(f"Job enfileirado: pedido={pedido_id} impressora={impressora} reimpressao={reimpressao}")
                return True
            except sqlite3.IntegrityError:
                logger.info(f"Job duplicado ignorado: pedido={pedido_id} impressora={impressora}")
                return False

    def get_next(self) -> Optional[dict]:
        """Retorna o próximo job pendente (FIFO)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM print_jobs WHERE status = 'pendente' AND tentativas < ? ORDER BY id LIMIT 1",
                (MAX_RETRIES,)
            ).fetchone()
            if row:
                return dict(row)
            return None

    def mark_printing(self, job_id: int):
        """Marca job como em impressão."""
        with self._lock:
            self._conn.execute(
                "UPDATE print_jobs SET status = 'imprimindo', tentativas = tentativas + 1 WHERE id = ?",
                (job_id,)
            )
            self._conn.commit()

    def mark_done(self, job_id: int, pedido_id: int, impressora: str):
        """Marca job como concluído e registra no histórico."""
        with self._lock:
            self._conn.execute("DELETE FROM print_jobs WHERE id = ?", (job_id,))
            self._conn.execute(
                "INSERT INTO print_history (pedido_id, impressora, impresso_em) VALUES (?, ?, ?)",
                (pedido_id, impressora, time.time())
            )
            self._conn.commit()
        logger.info(f"Job concluído: pedido={pedido_id} impressora={impressora}")

    def mark_failed(self, job_id: int):
        """Marca job como falhado (volta para pendente para retry)."""
        with self._lock:
            row = self._conn.execute("SELECT tentativas FROM print_jobs WHERE id = ?", (job_id,)).fetchone()
            if row and row["tentativas"] >= MAX_RETRIES:
                self._conn.execute("UPDATE print_jobs SET status = 'falhou' WHERE id = ?", (job_id,))
                logger.error(f"Job {job_id} falhou após {MAX_RETRIES} tentativas")
            else:
                self._conn.execute("UPDATE print_jobs SET status = 'pendente' WHERE id = ?", (job_id,))
            self._conn.commit()

    def get_failed_jobs(self) -> List[dict]:
        """Retorna jobs que falharam definitivamente."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM print_jobs WHERE status = 'falhou' ORDER BY id"
            ).fetchall()
            return [dict(r) for r in rows]

    def close(self):
        """Fecha conexão SQLite."""
        self._conn.close()
