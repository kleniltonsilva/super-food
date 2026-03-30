# ESTRUTURA.md — Arvore de Pastas e Fluxo de Dados

Documento atualizado em 30/03/2026. Descreve a estrutura completa do projeto Derekh Food com descricao de cada pasta/arquivo e diagramas de fluxo de dados.

---

## Arvore Completa do Projeto

```
super-food/
│
├── .env                                # Variaveis de ambiente (MAPBOX_TOKEN, SECRET_KEY, DATABASE_URL)
├── alembic.ini                         # Config do Alembic (conexao, script location)
├── init_database.py                    # Script de inicializacao do banco + seeds
├── requirements.txt                    # Dependencias Python (fastapi, sqlalchemy, authlib, etc)
├── Dockerfile                          # Multi-stage build (Node 20 + Python 3.12)
├── fly.toml                            # Config Fly.io (superfood-api, regiao GRU)
├── super_food.db                       # Banco SQLite de desenvolvimento
├── CLAUDE.md                           # Memoria tecnica completa (para IA)
├── README.md                           # Documentacao para humanos
├── DOCUMENTACAO_TECNICA.md             # Documentacao tecnica detalhada
├── ESTRUTURA.md                        # Este arquivo
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                 BACKEND (FastAPI)                    ║
│   ╚══════════════════════════════════════════════════════╝
│
├── backend/
│   ├── __init__.py
│   └── app/
│       ├── __init__.py
│       ├── main.py                     # App FastAPI principal
│       │                               #   - CORS + Security headers middleware
│       │                               #   - 15+ routers incluidos
│       │                               #   - WebSocket /ws/{restaurante_id}, /ws/kds/{id}, /ws/garcom/{id}
│       │                               #   - Serve React SPA: /cliente/{codigo}, /admin, /superadmin,
│       │                               #     /entregador, /cozinha, /garcom, /onboarding
│       │                               #   - /metrics (Super Admin JWT), /health
│       │                               #   - GET /api/public/app-version (versao APK motoboy)
│       │                               #   - GET /api/public/downloads (lista downloads disponiveis)
│       │                               #   - Static files (uploads/)
│       │
│       ├── auth.py                     # Auth JWT centralizado (source of truth)
│       │                               #   - SECRET_KEY com validacao + warning em dev
│       │                               #   - verify_password(), get_password_hash() — bcrypt + strip()
│       │                               #   - create_access_token() — JWT HS256, 24h
│       │                               #   - 6 dependencies: restaurante, motoboy, admin, cozinheiro, garcom, cliente
│       │
│       ├── database.py                 # get_db() — Generator para FastAPI Depends()
│       ├── models.py                   # Re-exporta de database/models.py
│       ├── websocket_manager.py        # Redis Pub/Sub multi-worker WebSocket
│       │
│       ├── feature_flags.py            # Registry central features (PlanTier, 22 features, 4 tiers)
│       ├── feature_guard.py            # FastAPI Depends factory (verificar_feature)
│       ├── email_service.py            # Servico email transacional Resend
│       ├── email_templates.py          # Templates HTML emails (boas-vindas, credenciais)
│       │
│       ├── routers/                    # Endpoints da API (15+ arquivos, 200+ endpoints)
│       │   ├── painel.py               # /painel/* — admin restaurante (60+ endpoints)
│       │   ├── admin.py                # /api/admin/* — super admin (20+ endpoints)
│       │   ├── auth_restaurante.py     # Login/perfil restaurante
│       │   ├── auth_cliente.py         # Registro/login/perfil cliente
│       │   ├── auth_motoboy.py         # Login/cadastro motoboy
│       │   ├── auth_admin.py           # Login super admin
│       │   ├── site_cliente.py         # Site publico do restaurante
│       │   ├── carrinho.py             # Carrinho/checkout cliente
│       │   ├── motoboys.py             # Endpoints motoboy (GPS, entregas, ganhos)
│       │   ├── billing.py              # Billing restaurante (/painel/billing/*)
│       │   ├── billing_admin.py        # Billing super admin (/api/admin/billing/*)
│       │   ├── billing_webhooks.py     # Webhook Asaas (/webhooks/asaas)
│       │   ├── integracoes.py          # Integracoes marketplace (iFood, Open Delivery)
│       │   ├── garcom.py               # Endpoints garcom (mesas, sessoes, pedidos)
│       │   ├── bridge.py               # Bridge Printer (parse, orders, patterns)
│       │   └── upload.py               # Upload imagem JWT protegido
│       │
│       ├── billing/                    # Sistema de cobranca Asaas
│       │   ├── asaas_client.py         # httpx async client (sandbox/prod)
│       │   ├── billing_service.py      # Logica trial/plano/pagamento/suspensao
│       │   └── billing_tasks.py        # Task periodica (30min) + polling fallback
│       │
│       ├── bot/                        # WhatsApp Humanoide (Bot IA)
│       │   ├── atendente.py            # Main loop: anti-spam, dedup, humanized delay
│       │   ├── context_builder.py      # 3 camadas prompt (system, restaurant, client)
│       │   ├── function_calls.py       # 24 function calls (pedido, pagamento, avaliacao, etc)
│       │   ├── xai_llm.py             # grok-3-fast, temp 0.6, max 400 tokens
│       │   ├── xai_tts.py             # TTS com pronuncia Derekh→Derikh
│       │   ├── groq_stt.py            # Groq Whisper whisper-large-v3-turbo
│       │   ├── evolution_client.py     # API Evolution (texto, audio, rejeitar chamada)
│       │   └── workers.py             # Avaliacoes pos-entrega, deteccao atraso, reset tokens
│       │
│       ├── integrations/              # iFood + Open Delivery
│       │   ├── ifood/                 # client.py, mapper.py, status_machine.py, catalog_sync.py
│       │   ├── opendelivery/          # client.py, mapper.py
│       │   ├── base.py, manager.py
│       │
│       ├── utils/                     # Helpers (despacho, menus, comanda, origem)
│       │   ├── despacho.py            # Logica de despacho automatico
│       │   ├── menu_templates.py      # Templates de cardapio por tipo de restaurante
│       │   └── origem_helper.py       # Helper para tipo/label origem pedido
│       │
│       ├── templates/                 # Templates HTML (Jinja2)
│       │   ├── landing.html           # Landing page vendas (Tailwind CDN)
│       │   └── site/                  # Templates legados
│       │
│       └── static/                    # Arquivos estaticos
│           ├── chefe-robo-derekh.png  # Logo IA chef (1024x1024)
│           ├── logo-derekh.png        # Logo principal
│           └── uploads/               # Volume Fly.io (imagens, downloads)
│               └── downloads/         # APKs e executaveis
│                   ├── DerekhFood-Entregador.apk
│                   └── DerekhFood-Bridge.exe
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║               DATABASE (SQLAlchemy ORM)              ║
│   ╚══════════════════════════════════════════════════════╝
│
├── database/
│   ├── __init__.py                     # Exporta modelos e sessao
│   ├── base.py                         # Base = declarative_base()
│   ├── models.py                       # 40+ classes ORM (FONTE DE VERDADE do schema)
│   │                                   #   SuperAdmin, Restaurante, SiteConfig, ConfigRestaurante,
│   │                                   #   CategoriaMenu, TipoProduto, Produto, VariacaoProduto,
│   │                                   #   Cliente, EnderecoCliente, Carrinho, Pedido, ItemPedido,
│   │                                   #   Entrega, Motoboy, MotoboySolicitacao, RotaOtimizada,
│   │                                   #   Caixa, MovimentacaoCaixa, Notificacao, GPSMotoboy,
│   │                                   #   BairroEntrega, PontosFidelidade, TransacaoFidelidade,
│   │                                   #   PremioFidelidade, Promocao, Combo, ComboItem,
│   │                                   #   Cozinheiro, CozinheiroProduto, PedidoCozinha, ConfigCozinha,
│   │                                   #   Garcom, GarcomMesa, ConfigGarcom, SessaoMesa, SessaoPedido,
│   │                                   #   ItemEsgotado, BridgePattern, BridgeInterceptedOrder,
│   │                                   #   FeatureFlag, RestauranteAddon, PlanoPreco,
│   │                                   #   BotConfig, BotConversa, BotMensagem, BotAvaliacao,
│   │                                   #   BotProblema, BotRepescagem, PixTransacao,
│   │                                   #   EmailVerification, SolicitacaoCadastro
│   │
│   ├── session.py                      # Gerenciamento de sessao
│   │                                   #   get_db_session(), get_db() (FastAPI DI)
│   │                                   #   criar_super_admin_padrao()
│   │                                   #   criar_config_padrao_restaurante()
│   │
│   ├── init.py                         # Funcoes de inicializacao do banco
│   └── seed/                           # Dados iniciais (seeds)
│       ├── seed_001_super_admin.py     # superadmin / SuperFood2025!
│       ├── seed_002_planos.py          # Basico, Essencial, Avancado, Premium
│       ├── seed_003_restaurante_teste.py
│       ├── seed_004_categorias_padrao.py
│       ├── seed_005_config_padrao.py
│       └── seed_006_produtos_pizzaria.py
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                  MIGRATIONS (Alembic)                ║
│   ╚══════════════════════════════════════════════════════╝
│
├── migrations/
│   ├── env.py                          # Config Alembic (target_metadata = Base.metadata)
│   ├── script.py.mako                  # Template para novas migrations
│   └── versions/                       # 42 migrations (001-036, 039-042)
│       ├── 001_initial_schema.py                          # Tabelas core
│       ├── 002-009                                        # GPS, site, motoboy, combos, sabores
│       ├── 010-019                                        # Painel admin, tipos, endpoints, integracoes
│       ├── 020-027                                        # Billing, feature flags, planos, caixa
│       ├── 028_pix_online.py                              # Pix online (Woovi)
│       ├── 029_kds_cozinha.py                             # KDS cozinha digital
│       ├── 030_garcom.py                                  # (reservado)
│       ├── 031_kds_pausar.py                              # Pausar pedido cozinha
│       ├── 032_garcom_mesas.py                            # App garcom + mesas
│       ├── 033_bridge_patterns.py                         # Bridge printer patterns
│       ├── 034_feature_flags.py                           # Feature flags por plano
│       ├── 035_bot_whatsapp.py                            # Bot WhatsApp Humanoide
│       ├── 036_bot_improvements.py                        # Melhorias bot (handoff, etc)
│       ├── 039_repescagem_email.py                        # Repescagem + verificacao email
│       ├── 040_pix_payment_link.py                        # Pix payment link URL
│       ├── 041_addon_bot_whatsapp.py                      # Add-on bot WhatsApp
│       └── 042_solicitacao_cadastro.py                    # Landing page + onboarding
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║          REACT SPA — 7 APLICACOES FRONTEND           ║
│   ╚══════════════════════════════════════════════════════╝
│
├── restaurante-pedido-online/
│   ├── package.json                    # Dependencias npm (react 19, vite 7, tailwind 4, etc)
│   ├── package-lock.json
│   ├── tsconfig.json                   # Config TypeScript
│   ├── vite.config.ts                  # Vite config (proxy /api -> localhost:8000)
│   ├── components.json                 # Config shadcn/ui
│   │
│   ├── dist/                           # Build de producao (servido pelo FastAPI)
│   │   └── public/
│   │       ├── index.html
│   │       └── assets/
│   │
│   └── client/
│       ├── index.html                  # Entry point HTML (Vite)
│       └── src/
│           ├── main.tsx                # Entry point React (QueryClient, Router)
│           ├── App.tsx                 # Router principal (wouter) — rotas por prefixo:
│           │                           #   /admin/* → AdminApp
│           │                           #   /superadmin/* → SuperAdminApp
│           │                           #   /entregador/* → MotoboyApp
│           │                           #   /cozinha/* → KdsApp
│           │                           #   /garcom/* → GarcomApp
│           │                           #   /onboarding → Landing
│           │                           #   /cliente/{codigo}/* → Site Cliente
│           │
│           ├── const.ts                # Constantes globais
│           ├── index.css               # CSS global + Tailwind
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 1 — Site Cliente (/cliente/{codigo}) │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── pages/                  # 13 paginas do site cliente
│           │   ├── Home.tsx            # Cardapio: categorias, combos, produtos
│           │   ├── ProductDetail.tsx   # Detalhe com variacoes/sabores/adicionais
│           │   ├── Cart.tsx            # Carrinho
│           │   ├── Checkout.tsx        # Finalizar: endereco Mapbox, taxa, pagamento
│           │   ├── Orders.tsx          # Historico pedidos
│           │   ├── OrderSuccess.tsx    # Confirmacao pos-pedido
│           │   ├── OrderTracking.tsx   # Rastreamento tempo real (mapa)
│           │   ├── Loyalty.tsx         # Programa fidelidade
│           │   ├── Login.tsx           # Login/cadastro cliente
│           │   ├── Account.tsx         # Minha conta
│           │   ├── Landing.tsx         # Landing page onboarding (/onboarding)
│           │   └── NotFound.tsx        # 404
│           │
│           ├── lib/
│           │   ├── apiClient.ts        # 30+ funcoes API (axios), interceptors JWT + 401
│           │   └── utils.ts            # cn, formatCurrency, etc
│           │
│           ├── hooks/
│           │   └── useQueries.ts       # Hooks React Query (site cliente)
│           │
│           ├── contexts/
│           │   ├── RestauranteContext.tsx  # SiteInfo + CSS variables (--cor-primaria)
│           │   ├── AuthContext.tsx         # JWT (sf_token), auto-logout
│           │   └── ThemeContext.tsx        # Light/dark mode
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 2 — Painel Admin (/admin)           │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── admin/
│           │   ├── AdminApp.tsx         # Router admin (20+ rotas)
│           │   ├── pages/              # 20+ paginas admin
│           │   │   ├── Dashboard.tsx        # Dashboard principal (metricas, graficos)
│           │   │   ├── Pedidos.tsx           # Gestao de pedidos
│           │   │   ├── Cardapio.tsx          # CRUD categorias/produtos/variacoes
│           │   │   ├── Motoboys.tsx          # CRUD motoboys
│           │   │   ├── Clientes.tsx          # Lista clientes
│           │   │   ├── Caixa.tsx             # Controle de caixa
│           │   │   ├── Configuracoes.tsx     # Config restaurante
│           │   │   ├── Relatorios.tsx        # Relatorios (vendas, produtos, clientes)
│           │   │   ├── Integracoes.tsx       # iFood, Open Delivery
│           │   │   ├── Billing.tsx           # Assinatura e plano
│           │   │   ├── CozinhaDigital.tsx    # Config KDS + cozinheiros
│           │   │   ├── Garcons.tsx           # Config garcons + mesas
│           │   │   ├── BotWhatsApp.tsx       # Config bot IA (3 abas)
│           │   │   ├── BridgePrinter.tsx     # Bridge impressora (interceptados + padroes)
│           │   │   ├── Downloads.tsx         # Downloads (APK motoboy + agents Windows)
│           │   │   ├── NovoPedido.tsx        # Criar pedido manual
│           │   │   ├── Fidelidade.tsx        # Programa fidelidade
│           │   │   ├── Promocoes.tsx         # Gestao de promocoes
│           │   │   └── Bairros.tsx           # Bairros + taxas entrega
│           │   │
│           │   ├── components/         # Componentes especificos admin
│           │   ├── hooks/
│           │   │   ├── useAdminQueries.ts  # 57+ hooks React Query
│           │   │   └── useFeatureFlag.ts   # Feature flags UI
│           │   ├── contexts/
│           │   │   ├── AdminAuthContext.tsx  # JWT admin (sf_admin_token)
│           │   │   └── ThemeContext.tsx
│           │   └── lib/
│           │       └── adminApiClient.ts    # API client + interceptor feature_blocked
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 3 — Super Admin (/superadmin)       │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── superadmin/
│           │   ├── SuperAdminApp.tsx    # Router super admin
│           │   ├── pages/
│           │   │   ├── SADashboard.tsx       # Dashboard global
│           │   │   ├── SARestaurantes.tsx    # CRUD restaurantes (tenants)
│           │   │   ├── SABilling.tsx         # Billing global
│           │   │   ├── Solicitacoes.tsx      # Solicitacoes de cadastro (onboarding)
│           │   │   └── SAConfiguracoes.tsx   # Config plataforma
│           │   ├── hooks/
│           │   │   └── useSuperAdminQueries.ts  # Hooks super admin
│           │   └── lib/
│           │       └── superAdminApiClient.ts
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 4 — App Motoboy PWA (/entregador)   │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── motoboy/
│           │   ├── MotoboyApp.tsx       # Router motoboy (6 rotas)
│           │   ├── pages/
│           │   │   ├── MotoboyLogin.tsx      # Login + banner instalar app nativo
│           │   │   ├── MotoboyCadastro.tsx   # Solicitar cadastro
│           │   │   ├── MotoboyDownload.tsx   # Pagina download APK + instrucoes
│           │   │   ├── MotoboyHome.tsx       # Home (status, entregas, mapa)
│           │   │   ├── MotoboyEntrega.tsx    # Detalhe entrega em andamento
│           │   │   ├── MotoboyGanhos.tsx     # Historico ganhos
│           │   │   └── MotoboyPerfil.tsx     # Perfil motoboy
│           │   ├── hooks/
│           │   │   ├── useMotoboyQueries.ts  # 14 hooks
│           │   │   ├── useGPS.ts             # GPS browser (watchPosition)
│           │   │   └── useMotoboyWebSocket.ts
│           │   ├── contexts/
│           │   │   └── MotoboyAuthContext.tsx  # JWT motoboy (sf_motoboy_token)
│           │   ├── components/
│           │   │   └── MotoboyPrivateRoute.tsx
│           │   └── lib/
│           │       └── motoboyApiClient.ts
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 5 — KDS Cozinha PWA (/cozinha)      │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── kds/
│           │   ├── KdsApp.tsx           # Router KDS (login, preparo, despacho)
│           │   ├── pages/
│           │   │   ├── KdsLogin.tsx          # Login cozinheiro (dark theme)
│           │   │   ├── KdsPreparo.tsx        # Fila horizontal + comanda + COMECEI/FEITO
│           │   │   └── KdsDespacho.tsx       # Pedidos FEITOS + PRONTO + REFAZER
│           │   ├── hooks/
│           │   │   └── useKdsQueries.ts     # Hooks KDS
│           │   ├── contexts/
│           │   │   └── KdsAuthContext.tsx    # JWT cozinheiro
│           │   └── lib/
│           │       └── kdsApiClient.ts
│           │
│           │   ┌─────────────────────────────────────────┐
│           │   │  APP 6 — App Garcom PWA (/garcom)        │
│           │   └─────────────────────────────────────────┘
│           │
│           ├── garcom/
│           │   ├── GarcomApp.tsx         # Router garcom
│           │   ├── pages/
│           │   │   ├── GarcomLogin.tsx       # Login garcom (dark amber theme)
│           │   │   ├── GarcomHome.tsx        # Grid mesas (LIVRE/ABERTA/FECHANDO)
│           │   │   ├── GarcomMesa.tsx        # Detalhe mesa (pedidos, conta)
│           │   │   ├── GarcomCardapio.tsx    # Cardapio + carrinho + course
│           │   │   └── GarcomTransferir.tsx  # Transferir mesa
│           │   ├── hooks/
│           │   │   └── useGarcomQueries.ts  # Hooks garcom
│           │   ├── contexts/
│           │   │   └── GarcomAuthContext.tsx # JWT garcom
│           │   └── lib/
│           │       └── garcomApiClient.ts
│           │
│           └── components/             # Componentes compartilhados
│               ├── ErrorBoundary.tsx
│               ├── MapTracking.tsx      # Mapa rastreamento (Mapbox GL)
│               └── ui/                 # ~50 componentes Radix/shadcn
│                   ├── accordion, alert, avatar, badge, button, card,
│                   │   carousel, checkbox, dialog, drawer, dropdown-menu,
│                   │   form, input, label, popover, progress, radio-group,
│                   │   select, separator, sheet, sidebar, skeleton, slider,
│                   │   sonner, spinner, switch, table, tabs, textarea,
│                   │   toggle, tooltip, ...
│                   └── (+ mais ~20 componentes UI)
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║     APP MOTOBOY NATIVO — Android (CapacitorJS)       ║
│   ╚══════════════════════════════════════════════════════╝
│
├── motoboy-app/                        # Projeto Capacitor separado (APK Android)
│   ├── package.json                    # Deps: @capacitor/core, android, geolocation, app, device
│   ├── capacitor.config.ts             # appId: food.derekh.entregador, webDir: dist
│   ├── vite.config.ts                  # Alias @ → monorepo src (reutiliza 100% codigo)
│   ├── tsconfig.json                   # Herda paths do monorepo
│   ├── index.html                      # Entry point HTML
│   ├── version.json                    # {"version": "1.0.0", "versionCode": 1}
│   │
│   ├── src/
│   │   ├── main.tsx                    # Entry point (importa MotoboyApp do monorepo)
│   │   ├── App.tsx                     # Wrapper: update checker + GPS background
│   │   └── native/
│   │       ├── gps-native.ts           # Bridge GPS nativo + background tracking
│   │       │                           #   - Foreground service (tela desligada OK)
│   │       │                           #   - @capacitor-community/background-geolocation
│   │       │                           #   - Intervalo: 10s em rota, 30s idle
│   │       ├── update-checker.ts       # Verificador versao + forca atualizacao
│   │       └── NativeUpdateBanner.tsx  # Modal bloqueante de atualizacao
│   │
│   └── android/                        # Projeto Android (gerado pelo Capacitor)
│       ├── app/
│       │   ├── build.gradle
│       │   └── src/main/
│       │       ├── AndroidManifest.xml # 9 permissoes (GPS, background, foreground service)
│       │       ├── res/                # Icone (chefe robo), splash, cores, strings
│       │       └── assets/public/      # Web assets (apos cap copy)
│       ├── build.gradle
│       └── gradlew
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║              AGENTS WINDOWS (Desktop)                ║
│   ╚══════════════════════════════════════════════════════╝
│
├── printer_agent/                      # Agent impressao Windows (ESC/POS)
│   ├── main.py                         # Orquestrador + system tray
│   ├── esc_pos_builder.py              # Construtor comandos ESC/POS
│   ├── printer_manager.py             # Gerenciador impressoras Win32
│   └── api_client.py                  # REST client → backend
│
├── bridge_agent/                       # Agent Bridge Windows (spooler + parse IA)
│   ├── main.py                         # Orquestrador + system tray (pystray)
│   ├── config.py                       # Config JSON em %APPDATA%/DerekhBridge/
│   ├── spooler_monitor.py              # Win32 spooler polling (2s)
│   ├── text_extractor.py              # ESC/POS → texto limpo (CP860/UTF-8)
│   ├── bridge_client.py               # REST client → backend parse + orders
│   └── ui/
│       └── config_window.py           # Tkinter login + selecao impressoras
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║                  CI/CD (GitHub Actions)               ║
│   ╚══════════════════════════════════════════════════════╝
│
├── .github/
│   └── workflows/
│       ├── build-agents.yml            # Build Windows agents (PyInstaller)
│       └── build-motoboy-apk.yml       # Build APK Android (JDK 21 + Capacitor)
│                                       #   - Trigger: push em motoboy-app/** ou motoboy/**
│                                       #   - Build: npm ci → vite build → cap sync → gradle
│                                       #   - Deploy: upload APK para Fly.io volume via sftp
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║              SALES AUTOPILOT (CRM B2B)               ║
│   ╚══════════════════════════════════════════════════════╝
│
├── Hacking-restaurant-b2b/            # CRM B2B separado (derekh-crm.fly.dev)
│   ├── crm/                           # App Flask principal
│   │   ├── app.py                     # Rotas + dashboard + outreach
│   │   ├── scanner.py                 # Scanner Google Maps
│   │   ├── admin_brain.py             # Chat IA linguagem natural
│   │   ├── competitor_service.py      # Analise concorrencia
│   │   ├── contact_validator.py       # Validacao contatos
│   │   └── templates/                 # 20+ templates Jinja2
│   ├── gmaps_scraper.py               # Scraper Google Maps
│   ├── auto_pipeline.py               # Pipeline automatico outreach
│   └── requirements.txt
│
│
│   ╔══════════════════════════════════════════════════════╗
│   ║              UTILS (Compartilhados)                  ║
│   ╚══════════════════════════════════════════════════════╝
│
└── utils/
    ├── mapbox_api.py                   # Geocodificar, rota, autocomplete (Mapbox)
    ├── haversine.py                    # Distancia offline (fallback)
    ├── calculos.py                     # Taxas entrega + ganhos motoboy
    ├── motoboy_selector.py             # Selecao justa de motoboys
    └── tsp_optimizer.py                # Otimizacao rotas (Nearest Neighbor TSP)
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
        │ Valida via Pydantic
        │ Busca sessao_id ou cria nova
        ▼
[SQLAlchemy ORM]
        │ Carrinho.query(restaurante_id=..., sessao_id=...)
        ▼
[SQLite / PostgreSQL]
        │ INSERT/UPDATE carrinho (itens_json)
        ▼
[Resposta JSON - CarrinhoResponse]
        ▼
[React Query - useCarrinho()]
        │ Invalida cache → re-renderiza
        ▼
[UI Atualizada - Cart.tsx]
```

### 2. Finalizar Pedido (Checkout)

```
[Checkout.tsx]
        │ Endereco (autocomplete Mapbox), forma_pagamento, tipo_entrega
        ▼
[FastAPI - carrinho.py - finalizar_carrinho()]
        │
        ├── 1. Busca carrinho por sessao_id
        ├── 2. Geocodifica endereco (Mapbox)
        ├── 3. Calcula distancia (Haversine)
        ├── 4. Calcula taxa entrega
        ├── 5. Cria Pedido + ItemPedido
        ├── 6. Vincula cliente_id se logado
        ├── 7. Limpa carrinho
        ├── 8. Se KDS ativo: cria PedidoCozinha (status NOVO)
        └── 9. Notifica via WebSocket (novo_pedido + kds:novo_pedido)
```

### 3. Fluxo KDS (Cozinha Digital)

```
[Pedido criado com KDS ativo]
        │ PedidoCozinha.status = NOVO
        ▼
[KDS PWA - KdsPreparo.tsx]
        │ WebSocket recebe kds:novo_pedido
        │ Cozinheiro ve comanda na fila
        │ COMECEI → status PREPARANDO
        │ FEITO → status FEITO
        ▼
[KDS PWA - KdsDespacho.tsx]
        │ Pedidos FEITOS aguardando
        │ PRONTO → Pedido.status = 'pronto'
        │ → WebSocket garcom:pedido_pronto
        ▼
[Despacho para motoboy]
```

### 4. Fluxo Garcom (Atendimento Mesa)

```
[Garcom PWA - GarcomHome.tsx]
        │ Toca na mesa LIVRE
        │ POST /garcom/mesas/{id}/abrir
        ▼
[SessaoMesa criada (pessoas, alergia, notas)]
        ▼
[GarcomCardapio.tsx]
        │ Seleciona itens, course (entrada/principal/sobremesa)
        │ POST /garcom/sessoes/{id}/pedidos
        ▼
[Pedido criado → KDS]
        │ tipo_origem = 'mesa'
        │ label_origem = 'Mesa 5 (Joao)'
        ▼
[Solicitar fechamento]
        │ POST /garcom/sessoes/{id}/solicitar-fechamento
        │ → WebSocket garcom:mesa_fechada → Painel admin
```

### 5. Fluxo Bot WhatsApp Humanoide

```
[Cliente envia mensagem WhatsApp]
        ▼
[Evolution API webhook → POST /webhooks/evolution]
        │ Resposta 200 imediata
        ▼
[atendente.py - process_message()]
        │ Anti-spam 30s, dedup cache
        │ Context builder (3 camadas)
        ▼
[xai_llm.py - Grok-3-fast]
        │ Function calling (max 5 iteracoes)
        │ 24 tools: criar_pedido, buscar_cardapio, etc
        ▼
[evolution_client.py]
        │ Envia texto/audio PTT
        │ Delay humanizado (digitando...)
        ▼
[Cliente recebe resposta no WhatsApp]
```

### 6. Fluxo GPS Motoboy (Nativo vs Browser)

```
[App Nativo Android (Capacitor)]
        │ Background Geolocation Plugin
        │ Foreground service → GPS mesmo com tela desligada
        │ Intervalo: 10s em rota, 30s idle
        ▼                                    OU
[PWA Browser (/entregador)]
        │ navigator.geolocation.watchPosition()
        │ Para quando minimiza/desliga tela
        ▼
[POST /api/gps/update]
        │ Body: {latitude, longitude, precisao, velocidade}
        ▼
[FastAPI - motoboys.py]
        │ Atualiza Motoboy.latitude_atual, longitude_atual
        │ Broadcast WebSocket: motoboy_gps
        ▼
[Painel Admin - Mapa tempo real]
[Site Cliente - Rastreamento entrega]
```

### 7. Fluxo Auto-Update App Nativo

```
[App abre (Capacitor)]
        │ App.getInfo() → versao local "1.0.0"
        ▼
[GET /api/public/app-version]
        │ Retorna: version, min_version, download_url, force_update
        ▼
[update-checker.ts]
        │ Compara semver
        │ Se version > local: mostra NativeUpdateBanner
        │ Se local < min_version: modal bloqueante
        ▼
[Botao "Atualizar" → abre URL do APK]
```

### 8. Arquitetura Simplificada

```
┌──────────────┐  HTTP/JSON   ┌──────────────┐  ORM    ┌─────────────┐
│  7 React Apps│ ───────────► │   FastAPI     │ ──────► │ PostgreSQL  │
│  (Browser)   │ ◄─────────── │   (Python)    │ ◄────── │ (Fly.io)    │
└──────────────┘  + WebSocket └───────┬───────┘         └─────────────┘
                                      │
┌──────────────┐  HTTP/JSON          │ Webhooks
│  App Nativo  │ ───────────►        │
│  (Capacitor) │                     │
└──────────────┘              ┌──────▼────────┐
                              │  Evolution API │  WhatsApp
┌──────────────┐  HTTP/JSON   │  (webhook)     │ ◄──────── Clientes
│ Bridge Agent │ ───────────► └───────────────┘
│  (Windows)   │
└──────────────┘              ┌───────────────┐
                              │  Asaas         │  Billing
┌──────────────┐  HTTP/JSON   │  (webhook)     │
│ Printer Agent│ ───────────► └───────────────┘
│  (Windows)   │
└──────────────┘

Legenda:
- React Apps → FastAPI: via apiClient.ts (axios), autenticado com JWT
- App Nativo → FastAPI: mesmas APIs, GPS nativo com foreground service
- FastAPI → PostgreSQL: via SQLAlchemy 2.0 ORM
- WebSocket: notificacoes tempo real (pedidos, KDS, garcom, GPS)
- Evolution API: gateway WhatsApp → bot IA humanoide
- Asaas: billing webhook (PIX/Boleto)
```

---

## Mapa de Dependencias entre Arquivos

```
database/models.py (40+ models)
    ├── backend/app/models.py (re-exporta)
    ├── backend/app/routers/*.py (todos importam)
    └── migrations/versions/*.py (schema changes)

backend/app/auth.py
    └── backend/app/routers/*.py (6 dependencies JWT)

backend/app/feature_flags.py + feature_guard.py
    └── backend/app/routers/*.py (38 endpoints protegidos)

apiClient.ts (site cliente)
    └── hooks/useQueries.ts → pages/*.tsx

adminApiClient.ts
    └── admin/hooks/useAdminQueries.ts → admin/pages/*.tsx

motoboyApiClient.ts
    └── motoboy/hooks/useMotoboyQueries.ts → motoboy/pages/*.tsx

kdsApiClient.ts
    └── kds/hooks/useKdsQueries.ts → kds/pages/*.tsx

garcomApiClient.ts
    └── garcom/hooks/useGarcomQueries.ts → garcom/pages/*.tsx

motoboy-app/src/main.tsx
    └── @/motoboy/MotoboyApp.tsx (importa do monorepo via alias Vite)

utils/calculos.py
    ├── backend/app/routers/carrinho.py (taxa entrega)
    └── backend/app/routers/motoboys.py (ganhos)

utils/mapbox_api.py
    ├── backend/app/routers/site_cliente.py (autocomplete)
    └── backend/app/routers/carrinho.py (geocodificacao)
```
