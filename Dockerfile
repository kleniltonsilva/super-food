# =============================================================================
# Derekh Food API - Dockerfile Multi-Stage
# Stage 1: Build React | Stage 2: Python API
# =============================================================================

# -------------------- Stage 1: Build React --------------------
FROM node:20-alpine AS frontend-builder

WORKDIR /build

COPY restaurante-pedido-online/package.json restaurante-pedido-online/package-lock.json* ./
RUN npm ci --no-audit

COPY restaurante-pedido-online/ .
RUN npm run build

# -------------------- Stage 2: Python API --------------------
FROM python:3.12-slim AS production

# Evita bytecode e buffering
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENVIRONMENT=production

WORKDIR /app

# Instala dependencias do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Copia e instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia codigo do projeto
COPY backend/ backend/
COPY database/ database/
COPY migrations/ migrations/
COPY utils/ utils/
COPY alembic.ini .

# Copia build do React
COPY --from=frontend-builder /build/dist/public/ restaurante-pedido-online/dist/public/

# Cria diretorios necessarios
RUN mkdir -p backend/static/uploads

# Porta da API
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Script de startup: Alembic migrations + Gunicorn
CMD ["sh", "-c", "alembic upgrade head && gunicorn backend.app.main:app --worker-class uvicorn.workers.UvicornWorker --workers 2 --bind 0.0.0.0:8000 --timeout 120 --graceful-timeout 30 --access-logfile - --error-logfile -"]
