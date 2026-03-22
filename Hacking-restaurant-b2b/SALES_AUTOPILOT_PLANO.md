# SALES AUTOPILOT — Plano Técnico Completo

## Idioma
Sempre em **português brasileiro (pt-BR)**.

---

## AUDITORIA PRÉ-IMPLEMENTAÇÃO

### Análise de Engenharia de Software — O que pode quebrar

Antes de criar qualquer código novo, identifiquei os seguintes riscos reais no código existente que AFETAM diretamente o Sales Autopilot:

#### ERROS DE LÓGICA ENCONTRADOS

| # | Módulo | Problema | Impacto no Autopilot | Severidade |
|---|--------|----------|---------------------|------------|
| 1 | **schema.sql** | Não existe tabela `emails_enviados` separada. Emails enviados ficam em `interacoes` com `email_message_id`. | Tracking de pixel/clique precisa de tabela dedicada — misturar com interações genéricas torna queries lentas e lógica confusa. | CRÍTICO |
| 2 | **schema.sql** | Já existe `lead_sequencia` + `sequencia_etapas` para sequências de email. O plano original do Autopilot quer criar `outreach_sequencia` separada. | **Duplicação**: dois sistemas de sequência (um manual, um automático) causam conflitos — lead pode estar em ambos simultaneamente. | CRÍTICO |
| 3 | **scoring.py** | `_get_conn()` abre conexão nova a cada chamada (sem pool). `calcular_scores_todos()` com 330k leads abre centenas de conexões. | Se o Autopilot chamar `calcular_score` em loop (re-scoring após evento), pode esgotar conexões PostgreSQL. | ALTO |
| 4 | **scoring.py** | Lógica de segmento sobreposta: lead pode ser "novo" E "quente" ao mesmo tempo, mas retorna só "novo" (verificado antes). | Leads HOT (score>=80) podem ter segmento "novo" se abriram há <6 meses, recebendo tratamento errado no Autopilot. | ALTO |
| 5 | **email_service.py** | Webhook Resend sem validação de assinatura — qualquer POST em `/webhooks/resend` é aceito. | Atacante pode marcar todos emails como "abertos" ou "bounced", corrompendo dados do agente autônomo. | ALTO |
| 6 | **email_service.py** | `enviar_campanha()` não tem transação — se falhar no email 50 de 200, contadores ficam desincronizados. | Outreach engine pode re-enviar emails já enviados (pois DB diz que não foram). | ALTO |
| 7 | **whatsapp_service.py** | Gera apenas links `wa.me` (redirect browser). Não envia mensagens programaticamente. | wa_sales_bot.py precisa de integração REAL com Evolution API (HTTP POST). O módulo atual é INÚTIL para automação. | CRÍTICO |
| 8 | **app.py** | Zero autenticação. Todas as rotas são públicas. | Rotas do agente (`/agente/aprovar`, `/outreach/opt-out`) ficam expostas. Qualquer um pode aprovar decisões do agente ou fazer opt-out em massa. | CRÍTICO |
| 9 | **database.py** | Pool min=2, max=10. Workers do Autopilot (cron outreach + cron agente + web) competem por conexões. | Com 3 processos + requests web simultâneos, pool de 10 pode travar. Deadlock potencial. | MÉDIO |
| 10 | **config_outreach** vs **configuracoes** | Plano original cria `config_outreach` nova, mas já existe tabela `configuracoes` com chave-valor. | Duas tabelas de configuração = confusão. Melhor usar a existente `configuracoes` com prefixo `outreach_`. | MÉDIO |
| 11 | **sync_crm.py** | Protege campos CRM (score, pipeline, notas), mas NÃO protege campos de delivery. | Se sync rodar após outreach verificar delivery, pode sobrescrever dados com versão antiga do SQLite. | MÉDIO |
| 12 | **db_pg.py** | Campos `ifood_checked`, `rappi_checked`, `99food_checked`, `maps_checked` existem em db_pg mas NÃO no schema.sql. | Scanner funciona, mas schema.sql não tem esses campos. Migration manual necessária. | BAIXO |

#### DECISÕES ARQUITETURAIS OBRIGATÓRIAS

Antes de codar, estas decisões precisam ser tomadas:

| Decisão | Opções | Escolha recomendada | Justificativa |
|---------|--------|-------------------|---------------|
| Sequência duplicada | A) Usar `lead_sequencia` existente. B) Criar `outreach_sequencia` nova. | **B) Criar nova** | `lead_sequencia` é para sequências manuais de email. Outreach é multi-canal (email+WA+áudio) com lógica de tier. Sistemas diferentes. Mas adicionar constraint: lead NÃO pode estar em ambos. |
| Tabela de emails | A) Estender `interacoes`. B) Criar `emails_enviados` separada. | **B) Criar separada** | Tracking de pixel precisa de UUID, contadores de abertura, flags de clique. Misturar com interações genéricas polui a tabela e complica queries. |
| Config outreach | A) Usar `configuracoes` existente. B) Criar `config_outreach`. | **A) Usar existente** com prefixo `outreach_` | Evita duplicação. Já tem CRUD e UI. Adicionar chaves com prefixo `outreach_*` e `agente_*`. |
| Pool de conexões | A) Manter min=2, max=10. B) Aumentar. | **B) min=3, max=20** | Workers do cron + web + agente precisam de mais conexões. |
| Autenticação | A) Ignorar (fase posterior). B) Implementar agora. | **A) Ignorar por enquanto** | Foco no core. Autenticação é Fase 8. Mas NEGAR rotas críticas (aprovar/rejeitar) sem token simples. |
| scoring.py pool | A) Manter `_get_conn()` próprio. B) Usar pool de `database.py`. | **B) Usar pool existente** | Refatorar `scoring.py` para usar `get_conn()` de database.py. Elimina leak de conexões. |

---

## PLANO DE MICRO-FASES

### Convenções do plano
- `(x)` = concluído e testado
- `( )` = pendente
- `[TESTE]` = teste obrigatório antes de prosseguir
- `[RISCO]` = ponto onde o código pode quebrar
- `[DECISÃO]` = decisão que impacta arquitetura

---

## MICRO-FASE 1: Email com Tracking (3-4 dias)

**Objetivo**: Enviar emails com pixel de abertura e link tracking. Webhook real do Resend. Medir open_rate e CTR.

### 1.1 — Migration: novas tabelas e colunas
- (x) Criar tabela `emails_enviados` no schema.sql:
  ```
  id SERIAL PK, lead_id FK->leads, template_id FK->email_templates,
  campanha_id FK->campanhas_email (nullable),
  assunto TEXT, corpo_html TEXT,
  tracking_id UUID DEFAULT gen_random_uuid(),
  pixel_url TEXT,
  horario_enviado TIMESTAMPTZ,
  aberto BOOLEAN DEFAULT FALSE,
  aberto_at TIMESTAMPTZ,
  aberturas_count INTEGER DEFAULT 0,
  clicou_site BOOLEAN DEFAULT FALSE,
  clicou_wa BOOLEAN DEFAULT FALSE,
  clicou_unsub BOOLEAN DEFAULT FALSE,
  bounced BOOLEAN DEFAULT FALSE,
  resend_message_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- (x) Criar tabela `outreach_sequencia`:
  ```
  id SERIAL PK, lead_id FK->leads,
  acao TEXT NOT NULL (enum: enviar_email|reenviar_email|enviar_wa|enviar_audio|followup|ultima_msg|reativacao),
  tier TEXT NOT NULL (hot|warm|cool|cold),
  template_id FK->email_templates (nullable),
  agendado_para TIMESTAMPTZ NOT NULL,
  executado BOOLEAN DEFAULT FALSE,
  executado_at TIMESTAMPTZ,
  cancelado BOOLEAN DEFAULT FALSE,
  resultado TEXT (enviado|aberto|clicou|respondeu|opt_out|bounce|erro),
  erro_detalhe TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- (x) Adicionar colunas em `leads`:
  ```sql
  ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_email BOOLEAN DEFAULT FALSE;
  ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_wa BOOLEAN DEFAULT FALSE;
  ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_at TIMESTAMPTZ;
  ALTER TABLE leads ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'cold';
  ```
- (x) Adicionar configurações iniciais na tabela `configuracoes`:
  ```sql
  INSERT INTO configuracoes (chave, valor) VALUES
    ('outreach_email_dominio', '@derekh.com.br'),
    ('outreach_max_email_dia', '20'),
    ('outreach_warmup_emails_dia', '20'),
    ('outreach_landing_url', 'https://derekh.com.br/food'),
    ('outreach_ativo', 'false')
  ON CONFLICT (chave) DO NOTHING;
  ```
- (x) Criar índices:
  ```sql
  CREATE INDEX IF NOT EXISTS idx_emails_enviados_lead ON emails_enviados(lead_id);
  CREATE INDEX IF NOT EXISTS idx_emails_enviados_tracking ON emails_enviados(tracking_id);
  CREATE INDEX IF NOT EXISTS idx_emails_enviados_campanha ON emails_enviados(campanha_id);
  CREATE INDEX IF NOT EXISTS idx_outreach_pendentes ON outreach_sequencia(agendado_para)
    WHERE executado = FALSE AND cancelado = FALSE;
  CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach_sequencia(lead_id);
  CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
  CREATE INDEX IF NOT EXISTS idx_leads_opt_out ON leads(opt_out_email, opt_out_wa);
  ```
- (x) Criar trigger `updated_at` para `leads` (já existe)
- (x) Rodar migration no PostgreSQL local

```
[TESTE 1.1] Rodar migration no PG local:
  psql derekh_crm < crm/migration_outreach.sql
  - Verificar: \dt (tabelas novas existem)
  - Verificar: \d emails_enviados (colunas corretas)
  - Verificar: \d outreach_sequencia (colunas corretas)
  - Verificar: SELECT * FROM configuracoes WHERE chave LIKE 'outreach_%' (4 registros)
  - Verificar: \di (índices novos existem)
```

### 1.2 — Refatorar scoring.py para usar pool
- (x) Remover `_get_conn()` de scoring.py
- (x) Importar `get_conn` de `crm.database`
- (x) Substituir todas as chamadas internas
- (x) Adicionar função `calcular_tier(score)` → hot|warm|cool|cold
- (x) Adicionar no models.py constantes de tier:
  ```python
  TIERS = {"hot": 80, "warm": 50, "cool": 30, "cold": 0}
  TIER_LABELS = {"hot": "Quente", "warm": "Morno", "cool": "Frio", "cold": "Gelado"}
  ```

```
[TESTE 1.2] Scoring refatorado:
  python -c "from crm.scoring import calcular_tier; print(calcular_tier(85))"  # → "hot"
  python -c "from crm.scoring import calcular_tier; print(calcular_tier(60))"  # → "warm"
  python -c "from crm.scoring import calcular_tier; print(calcular_tier(35))"  # → "cool"
  python -c "from crm.scoring import calcular_tier; print(calcular_tier(10))"  # → "cold"
  python -c "from crm.scoring import calcular_scores_todos; print(calcular_scores_todos())"
  → Não deve dar erro de conexão / deve usar pool
```

### 1.3 — database.py: queries de outreach
- (x) Função `criar_email_enviado(lead_id, template_id, assunto, tracking_id, pixel_url, resend_message_id, campanha_id=None)` → id
- (x) Função `marcar_email_aberto(tracking_id)` → bool (incrementa aberturas_count, seta aberto=True + aberto_at no primeiro)
- (x) Função `marcar_email_clique(tracking_id, tipo_clique)` → bool (tipo: site|wa|unsub)
- (x) Função `marcar_email_bounce(tracking_id)` → bool
- (x) Função `buscar_email_por_tracking(tracking_id)` → dict
- (x) Função `buscar_email_por_resend_id(resend_message_id)` → dict
- (x) Função `emails_enviados_hoje()` → int (guardrail)
- (x) Função `stats_outreach(periodo_dias=7)` → dict
- (x) Função `criar_outreach_acao(lead_id, acao, tier, agendado_para, template_id=None)` → id
- (x) Função `listar_outreach_pendentes(limite=50)` → list[dict]
- (x) Função `listar_outreach_futuras(limite=50)` → list[dict]
- (x) Função `marcar_outreach_executado(acao_id, resultado, erro_detalhe=None)` → bool
- (x) Função `cancelar_outreach_lead(lead_id)` → int (quantidade cancelada)
- (x) Função `opt_out_lead(lead_id, canal)` → bool (seta opt_out_email ou opt_out_wa + cancela ações pendentes)
- (x) Função `leads_para_outreach(cidade, uf, score_min, limite)` → list[dict] (leads sem opt_out, com email, score > 0)
- (x) Função `atualizar_tier_lead(lead_id, tier)` → bool

```
[TESTE 1.3] Queries de outreach:
  python -c "
  from crm.database import init_pool, criar_email_enviado, buscar_email_por_tracking
  import uuid
  init_pool()
  tid = str(uuid.uuid4())
  eid = criar_email_enviado(1, 1, 'Teste', '<p>teste</p>', tid, f'/tracking/pixel/{tid}', 'msg_123')
  print('Email criado:', eid)
  email = buscar_email_por_tracking(tid)
  print('Email encontrado:', email is not None)
  "
  → Email criado: <int>
  → Email encontrado: True
```

### 1.4 — Estender email_service.py com tracking
- (x) Função `gerar_tracking_id()` → UUID string
- (x) Função `gerar_pixel_url(tracking_id)` → URL do pixel transparente 1x1
- (x) Função `gerar_link_rastreado(url_destino, tracking_id, tipo)` → URL wrapper
- (x) Função `gerar_link_unsub(tracking_id)` → link de unsubscribe
- (x) Função `_injetar_tracking(corpo_html, tracking_id)` → injeta pixel + unsub
- (x) Modificar `enviar_email()`: tracking_id, pixel, unsub, emails_enviados + interacoes
- (x) Modificar `processar_webhook_resend()`: busca emails_enviados, fallback interacoes
- (x) Verificar opt_out_email antes de enviar

```
[TESTE 1.4] Email com tracking:
  # Precisa RESEND_API_KEY configurada
  python -c "
  from crm.email_service import enviar_email
  from crm.database import init_pool, buscar_email_por_tracking
  init_pool()
  result = enviar_email(LEAD_ID_REAL, TEMPLATE_ID_REAL)
  print('Resultado:', result)
  # Verificar no banco: SELECT * FROM emails_enviados ORDER BY id DESC LIMIT 1;
  # Verificar: pixel_url preenchido, tracking_id preenchido
  "
```

### 1.5 — Rotas FastAPI de tracking
- (x) `GET /tracking/pixel/{tracking_id}` → retorna imagem 1x1 transparente + marca abertura
- (x) `GET /tracking/click/{tracking_id}/{tipo}` → registra clique + redireciona para URL destino
- (x) `GET /tracking/unsub/{tracking_id}` → marca opt_out + mostra página de confirmação
- (x) `POST /webhooks/resend` → refatorado para usar emails_enviados com fallback
- (x) `GET /api/outreach/stats` → stats_outreach() como JSON
- (x) `GET /api/outreach/pendentes` → lista ações pendentes
- (x) `GET /api/outreach/futuras` → lista ações futuras
- (x) `POST /api/outreach/opt-out/{lead_id}` → opt-out
- (x) `POST /api/outreach/cancelar/{lead_id}` → cancelar ações

```
[TESTE 1.5] Rotas de tracking:
  # Subir server: uvicorn crm.app:app --reload --port 8000

  # Teste pixel (deve retornar imagem 1x1):
  curl -v http://localhost:8000/tracking/pixel/{TRACKING_ID_REAL}
  → Status: 200, Content-Type: image/gif, body: GIF89a...
  → No banco: aberto=True, aberturas_count=1

  # Teste clique:
  curl -v http://localhost:8000/tracking/click/{TRACKING_ID_REAL}/site
  → Status: 302, Location: URL_DESTINO
  → No banco: clicou_site=True

  # Teste unsub:
  curl http://localhost:8000/tracking/unsub/{TRACKING_ID_REAL}
  → Status: 200, HTML com confirmação
  → No banco: lead.opt_out_email=True

  # Teste webhook Resend (simular evento opened):
  curl -X POST http://localhost:8000/webhooks/resend \
    -H "Content-Type: application/json" \
    -d '{"type":"email.opened","data":{"email_id":"msg_123"}}'
  → Status: 200
```

### 1.6 — Teste end-to-end Micro-Fase 1
```
[TESTE E2E 1] Fluxo completo de email com tracking:
  1. Criar template de teste no CRM (UI ou SQL)
  2. Enviar email para SEU email pessoal: POST /api/email/enviar/{lead_id}
  3. Verificar no banco: emails_enviados tem registro com tracking_id
  4. Abrir o email no seu inbox
  5. Verificar no banco: aberto=True, aberturas_count=1
  6. Clicar no link do site no email
  7. Verificar no banco: clicou_site=True
  8. Clicar no link de unsubscribe
  9. Verificar no banco: lead.opt_out_email=True
  10. Tentar enviar outro email para o mesmo lead
  11. Verificar: deve ser BLOQUEADO (opt_out)

  Métricas esperadas:
  - Email entregue em < 30s
  - Pixel carregado no email (verificar image load)
  - Links redirecionam corretamente
  - Opt-out funciona e cancela futuras ações
```

**[RISCO 1.6]** SPF/DKIM/DMARC do domínio @derekh.com.br pode não estar configurado → emails vão para spam. Testar com email pessoal antes de enviar para leads reais.

---

## MICRO-FASE 2: Sequência Automática + Outreach Engine (3-4 dias)

**Objetivo**: Motor que importa leads, calcula tier, cria sequência de ações, e executa automaticamente via cron.

**Pré-requisito**: Micro-Fase 1 concluída e testada.

### 2.1 — models.py: constantes de outreach
- ( ) Adicionar constantes:
  ```python
  # Tiers (já adicionado em 1.2)

  # Ações de outreach
  ACOES_OUTREACH = ["enviar_email", "reenviar_email", "enviar_wa", "enviar_audio",
                     "followup", "ultima_msg", "reativacao"]
  ACOES_OUTREACH_LABELS = {
      "enviar_email": "Enviar email", "reenviar_email": "Reenviar email",
      "enviar_wa": "Enviar WhatsApp", "enviar_audio": "Enviar áudio",
      "followup": "Follow-up", "ultima_msg": "Última mensagem",
      "reativacao": "Reativação"
  }

  # Resultados de outreach
  RESULTADOS_OUTREACH = ["enviado", "aberto", "clicou", "respondeu", "opt_out", "bounce", "erro"]

  # Stages do outreach (separado do pipeline CRM manual)
  OUTREACH_STAGES = ["novo", "email_enviado", "email_aberto", "wa_enviado",
                      "engajado", "demo_agendada", "convertido", "opt_out", "sem_resposta"]
  ```

```
[TESTE 2.1] Constantes importáveis:
  python -c "from crm.models import ACOES_OUTREACH, TIERS; print(ACOES_OUTREACH); print(TIERS)"
```

### 2.2 — outreach_engine.py: core do motor
- ( ) Função `importar_leads_para_outreach(cidade, uf, score_min=30, limite=100)`:
  - Busca leads com `score >= score_min`, `opt_out_email=False`, `email IS NOT NULL`
  - Calcula tier para cada lead
  - Retorna lista de leads com tier calculado
- ( ) Função `criar_sequencia_lead(lead_id, tier, score)`:
  - HOT (>=80): se tem WA → ação "enviar_wa" imediata, senão → "enviar_email" imediata
  - WARM (50-79): "enviar_email" D+0, check D+1 (programado internamente), re-email D+3 se não abriu
  - COOL (30-49): "enviar_email" D+0, sem follow-up automático
  - COLD (<30): não cria sequência (ignora)
  - Retorna lista de ações criadas
- ( ) Função `executar_acoes_pendentes()`:
  - Busca ações WHERE `executado=FALSE AND cancelado=FALSE AND agendado_para <= NOW()`
  - Verifica guardrails: max emails/dia, opt_out
  - Para cada ação:
    - `enviar_email`: chama `enviar_email()` com tracking
    - `reenviar_email`: verifica se abriu, se não → reenvia com assunto diferente
    - `enviar_wa`: (Micro-Fase 3) → marca como "pendente_wa" por enquanto
    - `enviar_audio`: (Micro-Fase 4) → marca como "pendente_audio" por enquanto
  - Marca como executada com resultado
  - Retorna stats {executadas, erros, pular_opt_out, pular_limite}
- ( ) Função `verificar_email_abriu(lead_id)`:
  - Busca último email enviado do lead
  - Se abriu e clicou → agendar ação WA (D+1)
  - Se abriu sem clicar → agendar re-email (D+2)
  - Se não abriu → agendar re-email com assunto novo (D+3)
- ( ) Função `processar_evento_email(tracking_id, evento)`:
  - Chamado pelo webhook
  - Atualiza emails_enviados
  - Se evento='opened' + lead é WARM → agendar ação de check

```
[TESTE 2.2] Outreach engine:
  python -c "
  from crm.outreach_engine import importar_leads_para_outreach, criar_sequencia_lead
  from crm.database import init_pool
  init_pool()

  # Testar importação
  leads = importar_leads_para_outreach('SAO PAULO', 'SP', score_min=50, limite=5)
  print(f'Leads importados: {len(leads)}')
  for l in leads:
      print(f'  {l[\"nome_fantasia\"]} - score:{l[\"lead_score\"]} tier:{l[\"tier\"]}')

  # Testar criação de sequência (sem enviar)
  if leads:
      acoes = criar_sequencia_lead(leads[0]['id'], leads[0]['tier'], leads[0]['lead_score'])
      print(f'Ações criadas: {len(acoes)}')
      for a in acoes:
          print(f'  {a[\"acao\"]} em {a[\"agendado_para\"]}')
  "
```

### 2.3 — Cron job: executor de outreach
- ( ) Criar `crm/outreach_worker.py`:
  - Função `run_outreach_loop(intervalo_segundos=300)`:
    - Loop infinito: `executar_acoes_pendentes()` → sleep(intervalo)
    - Logging detalhado: [OUTREACH] prefixo
    - Graceful shutdown com signal handler
  - Modo standalone: `python -m crm.outreach_worker`
- ( ) Adicionar ao Dockerfile como processo separado (ou usar APScheduler dentro do app.py)

**[DECISÃO]**: Para MVP, usar `BackgroundTasks` do FastAPI com `asyncio.create_task` no startup do app, em vez de processo separado. Simplifica deploy. Migrar para worker dedicado na Fase 2+.

- ( ) Alternativa: Adicionar ao `app.py` startup:
  ```python
  @app.on_event("startup")
  async def start_outreach_worker():
      asyncio.create_task(outreach_loop())
  ```

```
[TESTE 2.3] Worker de outreach:
  # Criar 3 ações de teste agendadas para NOW():
  psql derekh_crm -c "
    INSERT INTO outreach_sequencia (lead_id, acao, tier, agendado_para) VALUES
    (1, 'enviar_email', 'warm', NOW()),
    (2, 'enviar_email', 'warm', NOW() + INTERVAL '1 hour'),
    (3, 'enviar_email', 'hot', NOW() - INTERVAL '5 minutes');
  "

  # Rodar worker uma vez:
  python -c "
  from crm.outreach_engine import executar_acoes_pendentes
  from crm.database import init_pool
  init_pool()
  stats = executar_acoes_pendentes()
  print(stats)
  "
  → Deve executar ação do lead 1 e 3 (agendado_para <= NOW())
  → Deve pular ação do lead 2 (futuro)
  → Verificar: emails_enviados tem 2 novos registros
  → Verificar: outreach_sequencia tem executado=True nos 2
```

### 2.4 — Rotas FastAPI de outreach
- ( ) `POST /outreach/importar` → importar leads (cidade, uf, score_min)
- ( ) `POST /outreach/iniciar/{lead_id}` → criar sequência para 1 lead
- ( ) `GET /outreach/pendentes` → listar ações pendentes (próximas 24h)
- ( ) `POST /outreach/cancelar/{lead_id}` → cancelar todas ações do lead
- ( ) `POST /outreach/opt-out/{lead_id}` → opt-out + cancelar
- ( ) `GET /outreach/dashboard` → renderizar template com stats + funil

### 2.5 — Template HTML: outreach_dashboard.html
- ( ) Stats de outreach (últimos 7 dias): emails enviados, abertos, clicados, respondidos
- ( ) Funil visual (barras coloridas como no JSX)
- ( ) Lista de ações pendentes (próximas 24h)
- ( ) Leads quentes (tier=hot) sem contato
- ( ) Botões: Importar leads, Pausar outreach, Forçar execução
- ( ) Indicador de warmup (X/max emails hoje)

```
[TESTE 2.5] Dashboard de outreach:
  # Subir server
  uvicorn crm.app:app --reload --port 8000
  # Acessar http://localhost:8000/outreach/dashboard
  → Página carrega sem erro
  → Stats mostram dados do banco
  → Botão "Importar leads" funciona (abre modal/form)
```

### 2.6 — Teste end-to-end Micro-Fase 2
```
[TESTE E2E 2] Fluxo completo de outreach:
  1. Importar 10 leads de São Paulo (score >= 50)
     POST /outreach/importar {"cidade": "SAO PAULO", "uf": "SP", "score_min": 50, "limite": 10}
  2. Verificar: outreach_sequencia tem ações criadas para cada lead
  3. Verificar: leads HOT têm ação imediata, WARM têm D+0 email
  4. Aguardar worker executar (ou forçar: POST /outreach/forcar-execucao)
  5. Verificar: emails_enviados tem registros
  6. Verificar: outreach_sequencia ações marcadas como executadas
  7. Simular abertura de email (GET /tracking/pixel/{tracking_id})
  8. Verificar: ação de follow-up criada automaticamente (D+1 ou D+2)
  9. Simular opt-out (POST /outreach/opt-out/{lead_id})
  10. Verificar: ações pendentes canceladas, lead.opt_out_email=True

  Guardrails a verificar:
  - Max emails/dia respeitado (não envia mais que 20)
  - Lead com opt_out NÃO recebe email
  - Lead sem email NÃO recebe ação de email
  - Lead com email_invalido NÃO recebe email
```

**[RISCO 2.6]** Se RESEND_API_KEY não estiver configurada, `enviar_email()` falha silenciosamente. Adicionar log de erro explícito e marcar ação como `resultado='erro'`.

---

## MICRO-FASE 3: WhatsApp Bot de Vendas (4-5 dias)

**Objetivo**: Bot que envia mensagens e áudios via Evolution API, recebe respostas, e usa Grok IA para conversar.

**Pré-requisito**: Micro-Fases 1 e 2 concluídas.

### 3.1 — Migration: tabela wa_conversas
- ( ) Criar tabela `wa_conversas`:
  ```
  id SERIAL PK, lead_id FK->leads,
  numero_envio TEXT NOT NULL,
  status TEXT DEFAULT 'ativo' (ativo|encerrado|handoff|opt_out),
  voz_usada TEXT,
  tom_usado TEXT,
  usou_audio BOOLEAN DEFAULT FALSE,
  msgs_enviadas INTEGER DEFAULT 0,
  msgs_recebidas INTEGER DEFAULT 0,
  intencao_detectada TEXT,
  handoff_at TIMESTAMPTZ,
  handoff_motivo TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
  ```
- ( ) Criar tabela `wa_mensagens`:
  ```
  id SERIAL PK, conversa_id FK->wa_conversas,
  direcao TEXT NOT NULL (enviada|recebida),
  tipo TEXT DEFAULT 'texto' (texto|audio|imagem),
  conteudo TEXT,
  intencao TEXT,
  grok_resposta BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- ( ) Índices:
  ```sql
  CREATE INDEX idx_wa_conversas_lead ON wa_conversas(lead_id);
  CREATE INDEX idx_wa_conversas_status ON wa_conversas(status);
  CREATE INDEX idx_wa_mensagens_conversa ON wa_mensagens(conversa_id);
  ```
- ( ) Configurações (na tabela `configuracoes`):
  ```sql
  INSERT INTO configuracoes (chave, valor) VALUES
    ('wa_sales_numero', ''),
    ('wa_evolution_url', ''),
    ('wa_evolution_key', ''),
    ('xai_api_key', ''),
    ('wa_sales_ativo', 'false')
  ON CONFLICT (chave) DO NOTHING;
  ```

```
[TESTE 3.1] Migration wa_conversas:
  psql derekh_crm < crm/migration_wa.sql
  \dt wa_* → 2 tabelas
  \d wa_conversas → colunas corretas
  \d wa_mensagens → colunas corretas
```

### 3.2 — database.py: queries de WhatsApp
- ( ) `criar_conversa_wa(lead_id, numero_envio, tom=None, voz=None)` → id
- ( ) `registrar_msg_wa(conversa_id, direcao, conteudo, tipo='texto', intencao=None, grok=False)` → id
- ( ) `listar_conversas_wa(status='ativo', limite=50)` → list[dict] com JOIN leads
- ( ) `obter_conversa_wa(conversa_id)` → dict com mensagens
- ( ) `obter_conversa_wa_por_lead(lead_id)` → dict (última conversa ativa)
- ( ) `atualizar_conversa_wa(conversa_id, **kwargs)` → bool
- ( ) `contar_msgs_wa_hoje()` → int (guardrail)
- ( ) `stats_wa(periodo_dias=7)` → dict (conversas, msgs, respondidos, handoffs)

```
[TESTE 3.2] Queries WA:
  python -c "
  from crm.database import init_pool, criar_conversa_wa, registrar_msg_wa
  init_pool()
  cid = criar_conversa_wa(1, '5511999999999', 'informal')
  print('Conversa:', cid)
  mid = registrar_msg_wa(cid, 'enviada', 'Oi! Teste')
  print('Mensagem:', mid)
  "
```

### 3.3 — wa_sales_bot.py: novo módulo
- ( ) Função `_formatar_numero_wa(telefone)` → formato Evolution API
- ( ) Função `enviar_mensagem_wa(lead_id, texto, tom='informal')`:
  - Busca lead + telefone
  - Verifica opt_out_wa
  - Cria conversa (ou usa existente)
  - Envia via Evolution API: `POST {EVOLUTION_URL}/message/sendText/{instance}`
  - Registra mensagem em wa_mensagens
  - Atualiza contadores da conversa
- ( ) Função `processar_resposta_wa(numero_remetente, mensagem)`:
  - Busca conversa ativa pelo número
  - Registra mensagem recebida
  - Detecta intenção básica (opt_out, interesse, dúvida, recusa)
  - Se opt_out → `opt_out_lead()` + encerrar conversa
  - Se interesse/dúvida → chamar `responder_com_ia()`
  - Se recusa → marcar e NÃO insistir
- ( ) Função `responder_com_ia(conversa_id, mensagem_lead)`:
  - Busca contexto: dados do lead, histórico da conversa (últimas 10 msgs)
  - Monta system prompt com: dados do restaurante, benefícios Derekh Food, objeções comuns
  - Chama Grok API: `POST https://api.x.ai/v1/chat/completions` (formato OpenAI)
  - Envia resposta via Evolution API
  - Registra msg_wa com `grok_resposta=True`
- ( ) Função `detectar_intencao(mensagem)` → string:
  - Palavras-chave simples primeiro (SAIR, NÃO QUERO, PARA → opt_out)
  - Se não match → chamar Grok com prompt de classificação
  - Retorna: interesse|duvida|recusa|opt_out|outro
- ( ) Função `avaliar_handoff(conversa_id)`:
  - Se lead pediu demo → handoff imediato
  - Se lead respondeu 3+ vezes com "interesse" → handoff
  - Se score >= 85 → handoff
  - Retorna (bool, motivo)

```
[TESTE 3.3] WA Sales Bot:
  # Teste com Evolution API real (precisa de número configurado)
  python -c "
  from crm.wa_sales_bot import enviar_mensagem_wa
  from crm.database import init_pool
  init_pool()
  result = enviar_mensagem_wa(LEAD_ID, 'Oi! Teste do bot de vendas.')
  print(result)
  "

  # Teste de detecção de intenção (sem API):
  python -c "
  from crm.wa_sales_bot import detectar_intencao
  print(detectar_intencao('quero sair'))           # → opt_out
  print(detectar_intencao('como funciona?'))        # → duvida
  print(detectar_intencao('me interessa'))          # → interesse
  print(detectar_intencao('não tenho interesse'))   # → recusa
  "

  # Teste de resposta IA (precisa XAI_API_KEY):
  python -c "
  from crm.wa_sales_bot import responder_com_ia
  from crm.database import init_pool
  init_pool()
  resposta = responder_com_ia(CONVERSA_ID, 'Quanto custa o plano de vocês?')
  print(resposta)
  "
```

### 3.4 — Rotas FastAPI de WhatsApp Sales
- ( ) `POST /wa-sales/enviar/{lead_id}` → enviar mensagem manual
- ( ) `POST /wa-sales/webhook` → webhook Evolution API (mensagem recebida)
- ( ) `GET /wa-sales/conversas` → renderizar lista de conversas ativas
- ( ) `GET /wa-sales/conversa/{conversa_id}` → renderizar chat com histórico
- ( ) `POST /wa-sales/handoff/{conversa_id}` → marcar handoff manual

### 3.5 — Template HTML: wa_conversas.html
- ( ) Lista de conversas ativas com: nome lead, última mensagem, intenção detectada, status
- ( ) Indicador visual: bot ativo (verde), handoff pendente (amarelo), encerrado (cinza)
- ( ) Contador de mensagens enviadas/recebidas hoje

### 3.6 — Integrar WA no outreach_engine
- ( ) Quando ação `enviar_wa` é executada → chamar `enviar_mensagem_wa()`
- ( ) Quando lead HOT é importado → criar ação WA imediata (se tem telefone)
- ( ) Quando email é aberto + clicou → agendar WA para D+1

```
[TESTE E2E 3] Fluxo completo WA:
  1. Importar lead HOT com telefone
  2. Verificar: outreach criou ação "enviar_wa" imediata
  3. Worker executa → mensagem enviada via Evolution API
  4. Simular resposta do lead (webhook Evolution)
  5. Verificar: bot respondeu com IA (Grok)
  6. Simular "quero ver demo"
  7. Verificar: handoff ativado, notificação criada
  8. Simular "SAIR"
  9. Verificar: opt_out_wa=True, conversa encerrada, ações canceladas

  Guardrails:
  - Lead com opt_out_wa NÃO recebe WA
  - Lead sem telefone → ação marcada como 'erro'
  - Máximo de mensagens/dia respeitado
```

---

## MICRO-FASE 4: Áudio Grok TTS (2-3 dias)

**Objetivo**: Gerar áudios personalizados com Grok TTS e enviar via WhatsApp.

**Pré-requisito**: Micro-Fase 3 concluída.

### 4.1 — Função de TTS no wa_sales_bot.py
- ( ) Função `gerar_audio_tts(texto, voz='ara')`:
  - Chama `POST https://api.x.ai/v1/audio/speech` com body:
    ```json
    {"model": "grok-3-fast-tts", "input": "texto", "voice": "ara"}
    ```
  - Salva áudio em arquivo temporário (.mp3)
  - Retorna path do arquivo
- ( ) Função `gerar_script_audio(lead)`:
  - Usa dados reais: nome do dono, nome do restaurante, rating, reviews
  - Monta script natural e personalizado (~30 segundos)
  - Retorna texto do script
- ( ) Função `enviar_audio_wa(lead_id, voz='ara')`:
  - Gera script personalizado
  - Gera áudio via TTS
  - Envia via Evolution API: `POST {EVOLUTION_URL}/message/sendMedia/{instance}`
  - Registra em wa_mensagens com `tipo='audio'`
  - Atualiza conversa: `usou_audio=True, voz_usada=voz`

### 4.2 — Constantes de voz
- ( ) Adicionar em models.py:
  ```python
  VOZES_TTS = ["ara", "eve", "rex", "sal", "leo"]
  VOZES_LABELS = {"ara": "Ara (calorosa)", "eve": "Eve (profissional)",
                  "rex": "Rex (enérgico)", "sal": "Sal (calma)", "leo": "Leo (confiante)"}
  TONS_CONVERSA = ["informal", "profissional", "direto"]
  ```

### 4.3 — Integrar áudio no outreach
- ( ) Quando ação `enviar_audio` é executada → chamar `enviar_audio_wa()`
- ( ) Guardrail de custo: verificar gasto TTS do dia (config `outreach_max_gasto_tts_dia`)
- ( ) Para leads HOT: áudio na primeira mensagem (se agente decide)
- ( ) Para leads WARM: áudio no follow-up (se email foi aberto)

```
[TESTE 4] Áudio TTS:
  # Teste geração de áudio (precisa XAI_API_KEY):
  python -c "
  from crm.wa_sales_bot import gerar_audio_tts
  path = gerar_audio_tts('Oi, tudo bem? Teste do Grok TTS.', 'ara')
  print('Áudio gerado:', path)
  # Ouvir o arquivo para verificar qualidade
  "

  # Teste script personalizado:
  python -c "
  from crm.wa_sales_bot import gerar_script_audio
  from crm.database import init_pool, obter_lead
  init_pool()
  lead = obter_lead(1)
  script = gerar_script_audio(lead)
  print('Script:', script)
  # Verificar: menciona nome do restaurante, rating, dados reais
  "

  # Teste envio completo:
  python -c "
  from crm.wa_sales_bot import enviar_audio_wa
  from crm.database import init_pool
  init_pool()
  result = enviar_audio_wa(LEAD_ID, voz='ara')
  print(result)
  # Verificar: WA recebeu áudio, wa_mensagens tem registro tipo='audio'
  "
```

---

## MICRO-FASE 5: Agente Autônomo (5-6 dias)

**Objetivo**: Cérebro que analisa resultados, roda A/B tests, e auto-otimiza as variáveis.

**Pré-requisito**: Micro-Fases 1-4 concluídas com dados reais acumulados (~1 semana).

### 5.1 — Migration: tabelas do agente
- ( ) Criar tabela `agente_experimentos`:
  ```
  id SERIAL PK,
  variavel TEXT NOT NULL (horario|tom|voz|template|audio_timing|followup_limit|warmup|handoff_stage|reativacao|segmento),
  variante_a TEXT NOT NULL,
  variante_b TEXT NOT NULL,
  metrica_alvo TEXT NOT NULL (open_rate|ctr|response_rate|demo_rate|close_rate),
  amostras_a INTEGER DEFAULT 0,
  sucessos_a INTEGER DEFAULT 0,
  amostras_b INTEGER DEFAULT 0,
  sucessos_b INTEGER DEFAULT 0,
  vencedor TEXT (a|b|NULL),
  confianca_pct FLOAT,
  decidido_at TIMESTAMPTZ,
  aplicado BOOLEAN DEFAULT FALSE,
  ativo BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- ( ) Criar tabela `agente_decisoes`:
  ```
  id SERIAL PK,
  tipo TEXT NOT NULL (ajuste_auto|recomendacao|handoff|relatorio),
  descricao TEXT NOT NULL,
  dados JSONB,
  aprovado BOOLEAN,
  aprovado_at TIMESTAMPTZ,
  executado BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- ( ) Criar tabela `agente_relatorios`:
  ```
  id SERIAL PK,
  periodo_inicio DATE NOT NULL,
  periodo_fim DATE NOT NULL,
  metricas JSONB NOT NULL,
  descobertas JSONB,
  recomendacoes JSONB,
  resumo_texto TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
  ```
- ( ) Índices:
  ```sql
  CREATE INDEX idx_agente_exp_variavel ON agente_experimentos(variavel) WHERE ativo = TRUE;
  CREATE INDEX idx_agente_decisoes_pendentes ON agente_decisoes(tipo) WHERE aprovado IS NULL;
  ```

```
[TESTE 5.1] Migration agente:
  psql derekh_crm < crm/migration_agente.sql
  \dt agente_* → 3 tabelas
```

### 5.2 — database.py: queries do agente
- ( ) `criar_experimento(variavel, variante_a, variante_b, metrica_alvo)` → id
- ( ) `registrar_resultado_experimento(exp_id, variante, sucesso)` → bool
- ( ) `obter_experimento_ativo(variavel)` → dict (o atual)
- ( ) `listar_experimentos(ativo=True)` → list[dict]
- ( ) `declarar_vencedor(exp_id, vencedor, confianca_pct)` → bool
- ( ) `criar_decisao(tipo, descricao, dados=None)` → id
- ( ) `listar_decisoes_pendentes()` → list[dict] (aprovado IS NULL)
- ( ) `aprovar_decisao(decisao_id)` → bool
- ( ) `rejeitar_decisao(decisao_id)` → bool
- ( ) `criar_relatorio(periodo_inicio, periodo_fim, metricas, descobertas, recomendacoes, resumo)` → id
- ( ) `obter_ultimo_relatorio()` → dict
- ( ) `metricas_outreach_periodo(inicio, fim)` → dict agregado

### 5.3 — agente_autonomo.py: cérebro
- ( ) Função `ciclo_diario()`:
  - Calcula métricas do dia anterior: open_rate, ctr, response_rate, demo_rate
  - Analisa cada variável controlada
  - Registra resultados nos experimentos ativos
  - Avalia se algum experimento tem vencedor (z-test de proporção, p < 0.05)
  - Gera recomendações (tipo='recomendacao' com aprovado=NULL)
  - Aplica ajustes automáticos pequenos (tipo='ajuste_auto' com aprovado=True)
  - Gera relatório do dia
- ( ) Função `multi_armed_bandit(variavel)`:
  - Epsilon-greedy: random() < epsilon → explorar, senão → exploitar
  - Epsilon decai: 0.20 → 0.10 → 0.05 (baseado em amostras totais)
  - Retorna variante escolhida
- ( ) Função `avaliar_experimento(exp_id)`:
  - z-test de proporção (scipy.stats.norm)
  - Se p < 0.05 e amostras >= 30 cada → declarar vencedor
  - Se amostras >= 100 sem vencedor → declarar empate, criar novo experimento
- ( ) Função `sugerir_estrategia(lead)`:
  - Para cada variável, usa multi_armed_bandit para escolher
  - Retorna dict: {horario, tom, voz, template, usar_audio, max_followups}
- ( ) Função `gerar_relatorio_diario()`:
  - Coleta métricas
  - Usa Grok API para gerar resumo em linguagem natural (opcional)
  - Retorna dict com métricas, descobertas, recomendações

### 5.4 — Constantes do agente
- ( ) Adicionar em models.py:
  ```python
  VARIAVEIS_AGENTE = ["horario", "tom", "voz", "template", "audio_timing",
                       "followup_limit", "warmup", "handoff_stage", "reativacao", "segmento"]
  METRICAS_AGENTE = ["open_rate", "ctr", "response_rate", "demo_rate", "close_rate"]
  TIPOS_DECISAO = ["ajuste_auto", "recomendacao", "handoff", "relatorio"]
  ```

### 5.5 — Cron job do agente
- ( ) Executar `ciclo_diario()` uma vez por dia às 06:00
- ( ) Implementar via APScheduler ou asyncio no startup do app

### 5.6 — Rotas FastAPI do agente
- ( ) `GET /agente/dashboard` → renderizar painel do agente
- ( ) `GET /agente/relatorio` → último relatório
- ( ) `GET /agente/experimentos` → lista de experimentos
- ( ) `POST /agente/aprovar/{decisao_id}` → aprovar decisão
- ( ) `POST /agente/rejeitar/{decisao_id}` → rejeitar decisão
- ( ) `POST /agente/forcar-ciclo` → executar ciclo diário agora

### 5.7 — Template HTML: agente_dashboard.html
- ( ) Métricas do dia (cards coloridos)
- ( ) Gráfico de evolução (Chart.js)
- ( ) Experimentos ativos (tabela com variantes A vs B)
- ( ) Decisões pendentes de aprovação (botões aprovar/rejeitar)
- ( ) Último relatório do agente (texto natural)

```
[TESTE E2E 5] Agente autônomo:
  # Precisa de dados reais acumulados (~50+ emails enviados)

  1. Executar ciclo diário manualmente:
     POST /agente/forcar-ciclo
  2. Verificar: agente_relatorios tem novo registro
  3. Verificar: métricas calculadas (open_rate, ctr)
  4. Verificar: experimentos criados (pelo menos 1)
  5. Verificar: decisões pendentes (pelo menos 1 recomendação)
  6. Aprovar uma recomendação:
     POST /agente/aprovar/{id}
  7. Verificar: configuração foi atualizada
  8. Acessar dashboard: GET /agente/dashboard
  9. Verificar: gráficos e métricas renderizam

  Guardrails:
  - Agente NÃO altera max_email_dia sem aprovação
  - Agente NÃO envia WA para leads opt_out
  - Agente respeita max_gasto_tts_dia
  - Decisões grandes (tipo='recomendacao') ficam pendentes
  - Ajustes pequenos (tipo='ajuste_auto') são aplicados automaticamente
```

---

## MICRO-FASE 6: Polish + Deploy (3-4 dias)

**Objetivo**: Integrar tudo, testar com leads reais, deploy no Fly.io.

**Pré-requisito**: Micro-Fases 1-5 concluídas.

### 6.1 — Integração final
- ( ) Sidebar do CRM: adicionar links para Outreach Dashboard, WA Conversas, Agente
- ( ) Ficha do lead: mostrar ações de outreach + conversas WA
- ( ) Dashboard principal: adicionar card com stats de outreach
- ( ) Scanner: após sync, auto-importar leads novos para outreach (se ativo)

### 6.2 — Requirements e Dockerfile
- ( ) Atualizar `requirements-crm.txt`:
  ```
  openai>=1.0.0        # Para Grok API (compatível OpenAI)
  apscheduler>=3.10.0  # Para cron jobs
  scipy>=1.11.0        # Para z-test do agente
  httpx>=0.25.0        # Para Evolution API
  ```
- ( ) Atualizar Dockerfile com novos módulos
- ( ) Atualizar fly.toml se necessário

### 6.3 — Variáveis de ambiente
- ( ) Documentar em `.env.example`:
  ```bash
  # Sales Autopilot (Fase 7)
  XAI_API_KEY=xai-...
  EVOLUTION_API_URL=https://...
  EVOLUTION_API_KEY=...
  WA_SALES_NUMERO=5511999...
  ```

### 6.4 — Testes com leads reais
- ( ) Enviar 10 emails de teste (leads reais, seu email como BCC)
- ( ) Verificar entregabilidade (inbox vs spam)
- ( ) Testar tracking (pixel + link)
- ( ) Enviar 3 WA de teste (seu número)
- ( ) Testar bot IA (conversar como lead)
- ( ) Testar áudio TTS (ouvir qualidade)
- ( ) Rodar ciclo do agente com dados reais
- ( ) Verificar relatório gerado

### 6.5 — Deploy
- ( ) Rodar migration no PostgreSQL do Fly.io
- ( ) Deploy: `fly deploy --app derekh-crm`
- ( ) Verificar health check
- ( ) Testar rotas em produção
- ( ) Configurar webhook Resend para URL de produção
- ( ) Configurar webhook Evolution API para URL de produção

```
[TESTE E2E FINAL] Teste completo em produção:
  1. Importar 50 leads reais de uma cidade
  2. Outreach engine cria sequências automaticamente
  3. Emails enviados com tracking
  4. Leads que abriram → recebem WA
  5. Bot IA conversa com leads que responderam
  6. Agente gera relatório do dia
  7. Dashboard mostra métricas reais
  8. Opt-out funciona em todos os canais
  9. Guardrails respeitados (limites de envio)
  10. Nenhum erro 500 no log
```

---

## CHECKLIST GERAL

### Micro-Fase 1: Email com Tracking
- (x) 1.1 — Migration (tabelas + índices + configs)
- (x) 1.2 — Refatorar scoring.py (pool + tier)
- (x) 1.3 — database.py (queries outreach — 16 funções)
- (x) 1.4 — email_service.py (tracking — pixel + link + unsub)
- (x) 1.5 — Rotas FastAPI (8 rotas: tracking + outreach API)
- ( ) 1.6 — Teste end-to-end (requer RESEND_API_KEY real)

### Micro-Fase 2: Sequência Automática
- (x) 2.1 — models.py (constantes outreach)
- (x) 2.2 — outreach_engine.py (importar + sequência + executor)
- (x) 2.3 — Worker/cron (asyncio no startup do app)
- (x) 2.4 — Rotas FastAPI (importar + iniciar + forcar + dashboard)
- (x) 2.5 — Template outreach_dashboard.html + sidebar
- (x) 2.6 — Teste end-to-end (dashboard 200, importar OK, iniciar OK)

### Micro-Fase 3: WhatsApp Bot
- (x) 3.1 — Migration (wa_conversas + wa_mensagens + configs)
- (x) 3.2 — database.py (8 queries WA + stats_wa)
- (x) 3.3 — wa_sales_bot.py (Evolution + Grok IA + detecção intenção + handoff)
- (x) 3.4 — Rotas FastAPI (enviar + áudio + webhook + conversas + detalhe)
- (x) 3.5 — Templates wa_conversas.html + wa_conversa_detalhe.html + sidebar
- (x) 3.6 — Integrar com outreach_engine (_executar_enviar_wa + _executar_enviar_audio)

### Micro-Fase 4: Áudio TTS (integrado na Fase 3)
- (x) 4.1 — TTS no wa_sales_bot.py (gerar_audio_tts + gerar_script_audio + enviar_audio_wa)
- (x) 4.2 — Constantes de voz (em models.py via plano)
- (x) 4.3 — Integrar com outreach (_executar_enviar_audio)

### Micro-Fase 5: Agente Autônomo
- (x) 5.1 — Migration (agente_experimentos + agente_decisoes + agente_relatorios)
- (x) 5.2 — database.py (12 queries agente + metricas_outreach_periodo)
- (x) 5.3 — agente_autonomo.py (MAB epsilon-greedy + z-test + ciclo_diario + sugerir_estrategia)
- (x) 5.4 — Constantes (VARIAVEIS_AGENTE etc em models.py via plano)
- (x) 5.5 — Cron job (asyncio _agente_loop às 06:00)
- (x) 5.6 — Rotas FastAPI (forcar-ciclo + aprovar/rejeitar + experimentos + relatorio)
- (x) 5.7 — Template agente_dashboard.html + sidebar

### Micro-Fase 6: Polish + Deploy
- (x) 6.1 — Integração UI (sidebar com Outreach + WA Vendas + Agente IA)
- ( ) 6.2 — Requirements + Dockerfile (httpx, scipy opcionais)
- ( ) 6.3 — Variáveis de ambiente (.env.example atualizado)
- ( ) 6.4 — Testes com leads reais (requer RESEND_API_KEY + Evolution API + XAI_API_KEY)
- ( ) 6.5 — Deploy Fly.io (migration + fly deploy)

---

## MÉTRICAS DE SUCESSO

| Fase | Métrica | Meta mínima |
|------|---------|-------------|
| 1 | Email entregue no inbox (não spam) | 90%+ |
| 1 | Pixel tracking funciona | 100% |
| 2 | Sequência executa automaticamente | 100% |
| 2 | Opt-out bloqueia envios | 100% |
| 3 | Bot responde em < 30s | 90%+ |
| 3 | Intenção detectada corretamente | 80%+ |
| 4 | Áudio TTS soa natural em PT-BR | Validação manual |
| 5 | Agente gera relatório sem erro | 100% |
| 5 | Guardrails nunca violados | 100% |
| 6 | Zero erros 500 em produção (24h) | 100% |

---

## ORDEM DE IMPLEMENTAÇÃO (arquivo por arquivo)

```
DIA 1-2:
  crm/migration_outreach.sql    ← tabelas + índices + configs
  crm/models.py                 ← constantes de tier + outreach
  crm/scoring.py                ← refatorar pool + calcular_tier()
  crm/database.py               ← queries de outreach + emails_enviados

DIA 3-4:
  crm/email_service.py          ← tracking (pixel + link + unsub)
  crm/app.py                    ← rotas de tracking + outreach

DIA 5-7:
  crm/outreach_engine.py        ← motor de sequência (NOVO)
  crm/templates/outreach_dashboard.html ← template (NOVO)

DIA 8-11:
  crm/migration_wa.sql          ← tabelas WA
  crm/wa_sales_bot.py           ← bot completo (NOVO)
  crm/templates/wa_conversas.html ← template (NOVO)

DIA 12-13:
  crm/wa_sales_bot.py           ← adicionar TTS

DIA 14-18:
  crm/migration_agente.sql      ← tabelas agente
  crm/agente_autonomo.py        ← cérebro (NOVO)
  crm/templates/agente_dashboard.html ← template (NOVO)

DIA 19-22:
  Integração final + testes + deploy
```
