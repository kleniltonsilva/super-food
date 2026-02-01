# Arquitetura Super Food - SaaS Escalavel

## Visao Geral

O Super Food utiliza uma arquitetura hibrida otimizada para escalabilidade:

```
                    +------------------+
                    |     NGINX        |
                    |  (Reverse Proxy) |
                    +--------+---------+
                             |
          +------------------+------------------+
          |                  |                  |
          v                  v                  v
+------------------+ +------------------+ +------------------+
|  FastAPI/Uvicorn | |  Streamlit Admin | |  Streamlit Apps  |
|    (API REST)    | |    (Port 8501)   | |  (Ports 8502-3)  |
|    (Port 8000)   | |                  | |                  |
+--------+---------+ +--------+---------+ +--------+---------+
          |                  |                  |
          +------------------+------------------+
                             |
                    +--------v---------+
                    |   PostgreSQL     |
                    |  (ou SQLite dev) |
                    +------------------+
```

## Componentes

### 1. FastAPI + Uvicorn (Backend Principal)

**Arquivo**: `backend/app/main.py`
**Porta**: 8000

Caracteristicas:
- Stateless e escalavel horizontalmente
- Suporta multiplos workers (1000+ requisicoes/segundo)
- WebSockets para GPS em tempo real
- Templates HTML para site do cliente
- Documentacao automatica via Swagger/OpenAPI
- Nao tem problema de SessionInfo

**Endpoints Principais**:

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Health check |
| `/docs` | GET | Documentacao Swagger |
| `/redoc` | GET | Documentacao ReDoc |
| `/site/{codigo}` | GET | Site do cliente (HTML) |
| `/site/{codigo}/cardapio` | GET | Cardapio (HTML) |
| `/ws/{restaurante_id}` | WebSocket | Tempo real |

### 2. Streamlit (Dashboards Administrativos)

**Arquivos**: `streamlit_app/*.py`, `app_motoboy/*.py`
**Portas**: 8501-8503

Caracteristicas:
- Ideal para dashboards internos
- Interface rapida para desenvolvimento
- NAO recomendado para clientes externos em escala

**Configuracao**: `.streamlit/config.toml`

## Como Executar

### Metodo 1: Script Shell (Recomendado)

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar TODOS os servicos
./start_services.sh

# Iniciar apenas FastAPI
./start_services.sh --api-only
```

### Metodo 2: Script Python

```bash
source venv/bin/activate

# Todos os servicos (foreground)
python run_production.py

# Apenas API
python run_production.py --api-only
```

### Metodo 3: Comandos Individuais

```bash
source venv/bin/activate

# FastAPI Backend (PRINCIPAL)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Producao (multiplos workers, sem reload)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Super Admin
streamlit run streamlit_app/super_admin.py --server.port=8501 --server.headless=true

# Dashboard Restaurante
streamlit run streamlit_app/restaurante_app.py --server.port=8502 --server.headless=true

# App Motoboy
streamlit run app_motoboy/motoboy_app.py --server.port=8503 --server.headless=true
```

### Parar Servicos

```bash
pkill -f "uvicorn|streamlit"
```

## Testando o Sistema

### Verificar Servicos Ativos

```bash
# Ver portas em uso
lsof -i :8000,:8501,:8502,:8503 | grep LISTEN

# Ou usando netstat
netstat -tlnp | grep -E ":800[0-3]"
```

### Testar Endpoints

```bash
# Health check FastAPI
curl http://localhost:8000/
# Esperado: {"mensagem":"Super Food API - Site do Cliente ativo!"}

# Testar codigo HTTP de cada servico
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/  # FastAPI
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501/  # Admin
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8502/  # Restaurante
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8503/  # Motoboy
# Todos devem retornar 200

# Testar site do cliente (substitua CODIGO)
curl http://localhost:8000/site/CODIGO
```

### Testar via Navegador

- **Swagger (API Docs)**: http://localhost:8000/docs
- **ReDoc (API Docs)**: http://localhost:8000/redoc
- **Super Admin**: http://localhost:8501
- **Dashboard Restaurante**: http://localhost:8502
- **App Motoboy**: http://localhost:8503
- **Site Cliente**: http://localhost:8000/site/{codigo_restaurante}

### Verificar Logs

```bash
# Logs quando usando start_services.sh
tail -f /tmp/superfood_api.log         # FastAPI
tail -f /tmp/superfood_admin.log       # Super Admin
tail -f /tmp/superfood_restaurante.log # Dashboard
tail -f /tmp/superfood_motoboy.log     # Motoboy
```

## Problema SessionInfo do Streamlit

### Causa
Bug conhecido do Streamlit (Issue #9767) onde mensagens WebSocket chegam fora de ordem durante reconexao.

### Solucao Profissional

1. **Para site do cliente**: Use FastAPI + Templates HTML
   - URL: `http://localhost:8000/site/{codigo_acesso}`
   - Nao tem problema de sessao

2. **Para dashboard restaurante**: Migrar para FastAPI gradualmente

3. **Para admin interno**: Streamlit e aceitavel (usuarios internos)

## Escalabilidade (1000+ Restaurantes)

### Desenvolvimento (Atual)
- SQLite local
- Streamlit para dashboards
- FastAPI para site cliente
- Servidor unico

### Producao (Recomendado)
- PostgreSQL com pool de conexoes
- FastAPI com multiplos workers
- Nginx como reverse proxy
- Redis para cache de sessoes
- Docker/Kubernetes para orquestracao

### Configuracao PostgreSQL
```env
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/super_food
```

### Producao com Docker

```bash
# Build
docker build -t superfood-api .

# Run com multiplos workers
docker run -p 8000:8000 -e DATABASE_URL=postgresql://... superfood-api
```

### Docker Compose (exemplo)

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db/super_food
    depends_on:
      - db

  admin:
    build: .
    command: streamlit run streamlit_app/super_admin.py --server.port=8501
    ports:
      - "8501:8501"
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=super_food
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Migracao Recomendada

### Fase 1 (Completa)
- [x] Backend FastAPI basico
- [x] WebSockets implementados
- [x] Templates HTML site cliente
- [x] Script de inicializacao unificado

### Fase 2 (Proximo)
- [ ] Migrar site cliente de Streamlit para FastAPI
- [ ] Implementar autenticacao JWT
- [ ] Adicionar Redis para sessoes

### Fase 3 (Producao)
- [ ] Migrar dashboard restaurante para FastAPI
- [ ] Deploy com Docker/Kubernetes
- [ ] PostgreSQL em producao
- [ ] CDN para arquivos estaticos

## Monitoramento

Para 1000 restaurantes, implemente:
- Prometheus + Grafana para metricas
- Sentry para tracking de erros
- Logs centralizados (ELK Stack)

## Troubleshooting

### Servicos nao iniciam

```bash
# Verificar se portas estao em uso
lsof -i :8000,:8501,:8502,:8503

# Matar processos antigos
pkill -f "uvicorn|streamlit"

# Reiniciar
./start_services.sh
```

### Erro "Address already in use"

```bash
# Encontrar e matar processo na porta
fuser -k 8000/tcp 8501/tcp 8502/tcp 8503/tcp
```

### Verificar ambiente virtual

```bash
which python  # Deve apontar para venv/bin/python
pip list | grep -E "fastapi|streamlit|uvicorn"
```
