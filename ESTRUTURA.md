# ESTRUTURA.md — Arvore de Pastas e Fluxo de Dados

Documento gerado em 10/02/2026. Descreve a estrutura completa do projeto Super Food com descricao de cada pasta/arquivo e diagramas de fluxo de dados.

---

## Arvore Completa do Projeto

```
super-food/
│
├── .env                                # Variaveis de ambiente (MAPBOX_TOKEN, SECRET_KEY, DATABASE_URL)
├── .streamlit/
│   └── config.toml                     # Config do Streamlit (tema, porta padrao)
├── alembic.ini                         # Config do Alembic (conexao, script location)
├── init_database.py                    # Script de inicializacao do banco + seeds
├── requirements.txt                    # Dependencias Python (fastapi, streamlit, sqlalchemy, etc)
├── run_production.py                   # Script Python para rodar todos os servicos
├── start_services.sh                   # Script shell para iniciar todos os servicos
├── super_food.db                       # Banco SQLite de desenvolvimento
├── CLAUDE.md                           # Memoria tecnica completa (para IA)
├── README.md                           # Documentacao para humanos
├── ESTRUTURA.md                        # Este arquivo
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                 BACKEND (FastAPI)                    ║
│   ╚══════════════════════════════════════════════════════╝
│
├── backend/
│   ├── __init__.py                     # Marca como pacote Python
│   ├── app.py                          # (legado) — nao usado
│   └── app/
│       ├── __init__.py
│       ├── main.py                     # App FastAPI principal
│       │                               #   - CORS (localhost:5173, 8504, 3000)
│       │                               #   - Inclui 7 routers
│       │                               #   - WebSocket /ws/{restaurante_id}
│       │                               #   - Serve React SPA em /cliente/{codigo}
│       │                               #   - Static files (uploads/)
│       │
│       ├── auth.py                     # Auth JWT para restaurantes
│       │                               #   - verify_password(), get_password_hash() — bcrypt + strip()
│       │                               #   - create_access_token() — JWT HS256, 24h
│       │                               #   - get_current_restaurante() — Dependency
│       │
│       ├── database.py                 # get_db() — Generator para FastAPI Depends()
│       ├── middleware.py               # Middleware customizado (se necessario)
│       ├── models.py                   # Re-exporta de database/models.py
│       │
│       ├── routers/                    # Endpoints da API (8 arquivos, 50+ endpoints)
│       │   ├── restaurantes.py         # /restaurantes — signup, listar, detalhe (3 endpoints)
│       │   ├── auth_cliente.py         # /auth/cliente — registro, login, perfil, enderecos, pedidos (12 endpoints)
│       │   ├── site_cliente.py         # /site/{codigo} — info publica, categorias, produtos, fidelidade (16 endpoints)
│       │   ├── carrinho.py             # /carrinho — adicionar, atualizar, remover, finalizar (7 endpoints)
│       │   ├── pedidos.py              # /pedidos — criar, listar para restaurante (2 endpoints)
│       │   ├── motoboys.py             # /motoboys — endpoints de motoboy (se houver)
│       │   ├── gps.py                  # /api/gps — update GPS, listar online, historico (3 endpoints)
│       │   └── upload.py               # /api/upload — upload imagem + resize WebP (1 endpoint)
│       │
│       ├── schemas/                    # Pydantic schemas (validacao entrada/saida)
│       │   ├── __init__.py             # Schemas legados (RestauranteBase/Create/Public, PedidoBase/Create/Public)
│       │   ├── site_schemas.py         # SiteInfoPublic, CategoriaPublic, ProdutoPublic, ComboPublic, etc
│       │   ├── carrinho_schemas.py     # AdicionarItemRequest, CarrinhoResponse, FinalizarCarrinhoRequest
│       │   └── cliente_schemas.py      # ClienteCadastro, Login, TokenResponse, Endereco, PedidoCliente
│       │
│       ├── utils/                      # Utilitarios do backend
│       │   ├── despacho.py             # Logica de despacho automatico
│       │   └── menu_templates.py       # Templates de cardapio por tipo de restaurante
│       │
│       ├── templates/                  # Templates HTML (Jinja2) — site legado
│       │   ├── base.html
│       │   └── site/
│       │       ├── home.html
│       │       └── cardapio.html
│       │
│       └── static/                     # Arquivos estaticos legado
│           └── css/
│               └── site_base.css
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║               DATABASE (SQLAlchemy ORM)              ║
│   ╚══════════════════════════════════════════════════════╝
│
├── database/
│   ├── __init__.py                     # Exporta modelos e sessao
│   ├── base.py                         # Base = declarative_base() — todas as models herdam
│   ├── models.py                       # 28 classes ORM (FONTE DE VERDADE do schema)
│   │                                   #   SuperAdmin, Restaurante, SiteConfig, ConfigRestaurante,
│   │                                   #   CategoriaMenu, TipoProduto, Produto, VariacaoProduto,
│   │                                   #   Cliente, EnderecoCliente, Carrinho, Pedido, ItemPedido,
│   │                                   #   Entrega, Motoboy, MotoboySolicitacao, RotaOtimizada,
│   │                                   #   Caixa, MovimentacaoCaixa, Notificacao, GPSMotoboy,
│   │                                   #   BairroEntrega, PontosFidelidade, TransacaoFidelidade,
│   │                                   #   PremioFidelidade, Promocao, Combo, ComboItem
│   │
│   ├── session.py                      # Gerenciamento de sessao
│   │                                   #   get_db_session() — para Streamlit (retorno direto)
│   │                                   #   get_db() — generator para FastAPI DI
│   │                                   #   criar_super_admin_padrao()
│   │                                   #   criar_config_padrao_restaurante()
│   │                                   #   criar_categorias_padrao_restaurante()
│   │
│   ├── init.py                         # Funcoes de inicializacao do banco
│   │
│   └── seed/                           # Dados iniciais (seeds)
│       ├── __init__.py
│       ├── base_seed.py                # Classe base para seeds
│       ├── seed_001_super_admin.py     # Cria superadmin / SuperFood2025!
│       ├── seed_002_planos.py          # Planos: Basico, Essencial, Avancado, Premium
│       ├── seed_003_restaurante_teste.py  # Restaurante demo
│       ├── seed_004_categorias_padrao.py  # Categorias de menu padrao
│       ├── seed_005_config_padrao.py   # ConfigRestaurante padrao
│       └── seed_006_produtos_pizzaria.py  # 23 produtos de pizzaria + variacoes
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                  MIGRATIONS (Alembic)                ║
│   ╚══════════════════════════════════════════════════════╝
│
├── migrations/
│   ├── env.py                          # Config do Alembic (target_metadata = Base.metadata)
│   ├── script.py.mako                  # Template para novas migrations
│   └── versions/                       # 12 migrations
│       ├── 001_initial_schema.py                       # Tabelas core
│       ├── 002_add_gps_motoboys_table.py               # GPS motoboys
│       ├── 003_add_site_cliente_schema.py              # Site config, categorias, produtos, clientes, carrinho
│       ├── 004_add_motoboy_selection_fields.py         # Campos de selecao justa
│       ├── 005_add_motoboy_usuario_unique_constraint.py # Unique (restaurante_id, usuario)
│       ├── 006_add_modo_prioridade_e_motivo_finalizacao.py # Modo despacho + motivo
│       ├── 007_add_missing_columns.py                  # Campos endereco restaurante
│       ├── 008_add_combos.py                           # Tabelas combos
│       ├── 009_add_max_sabores.py                      # max_sabores por variacao
│       ├── b7b9e66c_add_ranking_antifraude_fields.py   # Antifraude + CPF
│       ├── c6876da9_add_site_cliente_tables_fidelidade.py # Fidelidade, premios, promocoes
│       └── d494f82e_add_pagamento_real_fields.py       # Pagamento real (dinheiro vs cartao)
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║            REACT SPA (Site do Cliente)                ║
│   ╚══════════════════════════════════════════════════════╝
│
├── restaurante-pedido-online/
│   ├── package.json                    # Dependencias npm (react, vite, tailwind, radix, etc)
│   ├── package-lock.json
│   ├── tsconfig.json                   # Config TypeScript
│   ├── vite.config.ts                  # Vite config (proxy /api -> localhost:8000)
│   ├── components.json                 # Config do shadcn/ui
│   ├── todo.md                         # TODOs do frontend
│   │
│   ├── dist/                           # Build de producao (servido pelo FastAPI)
│   │   └── public/
│   │       ├── index.html
│   │       └── assets/
│   │
│   ├── client/
│   │   ├── .env.local                  # Variaveis de ambiente do React
│   │   ├── index.html                  # Entry point HTML (Vite)
│   │   │
│   │   └── src/
│   │       ├── main.tsx                # Entry point React
│   │       │                           #   - QueryClientProvider (React Query)
│   │       │                           #   - RestauranteProvider
│   │       │                           #   - AuthProvider
│   │       │                           #   - ThemeProvider
│   │       │
│   │       ├── App.tsx                 # Router principal (wouter) — 11 rotas
│   │       │                           #   / → Home
│   │       │                           #   /product/:id → ProductDetail
│   │       │                           #   /cart → Cart
│   │       │                           #   /checkout → Checkout
│   │       │                           #   /orders → Orders
│   │       │                           #   /order-success/:id → OrderSuccess
│   │       │                           #   /order/:id → OrderTracking
│   │       │                           #   /loyalty → Loyalty
│   │       │                           #   /login → Login
│   │       │                           #   /account → Account
│   │       │                           #   * → NotFound
│   │       │
│   │       ├── const.ts                # Constantes (RESTAURANTE_CODIGO, etc)
│   │       ├── index.css               # CSS global + Tailwind
│   │       │
│   │       ├── lib/
│   │       │   ├── apiClient.ts        # 30+ funcoes API (axios)
│   │       │   │                       #   - Interceptor: X-Session-ID + Bearer token
│   │       │   │                       #   - Interceptor 401: auto-logout
│   │       │   │                       #   - getSiteInfo, getCategorias, getProdutos
│   │       │   │                       #   - getCarrinho, adicionarAoCarrinho, finalizarPedido
│   │       │   │                       #   - loginCliente, registrarCliente, getClienteMe
│   │       │   │                       #   - getEnderecos, criarEndereco
│   │       │   │                       #   - getMeusPedidos, getCombos, getPromocoes
│   │       │   │                       #   - autocompleteEndereco, validarEntrega
│   │       │   │
│   │       │   └── utils.ts            # Utilitarios (cn, formatCurrency, etc)
│   │       │
│   │       ├── hooks/
│   │       │   ├── useQueries.ts       # HOOKS CENTRAIS React Query (QUERY_KEYS + hooks)
│   │       │   │                       #   Queries: useSiteInfo, useCategorias, useProdutos,
│   │       │   │                       #     useTodosProdutos, useCombos, useCarrinho,
│   │       │   │                       #     useMeusPedidos, useEnderecos, usePontosFidelidade,
│   │       │   │                       #     usePremiosFidelidade
│   │       │   │                       #   Mutations: useAdicionarCarrinho, useAtualizarQuantidade,
│   │       │   │                       #     useRemoverCarrinho, useLimparCarrinho,
│   │       │   │                       #     useFinalizarPedido, useCriarEndereco, useResgatarPremio
│   │       │   │
│   │       │   ├── useComposition.ts   # Hook de composicao de texto
│   │       │   ├── useMobile.tsx       # Detecta dispositivo mobile
│   │       │   └── usePersistFn.ts     # Persistir funcao callback
│   │       │
│   │       ├── contexts/
│   │       │   ├── RestauranteContext.tsx  # SiteInfo + CSS variables (--cor-primaria, --cor-secundaria)
│   │       │   ├── AuthContext.tsx         # JWT token (sf_token), cache cliente (sf_cliente)
│   │       │   │                          #   login(), logout(), register()
│   │       │   │                          #   Sync multi-aba via StorageEvent
│   │       │   └── ThemeContext.tsx        # Light/dark mode
│   │       │
│   │       ├── pages/                  # 11 paginas
│   │       │   ├── Home.tsx            # Cardapio: categorias, combos, produtos por secao
│   │       │   │                       #   Emoji/tema dinamico por tipo_restaurante
│   │       │   │                       #   Banner/hero section, rodape "Sobre"
│   │       │   │
│   │       │   ├── ProductDetail.tsx   # Detalhe do produto com variacoes agrupadas
│   │       │   │                       #   Selecao de tamanho, sabores, adicionais
│   │       │   │                       #   Emoji fallback dinamico
│   │       │   │
│   │       │   ├── Cart.tsx            # Carrinho: lista itens, +/-, remover, limpar
│   │       │   ├── Checkout.tsx        # Finalizar: endereco (autocomplete Mapbox),
│   │       │   │                       #   taxa calculada via API, forma pagamento, troco
│   │       │   │
│   │       │   ├── Orders.tsx          # Historico de pedidos (cliente logado)
│   │       │   ├── OrderSuccess.tsx    # Confirmacao pos-pedido
│   │       │   ├── OrderTracking.tsx   # Acompanhamento em tempo real
│   │       │   ├── Loyalty.tsx         # Programa fidelidade: pontos, premios, resgate
│   │       │   ├── Login.tsx           # Login/Cadastro de cliente
│   │       │   ├── Account.tsx         # Minha Conta: perfil, enderecos, logout
│   │       │   └── NotFound.tsx        # 404
│   │       │
│   │       └── components/
│   │           ├── ErrorBoundary.tsx    # Error boundary React
│   │           ├── ManusDialog.tsx      # Dialog customizado
│   │           ├── MapTracking.tsx      # Mapa de rastreamento de pedido
│   │           └── ui/                 # ~50 componentes Radix/shadcn
│   │               ├── accordion.tsx, alert.tsx, avatar.tsx, badge.tsx, button.tsx,
│   │               │   card.tsx, carousel.tsx, checkbox.tsx, dialog.tsx, drawer.tsx,
│   │               │   dropdown-menu.tsx, form.tsx, input.tsx, label.tsx, popover.tsx,
│   │               │   progress.tsx, radio-group.tsx, select.tsx, separator.tsx,
│   │               │   sheet.tsx, sidebar.tsx, skeleton.tsx, slider.tsx, sonner.tsx,
│   │               │   spinner.tsx, switch.tsx, table.tsx, tabs.tsx, textarea.tsx,
│   │               │   toggle.tsx, tooltip.tsx, ...
│   │               └── (+ mais ~20 componentes UI)
│   │
│   └── MODELOS DE RESTAURANTES/        # HTML de referencia de layouts (acai, bebidas,
│                                        #   esfiharia, hamburgueria, pizzaria, restaurante,
│                                        #   salgados, sushi)
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║              STREAMLIT APPS (Dashboards)             ║
│   ╚══════════════════════════════════════════════════════╝
│
├── streamlit_app/
│   ├── __init__.py
│   ├── super_admin.py                  # Painel Super Admin (porta 8501)
│   │                                   #   - Login SHA256
│   │                                   #   - CRUD restaurantes (tenants)
│   │                                   #   - Planos de assinatura
│   │                                   #   - Metricas globais
│   │
│   ├── restaurante_app.py             # Dashboard Restaurante (porta 8502) — ~1900 linhas
│   │                                   #   - Login SHA256
│   │                                   #   - Tabs: Pedidos, Cardapio, Motoboys, Mapa, Caixa, Config
│   │                                   #   - Criacao/gestao de pedidos
│   │                                   #   - Despacho automatico (3 modos)
│   │                                   #   - Gestao de cardapio (categorias, produtos, variacoes)
│   │                                   #   - Gestao de motoboys (cadastro, ranking)
│   │                                   #   - Mapa GPS Folium
│   │                                   #   - Controle de caixa
│   │                                   #   - Pagamento de motoboys (com export CSV)
│   │
│   └── cliente_app.py                 # Site do Cliente legado (Streamlit)
│                                       #   - Substituido pelo React SPA
│                                       #   - Mantido para retrocompatibilidade
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                APP MOTOBOY (PWA)                     ║
│   ╚══════════════════════════════════════════════════════╝
│
├── app_motoboy/
│   └── motoboy_app.py                 # App PWA Motoboy (porta 8503)
│                                       #   - Login: codigo restaurante + usuario + senha
│                                       #   - Recebe rotas otimizadas (TSP)
│                                       #   - Envia GPS a cada 10s
│                                       #   - Finaliza entregas com calculo de ganho
│                                       #   - Estatisticas do dia
│                                       #   - Toggle online/offline
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║              UTILS (Compartilhados)                  ║
│   ╚══════════════════════════════════════════════════════╝
│
└── utils/
    ├── __init__.py
    ├── mapbox_api.py                   # Integracao Mapbox
    │                                   #   - geocodificar_endereco(endereco) → (lat, lng)
    │                                   #   - obter_rota(origem, destino) → distancia_km, duracao_min
    │                                   #   - autocomplete(query) → sugestoes
    │
    ├── haversine.py                    # Calculo de distancia offline (fallback sem Mapbox)
    │                                   #   - calcular_distancia(lat1, lon1, lat2, lon2) → km
    │
    ├── calculos.py                     # Calculos de taxas e ganhos
    │                                   #   - calcular_taxa_entrega(distancia, config)
    │                                   #   - calcular_ganho_motoboy(distancia, config)
    │
    ├── motoboy_selector.py             # Selecao justa de motoboys
    │                                   #   - selecionar_motoboy(restaurante_id, db)
    │                                   #   - Filtra ONLINE + capacidade disponivel
    │                                   #   - Ordena por ordem_hierarquia (rotacao)
    │
    └── tsp_optimizer.py                # Otimizacao de rotas (Nearest Neighbor TSP)
                                        #   - otimizar_rota(pedidos, origem) → ordem otimizada
                                        #   - Usa distancias Haversine entre pontos
```

---

## Fluxo de Dados

### 1. Cliente faz pedido pelo React SPA

```
[React SPA - Browser]
        │
        │ POST /carrinho/adicionar
        │ Headers: X-Session-ID, Authorization (Bearer token se logado)
        ▼
[apiClient.ts]
        │ axios interceptor adiciona headers automaticamente
        ▼
[FastAPI - carrinho.py]
        │ Valida via Pydantic (AdicionarItemRequest)
        │ Busca sessao_id ou cria nova
        ▼
[SQLAlchemy ORM]
        │ Carrinho.query(restaurante_id=..., sessao_id=...)
        │ Produto.query(id=produto_id)
        │ VariacaoProduto.query(ids=variacoes_ids)
        ▼
[SQLite / PostgreSQL]
        │ INSERT/UPDATE carrinho (itens_json)
        ▼
[Resposta JSON - CarrinhoResponse]
        │ {id, sessao_id, itens[], valor_subtotal, valor_total}
        ▼
[React Query - useCarrinho()]
        │ Invalida cache ["carrinho"]
        │ Re-renderiza componentes que usam useCarrinho()
        ▼
[UI Atualizada - Cart.tsx]
```

### 2. Finalizar Pedido (Checkout)

```
[Checkout.tsx]
        │ Preenche: endereco, forma_pagamento, tipo_entrega
        │ Autocomplete endereco via Mapbox (apiClient.autocompleteEndereco)
        ▼
[apiClient.ts - finalizarPedido()]
        │ POST /carrinho/finalizar
        │ Body: FinalizarCarrinhoRequest
        ▼
[FastAPI - carrinho.py - finalizar_carrinho()]
        │
        ├── 1. Busca carrinho por sessao_id
        ├── 2. Geocodifica endereco (Mapbox ou coordenadas)
        ├── 3. Calcula distancia (Haversine)
        ├── 4. Calcula taxa de entrega (utils/calculos.py)
        ├── 5. Cria Pedido no banco
        ├── 6. Cria ItemPedido para cada item
        ├── 7. Vincula cliente_id se logado
        ├── 8. Limpa carrinho
        └── 9. Notifica restaurante via WebSocket
        ▼
[WebSocket /ws/{restaurante_id}]
        │ Broadcast: {"tipo": "novo_pedido", "pedido_id": ...}
        ▼
[Dashboard Restaurante (Streamlit)]
        │ Exibe novo pedido na lista
        │ Opcao de despacho automatico ou manual
```

### 3. Despacho de Entrega

```
[Dashboard Restaurante - restaurante_app.py]
        │ Pedido com status "pronto"
        │ Clica "Despachar" (ou automatico)
        ▼
[utils/motoboy_selector.py]
        │ Filtra motoboys ONLINE com capacidade
        │ Ordena por ordem_hierarquia
        │ Seleciona melhor candidato
        ▼
[utils/tsp_optimizer.py]
        │ Otimiza rota dos pedidos do motoboy
        │ Algoritmo: Nearest Neighbor
        │ Usa Haversine para distancias
        ▼
[SQLAlchemy ORM]
        │ Cria Entrega (motoboy_id, pedido_id, distancia_km, valor_motoboy)
        │ Cria RotaOtimizada (ordem_entregas JSON)
        │ Atualiza Motoboy (em_rota=True, entregas_pendentes++)
        ▼
[Notificacao (banco)]
        │ Cria notificacao para o motoboy
        ▼
[App Motoboy - motoboy_app.py]
        │ Polling detecta nova rota
        │ Exibe entregas na ordem otimizada
        │ Navega via Maps/Waze
```

### 4. Entrega e Calculo de Ganho

```
[App Motoboy - motoboy_app.py]
        │ Chega no endereco
        │ Registra forma de pagamento real
        │ Clica "Entrega Realizada"
        ▼
[SQLAlchemy ORM]
        │ Entrega.status = 'entregue'
        │ Entrega.entregue_em = datetime.utcnow()
        │ Entrega.motivo_finalizacao = 'entregue'
        │
        │ Calculo do ganho:
        │ ganho = valor_base_motoboy + max(0, distancia - distancia_base) × valor_km_extra
        │
        │ Motoboy.total_entregas += 1
        │ Motoboy.total_ganhos += ganho
        │ Motoboy.total_km += distancia
        │ Motoboy.entregas_pendentes -= 1
        │ Se entregas_pendentes == 0: em_rota = False
        ▼
[Pedido.status = 'entregue']
```

### 5. GPS em Tempo Real

```
[App Motoboy (a cada 10s)]
        │ navigator.geolocation.getCurrentPosition()
        ▼
[POST /api/gps/update]
        │ Body: {motoboy_id, latitude, longitude, velocidade}
        ▼
[FastAPI - gps.py]
        │ Cria GPSMotoboy no banco
        │ Atualiza Motoboy.latitude_atual, longitude_atual
        ▼
[Dashboard Restaurante - Aba Mapa]
        │ GET /api/gps/motoboys/{restaurante_id}
        │ Exibe marcadores no mapa Folium
        │ Auto-refresh a cada 10s
```

### 6. Autenticacao do Cliente

```
[Login.tsx]
        │ Email + Senha + Codigo Restaurante
        ▼
[apiClient.ts - loginCliente()]
        │ POST /auth/cliente/login
        ▼
[FastAPI - auth_cliente.py]
        │ Busca restaurante por codigo_acesso
        │ Busca cliente por email + restaurante_id
        │ Verifica senha (bcrypt + strip())
        │ Gera JWT (HS256, 72h)
        ▼
[Resposta: {access_token, token_type, cliente}]
        ▼
[AuthContext.tsx]
        │ Salva sf_token no localStorage
        │ Salva sf_cliente no localStorage (cache)
        │ Dispara StorageEvent (sync multi-aba)
        ▼
[apiClient.ts - interceptor]
        │ Adiciona Authorization: Bearer {token} em todas as requests
        │ Se 401: auto-logout
```

### 7. Fluxo de Dados Simplificado

```
┌─────────────┐     HTTP/JSON      ┌──────────────┐      ORM       ┌────────────┐
│  React SPA  │ ──────────────────► │   FastAPI    │ ──────────────► │  Database  │
│  (Browser)  │ ◄────────────────── │   (Python)   │ ◄────────────── │  (SQLite/  │
│             │     JSON Response   │              │   SQLAlchemy    │  PostgreSQL)│
└─────────────┘                     └──────┬───────┘                └────────────┘
                                           │
                                    WebSocket │
                                           │
                                    ┌──────▼───────┐
                                    │  Streamlit   │      ORM (direto)
┌─────────────┐     ORM (direto)    │  Dashboard   │ ──────────────────►
│ App Motoboy │ ───────────────────►│  Restaurant  │                    Database
│ (Streamlit) │                     └──────────────┘
└─────────────┘

Legenda:
- React SPA → FastAPI: via apiClient.ts (axios), autenticado com JWT
- Streamlit apps → Database: via get_db_session() (acesso direto ao ORM)
- FastAPI → Database: via get_db() (generator para DI)
- WebSocket: notificacoes em tempo real por restaurante
```

---

## Mapa de Dependencias entre Arquivos

```
database/models.py (28 models)
    ├── backend/app/models.py (re-exporta)
    ├── backend/app/routers/*.py (todos importam models)
    ├── streamlit_app/restaurante_app.py
    ├── streamlit_app/super_admin.py
    ├── streamlit_app/cliente_app.py
    └── app_motoboy/motoboy_app.py

database/session.py
    ├── streamlit_app/*.py (get_db_session)
    ├── app_motoboy/motoboy_app.py (get_db_session)
    └── backend/app/database.py (get_db - wrapper)

backend/app/schemas/*
    └── backend/app/routers/* (validacao)

apiClient.ts
    └── hooks/useQueries.ts (importa funcoes)
        └── pages/*.tsx (importam hooks)

contexts/RestauranteContext.tsx
    └── pages/*.tsx (via useRestaurante)

contexts/AuthContext.tsx
    └── pages/*.tsx (via useAuth)

utils/motoboy_selector.py
    └── streamlit_app/restaurante_app.py (despacho)

utils/tsp_optimizer.py
    └── streamlit_app/restaurante_app.py (otimizacao rota)

utils/calculos.py
    ├── streamlit_app/restaurante_app.py (taxas)
    ├── app_motoboy/motoboy_app.py (ganhos)
    └── backend/app/routers/carrinho.py (taxa entrega)

utils/mapbox_api.py
    ├── backend/app/routers/site_cliente.py (autocomplete)
    ├── backend/app/routers/carrinho.py (geocodificacao)
    └── streamlit_app/restaurante_app.py (geocodificacao)
```
