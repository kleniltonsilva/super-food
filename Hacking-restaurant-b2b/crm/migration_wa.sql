-- ============================================================
-- MIGRATION: Sales Autopilot - Micro-Fase 3 (WhatsApp Bot)
-- Rodar: psql derekh_crm < crm/migration_wa.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS wa_conversas (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    numero_envio TEXT NOT NULL,
    status TEXT DEFAULT 'ativo',
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
);

CREATE TABLE IF NOT EXISTS wa_mensagens (
    id SERIAL PRIMARY KEY,
    conversa_id INTEGER NOT NULL REFERENCES wa_conversas(id) ON DELETE CASCADE,
    direcao TEXT NOT NULL,
    tipo TEXT DEFAULT 'texto',
    conteudo TEXT,
    intencao TEXT,
    grok_resposta BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wa_conversas_lead ON wa_conversas(lead_id);
CREATE INDEX IF NOT EXISTS idx_wa_conversas_status ON wa_conversas(status);
CREATE INDEX IF NOT EXISTS idx_wa_mensagens_conversa ON wa_mensagens(conversa_id);

INSERT INTO configuracoes (chave, valor) VALUES
    ('wa_sales_numero', ''),
    ('wa_evolution_url', ''),
    ('wa_evolution_key', ''),
    ('xai_api_key', ''),
    ('wa_sales_ativo', 'false')
ON CONFLICT (chave) DO NOTHING;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_wa_conversas
        BEFORE UPDATE ON wa_conversas
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN RAISE NOTICE '[WA] Migration concluída.'; END $$;
