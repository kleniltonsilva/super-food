# CLAUDE.md — Derekh Food

## REGRAS

1. Responder **sempre em português**.
2. Gerar **codigo completo**, nunca snippets parciais.
3. **TODAS** as queries filtram por `restaurante_id` (multi-tenant).
4. No React, usar hooks de `hooks/useQueries.ts` — **NUNCA** useState+useEffect manual para fetching.
5. Senhas **SEMPRE** com `.strip()` antes de hash.
6. Interceptor 401 ja existe no `apiClient.ts` — nao duplicar.
7. Ao concluir sprint/tarefa, **substituir checkboxes por resumo de 1 linha** — CLAUDE.md maximo 250 linhas.
8. **GESTAO AUTOMATICA DE MEMORIA (OBRIGATORIO):**
    - **Diretorio:** `/home/pcempresa/.claude/projects/-home-pcempresa-Documentos-super-food/memory/`
    - Ao iniciar sessao: ler MEMORY.md + arquivos de topico relevantes
    - Durante sessao: salvar padroes/bugs/decisoes nos arquivos de topico
    - Ao finalizar: atualizar MEMORY.md (<150 linhas) + CLAUDE.md estado atual
    - Arquivos: `MEMORY.md` (estado), `architecture.md` (caminhos/stack), `corrections-log.md` (bugs)
    - **Referencia somente-leitura:** `README.md` (stack/endpoints/fluxos), `ESTRUTURA.md` (arvore)

---

## ESTADO ATUAL DO PROJETO

- **Versao:** 4.0.0 (tag v4.0.0)
- **Sprint atual:** Sprint 14 — Refatoração integrações marketplace (credenciais plataforma)
- **Ultima sessao:** 16/03/2026
- **Migrations em produção:** 001-025 (última: 025_platform_credentials)
- **Bugs conhecidos:** Nenhum crítico
- **Pendente:** domínio próprio, alertas downtime, testar integrações com conta real

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
- App: `superfood-api` — https://superfood-api.fly.dev (GRU)
- PostgreSQL: `superfood-db` — flycast:5432
- Redis: Upstash — fly-superfood-redis.upstash.io:6379
- Volume: `superfood_uploads` (1GB) em `/app/backend/static/uploads`
- Secrets: SECRET_KEY, SUPER_ADMIN_*, MAPBOX_TOKEN, REDIS_URL, SENTRY_*, FLY_API_TOKEN, STORAGE_BACKEND

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
# ✅ CORRETO
op.execute("ALTER TABLE x DROP CONSTRAINT IF EXISTS nome")
op.execute("CREATE INDEX IF NOT EXISTS ix_nome ON tabela (coluna)")

# ✅ Constraints condicionais
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
│   ├── main.py              # FastAPI entry + WebSocket + lifespan
│   ├── routers/
│   │   ├── painel.py        # Todas rotas /painel/* (admin restaurante)
│   │   ├── integracoes.py   # Integrações marketplace (connect/disconnect)
│   │   ├── admin.py         # Super Admin /api/admin/* + credenciais plataforma
│   │   ├── carrinho.py      # Carrinho/checkout cliente
│   │   ├── site_cliente.py  # Site público
│   │   ├── auth_restaurante.py / auth_cliente.py / upload.py / motoboys.py
│   ├── models.py            # Re-exporta models de database/models.py
│   ├── database.py          # Config BD SQLite/PostgreSQL
│   ├── auth.py              # JWT helpers
│   ├── integrations/        # iFood + Open Delivery clients
│   │   ├── ifood/           # client.py, mapper.py, status_machine.py, catalog_sync.py
│   │   ├── opendelivery/    # client.py, mapper.py
│   │   ├── base.py, manager.py
│   ├── utils/               # Helpers (despacho, menus, comanda)
│   └── websocket_manager.py # Redis Pub/Sub multi-worker
├── restaurante-pedido-online/client/src/
│   ├── admin/               # Painel restaurante (20+ páginas)
│   ├── superadmin/          # Super Admin (+ IntegracoesPlatforma)
│   ├── motoboy/             # App motoboy PWA
│   ├── pages/               # Site cliente
│   └── components/          # shadcn/ui compartilhados
├── database/models.py       # SQLAlchemy ORM models (source of truth)
├── printer_agent/           # Agent impressão Windows (ESC/POS)
├── migrations/versions/     # Alembic 001-025
└── requirements.txt
```

**Stack:** FastAPI + SQLAlchemy + JWT | React 19 + TypeScript + Vite + Tailwind 4 + TanStack Query v5
**Router:** wouter | **UI:** shadcn/radix-ui | **Build:** `dist/public/` servido pelo FastAPI

---

## HISTÓRICO DE SPRINTS (completos)

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
| 14 | Refatoração integrações (credenciais plataforma) | 🔄 Em andamento |

---

## TAREFAS PENDENTES

### Sprint 11 (pendentes)
- [ ] Comprar domínio + `fly certs add` + DNS
- [ ] Configurar alertas downtime (Fly.io dashboard)

### Sprint 12 — Migração R2 (quando necessário)
- Cloudflare R2 bucket + secrets + `STORAGE_BACKEND=r2` + migrar imagens
- Código pronto em `storage.py` (R2StorageBackend)

### Sprint 14 — Arquitetura Integrações Marketplace
- **Modelo:** CredencialPlataforma (Super Admin) + IntegracaoMarketplace (por restaurante, só autorização)
- **iFood:** userCode + authorization_code flow (1 credencial Derekh Food)
- **Open Delivery:** webhook authorization (1 credencial por marketplace)
- **Super Admin:** CRUD credenciais em /api/admin/integracoes/plataformas
- **Restaurante:** connect/disconnect flow (sem inserir credenciais)
