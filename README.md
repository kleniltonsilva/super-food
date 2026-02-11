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

**Versao atual: 2.8.3+ (10/02/2026)**

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

## Recomendacoes para Producao (1000+ restaurantes)

### Banco de Dados
- Migrar SQLite -> **PostgreSQL** antes de ir para cloud
- Connection pooling com pgBouncer

### Armazenamento de Imagens
- **S3/MinIO** para fotos de produtos, logos e banners
- CDN (CloudFront/Cloudflare) para servir imagens

### Cache
- **Redis** para cache de cardapios e sessoes de carrinho

### Deploy
- Docker Compose para desenvolvimento
- Docker + Kubernetes (ou ECS) para producao
- Nginx/Caddy como reverse proxy

### Subdominios em Producao
| Servico | URL |
|---------|-----|
| Site cliente | `superfood.com.br/cliente/CODIGO` |
| API | `api.superfood.com.br` |
| Dashboard | `painel.superfood.com.br` |
| Motoboy | `entregador.superfood.com.br` |
| Super Admin | `admin.superfood.com.br` |

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

### v3.0+ (Site Cliente React SPA)
- React SPA completo: Home, ProductDetail, Cart, Checkout, Orders, Loyalty, Login, Account
- OrderTracking e OrderSuccess
- AuthContext com JWT + sync multi-aba
- RestauranteContext com CSS variables
- Hooks centralizados (useQueries.ts) com React Query
- apiClient.ts com 30+ funcoes e interceptors

---

## Roadmap

- [x] Fase 1-8: Sistema base, Alembic, motoboys, GPS
- [x] Fase 9: Site Cliente React SPA (v3.0)
- [ ] Fase 10: Integracao iFood
- [ ] Fase 11: App nativo (WebView)
- [ ] Fase 12: Recuperacao de senha por SMS (Twilio/AWS SNS)
- [ ] Fase 13: Push notifications para motoboy (PWA)

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
