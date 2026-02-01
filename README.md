# Super Food - Plataforma SaaS para Gestao de Restaurantes

**AVISO DE LICENCA - IMPORTANTE**
Este repositorio NAO e open source. O codigo e PROPRIETARIO E CONFIDENCIAL.
Qualquer uso, copia ou distribuicao nao autorizada e estritamente proibida.
Veja o arquivo LICENSE para os termos legais completos.

---

Sistema multi-tenant completo para gestao de restaurantes com entregas inteligentes, rastreamento GPS em tempo real, otimizacao de rotas (TSP) e gestao financeira integrada.

## Visao Geral

O Super Food e composto por **4 aplicacoes principais** (4 cabecas):

| Aplicacao | Arquivo | Porta | Descricao |
|-----------|---------|-------|-----------|
| **Super Admin** | `streamlit_app/super_admin.py` | 8501 | Painel administrativo do SaaS |
| **Dashboard Restaurante** | `streamlit_app/restaurante_app.py` | 8502 | Gestao completa do restaurante |
| **App Motoboy (PWA)** | `app_motoboy/motoboy_app.py` | 8503 | App mobile para entregadores |
| **Site do Cliente** | `streamlit_app/cliente_app.py` | 8504 | Pedidos online para clientes |

**Destaques Tecnicos (v2.7.1 - 01/02/2026):**
- Banco de dados unificado em SQLAlchemy ORM
- Sistema de selecao justa de motoboys
- Calculo automatico de taxa de entrega e ganhos
- Autocomplete de endereco com Mapbox
- Site do cliente completo (4a cabeca)
- Alembic configurado para migrations
- Correcoes de bugs no multiselect de dias e URL do site

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

## Executando as Aplicacoes

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Super Admin (porta 8501)
streamlit run streamlit_app/super_admin.py

# Dashboard Restaurante (porta 8502)
streamlit run streamlit_app/restaurante_app.py --server.port=8502

# App Motoboy PWA (porta 8503)
streamlit run app_motoboy/motoboy_app.py --server.port=8503

# Site do Cliente (porta 8504)
streamlit run streamlit_app/cliente_app.py --server.port=8504
```

## Credenciais de Teste

| Aplicacao | Usuario/Email | Senha |
|-----------|---------------|-------|
| Super Admin | `superadmin` | `SuperFood2025!` |
| Restaurante Teste | `teste@superfood.com` | `123456` |
| Motoboy | Criar via dashboard | Codigo de acesso do restaurante |

## Estrutura do Projeto

```
super-food/
├── alembic.ini                 # Configuracao Alembic
├── .env                        # Variaveis de ambiente
├── requirements.txt            # Dependencias Python
├── init_database.py            # Inicializador do banco
├── super_food.db               # Banco SQLite (dev)
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
│       └── 004_add_motoboy_selection_fields.py
│
├── streamlit_app/              # Aplicacoes Streamlit
│   ├── super_admin.py          # Cabeca 1: Admin SaaS
│   ├── restaurante_app.py      # Cabeca 2: Dashboard Restaurante
│   └── cliente_app.py          # Cabeca 4: Site do Cliente
│
├── app_motoboy/                # PWA Motoboy
│   └── motoboy_app.py          # Cabeca 3: App Entregadores
│
├── utils/                      # Utilitarios
│   ├── __init__.py
│   ├── mapbox_api.py           # Integracao Mapbox (geocoding, rotas)
│   ├── haversine.py            # Calculo de distancia offline
│   ├── calculos.py             # Taxas e ganhos
│   ├── motoboy_selector.py     # Selecao justa de motoboys
│   └── tsp_optimizer.py        # Otimizacao de rotas
│
└── backend/                    # FastAPI (em desenvolvimento)
    ├── main.py
    └── app/
```

## Funcionalidades Principais

### Super Admin
- Criacao e gestao de restaurantes (tenants)
- Controle de planos de assinatura (Basico, Essencial, Avancado, Premium)
- Dashboard com metricas globais
- Gestao de inadimplencia e renovacoes

### Dashboard Restaurante
- Criacao e gestao de pedidos (Entrega, Retirada, Mesa)
- Despacho automatico com selecao justa de motoboys
- Configuracao de taxas de entrega
- Configuracao de pagamento de motoboys
- Ranking de motoboys por performance
- Gestao de caixa

### App Motoboy (PWA)
- Cadastro com codigo de acesso do restaurante
- Recebimento de rotas otimizadas (TSP)
- Finalizacao de entregas com calculo automatico de ganhos
- Visualizacao de estatisticas e ganhos do dia
- Toggle online/offline para disponibilidade

### Site do Cliente
- Acesso via codigo do restaurante (`?restaurante=CODIGO`)
- Cardapio organizado por categorias
- Carrinho de compras persistente
- Autocomplete de endereco inteligente (filtra por cidade)
- Calculo de taxa de entrega em tempo real
- Checkout com multiplas formas de pagamento
- Acompanhamento do pedido em tempo real

## Sistema de Selecao Justa de Motoboys

O Super Food implementa um algoritmo de selecao justa para distribuir entregas:

1. **Disponibilidade**: Motoboy deve estar ativo e online
2. **Sem rota ativa**: Prioriza quem nao esta em entrega
3. **Menos pendencias**: Quem tem menos entregas pendentes
4. **Rotacao hierarquica**: Quem recebeu ha mais tempo vai primeiro
5. **Proximidade**: Em empate, o mais proximo do restaurante

## Calculo de Taxa e Ganhos

### Taxa de Entrega (cobrada do cliente)
```
Se distancia <= distancia_base:
    taxa = taxa_base
Senao:
    km_extra = distancia - distancia_base
    taxa = taxa_base + (km_extra * taxa_por_km_extra)
```

### Ganho do Motoboy (pago ao entregador)
```
Se distancia <= distancia_base:
    ganho = valor_base_motoboy
Senao:
    km_extra = distancia - distancia_base
    ganho = valor_base_motoboy + (km_extra * valor_km_extra_motoboy)
```

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

## Banco de Dados

### Modelos Principais (22+ tabelas)

- **Tenants**: `super_admin`, `restaurantes`, `config_restaurante`, `site_config`
- **Motoboys**: `motoboys`, `motoboys_solicitacoes`, `gps_motoboys`
- **Produtos**: `categorias_menu`, `produtos`, `tipos_produto`, `variacoes_produto`
- **Pedidos**: `pedidos`, `itens_pedido`, `entregas`, `rotas_otimizadas`
- **Clientes**: `clientes`, `enderecos_cliente`, `carrinho`
- **Financeiro**: `caixa`, `movimentacoes_caixa`
- **Sistema**: `notificacoes`

### Isolamento Multi-Tenant

Todas as queries filtram por `restaurante_id` para garantir isolamento de dados entre restaurantes.

## Roadmap

- [x] Fase 1: Sistema base com ORM SQLAlchemy
- [x] Fase 2: Migracao completa para Alembic
- [x] Fase 3: Site do Cliente (4a cabeca)
- [x] Fase 4: Selecao justa de motoboys
- [x] Fase 5: Calculo automatico de taxas e ganhos
- [ ] Fase 6: Backend FastAPI completo
- [ ] Fase 7: WebSockets para GPS em tempo real
- [ ] Fase 8: Integracao iFood
- [ ] Fase 9: App nativo (WebView)

## Tecnologias

- **Frontend**: Streamlit (PWA-ready)
- **Backend**: Python 3.12+, FastAPI (em dev)
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
