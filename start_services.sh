#!/bin/bash
# Super Food v4.0 - Script de inicialização
# Uso: ./start_services.sh [--api-only|--build-react]

set -e

cd "$(dirname "$0")"

# Ativa o ambiente virtual
source venv/bin/activate

# Limpa processos anteriores
echo "Limpando processos anteriores..."
pkill -9 -f "uvicorn backend" 2>/dev/null || true
sleep 2

echo "============================================================"
echo "   SUPER FOOD v4.0 - Iniciando Sistema"
echo "============================================================"

# Build do React (se solicitado ou se não existir)
REACT_DIR="restaurante-pedido-online"
if [ "$1" == "--build-react" ] || [ ! -d "$REACT_DIR/dist" ]; then
    if [ -d "$REACT_DIR" ] && [ -f "$REACT_DIR/package.json" ]; then
        echo "Fazendo build do React..."
        cd "$REACT_DIR"
        npm run build
        cd ..
        echo "   [OK] Build concluído → dist/public/"
    fi
fi

# Inicia FastAPI (serve todos os apps React)
echo "Iniciando FastAPI Backend (porta 8000)..."
nohup uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/superfood_api.log 2>&1 &
sleep 3

echo ""
echo "============================================================"
echo "   Sistema Iniciado!"
echo "============================================================"
echo ""
echo "Endpoints:"
echo "   - Admin:       http://localhost:8000/admin"
echo "   - Super Admin: http://localhost:8000/superadmin"
echo "   - Motoboy:     http://localhost:8000/entregador"
echo "   - Cliente:     http://localhost:8000/cliente/{CODIGO}"
echo "   - API Docs:    http://localhost:8000/docs"
echo ""
echo "Credenciais:"
echo "   - Super Admin: superadmin / SuperFood2025!"
echo "   - Restaurante: teste-{tipo}@superfood.test / 123456"
echo ""
echo "Log API: /tmp/superfood_api.log"
echo "Para parar: pkill -f 'uvicorn backend'"
echo "============================================================"

# Verifica se o serviço está rodando
sleep 2
if lsof -i :8000 >/dev/null 2>&1; then
    echo "   [OK] FastAPI rodando na porta 8000"
else
    echo "   [ERRO] FastAPI não iniciou — verifique /tmp/superfood_api.log"
fi
