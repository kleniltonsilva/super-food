-- ============================================================
-- MIGRATION: Sales Autopilot - Micro-Fase 5 (Agente Autônomo)
-- Rodar: psql derekh_crm < crm/migration_agente.sql
-- ============================================================

CREATE TABLE IF NOT EXISTS agente_experimentos (
    id SERIAL PRIMARY KEY,
    variavel TEXT NOT NULL,
    variante_a TEXT NOT NULL,
    variante_b TEXT NOT NULL,
    metrica_alvo TEXT NOT NULL,
    amostras_a INTEGER DEFAULT 0,
    sucessos_a INTEGER DEFAULT 0,
    amostras_b INTEGER DEFAULT 0,
    sucessos_b INTEGER DEFAULT 0,
    vencedor TEXT,
    confianca_pct FLOAT,
    decidido_at TIMESTAMPTZ,
    aplicado BOOLEAN DEFAULT FALSE,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agente_decisoes (
    id SERIAL PRIMARY KEY,
    tipo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    dados JSONB,
    aprovado BOOLEAN,
    aprovado_at TIMESTAMPTZ,
    executado BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agente_relatorios (
    id SERIAL PRIMARY KEY,
    periodo_inicio DATE NOT NULL,
    periodo_fim DATE NOT NULL,
    metricas JSONB NOT NULL,
    descobertas JSONB,
    recomendacoes JSONB,
    resumo_texto TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agente_exp_variavel ON agente_experimentos(variavel) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_agente_decisoes_pendentes ON agente_decisoes(tipo) WHERE aprovado IS NULL;

DO $$ BEGIN RAISE NOTICE '[AGENTE] Migration concluída.'; END $$;
