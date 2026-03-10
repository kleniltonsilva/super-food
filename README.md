# Super Food - Plataforma SaaS para Gestao de Restaurantes

**AVISO DE LICENCA - IMPORTANTE**
Este repositorio NAO e open source. O codigo e PROPRIETARIO E CONFIDENCIAL.
Qualquer uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para os termos legais completos.

---

Sistema multi-tenant completo para gestao de restaurantes com entregas inteligentes, rastreamento GPS em tempo real, otimizacao de rotas (TSP), site do cliente React SPA e gestao financeira integrada.

## Visao Geral

O Super Food e composto por **5 aplicacoes principais**:

| Aplicacao | Tecnologia | Porta | Descricao |
|-----------|------------|-------|-----------|
| **API Backend** | FastAPI + Uvicorn | 8000 | API REST, WebSockets, serve React SPA |
| **Super Admin** | Streamlit | 8501 | Painel administrativo do SaaS |
| **Dashboard Restaurante** | Streamlit | 8502 | Gestao completa do restaurante |
| **App Motoboy (PWA)** | Streamlit | 8503 | App mobile para entregadores |
| **Site Cliente (React SPA)** | React 19 + Vite 7 | 5173 (dev) / 8000 (prod) | Pedido online para clientes |

**Versao atual: 3.1.0 (14/02/2026) — Migracao v4.0 em andamento**

### Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Backend API | Python 3.12+ / FastAPI / Uvicorn |
| ORM | SQLAlchemy 2.0+ |
| Migrations | Alembic |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL |
| Dashboards | Streamlit 1.40+ |
| Site Cliente | React 19 + Vite 7 + TanStack Query v5 + wouter + Tailwind CSS 4 + Radix UI |
| Auth | JWT (HS256) + bcrypt (FastAPI) / SHA256 (Streamlit) |
| Mapas | Mapbox API (geocoding, autocomplete, rotas) |
| Imagens | Pillow (resize + WebP) |
| Algoritmos | TSP (Nearest Neighbor), Haversine |

---

## Pre-requisitos

- Python 3.12+
- Node.js 18+ e npm (para o React SPA)
- pip
- Conta Mapbox (para API de geocodificacao)

---

## Instalacao

```bash
# Clonar repositorio
git clone https://github.com/kleniltonsilva/super-food.git
cd super-food

# Criar ambiente virtual Python
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependencias Python
pip install -r requirements.txt

# Instalar dependencias do React SPA
cd restaurante-pedido-online
npm install
cd ..

# Configurar variaveis de ambiente
cp .env.example .env
# Edite .env e adicione seu MAPBOX_TOKEN e SECRET_KEY

# Inicializar banco de dados
python init_database.py

# Aplicar migrations
alembic upgrade head
```

---

## Variaveis de Ambiente (.env)

```env
# Banco de dados
DATABASE_URL=sqlite:///./super_food.db

# Mapbox API (obrigatorio para geocodificacao e autocomplete)
MAPBOX_TOKEN=seu_token_aqui

# JWT Secret (obrigatorio)
SECRET_KEY=sua_chave_secreta_aqui

# API URL base
API_URL=http://127.0.0.1:8000

# Ambiente
ENVIRONMENT=development
DEBUG=True
```

Para producao, substituir `DATABASE_URL` por PostgreSQL:
```env
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/super_food
```

---

## Executando o Sistema

### Metodo Recomendado: Script Unificado

```bash
source venv/bin/activate

# Iniciar TODOS os servicos (FastAPI + Streamlit)
./start_services.sh

# Iniciar apenas a API FastAPI
./start_services.sh --api-only
```

### Executar Servicos Individualmente

```bash
source venv/bin/activate

# FastAPI Backend (porta 8000) - PRINCIPAL
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# Super Admin (porta 8501)
streamlit run streamlit_app/super_admin.py --server.port=8501

# Dashboard Restaurante (porta 8502)
streamlit run streamlit_app/restaurante_app.py --server.port=8502

# App Motoboy PWA (porta 8503)
streamlit run app_motoboy/motoboy_app.py --server.port=8503

# React SPA - Desenvolvimento (porta 5173, com proxy para API)
cd restaurante-pedido-online && npm run dev

# React SPA - Build para producao (servido pelo FastAPI em /cliente/{codigo})
cd restaurante-pedido-online && npm run build
```

### Parar Todos os Servicos

```bash
pkill -f "uvicorn|streamlit"
```

---

## Acessando o Sistema

| Servico | URL |
|---------|-----|
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Super Admin | http://localhost:8501 |
| Dashboard Restaurante | http://localhost:8502 |
| App Motoboy | http://localhost:8503 |
| Site Cliente (dev) | http://localhost:5173 |
| Site Cliente (prod) | http://localhost:8000/cliente/{CODIGO_RESTAURANTE} |

### Credenciais de Teste

| Aplicacao | Usuario/Email | Senha |
|-----------|---------------|-------|
| Super Admin | `superadmin` | `SuperFood2025!` |
| Restaurante Teste | `teste@superfood.com` | `123456` |
| Motoboy | Codigo do restaurante + usuario + senha | Configurado no cadastro |

---

## Estrutura Geral do Projeto

```
super-food/
├── backend/                    # FastAPI Backend (API REST + WebSockets)
│   └── app/
│       ├── main.py             # App principal, CORS, routers, WebSocket, SPA serving
│       ├── auth.py             # Auth JWT para restaurantes
│       ├── database.py         # get_db() para FastAPI DI
│       ├── models.py           # Re-exporta de database/models.py
│       ├── routers/            # 8 arquivos de rotas (50+ endpoints)
│       ├── schemas/            # Pydantic schemas (site, carrinho, cliente)
│       ├── utils/              # Despacho, templates de menu
│       ├── templates/          # HTML legado (Jinja2)
│       └── static/             # CSS legado
│
├── database/                   # SQLAlchemy ORM
│   ├── models.py               # 28 modelos ORM (fonte de verdade)
│   ├── session.py              # get_db_session() + helpers
│   ├── base.py                 # Base declarativa
│   ├── init.py                 # Funcoes de inicializacao
│   └── seed/                   # 6 seeds (super admin, planos, restaurante, etc)
│
├── migrations/                 # Alembic (12 migrations)
│   ├── env.py
│   └── versions/
│
├── restaurante-pedido-online/  # React SPA (Site do Cliente)
│   └── client/
│       └── src/
│           ├── App.tsx         # 11 rotas (wouter)
│           ├── main.tsx        # Entry point (QueryClient, contexts)
│           ├── lib/apiClient.ts # 30+ funcoes API (axios)
│           ├── hooks/useQueries.ts # React Query hooks centralizados
│           ├── contexts/       # RestauranteContext, AuthContext, ThemeContext
│           ├── pages/          # 11 paginas (Home, Cart, Checkout, etc)
│           └── components/     # UI components (Radix)
│
├── streamlit_app/              # Dashboards Streamlit
│   ├── super_admin.py          # Admin SaaS
│   ├── restaurante_app.py      # Dashboard Restaurante (~1900 linhas)
│   └── cliente_app.py          # Site do Cliente (legado Streamlit)
│
├── app_motoboy/                # PWA Motoboy
│   └── motoboy_app.py          # App Entregadores
│
├── utils/                      # Utilitarios compartilhados
│   ├── mapbox_api.py           # Integracao Mapbox (geocoding, rotas)
│   ├── haversine.py            # Calculo de distancia offline (fallback)
│   ├── calculos.py             # Taxas de entrega e ganhos de motoboy
│   ├── motoboy_selector.py     # Selecao justa de motoboys (rotacao)
│   └── tsp_optimizer.py        # Otimizacao de rotas (Nearest Neighbor)
│
├── alembic.ini                 # Config Alembic
├── requirements.txt            # Dependencias Python
├── init_database.py            # Inicializador do banco
├── start_services.sh           # Script para iniciar todos os servicos
├── run_production.py           # Script Python alternativo
├── super_food.db               # Banco SQLite (dev)
├── CLAUDE.md                   # Memoria tecnica completa (para IA)
├── ESTRUTURA.md                # Arvore de pastas + fluxo de dados
└── .env                        # Variaveis de ambiente
```

Para a arvore completa com descricoes detalhadas, veja `ESTRUTURA.md`.

---

## Funcionalidades Principais

### API FastAPI (Backend)
- API REST completa com 50+ endpoints documentados (Swagger/ReDoc)
- WebSockets para notificacoes em tempo real por restaurante
- Servindo React SPA em producao (`/cliente/{codigo}`)
- Upload de imagens com resize automatico (WebP)
- JWT auth para restaurantes (24h) e clientes (72h)

### Site Cliente (React SPA)
- Cardapio por categorias com busca
- Carrinho de compras (anonimo ou logado)
- Checkout com autocomplete de endereco (Mapbox) e calculo de taxa
- Cadastro/login de clientes (JWT + bcrypt)
- Historico de pedidos com acompanhamento em tempo real
- Programa de fidelidade (pontos + premios)
- Combos e promocoes com cupons
- Gestao de enderecos (CRUD)
- Pagina Minha Conta (perfil, enderecos, logout)
- Cache inteligente com React Query (staleTime por tipo de dado)

### Super Admin
- Criacao e gestao de restaurantes (tenants)
- Controle de planos de assinatura (Basico, Essencial, Avancado, Premium)
- Dashboard com metricas globais
- Gestao de inadimplencia e renovacoes

### Dashboard Restaurante
- Criacao e gestao de pedidos (Entrega, Retirada, Mesa)
- Despacho automatico com 3 modos (rapido economico, cronologico, manual)
- Gestao de cardapio (categorias, produtos, variacoes, combos)
- Gestao de motoboys (cadastro, capacidade, ranking)
- Mapa GPS em tempo real dos motoboys (Folium)
- Controle de caixa (abertura, movimentacoes, fechamento)
- Configuracao de taxas de entrega e pagamento de motoboys
- Antifraude por localizacao (raio 50m)

### App Motoboy (PWA)
- Login com codigo do restaurante + usuario + senha
- Recebimento de rotas otimizadas (TSP)
- GPS em tempo real (envia a cada 10s)
- Finalizacao de entregas com calculo automatico de ganhos
- Visualizacao de estatisticas e ganhos do dia
- Toggle online/offline para disponibilidade

---

## Fluxo de Motoboys

### Cadastro e Login
1. **Restaurante cadastra motoboy** -> motoboy fica OFFLINE
2. **Motoboy faz login no App** (codigo restaurante + usuario + senha) -> fica ONLINE
3. **Restaurante despacha pedidos** -> apenas para motoboys ONLINE
4. **Motoboy finaliza entregas** -> recebe novos pedidos ou fica disponivel

### Modos de Despacho
| Modo | Descricao |
|------|-----------|
| **Rapido Economico** | TSP por proximidade - otimiza combustivel (padrao) |
| **Cronologico Inteligente** | Agrupa pedidos por tempo (10 min), depois TSP |
| **Manual** | Restaurante atribui manualmente cada pedido |

### Rastreamento GPS em Tempo Real
- Motoboy online envia GPS automaticamente a cada 10 segundos
- Mapa em tempo real no painel do restaurante (aba "Mapa")
- Historico de posicoes armazenado no banco
- Indicador visual de status GPS no app do motoboy

---

## Endpoints da API (Resumo)

| Prefixo | Router | Endpoints | Descricao |
|---------|--------|-----------|-----------|
| `/restaurantes` | restaurantes.py | 3 | Signup, listar, detalhe |
| `/auth/cliente` | auth_cliente.py | 12 | Registro, login, perfil, enderecos, pedidos |
| `/site/{codigo}` | site_cliente.py | 16 | Info publica, categorias, produtos, combos, fidelidade, promocoes |
| `/carrinho` | carrinho.py | 7 | Adicionar, atualizar, remover, finalizar |
| `/pedidos` | pedidos.py | 2 | Criar, listar (restaurante) |
| `/api/gps` | gps.py | 3 | Update GPS, motoboys online, historico |
| `/api/upload` | upload.py | 1 | Upload de imagem (resize + WebP) |
| `/ws/{id}` | main.py | 1 | WebSocket por restaurante |

Documentacao completa: http://localhost:8000/docs

---

## Comandos Alembic

```bash
alembic upgrade head                          # Aplicar todas as migrations
alembic downgrade -1                          # Reverter ultima migration
alembic current                               # Ver versao atual
alembic history                               # Ver historico
alembic revision --autogenerate -m "descricao"  # Criar nova migration
```

---

## Cache e Performance (Site Cliente React)

O site cliente usa **React Query (TanStack Query v5)** para cache profissional:

| Dado | staleTime | Descricao |
|------|-----------|-----------|
| Site Info | 60 min | Nome, cores, horario — raramente muda |
| Categorias | 15 min | Categorias do cardapio |
| Produtos | 5 min | Produtos por categoria (placeholderData entre trocas) |
| Combos | 15 min | Combos e ofertas |
| Carrinho | 30 seg | Dado em tempo real |
| Pedidos | 1 min | Status pode mudar frequentemente |
| Enderecos | 5 min | Muda quando cliente edita |

**Hooks centrais**: `hooks/useQueries.ts` — todos os hooks React Query.
**Mutations**: invalidam cache automaticamente (ex: adicionar ao carrinho invalida `["carrinho"]`).

### Sessao e Autenticacao (Cliente)
- JWT token salvo em `localStorage` (sf_token) — sobrevive reload
- Cache do cliente em `localStorage` (sf_cliente) — evita flash de UI deslogada
- Interceptor 401 no axios — logout automatico quando token expira
- Sync multi-aba via StorageEvent — login/logout reflete em todas as abas

---

## Arquitetura Cloud — Escala para 1000+ Restaurantes

O Super Food esta sendo preparado para funcionar como SaaS completo na nuvem, suportando **1000+ restaurantes simultaneos** com seus respectivos sites, paineis e apps de motoboy.

### Visao Geral da Arquitetura de Producao

```
                        ┌──────────────────────────────┐
                        │     Cloudflare (CDN + WAF)    │
                        │   DNS, SSL, cache, protecao   │
                        └──────────────┬───────────────┘
                                       │
                        ┌──────────────▼───────────────┐
                        │      Caddy (Reverse Proxy)    │
                        │   SSL automatico, dominios     │
                        │   personalizados, wildcard     │
                        └──────────────┬───────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
     ┌────────▼────────┐    ┌─────────▼─────────┐    ┌────────▼────────┐
     │   FastAPI x N    │    │   React Static     │    │   Celery Workers │
     │   (Gunicorn)     │    │   (via CDN)        │    │   (tarefas bg)   │
     │   API + WebSocket│    │   3 SPAs:           │    │   - notificacoes │
     │                  │    │   - Site Cliente    │    │   - relatorios   │
     │                  │    │   - Painel Rest.    │    │   - cleanup      │
     │                  │    │   - App Motoboy     │    │                  │
     └────────┬────────┘    └───────────────────┘    └────────┬────────┘
              │                                                │
     ┌────────▼────────────────────────────────────────────────▼────┐
     │                    PostgreSQL (Principal)                     │
     │              PgBouncer (connection pooling)                   │
     │         Indices compostos em restaurante_id + ...             │
     └──────────────────────────────────────────────────────────────┘
              │                        │
     ┌────────▼────────┐    ┌─────────▼─────────┐
     │   Redis          │    │   S3 / R2          │
     │   - Cache menus  │    │   (Cloudflare R2)  │
     │   - Sessoes      │    │   - logos           │
     │   - Rate limit   │    │   - banners         │
     │   - Pub/Sub WS   │    │   - fotos produtos  │
     └─────────────────┘    └───────────────────┘
```

### Por que migrar de Streamlit para React

O Streamlit funciona por processo Python por sessao de usuario. Para 1000 restaurantes:

| Componente | Streamlit (atual) | React (planejado) |
|------------|-------------------|-------------------|
| RAM por usuario | ~50-100 MB (processo Python) | ~0 MB (static files via CDN) |
| 1000 restaurantes (3 usuarios cada) | 150-300 GB RAM | ~2 GB (apenas FastAPI) |
| Motoboys (5 por restaurante x 1000) | +250-500 GB RAM | ~0 MB (PWA statico) |
| CDN cache | Impossivel | Sim (React = arquivos estaticos) |
| PWA/Offline | Nao suportado | Suporte nativo |
| Push notifications | Nao suportado | Web Push API |
| GPS em background | Limitado (precisa aba aberta) | Service Worker |
| Load balancing | Complexo (estado local) | Trivial (API stateless) |

**Conclusao:** Streamlit e inviavel para mais de ~50 restaurantes simultaneos. React + FastAPI escala horizontalmente.

### Banco de Dados — PostgreSQL Multi-Tenant

O sistema usa **banco unico** com isolamento por `restaurante_id` em todas as 28 tabelas. Isso e a abordagem correta para ate ~5000 restaurantes.

**Requisitos para producao:**
- **PostgreSQL 16+** (substituir SQLite)
- **PgBouncer** para connection pooling (max ~200 conexoes reais, ~10000 virtuais)
- **Indices compostos** nas tabelas mais consultadas:
  - `pedidos(restaurante_id, status, data_criacao)`
  - `produtos(restaurante_id, categoria_id, disponivel)`
  - `motoboys(restaurante_id, disponivel, em_rota)`
  - `gps_motoboys(motoboy_id, timestamp)`
- **Read replicas** se necessario (leitura de cardapios em replica, escrita no primary)
- **Backups automaticos** (pg_dump diario + WAL archiving)

```env
# .env producao
DATABASE_URL=postgresql+psycopg2://superfood:senha@db.internal:5432/superfood
PGBOUNCER_URL=postgresql+psycopg2://superfood:senha@pgbouncer.internal:6432/superfood
```

### Armazenamento de Imagens — S3/R2 + CDN

Em producao, imagens NAO ficam no filesystem local. Cada restaurante pode ter:
- 1 logo + 1 banner + ~50 fotos de produtos = ~52 imagens
- 1000 restaurantes = ~52.000 imagens

**Stack recomendada:**
- **Cloudflare R2** (compativel S3, sem egress fee — mais barato que AWS S3)
- **CDN Cloudflare** para servir imagens (cache global)
- Estrutura: `r2://superfood-uploads/{restaurante_id}/{tipo}_{uuid}.webp`

**Fluxo:**
```
Upload via API → Pillow redimensiona → Salva no R2 → Retorna URL CDN
URL: https://cdn.superfood.com.br/uploads/123/logo_abc123.webp
```

### Dominios Personalizados

Cada restaurante pode ter:

**Nivel 1 — Subdominio automatico (incluso em todos os planos):**
```
pizzaria-do-ze.superfood.com.br     → Site do cliente
```
- Wildcard DNS: `*.superfood.com.br → IP do servidor`
- Wildcard SSL via Caddy ou Cloudflare
- FastAPI resolve subdominio → codigo_acesso do restaurante

**Nivel 2 — Dominio proprio do cliente (planos avancados):**
```
www.pizzariadoze.com.br → CNAME para custom.superfood.com.br
```
**Fluxo de configuracao:**
1. Restaurante digita seu dominio no painel (`www.pizzariadoze.com.br`)
2. Sistema gera instrucao: "Configure um CNAME apontando para `custom.superfood.com.br`"
3. Restaurante configura no registrador de dominio
4. Sistema verifica DNS (polling a cada 5 min por 48h)
5. Caddy emite SSL automaticamente via Let's Encrypt
6. Dominio ativo

**Tabela no banco:**
```
dominios_personalizados:
  id, restaurante_id, dominio, verificado, ssl_ativo, criado_em
```

**Middleware FastAPI:**
```python
# Resolve o Host header para identificar o restaurante
# 1. pizza.superfood.com.br → busca por subdominio
# 2. www.pizzariadoze.com.br → busca na tabela dominios_personalizados
# 3. superfood.com.br/cliente/CODIGO → busca por codigo_acesso (fallback atual)
```

### Docker Compose (Deploy)

```yaml
# docker-compose.prod.yml (simplificado)
services:
  api:
    build: .
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql+psycopg2://...
      REDIS_URL: redis://redis:6379
      S3_BUCKET: superfood-uploads
    depends_on: [db, redis]
    deploy:
      replicas: 3  # escala horizontal

  db:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]

  pgbouncer:
    image: edoburu/pgbouncer
    depends_on: [db]

  redis:
    image: redis:7-alpine

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
    volumes: [./Caddyfile:/etc/caddy/Caddyfile]
```

### Onboarding de Novo Restaurante (Fluxo SaaS)

Quando o super admin cria um restaurante, TUDO e automatico:

| Passo | Acao | Automatico? |
|-------|------|-------------|
| 1 | Criar registro no banco (restaurantes + config + site_config) | Sim |
| 2 | Gerar codigo_acesso unico | Sim |
| 3 | Site do cliente disponivel em `/{codigo}` ou subdominio | Sim |
| 4 | Painel do restaurante disponivel (login com email/senha) | Sim |
| 5 | App motoboy disponivel (login com codigo + usuario) | Sim |
| 6 | Pasta no S3 para uploads criada | Sim |
| 7 | Subdominio automatico ativo | Sim |
| 8 | Dominio personalizado (opcional) | Restaurante configura |

**Zero comandos manuais do dono do SaaS.** Tudo via painel super admin.

### Performance Estimada (1000 restaurantes)

| Recurso | Estimativa |
|---------|-----------|
| FastAPI (3 replicas, 4 workers cada) | ~12.000 req/s |
| PostgreSQL + PgBouncer | ~5.000 queries/s |
| Redis cache | ~100.000 ops/s |
| RAM total servidor | ~4-8 GB (API) + 2 GB (PostgreSQL) + 512 MB (Redis) |
| Armazenamento S3 | ~5 GB (imagens) |
| Bandwidth CDN | Cloudflare Free/Pro tier |

### Custos Estimados de Infraestrutura (USD)

| Restaurantes | VPS/Cloud | DB Managed | S3/R2 + CDN | Redis | Total USD | Total BRL (~R$6/USD) |
|-------------|-----------|------------|-------------|-------|-----------|----------------------|
| 100 | $40 (8GB) | $25 | $5 | $10 | **~$80/mes** | **~R$480/mes** |
| 500 | $120 (16GB) | $50 | $15 | $20 | **~$205/mes** | **~R$1.230/mes** |
| 1000 | $250 (32GB ou multi) | $80 | $25 | $30 | **~$385/mes** | **~R$2.310/mes** |

**Providers recomendados:** Hetzner (melhor custo), DigitalOcean, ou AWS Lightsail para VPS. Supabase ou Neon para PostgreSQL managed. Cloudflare R2 + CDN (sem taxa de egress). Upstash para Redis serverless.

> Com 1000 restaurantes pagando R$99/mes cada = R$99.000/mes de receita. Custo de infra ~R$2.310 = **~2.3% da receita**.

### Variaveis de Ambiente — Producao

```env
# Banco
DATABASE_URL=postgresql+psycopg2://superfood:SENHA_FORTE@db.internal:5432/superfood

# Auth
SECRET_KEY=chave_secreta_256_bits_gerada_com_openssl
JWT_ALGORITHM=HS256

# Mapbox
MAPBOX_TOKEN=pk.live_token_aqui

# Storage (S3/R2)
S3_ENDPOINT=https://ACCOUNT_ID.r2.cloudflarestorage.com
S3_ACCESS_KEY=chave_acesso
S3_SECRET_KEY=chave_secreta
S3_BUCKET=superfood-uploads
CDN_BASE_URL=https://cdn.superfood.com.br

# Redis
REDIS_URL=redis://redis.internal:6379/0

# App
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://superfood.com.br,https://*.superfood.com.br
BASE_DOMAIN=superfood.com.br
```

---

## Changelog

### v2.8.3 (07/02/2026)
- Ranking antifraude: config para permitir/bloquear finalizacao fora do raio de 50m
- UI Configuracoes: checkbox e aviso visual para opcao de antifraude

### v2.8.2 (03/02/2026)
- Correcoes: status de entregas, permissao GPS, notificacoes com som, erro removeChild
- Melhorias: toast temporario, status ABERTO/FECHADO, retirada de caixa, historico caixa

### v2.8.1 (02/02/2026)
- GPS em tempo real dos motoboys (a cada 10s)
- Mapa Folium no painel do restaurante
- 3 modos de despacho (rapido economico, cronologico, manual)
- API GPS completa (`/api/gps/*`)

### v2.8.0
- Login de motoboy com codigo do restaurante (isolamento multi-tenant)
- Capacidade de entregas configuravel por motoboy (1-20)
- Despacho automatico respeita capacidade

### v3.1.0 (14/02/2026)
- Fix bug upload logo/banner no painel restaurante (st.image com URL relativa)
- Plano de migracao v4.0 documentado (185 etapas, 8 sprints)
- Arquitetura cloud documentada (PostgreSQL, S3, Redis, Docker, dominios custom)

### v3.0+ (Site Cliente React SPA)
- React SPA completo: Home, ProductDetail, Cart, Checkout, Orders, Loyalty, Login, Account
- OrderTracking e OrderSuccess
- Redesign tema escuro profissional (11/02/2026)
- AuthContext com JWT + sync multi-aba
- RestauranteContext com CSS variables
- Hooks centralizados (useQueries.ts) com React Query
- apiClient.ts com 30+ funcoes e interceptors

---

## Roadmap

- [x] Fase 1-8: Sistema base, ORM, Alembic, motoboys, GPS, multi-tenant
- [x] Fase 9: Site Cliente React SPA (v3.0) — cardapio, carrinho, checkout, fidelidade
- [x] Fase 10: Redesign tema escuro profissional
- [ ] **Fase 11: MEGA MIGRACAO v4.0** — Streamlit → React + Cloud-Ready (em andamento)
  - Sprint 0: Correcoes pre-migracao (bugs, seguranca, limpeza)
  - Sprint 1: API endpoints para painel restaurante (64 endpoints)
  - Sprint 2: React SPA painel restaurante (32 telas)
  - Sprint 3: API endpoints para app motoboy (11 endpoints)
  - Sprint 4: React PWA app motoboy (14 telas + Service Worker + Push)
  - Sprint 5: API endpoints para super admin (10 endpoints)
  - Sprint 6: React SPA super admin (10 telas)
  - Sprint 7: Infraestrutura cloud (PostgreSQL, S3, Redis, Docker, dominios custom)
  - Sprint 8: Aposentar Streamlit (remover dependencia, release v4.0.0)
- [ ] Fase 12: Integracao iFood
- [ ] Fase 13: Recuperacao de senha por SMS (Twilio/AWS SNS)
- [ ] Fase 14: Push notifications para motoboy (Web Push API)
- [ ] Fase 15: App nativo (React Native ou Capacitor)

---

## Verificando se os Servicos Estao Rodando

```bash
# Verificar portas ativas
lsof -i :8000,:8501,:8502,:8503 | grep LISTEN

# Testar FastAPI
curl http://localhost:8000/
# Resposta: {"mensagem":"Super Food API - Site do Cliente ativo!"}

# Testar Swagger
# Abrir no navegador: http://localhost:8000/docs

# Logs dos servicos
tail -f /tmp/superfood_api.log
tail -f /tmp/superfood_admin.log
tail -f /tmp/superfood_restaurante.log
tail -f /tmp/superfood_motoboy.log
```

---

## Licenca

Este software e propriedade exclusiva do autor.
Uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para termos completos.

## Autor

Klenilton Silva - [@kleniltonsilva](https://github.com/kleniltonsilva)
