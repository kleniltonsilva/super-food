"""Bot WhatsApp Humanoide — tabelas config, conversas, mensagens, avaliacoes, problemas

Revision ID: 035_bot_whatsapp
Revises: 034_feature_flags
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = '035_bot_whatsapp'
down_revision = '034_feature_flags'
branch_labels = None
depends_on = None


def upgrade():
    # ==================== BOT CONFIG POR RESTAURANTE ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_config (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            bot_ativo BOOLEAN DEFAULT FALSE,
            -- Identidade
            nome_atendente VARCHAR(100) DEFAULT 'Bia',
            tom_personalidade VARCHAR(200) DEFAULT 'informal amigável',
            voz_tts VARCHAR(20) DEFAULT 'ara',
            idioma VARCHAR(10) DEFAULT 'pt-BR',
            -- Evolution API
            evolution_instance VARCHAR(100),
            evolution_api_url VARCHAR(500),
            evolution_api_key VARCHAR(500),
            whatsapp_numero VARCHAR(20),
            -- Capacidades (permissões do dono)
            pode_criar_pedido BOOLEAN DEFAULT TRUE,
            pode_alterar_pedido BOOLEAN DEFAULT TRUE,
            pode_cancelar_pedido BOOLEAN DEFAULT FALSE,
            pode_dar_desconto BOOLEAN DEFAULT FALSE,
            desconto_maximo_pct FLOAT DEFAULT 0,
            pode_reembolsar BOOLEAN DEFAULT FALSE,
            reembolso_maximo_valor FLOAT DEFAULT 0,
            pode_receber_pix BOOLEAN DEFAULT FALSE,
            pode_agendar BOOLEAN DEFAULT FALSE,
            -- Comportamento
            comportamento_fechado VARCHAR(30) DEFAULT 'so_informa',
            estoque_esgotado_acao VARCHAR(30) DEFAULT 'sugere_mais_vendido',
            cancelamento_ate_status VARCHAR(30) DEFAULT 'em_preparo',
            taxa_cancelamento FLOAT DEFAULT 0,
            -- Pós-entrega
            avaliacao_ativa BOOLEAN DEFAULT TRUE,
            delay_avaliacao_min INTEGER DEFAULT 10,
            avaliacao_lembrete_24h BOOLEAN DEFAULT TRUE,
            reclamacao_acao VARCHAR(20) DEFAULT 'manual',
            reclamacao_credito_pct FLOAT DEFAULT 0,
            desconto_por_review BOOLEAN DEFAULT FALSE,
            desconto_review_pct FLOAT DEFAULT 10,
            -- Repescagem
            repescagem_ativa BOOLEAN DEFAULT FALSE,
            repescagem_dias_inativo INTEGER DEFAULT 15,
            repescagem_desconto_pct FLOAT DEFAULT 10,
            -- Impressão automática
            impressao_automatica_bot BOOLEAN DEFAULT TRUE,
            -- Audio
            stt_ativo BOOLEAN DEFAULT TRUE,
            tts_autonomo BOOLEAN DEFAULT TRUE,
            -- Limites
            max_tokens_dia INTEGER DEFAULT 50000,
            tokens_usados_hoje INTEGER DEFAULT 0,
            tokens_reset_em TIMESTAMP,
            -- Timestamps
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(restaurante_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_config_restaurante ON bot_config(restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_config_numero ON bot_config(whatsapp_numero)")

    # ==================== CONVERSAS BOT ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_conversas (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
            telefone VARCHAR(20) NOT NULL,
            nome_cliente VARCHAR(200),
            status VARCHAR(20) DEFAULT 'ativa',
            -- Contexto
            pedido_ativo_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            intencao_atual VARCHAR(50),
            itens_carrinho JSON,
            endereco_confirmado TEXT,
            forma_pagamento VARCHAR(30),
            -- Métricas
            msgs_enviadas INTEGER DEFAULT 0,
            msgs_recebidas INTEGER DEFAULT 0,
            usou_audio BOOLEAN DEFAULT FALSE,
            -- Handoff
            handoff_em TIMESTAMP,
            handoff_motivo TEXT,
            -- Sessão Redis TTL backup
            session_data JSON,
            -- Timestamps
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            encerrado_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_conversas_restaurante ON bot_conversas(restaurante_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_conversas_telefone ON bot_conversas(restaurante_id, telefone)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_conversas_cliente ON bot_conversas(cliente_id)")

    # ==================== MENSAGENS BOT ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_mensagens (
            id SERIAL PRIMARY KEY,
            conversa_id INTEGER NOT NULL REFERENCES bot_conversas(id) ON DELETE CASCADE,
            direcao VARCHAR(10) NOT NULL,
            tipo VARCHAR(20) DEFAULT 'texto',
            conteudo TEXT,
            audio_url TEXT,
            duracao_audio_seg INTEGER,
            -- IA
            tokens_input INTEGER DEFAULT 0,
            tokens_output INTEGER DEFAULT 0,
            modelo_usado VARCHAR(50),
            function_calls JSON,
            tempo_resposta_ms INTEGER,
            -- Timestamps
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_mensagens_conversa ON bot_mensagens(conversa_id, criado_em)")

    # ==================== AVALIACOES PÓS-ENTREGA ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_avaliacoes (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
            conversa_id INTEGER REFERENCES bot_conversas(id) ON DELETE SET NULL,
            nota INTEGER,
            categoria VARCHAR(30),
            detalhe TEXT,
            avaliou_maps BOOLEAN DEFAULT FALSE,
            credito_aplicado FLOAT DEFAULT 0,
            status VARCHAR(20) DEFAULT 'pendente',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            respondido_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_avaliacoes_restaurante ON bot_avaliacoes(restaurante_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_avaliacoes_pedido ON bot_avaliacoes(pedido_id)")

    # ==================== PROBLEMAS REPORTADOS ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_problemas (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            pedido_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            cliente_id INTEGER REFERENCES clientes(id) ON DELETE SET NULL,
            conversa_id INTEGER REFERENCES bot_conversas(id) ON DELETE SET NULL,
            tipo VARCHAR(30) NOT NULL,
            descricao TEXT,
            resolucao TEXT,
            resolvido BOOLEAN DEFAULT FALSE,
            notificou_dono BOOLEAN DEFAULT FALSE,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolvido_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_problemas_restaurante ON bot_problemas(restaurante_id)")

    # ==================== REPESCAGENS ====================
    op.execute("""
        CREATE TABLE IF NOT EXISTS bot_repescagens (
            id SERIAL PRIMARY KEY,
            restaurante_id INTEGER NOT NULL REFERENCES restaurantes(id) ON DELETE CASCADE,
            cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
            cupom_codigo VARCHAR(50),
            cupom_desconto_pct FLOAT,
            mensagem_enviada TEXT,
            retornou BOOLEAN DEFAULT FALSE,
            pedido_retorno_id INTEGER REFERENCES pedidos(id) ON DELETE SET NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            retornou_em TIMESTAMP
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_bot_repescagens_restaurante ON bot_repescagens(restaurante_id)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS bot_repescagens CASCADE")
    op.execute("DROP TABLE IF EXISTS bot_problemas CASCADE")
    op.execute("DROP TABLE IF EXISTS bot_avaliacoes CASCADE")
    op.execute("DROP TABLE IF EXISTS bot_mensagens CASCADE")
    op.execute("DROP TABLE IF EXISTS bot_conversas CASCADE")
    op.execute("DROP TABLE IF EXISTS bot_config CASCADE")
