# Derekh Food - Plataforma SaaS para Gestao de Restaurantes

**AVISO DE LICENCA - IMPORTANTE**
Este repositorio NAO e open source. O codigo e PROPRIETARIO E CONFIDENCIAL.
Qualquer uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para os termos legais completos.

---

Sistema multi-tenant completo para gestao de restaurantes com entregas inteligentes, rastreamento GPS em tempo real, otimizacao de rotas (TSP), layouts tematicos por tipo de restaurante, analytics avancados e gestao financeira integrada.

## Visao Geral

O Derekh Food e composto por **10 aplicacoes principais**:

| Aplicacao | Tecnologia | Rota/URL | Descricao |
|-----------|------------|----------|-----------|
| **API Backend** | FastAPI + Uvicorn | `:8000` | API REST, WebSockets, serve React SPAs |
| **Super Admin** | React 19 | `/superadmin` | Painel administrativo do SaaS com analytics |
| **Painel Restaurante** | React 19 | `/admin` | Gestao completa do restaurante (22+ paginas) |
| **App Motoboy (PWA)** | React 19 | `/entregador` | App mobile para entregadores com GPS |
| **App KDS Cozinha (PWA)** | React 19 | `/cozinha` | Kitchen Display System para cozinheiros |
| **App Garcom (PWA)** | React 19 | `/garcom` | Atendimento mesa, pedidos por etapa |
| **Site Cliente** | React 19 | `/cliente/{codigo}` | Pedido online com 8 layouts tematicos |
| **Bridge Agent** | Python + Win32 | Windows exe | Intercepta impressoes de iFood/Rappi/etc. |
| **Sales Autopilot CRM** | FastAPI + Jinja2 | `derekh-crm.fly.dev` | CRM B2B prospeccao automatica (email + WA + IA) |
| **Evolution API** | Self-hosted | `derekh-evolution.fly.dev` | WhatsApp gateway (Baileys) |

**Versao atual: 4.0.1 (24/03/2026) — Em producao: https://superfood-api.fly.dev**

### Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Backend API | Python 3.12+ / FastAPI / Uvicorn |
| ORM | SQLAlchemy 2.0+ |
| Migrations | Alembic (34 migrations) |
| Banco (dev) | SQLite |
| Banco (prod) | PostgreSQL 16+ / PgBouncer |
| Frontend | React 19 + TypeScript + Vite 7 + Tailwind CSS 4 |
| State Management | TanStack Query v5 (React Query) |
| Router | wouter (nest mode) |
| UI Components | shadcn/ui (Radix UI) |
| Graficos | recharts (LineChart, PieChart, BarChart) |
| Carousel | embla-carousel |
| Mapas | Mapbox GL JS (mapas) + Mapbox API (geocoding, rotas) |
| Auth | JWT (HS256) via authlib + bcrypt (6 roles) |
| IA Parsing | Groq (Llama 3.3 70B) — parsing de cupons delivery |
| Imagens | Pillow (resize + WebP) / Cloudflare R2 (prod) |
| Cache | Redis (menus, sessoes, rate limit, Pub/Sub WS) |
| Algoritmos | TSP (Nearest Neighbor), Haversine, GPS antifraude |

---

## Pre-requisitos

- Python 3.12+
- Node.js 18+ e npm
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

# Instalar dependencias Python
pip install -r requirements.txt

# Instalar dependencias do React
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

# Build do React (producao)
cd restaurante-pedido-online && npm run build && cd ..
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

# Iniciar API FastAPI (serve todas as SPAs React)
./start_services.sh --api-only

# Desenvolvimento (API + Vite dev server com HMR)
# Terminal 1: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
# Terminal 2: cd restaurante-pedido-online && npm run dev
```

### Executar Servicos Individualmente

```bash
source venv/bin/activate

# FastAPI Backend (porta 8000) - serve todas as SPAs em producao
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# React - Desenvolvimento (porta 5173, proxy para API)
cd restaurante-pedido-online && npm run dev

# React - Build para producao (servido pelo FastAPI)
cd restaurante-pedido-online && npm run build
```

---

## Acessando o Sistema

| Servico | URL |
|---------|-----|
| API Docs (Swagger) | http://localhost:8000/docs |
| API Docs (ReDoc) | http://localhost:8000/redoc |
| Super Admin | http://localhost:8000/superadmin |
| Painel Restaurante | http://localhost:8000/admin |
| App Motoboy (PWA) | http://localhost:8000/entregador |
| App KDS Cozinha (PWA) | http://localhost:8000/cozinha |
| Site Cliente | http://localhost:8000/cliente/{CODIGO_RESTAURANTE} |
| Health Check | http://localhost:8000/health |

### Credenciais de Teste

| Aplicacao | Usuario/Email | Senha |
|-----------|---------------|-------|
| Super Admin | `superadmin` | `SuperFood2025!` |
| Restaurante Teste | `teste@superfood.com` | `123456` |
| Motoboy | Codigo do restaurante + usuario + senha | Configurado no cadastro |
| Cozinheiro (KDS) | Codigo do restaurante + login + senha | Configurado pelo admin |

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
│       ├── storage.py          # Abstração storage (Local / R2)
│       ├── cache.py            # Redis cache helper
│       ├── rate_limit.py       # Rate limiting (Redis sliding window)
│       ├── routers/            # 17 arquivos de rotas (130+ endpoints)
│       │   ├── auth_restaurante.py  # Auth JWT restaurante
│       │   ├── auth_cliente.py      # Auth cliente
│       │   ├── auth_motoboy.py      # Auth motoboy
│       │   ├── auth_cozinheiro.py   # Auth cozinheiro (KDS)
│       │   ├── auth_admin.py        # Auth super admin
│       │   ├── painel.py            # Todas rotas /painel/* (admin restaurante)
│       │   ├── admin.py             # Rotas /api/admin/* (super admin)
│       │   ├── site_cliente.py      # Rotas site publico
│       │   ├── carrinho.py          # Carrinho/checkout
│       │   ├── upload.py            # Upload imagens (JWT + Pillow)
│       │   ├── kds.py               # Endpoints KDS cozinha (pedidos, status, assumir)
│       │   ├── pix.py               # Endpoints Pix online (ativacao, saque, config)
│       │   ├── pix_webhooks.py      # Webhook Woovi/OpenPix (pagamentos Pix)
│       │   ├── integracoes.py        # Integracoes marketplace (iFood, Open Delivery)
│       │   ├── billing.py            # Billing restaurante (assinatura/pagamento)
│       │   ├── billing_admin.py      # Billing super admin (config, dashboard, acoes)
│       │   ├── billing_webhooks.py   # Webhook Asaas (pagamentos)
│       │   ├── pedidos.py           # Pedidos legado
│       │   └── motoboys.py          # GPS motoboys
│       ├── billing/            # Sistema de cobranca Asaas (PIX + Boleto)
│       │   ├── asaas_client.py      # httpx async (sandbox/prod)
│       │   ├── billing_service.py   # Logica trial/plano/pagamento/suspensao
│       │   └── billing_tasks.py     # Task periodica (30min) + polling
│       ├── pix/                # Pix online Woovi/OpenPix
│       │   └── woovi_service.py     # Client API Woovi (subcontas, cobranças, saques)
│       ├── integrations/       # iFood + Open Delivery clients
│       ├── schemas/            # Pydantic schemas
│       └── utils/              # Despacho, menus, templates
│
├── database/                   # SQLAlchemy ORM
│   ├── models.py               # 35+ modelos ORM (fonte de verdade)
│   ├── session.py              # get_db_session() + helpers
│   ├── base.py                 # Base declarativa
│   ├── init.py                 # Funcoes de inicializacao
│   └── seed/                   # Seeds (super admin, planos, restaurante, etc)
│
├── migrations/                 # Alembic (29 migrations)
│   └── versions/
│
├── restaurante-pedido-online/  # FRONTEND REACT (todas as SPAs)
│   ├── package.json            # Scripts: dev, build, check
│   ├── vite.config.ts          # Build config (proxy, aliases)
│   ├── tsconfig.json           # TypeScript config
│   ├── dist/public/            # BUILD OUTPUT (servido pelo FastAPI)
│   └── client/
│       └── src/
│           ├── main.tsx            # Entry point React
│           ├── App.tsx             # Router principal (5 apps: cliente, admin, motoboy, superadmin, kds)
│           ├── index.css           # Estilos globais + Tailwind + CSS vars tematicos
│           │
│           ├── pages/              # Paginas site cliente (11 paginas)
│           ├── components/         # Componentes UI compartilhados (shadcn + tematicos)
│           │   ├── ui/             # shadcn/radix-ui primitives
│           │   ├── site/           # Componentes tematicos do site
│           │   │   ├── RestauranteHeader.tsx    # Header adaptativo por tema
│           │   │   ├── HeroBanner.tsx           # Banner com fallback por tipo
│           │   │   ├── CategoryNav.tsx          # Nav categorias horizontal
│           │   │   ├── ProductCard.tsx          # Card produto tematico
│           │   │   ├── ProductCarousel.tsx      # Carousel embla (7+ itens)
│           │   │   ├── ComboSection.tsx         # Combos + ComboDetailModal
│           │   │   ├── CartSidebar.tsx          # Carrinho lateral/drawer
│           │   │   ├── FooterSection.tsx        # Footer 3 colunas
│           │   │   └── AgeVerification.tsx      # Verificacao idade (Bebidas)
│           │   ├── InfoTooltip.tsx  # Tooltip reutilizavel (icone ℹ️)
│           │   └── MapTracking.tsx  # Mapa rastreamento Mapbox GL
│           │
│           ├── config/
│           │   └── themeConfig.ts   # 8 temas visuais por tipo de restaurante
│           ├── hooks/              # Hooks cliente (useQueries, useCart, etc)
│           ├── contexts/           # RestauranteContext, AuthContext, ThemeContext
│           ├── lib/                # apiClient.ts (axios + JWT)
│           │
│           ├── admin/              # PAINEL ADMIN RESTAURANTE
│           │   ├── AdminApp.tsx    # Router admin (protegido)
│           │   ├── lib/            # adminApiClient.ts
│           │   ├── hooks/          # useAdminQueries.ts (64+ hooks), useWebSocket.ts
│           │   ├── pages/          # 22+ paginas (inclui CozinhaDigital, PagamentoPix)
│           │   │   ├── Dashboard.tsx         # Metricas + entregas ativas + alertas atraso
│           │   │   ├── Pedidos.tsx            # Lista + entregas em rota + timeline
│           │   │   ├── PedidoDetalhe.tsx      # Detalhe + timeline 5 passos
│           │   │   ├── Configuracoes.tsx      # Config restaurante + site (32 tooltips)
│           │   │   ├── Relatorios.tsx         # Vendas/Motoboys/Produtos + Analytics avancado
│           │   │   ├── MapaMotoboys.tsx       # Mapa GPS tempo real
│           │   │   └── ...                   # Categorias, Produtos, Combos, Motoboys, Caixa, etc
│           │   └── components/     # AdminLayout, Sidebar, Topbar
│           │
│           ├── motoboy/            # APP MOTOBOY (PWA)
│           │   ├── MotoboyApp.tsx   # Router motoboy
│           │   ├── lib/            # motoboyApiClient.ts
│           │   ├── hooks/          # useMotoboyQueries.ts, useGPS.ts
│           │   └── pages/          # Login, Home, Entrega, Ganhos, Historico
│           │
│           ├── kds/                # APP KDS COZINHA (PWA)
│           │   ├── KdsApp.tsx       # Router KDS (auth + WebSocket)
│           │   ├── lib/            # kdsApiClient.ts
│           │   ├── contexts/       # KdsAuthContext.tsx
│           │   ├── hooks/          # useKdsQueries.ts, useKdsWebSocket.ts (sons)
│           │   ├── components/     # KdsPrivateRoute.tsx
│           │   └── pages/          # KdsLogin, KdsMain (Preparo + Despacho)
│           │
│           └── superadmin/         # SUPER ADMIN
│               ├── SuperAdminApp.tsx  # Router super admin
│               ├── lib/            # superAdminApiClient.ts
│               ├── hooks/          # useSuperAdminQueries.ts
│               └── pages/          # Dashboard (analytics), Restaurantes, Planos, Inadimplentes
│
├── utils/                      # Utilitarios compartilhados
│   ├── mapbox_api.py           # Integracao Mapbox (geocoding, rotas)
│   ├── haversine.py            # Calculo de distancia offline (fallback)
│   ├── calculos.py             # Taxas de entrega e ganhos de motoboy
│   ├── motoboy_selector.py     # Selecao justa de motoboys (GPS 50m, rotacao)
│   └── tsp_optimizer.py        # Otimizacao de rotas (Nearest Neighbor)
│
├── infra/                      # Infraestrutura Docker/Cloud
│   ├── Dockerfile              # Multi-stage (Node build + Python API)
│   ├── docker-compose.yml      # Dev: postgres + redis + api
│   ├── docker-compose.prod.yml # Prod: + pgbouncer + caddy + replicas
│   └── Caddyfile               # Reverse proxy + SSL + wildcard
│
├── docs/                       # Documentacao extra
│   └── dominios-personalizados.md
│
├── alembic.ini                 # Config Alembic
├── requirements.txt            # Dependencias Python
├── init_database.py            # Inicializador do banco
├── start_services.sh           # Script para iniciar servicos
├── CLAUDE.md                   # Memoria tecnica (para IA)
├── ESTRUTURA.md                # Arvore de pastas + fluxo de dados
└── .env                        # Variaveis de ambiente
```

Para a arvore completa com descricoes detalhadas, veja `ESTRUTURA.md`.

---

## Funcionalidades Principais

### API FastAPI (Backend)
- API REST completa com 130+ endpoints documentados (Swagger/ReDoc)
- WebSockets para notificacoes em tempo real por restaurante (3 canais: restaurante, printer, kds)
- Servindo 5 React SPAs em producao (admin, motoboy, kds cozinha, superadmin, site cliente)
- Upload de imagens com resize automatico (WebP)
- JWT auth para restaurantes (24h), clientes (72h), motoboys (30d), cozinheiros (7d), super admin (12h)
- Rate limiting, cache Redis, health checks

### Site Cliente (8 Layouts Tematicos)
- **8 temas visuais**: Pizzaria, Hamburgueria, Acai/Sorvetes, Bebidas, Esfiharia, Restaurante, Salgados/Doces, Sushi
- Cardapio por categorias com busca e carousel
- Carrinho lateral (sidebar desktop / drawer mobile)
- Checkout com autocomplete de endereco (Mapbox) e calculo de taxa
- Combos: padrao, do dia (por dia da semana), kits festa (por quantidade de pessoas)
- Programa de fidelidade (pontos + premios)
- Promocoes com cupons
- Verificacao de idade (Bebidas)
- Montador de pizza (multi-sabores)
- Acompanhamento de pedido em tempo real

### Super Admin (Dashboard Analytics)
- Dashboard com analytics globais (faturamento real, pedidos, ticket medio)
- Top 5 restaurantes por faturamento (com medalhas)
- Graficos: tendencia faturamento, formas pagamento, tipos entrega
- Tabela "Saude dos Restaurantes" (pesquisavel/ordenavel)
- Alertas: restaurantes inativos, motoboys ociosos
- Insights: horario pico, crescimento MoM, clientes novos
- Gestao de restaurantes (CRUD, ativar/desativar)
- Controle de planos de assinatura (Basico, Essencial, Avancado, Premium)
- Gestao de inadimplencia com tolerancia configuravel
- **Billing/Assinatura**: dashboard MRR, config trial/suspensao, audit log, acoes por restaurante
- **Integracoes**: credenciais plataforma (iFood, Open Delivery) por restaurante
- **Dominios personalizados**: SSL automatico via Fly.io Certificates API

### Painel Restaurante (20+ Paginas)
- Dashboard com metricas + entregas ativas + alertas de atraso
- Pedidos com timeline visual 5 passos e deteccao de gargalo
- Despacho automatico com 3 modos (rapido economico, cronologico, manual)
- Gestao de cardapio (categorias drag & drop, produtos, variacoes, combos)
- Mapa GPS em tempo real (Mapbox GL JS)
- Controle de caixa (abertura, movimentacoes, fechamento)
- **Relatorios com aba Analytics protegida por senha** (projecoes, analise horario/dia, top produtos, recorrencia)
- **Cozinha Digital (KDS)**: CRUD cozinheiros, config tempo alerta/critico, monitor em tempo real
- **Pagamentos Pix Online**: ativacao com consentimento, saque manual/automatico, dashboard financeiro
- **Operadores de Caixa**: autenticacao para abrir/fechar caixa com senha
- **32 tooltips explicativos** em todas as configuracoes (ℹ️)
- Configuracao de taxas, raio, pagamentos, tema visual, SEO

### App KDS Cozinha (PWA)
- Login com codigo do restaurante + login + senha do cozinheiro
- **Tab PREPARO**: fila horizontal de pedidos com timer em tempo real, card comanda grande com itens/observacoes
- **Tab DESPACHO**: pedidos FEITOS aguardando despacho, historico PRONTO
- Status flow: NOVO → FAZENDO → FEITO → PRONTO (com timestamps)
- Filtro por produtos: cozinheiro com modo "individual" ve apenas pedidos contendo seus produtos
- Cores por tempo: verde (OK), ambar (alerta), vermelho (critico) com animacao pulse
- Sons via Web Audio API: novo pedido (880Hz+1174Hz), feito (523Hz), pronto (523+659+783Hz)
- WebSocket em tempo real (canal `ws:kds`)
- Auto-criacao de PedidoCozinha quando pedido muda para `em_preparo` e KDS ativo
- Admin: CRUD cozinheiros, config KDS (tempo alerta/critico, som), monitor em tempo real

### App Motoboy (PWA)
- Login com codigo do restaurante + usuario + senha
- Fluxo completo: em_rota → no_destino → pagamento → finalizar
- GPS em tempo real (watchPosition + envio 10s)
- Antifraude: finalizacao apenas a 50m do destino (configuravel)
- Notificacoes sonoras (Web Push API)
- Visualizacao de ganhos (base + extra) e historico
- Service Worker + manifest.json (instalavel como app)

---

## Sistema de Entregas Inteligente

### 3 Modos de Despacho

| Modo | Descricao |
|------|-----------|
| **Rapido Economico** | TSP por proximidade — otimiza combustivel. Seleciona motoboy com menos entregas no dia + mais proximo (GPS real) |
| **Cronologico Inteligente** | Agrupa pedidos por janela de tempo (10 min), depois aplica TSP no grupo |
| **Manual** | Restaurante atribui manualmente cada pedido a um motoboy |

### Selecao Justa de Motoboys

O algoritmo de selecao (`motoboy_selector.py`) garante distribuicao justa:

1. **Filtro disponibilidade**: apenas motoboys ONLINE + com capacidade + com GPS recente (<5 min)
2. **Prioridade hierarquica**: respeita ordem definida pelo restaurante
3. **Menos entregas no dia**: motoboy com menos corridas tem prioridade
4. **GPS real**: usa posicao GPS para calcular distancia ao restaurante
5. **Sem fallback**: se nenhum motoboy qualificado, retorna erro (nao despacha para inapto)

### Antifraude GPS

- Motoboy so pode finalizar entrega a **50m do endereco de destino** (configuravel via `permitir_finalizar_fora_raio`)
- Calculo de distancia via Haversine entre GPS do motoboy e coordenadas do pedido
- Configuracao no painel: ativar/desativar por restaurante

### Rastreamento GPS em Tempo Real

- Motoboy online envia GPS automaticamente a cada 10 segundos (`useGPS` hook)
- Mapa Mapbox GL JS no painel do restaurante (aba "Mapa")
- Historico de posicoes armazenado no banco
- Timeline visual de 5 passos no detalhe do pedido

### Entregas Ativas + Deteccao de Atraso

- Endpoint `GET /painel/entregas/ativas` retorna todas entregas em andamento com tempo decorrido
- Dashboard exibe banner vermelho pulsante quando ha entregas atrasadas
- Tolerancia de atraso configuravel (5/8/10/15 minutos) por restaurante
- Sons diferenciados: 880Hz (novo pedido), 440Hz (atraso), 523Hz (ajuste tempo)

### Diagnostico e Ajuste Automatico de Tempo

- Endpoint `GET /painel/entregas/diagnostico-tempo` analisa historico de entregas
- Calcula tempo medio real vs tempo estimado configurado
- Sugere ajustes automaticos baseados em dados reais
- Endpoint `POST /painel/entregas/ajustar-tempo` aplica sugestoes

---

## Layouts Tematicos (8 Tipos)

Cada restaurante pode escolher um tipo visual que altera **todo** o site do cliente:

| Tipo | Cores | Mood | Features Unicas |
|------|-------|------|-----------------|
| **Pizzaria** | Vermelho `#e4002e` + Rosa | Italiano/classico | Montador de pizza multi-sabores |
| **Hamburgueria** | Amarelo `#ffcd00` + Preto | Dark/urbano | Tema dark completo |
| **Acai/Sorvetes** | Roxo `#61269c` + Verde | Dessert/tropical | Upsell de adicionais com +/- |
| **Bebidas** | Vermelho `#e50e16` + Cinza | Clean/fresh | Verificacao de idade |
| **Esfiharia** | Laranja `#d4880f` + Marrom | Arabe/quente | — |
| **Restaurante** | Laranja `#ff990a` + Marrom | Casual/quente | Combos do dia (por dia da semana) |
| **Salgados/Doces** | Laranja `#ff883a` + Creme | Artesanal/festa | Kits festa (por quantidade de pessoas) |
| **Sushi** | Vermelho escuro `#a40000` + Carvao | Oriental/minimalista | Fonte cursiva Kaushan Script |

### Componentes Tematicos

Cada componente adapta-se automaticamente ao tema:

- **RestauranteHeader** — dark/light/pattern backgrounds
- **HeroBanner** — banner por tipo com fallback (`/themes/{tipo}/banner.png`)
- **CategoryNav** — scroll horizontal com cores adaptativas
- **ProductCard** — imagem circular (pizzaria) vs rounded, badges coloridos
- **ProductCarousel** — carousel embla para 7+ produtos
- **ComboSection** — agrupamento por tipo (padrao, do_dia, kit_festa)
- **CartSidebar** — sidebar 340px desktop / drawer mobile
- **FooterSection** — 3 colunas com cores do tema
- **AgeVerification** — modal verificacao idade (apenas Bebidas)

### CSS Variables Dinamicas

O tema e aplicado via 25+ CSS variables no `:root` + classe `theme-dark`/`theme-light` + atributo `data-theme`:

```css
--primary, --secondary, --background, --text-primary, --text-secondary,
--card-bg, --card-border, --header-bg, --footer-bg, --badge-color,
--price-color, --button-bg, --button-text, --nav-active, --nav-hover, ...
```

O restaurante pode sobrescrever cores primaria/secundaria no painel de configuracoes.

---

## Analytics Super Admin

### Dashboard Completo

O super admin acessa um dashboard com dados reais de **todos os restaurantes**:

- **Faturamento**: hoje, semana, mes, mes anterior (liquido vs bruto)
- **Pedidos**: hoje, mes, cancelamentos (%), ticket medio
- **Top 5 Restaurantes**: ranqueados por faturamento com medalhas ouro/prata/bronze
- **Graficos**: tendencia faturamento (LineChart), formas pagamento (PieChart), tipo entrega (PieChart)
- **Insights**: horario pico, clientes novos na semana, motoboys ociosos, crescimento MoM (%)
- **Alertas**: restaurantes inativos (0 pedidos em 7 dias) com banner amarelo
- **Tabela Saude**: pesquisavel por nome, ordenavel por qualquer coluna, badges de status (verde/amarelo/vermelho)

### Seletor de Periodo

- 7 dias / 30 dias / 90 dias
- staleTime: 60 segundos

---

## Relatorios Avancados do Restaurante

### Aba Analytics (Protegida por Senha)

Alem dos relatorios basicos (vendas, motoboys, produtos), o painel restaurante oferece uma aba **Analytics** com dados avancados protegida por senha dupla (JWT + senha do admin):

**Secoes:**

1. **Faturamento** — Mes atual, projecao anual, variacao vs anterior, ticket medio + grafico tendencia
2. **Quando Mais Vende** — Melhor dia da semana, horario pico, distribuicao por dia (BarChart) e por hora (BarChart)
3. **O Que Mais Vende** — Top 20 produtos (tabela), categorias mais vendidas (PieChart)
4. **Como Pagam** — Cards por forma de pagamento (Dinheiro, Cartao, PIX, Vale)
5. **Clientes** — Unicos no mes, novos, recorrentes (2+ pedidos), taxa de recorrencia
6. **Cancelamentos** — Total e taxa (%), grafico tendencia
7. **Previsao** — Projecao 3 meses (media movel ponderada), comparacao ano atual vs anterior
8. **Entregas vs Retiradas** — Proporacao (PieChart)

**Periodos disponiveis:** 30 dias, 90 dias, 12 meses, anual

**Logica de projecao:**
- Projecao anual = media dos ultimos 3 meses x 12
- Previsao proximos 3 meses = media movel ponderada (mes recente peso 3, anterior peso 2, outro peso 1)
- Comparacao anual = mes a mes quando existem dados do ano anterior

---

## Tooltips Explicativos

Todas as configuracoes do painel restaurante possuem tooltips (icone ℹ️) com explicacoes claras:

### Aba Restaurante (17 campos)
| Campo | Explicacao |
|-------|-----------|
| Status | Define se aceita pedidos (Aberto/Fechado/Pausado) |
| Horario Abertura/Fechamento | Horario de funcionamento exibido no site |
| Modo Prioridade Entrega | Rapido=TSP, Cronologico=agrupa tempo, Manual=operador |
| Tolerancia Atraso | Minutos extras antes de marcar entrega como atrasada |
| Max Pedidos por Rota | Pedidos por saida do motoboy (1-10) |
| Raio Entrega | Distancia maxima aceita (recusa no checkout) |
| Taxa Base / Dist. Base / KM Extra | Calculo de frete do cliente |
| Permitir Ver Saldo | Motoboy pode ver ganhos no app |
| Permitir Finalizar Fora Raio | Antifraude GPS (50m) |
| Aceitar Pedidos Auto | Pedidos do site aceitos automaticamente |
| Valor Base / KM Extra Motoboy | Pagamento do motoboy por entrega |
| Taxa Diaria / Valor Lanche | Beneficios fixos diarios |
| Endereco + Geocodificar | Converte endereco em GPS |

### Aba Site/Cardapio (15 campos)
| Campo | Explicacao |
|-------|-----------|
| Tipo Restaurante | Tema visual completo (cores, fontes, layout) |
| Cor Primaria/Secundaria | Sobrescreve cores do tema |
| Logo / Banner | Imagens do header e destaque |
| Pedido Minimo | Valor minimo em produtos (sem frete) |
| Tempo Entrega/Retirada | Exibido no site (ajuste automatico) |
| WhatsApp | Numero com DDD para botao de contato |
| Site Ativo | Desativado=site inacessivel |
| Pagamentos (4 switches) | Formas aceitas no checkout |
| Meta Title/Description | SEO — resultados do Google |

### Tooltips em Super Admin
- Novo Restaurante: 7 tooltips (Nome, CNPJ, Criar Site, Tipo, WhatsApp, Plano)
- Gerenciar Planos: 3 tooltips (Valor, Limite Motoboys, Descricao)
- Inadimplentes: 1 tooltip (Tolerancia dias)

---

## Endpoints da API (Resumo)

| Prefixo | Router | Endpoints | Descricao |
|---------|--------|-----------|-----------|
| `/auth/restaurante` | auth_restaurante.py | 4 | Login, me, perfil, senha |
| `/auth/cliente` | auth_cliente.py | 12 | Registro, login, perfil, enderecos, pedidos |
| `/auth/motoboy` | auth_motoboy.py | 2 | Login, me |
| `/auth/admin` | admin.py | 2 | Login super admin, me |
| `/painel` | painel.py | 50+ | Dashboard, pedidos, categorias, produtos, combos, motoboys, caixa, config, bairros, promocoes, fidelidade, relatorios, entregas, analytics |
| `/api/admin` | admin.py | 8 | Restaurantes, planos, metricas, inadimplentes, analytics |
| `/site/{codigo}` | site_cliente.py | 16 | Info publica, categorias, produtos, combos, fidelidade, promocoes |
| `/carrinho` | carrinho.py | 7 | Adicionar, atualizar, remover, finalizar |
| `/motoboy` | auth_motoboy.py | 8 | Entregas, status, estatisticas, ganhos |
| `/api/gps` | motoboys.py | 3 | Update GPS, motoboys online, historico |
| `/api/upload` | upload.py | 1 | Upload imagem (resize + WebP) |
| `/painel/billing` | billing.py | 5 | Status, planos, selecionar plano, faturas, PIX |
| `/api/admin/billing` | billing_admin.py | 9 | Config, dashboard MRR, audit log, acoes restaurante |
| `/webhooks/asaas` | billing_webhooks.py | 1 | Webhook Asaas (pagamentos) |
| `/painel/integracoes` | integracoes.py | 6 | Connect/disconnect iFood, Open Delivery |
| `/auth/cozinheiro` | auth_cozinheiro.py | 2 | Login, me (cozinheiro KDS) |
| `/kds` | kds.py | 5 | Pedidos KDS, status, assumir, refazer, config |
| `/painel/cozinha` | painel.py | 7 | CRUD cozinheiros, config KDS, dashboard cozinha |
| `/painel/pix` | pix.py | 6 | Ativar/desativar Pix, saque, config, status |
| `/webhooks/woovi` | pix_webhooks.py | 1 | Webhook Woovi/OpenPix (pagamentos Pix) |
| `/ws/{id}` | main.py | 1 | WebSocket por restaurante |
| `/ws/kds/{id}` | main.py | 1 | WebSocket KDS cozinha |
| `/garcom` | garcom.py | 12 | Mesas, sessoes, pedidos por etapa, itens esgotados |
| `/garcom/auth` | auth_garcom.py | 2 | Login, me (garcom) |
| `/painel/garcom` | painel.py | 6 | CRUD garcons, config, monitor mesas |
| `/painel/bridge` | bridge.py | 10 | Parse cupom (Groq IA), orders, patterns, status |
| `/ws/garcom/{id}` | main.py | 1 | WebSocket garcom |
| `/health` | main.py | 3 | Health check (live, ready, full) |

**Novos endpoints v4.0:**
- `GET /api/admin/analytics` — Analytics globais do super admin
- `GET /painel/relatorios/analytics` — Analytics avancado do restaurante (exige senha)
- `GET /painel/entregas/ativas` — Entregas em andamento com tempo real
- `GET /painel/entregas/diagnostico-tempo` — Diagnostico de tempos de entrega
- `POST /painel/entregas/ajustar-tempo` — Ajuste automatico de tempos
- `GET /painel/billing/status` — Status billing do restaurante
- `POST /painel/billing/selecionar-plano` — Selecionar/trocar plano
- `GET /api/admin/billing/dashboard` — Dashboard MRR + KPIs billing

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

## Cache e Performance

### React Query (TanStack Query v5)

| Dado | staleTime | Descricao |
|------|-----------|-----------|
| Site Info | 60 min | Nome, cores, horario — raramente muda |
| Categorias | 15 min | Categorias do cardapio |
| Produtos | 5 min | Produtos por categoria |
| Combos | 15 min | Combos e ofertas |
| Carrinho | 30 seg | Dado em tempo real |
| Pedidos | 1 min | Status muda frequentemente |
| Enderecos | 5 min | Muda quando cliente edita |
| Analytics (admin) | 60 seg | Dados agregados |
| Analytics (super admin) | 60 seg | Dados globais |

### Sessao e Autenticacao

| App | Token | localStorage Key | Expiracao |
|-----|-------|-------------------|-----------|
| Cliente | JWT | `sf_token` + `sf_cliente` | 72h |
| Admin Restaurante | JWT | `sf_admin_token` + `sf_admin_restaurante` | 24h |
| Motoboy | JWT | `sf_motoboy_token` + `sf_motoboy_data` | 30 dias |
| Cozinheiro (KDS) | JWT | `sf_kds_token` + `sf_kds_data` | 7 dias |
| Super Admin | JWT | `sf_superadmin_token` | 12h |

- Interceptor 401 no axios — logout automatico quando token expira
- Sync multi-aba via StorageEvent — login/logout reflete em todas as abas

### Backend

- **Redis cache** para cardapios e menus (invalidacao automatica)
- **Redis Pub/Sub** para WebSocket multi-instancia
- **Rate limiting** via sliding window (Redis)
- **GZip/Brotli** via middleware + Caddy em producao
- **Health checks**: `/health`, `/health/live`, `/health/ready`
- **Metricas**: `GET /metrics` (request count, latency, errors)

---

## Arquitetura Cloud — Escala para 1000+ Restaurantes

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
     │   FastAPI x N    │    │   React Static     │    │   Redis          │
     │   (Gunicorn)     │    │   (via CDN)        │    │   - Cache menus  │
     │   API + WebSocket│    │   5 SPAs:           │    │   - Rate limit   │
     │                  │    │   - Site Cliente    │    │   - Pub/Sub WS   │
     │                  │    │   - Painel Rest.    │    │                  │
     │                  │    │   - App Motoboy     │    │                  │
     │                  │    │   - App KDS Cozinha │    │                  │
     │                  │    │   - Super Admin     │    │                  │
     └────────┬────────┘    └───────────────────┘    └─────────────────┘
              │
     ┌────────▼────────────────────────────────────────────────────┐
     │                    PostgreSQL (Principal)                     │
     │              PgBouncer (connection pooling)                   │
     │         Indices compostos em restaurante_id + ...             │
     └──────────────────────────┬───────────────────────────────────┘
                                │
                       ┌────────▼────────┐
                       │   S3 / R2        │
                       │   (Cloudflare R2) │
                       │   logos, banners  │
                       │   fotos produtos  │
                       └─────────────────┘
```

### Banco de Dados — PostgreSQL Multi-Tenant

Banco unico com isolamento por `restaurante_id` em todas as 35+ tabelas:
- **PgBouncer** para connection pooling
- **45+ indices compostos** nas tabelas mais consultadas
- **Read replicas** se necessario

### Armazenamento de Imagens — S3/R2 + CDN

- **Cloudflare R2** (compativel S3, sem egress fee)
- **CDN Cloudflare** para servir imagens
- Estrutura: `r2://superfood-uploads/{restaurante_id}/{tipo}_{uuid}.webp`

### Dominios Personalizados

- **Subdominio automatico**: `pizzaria-do-ze.superfood.com.br` (incluso)
- **Dominio proprio**: CNAME para `custom.superfood.com.br` + SSL via Caddy

### Docker Compose

```yaml
services:
  api:
    build: .
    deploy:
      replicas: 3
    depends_on: [db, redis]

  db:
    image: postgres:16

  pgbouncer:
    image: edoburu/pgbouncer

  redis:
    image: redis:7-alpine

  caddy:
    image: caddy:2
    ports: ["80:80", "443:443"]
```

### Performance Estimada (1000 restaurantes)

| Recurso | Estimativa |
|---------|-----------|
| FastAPI (3 replicas, 4 workers) | ~12.000 req/s |
| PostgreSQL + PgBouncer | ~5.000 queries/s |
| Redis cache | ~100.000 ops/s |
| RAM total | ~4-8 GB (API) + 2 GB (DB) + 512 MB (Redis) |
| Armazenamento S3 | ~5 GB (imagens) |

---

## Changelog

### v4.0.0 (21/03/2026) — Mega Migracao React + Deploy Fly.io

- **Deploy em producao** — Fly.io GRU (Sao Paulo), PostgreSQL + Upstash Redis
- **Sprint 10 completo** — Streamlit 100% removido, sistema 100% React
- **Alembic em producao** — migrations automaticas no startup do Docker
- **Sprint 13** — Integracao iFood + Open Delivery (marketplace)
- **Sprint 14** — Credenciais plataforma (Super Admin) + refatoracao integracoes
- **Sprint 15** — Sistema de Billing/Assinatura com Asaas (PIX + Boleto): trial, planos, pagamento, suspensao, reativacao, webhook idempotente, audit log, dashboard MRR
- **Sprint 15.1** — Operadores de Caixa com autenticacao (abrir/fechar caixa com senha, migration 027)
- **Sprint 17** — Pix Online Woovi/OpenPix: subcontas, split de pagamento, saque automatico, QR Code, webhook (migration 028)
- **Sprint 18** — KDS / Comanda Digital: app PWA cozinha, CRUD cozinheiros, auto-criacao pedidos, WebSocket tempo real, sons Web Audio API, 2 tabs (Preparo + Despacho) (migration 029)
- **Sprint 19** — App Garcom: PWA atendimento mesa, sessoes, pedidos por etapa (course), transferencia mesa, itens esgotados, WebSocket garcom (migration 032)
- **Sprint 21** — Bridge Agent + Smart Client Lookup: interceptacao impressoes iFood/Rappi/14 plataformas, Groq IA (Llama 3.3 70B), ciclo auto-aprendizado de patterns, busca cliente por telefone (migration 033)
- **Sprint 22** — Feature Flags por Plano: 22 features em 4 tiers (Basico/Essencial/Avancado/Premium), 38 endpoints protegidos, useFeatureFlag hook, UpgradePrompt UI, landing page dinamica (migration 034)
- **Sales Autopilot CRM Automatico** — Email template branded (header Derekh + footer site/WA + unsub), regras de outreach configuráveis (CRUD + prioridade + match-all), auto-import leads a cada 30 min, WA inteligente as 09:30 (fora horario restaurante), deteccao trial + notificacao ao dono, UI regras no Autopilot dashboard
- **Demo WhatsApp Humanoide** — Modal interativo na landing page: 8 tipos restaurante × 20 cenarios cotidianos = 160 conversas unicas, chat animado com sons Web Audio API, brain replay mostrando raciocinio da IA, UI WhatsApp dark mode autentica, smartphone frame em desktop / full-screen em mobile

### v4.0.0-rc (11/03/2026) — Mega Migracao React + Features Avancadas
- **100% React** — Zero Streamlit. Todas 4 aplicacoes em React 19 + TypeScript
- **Painel Restaurante React** — 20+ paginas, 57 hooks, WebSocket tempo real
- **App Motoboy PWA** — React + Service Worker + GPS background + Push API
- **Super Admin React** — Dashboard com analytics globais completos
- **8 Layouts Tematicos** — Pizzaria, Hamburgueria, Acai, Bebidas, Esfiharia, Restaurante, Salgados, Sushi
- **Sistema de Entregas Inteligente** — 3 modos despacho, GPS 50m antifraude, selecao justa, timeline, diagnostico
- **Analytics Super Admin** — Faturamento real, top 5 restaurantes, saude por restaurante, tendencias
- **Relatorios Avancados** — Aba Analytics protegida por senha, projecoes, analise horario/dia
- **32 Tooltips** — Todas configuracoes documentadas com icone ℹ️
- **Combos avancados** — Do dia (por dia semana), kits festa (por quantidade pessoas)
- **Infraestrutura Cloud** — Docker, PostgreSQL, Redis, R2, Caddy, dominios custom, health checks
- **Auditoria completa** — Paridade funcional Streamlit/React verificada campo a campo

### v3.1.0 (14/02/2026)
- Fix bug upload logo/banner no painel restaurante
- Plano de migracao v4.0 documentado (343 etapas, 11 sprints)
- Arquitetura cloud documentada

### v3.0+ (Site Cliente React SPA)
- React SPA completo: Home, ProductDetail, Cart, Checkout, Orders, Loyalty
- AuthContext com JWT + sync multi-aba
- RestauranteContext com CSS variables
- Hooks centralizados com React Query

### v2.8.3 (07/02/2026)
- Ranking antifraude: config para permitir/bloquear finalizacao fora do raio de 50m

### v2.8.2 (03/02/2026)
- Correcoes: status de entregas, permissao GPS, notificacoes com som

### v2.8.1 (02/02/2026)
- GPS em tempo real dos motoboys (a cada 10s)
- 3 modos de despacho (rapido economico, cronologico, manual)

### v2.8.0
- Login de motoboy com codigo do restaurante
- Capacidade de entregas configuravel por motoboy

---

## Roadmap

- [x] Fases 1-8: Sistema base, ORM, Alembic, motoboys, GPS, multi-tenant
- [x] Fase 9: Site Cliente React SPA (v3.0)
- [x] Fase 10: Redesign tema escuro
- [x] **Fase 11: MEGA MIGRACAO v4.0** — Streamlit → React + Cloud-Ready
  - Sprint 0-8: API + React (painel, motoboy, super admin, site) + auditoria
  - Sprint 9: 8 layouts tematicos por tipo de restaurante
  - Sprint 10: Aposentar Streamlit (remover dependencias) ✅
  - Sprint 11: Deploy Fly.io (producao GRU) ✅
- [x] Fase 12: Integracao iFood + Open Delivery ✅
- [x] Fase 13: Sistema de Billing/Assinatura (Asaas) ✅
- [x] Fase 13.1: Operadores de Caixa (autenticacao abrir/fechar) ✅
- [x] Fase 14: Pix Online Woovi/OpenPix (split, subcontas, QR Code) ✅
- [x] Fase 15: KDS / Comanda Digital (app cozinha PWA, WebSocket, sons) ✅
- [x] Fase 16: App Garcom (atendimento mesa, sessoes, pedidos por etapa) ✅
- [x] Fase 17: Bridge Agent + Smart Client Lookup (interceptacao impressoes, Groq IA, auto-aprendizado) ✅
- [x] Fase 18: Feature Flags por Plano (22 features, 4 tiers, 38 endpoints protegidos) ✅
- [x] Fase 19: Sales Autopilot CRM Automatico (email branded + regras outreach + WA inteligente + auto-import + trial detection) ✅
- [x] Fase 19.1: Demo WhatsApp Humanoide na Landing Page (20 cenarios × 8 tipos = 160 conversas + brain replay) ✅
- [ ] Fase 20: WhatsApp Humanoide (atendimento IA humanizado 24h, sem menus robotizados — Premium incluso, demais +R$99,45/mês)

---

## Deploy — Fly.io (Producao)

O sistema esta em producao na Fly.io, regiao GRU (Sao Paulo):

**URL de producao:** https://superfood-api.fly.dev

### Infraestrutura Fly.io

| Recurso | Detalhes |
|---------|---------|
| App | `superfood-api` — GRU (Sao Paulo) |
| PostgreSQL | `superfood-db` — GRU, conectado via DATABASE_URL |
| Redis | Upstash (via Fly.io) — conectado via REDIS_URL |
| VM | shared-cpu-1x, 512MB RAM |
| Workers | 2 Gunicorn + Uvicorn |

### Fazer Deploy

```bash
# Instalar CLI (se nao tiver)
curl -L https://fly.io/install.sh | sh

# Login (conta: kleniltonportugal@gmail.com)
~/.fly/bin/fly auth login

# Deploy (na pasta raiz do projeto)
~/.fly/bin/fly deploy
```

O Dockerfile faz tudo automaticamente:
1. Build do React (Node 20)
2. Instala dependencias Python
3. Ao iniciar: `alembic upgrade head` (migrations automaticas)
4. Inicia Gunicorn com 2 workers Uvicorn

### Verificar Apos Deploy

```bash
# Ver logs em tempo real
~/.fly/bin/fly logs --app superfood-api

# Verificar status das maquinas
~/.fly/bin/fly status --app superfood-api

# Health check
curl https://superfood-api.fly.dev/health
# Resposta esperada: {"status":"healthy","checks":{"api":"ok","database":"ok","redis":"ok"}}
```

### Acesso em Producao

| Servico | URL |
|---------|-----|
| Super Admin | https://superfood-api.fly.dev/superadmin |
| Painel Restaurante | https://superfood-api.fly.dev/admin |
| App Motoboy | https://superfood-api.fly.dev/entregador |
| App KDS Cozinha | https://superfood-api.fly.dev/cozinha |
| Site Cliente | https://superfood-api.fly.dev/cliente/{CODIGO} |
| Health Check | https://superfood-api.fly.dev/health |

### Notas Importantes

- **Local vs Producao:** Local usa SQLite + `create_all` automatico. Producao usa PostgreSQL + Alembic.
- **Novas migrations:** Criar arquivo em `migrations/versions/` e rodar `fly deploy`.
- **Migrations PostgreSQL:** Usar `false`/`true` para booleanos (nao `0`/`1`).

---

## Verificando se o Sistema Esta Rodando (Local)

```bash
# Verificar porta ativa
lsof -i :8000 | grep LISTEN

# Testar FastAPI
curl http://localhost:8000/health
# Resposta: {"status":"healthy","checks":{"database":"ok",...}}

# Testar Swagger
# Abrir no navegador: http://localhost:8000/docs
```

---

## Licenca

Este software e propriedade exclusiva do autor.
Uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para termos completos.

## Autor

Klenilton Silva - [@kleniltonsilva](https://github.com/kleniltonsilva)
