-- ============================================================
-- Derekh CRM - Schema PostgreSQL CONSOLIDADO
-- Database: derekh_crm (fly.io PostgreSQL)
-- Inclui: base + outreach + whatsapp + agente + scanner
-- Totalmente idempotente (IF NOT EXISTS / IF EXISTS)
-- ============================================================

-- Extensão para UUID
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- LEADS (espelho de cnpjs_receita + campos CRM + Maps)
-- ============================================================
CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    cnpj VARCHAR(14) NOT NULL UNIQUE,

    -- Dados Receita Federal (Estabelecimentos)
    razao_social TEXT,
    nome_fantasia TEXT,
    tipo_logradouro TEXT,
    logradouro TEXT,
    numero TEXT,
    complemento TEXT,
    bairro TEXT,
    cidade TEXT,
    uf VARCHAR(2),
    cep VARCHAR(8),
    telefone1 TEXT,
    telefone2 TEXT,
    email TEXT,
    cnae_principal VARCHAR(7),
    data_abertura TEXT,
    situacao_cadastral VARCHAR(10),

    -- Dados RF complementares (Empresas + Simples + Sócios)
    tipo_empresa TEXT,
    tipo_negocio TEXT,
    capital_social REAL,
    porte TEXT,
    natureza_juridica TEXT,
    simples VARCHAR(1),
    mei VARCHAR(1),
    data_opcao_simples TEXT,
    socios_json JSONB,

    -- Contato extra (cnpj.biz - opcional)
    telefone_proprietario TEXT,
    email_proprietario TEXT,

    -- Delivery
    tem_ifood SMALLINT DEFAULT 0,
    nome_ifood TEXT,
    url_ifood TEXT,
    ifood_checked SMALLINT DEFAULT 0,
    tem_rappi SMALLINT DEFAULT 0,
    nome_rappi TEXT,
    url_rappi TEXT,
    rappi_checked SMALLINT DEFAULT 0,
    tem_99food SMALLINT DEFAULT 0,
    nome_99food TEXT,
    url_99food TEXT,
    food99_checked SMALLINT DEFAULT 0,

    -- Dados Google Maps (desnormalizados no sync)
    rating REAL,
    total_reviews INTEGER,
    website TEXT,
    google_maps_url TEXT,
    categoria TEXT,
    nome_maps TEXT,
    endereco_maps TEXT,
    telefone_maps TEXT,
    maps_checked SMALLINT DEFAULT 0,
    matched SMALLINT DEFAULT 0,
    score_match REAL,
    detalhado SMALLINT DEFAULT 0,

    -- Controle de rede
    multi_restaurante SMALLINT DEFAULT 0,

    -- CRM
    lead_score INTEGER DEFAULT 0,
    segmento TEXT DEFAULT 'novo',
    status_pipeline TEXT DEFAULT 'novo',
    motivo_perda TEXT,
    notas TEXT,
    data_ultimo_contato TIMESTAMP,
    data_proximo_contato DATE,
    email_invalido SMALLINT DEFAULT 0,

    -- Outreach
    opt_out_email BOOLEAN DEFAULT FALSE,
    opt_out_wa BOOLEAN DEFAULT FALSE,
    opt_out_at TIMESTAMPTZ,
    tier TEXT DEFAULT 'cold',
    wa_outreach_manual_at TIMESTAMPTZ,
    lead_falso BOOLEAN DEFAULT FALSE,

    -- Controle
    synced_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- INTERAÇÕES
-- ============================================================
CREATE TABLE IF NOT EXISTS interacoes (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,
    canal TEXT,
    conteudo TEXT,
    resultado TEXT,
    email_message_id TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- EMAIL TEMPLATES
-- ============================================================
CREATE TABLE IF NOT EXISTS email_templates (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    assunto TEXT NOT NULL,
    corpo_html TEXT NOT NULL,
    segmento_alvo TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- CAMPANHAS DE EMAIL
-- ============================================================
CREATE TABLE IF NOT EXISTS campanhas_email (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    template_id INTEGER REFERENCES email_templates(id) ON DELETE SET NULL,
    filtros_json JSONB,
    total_enviados INTEGER DEFAULT 0,
    total_abertos INTEGER DEFAULT 0,
    total_clicados INTEGER DEFAULT 0,
    total_bounced INTEGER DEFAULT 0,
    status TEXT DEFAULT 'rascunho',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- SEQUÊNCIAS DE EMAIL
-- ============================================================
CREATE TABLE IF NOT EXISTS sequencias_email (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sequencia_etapas (
    id SERIAL PRIMARY KEY,
    sequencia_id INTEGER NOT NULL REFERENCES sequencias_email(id) ON DELETE CASCADE,
    ordem INTEGER NOT NULL,
    template_id INTEGER NOT NULL REFERENCES email_templates(id) ON DELETE CASCADE,
    dias_espera INTEGER NOT NULL DEFAULT 1,
    condicao TEXT DEFAULT 'sempre',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS lead_sequencia (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    sequencia_id INTEGER NOT NULL REFERENCES sequencias_email(id) ON DELETE CASCADE,
    etapa_atual INTEGER DEFAULT 1,
    status TEXT DEFAULT 'ativo',
    proximo_envio TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(lead_id, sequencia_id)
);

-- ============================================================
-- CONFIGURAÇÕES DO SISTEMA
-- ============================================================
CREATE TABLE IF NOT EXISTS configuracoes (
    chave VARCHAR(100) PRIMARY KEY,
    valor TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- EMAILS ENVIADOS (tracking individual — Outreach)
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
-- OUTREACH SEQUÊNCIA (ações automáticas agendadas)
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
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    proximo_retry TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- WHATSAPP CONVERSAS E MENSAGENS
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

-- ============================================================
-- AGENTE AUTÔNOMO
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

-- ============================================================
-- iFOOD ENRIQUECIDO — dados extraídos do card de busca
-- ============================================================
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_rating REAL;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_reviews INTEGER;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_preco TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_categorias TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_tempo_entrega TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_aberto SMALLINT DEFAULT 1;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ifood_checked_at TIMESTAMPTZ;

-- Índice para filtros iFood
CREATE INDEX IF NOT EXISTS idx_leads_ifood_rating ON leads(ifood_rating DESC) WHERE ifood_rating IS NOT NULL;

-- ============================================================
-- CONTACT VALIDATOR — novas colunas em leads
-- ============================================================
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_tipo TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS email_validado BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS wa_verificado BOOLEAN DEFAULT FALSE;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS wa_existe BOOLEAN;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS canal_primario TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS canal_secundario TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS contato_validado_at TIMESTAMPTZ;

-- ============================================================
-- PATTERN LIBRARY — padrões vencedores + mensagens geradas
-- ============================================================
CREATE TABLE IF NOT EXISTS padroes_vencedores (
    id SERIAL PRIMARY KEY,
    tipo TEXT NOT NULL,           -- assunto, abertura, cta, corpo
    conteudo TEXT NOT NULL,
    segmento_alvo TEXT,
    tier_alvo TEXT,
    usos INTEGER DEFAULT 0,
    aberturas INTEGER DEFAULT 0,
    cliques INTEGER DEFAULT 0,
    respostas INTEGER DEFAULT 0,
    score_eficacia FLOAT DEFAULT 0.5,
    ativo BOOLEAN DEFAULT TRUE,
    extraido_de TEXT,             -- campanha/email que originou o padrão
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS mensagens_geradas (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    padroes_usados JSONB,         -- [{"padrao_id": 1, "tipo": "assunto"}, ...]
    assunto TEXT,
    corpo TEXT,
    canal TEXT DEFAULT 'email',
    resultado TEXT,               -- enviado, aberto, clicou, respondeu
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices Pattern Library
CREATE INDEX IF NOT EXISTS idx_padroes_tipo ON padroes_vencedores(tipo) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_padroes_score ON padroes_vencedores(score_eficacia DESC) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_msgs_geradas_lead ON mensagens_geradas(lead_id);

-- ============================================================
-- SCANNER (scan jobs + logs)
-- ============================================================
CREATE TABLE IF NOT EXISTS scan_jobs (
    id SERIAL PRIMARY KEY,
    cidades JSONB,
    etapas JSONB,
    headless BOOLEAN DEFAULT TRUE,
    status TEXT DEFAULT 'pendente',
    cidade_atual TEXT,
    etapa_atual TEXT,
    total_leads INTEGER DEFAULT 0,
    processados INTEGER DEFAULT 0,
    encontrados INTEGER DEFAULT 0,
    erros INTEGER DEFAULT 0,
    progresso JSONB,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scan_logs (
    id SERIAL PRIMARY KEY,
    scan_job_id INTEGER NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    level TEXT DEFAULT 'info',
    message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ÍNDICES
-- ============================================================

-- Leads
CREATE INDEX IF NOT EXISTS idx_leads_cidade_uf ON leads(cidade, uf);
CREATE INDEX IF NOT EXISTS idx_leads_lead_score ON leads(lead_score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_segmento ON leads(segmento);
CREATE INDEX IF NOT EXISTS idx_leads_status_pipeline ON leads(status_pipeline);
CREATE INDEX IF NOT EXISTS idx_leads_proximo_contato ON leads(data_proximo_contato);
CREATE INDEX IF NOT EXISTS idx_leads_synced_at ON leads(synced_at);
CREATE INDEX IF NOT EXISTS idx_leads_uf ON leads(uf);
CREATE INDEX IF NOT EXISTS idx_leads_tier ON leads(tier);
CREATE INDEX IF NOT EXISTS idx_leads_opt_out ON leads(opt_out_email, opt_out_wa);

-- Interações
CREATE INDEX IF NOT EXISTS idx_interacoes_lead_id ON interacoes(lead_id);
CREATE INDEX IF NOT EXISTS idx_interacoes_created ON interacoes(created_at DESC);

-- Campanhas
CREATE INDEX IF NOT EXISTS idx_campanhas_status ON campanhas_email(status);

-- Sequências
CREATE INDEX IF NOT EXISTS idx_lead_sequencia_proximo ON lead_sequencia(proximo_envio)
    WHERE status = 'ativo';
CREATE INDEX IF NOT EXISTS idx_sequencia_etapas_seq ON sequencia_etapas(sequencia_id, ordem);

-- Emails enviados
CREATE INDEX IF NOT EXISTS idx_emails_enviados_lead ON emails_enviados(lead_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_tracking ON emails_enviados(tracking_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_resend ON emails_enviados(resend_message_id);
CREATE INDEX IF NOT EXISTS idx_emails_enviados_campanha ON emails_enviados(campanha_id);

-- Outreach
CREATE INDEX IF NOT EXISTS idx_outreach_pendentes ON outreach_sequencia(agendado_para)
    WHERE executado = FALSE AND cancelado = FALSE;
CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach_sequencia(lead_id);

-- WhatsApp
CREATE INDEX IF NOT EXISTS idx_wa_conversas_lead ON wa_conversas(lead_id);
CREATE INDEX IF NOT EXISTS idx_wa_conversas_status ON wa_conversas(status);
CREATE INDEX IF NOT EXISTS idx_wa_mensagens_conversa ON wa_mensagens(conversa_id);

-- Agente
CREATE INDEX IF NOT EXISTS idx_agente_exp_variavel ON agente_experimentos(variavel) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_agente_decisoes_pendentes ON agente_decisoes(tipo) WHERE aprovado IS NULL;

-- Scanner
CREATE INDEX IF NOT EXISTS idx_scan_logs_job ON scan_logs(scan_job_id);

-- ============================================================
-- TRIGGER: updated_at automático
-- ============================================================
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_leads
        BEFORE UPDATE ON leads
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_campanhas
        BEFORE UPDATE ON campanhas_email
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_templates
        BEFORE UPDATE ON email_templates
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_wa_conversas
        BEFORE UPDATE ON wa_conversas
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- OUTREACH REGRAS (sequências automáticas configuráveis)
-- ============================================================
CREATE TABLE IF NOT EXISTS outreach_regras (
    id SERIAL PRIMARY KEY,
    nome TEXT NOT NULL,
    prioridade INTEGER DEFAULT 0,
    condicao JSONB NOT NULL DEFAULT '{}',
    acoes JSONB,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outreach_regras_ativo ON outreach_regras(prioridade DESC) WHERE ativo = TRUE;

-- Seed regras padrão (idempotente)
INSERT INTO outreach_regras (nome, prioridade, condicao, acoes) VALUES
    ('iFood Leads — Email + WA', 10,
     '{"tem_ifood": true}',
     '[{"tipo":"enviar_email","delay_dias":0},{"tipo":"reenviar_email","delay_dias":1,"condicao":"nao_abriu"},{"tipo":"enviar_wa","delay_dias":3,"condicao":"nao_abriu"}]'
    ),
    ('Sem Delivery — Urgente', 5,
     '{"sem_delivery": true}',
     '[{"tipo":"enviar_email","delay_dias":0},{"tipo":"reenviar_email","delay_dias":2,"condicao":"nao_abriu"},{"tipo":"enviar_wa","delay_dias":3,"condicao":"nao_abriu"}]'
    ),
    ('Default — Tier', 0,
     '{}',
     null
    )
ON CONFLICT DO NOTHING;

DO $$ BEGIN
    CREATE TRIGGER set_updated_at_outreach_regras
        BEFORE UPDATE ON outreach_regras
        FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================
-- CONFIGURAÇÕES DEFAULT
-- ============================================================
INSERT INTO configuracoes (chave, valor) VALUES
    ('outreach_email_dominio', '@derekhfood.com.br'),
    ('outreach_max_email_dia', '20'),
    ('outreach_warmup_emails_dia', '20'),
    ('outreach_landing_url', 'https://derekhfood.com.br'),
    ('outreach_ativo', 'false'),
    ('wa_sales_numero', ''),
    ('wa_evolution_url', ''),
    ('wa_evolution_key', ''),
    ('wa_evolution_instance', 'derekh_sales'),
    ('xai_api_key', ''),
    ('wa_sales_ativo', 'false'),
    -- Toggles Áudio STT/TTS
    ('audio_stt_ativo', 'true'),
    ('audio_tts_autonomo', 'true'),
    ('audio_voz', 'ara'),
    -- Toggles Retry
    ('retry_ativo', 'true'),
    ('retry_max', '3'),
    -- Toggles Cooling Period
    ('cooling_ativo', 'true'),
    ('cooling_dias', '7'),
    ('cooling_max_sem_resposta', '3'),
    -- Descoberta automática de regras
    ('regras_auto_ativo', 'true')
ON CONFLICT (chave) DO NOTHING;

-- ============================================================
-- MIGRATION: Campos retry em outreach_sequencia (idempotente)
-- ============================================================
ALTER TABLE outreach_sequencia ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE outreach_sequencia ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;
ALTER TABLE outreach_sequencia ADD COLUMN IF NOT EXISTS proximo_retry TIMESTAMPTZ;

-- ============================================================
-- EMAIL INBOX — Threads + Mensagens recebidas/enviadas
-- ============================================================
CREATE TABLE IF NOT EXISTS email_threads (
    id SERIAL PRIMARY KEY,
    assunto TEXT NOT NULL,
    categoria VARCHAR(20) DEFAULT 'desconhecido',  -- urgente, cliente, desconhecido
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    email_remetente VARCHAR(255) NOT NULL,
    nome_remetente VARCHAR(255),
    ultima_mensagem_at TIMESTAMPTZ DEFAULT NOW(),
    total_mensagens INTEGER DEFAULT 1,
    lido BOOLEAN DEFAULT FALSE,
    arquivado BOOLEAN DEFAULT FALSE,
    starred BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emails_inbox (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES email_threads(id) ON DELETE CASCADE,
    resend_email_id VARCHAR(255),
    direcao VARCHAR(10) DEFAULT 'recebido',  -- recebido, enviado
    de_email VARCHAR(255) NOT NULL,
    de_nome VARCHAR(255),
    para_email VARCHAR(255) NOT NULL,
    assunto TEXT,
    corpo_html TEXT,
    corpo_texto TEXT,
    tem_anexos BOOLEAN DEFAULT FALSE,
    anexos_json JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices inbox
CREATE INDEX IF NOT EXISTS idx_email_threads_categoria ON email_threads(categoria) WHERE arquivado = FALSE;
CREATE INDEX IF NOT EXISTS idx_email_threads_lido ON email_threads(lido, ultima_mensagem_at DESC) WHERE arquivado = FALSE;
CREATE INDEX IF NOT EXISTS idx_email_threads_remetente ON email_threads(email_remetente);
CREATE INDEX IF NOT EXISTS idx_email_threads_lead ON email_threads(lead_id) WHERE lead_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_emails_inbox_thread ON emails_inbox(thread_id, created_at);
CREATE INDEX IF NOT EXISTS idx_emails_inbox_resend ON emails_inbox(resend_email_id) WHERE resend_email_id IS NOT NULL;

-- ============================================================
-- AUDIO CACHE — Cache inteligente de áudios TTS reutilizáveis
-- ============================================================
CREATE TABLE IF NOT EXISTS audio_cache (
    id SERIAL PRIMARY KEY,
    intent_key TEXT NOT NULL,              -- ex: "preco_planos", "teste_gratis"
    texto_hash TEXT NOT NULL UNIQUE,       -- SHA256 do texto normalizado
    texto_original TEXT NOT NULL,          -- texto completo (para debug)
    pergunta_exemplo TEXT,                 -- pergunta que gerou este cache
    audio_data BYTEA NOT NULL,            -- bytes do MP3
    emocao TEXT DEFAULT '',               -- emotion tag usada na geração
    duracao_estimada_s FLOAT,             -- estimativa em segundos
    vezes_usado INTEGER DEFAULT 1,
    ultimo_uso TIMESTAMPTZ DEFAULT NOW(),
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    ativo BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_audio_cache_intent ON audio_cache(intent_key) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_audio_cache_hash ON audio_cache(texto_hash) WHERE ativo = TRUE;
CREATE INDEX IF NOT EXISTS idx_audio_cache_uso ON audio_cache(vezes_usado DESC, ultimo_uso DESC);

-- Campos novos em wa_conversas para rastrear áudios cache
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS cache_ids_usados JSONB DEFAULT '[]';
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS intents_usadas JSONB DEFAULT '[]';

-- ============================================================
-- P2-P5: CRM TRUE AUTO SALES
-- ============================================================

-- P2: Funil Completo — campos trial link + follow-up handoff
ALTER TABLE leads ADD COLUMN IF NOT EXISTS trial_link_enviado_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS ultimo_reengajamento_at TIMESTAMPTZ;

-- P3: Brain Loop — persona detectada + contagem msgs lead
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS persona_detectada TEXT;
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS msgs_lead_count INTEGER DEFAULT 0;
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS followup_handoff_etapa INTEGER DEFAULT 0;
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS followup_handoff_at TIMESTAMPTZ;

-- Notas em wa_conversas (enriquecimento, agendamento, lead_falso)
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS notas TEXT;

-- Rastreamento de notificações de handoff (evita re-notificar mesmo lead)
-- handoff_notificado_em: quando a última notificação foi enviada ao dono
-- handoff_notificado_score: score no momento da notificação (re-notifica só se +15 pontos)
-- handoff_notificado_tipo: "immediate" | "warm" | "strategic" — para re-notificar se tipo muda
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS handoff_notificado_em TIMESTAMPTZ;
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS handoff_notificado_score INTEGER DEFAULT 0;
ALTER TABLE wa_conversas ADD COLUMN IF NOT EXISTS handoff_notificado_tipo TEXT;

-- P4: Event-Driven Scoring — tabela de eventos
CREATE TABLE IF NOT EXISTS lead_eventos (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    evento TEXT NOT NULL,
    valor INTEGER DEFAULT 0,
    score_antes INTEGER,
    score_depois INTEGER,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_lead_eventos_lead ON lead_eventos(lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_eventos_evento ON lead_eventos(evento, created_at DESC);

-- P5: Tracking de Conversão — tabela de conversões
CREATE TABLE IF NOT EXISTS conversoes (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
    cnpj VARCHAR(14),
    plano TEXT,
    valor_mensal REAL,
    canal_atribuicao TEXT,
    primeira_interacao_at TIMESTAMPTZ,
    conversao_at TIMESTAMPTZ DEFAULT NOW(),
    meses_ativo INTEGER DEFAULT 0,
    receita_total REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_conversoes_lead ON conversoes(lead_id);
CREATE INDEX IF NOT EXISTS idx_conversoes_cnpj ON conversoes(cnpj);
CREATE INDEX IF NOT EXISTS idx_conversoes_canal ON conversoes(canal_atribuicao, conversao_at DESC);

-- Outreach Manual WA — tracking de envios manuais
ALTER TABLE leads ADD COLUMN IF NOT EXISTS wa_outreach_manual_at TIMESTAMPTZ;

-- ============================================================
-- TTS PRONÚNCIA APRENDIDA — auto-aprendizado de fala natural
-- O filtro de humanidade detecta pronúncias erradas, salva aqui,
-- e nas próximas gerações aplica automaticamente.
-- ============================================================
CREATE TABLE IF NOT EXISTS tts_pronuncia_aprendida (
    id SERIAL PRIMARY KEY,
    escrita TEXT NOT NULL UNIQUE,
    pronuncia TEXT NOT NULL,
    origem TEXT DEFAULT 'auto',
    vezes_corrigido INT DEFAULT 1,
    exemplo_contexto TEXT,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tts_pronuncia_escrita ON tts_pronuncia_aprendida(escrita);
