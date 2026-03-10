#!/bin/bash
# =============================================================================
# Super Food - Script de Deploy
# Uso: ./scripts/deploy.sh [dev|prod]
# =============================================================================

set -e

MODE="${1:-dev}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "========================================="
echo " Super Food - Deploy ($MODE)"
echo "========================================="

if [ "$MODE" = "prod" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"

    # Verifica variaveis obrigatorias
    if [ -z "$POSTGRES_PASSWORD" ] || [ -z "$SECRET_KEY" ] || [ -z "$SUPER_ADMIN_PASS" ]; then
        echo "ERRO: Defina as variaveis obrigatorias no .env:"
        echo "  POSTGRES_PASSWORD, SECRET_KEY, SUPER_ADMIN_PASS"
        echo ""
        echo "Copie o template: cp .env.example .env"
        exit 1
    fi
else
    COMPOSE_FILE="docker-compose.yml"
fi

echo "[1/5] Parando containers existentes..."
docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true

echo "[2/5] Baixando imagens e construindo..."
docker compose -f "$COMPOSE_FILE" build --no-cache api

echo "[3/5] Subindo servicos..."
docker compose -f "$COMPOSE_FILE" up -d

echo "[4/5] Aguardando banco ficar pronto..."
sleep 5

echo "[5/5] Rodando migrations..."
docker compose -f "$COMPOSE_FILE" exec api alembic upgrade head || echo "AVISO: Migrations falharam (pode ser primeira execucao)"

echo ""
echo "========================================="
echo " Deploy concluido!"
echo " API: http://localhost:8000"
echo " Health: http://localhost:8000/health"
echo "========================================="
echo ""
docker compose -f "$COMPOSE_FILE" ps
