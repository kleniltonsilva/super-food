# CLAUDE.md — Derekh Food

## REGRAS FUNDAMENTAIS

1. Responder **sempre em português**.
2. Gerar **codigo completo**, nunca snippets parciais.
3. **TODAS** as queries filtram por `restaurante_id` (multi-tenant obrigatório).
4. No React, usar hooks de `hooks/useQueries.ts` — **NUNCA** useState+useEffect manual para fetching.
5. Senhas **SEMPRE** com `.strip()` antes de hash.
6. Interceptor 401 ja existe no `apiClient.ts` — nao duplicar.
7. Ao concluir sprint/tarefa, atualizar CLAUDE.md e MEMORY.md com estado atual.
8. **GESTAO DE MEMORIA — PADRÃO REDE NEURAL (OBRIGATORIO):**
    - **Hub:** `MEMORY.md` — ultra-lean (~50 linhas), carregado SEMPRE, contém ponteiros para nós
    - **Nós temáticos:** arquivos filhos carregados SOMENTE quando a tarefa exige aquele tema
    - **Diretório:** `/home/pcempresa/.claude/projects/-home-pcempresa-Documentos-super-food/memory/`
    - **Mapa de nós:** ver seção "Mapa da Memória" abaixo
    - **Referência somente-leitura:** `README.md` (stack/endpoints/fluxos), `ESTRUTURA.md` (árvore)

    **Ciclo de vida da memória:**
    - **Ao iniciar sessão:** ler MEMORY.md → identificar nós relevantes → carregar sob demanda
    - **Durante sessão (PARALELO):** a cada alteração/criação no código, atualizar o nó temático correspondente EM PARALELO com o trabalho — nunca deixar para depois
    - **Ao finalizar:** atualizar MEMORY.md (hub) com estado atual

    **Esquecimento ativo (como memória humana):**
    - Cada nó tem limite de ~120 linhas — quando ultrapassar, APAGAR informação mais antiga/obsoleta
    - Detalhes de sessões antigas → comprimir em 1 linha resumo ou apagar
    - Bugs corrigidos há muito tempo → manter só os que ainda são relevantes (padrão recorrente)
    - Código/arquivos que foram deletados ou substituídos → remover da memória
    - Prioridade: informação recente e recorrente > informação antiga e pontual
    - Se um nó ficar irrelevante (ex: sprint concluído sem pendências), pode ser apagado

    **Princípio de economia (CRÍTICO):**
    - O sistema de memória existe para ECONOMIZAR tokens, nunca para gastar mais
    - NÃO atualizar memória para mudanças triviais (typo, 1 linha, ajuste cosmético)
    - NÃO ler nós temáticos que não são necessários para a tarefa atual
    - NÃO gastar tokens descrevendo o que vai fazer na memória — só fazer
    - Se a tarefa é simples e rápida, NÃO tocar na memória (custo > benefício)
    - Regra geral: atualizar memória quando a informação será útil em sessões FUTURAS
9. **REGRA CRÍTICA — CHECKBOXES:** Ao concluir qualquer etapa do Plano Mestre, marcar `[x]` IMEDIATAMENTE neste arquivo. Nunca deixar para depois.
10. **REGRA INQUEBRÁVEL — DOCUMENTAÇÃO TÉCNICA:** Ao criar novas funcionalidades, endpoints, páginas ou alterações significativas no projeto, **ATUALIZAR `DOCUMENTACAO_TECNICA.md` IMEDIATAMENTE** (de forma simultânea ao desenvolvimento, se possível). Esta regra **NUNCA pode ser quebrada**. A documentação deve sempre refletir o estado real do sistema.

---

## MAPA DA MEMÓRIA (Rede Neural)

```
MEMORY.md (hub — SEMPRE carregado)
│
├── architecture.md ─── Stack, caminhos, ORM models, auth, decisões técnicas
├── frontend.md ─────── 5 apps React, hooks, contexts, API clients, páginas
├── conventions.md ──── Padrões de código, gotchas, erros comuns a evitar
├── deploy.md ───────── Fly.io, Docker, checklist deploy, secrets, volume
├── billing.md ──────── Sistema Asaas, billing flow, billing guard
├── bot-whatsapp.md ─── Sprint 16 arquitetura bot, LLM, function calls
├── integrations.md ─── iFood, Open Delivery, credenciais plataforma
├── sprints.md ──────── Histórico de sprints + tarefas pendentes
├── corrections-log.md  Histórico completo de bugs corrigidos
└── COMO-FUNCIONA.md ── Documentação para o desenvolvedor humano
```

**Quando carregar cada nó:**
| Nó | Carregar quando... |
|----|-------------------|
| `architecture.md` | Criar endpoints, models, routers, mudar stack |
| `frontend.md` | Criar/editar componentes React, hooks, páginas |
| `conventions.md` | Qualquer tarefa de código (consulta rápida de gotchas) |
| `deploy.md` | Deploy, migrations, infra Fly.io, Docker |
| `billing.md` | Billing, assinatura, Asaas, planos |
| `bot-whatsapp.md` | Sprint 16, bot, WhatsApp, LLM |
| `integrations.md` | iFood, Open Delivery, marketplace |
| `sprints.md` | Planejamento, priorização, histórico |
| `corrections-log.md` | Debug, investigar bug similar a um antigo |

---

## ESTADO ATUAL DO PROJETO

- **Nome:** Derekh Food (anteriormente Super Food)
- **Versão:** 4.0.0 (tag v4.0.0)
- **Autor:** Klenilton Silva (@kleniltonsilva)
- **Tipo:** SaaS multi-tenant de delivery para restaurantes (proprietário)
- **Produção:** https://superfood-api.fly.dev (Fly.io, região GRU)
- **Sprint atual:** Plano Mestre de Implementação — 6 módulos
- **Última sessão:** 21/03/2026
- **Migrations em produção:** 001-027 (última: 027_operadores_caixa)
- **Migrations locais:** 028 (Pix), 029 (KDS), 030 (Planos), 031 (KDS pausa)
- **Migrations planejadas:** 032 (Garçom), 033 (Bot), 034 (Bridge)
- **Bugs conhecidos:** Nenhum crítico
- **Pendente:** 6 módulos (Pix → KDS → Garçom → Bot → Sales → Printer), domínio próprio

---

## DEPLOY — COMO SUBIR PARA PRODUÇÃO

### Antes de fazer deploy (OBRIGATÓRIO):
1. **Ler esta seção inteira** antes de executar qualquer comando
2. **`npm run check`** — verificar TypeScript sem erros
3. **`npm run build`** — verificar build sem erros
4. Se houver **migrations novas**, revisar seguindo as regras de PostgreSQL abaixo

### Comando de deploy:
```bash
cd /home/pcempresa/Documentos/super-food && ~/.fly/bin/fly deploy
```

### O Dockerfile faz tudo automaticamente:
1. Build React (Node 20)
2. Instala deps Python
3. Na inicialização: `alembic upgrade head` → migrations automáticas
4. Inicia Gunicorn com 2 workers Uvicorn

### Infraestrutura Fly.io:
- **App:** `superfood-api` — https://superfood-api.fly.dev (GRU)
- **PostgreSQL:** `superfood-db` — flycast:5432
- **Redis:** Upstash — fly-superfood-redis.upstash.io:6379
- **Volume:** `superfood_uploads` (1GB) em `/app/backend/static/uploads`
- **VM:** shared-cpu-1x, 512MB RAM
- **Secrets:** SECRET_KEY, SUPER_ADMIN_*, MAPBOX_TOKEN, REDIS_URL, SENTRY_*, FLY_API_TOKEN, STORAGE_BACKEND, ASAAS_API_KEY, ASAAS_ENVIRONMENT

### Verificar depois do deploy:
```bash
~/.fly/bin/fly logs --app superfood-api
curl https://superfood-api.fly.dev/health
~/.fly/bin/fly status --app superfood-api
```

### REGRAS CRÍTICAS PARA MIGRATIONS (PostgreSQL):

**NUNCA usar try/except em migrations Alembic para PostgreSQL!**
- Statement SQL falha → toda transação abortada → `InFailedSqlTransaction`

**SEMPRE usar SQL com IF EXISTS / IF NOT EXISTS:**
```python
# CORRETO
op.execute("ALTER TABLE x DROP CONSTRAINT IF EXISTS nome")
op.execute("CREATE INDEX IF NOT EXISTS ix_nome ON tabela (coluna)")

# Constraints condicionais
op.execute("""
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'nome') THEN
            ALTER TABLE tabela ADD CONSTRAINT nome UNIQUE (col1, col2);
        END IF;
    END $$;
""")
```

**Outras regras:** `sa.text('false')` para server_default, `sa.Text()` com parênteses, revision IDs max 128 chars.

> **REGRA VOLUME:** NUNCA deletar `superfood_uploads` sem migrar. Limite 1GB.
> Quando ~700MB: migrar para Cloudflare R2 (código pronto em `storage.py`).

---

## ESTRUTURA DO PROJETO

```
super-food/
├── backend/app/
│   ├── main.py                # FastAPI entry + WebSocket + lifespan
│   ├── database.py            # Config BD SQLite/PostgreSQL
│   ├── auth.py                # JWT helpers (3 roles: restaurante, motoboy, admin)
│   ├── models.py              # Re-exporta models de database/models.py
│   ├── websocket_manager.py   # Redis Pub/Sub multi-worker
│   ├── routers/
│   │   ├── painel.py          # Todas rotas /painel/* (admin restaurante)
│   │   ├── integracoes.py     # Integrações marketplace (connect/disconnect)
│   │   ├── admin.py           # Super Admin /api/admin/* + credenciais plataforma
│   │   ├── carrinho.py        # Carrinho/checkout cliente
│   │   ├── site_cliente.py    # Site público do restaurante
│   │   ├── billing.py         # Billing restaurante (/painel/billing/*)
│   │   ├── billing_admin.py   # Billing super admin (/api/admin/billing/*)
│   │   ├── billing_webhooks.py # Webhook Asaas (/webhooks/asaas)
│   │   ├── auth_restaurante.py # Login/perfil restaurante
│   │   ├── auth_cliente.py    # Registro/login/perfil cliente
│   │   ├── auth_motoboy.py    # Login/cadastro motoboy
│   │   ├── auth_admin.py      # Login super admin
│   │   ├── upload.py          # Upload imagem JWT protegido
│   │   └── motoboys.py       # Endpoints motoboy
│   ├── billing/               # Sistema de cobrança Asaas
│   │   ├── asaas_client.py    # httpx async client (sandbox/prod)
│   │   ├── billing_service.py # Lógica trial/plano/pagamento/suspensão
│   │   └── billing_tasks.py   # Task periódica (30min) + polling fallback
│   ├── integrations/          # iFood + Open Delivery
│   │   ├── ifood/             # client.py, mapper.py, status_machine.py, catalog_sync.py
│   │   ├── opendelivery/      # client.py, mapper.py
│   │   ├── base.py, manager.py
│   └── utils/                 # Helpers (despacho, menus, comanda)
├── restaurante-pedido-online/client/src/
│   ├── admin/                 # Painel restaurante (20+ páginas)
│   │   ├── pages/             # Todas as páginas admin
│   │   ├── components/        # Componentes específicos admin
│   │   ├── hooks/             # useAdminQueries.ts (57 hooks)
│   │   ├── contexts/          # AdminAuthContext, ThemeContext
│   │   └── lib/               # adminApiClient.ts
│   ├── superadmin/            # Super Admin (5+ páginas)
│   │   ├── pages/
│   │   ├── hooks/             # useSuperAdminQueries.ts
│   │   └── lib/               # superAdminApiClient.ts
│   ├── motoboy/               # App motoboy PWA (5 páginas + cadastro)
│   │   ├── pages/
│   │   ├── hooks/             # useMotoboyQueries.ts (14 hooks)
│   │   └── lib/               # motoboyApiClient.ts
│   ├── pages/                 # Site cliente (11 páginas)
│   ├── components/            # shadcn/ui compartilhados
│   ├── hooks/                 # useQueries.ts (site cliente)
│   └── lib/                   # apiClient.ts (30+ funções)
├── database/models.py         # SQLAlchemy ORM models (source of truth, 28+ modelos)
├── printer_agent/             # Agent impressão Windows (ESC/POS)
├── migrations/versions/       # Alembic 001-027
├── requirements.txt           # Dependencies Python
├── Dockerfile                 # Multi-stage build (Node + Python)
└── fly.toml                   # Config Fly.io
```

**Stack completa:**
- **Backend:** FastAPI + SQLAlchemy 2.0 + JWT (authlib/HS256) + WebSocket + Uvicorn
- **Frontend:** React 19 + TypeScript + Vite 7 + Tailwind CSS 4 + TanStack Query v5
- **Router:** wouter | **UI:** shadcn/radix-ui | **Charts:** recharts | **Maps:** Mapbox GL
- **BD dev:** SQLite | **BD prod:** PostgreSQL 16
- **Build:** `dist/public/` servido pelo FastAPI em produção

---

## APLICAÇÕES DO SISTEMA

| # | App | Tech | Rota/URL | Status |
|---|-----|------|----------|--------|
| 1 | API Backend | FastAPI 8000 | superfood-api.fly.dev | Produção |
| 2 | Super Admin | React | /superadmin | Produção |
| 3 | Painel Restaurante | React | /admin | Produção |
| 4 | App Motoboy | React PWA | /entregador | Produção |
| 5 | Site Cliente | React | /cliente/{codigo} | Produção |
| 6 | App KDS (Cozinha) | React PWA | /cozinha | Implementado |
| 7 | App Garçom | React PWA | /garcom | Planejado |
| 8 | Bot WhatsApp | FastAPI (micro) | derekh-bot.fly.dev | Planejado |
| 9 | Sales Autopilot | FastAPI | derekh-crm.fly.dev | Em deploy |
| 10 | Printer Agent | Windows Service | localhost:8765 | Planejado |

---

## HISTÓRICO DE SPRINTS

| Sprint | Descrição | Status |
|--------|-----------|--------|
| 0 | Correções pré-migração | ✅ 14-15/02 |
| 1 | API endpoints painel (64 endpoints) | ✅ 15/02 |
| 2 | React painel restaurante (20 páginas) | ✅ 15-22/02 |
| 3 | API endpoints motoboy | ✅ 08/03 |
| 4 | React app motoboy PWA | ✅ 08/03 |
| 5 | API endpoints super admin | ✅ 08/03 |
| 6 | React super admin | ✅ 08/03 |
| 7 | Infra cloud (PostgreSQL, Redis, Docker, R2, domínios) | ✅ 08/03 |
| 8 | Grande auditoria paridade funcional | ✅ 08/03 |
| 9 | Layouts temáticos (8 tipos restaurante) | ✅ 08/03 |
| 10 | Aposentar Streamlit (tag v4.0.0) | ✅ 12/03 |
| 11 | Deploy Fly.io produção | ✅ 12-15/03 |
| 12 | Migração R2 | ⏳ Quando volume >700MB |
| 13 | iFood + Open Delivery (implementação inicial) | ✅ 15/03 |
| 14 | Refatoração integrações (credenciais plataforma) | ✅ 16/03 |
| 15 | Billing/Assinatura Asaas (PIX+Boleto) | ✅ 16/03 |
| 15.1 | Operadores de Caixa (autenticação abrir/fechar) | ✅ 18/03 |
| 16 | Bot WhatsApp IA (Plano Premium) | ⏳ Planejado |
| 17 | Pix Online Woovi/OpenPix | ⏳ Planejado |
| 18 | KDS / Comanda Digital | ✅ 21/03 (falta deploy) |
| 19 | App Garçom (Atendimento Mesa) | ⏳ Planejado |
| 20 | Sales Autopilot (CRM B2B) | ⏳ Planejado |
| 21 | Printer Agent (Windows Service) | ⏳ Planejado |

---

## PLANO MESTRE DE IMPLEMENTAÇÃO

> **Ordem de prioridade:** Pix → KDS → Garçom → Bot WhatsApp → Sales Autopilot → Printer Agent
>
> **Regras de adaptação (TODOS os módulos):** tabelas em português, PKs Integer autoincrement, FK `restaurante_id` (multi-tenant), rotas `/painel/*` e `/api/admin/*` (sem `/api/v1/`), TanStack Query hooks, wouter nest, shadcn/radix-ui, migrations com `IF EXISTS`/`IF NOT EXISTS`

### INFRAESTRUTURA PENDENTE

- [ ] Comprar domínio + `fly certs add` + DNS
- [ ] Configurar alertas downtime (Fly.io dashboard)
- [ ] Deploy billing produção: testar sandbox completo → trocar `ASAAS_ENVIRONMENT=production`
- [ ] Migração R2 (quando volume > 700MB) — código pronto em `storage.py`

---

### MÓDULO 1 — Pix Online (Woovi/OpenPix) — Sprint 17 — Migration 028

> **Modelo de negócio:**
> - Woovi cobra **R$0,85 por transação Pix** — Derekh Food **NÃO cobra nada** do restaurante
> - Restaurante **NÃO precisa ter conta Woovi** — subconta é 100% virtual, sem login, sem dashboard
> - Restaurante só precisa informar **chave Pix válida** (já registrada no banco dele)
> - Saque: **R$1,00 por transferência** | **Isento para saques ≥ R$500** (confirmar valor exato com Woovi)
> - Split já ativado na conta Derekh Food (Split Partner OK)
> - **Futuro:** Transfeera como alternativa (aguardando consultor)
>
> **API Woovi — Referência:**
> - Auth: header `Authorization: <WOOVI_APP_ID>` (sem Bearer)
> - Base prod: `https://api.openpix.com.br` | Sandbox: `https://api.woovi-sandbox.com`
> - `POST /api/v1/subaccount` — criar subconta (`pixKey` + `name`)
> - `GET /api/v1/subaccount/{pixKey}` — saldo em centavos
> - `POST /api/v1/subaccount/{pixKey}/withdraw` — sacar saldo TOTAL (não aceita valor parcial)
> - `POST /api/v1/subaccount/transfer` — transferir entre subcontas (`value`, `fromPixKey`, `toPixKey`)
> - `POST /api/v1/charge` — cobrança com `splits[{pixKey, value, splitType: "SPLIT_SUB_ACCOUNT"}]`
> - Webhook: `OPENPIX:CHARGE_COMPLETED` confirma pagamento
>
> **Saque parcial (workaround — API só suporta saque total):**
> - Derekh Food tem uma subconta "cofre" (`derekh_vault`)
> - Para sacar R$300 de R$500: transferir R$200 → cofre, sacar tudo (R$300), devolver R$200 ← cofre
> - 3 chamadas API: transfer out → withdraw → transfer back

**Fase 1: Pré-requisitos Woovi**
- [x] Criar conta Woovi/OpenPix
- [x] Ativar Split de Pagamentos na conta
- [ ] **AGUARDANDO:** Confirmar com suporte Woovi o valor exato de isenção de taxa de saque para subcontas (R$500 ou R$1.000) — mensagem enviada, aguardando resposta
- [ ] Obter `WOOVI_APP_ID` (Admin > Permissões > APIs) e configurar webhook
- [ ] Criar subconta "cofre" Derekh (`derekh_vault`) para suportar saques parciais
- [ ] Testar no sandbox: criar subconta + cobrança + pagamento + saque parcial

**Fase 2: Backend**
- [ ] Migration 028:
  - Em `restaurantes`: `pix_habilitado`, `pix_chave`, `pix_tipo_chave` [cpf/cnpj/email/celular/aleatoria], `pix_subconta_nome`, `pix_termos_aceitos_em` (TIMESTAMP — consentimento), `pix_habilitado_em`, `pix_saque_automatico` (BOOLEAN default false), `pix_saque_minimo` (INTEGER default 50000 = R$500,00 em centavos)
  - Em `pedidos`: `metodo_pagamento`, `woovi_charge_id`, `woovi_correlation_id`, `pix_qr_code`, `pix_qr_code_imagem`, `status_pagamento`, `pagamento_confirmado_em`
  - Tabela `pix_transacoes`: id, restaurante_id, pedido_id, woovi_charge_id, correlation_id, valor_centavos, status, webhook_recebido_em, criado_em
  - Tabela `pix_saques`: id, restaurante_id, valor_centavos, taxa_centavos (0 ou 100), status [solicitado/concluido/falhou], solicitado_em, concluido_em, automatico (BOOLEAN)
- [ ] Models ORM: `PixTransacao`, `PixSaque` em `database/models.py`
- [ ] Service `backend/app/pix/woovi_service.py`:
  - `criar_subconta(pix_chave, nome)` → `POST /api/v1/subaccount`
  - `consultar_saldo(pix_chave)` → `GET /api/v1/subaccount/{pixKey}` → retorna centavos
  - `criar_cobranca(valor_centavos, correlation_id, pix_chave_rest)` → `POST /api/v1/charge` com split 100%
  - `sacar_total(pix_chave)` → `POST /api/v1/subaccount/{pixKey}/withdraw`
  - `transferir(from_key, to_key, valor_centavos)` → `POST /api/v1/subaccount/transfer`
  - `sacar_parcial(pix_chave, valor_centavos)` → transfer excedente → vault, withdraw, transfer back
  - `validar_webhook(payload, signature)` → HMAC-SHA256
- [ ] Endpoint: `POST /painel/pix/ativar` — recebe chave Pix + tipo + nome + aceite de termos → cria subconta → salva
- [ ] Endpoint: `GET /painel/pix/status` — status + saldo + config saque + histórico saques
- [ ] Endpoint: `POST /painel/pix/desativar` — desativa (não deleta subconta Woovi)
- [ ] Endpoint: `PUT /painel/pix/config-saque` — configura saque automático (ligado/desligado + valor mínimo)
- [ ] Endpoint: `POST /painel/pix/sacar` — recebe `valor_centavos`, valida saldo, retorna preview com taxa antes de confirmar
- [ ] Endpoint: `POST /painel/pix/sacar/confirmar` — executa o saque (parcial ou total)
- [ ] Endpoint: `POST /painel/pedidos/{id}/pix/cobrar` — gerar QR Code
- [ ] Webhook: `POST /webhooks/woovi` — público, valida HMAC-SHA256, processa `OPENPIX:CHARGE_COMPLETED`
- [ ] Endpoint: `GET /cliente/{codigo}/pedido/{id}/pagamento-status` — polling cliente
- [ ] WebSocket: notificar restaurante ao confirmar pagamento
- [ ] Task periódica (billing_tasks.py ou novo pix_tasks.py): a cada 30 min, verificar restaurantes com `pix_saque_automatico=True` e saldo ≥ `pix_saque_minimo` → executar saque automático

**Fase 3: Frontend Painel — Adesão com Consentimento**
- [ ] Página "Pagamentos Online" no painel com 4 estados:
  - **Estado 1 — Não aderido:**
    - Card informativo profissional com regras claras:
      > **Receba pagamentos Pix online dos seus clientes!**
      > - A Derekh Food oferece este serviço **100% gratuito** para seu negócio crescer sem barreiras
      > - Utilizamos o sistema de split de pagamentos da Woovi (instituição regulada pelo Banco Central)
      > - A Woovi cobra **R$0,85 por pagamento Pix** recebido — a Derekh Food não cobra nada
      > - Saques para sua conta: **R$1,00 por saque** (grátis para saques ≥ R$500)
      > - Você pode configurar saque automático para nunca pagar taxa
      > - Não é necessário criar conta na Woovi — tudo é gerenciado pelo seu painel Derekh
    - Formulário de adesão:
      - Select tipo chave Pix (CPF / CNPJ / E-mail / Celular / Aleatória)
      - Input chave Pix (validação conforme tipo selecionado)
      - Nome da subconta (pré-preenchido com nome do restaurante)
    - Checkbox obrigatório: "Li e concordo com as regras de pagamento Pix online" (link para termos)
    - Botão "Ativar Pix Online" (desabilitado até aceitar termos)
  - **Estado 2 — Pix ativo (dashboard financeiro):**
    - Chave Pix exibida (mascarada parcialmente) + tipo + botão alterar
    - **Card saldo:** "Saldo disponível: R$ XXX,XX" (consulta Woovi em tempo real)
    - **Seção saque manual:**
      - Input valor (igual interface de transferência bancária: "Quanto deseja sacar?")
      - Validação: mínimo R$1, máximo = saldo disponível
      - Botão "Sacar" → abre modal de confirmação:
        - Se valor < R$500: aviso amarelo "Será cobrada taxa de R$1,00 pela Woovi. Você receberá R$ XX,XX"
        - Se valor ≥ R$500: badge verde "Saque sem taxa! Você receberá R$ XX,XX"
        - Destino: "Chave Pix: ***XXX" (chave mascarada)
        - Botão "Confirmar Saque" / "Cancelar"
    - **Seção saque automático:**
      - Toggle "Saque automático" (liga/desliga)
      - Se ligado: select "Sacar quando saldo atingir:" → R$500 (recomendado — sem taxa) | R$1.000
      - Aviso: "O saque automático é feito para sua chave Pix cadastrada. Sem taxa para saques ≥ R$500."
    - **Histórico de saques:** tabela com data, valor, taxa, status (concluído/processando/falhou)
    - Botão "Desativar Pix Online"
- [ ] Badge "Aguardando Pix" / "Pix Confirmado" nos cards de pedido
- [ ] Modal QR Code no detalhe do pedido (QR + código copia-e-cola)
- [ ] Notificação sonora/visual ao confirmar Pix (WebSocket)

**Fase 4: Frontend Cliente**
- [ ] Opção "Pagar com Pix" no checkout (só aparece se restaurante tem pix_habilitado)
- [ ] Tela QR Code com countdown 30 min + código copia-e-cola + polling automático
- [ ] Tela de confirmação pós-pagamento (redireciona ao confirmar)

**Fase 5: Frontend Super Admin**
- [ ] Badge "Pix Ativo/Inativo" na listagem de restaurantes
- [ ] Coluna saldo Pix agregado

**Fase 6: Deploy**
- [ ] Secrets Fly.io: `WOOVI_APP_ID`, `WOOVI_WEBHOOK_SECRET`
- [ ] Deploy + testar E2E: consentimento → ativar → subconta → pedido → QR → pagamento → webhook → saque manual + automático
- [ ] Validar webhook público em produção
- [ ] Confirmar com Woovi: valor exato de isenção de taxa (R$500 ou R$1.000)

---

### MÓDULO 2 — KDS / Comanda Digital — Sprint 18 — Migration 029

**Fase 1: Backend Models + Migration**
- [x] Migration 029: tabelas `cozinheiros`, `cozinheiro_produtos`, `pedidos_cozinha`, `config_cozinha`
- [x] Models ORM: `Cozinheiro`, `CozinheiroProduto`, `PedidoCozinha`, `ConfigCozinha`

**Fase 2: Backend Endpoints Admin**
- [x] CRUD cozinheiros: `GET/POST /painel/cozinha/cozinheiros`, `PUT/DELETE /painel/cozinha/cozinheiros/{id}`
- [x] Config: `GET/PUT /painel/cozinha/config`
- [x] Dashboard: `GET /painel/cozinha/dashboard`

**Fase 3: Backend Endpoints KDS**
- [x] Auth: `POST /auth/cozinheiro/login`, `GET /auth/cozinheiro/me` → JWT role=cozinheiro
- [x] Pedidos: `GET /kds/pedidos`, `PATCH /kds/pedidos/{id}/status`, `POST /kds/pedidos/{id}/assumir`, `POST /kds/pedidos/{id}/refazer`
- [x] Auto-criação PedidoCozinha: ao mudar pedido para `em_preparo` + KDS ativo → cria PedidoCozinha(NOVO)

**Fase 4: Backend WebSocket KDS**
- [x] Canal `/ws/kds/{restaurante_id}?token={jwt}`, eventos: `kds:novo_pedido`, `kds:pedido_atualizado`

**Fase 5: Frontend Admin**
- [x] Página "Cozinha Digital" no painel (CRUD cozinheiros + config + monitor)
- [x] Hooks em `useAdminQueries.ts` (7 hooks)
- [x] Menu sidebar "Cozinha Digital" (ChefHat icon)

**Fase 6: Frontend PWA KDS**
- [x] App React em `src/kds/` (rota `/cozinha`), `KdsAuthContext`, `useKdsQueries.ts`
- [x] Login cozinheiro (dark theme, código restaurante + login + senha)
- [x] Tela PREPARO: fila horizontal + card comanda + COMECEI/FEITO
- [x] Tela DESPACHO: pedidos FEITOS + PRONTO + REFAZER
- [x] Sons (Web Audio API): sndNew (880Hz+1174Hz), sndDone (523Hz), sndReady (523+659+783Hz)

**Fase 7: Melhorias KDS (22/03)**
- [x] Auto-envio para cozinha ao criar pedido (carrinho.py) — KDS ativo → em_preparo + PedidoCozinha NOVO
- [x] Sincronização KDS→Pedido: cook marca PRONTO → Pedido.status='pronto' + tempo_preparo_real_min
- [x] Pausar/despausar pedido na cozinha (endpoints POST /painel/pedidos/{id}/pausar e despausar)
- [x] Migration 031: campos pausado, pausado_em, despausado_em, posicao_original em pedidos_cozinha
- [x] Endpoint GET /painel/cozinha/desempenho — ranking cozinheiros por tempo médio
- [x] Frontend admin: aba Desempenho na CozinhaDigital (ranking + filtro período)
- [x] Frontend admin: Pedidos.tsx remove "Marcar Pronto" quando KDS ativo, adiciona Pausar
- [x] Frontend KDS: pedidos pausados com cadeado, final da fila, botões desabilitados
- [x] WebSocket: kds:pedido_pausado, kds:pedido_despausado

**Fase 8: Deploy**
- [ ] Deploy migrations 029-031 + testar fluxo pedido → cozinha → pausa → despacho

---

### MÓDULO 3 — App Garçom — Sprint 19 — Migration 030

**Fase 1: Backend Models + Migration**
- [ ] Migration 030: tabelas `garcons` (id, restaurante_id, nome, login, senha_hash, secao_inicio, secao_fim, modo_secao [FAIXA/TODOS/CUSTOM], avatar_emoji, ativo), `garcom_mesas` (garcom_id, mesa_id), `config_garcom` (restaurante_id UNIQUE, taxa_servico, pct_taxa, couvert_auto, item_couvert_id, campos_obrigatorios, permitir_cancelamento), `sessoes_mesa` (id, restaurante_id, mesa_id, garcom_id, status [ABERTA/FECHANDO/FECHADA], qtd_pessoas, alergia, tags, subtotal, taxa, total), `sessao_pedidos` (sessao_id, pedido_id), `itens_esgotados` (id, restaurante_id, item_cardapio_id, reportado_por, ativo)
- [ ] Campos novos em `pedidos`: `course`, `tipo_origem`, `label_origem`
- [ ] Campos novos em `itens_pedido`: `status_cozinha`, `cancelado`, `cancelado_em`
- [ ] Models ORM: `Garcom`, `GarcomMesa`, `ConfigGarcom`, `SessaoMesa`, `SessaoPedido`, `ItemEsgotado`

**Fase 2: Backend Endpoints Admin**
- [ ] CRUD garçons: `GET/POST /painel/garcons`, `PUT/DELETE /painel/garcons/{id}`
- [ ] Config: `GET/PUT /painel/garcons/config`
- [ ] Monitor: `GET /painel/garcons/monitor`

**Fase 3: Backend Endpoints Garçom**
- [ ] Auth: `POST /garcom/auth/login` → JWT role=garcom
- [ ] Mesas: `GET /garcom/mesas`, `POST /garcom/mesas/{id}/abrir`, `POST /garcom/mesas/{id}/transferir`
- [ ] Sessão: `GET /garcom/sessoes/{id}`, `POST /garcom/sessoes/{id}/pedidos`, `POST /garcom/sessoes/{id}/solicitar-fechamento`
- [ ] Itens: `DELETE /garcom/pedidos/{id}/itens/{item_id}`, `POST/DELETE /garcom/itens-esgotados`

**Fase 4: Backend WebSocket**
- [ ] Canal `/ws/garcom?token={jwt}`, eventos: `garcom:pedido_pronto`, `garcom:item_esgotado`, `garcom:mesa_fechada`

**Fase 5: Frontend Admin**
- [ ] Página "Garçons e Atendimento" no painel (CRUD + config + monitor)
- [ ] Hooks em `useAdminQueries.ts`

**Fase 6: Frontend PWA Garçom**
- [ ] App React em `src/garcom/` (rota `/garcom`), `GarcomAuthContext`, `useGarcomQueries.ts`
- [ ] Login garçom
- [ ] Grid de mesas (status visual: LIVRE/OCUPADA/FECHANDO/PRONTO)
- [ ] Modal abertura mesa (pessoas, alergia, tags)
- [ ] Detalhe da mesa (pedidos por etapa, conta, cancelados)
- [ ] Cardápio (categorias, carrinho, enviar pedido com course)
- [ ] Notificações pedido pronto (WebSocket do KDS) + sons + badges
- [ ] PWA manifest + service worker

**Fase 7: Deploy**
- [ ] Deploy migration 030 + testar fluxo garçom → mesa → pedido → KDS → pronto

---

### MÓDULO 4 — Bot WhatsApp IA — Sprint 16 — Migration 031

> Plano detalhado: `PLANO_BOT_WHATSAPP.md` (10 etapas, 67 tarefas)
> Docs: `atualização geral do sistema/DEREKH Bot Technical Documentation.html`

**Etapa 1: Infra**
- [ ] Criar `derekh-bot/` (FastAPI + Dockerfile + fly.toml)
- [ ] Webhook: resposta 200 imediata + fila Redis async + idempotência

**Etapa 2: Migration + Guard**
- [ ] Migration 031: campos bot em `config_restaurante` (bot_ativo, nome_atendente, whatsapp_phone_id, etc.)
- [ ] Billing guard: só Premium + billing_status active/trial + bot_ativo=True

**Etapa 3: LLM + Context**
- [ ] `context_builder.py` (3 camadas prompt), `atendente.txt`
- [ ] LLM Router: Grok 3 Mini → fallback, sessão Redis TTL 2h

**Etapa 4: Function Calls MVP**
- [ ] buscar_cliente, cadastrar_cliente, buscar_item, buscar_categorias, criar_pedido, consultar_pedido, verificar_horario

**Etapa 5: Áudio**
- [ ] `audio_handler.py`: Groq Whisper STT → texto → processar

**Etapa 6: Pedido Completo**
- [ ] alterar/cancelar/repetir pedido + guardrails validação dupla

**Etapa 7: Pagamento**
- [ ] Integração Pix Woovi (reusa Módulo 1) + gerar_pix + verificar_pagamento

**Etapa 8: Pós-entrega**
- [ ] Avaliação, detecção atraso, repescagem, workers periódicos

**Etapa 9: Fallback Humano**
- [ ] 3 tentativas → escalar com msg + telefone + WebSocket ao dono

**Etapa 10: Deploy**
- [ ] Deploy `derekh-bot` no Fly.io (GRU) + secrets + teste E2E

---

### MÓDULO 5 — Sales Autopilot (Hacking-restaurant-b2b) — Sprint 20

> Código existente em `Hacking-restaurant-b2b/`. Micro-fases 1-5 já implementadas.

**Fase 1: Deploy Existente**
- [ ] Configurar secrets Fly.io (derekh-crm): RESEND_API_KEY, XAI_API_KEY, EVOLUTION_*
- [ ] Deploy + testar E2E com APIs reais (email + WA + agente autônomo)

**Fase 2: Contact Validator**
- [ ] `contact_validator.py`: detectar email/tel contador, verificar WA, classificar canal
- [ ] Migration: campos validação em `leads`

**Fase 3: Lead Enricher**
- [ ] `lead_enricher.py`: cenários A/B/C/D, enriquecer Maps/Instagram/Facebook
- [ ] Captura ratings delivery (iFood/Rappi/99Food)
- [ ] Migration: campos enriquecimento + ratings em `leads`

**Fase 4: Admin Brain**
- [ ] `admin_brain.py`: chat linguagem natural, 24 function calls
- [ ] Endpoint `POST /admin/brain/chat` + frontend interface chat

**Fase 5: Pattern Library**
- [ ] Tabelas `padroes_vencedores` + `mensagens_geradas`
- [ ] Ciclo diário `extrair_padroes_diario()` + decaimento

---

### MÓDULO 6 — Printer Agent (Windows Service) — Sprint 21 — Migration 032

> Sistema separado (Windows). Bridge endpoints no backend SaaS.

**Fase 1: Bridge Backend**
- [ ] Migration 032: tabelas `bridge_patterns`, `bridge_raw_examples`, `bridge_groq_usage`, `bridge_learning_events`
- [ ] Router: `POST /api/bridge/parse`, `POST /api/bridge/orders`, `GET /api/bridge/config`
- [ ] Services: `groq_service.py` + `pattern_engine.py`

**Fase 2: Windows Service**
- [ ] `derekh-printer-agent/`: spooler_monitor, escpos_parser, platform_detector
- [ ] HTTP server local (porta 8765) para receber pedidos do SaaS
- [ ] Windows Service (pywin32)

**Fase 3: Groq Learning**
- [ ] Ciclo 3 fases: Cego → Aprendendo → Autônomo (confidence >= 0.90)
- [ ] Pattern cache local + sync com backend

**Fase 4: Super Admin Dashboard**
- [ ] Endpoints `/api/admin/bridge/*` + página "Impressoras" no super admin

**Fase 5: Instalador**
- [ ] Setup wizard + Inno Setup + PyInstaller → `.exe`

---

## CONTAS EXTERNAS NECESSÁRIAS

| Serviço | URL de Cadastro | Uso | Módulo |
|---------|----------------|-----|--------|
| Woovi/OpenPix | https://app.woovi.com/register | Pix online com split | 1 |
| xAI | https://console.x.ai | Grok LLM (bot + vendas) | 4, 5 |
| Groq | https://console.groq.com | Whisper STT + learning | 4, 6 |
| Resend | https://resend.com/signup | Email marketing B2B | 5 |
| Meta Business | https://business.facebook.com | WhatsApp Cloud API | 4 |
| Evolution API | Self-hosted ou opção cloud | WhatsApp gateway | 4, 5 |
| Transfeera | Aguardando consultor | Split Pix alternativo (futuro) | 1 |

---

## CREDENCIAIS DE TESTE

- **Super Admin:** `superadmin` / `SuperFood2025!`
- **Restaurante teste:** código de acesso `237CC868`, nome "pizza tuga"
- **Senha padrão restaurante:** 6 primeiros dígitos do telefone
- **Conta Fly.io:** kleniltonportugal@gmail.com
