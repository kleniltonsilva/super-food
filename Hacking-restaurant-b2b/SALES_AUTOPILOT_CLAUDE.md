# SALES AUTOPILOT — Plano de Integração ao CRM (Fase 7+)

## Idioma
Sempre responda em **português brasileiro (pt-BR)**.

## Contexto
Este documento é a **Fase 7** do Hacking Restaurant BI / Derekh CRM. As Fases 1-6 já estão implementadas (schema PostgreSQL, dashboard, busca, ficha, pipeline, email Resend, WhatsApp links, scoring, deploy Fly.io). Agora precisamos adicionar o **Sales Autopilot** — um agente autônomo de vendas B2B que auto-otimiza suas estratégias.

## O que já existe (NÃO recriar)
- `crm/schema.sql` — PostgreSQL com leads, interações, email_templates, campanhas, sequências
- `crm/database.py` — 40+ queries (dashboard, busca, ficha, pipeline, email, campanhas)
- `crm/email_service.py` — Resend API já integrado (envio, campanhas batch, webhook)
- `crm/scoring.py` — Lead scoring 0-100, segmentação automática
- `crm/whatsapp_service.py` — Links wa.me personalizados com templates
- `crm/app.py` — FastAPI com 30+ rotas
- `sync_crm.py` — Sync SQLite→PostgreSQL
- Deploy em Fly.io (app derekh-crm, região gru)

## O que precisa ser CRIADO

### Fase 7A: Outreach Engine (Semanas 1-2)

#### Novas tabelas PostgreSQL (adicionar ao schema.sql)
```sql
-- Tracking de emails (estende o email_service existente)
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS pixel_url TEXT;
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS tracking_id UUID DEFAULT gen_random_uuid();
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS aberto_at TIMESTAMPTZ;
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS aberturas_count INTEGER DEFAULT 0;
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS clicou_site BOOLEAN DEFAULT FALSE;
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS clicou_wa BOOLEAN DEFAULT FALSE;
ALTER TABLE emails_enviados ADD COLUMN IF NOT EXISTS clicou_unsub BOOLEAN DEFAULT FALSE;

-- Sequência de outreach automática
CREATE TABLE IF NOT EXISTS outreach_sequencia (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    acao TEXT NOT NULL, -- enviar_email|reenviar_email|enviar_wa|enviar_audio|followup|ultima_msg|reativacao
    agendado_para TIMESTAMPTZ NOT NULL,
    executado BOOLEAN DEFAULT FALSE,
    executado_at TIMESTAMPTZ,
    cancelado BOOLEAN DEFAULT FALSE,
    resultado TEXT, -- enviado|aberto|clicou|respondeu|opt_out|bounce
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- WhatsApp conversas de vendas
CREATE TABLE IF NOT EXISTS wa_conversas (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    numero_envio TEXT NOT NULL,
    iniciado_por TEXT DEFAULT 'bot', -- bot|lead
    status TEXT DEFAULT 'ativo', -- ativo|encerrado|handoff
    voz_usada TEXT, -- ara|eve|rex|sal|leo
    tom_usado TEXT, -- informal|profissional|direto
    usou_audio BOOLEAN DEFAULT FALSE,
    msgs_enviadas INTEGER DEFAULT 0,
    msgs_recebidas INTEGER DEFAULT 0,
    intencao_detectada TEXT, -- interesse|duvida|recusa|outro
    handoff_at TIMESTAMPTZ,
    handoff_motivo TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agente: experimentos A/B
CREATE TABLE IF NOT EXISTS agente_experimentos (
    id SERIAL PRIMARY KEY,
    variavel TEXT NOT NULL, -- horario|tom|voz|template|audio_timing|followup_limit|warmup|handoff_stage|reativacao|segmento
    variante_a TEXT NOT NULL,
    variante_b TEXT NOT NULL,
    metrica_alvo TEXT NOT NULL, -- open_rate|ctr|response_rate|demo_rate|close_rate
    amostras_a INTEGER DEFAULT 0,
    sucessos_a INTEGER DEFAULT 0,
    amostras_b INTEGER DEFAULT 0,
    sucessos_b INTEGER DEFAULT 0,
    vencedor TEXT, -- a|b|null (indeterminado)
    confianca_pct FLOAT,
    decidido_at TIMESTAMPTZ,
    aplicado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agente: decisões e recomendações
CREATE TABLE IF NOT EXISTS agente_decisoes (
    id SERIAL PRIMARY KEY,
    tipo TEXT NOT NULL, -- ajuste_auto|recomendacao|handoff|relatorio
    descricao TEXT NOT NULL,
    dados JSONB,
    aprovado BOOLEAN,
    aprovado_at TIMESTAMPTZ,
    executado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Config do outreach
CREATE TABLE IF NOT EXISTS config_outreach (
    chave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    atualizado_at TIMESTAMPTZ DEFAULT NOW()
);

-- Valores iniciais
INSERT INTO config_outreach (chave, valor) VALUES
    ('email_provider', 'resend'),
    ('email_dominio', '@derekh.com.br'),
    ('wa_numero_vendas', ''),
    ('tts_provider', 'grok'),
    ('tts_preco_1m_chars', '4.20'),
    ('lgpd_base_legal', 'legitimo_interesse_b2b'),
    ('lgpd_optout_email', 'true'),
    ('lgpd_optout_wa', 'true'),
    ('agente_epsilon', '0.20'),
    ('agente_guardrail_max_email_dia', '100'),
    ('agente_guardrail_max_gasto_tts_dia', '5.00'),
    ('agente_warmup_emails_dia', '20'),
    ('landing_page_url', 'derekh.com.br/food')
ON CONFLICT (chave) DO NOTHING;
```

#### Novos arquivos Python

**`crm/outreach_engine.py`** — Motor de sequência automática
```
Responsabilidades:
- importar_leads_para_outreach(cidade, uf, filtros) — puxa leads do scoring existente
- calcular_tier(lead) — hot(>=80) | warm(50-79) | cool(30-49) | cold(<30)
- criar_sequencia(lead_id, tier) — agenda ações baseado no tier
- executar_acoes_pendentes() — cron job que roda a cada 5 min
- processar_email_webhook(tracking_id, evento) — open/click/bounce
- opt_out(lead_id, canal, motivo) — remove de todas as sequências

Lógica da sequência:
- HOT (score>=80): se tem WA → WA imediato, senão → email
- WARM (50-79): email D+0 → check D+1 → WA D+2 (se abriu) ou re-email D+3
- COOL (<50): email genérico, sem WA automático

Usar: scoring.py existente para calcular score
Usar: email_service.py existente para enviar emails (estender com pixel tracking)
```

**`crm/wa_sales_bot.py`** — Bot de vendas WhatsApp
```
Responsabilidades:
- enviar_mensagem_vendas(lead_id, texto, tom) — via Evolution API
- enviar_audio_vendas(lead_id, script) — gera TTS via Grok, envia via Evolution
- processar_resposta(lead_id, mensagem) — Grok IA analisa e responde
- detectar_intencao(mensagem) — interesse|duvida|recusa|opt_out
- decidir_handoff(conversa_id) — baseado na intenção + score
- gerar_script_audio(lead) — script personalizado com dados reais do restaurante

Integração com xAI:
- LLM: POST https://api.x.ai/v1/messages (model: grok-4-fast, compatível OpenAI)
- TTS: POST https://api.x.ai/v1/tts (vozes: ara, eve, rex, sal, leo)
- System prompt inclui: dados do restaurante, benefícios do Derekh Food, objeções comuns

Evolution API: já configurada no projeto, só precisa do novo número dedicado
```

**`crm/agente_autonomo.py`** — Cérebro auto-otimizador
```
Responsabilidades:
- ciclo_diario() — cron job 06:00, analisa resultados, gera recomendações
- multi_armed_bandit(variavel) — epsilon-greedy com decaimento
- criar_experimento(variavel, variante_a, variante_b, metrica)
- registrar_resultado(experimento_id, variante, sucesso)
- avaliar_experimento(experimento_id) — teste estatístico, declara vencedor
- gerar_relatorio_diario() — métricas + descobertas + recomendações
- aplicar_ajuste(decisao_id) — só se aprovado=True
- sugerir_estrategia(lead) — retorna {horario, tom, voz, audio, template}

10 variáveis controladas:
1. horario_envio — testa faixas, mede open_rate
2. tom_conversa — informal|profissional|direto, mede response_rate
3. audio_timing — 1a_msg|followup|nunca, mede response_rate
4. voz_tts — ara|eve|rex|sal|leo, mede response_rate
5. followup_limit — 2|3|4, mede ROI por tentativa
6. warmup_velocidade — sobe 20%/semana se bounce<4%
7. template_email — pool de templates, mede open_rate+ctr
8. handoff_stage — em qual stage passar pra humano
9. reativacao_d30 — reativar ou não, mede conversion_rate
10. segmentacao — priorizar segmentos de alto valor

Guardrails (NÃO pode):
- Enviar mais que config.max_email_dia
- Enviar WA a lead com opt_out
- Gastar mais que config.max_gasto_tts_dia em TTS
- Mudar estratégia grande sem aprovação (tipo='recomendacao', aprovado=NULL)
- Ignorar bounce_rate > 4%
```

#### Novas rotas FastAPI (adicionar ao app.py)

```python
# Outreach
POST /outreach/iniciar-sequencia/{lead_id}
GET  /outreach/pendentes  # próximas ações agendadas
POST /outreach/webhook/email  # Resend webhook (open/click/bounce)
POST /outreach/opt-out/{lead_id}

# WhatsApp Sales
POST /wa-sales/enviar/{lead_id}
POST /wa-sales/audio/{lead_id}
POST /wa-sales/webhook  # Evolution API incoming message
GET  /wa-sales/conversas

# Agente
GET  /agente/dashboard  # painel com métricas + recomendações
GET  /agente/relatorio-diario
POST /agente/aprovar/{decisao_id}
POST /agente/rejeitar/{decisao_id}
GET  /agente/experimentos
```

#### Novos templates HTML

```
crm/templates/outreach_dashboard.html  — Painel de vendas (funil, ações do dia, leads quentes)
crm/templates/agente_dashboard.html    — Painel do agente (relatório, recomendações, aprovar/rejeitar)
crm/templates/wa_conversas.html        — Lista de conversas WA com status
```

### Fase 7B: Auto-otimizador (Semanas 3-5)

Implementar `agente_autonomo.py` com:
- Cron job diário (pode usar APScheduler ou Celery simples)
- Multi-Armed Bandit epsilon-greedy
- Testes estatísticos (scipy.stats para proporção z-test)
- Geração de relatório via Grok (prompt com métricas → resumo em linguagem natural)
- Interface de aprovação no dashboard

### Fase 7C: Polish + Deploy (Semana 6)

- Testes end-to-end com leads reais
- Ajustar prompts do Grok (vendas + relatório)
- Deploy no Fly.io (mesmo app, novos workers)
- Documentar variáveis de ambiente novas

## Variáveis de Ambiente (adicionar ao .env)

```bash
# Sales Autopilot
XAI_API_KEY=xai-...              # Grok API (LLM + TTS)
RESEND_API_KEY=re_...            # Já existe, reusar
EVOLUTION_API_URL=...            # Já existe, reusar
EVOLUTION_API_KEY=...            # Já existe, reusar
WA_SALES_NUMERO=5511999...      # Número WA Business dedicado pra vendas
OUTREACH_LANDING_URL=https://derekh.com.br/food
```

## Custos reais verificados (Março 2026)

| Componente | Preço | Fonte |
|---|---|---|
| Grok 4.1 Fast (LLM) | $0.20/1M input, $0.50/1M output | docs.x.ai |
| Grok TTS (áudio) | $4.20/1M caracteres (beta) | docs.x.ai |
| xAI créditos grátis | $175/mês (data sharing program) | console.x.ai |
| Resend Free | 3.000 emails/mês, 100/dia | resend.com |
| Resend Pro | $20/mês, 50.000 emails | resend.com |
| Evolution API | Self-hosted (já tem) | — |
| Fly.io | Já pago (mesmo server) | — |

**Fase 1 (200 leads/mês): R$0/mês** — tudo coberto por free tiers e créditos xAI.
**Fase 2 (2.000 leads/mês): ~R$584/mês** — Resend Pro + excedente Grok + WA marketing.

## Arquitetura de deploy

```
LOCAL (seu computador):
├─ Hacking Restaurant BI (scraping — Playwright + SQLite)
└─ sync_crm.py → PostgreSQL no Fly.io

FLY.IO (mesmo app derekh-crm):
├─ FastAPI (app.py) — rotas web + API
├─ Worker outreach (executar_acoes_pendentes) — cron cada 5 min
├─ Worker agente (ciclo_diario) — cron 06:00
└─ PostgreSQL — banco compartilhado com CRM existente

Scraping NÃO vai pra nuvem (IPs de cloud são bloqueados por Maps/iFood/Cloudflare).
```

## Regras para o Claude Code

1. **NÃO recriar** o que já existe — estender os módulos atuais
2. **Reusar** email_service.py, scoring.py, database.py, whatsapp_service.py
3. **Manter** a estrutura de arquivos em `crm/`
4. **Manter** o padrão FastAPI + Jinja2 + Tailwind CSS (CDN)
5. **Adicionar** tabelas via ALTER TABLE / CREATE TABLE IF NOT EXISTS
6. **Testar** localmente antes de deploy: `uvicorn crm.app:app --reload`
7. **Ordem de implementação**: schema → outreach_engine → wa_sales_bot → rotas → templates → agente_autonomo
8. **Grok API** é compatível com formato OpenAI — usar `openai` SDK com `base_url="https://api.x.ai/v1"`
9. **Grok TTS** — endpoint: `POST https://api.x.ai/v1/tts`, body: `{model:"grok-tts-default", input:"texto", voice:"ara"}`
10. **Sempre em pt-BR** — todos os textos, templates, logs, relatórios

## Checkpoints Fase 7

- ( ) **7A.1**: Novas tabelas PostgreSQL (migration)
- ( ) **7A.2**: outreach_engine.py (sequência automática)
- ( ) **7A.3**: Estender email_service.py (pixel tracking + link tracking)
- ( ) **7A.4**: wa_sales_bot.py (Evolution API + Grok LLM + Grok TTS)
- ( ) **7A.5**: Novas rotas FastAPI
- ( ) **7A.6**: Templates HTML (outreach + agente + conversas)
- ( ) **7B.1**: agente_autonomo.py (Multi-Armed Bandit)
- ( ) **7B.2**: Cron jobs (outreach worker + agente diário)
- ( ) **7B.3**: Painel do agente (relatório + aprovar/rejeitar)
- ( ) **7C.1**: Testes com leads reais
- ( ) **7C.2**: Deploy Fly.io
- ( ) **7C.3**: Documentação final
