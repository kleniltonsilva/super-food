-- ============================================================
-- MIGRATION: Sales Autopilot - Micro-Fase 1
-- Tabelas de outreach, emails_enviados, configs
-- Rodar: psql derekh_crm < crm/migration_outreach.sql
-- ============================================================

-- Extensão UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABELA: emails_enviados (tracking de cada email)
-- ============================================================
CREATE TABLE IF NOT EXISTS emails_enviados (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    template_id INTEGER REFERENCES email_templates(id) ON DELETE SET NULL,
    campanha_id INTEGER REFERENCES campanhas_email(id) ON DELETE SET NULL,
    assunto TEXT NOT NULL,
    tracking_id UUID NOT NULL DEFAULT gen_random_uuid(),
    pixel_url TEXT,
    horario_enviado TIMESTAMPTZ DEFAULT NOW(),
    aberto BOOLEAN DEFAULT FALSE,
    aberto_at TIMESTAMPTZ,
    aberturas_count INTEGER DEFAULT 0,
    clicou_site BOOLEAN DEFAULT FALSE,
    clicou_wa BOOLEAN DEFAULT FALSE,
    clicou_unsub BOOLEAN DEFAULT FALSE,
    bounced BOOLEAN DEFAULT FALSE,
    resend_message_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABELA: outreach_sequencia (ações automáticas agendadas)
-- ============================================================
CREATE TABLE IF NOT EXISTS outreach_sequencia (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    acao TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'cold',
    template_id INTEGER REFERENCES email_templates(id) ON DELETE SET NULL,
    agendado_para TIMESTAMPTZ NOT NULL,
    executado BOOLEAN DEFAULT FALSE,
    executado_at TIMESTAMPTZ,
    cancelado BOOLEAN DEFAULT FALSE,
    resultado TEXT,
    erro_detalhe TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COLUNAS NOVAS EM LEADS
-- ============================================================
ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_email BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_wa BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS opt_out_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'cold';

-- ============================================================
-- ÍNDICES
-- ============================================================

-- emails_enviados
CREATE INDEX IF NOT EXISTS idx_emails_enviados_lead ON emails_enviados(lead_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_tracking ON emails_enviados(tracking_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_resend ON emails_enviados(resend_message_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_campanha ON emails_enviados(campanha_id);

-- outreach_sequencia
CREATE INDEX IF NOT EXISTS idx_outreach_pendentes ON outreach_sequencia(agendado_para)
    WHERE executado = FALSE AND cancelado = FALSE;
CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach_sequencia(lead_id);

-- leads (novas colunas)
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
CREATE INDEX IF NOT EXISTS idx_leads_opt_out ON leads(opt_out_email, opt_out_wa);

-- ============================================================
-- CONFIGURAÇÕES DE OUTREACH (usa tabela existente)
-- ============================================================
INSERT INTO configuracoes (chave, valor) VALUES
    ('outreach_email_dominio', '@derekh.com.br'),
    ('outreach_max_email_dia', '20'),
    ('outreach_warmup_emails_dia', '20'),
    ('outreach_landing_url', 'https://derekh.com.br/food'),
    ('outreach_ativo', 'false')
ON CONFLICT (chave) DO NOTHING;

-- ============================================================
-- VERIFICAÇÃO
-- ============================================================
DO $$
BEGIN
    RAISE NOTICE '[OUTREACH] Migration concluída com sucesso.';
    RAISE NOTICE '[OUTREACH] Tabelas: emails_enviados, outreach_sequencia';
    RAISE NOTICE '[OUTREACH] Colunas: leads.opt_out_email, leads.opt_out_wa, leads.opt_out_at, leads.tier';
    RAISE NOTICE '[OUTREACH] Configs: outreach_* em configuracoes';
END $$;
