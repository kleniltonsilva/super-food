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
|    (API REST)    | |    (Port 8501)   | |  (Ports 8502-4)  |
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

### 1. FastAPI + Uvicorn (Recomendado para Producao)

**Arquivo**: `backend/app/main.py`
**Porta**: 8000

Caracteristicas:
- Stateless e escalavel horizontalmente
- Suporta multiplos workers (1000+ requisicoes/segundo)
- WebSockets para GPS em tempo real
- Templates HTML para site do cliente
- Nao tem problema de SessionInfo

**Iniciar**:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Streamlit (Dashboard Administrativo)

**Arquivos**: `streamlit_app/*.py`, `app_motoboy/*.py`
**Portas**: 8501-8504

Caracteristicas:
- Ideal para dashboards internos
- Interface rapida para desenvolvimento
- NAO recomendado para clientes externos em escala

**Configuracao**: `.streamlit/config.toml`

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
- Streamlit para tudo
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

## Como Executar

### Desenvolvimento
```bash
# Todos os servicos
python run_production.py

# Apenas API (mais estavel)
python run_production.py --api-only
```

### Producao com Docker
```bash
# Build
docker build -t superfood-api .

# Run com multiplos workers
docker run -p 8000:8000 -e DATABASE_URL=postgresql://... superfood-api
```

## Endpoints Principais

### API FastAPI (Port 8000)
- `GET /` - Health check
- `GET /docs` - Documentacao Swagger
- `GET /site/{codigo}` - Site do cliente (HTML)
- `GET /site/{codigo}/cardapio` - Cardapio (HTML)
- `WS /ws/{restaurante_id}` - WebSocket tempo real

### Streamlit (Ports 8501-8504)
- Super Admin: http://localhost:8501
- Restaurante: http://localhost:8502
- Motoboy: http://localhost:8503
- Cliente: http://localhost:8504

## Migracao Recomendada

### Fase 1 (Atual)
- [x] Backend FastAPI basico
- [x] WebSockets implementados
- [x] Templates HTML site cliente

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
