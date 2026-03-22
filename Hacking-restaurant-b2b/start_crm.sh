#!/bin/bash
# Inicia o servidor Derekh CRM e abre no navegador

cd "$(dirname "$0")"

# Ativa o ambiente virtual
source .venv/bin/activate

# PostgreSQL local (peer auth via Unix socket)
export DATABASE_URL="postgres:///derekh_crm?host=/var/run/postgresql"

PORT=8000
URL="http://localhost:$PORT"

# Mata processo anterior na mesma porta (se houver)
PID=$(lsof -i :"$PORT" -t 2>/dev/null)
if [ -n "$PID" ]; then
    echo "[CRM] Porta $PORT ocupada (PID $PID). Encerrando..."
    kill "$PID" 2>/dev/null
    sleep 1
fi

echo "[CRM] Iniciando Derekh CRM em $URL ..."

# Abre o navegador após 2s (em background)
(sleep 2 && xdg-open "$URL") &

# Inicia o servidor (fica em foreground — Ctrl+C para parar)
uvicorn crm.app:app --reload --port "$PORT"
