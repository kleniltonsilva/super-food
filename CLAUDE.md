# CLAUDE.md — Derekh Food

> **Hub de regras fundamentais.** Informações detalhadas (arquitetura, deploy, plano mestre, etc.) ficam fragmentadas em `memory/*.md` e são carregadas SOB DEMANDA conforme a tarefa — nunca todas de uma vez. Ver seção "Mapa da Memória".

## IDENTIDADE

- **Nome:** Derekh Food (anteriormente Super Food)
- **Versão:** 4.1.0
- **Autor:** Klenilton Silva (@kleniltonsilva)
- **Tipo:** SaaS multi-tenant de delivery para restaurantes (proprietário)
- **Produção:** https://superfood-api.fly.dev (Fly.io, região GRU)

## REGRAS FUNDAMENTAIS

1. Responder **sempre em português**.
2. Gerar **código completo**, nunca snippets parciais.
3. **TODAS** as queries filtram por `restaurante_id` (multi-tenant obrigatório).
4. No React, usar hooks de `hooks/useQueries.ts` — **NUNCA** `useState+useEffect` manual para fetching.
5. Senhas **SEMPRE** com `.strip()` antes de hash.
6. Interceptor 401 já existe no `apiClient.ts` — não duplicar.
7. Ao concluir sprint/tarefa, atualizar `MEMORY.md` (hub) e nó temático correspondente.
8. **GESTÃO DE MEMÓRIA — PADRÃO REDE NEURAL (OBRIGATÓRIO):**
    - **Hub:** `MEMORY.md` — ultra-lean (~50 linhas), carregado SEMPRE, contém ponteiros
    - **Nós temáticos:** arquivos filhos carregados SOMENTE quando a tarefa exige aquele tema
    - **Diretório:** `/home/pcempresa/.claude/projects/-home-pcempresa-Documentos-super-food/memory/`
    - **Ciclo de vida:**
        - Ao iniciar sessão: ler `MEMORY.md` → identificar nós relevantes → carregar sob demanda
        - Durante sessão: atualizar nó temático EM PARALELO com o trabalho
        - Ao finalizar: atualizar hub com estado atual
    - **Esquecimento ativo:** limite ~120 linhas por nó. Comprimir sessões antigas, apagar bugs obsoletos, remover arquivos deletados. Prioridade: recente e recorrente > antigo e pontual.
    - **Princípio de economia:** o sistema existe para ECONOMIZAR tokens. Não atualizar para mudanças triviais. Não ler nós desnecessários. Se a tarefa é simples, não tocar na memória.
9. **CHECKBOXES:** Ao concluir etapas do Plano Mestre (`memory/plano-mestre.md`), marcar `[x]` IMEDIATAMENTE. Nunca deixar para depois.
10. **DOCUMENTAÇÃO TÉCNICA (INQUEBRÁVEL):** Ao criar funcionalidades, endpoints, páginas ou alterações significativas, **ATUALIZAR `DOCUMENTACAO_TECNICA.md` IMEDIATAMENTE**. Esta regra **NUNCA** pode ser quebrada.
11. **APK MOTOBOY (App Nativo Android) — Ciclo obrigatório:**
    Quando alteração afeta motoboy (`client/src/motoboy/`, `motoboy-app/`, endpoints usados pelo motoboy, deps compartilhadas):
    1. Incrementar versão em `motoboy-app/version.json` (`version` + `versionCode` — sempre +1)
    2. Commit e push para `main` — GitHub Actions (`build-motoboy-apk.yml`) gera APK automaticamente
    3. Aguardar build success: `gh run list --limit 1`
    4. Deploy backend (`fly deploy`) — para servir `version.json` atualizado em `/api/public/app-version`
    5. App nativo detecta via `update-checker.ts` e mostra modal "Atualizar Agora"
    - **Arquivos-chave:** `motoboy-app/version.json`, `.github/workflows/build-motoboy-apk.yml`, `motoboy-app/src/native/update-checker.ts`
    - **NUNCA** alterar código do motoboy sem gerar novo APK — app nativo usa assets locais e NÃO atualiza sozinho
    - **ASSINATURA APK:** Keystore permanente via secrets GitHub (`MOTOBOY_KEYSTORE_BASE64` etc.). Sem secrets, CI gera keystore novo → usuário precisa desinstalar e reinstalar. Ver DOCUMENTACAO_TECNICA.md seção 20.5.1
    - **Versão atual:** 1.1.1 (versionCode 4)

---

## MAPA DA MEMÓRIA (Rede Neural)

```
CLAUDE.md (este — regras + ponteiros, SEMPRE carregado)
memory/MEMORY.md (hub — estado atual, SEMPRE carregado)
│
├── architecture.md ─── Stack, caminhos, ORM models, routers, auth, feature flags, estrutura, apps
├── frontend.md ─────── 7 apps React, hooks, contexts, API clients, páginas
├── conventions.md ──── Padrões de código, gotchas, erros comuns a evitar
├── deploy.md ───────── Fly.io, Docker, secrets, volume, migrations PostgreSQL
├── billing.md ──────── Sistema Asaas, billing flow, add-ons, feature flags
├── bot-whatsapp.md ─── Sprint 16 bot, LLM, function calls, onboarding self-service
├── meta-whatsapp.md ── Meta Business, App ID, WABA, tokens, webhook
├── integrations.md ─── iFood, Open Delivery, marketplace
├── sprints.md ──────── Histórico sprints + marcos
├── plano-mestre.md ─── 6 módulos (Pix, KDS, Garçom, Bot, Sales, Bridge) — checkboxes
├── bridge-agent.md ─── Bridge Agent, Groq IA, ciclo aprendizado
├── sales-autopilot.md  CRM B2B, outreach, email branded, WA bot
└── corrections-log.md  Histórico bugs corrigidos
```

**Quando carregar cada nó:**

| Nó | Carregar quando... |
|----|-------------------|
| `architecture.md` | Criar endpoints, models, routers, entender estrutura/stack |
| `frontend.md` | Criar/editar componentes React, hooks, páginas, contexts |
| `conventions.md` | Qualquer tarefa de código (consulta rápida de gotchas) |
| `deploy.md` | Deploy, migrations, infra Fly.io, Docker, volume |
| `billing.md` | Billing, assinatura, Asaas, planos, add-ons |
| `bot-whatsapp.md` | Bot WhatsApp, LLM, function calls, onboarding phone |
| `meta-whatsapp.md` | Config Meta Business, WABA, tokens, webhook |
| `integrations.md` | iFood, Open Delivery, credenciais plataforma |
| `sprints.md` | Planejamento, priorização, marcos |
| `plano-mestre.md` | Trabalhar em qualquer módulo do plano (marcar checkboxes) |
| `bridge-agent.md` | Bridge/impressora/parser/Windows spooler |
| `sales-autopilot.md` | CRM outreach, email B2B, WA sales bot |
| `corrections-log.md` | Debug, investigar bug similar a um antigo |

---

## CREDENCIAIS DE TESTE

- **Super Admin:** `superadmin` / `SuperFood2025!`
- **Restaurante teste:** código `237CC868`, nome "pizza tuga"
- **Senha padrão restaurante:** 6 primeiros dígitos do telefone
- **Conta Fly.io:** kleniltonportugal@gmail.com

---

## DEPLOY RÁPIDO

> **Detalhes completos (secrets, regras migrations PostgreSQL, checklist):** ver `memory/deploy.md`

```bash
# Antes:
npm run check && npm run build

# Deploy:
cd /home/pcempresa/Documentos/super-food && ~/.fly/bin/fly deploy

# Depois:
~/.fly/bin/fly logs --app superfood-api
curl https://superfood-api.fly.dev/health
```

**Regra de ouro migrations:** NUNCA try/except em Alembic para PostgreSQL. SEMPRE usar SQL com `IF EXISTS`/`IF NOT EXISTS`. Ver `memory/deploy.md` para detalhes.

**Regra volume:** NUNCA deletar `superfood_uploads` sem migrar. Quando ~700MB → migrar para R2.
