# Documentação Técnica — WhatsApp Dual-Number (Evolution API + Meta Cloud API)

> **Última atualização:** 22/03/2026
> **Autor:** Klenilton Silva / Claude AI
> **Projeto:** Derekh Food — Sales Autopilot CRM

---

## 1. VISÃO GERAL DA ARQUITETURA

O sistema utiliza **3 canais WhatsApp** com propósitos distintos:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEREKH FOOD — WHATSAPP                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐   ┌─────────────────────┐             │
│  │  EVOLUTION API #1   │   │  EVOLUTION API #2   │             │
│  │  derekh-vendas-1    │   │  derekh-vendas-2    │             │
│  │  +55 11 97176-5565  │   │  +55 45 99971-3063  │             │
│  │  INBOUND (site)     │   │  OUTBOUND (prospec.) │             │
│  └────────┬────────────┘   └────────┬────────────┘             │
│           │                         │                           │
│           └────────┬────────────────┘                           │
│                    ▼                                            │
│           ┌────────────────┐                                    │
│           │  derekh-crm    │                                    │
│           │  (FastAPI)     │                                    │
│           │  fly.dev       │                                    │
│           └────────┬───────┘                                    │
│                    │                                            │
│           ┌────────▼───────┐                                    │
│           │  META CLOUD API│                                    │
│           │  +1 555-900-   │  (TESTE — será descartado)        │
│           │  4563          │                                    │
│           └────────────────┘                                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. NÚMEROS E INSTÂNCIAS

### 2a. Número 1 — INBOUND (Site + Emails Rastreados)

| Campo | Valor |
|-------|-------|
| **Número** | +55 11 97176-5565 |
| **Operadora** | Chip Massa (Telein) — virtual BR |
| **Instância Evolution** | `derekh-vendas-1` |
| **Uso** | Recebe conversas do site Derekh Food, emails de marketing com link rastreado |
| **Quem inicia** | O LEAD (cliente) inicia a conversa |
| **Bot responde** | Sim — Grok IA (atendente virtual Derekh Food) |

### 2b. Número 2 — OUTBOUND (Prospecção Ativa)

| Campo | Valor |
|-------|-------|
| **Número** | +55 45 99971-3063 |
| **Operadora** | Chip Massa (Telein) — virtual BR |
| **Instância Evolution** | `derekh-vendas-2` |
| **Uso** | Prospecção ativa — contata leads que não responderam emails de gatilho |
| **Quem inicia** | O BOT (Derekh) inicia a conversa |
| **Bot responde** | Sim — Grok IA (vendedor Derekh Food) |

### 2c. Número Meta Cloud API (TESTE — DESCARTAR)

| Campo | Valor |
|-------|-------|
| **Número** | +1 555-900-4563 |
| **Phone Number ID** | `1037307436137511` |
| **Status** | Virtual Meta — limitações de envio (erro 131037) |
| **Destino** | Será descartado quando Evolution API estiver 100% operacional |

---

## 3. EVOLUTION API — INFRAESTRUTURA

| Campo | Valor |
|-------|-------|
| **URL** | `https://derekh-evolution.fly.dev` |
| **Versão** | 2.2.3 |
| **API Key Global** | `81d537f83e77ba61f4efb9c6f403bbe056c060065943995b8da8e22c8a7bd232` |
| **Manager UI** | `https://derekh-evolution.fly.dev/manager/` |
| **Host** | Fly.io — região GRU (São Paulo) |
| **VM** | shared-cpu-1x, 1024MB RAM |
| **Volume** | `vol_vz590ze7kgzjmgjv` montado em `/evolution/instances` |
| **Machine ID** | `2874551a1ee158` |
| **Integração** | WHATSAPP-BAILEYS |

### Problema conhecido: Autostop
A máquina Fly.io desliga automaticamente por "excess capacity" quando não há tráfego. Isso impede a geração de QR code e a manutenção da sessão WhatsApp.

**Solução necessária:**
```bash
# Desativar autostop (manter máquina sempre ligada)
~/.fly/bin/fly machine update 2874551a1ee158 --app derekh-evolution --autostop=off -y
```

### Instâncias Evolution API

| Instância | Número | Token | Status |
|-----------|--------|-------|--------|
| `derekh-vendas-1` | +55 11 97176-5565 | (gerado ao criar) | Criada, aguardando QR scan |
| `derekh-vendas-2` | +55 45 99971-3063 | (a criar) | Pendente |

---

## 4. META CLOUD API — CREDENCIAIS COMPLETAS

> Detalhes completos em `memory/meta-whatsapp.md`

| Campo | Valor |
|-------|-------|
| **Business ID** | `1428912548285807` |
| **App ID** | `874086172333541` |
| **App Secret** | `4e6feb59d750b4e3408de0f7b889d3fd` |
| **WABA ID** | `1486557139857851` |
| **Phone Number ID** | `1037307436137511` (+1 555-900-4563) |
| **Token** | Long-lived 60 dias (expira ~21/05/2026) |
| **Webhook URL** | `https://derekh-crm.fly.dev/wa-sales/webhook` |
| **Verify Token** | `derekh_wa_verify_2026` |

---

## 5. ROTEAMENTO INTELIGENTE DUAL-NUMBER

### Regra de Ouro: 1 Lead = 1 Número (SEMPRE)

```
Lead novo → hash(lead_id) % 2 → Número 1 ou 2 (FIXO para sempre)
Lead responde → buscar conversa existente → usar MESMO número
Lead já contactado por email com link → Número 1 (site/inbound)
Lead sem resposta a email → Número 2 (outbound/prospecção)
```

### Fluxo Inbound (Número 1)

```
1. Lead vê email marketing / site Derekh Food
2. Clica no botão "Fale Conosco" → abre WA +55 11 97176-5565
3. Lead envia mensagem
4. Evolution API recebe → webhook → derekh-crm
5. CRM cria lead_inbound + conversa
6. Grok IA responde como atendente virtual
7. Campo instancia_vinculada = "derekh-vendas-1" (permanente)
```

### Fluxo Outbound (Número 2)

```
1. Bot envia email de gatilho personalizado (Resend)
2. Email tem link rastreado (UTM + pixel de abertura)
3. Lead ABRE email mas NÃO responde (3+ dias)
4. Número 2 envia WA: "Vi que recebeu nosso email sobre..."
5. Evolution API envia → lead responde
6. CRM registra conversa com instancia_vinculada = "derekh-vendas-2"
7. Grok IA responde como vendedor
```

### Proteção Anti-Confusão

```python
# Antes de enviar QUALQUER mensagem:
def obter_instancia_lead(lead_id):
    """Retorna instância vinculada ao lead (ou atribui uma nova)."""
    conversa = obter_conversa_wa_por_lead(lead_id)
    if conversa and conversa.get("instancia_vinculada"):
        return conversa["instancia_vinculada"]
    # Novo lead: atribuir por hash
    instancia = "derekh-vendas-1" if lead_id % 2 == 0 else "derekh-vendas-2"
    return instancia
```

---

## 6. REGRAS DE SEGURANÇA (Anti-Ban WhatsApp)

### Warmup Gradual (por número)

| Semana | Msgs/dia | Tipo |
|--------|----------|------|
| 1 | 10-20 | Só texto, leads quentes |
| 2 | 30-50 | Texto + áudio |
| 3 | 50-100 | Volume normal |
| 4+ | 100-200 | Velocidade de cruzeiro |

### Regras Operacionais

- **Horário:** 9h-18h BRT (segunda a sexta), 9h-13h (sábado)
- **Delay entre mensagens:** 30-90 segundos (randomizado)
- **Pausa longa:** A cada 10-15 mensagens, pausa de 5-15 minutos
- **Mensagens personalizadas:** NUNCA enviar texto idêntico em massa
- **Dados do lead:** Usar nome, restaurante, cidade, rating (quando disponível)
- **Opt-out:** Respeitar IMEDIATAMENTE (keywords: sair, parar, cancelar, stop)
- **Limite diário combinado:** Soma dos dois números ≤ limites do warmup
- **Nunca enviar para o mesmo lead dos dois números**

### Failover

- Se um número cair (banido/bloqueado), o outro assume temporariamente
- Flag `numero_backup = True` na conversa para rastrear
- Notificar admin imediatamente via email

---

## 7. SECRETS FLY.IO

### derekh-crm (CRM + Bot Vendas)

```
WHATSAPP_PHONE_ID=1037307436137511          # Meta Cloud API (teste)
WHATSAPP_ACCESS_TOKEN=<token 60 dias>       # Meta (expira ~21/05/2026)
WHATSAPP_VERIFY_TOKEN=derekh_wa_verify_2026 # Webhook Meta
WHATSAPP_WEBHOOK_SECRET=<pendente>          # HMAC validation (não configurado)
XAI_API_KEY=xai-Uw90Gqm4Ug4Zd2...         # Grok LLM + TTS
RESEND_API_KEY=<configurar>                 # Email marketing
EVOLUTION_API_URL=https://derekh-evolution.fly.dev
EVOLUTION_API_KEY=81d537f83e77ba61f4efb9c6f403bbe056c060065943995b8da8e22c8a7bd232
```

### derekh-evolution (Evolution API)

```
AUTHENTICATION_API_KEY=81d537f83e77ba61f4efb9c6f403bbe056c060065943995b8da8e22c8a7bd232
# (outras env vars configuradas no fly.toml da instância Evolution)
```

---

## 8. ENDPOINTS CRM (wa_sales_bot.py)

### Envio

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/wa-sales/enviar/{lead_id}` | Envia texto WA (manual) |
| POST | `/wa-sales/audio/{lead_id}` | Envia áudio TTS personalizado |

### Webhook

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/wa-sales/webhook` | Verificação Meta (challenge) |
| POST | `/wa-sales/webhook` | Recebe mensagens Meta Cloud API |

### Conversas

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/wa-sales/conversas` | Lista conversas WA |
| GET | `/wa-sales/conversa/{id}` | Detalhe conversa com histórico |

### Outreach

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/outreach/importar` | Importa leads para outreach |
| POST | `/api/outreach/iniciar/{lead_id}` | Cria sequência para 1 lead |
| POST | `/api/outreach/forcar-execucao` | Força worker de outreach |
| GET | `/api/outreach/stats` | Stats de outreach (7 dias) |
| GET | `/api/outreach/pendentes` | Ações pendentes |

---

## 9. CÓDIGO — COMPONENTES PRINCIPAIS

### wa_sales_bot.py (Bot de Vendas WhatsApp)

```
Funções de envio:
- enviar_mensagem_wa(lead_id, texto, tom)     → Meta Cloud API
- enviar_audio_wa(lead_id, voz)               → Grok TTS + Meta upload
- _enviar_direto(numero, texto)               → Envio sem lead_id

Funções de recebimento:
- processar_resposta_wa(numero, mensagem)      → Processa msg recebida
- _responder_inbound(conversa_id, mensagem)    → IA para contato novo
- responder_com_ia(conversa_id, mensagem)      → IA para lead existente

Detecção:
- detectar_intencao(mensagem)                  → opt_out|recusa|interesse|duvida|outro
- avaliar_handoff(conversa_id)                 → Quando escalar para humano

Helpers:
- _formatar_numero_wa(telefone)                → Formato internacional
- verificar_webhook_meta(body, signature)      → HMAC-SHA256
```

### whatsapp_service.py (Links wa.me)

```
- gerar_link_whatsapp(lead_id, template_key)   → Link wa.me personalizado
- listar_templates_para_lead(lead_id)          → Templates disponíveis
- listar_templates_whatsapp()                  → Todos os templates
```

### outreach_engine.py (Motor de Outreach)

```
- importar_leads_para_outreach(cidade, uf)     → Importa leads + cria sequências
- criar_sequencia_lead(lead_id, tier, score)   → Sequência por tier (hot/warm/cold)
- executar_acoes_pendentes()                   → Worker (a cada 5 min)
```

### email_service.py (Email Marketing)

```
- enviar_email(lead_id, template_id)           → Email individual (Resend)
- enviar_campanha(campanha_id, filtros)        → Batch com tracking
- processar_webhook_resend(payload)            → Open/click/bounce
```

---

## 10. GROK IA (xAI)

| Campo | Valor |
|-------|-------|
| **Modelo chat** | `grok-3-fast` |
| **Modelo TTS** | `grok-3-fast-tts` |
| **Voz padrão** | `ara` |
| **API URL** | `https://api.x.ai/v1/chat/completions` |
| **Max tokens** | 250-300 |
| **Temperature** | 0.7 |

### Prompts do Bot

**Vendedor (outbound — leads existentes):**
- Tom informal, breve (max 3 parágrafos)
- Usa dados reais: nome restaurante, rating Google, nº avaliações
- Benefícios: delivery sem comissão, IA 24h, setup 48h, plano R$50/mês

**Atendente (inbound — contato novo do site):**
- Tom caloroso e profissional
- Entende necessidade do lead
- Coleta: nome restaurante, cidade, tipo de comida
- Emojis com moderação (1-2 por mensagem)

---

## 11. BANCO DE DADOS (PostgreSQL — derekh-crm)

### Tabelas WhatsApp

```sql
-- Conversas WhatsApp
wa_conversas: id, lead_id, numero_envio, tom, status, intencao_detectada,
              usou_audio, voz_usada, msgs_enviadas, msgs_recebidas,
              handoff_motivo, created_at, updated_at

-- Mensagens WhatsApp
wa_mensagens: id, conversa_id, direcao (enviada/recebida), conteudo,
              tipo (texto/audio), intencao, grok_gerado, created_at

-- Leads (campos relevantes WA)
leads: id, cnpj, nome_fantasia, telefone1, telefone_proprietario,
       status_pipeline, segmento, tier, lead_score,
       opt_out_wa, opt_out_email, instancia_vinculada
```

---

## 12. TAREFAS PENDENTES

### Imediatas
- [ ] Desativar autostop no Fly.io Evolution API (`--autostop=off`)
- [ ] Conectar +55 11 97176-5565 na instância `derekh-vendas-1` (QR code via Manager UI)
- [ ] Criar instância `derekh-vendas-2` para +55 45 99971-3063
- [ ] Conectar +55 45 99971-3063 na instância `derekh-vendas-2`

### Backend (Migração para Evolution API)
- [ ] Criar `crm/evolution_service.py` — wrapper para Evolution API REST
  - `enviar_texto(instancia, numero, texto)`
  - `enviar_audio(instancia, numero, audio_base64)`
  - `obter_status_instancia(instancia)`
  - `verificar_numero_whatsapp(instancia, numero)`
- [ ] Modificar `wa_sales_bot.py` para usar Evolution API em vez de Meta Cloud API
- [ ] Adicionar campo `instancia_vinculada` na tabela `wa_conversas`
- [ ] Implementar roteamento inteligente (1 lead = 1 número)
- [ ] Configurar webhook Evolution → derekh-crm (receber mensagens)

### Segurança
- [ ] Implementar warmup gradual (limites diários por instância)
- [ ] Implementar delays humanizados (30-90s entre mensagens)
- [ ] Implementar horário comercial (9h-18h BRT)
- [ ] Monitoramento de ban/bloqueio com alerta

### Meta Cloud API (Futuro)
- [ ] Comprar novo chip Massa para Meta Cloud API (verificação SMS)
- [ ] Registrar número na WABA (Phone Number ID)
- [ ] Renovar token 60 dias antes de 21/05/2026
- [ ] Ativar token permanente (DerekhBot — 1 passo na UI do Facebook)

---

## 13. ESTRATÉGIA DE COMUNICAÇÃO COMPLETA

```
                    ┌─────────────────┐
                    │   LEAD NOVO     │
                    │   (do scanner)  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  SCORING 0-100  │
                    │  Tier: hot/warm │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐  ┌────────────┐  ┌────────────┐
     │ EMAIL #1   │  │ EMAIL #2   │  │ EMAIL #3   │
     │ Apresenta  │  │ Case study │  │ Oferta     │
     │ (dia 0)    │  │ (dia 3)    │  │ (dia 7)    │
     └──────┬─────┘  └──────┬─────┘  └──────┬─────┘
            │               │               │
      ┌─────▼─────┐  ┌─────▼─────┐  ┌─────▼─────┐
      │ Abriu?    │  │ Abriu?    │  │ Abriu?    │
      │ Clicou?   │  │ Clicou?   │  │ Clicou?   │
      └─────┬─────┘  └─────┬─────┘  └─────┬─────┘
            │               │               │
            │  SIM: Número 1 responde       │
            │  (lead veio pelo site)        │
            │                               │
            │  NÃO respondeu nenhum email:  │
            └───────────┬───────────────────┘
                        │
               ┌────────▼────────┐
               │  NÚMERO 2 ENVIA │
               │  WA proativo    │
               │  (dia 10)       │
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │  Respondeu?     │
               │  SIM → Grok IA │
               │  NÃO → Desiste │
               └─────────────────┘
```

---

## 14. REFERÊNCIAS

- **Evolution API Docs:** https://doc.evolution-api.com
- **Meta WhatsApp Cloud API:** https://developers.facebook.com/docs/whatsapp/cloud-api
- **xAI/Grok API:** https://docs.x.ai
- **Resend API:** https://resend.com/docs
- **Credenciais Meta completas:** `memory/meta-whatsapp.md`
