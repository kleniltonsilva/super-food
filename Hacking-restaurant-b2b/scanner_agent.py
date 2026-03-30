#!/usr/bin/env python3
"""
scanner_agent.py — Agent local que executa scan jobs pendentes via PostgreSQL direto.

Uso:
    export DATABASE_URL="postgresql://user:pass@localhost:15432/derekh_crm"
    python scanner_agent.py

Requer: fly proxy rodando (15432:5432) + Playwright instalado localmente.
"""
import asyncio
import os
import sys
import time
import signal
import traceback
from datetime import datetime, timedelta

# Garantir que o diretório raiz esteja no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_pg import (
    init_pg, get_conn, obter_scan_job, atualizar_scan_job, scan_log,
)

# ============================================================
# CONFIG
# ============================================================

POLL_INTERVAL = 10  # segundos entre polls
ORPHAN_TIMEOUT_HOURS = 2  # jobs 'executando' há mais de X horas = órfãos

# Cores para terminal
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_CYAN = "\033[96m"
C_DIM = "\033[90m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

_running = True


def _log(msg: str, color: str = C_DIM):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C_DIM}[{ts}]{C_RESET} {color}[AGENT]{C_RESET} {msg}")


# ============================================================
# POLL & CLAIM
# ============================================================

def poll_pendente() -> dict | None:
    """Busca o job pendente mais antigo."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM scan_jobs
            WHERE status = 'pendente'
            ORDER BY created_at ASC
            LIMIT 1
        """)
        row = cur.fetchone()
        return dict(row) if row else None


def claim_job(job_id: int) -> bool:
    """Tenta reivindicar o job (proteção contra race condition com outro agent)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE scan_jobs
            SET status = 'executando', started_at = NOW()
            WHERE id = %s AND status = 'pendente'
        """, (job_id,))
        conn.commit()
        return cur.rowcount > 0


def check_cancelled(job_id: int) -> bool:
    """Verifica se o job foi marcado para cancelamento."""
    job = obter_scan_job(job_id)
    return job is not None and job.get("status") in ("cancelando", "cancelado")


def recover_orphans():
    """Marca jobs 'executando' órfãos (sem agent) como 'erro'."""
    cutoff = datetime.now() - timedelta(hours=ORPHAN_TIMEOUT_HOURS)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, started_at FROM scan_jobs
            WHERE status = 'executando'
            AND started_at < %s
        """, (cutoff,))
        orphans = cur.fetchall()

    for orphan in orphans:
        job_id = orphan["id"]
        _log(f"Job #{job_id} órfão (executando há +{ORPHAN_TIMEOUT_HOURS}h) — marcando como erro", C_YELLOW)
        atualizar_scan_job(job_id, status="erro", finished_at=datetime.now())
        scan_log(job_id, "Agent reiniciado — scan interrompido (job órfão).", "error")


# ============================================================
# EXECUTAR JOB
# ============================================================

async def executar_job(job_id: int, cidades: list, etapas: list, headless: bool):
    """Executa o scan usando o código existente de crm/scanner.py."""
    _log(f"Executando job #{job_id}: {len(cidades)} cidade(s), etapas={etapas}", C_GREEN)
    scan_log(job_id, f"Scanner agent local iniciou execução.")

    try:
        from crm.scanner import executar_scan
        await executar_scan(job_id, cidades, etapas, headless)
    except asyncio.CancelledError:
        _log(f"Job #{job_id} cancelado.", C_YELLOW)
        atualizar_scan_job(job_id, status="cancelado", finished_at=datetime.now())
        scan_log(job_id, "Scan cancelado pelo usuário (via agent).", "warning")
    except Exception as e:
        tb = traceback.format_exc()
        _log(f"Job #{job_id} falhou: {e}", C_RED)
        atualizar_scan_job(job_id, status="erro", finished_at=datetime.now())
        scan_log(job_id, f"Agent erro: {e}\n{tb}", "error")

    # Verificar status final
    job = obter_scan_job(job_id)
    status_final = job["status"] if job else "desconhecido"
    _log(f"Job #{job_id} finalizado — status: {status_final}", C_CYAN)


# ============================================================
# MAIN LOOP
# ============================================================

async def main_loop():
    global _running

    _log(f"Scanner agent iniciado. Aguardando jobs...", C_GREEN)
    _log(f"Poll interval: {POLL_INTERVAL}s | DB: {os.environ.get('DATABASE_URL', '(default)')[:50]}...", C_DIM)

    # Recuperar jobs órfãos
    recover_orphans()

    while _running:
        try:
            job = poll_pendente()
            if job:
                job_id = job["id"]
                import json
                cidades = json.loads(job["cidades"]) if isinstance(job["cidades"], str) else job["cidades"]
                etapas = json.loads(job["etapas"]) if isinstance(job["etapas"], str) else job["etapas"]
                headless = job.get("headless", True)

                _log(f"Job #{job_id} encontrado! Cidades: {len(cidades)}, Etapas: {etapas}", C_CYAN)

                if claim_job(job_id):
                    _log(f"Job #{job_id} reivindicado com sucesso.", C_GREEN)
                    await executar_job(job_id, cidades, etapas, headless)
                else:
                    _log(f"Job #{job_id} já foi capturado por outro agent.", C_YELLOW)
            else:
                pass  # Silencioso quando não há jobs
        except KeyboardInterrupt:
            break
        except Exception as e:
            _log(f"Erro no loop: {e}", C_RED)

        # Sleep com verificação de _running para encerramento rápido
        for _ in range(POLL_INTERVAL):
            if not _running:
                break
            await asyncio.sleep(1)

    _log("Scanner agent encerrado.", C_YELLOW)


def _signal_handler(sig, frame):
    global _running
    _log("Recebido sinal de encerramento...", C_YELLOW)
    _running = False


def main():
    # Verificar DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print(f"{C_RED}[ERRO] DATABASE_URL não definida.{C_RESET}")
        print(f"Use: export DATABASE_URL=\"postgresql://user:pass@localhost:15432/derekh_crm\"")
        print(f"E certifique-se que fly proxy está rodando: fly proxy 15432:5432 -a <pg-app>")
        sys.exit(1)

    # Inicializar pool PostgreSQL
    try:
        init_pg()
        _log("Conexão PostgreSQL OK.", C_GREEN)
    except Exception as e:
        print(f"{C_RED}[ERRO] Falha ao conectar PostgreSQL: {e}{C_RESET}")
        print(f"Verifique se fly proxy está rodando e DATABASE_URL está correta.")
        sys.exit(1)

    # Registrar signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    # Rodar loop
    asyncio.run(main_loop())


if __name__ == "__main__":
    main()
