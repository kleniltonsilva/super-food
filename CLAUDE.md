# CLAUDE.md

Orientações obrigatórias para o Claude Code trabalhar neste repositório.

## Projeto

**Super Food** é um SaaS multi-tenant para gestão de restaurantes com despacho inteligente de entregas.

Stack:
- Python 3.12+
- FastAPI (backend)
- Streamlit (dashboards)
- SQLAlchemy 2.0 + Alembic
- SQLite (dev) / PostgreSQL (prod)

Versão atual: **2.8.3 (07/02/2026)**

---

## Arquitetura Essencial

Serviços principais:
- FastAPI → `backend/app/main.py` (porta 8000)
- Streamlit:
  - Super Admin → `streamlit_app/super_admin.py` (8501)
  - Restaurante → `streamlit_app/restaurante_app.py` (8502)
  - Motoboy PWA → `app_motoboy/motoboy_app.py` (8503)

Estrutura:
backend/ # API FastAPI + WebSockets + Site Cliente
database/ # ORM + sessão
migrations/ # Alembic
streamlit_app/ # Dashboards
app_motoboy/ # PWA motoboy
utils/ # Mapbox, TSP, cálculos, seleção de motoboy

markdown
Copiar código

---

## REGRAS CRÍTICAS (NUNCA VIOLAR)

- Sistema **multi-tenant**
- TODAS as queries DEVEM filtrar por `restaurante_id`
- Motoboys são isolados por restaurante
- Nunca armazenar objetos ORM no `session_state`
- Sempre usar `get_db_session()`
- Usar eager loading (`joinedload`) quando houver relacionamento
- Gerar **código completo**, nunca snippets parciais
- Não hardcodar segredos (usar `.env`)
- Responder sempre em **português**

---

## Banco de Dados

- Banco padrão: `super_food.db` (na raiz do projeto)
- ORM: `database/models.py`
- Sessão: `database/session.py`

Migrations:
```bash
alembic upgrade head
alembic downgrade -1
alembic current
Sistema de Motoboys (Resumo Funcional)
Estados:

OFFLINE → cadastrado

ONLINE → login no app

EM ROTA → entregando

Seleção:

Rotação justa

Respeita capacidade do motoboy

Apenas motoboys ONLINE recebem pedidos

Arquivos-chave:

utils/motoboy_selector.py

utils/tsp_optimizer.py

utils/calculos.py

Mapas e Rotas
Mapbox para geocoding e rotas

Haversine como fallback offline

MAPBOX_TOKEN obrigatório no .env

Comandos Rápidos
bash
Copiar código
source venv/bin/activate
./start_services.sh
Parar tudo:

bash
Copiar código
pkill -f "uvicorn|streamlit"
Ambiente (.env)
env
Copiar código
DATABASE_URL=sqlite:///./super_food.db
MAPBOX_TOKEN=seu_token
