#!/bin/bash
# start_scanner.sh — Inicia fly proxy + scanner_agent.py
#
# Uso: ./start_scanner.sh
#
# Pré-requisitos:
#   - fly CLI instalado (~/.fly/bin/fly ou no PATH)
#   - Playwright instalado (playwright install chromium)
#   - .venv ativado com dependências do projeto

set -e

# ============================================================
# CONFIGURAÇÃO — ajustar conforme necessário
# ============================================================
PG_APP="derekh-crm-db"           # Nome do app PostgreSQL no Fly.io
PG_LOCAL_PORT=15432               # Porta local do proxy
PG_USER="postgres"                # Usuário PostgreSQL
PG_DB="derekh_crm"               # Nome do banco

# Detectar fly CLI
FLY_CMD=""
if command -v fly &>/dev/null; then
    FLY_CMD="fly"
elif [ -f "$HOME/.fly/bin/fly" ]; then
    FLY_CMD="$HOME/.fly/bin/fly"
elif command -v flyctl &>/dev/null; then
    FLY_CMD="flyctl"
else
    echo "[ERRO] fly CLI não encontrado. Instale: https://fly.io/docs/flyctl/install/"
    exit 1
fi

# ============================================================
# VERIFICAÇÃO
# ============================================================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "scanner_agent.py" ]; then
    echo "[ERRO] scanner_agent.py não encontrado em $SCRIPT_DIR"
    exit 1
fi

# Ativar venv se não estiver ativo
if [ -z "$VIRTUAL_ENV" ] && [ -d ".venv" ]; then
    echo "[INFO] Ativando .venv..."
    source .venv/bin/activate
fi

# Verificar se a porta já está em uso (proxy já rodando?)
if lsof -i :$PG_LOCAL_PORT &>/dev/null; then
    echo "[INFO] Porta $PG_LOCAL_PORT já em uso — assumindo fly proxy ativo"
else
    echo "[INFO] Iniciando fly proxy ($PG_APP) na porta $PG_LOCAL_PORT..."
    $FLY_CMD proxy $PG_LOCAL_PORT:5432 -a $PG_APP &
    FLY_PROXY_PID=$!
    sleep 3

    # Verificar se proxy iniciou
    if ! kill -0 $FLY_PROXY_PID 2>/dev/null; then
        echo "[ERRO] fly proxy falhou ao iniciar"
        exit 1
    fi
    echo "[INFO] fly proxy PID=$FLY_PROXY_PID"
fi

# ============================================================
# SOLICITAR SENHA SE NÃO DEFINIDA
# ============================================================
if [ -z "$DATABASE_URL" ]; then
    if [ -z "$PG_PASSWORD" ]; then
        echo ""
        echo "Senha do PostgreSQL ($PG_APP):"
        echo "  (use: fly postgres connect -a $PG_APP para verificar)"
        read -s -p "Senha: " PG_PASSWORD
        echo ""
    fi
    export DATABASE_URL="postgresql://$PG_USER:$PG_PASSWORD@localhost:$PG_LOCAL_PORT/$PG_DB"
fi

echo "[INFO] DATABASE_URL configurada (${DATABASE_URL:0:40}...)"
echo ""

# ============================================================
# INICIAR SCANNER AGENT
# ============================================================
echo "============================================="
echo "  Scanner Agent — Derekh CRM"
echo "  Ctrl+C para encerrar"
echo "============================================="
echo ""

python scanner_agent.py
EXIT_CODE=$?

# ============================================================
# CLEANUP
# ============================================================
if [ -n "$FLY_PROXY_PID" ]; then
    echo "[INFO] Encerrando fly proxy (PID=$FLY_PROXY_PID)..."
    kill $FLY_PROXY_PID 2>/dev/null
fi

exit $EXIT_CODE
