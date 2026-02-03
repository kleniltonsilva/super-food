# Super Food - Plataforma SaaS para Gestao de Restaurantes

**AVISO DE LICENCA - IMPORTANTE**
Este repositorio NAO e open source. O codigo e PROPRIETARIO E CONFIDENCIAL.
Qualquer uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para os termos legais completos.

---

Sistema multi-tenant completo para gestao de restaurantes com entregas inteligentes, rastreamento GPS em tempo real, otimizacao de rotas (TSP) e gestao financeira integrada.

## Visao Geral

O Super Food e composto por **4 aplicacoes principais**:

| Aplicacao | Tecnologia | Porta | Descricao |
|-----------|------------|-------|-----------|
| **API Backend** | FastAPI + Uvicorn | 8000 | API REST, Site Cliente, WebSockets |
| **Super Admin** | Streamlit | 8501 | Painel administrativo do SaaS |
| **Dashboard Restaurante** | Streamlit | 8502 | Gestao completa do restaurante |
| **App Motoboy (PWA)** | Streamlit | 8503 | App mobile para entregadores |

**Destaques Tecnicos (v2.8.2 - 03/02/2026):**
- FastAPI como backend principal (API REST + WebSockets)
- Banco de dados unificado em SQLAlchemy ORM
- Sistema de selecao justa de motoboys com rotacao
- Despacho automatico respeitando capacidade do motoboy
- Isolamento multi-tenant completo (motoboys por restaurante)
- Login de motoboy com codigo do restaurante
- Capacidade de entregas configuravel por motoboy
- Calculo automatico de taxa de entrega e ganhos
- Autocomplete de endereco com Mapbox
- Site do cliente via FastAPI + Templates HTML
- Alembic configurado para migrations
- Script de inicializacao unificado (`start_services.sh`)
- **NOVO:** Rastreamento GPS em tempo real de motoboys
- **NOVO:** Mapa tempo real no painel do restaurante (Folium)
- **NOVO:** 3 modos de despacho (rapido economico, cronologico, manual)
- **NOVO:** API GPS completa (`/api/gps/*`)

## Instalacao

### Pre-requisitos

- Python 3.12+
- pip
- Conta Mapbox (para API de geocodificacao)

### Setup

```bash
# Clonar repositorio
git clone https://github.com/kleniltonsilva/super-food.git
cd super-food

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variaveis de ambiente
cp .env.example .env
# Edite .env e adicione seu MAPBOX_TOKEN

# Inicializar banco de dados
python init_database.py

# Aplicar migrations
alembic upgrade head
```

## Executando o Sistema

### Metodo Recomendado: Script Unificado

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar TODOS os servicos (FastAPI + Streamlit)
./start_services.sh

# Iniciar apenas a API FastAPI
./start_services.sh --api-only
```

### Metodo Alternativo: Python

```bash
source venv/bin/activate

# Todos os servicos em foreground
python run_production.py

# Apenas API
python run_production.py --api-only
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
```

### Parar Todos os Servicos

```bash
pkill -f "uvicorn|streamlit"
```

## Testando o Sistema

### Verificar se os Servicos Estao Rodando

```bash
# Verificar portas ativas
lsof -i :8000,:8501,:8502,:8503 | grep LISTEN

# Testar FastAPI
curl http://localhost:8000/
# Resposta esperada: {"mensagem":"Super Food API - Site do Cliente ativo!"}

# Testar Swagger (documentacao da API)
# Abrir no navegador: http://localhost:8000/docs

# Testar site do cliente (substitua CODIGO pelo codigo do restaurante)
curl http://localhost:8000/site/CODIGO
```

### Testar Endpoints HTTP

```bash
# FastAPI Backend
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
# Esperado: 200

# Super Admin
curl -s -o /dev/null -w "%{http_code}" http://localhost:8501/
# Esperado: 200

# Dashboard Restaurante
curl -s -o /dev/null -w "%{http_code}" http://localhost:8502/
# Esperado: 200

# App Motoboy
curl -s -o /dev/null -w "%{http_code}" http://localhost:8503/
# Esperado: 200
```

### Verificar Logs

```bash
# Logs dos servicos (quando iniciados via start_services.sh)
tail -f /tmp/superfood_api.log         # FastAPI
tail -f /tmp/superfood_admin.log       # Super Admin
tail -f /tmp/superfood_restaurante.log # Dashboard Restaurante
tail -f /tmp/superfood_motoboy.log     # App Motoboy
```

## Credenciais de Teste

| Aplicacao | Usuario/Email | Senha |
|-----------|---------------|-------|
| Super Admin | `superadmin` | `SuperFood2025!` |
| Restaurante Teste | `teste@superfood.com` | `123456` |
| Motoboy | Codigo do restaurante + usuario + senha | Configurado no cadastro |

## Fluxo de Motoboys

### Cadastro e Login
1. **Restaurante cadastra motoboy** -> motoboy fica OFFLINE
2. **Motoboy faz login no App** (codigo restaurante + usuario + senha) -> fica ONLINE
3. **Restaurante despacha pedidos** -> apenas para motoboys ONLINE
4. **Motoboy finaliza entregas** -> recebe novos pedidos ou fica disponivel

### Capacidade de Entregas
- Cada motoboy tem capacidade configuravel (1-20 pedidos)
- Padrao: 3 pedidos por motoboy
- Pode ser ajustado por tipo de veiculo (moto=3, carro=8, bicicleta=2)
- Configuravel no cadastro e na lista de motoboys

### Despacho Automatico
- Respeita capacidade do motoboy
- Distribui pedidos de forma justa (rotacao)
- Pedidos excedentes ficam aguardando proximo motoboy

### Modos de Despacho (v2.8.1)
| Modo | Descricao |
|------|-----------|
| **Rapido Economico** | TSP por proximidade - otimiza combustivel (padrao) |
| **Cronologico Inteligente** | Agrupa pedidos por tempo (10 min), depois TSP |
| **Manual** | Restaurante atribui manualmente cada pedido |

### Rastreamento GPS em Tempo Real (v2.8.1)
- Motoboy online envia GPS automaticamente a cada 10 segundos
- Mapa em tempo real no painel do restaurante (aba "Mapa")
- Historico de posicoes armazenado no banco
- Indicador visual de status GPS no app do motoboy

## Estrutura do Projeto

```
super-food/
├── start_services.sh           # Script para iniciar todos os servicos
├── run_production.py           # Script Python alternativo
├── alembic.ini                 # Configuracao Alembic
├── .env                        # Variaveis de ambiente
├── requirements.txt            # Dependencias Python
├── init_database.py            # Inicializador do banco
├── super_food.db               # Banco SQLite (dev)
│
├── backend/                    # FastAPI Backend
│   └── app/
│       ├── main.py             # Aplicacao principal
│       ├── routers/            # Rotas da API
│       └── templates/          # Templates HTML
│
├── database/                   # SQLAlchemy ORM
│   ├── __init__.py
│   ├── base.py                 # Base declarativa
│   ├── models.py               # 22+ modelos ORM
│   ├── session.py              # Gerenciamento de sessao
│   ├── init.py                 # Funcoes de inicializacao
│   └── seed/                   # Dados iniciais
│
├── migrations/                 # Alembic migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_gps_motoboys_table.py
│       ├── 003_add_site_cliente_schema.py
│       ├── 004_add_motoboy_selection_fields.py
│       ├── 005_add_motoboy_usuario_unique_constraint.py
│       └── 006_add_modo_prioridade_e_motivo_finalizacao.py
│
├── streamlit_app/              # Aplicacoes Streamlit
│   ├── super_admin.py          # Admin SaaS
│   ├── restaurante_app.py      # Dashboard Restaurante
│   └── cliente_app.py          # Site do Cliente (legado)
│
├── app_motoboy/                # PWA Motoboy
│   └── motoboy_app.py          # App Entregadores
│
└── utils/                      # Utilitarios
    ├── __init__.py
    ├── mapbox_api.py           # Integracao Mapbox
    ├── haversine.py            # Calculo de distancia offline
    ├── calculos.py             # Taxas e ganhos
    ├── motoboy_selector.py     # Selecao justa de motoboys
    └── tsp_optimizer.py        # Otimizacao de rotas
```

## Funcionalidades Principais

### API FastAPI (Backend)
- API REST completa com documentacao Swagger
- Site do cliente via templates HTML
- WebSockets para atualizacoes em tempo real
- Escalavel com multiplos workers

### Super Admin
- Criacao e gestao de restaurantes (tenants)
- Controle de planos de assinatura (Basico, Essencial, Avancado, Premium)
- Dashboard com metricas globais
- Gestao de inadimplencia e renovacoes

### Dashboard Restaurante
- Criacao e gestao de pedidos (Entrega, Retirada, Mesa)
- Despacho automatico com selecao justa de motoboys
- **Configuracao de capacidade por motoboy**
- Configuracao de taxas de entrega
- Configuracao de pagamento de motoboys
- Ranking de motoboys por performance
- Gestao de caixa
- Visualizacao de ultimo login de cada motoboy

### App Motoboy (PWA)
- **Login com codigo do restaurante + usuario + senha**
- Cadastro com codigo de acesso do restaurante
- Recebimento de rotas otimizadas (TSP)
- Finalizacao de entregas com calculo automatico de ganhos
- Visualizacao de estatisticas e ganhos do dia
- Toggle online/offline para disponibilidade

### Site do Cliente (via FastAPI)
- Acesso via URL: `http://localhost:8000/site/{codigo_restaurante}`
- Cardapio organizado por categorias
- Carrinho de compras
- Calculo de taxa de entrega em tempo real
- Checkout com multiplas formas de pagamento

## Endpoints da API FastAPI

| Endpoint | Metodo | Descricao |
|----------|--------|-----------|
| `/` | GET | Health check |
| `/docs` | GET | Documentacao Swagger interativa |
| `/redoc` | GET | Documentacao ReDoc |
| `/site/{codigo}` | GET | Site do cliente (HTML) |
| `/site/{codigo}/cardapio` | GET | Cardapio do restaurante |
| `/ws/{restaurante_id}` | WebSocket | Atualizacoes em tempo real |
| `/api/gps/update` | POST | Atualiza localizacao GPS do motoboy |
| `/api/gps/motoboys/{restaurante_id}` | GET | Lista motoboys online com GPS |
| `/api/gps/historico/{motoboy_id}` | GET | Historico de posicoes GPS |

## Configuracao

### Variaveis de Ambiente (.env)

```env
# Mapbox API (obrigatorio para geocodificacao)
MAPBOX_TOKEN=seu_token_aqui

# Banco de dados
DATABASE_URL=sqlite:///./super_food.db

# Para producao (PostgreSQL)
# DATABASE_URL=postgresql+psycopg2://user:pass@host/db
```

### Comandos Alembic

```bash
# Aplicar todas as migrations
alembic upgrade head

# Reverter ultima migration
alembic downgrade -1

# Ver historico
alembic history

# Ver versao atual
alembic current

# Criar nova migration (apos alterar models.py)
alembic revision --autogenerate -m "descricao"
```

## Changelog v2.8.2 (03/02/2026)

### Correcoes
- **App Motoboy - Status de entregas** - Contador "Pedido X de Y" agora atualiza corretamente apos cada entrega
- **App Motoboy - Permissao GPS** - Solicitacao explicita de permissao com indicador clicavel e mensagem de ajuda
- **App Motoboy - Notificacoes com som** - Som de notificacao mais alto e vibracao no dispositivo
- **App Motoboy - Erro removeChild** - Keys estaveis nos formularios evitam erro de DOM
- **Restaurante - Notificacoes temporarias** - Mensagens de despacho agora usam toast e desaparecem apos 3s
- **Restaurante - Status ABERTO/FECHADO** - Menu lateral agora mostra status em tempo real do banco
- **Caixa - Retirada funcional** - Formulario de retirada corrigido com validacoes e feedback
- **Caixa - Historico** - Adicionada visualizacao de movimentacoes do caixa
- **Modos de despacho** - Validados: rapido economico (TSP), cronologico inteligente, manual

### Melhorias
- Solicitacao automatica de permissao de notificacao no login do motoboy
- Vibracao do dispositivo ao receber novas entregas
- Indicador GPS clicavel para reautorizar permissao negada
- Caixa pode ser aberto independente do status do restaurante

---

## Changelog v2.8.1 (02/02/2026)

### Novidades
- **Rastreamento GPS em tempo real** - Motoboy envia localizacao a cada 10s
- **Mapa tempo real no restaurante** - Visualiza motoboys online no mapa (Folium)
- **3 modos de despacho** - Rapido economico, cronologico inteligente, manual
- **API GPS completa** - Endpoints para update, listagem e historico
- **Motivo de finalizacao** - Rastreia se entrega foi entregue, cliente ausente, etc.
- **Motoboy recebe em cancelamentos** - Ganho registrado mesmo com cliente ausente

### Correcoes
- Ganhos do motoboy em entregas canceladas (cliente ausente agora paga)
- Inconsistencia entre ganho total vs ganho diario
- Erro JavaScript "removeChild" no Streamlit (keys unicos)
- Cache de coordenadas do restaurante atualizado automaticamente

### Migration 006
- Campo `modo_prioridade_entrega` em config_restaurante
- Campo `motivo_finalizacao` em entregas
- Campo `motivo_cancelamento` em entregas

---

## Changelog v2.8.0

### Novidades
- Login de motoboy com codigo do restaurante (isolamento multi-tenant)
- Capacidade de entregas configuravel por motoboy (1-20)
- Despacho automatico respeita capacidade do motoboy
- Pedidos excedentes ficam aguardando proximo motoboy
- Visualizacao de ultimo login na lista de motoboys
- Constraint unica (restaurante_id + usuario) no banco

### Correcoes
- Bug SQLAlchemy ao finalizar entrega corrigido
- Motoboys agora so ficam online ao fazer login no App
- Menu do restaurante estavel (sem recarregamento em loop)
- Erro JavaScript "removeChild" corrigido

## Roadmap

- [x] Fase 1: Sistema base com ORM SQLAlchemy
- [x] Fase 2: Migracao completa para Alembic
- [x] Fase 3: Site do Cliente (4a cabeca)
- [x] Fase 4: Selecao justa de motoboys
- [x] Fase 5: Calculo automatico de taxas e ganhos
- [x] Fase 6: Backend FastAPI com Site Cliente
- [x] Fase 7: Isolamento multi-tenant de motoboys
- [x] Fase 8: GPS em tempo real + Mapa no restaurante (v2.8.1)
- [ ] Fase 9: Integracao iFood
- [ ] Fase 10: App nativo (WebView)

## Tecnologias

- **Backend**: FastAPI + Uvicorn
- **Dashboards**: Streamlit (PWA-ready)
- **Linguagem**: Python 3.12+
- **ORM**: SQLAlchemy 2.0+
- **Migrations**: Alembic
- **Banco**: SQLite (dev) / PostgreSQL (prod)
- **APIs**: Mapbox (geocoding, rotas, directions)
- **Algoritmos**: TSP (Nearest Neighbor), Haversine

## Licenca

Este software e propriedade exclusiva do autor.
Uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para termos completos.

## Autor

Klenilton Silva - [@kleniltonsilva](https://github.com/kleniltonsilva)
