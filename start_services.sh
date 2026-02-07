#!/bin/bash
# Super Food - Script de inicialização de serviços
# Uso: ./start_services.sh [--all|--api-only|--build-react]

set -e

# Diretório do projeto
cd "$(dirname "$0")"

# Ativa o ambiente virtual
source venv/bin/activate

# Limpa processos anteriores
echo "Limpando processos anteriores..."
pkill -9 -f "uvicorn backend" 2>/dev/null || true
pkill -9 -f "streamlit run streamlit_app" 2>/dev/null || true
pkill -9 -f "streamlit run app_motoboy" 2>/dev/null || true
sleep 2

echo "============================================================"
echo "   SUPER FOOD - Iniciando Sistema"
echo "============================================================"

# Build do React (se solicitado ou se não existir)
REACT_DIR="restaurante-pedido-online"
if [ "$1" == "--build-react" ] || [ ! -d "$REACT_DIR/dist" ]; then
    if [ -d "$REACT_DIR" ] && [ -f "$REACT_DIR/package.json" ]; then
        echo "Fazendo build do Site Cliente React..."
        cd "$REACT_DIR"
        if command -v pnpm &> /dev/null; then
            pnpm install 2>/dev/null || npm install
            pnpm build 2>/dev/null || npm run build
        else
            npm install
            npm run build
        fi
        cd ..
        echo "   [OK] Build do React concluído"
    fi
fi

# Inicia FastAPI
echo "Iniciando FastAPI Backend (porta 8000)..."
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/superfood_api.log 2>&1 &
sleep 3

if [ "$1" != "--api-only" ]; then
    # Inicia Super Admin
    echo "Iniciando Super Admin (porta 8501)..."
    nohup streamlit run streamlit_app/super_admin.py --server.port=8501 --server.headless=true > /tmp/superfood_admin.log 2>&1 &
    sleep 2

    # Inicia Dashboard Restaurante
    echo "Iniciando Dashboard Restaurante (porta 8502)..."
    nohup streamlit run streamlit_app/restaurante_app.py --server.port=8502 --server.headless=true > /tmp/superfood_restaurante.log 2>&1 &
    sleep 2

    # Inicia App Motoboy
    echo "Iniciando App Motoboy (porta 8503)..."
    nohup streamlit run app_motoboy/motoboy_app.py --server.port=8503 --server.headless=true > /tmp/superfood_motoboy.log 2>&1 &
    sleep 2

    # Inicia Site Cliente
    echo "Iniciando Site Cliente (porta 8504)..."
    nohup streamlit run streamlit_app/cliente_app.py --server.port=8504 --server.headless=true > /tmp/superfood_cliente.log 2>&1 &
    sleep 2
fi

echo ""
echo "============================================================"
echo "   Sistema Iniciado!"
echo "============================================================"
echo ""
echo "Endpoints disponiveis:"
echo "   - API FastAPI:      http://localhost:8000"
echo "   - API Docs:         http://localhost:8000/docs"

if [ "$1" != "--api-only" ]; then
    echo "   - Super Admin:      http://localhost:8501"
    echo "   - Restaurante:      http://localhost:8502"
    echo "   - App Motoboy:      http://localhost:8503"
fi

echo ""
echo "Site do Cliente:"
echo "   - Direto:  http://localhost:8504/?restaurante={CODIGO}"
echo "   - Via API: http://localhost:8000/cliente/{CODIGO}"
echo ""
echo "Logs em:"
echo "   - API:         /tmp/superfood_api.log"

if [ "$1" != "--api-only" ]; then
    echo "   - Admin:       /tmp/superfood_admin.log"
    echo "   - Restaurante: /tmp/superfood_restaurante.log"
    echo "   - Motoboy:     /tmp/superfood_motoboy.log"
fi

echo ""
echo "Para parar os servicos: pkill -f 'uvicorn|streamlit'"
echo "============================================================"

# Verifica se os serviços estão rodando
sleep 2
echo ""
echo "Verificando servicos..."

if lsof -i :8000 >/dev/null 2>&1; then
    echo "   [OK] FastAPI Backend"
else
    echo "   [ERRO] FastAPI Backend"
fi

if [ "$1" != "--api-only" ]; then
    if lsof -i :8501 >/dev/null 2>&1; then
        echo "   [OK] Super Admin"
    else
        echo "   [ERRO] Super Admin"
    fi

    if lsof -i :8502 >/dev/null 2>&1; then
        echo "   [OK] Dashboard Restaurante"
    else
        echo "   [ERRO] Dashboard Restaurante"
    fi

    if lsof -i :8503 >/dev/null 2>&1; then
        echo "   [OK] App Motoboy"
    else
        echo "   [ERRO] App Motoboy"
    fi
fi

# Verifica build do React
if [ -d "$REACT_DIR/dist" ]; then
    echo "   [OK] Site Cliente React (build disponível)"
else
    echo "   [INFO] Site Cliente React não compilado. Execute: ./start_services.sh --build-react"
fi
