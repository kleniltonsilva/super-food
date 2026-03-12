#!/usr/bin/env bash
# ============================================================
# Super Food v4.0 - Iniciar Sistema (Build + FastAPI)
# ============================================================
# Fluxo: build React → FastAPI (serve todos os apps React)
# Acesso produção: http://localhost:8000
# Acesso dev live: http://localhost:5173 (hot-reload, sem build)
#
# Uso:
#   ./iniciar_tudo.sh              # Build + FastAPI
#   ./iniciar_tudo.sh --no-browser # Não abre navegador
#   ./iniciar_tudo.sh --skip-build # Pula o build (mais rápido)
# ============================================================

set -e

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Diretório raiz do projeto
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$PROJECT_DIR/restaurante-pedido-online"
LOG_DIR="/tmp/superfood_logs"

# Flags
NO_BROWSER=false
SKIP_BUILD=false

for arg in "$@"; do
    case $arg in
        --no-browser)  NO_BROWSER=true ;;
        --skip-build)  SKIP_BUILD=true ;;
    esac
done

mkdir -p "$LOG_DIR"

# ============================================================
# Funções auxiliares
# ============================================================

print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}============================================================${NC}"
    echo -e "${BOLD}${CYAN}  🍕 SUPER FOOD - Build + Iniciar Todos os Serviços${NC}"
    echo -e "${BOLD}${CYAN}============================================================${NC}"
    echo ""
}

print_status() { echo -e "  ${GREEN}✓${NC} $1"; }
print_warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
print_error()  { echo -e "  ${RED}✗${NC} $1"; }
print_step()   { echo -e "${BLUE}$1${NC}"; }

cleanup_old_processes() {
    echo -e "${YELLOW}Limpando processos antigos...${NC}"
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    sleep 1
    print_status "Processos antigos limpos"
}

# Busca código de acesso de um restaurante pelo email
get_codigo() {
    local email="$1"
    python3 -c "
import sqlite3, sys
try:
    conn = sqlite3.connect('$PROJECT_DIR/super_food.db')
    c = conn.cursor()
    c.execute(\"SELECT codigo_acesso FROM restaurantes WHERE email=? AND ativo=1 LIMIT 1\", ('$email',))
    row = c.fetchone()
    conn.close()
    print(row[0] if row else '')
except:
    print('')
" 2>/dev/null
}

wait_for_service() {
    local url="$1"
    local max_wait="${2:-30}"
    local count=0
    while [ $count -lt $max_wait ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -qE "^(200|301|302|307|404)$"; then
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done
    return 1
}

open_browser() {
    local url="$1"
    if command -v xdg-open &>/dev/null; then
        xdg-open "$url" 2>/dev/null &
    elif command -v google-chrome &>/dev/null; then
        google-chrome "$url" 2>/dev/null &
    elif command -v firefox &>/dev/null; then
        firefox "$url" 2>/dev/null &
    fi
}

cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Parando todos os serviços...${NC}"
    for pidfile in "$LOG_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile")
        kill "$pid" 2>/dev/null || true
        rm -f "$pidfile"
    done
    lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    lsof -ti:5173 2>/dev/null | xargs -r kill -9 2>/dev/null || true
    echo -e "${GREEN}✅ Todos os serviços parados.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================
# MAIN
# ============================================================

print_header
cleanup_old_processes

# Ativar venv
if [ -f "$PROJECT_DIR/venv/bin/activate" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
    print_status "Virtual environment ativado"
fi

# ============================================================
# 1. BUILD REACT (sempre, para garantir mudanças no ar)
# ============================================================
echo ""
if [ "$SKIP_BUILD" = true ]; then
    print_warn "Build pulado (--skip-build)"
else
    print_step "[1/3] Compilando React (npm run build)..."
    echo -e "      ${YELLOW}Aguarde, isso leva ~1 minuto...${NC}"
    cd "$FRONTEND_DIR"
    if npm run build > "$LOG_DIR/build.log" 2>&1; then
        print_status "Build concluído com sucesso → dist/public/"
    else
        print_error "Build FALHOU! Verifique: $LOG_DIR/build.log"
        echo ""
        tail -20 "$LOG_DIR/build.log"
        exit 1
    fi
fi

# ============================================================
# 2. FastAPI Backend (porta 8000) — serve o build React
# ============================================================
echo ""
print_step "[2/3] Iniciando FastAPI Backend (porta 8000)..."

cd "$PROJECT_DIR"
uvicorn backend.app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    > "$LOG_DIR/fastapi.log" 2>&1 &
echo $! > "$LOG_DIR/fastapi.pid"
print_status "FastAPI iniciado (PID: $(cat "$LOG_DIR/fastapi.pid"))"

# ============================================================
# 3. Aguardar serviços
# ============================================================
echo ""
print_step "[3/3] Aguardando serviços ficarem prontos..."

echo -n "  FastAPI (8000)... "
if wait_for_service "http://localhost:8000/health/live" 30; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}TIMEOUT — verifique $LOG_DIR/fastapi.log${NC}"
fi

# ============================================================
# Buscar códigos dos 8 restaurantes de teste
# ============================================================
echo ""
echo -e "${YELLOW}Buscando restaurantes de teste no banco...${NC}"

declare -A TIPOS_EMAIL=(
    ["pizzaria"]="teste-pizzaria@superfood.test"
    ["hamburgueria"]="teste-hamburgueria@superfood.test"
    ["sushi"]="teste-sushi@superfood.test"
    ["acai"]="teste-acai@superfood.test"
    ["bebidas"]="teste-bebidas@superfood.test"
    ["esfiharia"]="teste-esfiharia@superfood.test"
    ["restaurante"]="teste-restaurante@superfood.test"
    ["salgados"]="teste-salgados@superfood.test"
)

declare -A TIPOS_NOME=(
    ["pizzaria"]="Don Massimo Pizzaria  "
    ["hamburgueria"]="Smash Bros Burgers    "
    ["sushi"]="Sakura Sushi House    "
    ["acai"]="Açaí Tropical Point   "
    ["bebidas"]="Gelou Bebidas         "
    ["esfiharia"]="Habibs da Vila        "
    ["restaurante"]="Cantina da Praça      "
    ["salgados"]="Delícias da Vovó      "
)

declare -A CODIGOS

for tipo in pizzaria hamburgueria sushi acai bebidas esfiharia restaurante salgados; do
    email="${TIPOS_EMAIL[$tipo]}"
    codigo=$(get_codigo "$email")
    CODIGOS[$tipo]="$codigo"
    if [ -n "$codigo" ]; then
        print_status "${TIPOS_NOME[$tipo]} → $codigo"
    else
        print_warn "${TIPOS_NOME[$tipo]} → não encontrado no banco"
    fi
done

# Código do restaurante de teste padrão (legado)
CODIGO_PADRAO=$(get_codigo "teste@superfood.com")

# ============================================================
# Exibir URLs
# ============================================================
echo ""
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo -e "${BOLD}${CYAN}  ✅ SISTEMA INICIADO COM BUILD ATUALIZADO!${NC}"
echo -e "${BOLD}${CYAN}============================================================${NC}"
echo ""
echo -e "${BOLD}  🔧 Painel Admin / Super Admin:${NC}"
echo -e "     Admin:        ${GREEN}http://localhost:8000/admin${NC}"
echo -e "     Super Admin:  ${GREEN}http://localhost:8000/superadmin${NC}"
echo -e "     Motoboy:      ${GREEN}http://localhost:8000/entregador${NC}"
echo -e "     API Docs:     ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BOLD}  🍽️  Sites dos 8 Restaurantes de Teste:${NC}"
for tipo in pizzaria hamburgueria sushi acai bebidas esfiharia restaurante salgados; do
    codigo="${CODIGOS[$tipo]}"
    nome="${TIPOS_NOME[$tipo]}"
    if [ -n "$codigo" ]; then
        echo -e "     ${nome} ${GREEN}http://localhost:8000/cliente/${codigo}${NC}"
    else
        echo -e "     ${nome} ${RED}(rodar seed_011 primeiro)${NC}"
    fi
done

if [ -n "$CODIGO_PADRAO" ]; then
    echo ""
    echo -e "     Teste padrão:           ${GREEN}http://localhost:8000/cliente/${CODIGO_PADRAO}${NC}"
fi

echo ""
echo -e "${BOLD}  🔑 Credenciais:${NC}"
echo -e "     Super Admin:  superadmin / SuperFood2025!"
echo -e "     Restaurantes: teste-{tipo}@superfood.test / 123456"

echo ""
echo -e "${BOLD}  📁 Logs:${NC} $LOG_DIR/"
echo -e "${BOLD}  💡 Para pular o build:${NC} ./iniciar_tudo.sh --skip-build"
echo ""

# ============================================================
# Abrir navegador
# ============================================================
if [ "$NO_BROWSER" = false ]; then
    echo -e "${YELLOW}Abrindo navegador...${NC}"
    sleep 2

    open_browser "http://localhost:8000/admin"
    sleep 0.3
    open_browser "http://localhost:8000/superadmin"
    sleep 0.3

    for tipo in pizzaria hamburgueria sushi acai bebidas esfiharia restaurante salgados; do
        codigo="${CODIGOS[$tipo]}"
        if [ -n "$codigo" ]; then
            open_browser "http://localhost:8000/cliente/${codigo}"
            sleep 0.3
        fi
    done

    print_status "Abas do navegador abertas"
fi

echo ""
echo -e "${BOLD}💡 Pressione Ctrl+C para parar todos os serviços${NC}"
echo -e "${CYAN}------------------------------------------------------------${NC}"

# Monitorar — manter script vivo + reiniciar FastAPI se cair
while true; do
    if [ -f "$LOG_DIR/fastapi.pid" ]; then
        pid=$(cat "$LOG_DIR/fastapi.pid")
        if ! kill -0 "$pid" 2>/dev/null; then
            print_error "FastAPI parou! Reiniciando..."
            cd "$PROJECT_DIR"
            uvicorn backend.app.main:app \
                --host 0.0.0.0 --port 8000 --reload \
                > "$LOG_DIR/fastapi.log" 2>&1 &
            echo $! > "$LOG_DIR/fastapi.pid"
            print_status "FastAPI reiniciado (PID: $(cat "$LOG_DIR/fastapi.pid"))"
        fi
    fi
    sleep 5
done
