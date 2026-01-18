
# 🍕 Super Food – Sistema Multi-Restaurante SaaS Proprietário

⚠️ **LICENSE NOTICE — IMPORTANT** 🚫  
**THIS REPOSITORY IS NOT OPEN SOURCE**  
This source code is **PROPRIETARY AND CONFIDENTIAL**. The code is made publicly visible solely for presentation and portfolio reference. **NO RIGHTS ARE GRANTED**, including but not limited to:  
❌ Use ❌ Copy ❌ Reproduce ❌ Modify ❌ Adapt ❌ Study for implementation ❌ Distribute ❌ Sublicense ❌ Sell ❌ Create derivative works  
Any reproduction, storage, transmission, execution, or exploitation of this code — in whole or in part, by any means — is strictly prohibited without explicit prior written authorization from the copyright holder. Violations may result in civil and criminal liability. See the LICENSE file for full legal terms.

## 📋 Índice
- [Visão Geral](#visão-geral)
- [Funcionalidades](#funcionalidades)
- [Arquitetura](#arquitetura)
- [Instalação](#instalação)
- [Configuração](#configuração)
- [Como Usar](#como-usar)
- [Estrutura de Dados](#estrutura-de-dados)
- [Integração com Mapbox](#integração-com-mapbox)
- [Migrations e Banco de Dados](#migrations-e-banco-de-dados)
- [Roadmap](#roadmap)
- [Status do Projeto](#status-do-projeto)
- [Contato](#contato)
- [Licença](#licença)

## 🎯 Visão Geral
O Super Food é uma plataforma SaaS proprietária para gestão de múltiplos restaurantes, com foco em entregas inteligentes, rastreamento GPS em tempo real, otimização de rotas (usando TSP) e gestão financeira integrada. Projetado para escalabilidade, o sistema suporta multi-tenant (isolamento por restaurante), despacho automático/econômico e interfaces mobile-first via PWA. Todas as componentes foram atualizadas para usar SQLAlchemy ORM unificado, removendo legados de SQLite raw, com suporte completo a migrations via Alembic. Isso garante consistência, type-safety e fácil manutenção/portabilidade para PostgreSQL em produção.

**Destaques Técnicos Atualizados (v2.6 – 18/01/2026):**
- Banco de dados unificado em SQLAlchemy ORM (sem duplicação de sistemas).
- Suporte completo a histórico GPS para motoboys (tabela e model dedicados).
- Correções de erros ORM (eager loading para relacionamentos, evitando detached instances).
- Alembic configurado e funcional para migrations automáticas/manuais.
- Apps 100% migrados para ORM puro, com filtros multi-tenant rigorosos.

## ✨ Funcionalidades
### 👑 Super Admin (streamlit_app/super_admin.py)
- Login seguro com hash SHA256.
- Criação e gerenciamento de restaurantes (multi-tenant).
- Controle de planos de assinatura (Básico, Essencial, Avançado, Premium) e limites (ex: número de motoboys).
- Renovação e monitoramento de assinaturas com alertas de vencimento.
- Dashboard com métricas globais (ex: restaurantes ativos, receitas totais).
- Suspensão/ativação/cancelamento de contas.

### 🏪 Dashboard Restaurante (streamlit_app/restaurante_app.py)
- Login via email/senha (proprietário).
- Criação e gerenciamento de pedidos (tipos: Entrega, Retirada na Loja, Para Mesa).
- Listagem de pedidos ativos/histórico com filtros por status/data.
- Aprovação/recusa de solicitações de motoboys.
- Despacho inteligente: Modos Automático Econômico (TSP otimizado), Manual ou por Ordem Cronológica.
- Gestão de caixa: Abertura/fechamento, movimentações (vendas, retiradas), relatórios.
- Configurações operacionais: Horários, taxas de entrega, valores para motoboys.
- Ranking de motoboys por entregas/ganhos/distância.
- Notificações em tempo real.

### 🏍️ App PWA Motoboy (app_motoboy/motoboy_app.py)
- Cadastro com código de acesso do restaurante (aguarda aprovação).
- Login após aprovação (senha inicial gerada automaticamente).
- Atualização de localização GPS em tempo real (histórico armazenado).
- Recebimento de entregas otimizadas (ordem TSP, navegação via Google Maps/Waze).
- Histórico de ganhos, entregas e perfil pessoal.
- Marcação de entregas como concluídas/recusadas/ausentes.
- Interface mobile-first com menu inferior e CSS responsivo.

### 🗺️ Rastreamento e Otimização
- Integração Mapbox para geocodificação, cálculo de rotas e distâncias.
- Cache inteligente de distâncias (reduz 90% das chamadas API).
- Fallback Haversine para distâncias offline.
- Algoritmo TSP para otimização de rotas múltiplas.
- Histórico GPS completo para análise e auditoria.

### 💰 Gestão Financeira
- Planos de assinatura com pagamentos monitorados.
- Cálculo automático de valores de entrega (base + km extra).
- Caixa diário com movimentações detalhadas (vendas, retiradas, formas de pagamento).

## 🏗️ Arquitetura
O sistema é modular e escalável, com banco unificado ORM e migrations automáticas. Diagrama simplificado:

```
super-food/
├── alembic.ini                        # Config Alembic
├── .env                               # Vars ambiente (MAPBOX_TOKEN, etc.)
├── requirements.txt                   # Dependências
├── README.md                          # Este arquivo
├── MANIFEST.md                        # Visão geral detalhada
├── LICENSE                            # Licença proprietária
├── logo.png                           # Assets
├── foto.png                           # Assets
│
├── database/                          # SQLAlchemy ORM unificado
│   ├── __init__.py
│   ├── base.py                        # Base ORM
│   ├── models.py                      # Models (16 tabelas, incl. gps_motoboys)
│   └── session.py                     # Gerenciamento de sessões
│
├── migrations/                        # Alembic migrations (funcional)
│   ├── env.py                         # Ambiente com models
│   ├── script.py.mako                 # Template
│   └── versions/                      # Scripts de migration
│       ├── 001_initial_schema.py
│       └── 002_add_gps_motoboys_table.py
│
├── streamlit_app/                     # Interfaces Streamlit
│   ├── super_admin.py                 # Super Admin
│   └── restaurante_app.py             # Dashboard Restaurante
│
├── app_motoboy/                       # PWA Motoboy
│   └── motoboy_app.py                 # App completo (ORM + GPS)
│
├── utils/                             # Utilitários
│   ├── mapbox_api.py                  # Mapbox com cache
│   └── haversine.py                   # Distâncias offline
│
└── backend/                           # Futuro FastAPI
```

- **Banco de Dados:** SQLite para dev (super_food.db); pronto para PostgreSQL via config Alembic.
- **ORM:** SQLAlchemy com eager loading para performance.
- **Migrations:** Alembic para schema controlado (upgrade/downgrade).
- **Segurança:** Filtros multi-tenant em todas queries (restaurante_id).

## 🚀 Instalação
⚠️ **Este projeto não é licenciado para uso externo. As instruções abaixo existem apenas para fins demonstrativos do funcionamento técnico.**

### Pré-requisitos
- Python 3.12+
- pip
- Conta Mapbox (para API token)
- Git (para clonar – visualização apenas)

### Passos
1. Clone o repositório (para fins de análise apenas):
   ```bash
   git clone https://github.com/kleniltonsilva/super-food.git
   cd super-food
   ```

2. Crie e ative ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # Ou: venv\Scripts\activate no Windows
   ```

3. Instale dependências:
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuração
1. Crie `.env` na raiz (exemplo):
   ```env
   MAPBOX_TOKEN=seu_token_mapbox_aqui
   DATABASE_URL=sqlite:///./super_food.db  # Para PostgreSQL: postgresql://user:pass@host/db
   DEBUG=True
   ```

2. Inicialize o banco de dados (se necessário):
   ```bash
   python init_database.py  # Cria schema inicial, super admin e restaurante teste
   ```

3. Rode migrations pendentes:
   ```bash
   alembic upgrade head
   ```

## 📖 Como Usar
⚠️ **Execução, teste ou deploy por terceiros NÃO É AUTORIZADO. Os comandos abaixo são exibidos apenas para documentação técnica.**

1. Ative venv (se não estiver):
   ```bash
   source venv/bin/activate
   ```

2. Rode os apps (em terminais separados para portas diferentes):
   ```bash
   streamlit run streamlit_app/super_admin.py       # Porta padrão 8501 – Super Admin
   streamlit run streamlit_app/restaurante_app.py   # Porta 8502 (use --server.port=8502) – Dashboard Restaurante
   streamlit run app_motoboy/motoboy_app.py         # Porta 8503 (use --server.port=8503) – PWA Motoboy
   ```

Credenciais de Teste (para fins demonstrativos):
- Super Admin: `superadmin` / `SuperFood2025!`
- Restaurante Teste: `teste@superfood.com` / `123456`
- Motoboy Teste: Crie via dashboard restaurante (código de acesso gerado automaticamente).

## 🗄️ Estrutura de Dados
16 tabelas integradas via SQLAlchemy ORM (multi-tenant com restaurante_id em todas):
- `super_admin`: Usuários admin globais.
- `restaurantes`: Tenants (restaurantes) com planos e configs.
- `config_restaurante`: Configs operacionais por restaurante.
- `motoboys`: Motoboys por restaurante.
- `motoboys_solicitacoes`: Solicitações de cadastro.
- `produtos`: Cardápio por restaurante.
- `pedidos`: Pedidos com tipos e status.
- `itens_pedido`: Detalhes de itens.
- `entregas`: Entregas otimizadas (TSP).
- `rotas_otimizadas`: Rotas calculadas.
- `caixa`: Controle diário de caixa.
- `movimentacoes_caixa`: Movimentos financeiros.
- `notificacoes`: Alertas para users.
- `gps_motoboys`: Histórico GPS (novo – localização em tempo real).
- `ranking_motoboys`: Rankings por performance.
- `assinaturas`: Gestão de planos pagos.

Filtros multi-tenant obrigatórios em queries para isolamento.

## 🗺️ Integração com Mapbox
- Geocoding: Conversão endereço → lat/long.
- Rotas: Cálculo de distâncias/tempos.
- Cache: Armazenamento de resultados para economia (reduz 90% de chamadas API).
- Fallback: Fórmula Haversine para distâncias offline.
- Uso: Configurar `MAPBOX_TOKEN` no `.env`.

## 🔧 Migrations e Banco de Dados
- Use Alembic para gerenciar schema:
  ```bash
  alembic revision --autogenerate -m "descrição da mudança"  # Gera nova migration
  alembic upgrade head                                      # Aplica todas
  alembic downgrade -1                                      # Reverte última
  ```
- Banco inicializado via `init_database.py` (cria super admin e restaurante teste).
- Para produção: Altere `sqlalchemy.url` no alembic.ini para PostgreSQL.

## 🔮 Roadmap
- Fase 1: Rotas Inteligentes com IA (concluída – TSP, GPS histórico).
- Fase 2: Backend FastAPI completo (APIs REST, WebSockets para GPS).
- Fase 3: Site do Cliente (pedidos online, rastreamento).
- Fase 4: Integração iFood (sincronização automática).

## 📊 Status do Projeto
✔️ Ativo  
✔️ Em desenvolvimento contínuo  
✔️ Uso comercial exclusivo do autor  
✔️ Banco unificado ORM + Alembic funcional  
✔️ GPS e otimizações completas  

## 📧 Contato
Autor: Klenilton Silva  
GitHub: https://github.com/kleniltonsilva  
Repositório: https://github.com/kleniltonsilva/super-food  

## ⚖️ Licença
**PROPRIETARY SOFTWARE — ALL RIGHTS RESERVED**  
Este software é proprietário e confidencial. Nenhuma permissão é concedida para uso, cópia, reprodução, modificação, redistribuição ou criação de obras derivadas, sem autorização expressa e escrita do autor. Consulte o arquivo LICENSE para os termos completos.

🚀 Super Food — Plataforma SaaS proprietária para gestão inteligente de restaurantes.
```
