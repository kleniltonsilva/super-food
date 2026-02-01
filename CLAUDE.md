# CLAUDE.md

Este arquivo fornece orientacoes para o Claude Code ao trabalhar com este repositorio.

## Visao Geral do Projeto

Super Food e uma plataforma SaaS multi-tenant para gestao de restaurantes com rastreamento de entregas em tempo real e otimizacao de rotas. Construido com Python 3.12+, FastAPI (backend), Streamlit (dashboards), SQLAlchemy 2.0+ ORM e migrations Alembic.

**Versao Atual:** 2.7.6 (01/02/2026)

## Arquitetura do Sistema

O sistema possui duas camadas de execucao:

| Camada | Tecnologia | Porta | Uso |
|--------|------------|-------|-----|
| API Backend | FastAPI + Uvicorn | 8000 | Site cliente, WebSockets, API REST |
| Dashboards | Streamlit | 8501-8503 | Admin, Restaurante, Motoboy |

### As 4 Cabecas do Sistema

| App | Arquivo | Porta | Funcao |
|-----|---------|-------|--------|
| FastAPI Backend | `backend/app/main.py` | 8000 | API REST + Site Cliente |
| Super Admin | `streamlit_app/super_admin.py` | 8501 | Gestao do SaaS |
| Dashboard Restaurante | `streamlit_app/restaurante_app.py` | 8502 | Gestao do restaurante |
| App Motoboy | `app_motoboy/motoboy_app.py` | 8503 | PWA para entregadores |

## Comandos Comuns

### Iniciar Sistema Completo (Recomendado)

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar todos os servicos (FastAPI + Streamlit)
./start_services.sh

# Ou apenas a API FastAPI
./start_services.sh --api-only
```

### Iniciar Servicos Individualmente

```bash
# Ativar ambiente virtual
source venv/bin/activate

# FastAPI Backend (porta 8000) - PRINCIPAL
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Super Admin (porta 8501)
streamlit run streamlit_app/super_admin.py --server.port=8501

# Dashboard Restaurante (porta 8502)
streamlit run streamlit_app/restaurante_app.py --server.port=8502

# App Motoboy PWA (porta 8503)
streamlit run app_motoboy/motoboy_app.py --server.port=8503
```

### Parar Todos os Servicos

```bash
pkill -f "uvicorn|streamlit"
```

### Testar Endpoints

```bash
# Testar se FastAPI esta rodando
curl http://localhost:8000/

# Testar documentacao Swagger
curl http://localhost:8000/docs

# Testar site do cliente (substitua CODIGO pelo codigo do restaurante)
curl http://localhost:8000/site/CODIGO

# Verificar portas ativas
lsof -i :8000,:8501,:8502,:8503 | grep LISTEN
```

### Operacoes de Banco

```bash
# Inicializar banco com dados padrao
python init_database.py

# Aplicar todas as migrations
alembic upgrade head

# Reverter ultima migration
alembic downgrade -1

# Ver versao atual
alembic current

# Gerar nova migration
alembic revision --autogenerate -m "descricao"
```

### Instalacao

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Arquitetura

### Design Multi-Tenant
- Todas as queries DEVEM filtrar por `restaurante_id` para isolamento
- `SuperAdmin` gerencia todos os restaurantes globalmente
- Cada restaurante e um tenant isolado

### Estrutura de Camadas

```
FastAPI Backend (API REST + WebSockets)
      |
Streamlit Apps (Dashboards internos)
      |
SQLAlchemy ORM (database/models.py)
      |
Session Management (database/session.py)
      |
Utility Services (utils/)
```

### Diretorios Principais
- `backend/` - FastAPI (API REST, WebSockets, Site Cliente)
- `database/` - Models ORM e gerenciamento de sessao
- `migrations/` - Scripts Alembic
- `streamlit_app/` - Dashboards Streamlit
- `app_motoboy/` - PWA mobile para motoboys
- `utils/` - Integracao Mapbox, Haversine, TSP, Calculos, Selecao de Motoboys

### Modelos do Banco (22+ tabelas)

**Tenants:**
- `super_admin`, `restaurantes`, `config_restaurante`, `site_config`

**Motoboys:**
- `motoboys` (com campos de selecao justa), `motoboys_solicitacoes`, `gps_motoboys`

**Produtos:**
- `categorias_menu`, `produtos`, `tipos_produto`, `variacoes_produto`

**Pedidos:**
- `pedidos`, `itens_pedido`, `entregas`, `rotas_otimizadas`

**Clientes:**
- `clientes`, `enderecos_cliente`, `carrinho`

**Financeiro:**
- `caixa`, `movimentacoes_caixa`, `notificacoes`

### Modulos de Utils

| Modulo | Funcao |
|--------|--------|
| `mapbox_api.py` | Geocoding, rotas, direcoes |
| `haversine.py` | Calculo de distancia offline |
| `calculos.py` | Taxa de entrega, ganhos do motoboy |
| `motoboy_selector.py` | Selecao justa de motoboys |
| `tsp_optimizer.py` | Otimizacao de rotas (TSP) |

### Padroes ORM
- Usar `get_db_session()` de `database/session.py`
- Sempre usar eager loading (`joinedload()`) para relacionamentos
- Fechar sessoes com try/finally

### APIs Externas
- **Mapbox**: Geocoding, rotas (requer `MAPBOX_TOKEN` no `.env`)
- **Haversine**: Fallback offline para distancias

## Configuracao

Variaveis `.env` obrigatorias:
```
MAPBOX_TOKEN=seu_token_aqui
DATABASE_URL=sqlite:///./super_food.db
```

**IMPORTANTE:** O banco fica na RAIZ do projeto (`super_food.db`), nao em `/database/`.

Para producao (PostgreSQL):
```
DATABASE_URL=postgresql+psycopg2://user:pass@host/db
```

## Credenciais de Teste
- Super Admin: `superadmin` / `SuperFood2025!`
- Restaurante Teste: `teste@superfood.com` / `123456`

## Seguranca
- Senhas usam hash SHA256 via `set_senha()` e `verificar_senha()`
- Codigos de acesso sao hex strings de 8 caracteres
- Isolamento multi-tenant em todas as queries

## Sistema de Selecao Justa de Motoboys

Campos do modelo `Motoboy`:
- `ordem_hierarquia` - Posicao na fila de rotacao
- `disponivel` - Flag online/offline
- `em_rota` - Flag se esta entregando
- `entregas_pendentes` - Contador de entregas
- `ultima_entrega_em` - Timestamp da ultima entrega
- `ultima_rota_em` - Timestamp da ultima rota recebida

Funcoes em `utils/motoboy_selector.py`:
- `selecionar_motoboy_para_rota()` - Seleciona motoboy de forma justa
- `atribuir_rota_motoboy()` - Atribui pedidos ao motoboy
- `finalizar_entrega_motoboy()` - Finaliza entrega e calcula ganhos
- `marcar_motoboy_disponivel()` - Toggle online/offline

## Endpoints da API FastAPI

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Health check |
| `/docs` | GET | Documentacao Swagger |
| `/site/{codigo}` | GET | Site do cliente (HTML) |
| `/site/{codigo}/cardapio` | GET | Cardapio do restaurante |
| `/ws/{restaurante_id}` | WS | WebSocket tempo real |

## Configuracoes de Idioma

- Responda sempre em portugues, independentemente do idioma do comando.
- Todas explicacoes, planos e mensagens devem estar em portugues.
