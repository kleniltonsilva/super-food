"""
database.py - Conexão PostgreSQL + queries do CRM Derekh
Usa pool de conexões psycopg2. DATABASE_URL via env var.
"""
import json
import os
import re
import logging
from datetime import date, datetime
from typing import Optional
from contextlib import contextmanager

log = logging.getLogger("database")

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

DATABASE_URL = os.environ.get("DATABASE_URL", "")


def init_pool(min_conn: int = 1, max_conn: int = 5):
    """Compatibilidade — no-op. Conexões são criadas por request."""
    pass


def close_pool():
    """Compatibilidade — no-op."""
    pass


@contextmanager
def get_conn():
    """Cria conexão nova por request (Fly.io flycast mata idle connections)."""
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()


def init_schema():
    """Executa o schema.sql para criar tabelas (idempotente)."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        sql = f.read()
    with get_conn() as conn:
        conn.cursor().execute(sql)
        conn.commit()
    print("[CRM] Schema PostgreSQL aplicado.")


# ============================================================
# FUNÇÕES DASHBOARD
# ============================================================

def kpis_dashboard() -> dict:
    """KPIs do dashboard: totais de leads, quentes, contactados, pipeline, clientes, emails."""
    with get_conn() as conn:
        cur = conn.cursor()
        kpis = {}
        cur.execute("SELECT COUNT(*) as c FROM leads")
        kpis["total_leads"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM leads WHERE lead_score >= 70")
        kpis["quentes"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM leads WHERE status_pipeline NOT IN ('novo', 'perdido')")
        kpis["contactados"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM leads WHERE status_pipeline NOT IN ('novo', 'cliente', 'perdido')")
        kpis["no_pipeline"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM leads WHERE status_pipeline = 'cliente'")
        kpis["clientes"] = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM interacoes WHERE tipo = 'email'")
        kpis["emails_enviados"] = cur.fetchone()["c"]

        return kpis


def funil_pipeline() -> list:
    """COUNT por status_pipeline para gráfico de funil."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT status_pipeline, COUNT(*) as total
            FROM leads
            GROUP BY status_pipeline
            ORDER BY CASE status_pipeline
                WHEN 'novo' THEN 1
                WHEN 'contactado' THEN 2
                WHEN 'respondeu' THEN 3
                WHEN 'demo_agendada' THEN 4
                WHEN 'proposta_enviada' THEN 5
                WHEN 'negociando' THEN 6
                WHEN 'cliente' THEN 7
                WHEN 'perdido' THEN 8
            END
        """)
        return [dict(r) for r in cur.fetchall()]


def distribuicao_segmento() -> list:
    """COUNT por segmento para gráfico de pizza."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT segmento, COUNT(*) as total
            FROM leads
            GROUP BY segmento
            ORDER BY total DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def top_cidades(limite: int = 10) -> list:
    """Top N cidades por quantidade de leads."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cidade, uf, COUNT(*) as total
            FROM leads
            WHERE cidade IS NOT NULL AND cidade != ''
            GROUP BY cidade, uf
            ORDER BY total DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def followups_hoje() -> list:
    """Leads com follow-up agendado para hoje."""
    with get_conn() as conn:
        cur = conn.cursor()
        hoje = date.today()
        cur.execute("""
            SELECT id, cnpj, razao_social, nome_fantasia, cidade, uf,
                   lead_score, segmento, status_pipeline, data_proximo_contato
            FROM leads
            WHERE data_proximo_contato = %s
            ORDER BY lead_score DESC
            LIMIT 50
        """, (hoje,))
        return [dict(r) for r in cur.fetchall()]


def leads_quentes_sem_contato() -> list:
    """Leads com score >= 70 que nunca foram contactados."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, cnpj, razao_social, nome_fantasia, cidade, uf,
                   lead_score, segmento, status_pipeline,
                   telefone1, email
            FROM leads
            WHERE lead_score >= 70
            AND data_ultimo_contato IS NULL
            AND status_pipeline = 'novo'
            ORDER BY lead_score DESC
            LIMIT 50
        """)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# FUNÇÕES DELIVERY / VARREDURA
# ============================================================

def stats_delivery(cidade: str = None, uf: str = None) -> dict:
    """Stats globais ou por cidade de varredura delivery + agregados iFood."""
    with get_conn() as conn:
        cur = conn.cursor()
        where_parts = []
        params = []
        if cidade:
            where_parts.append("cidade = %s")
            params.append(cidade.upper())
        if uf:
            where_parts.append("uf = %s")
            params.append(uf.upper())
        where = "WHERE " + " AND ".join(where_parts) if where_parts else ""

        cur.execute(f"""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE tem_ifood = 1) as com_ifood,
                COUNT(*) FILTER (WHERE tem_rappi = 1) as com_rappi,
                COUNT(*) FILTER (WHERE tem_99food = 1) as com_99food,
                COUNT(*) FILTER (WHERE tem_ifood = 1 OR tem_rappi = 1 OR tem_99food = 1) as com_algum_delivery,
                COUNT(*) FILTER (WHERE COALESCE(tem_ifood, 0) = 0 AND COALESCE(tem_rappi, 0) = 0 AND COALESCE(tem_99food, 0) = 0) as sem_nenhum_delivery,
                -- Agregados iFood enriquecido
                ROUND(AVG(ifood_rating)::numeric, 2) as ifood_rating_medio,
                COUNT(*) FILTER (WHERE ifood_rating IS NOT NULL) as com_rating_ifood,
                COUNT(*) FILTER (WHERE ifood_reviews IS NOT NULL AND ifood_reviews > 0) as com_reviews_ifood,
                COUNT(*) FILTER (WHERE ifood_aberto = 1 AND tem_ifood = 1) as ifood_abertos,
                COUNT(*) FILTER (WHERE ifood_aberto = 0 AND tem_ifood = 1) as ifood_fechados,
                COUNT(*) FILTER (WHERE ifood_preco = '$') as ifood_preco_baixo,
                COUNT(*) FILTER (WHERE ifood_preco = '$$') as ifood_preco_medio,
                COUNT(*) FILTER (WHERE ifood_preco = '$$$' OR ifood_preco = '$$$$') as ifood_preco_alto
            FROM leads
            {where}
        """, params)
        return dict(cur.fetchone())


def stats_delivery_por_cidade(limite: int = 50) -> list:
    """Stats de delivery por cidade para tabela comparativa."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                cidade, uf,
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE tem_ifood = 1) as com_ifood,
                COUNT(*) FILTER (WHERE tem_rappi = 1) as com_rappi,
                COUNT(*) FILTER (WHERE tem_99food = 1) as com_99food,
                COUNT(*) FILTER (WHERE COALESCE(tem_ifood, 0) = 0 AND COALESCE(tem_rappi, 0) = 0 AND COALESCE(tem_99food, 0) = 0) as sem_nenhum
            FROM leads
            WHERE cidade IS NOT NULL AND cidade != ''
            GROUP BY cidade, uf
            ORDER BY total DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def top_categorias_ifood(limite: int = 10) -> list:
    """Top categorias iFood (explode string CSV em categorias individuais)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT TRIM(cat) as categoria, COUNT(*) as total
            FROM leads, LATERAL unnest(string_to_array(ifood_categorias, ',')) AS cat
            WHERE ifood_categorias IS NOT NULL AND ifood_categorias != ''
            AND tem_ifood = 1
            GROUP BY TRIM(cat)
            ORDER BY total DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def cidades_escaneadas_ifood() -> list:
    """Cidades que têm pelo menos 1 lead com iFood verificado (com_ifood > 0)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT cidade, uf, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE tem_ifood = 1) as com_ifood
            FROM leads
            WHERE cidade IS NOT NULL AND cidade != ''
            GROUP BY cidade, uf
            HAVING COUNT(*) FILTER (WHERE tem_ifood = 1) > 0
            ORDER BY com_ifood DESC
        """)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# FUNÇÕES BUSCA
# ============================================================

def buscar_leads(filtros: dict, pagina: int = 1, por_pagina: int = 50) -> tuple:
    """Busca leads com filtros e paginação server-side.
    Retorna (lista_leads, total_count)."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = ["1=1"]
        params = []

        if filtros.get("uf"):
            params.append(filtros["uf"].upper())
            where.append(f"l.uf = %s")

        if filtros.get("cidade"):
            params.append(filtros["cidade"].upper())
            where.append(f"l.cidade = %s")

        if filtros.get("segmento"):
            params.append(filtros["segmento"])
            where.append(f"l.segmento = %s")

        if filtros.get("status_pipeline"):
            params.append(filtros["status_pipeline"])
            where.append(f"l.status_pipeline = %s")

        if filtros.get("score_min"):
            params.append(int(filtros["score_min"]))
            where.append(f"l.lead_score >= %s")

        if filtros.get("score_max"):
            params.append(int(filtros["score_max"]))
            where.append(f"l.lead_score <= %s")

        if filtros.get("tem_ifood") == "sim":
            where.append("l.tem_ifood = 1")
        elif filtros.get("tem_ifood") == "nao":
            where.append("(l.tem_ifood = 0 OR l.tem_ifood IS NULL)")

        if filtros.get("tem_rappi") == "sim":
            where.append("l.tem_rappi = 1")
        elif filtros.get("tem_rappi") == "nao":
            where.append("(l.tem_rappi = 0 OR l.tem_rappi IS NULL)")

        if filtros.get("tem_99food") == "sim":
            where.append("l.tem_99food = 1")
        elif filtros.get("tem_99food") == "nao":
            where.append("(l.tem_99food = 0 OR l.tem_99food IS NULL)")

        if filtros.get("eh_rede") == "sim":
            where.append("l.multi_restaurante = 1")

        # Filtros iFood enriquecidos
        if filtros.get("ifood_rating_min"):
            params.append(float(filtros["ifood_rating_min"]))
            where.append("l.ifood_rating >= %s")

        if filtros.get("ifood_preco"):
            precos = filtros["ifood_preco"] if isinstance(filtros["ifood_preco"], list) else [filtros["ifood_preco"]]
            placeholders = ", ".join(["%s"] * len(precos))
            params.extend(precos)
            where.append(f"l.ifood_preco IN ({placeholders})")

        if filtros.get("ifood_categorias"):
            params.append(f"%{filtros['ifood_categorias']}%")
            where.append("l.ifood_categorias ILIKE %s")

        if filtros.get("ifood_aberto") == "sim":
            where.append("l.ifood_aberto = 1 AND l.tem_ifood = 1")
        elif filtros.get("ifood_aberto") == "fechado":
            where.append("l.ifood_aberto = 0 AND l.tem_ifood = 1")

        if filtros.get("q"):
            termo = f"%{filtros['q']}%"
            params.extend([termo, termo, termo])
            where.append("(l.razao_social ILIKE %s OR l.nome_fantasia ILIKE %s OR l.cnpj LIKE %s)")

        where_clause = " AND ".join(where)

        # Count total
        cur.execute(f"SELECT COUNT(*) as c FROM leads l WHERE {where_clause}", params)
        total = cur.fetchone()["c"]

        # Busca com paginação
        offset = (pagina - 1) * por_pagina
        params.extend([por_pagina, offset])
        cur.execute(f"""
            SELECT l.id, l.cnpj, l.razao_social, l.nome_fantasia,
                   l.cidade, l.uf, l.lead_score, l.segmento,
                   l.status_pipeline, l.telefone1, l.email,
                   l.tem_ifood, l.tem_rappi, l.tem_99food,
                   l.capital_social, l.data_abertura,
                   l.rating, l.website, l.data_ultimo_contato,
                   l.ifood_rating, l.ifood_reviews, l.ifood_preco,
                   l.ifood_categorias, l.ifood_tempo_entrega, l.ifood_aberto
            FROM leads l
            WHERE {where_clause}
            ORDER BY l.lead_score DESC, l.razao_social ASC
            LIMIT %s OFFSET %s
        """, params)

        return [dict(r) for r in cur.fetchall()], total


def listar_ufs_disponiveis() -> list:
    """UFs distintas presentes no banco."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT uf FROM leads
            WHERE uf IS NOT NULL AND uf != ''
            ORDER BY uf
        """)
        return [r["uf"] for r in cur.fetchall()]


def listar_cidades_disponiveis(uf: str = None) -> list:
    """Cidades disponíveis, opcionalmente filtradas por UF."""
    with get_conn() as conn:
        cur = conn.cursor()
        if uf:
            cur.execute("""
                SELECT cidade, uf, COUNT(*) as total
                FROM leads
                WHERE uf = %s AND cidade IS NOT NULL AND cidade != ''
                GROUP BY cidade, uf
                ORDER BY total DESC
            """, (uf.upper(),))
        else:
            cur.execute("""
                SELECT cidade, uf, COUNT(*) as total
                FROM leads
                WHERE cidade IS NOT NULL AND cidade != ''
                GROUP BY cidade, uf
                ORDER BY total DESC
                LIMIT 100
            """)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# FUNÇÕES FICHA
# ============================================================

def obter_lead(lead_id: int) -> Optional[dict]:
    """Retorna lead completo."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def obter_interacoes_lead(lead_id: int) -> list:
    """Retorna interações de um lead, ordem cronológica reversa."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM interacoes
            WHERE lead_id = %s
            ORDER BY created_at DESC
        """, (lead_id,))
        return [dict(r) for r in cur.fetchall()]


def obter_socios_lead(lead_id: int) -> list:
    """Retorna sócios do lead (parse do socios_json)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT socios_json FROM leads WHERE id = %s", (lead_id,))
        row = cur.fetchone()
        if row and row["socios_json"]:
            data = row["socios_json"]
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except (json.JSONDecodeError, TypeError):
                    return []
            elif isinstance(data, list):
                return data
        return []


# ============================================================
# FUNÇÕES PIPELINE (AÇÕES)
# ============================================================

def atualizar_status_pipeline(lead_id: int, status: str, motivo_perda: str = None):
    """Atualiza status do pipeline de um lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        if status == "perdido" and motivo_perda:
            cur.execute("""
                UPDATE leads SET status_pipeline = %s, motivo_perda = %s WHERE id = %s
            """, (status, motivo_perda, lead_id))
        else:
            cur.execute("""
                UPDATE leads SET status_pipeline = %s WHERE id = %s
            """, (status, lead_id))
        conn.commit()


def agendar_followup(lead_id: int, data: str):
    """Agenda data de próximo contato."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE leads SET data_proximo_contato = %s WHERE id = %s", (data, lead_id))
        conn.commit()


def registrar_interacao(lead_id: int, tipo: str, canal: str, conteudo: str,
                        resultado: str, email_message_id: str = None):
    """Registra interação e atualiza data_ultimo_contato."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO interacoes (lead_id, tipo, canal, conteudo, resultado, email_message_id)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (lead_id, tipo, canal, conteudo, resultado, email_message_id))
        cur.execute("""
            UPDATE leads SET data_ultimo_contato = NOW() WHERE id = %s
        """, (lead_id,))
        conn.commit()


def atualizar_notas(lead_id: int, notas: str):
    """Salva notas de um lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE leads SET notas = %s WHERE id = %s", (notas, lead_id))
        conn.commit()


# ============================================================
# FUNÇÕES PIPELINE (CONSULTA)
# ============================================================

def leads_por_pipeline(status: str, limite: int = 20) -> list:
    """Retorna top N leads de um status do pipeline, ordenados por score."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, cnpj, razao_social, nome_fantasia, cidade, uf,
                   lead_score, segmento, data_proximo_contato
            FROM leads
            WHERE status_pipeline = %s
            ORDER BY lead_score DESC
            LIMIT %s
        """, (status, limite))
        return [dict(r) for r in cur.fetchall()]


def contagem_pipeline() -> dict:
    """Retorna contagem por status do pipeline."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT status_pipeline, COUNT(*) as total
            FROM leads
            GROUP BY status_pipeline
        """)
        return {r["status_pipeline"]: r["total"] for r in cur.fetchall()}


# ============================================================
# EXPORT
# ============================================================

def buscar_leads_para_export(filtros: dict) -> list:
    """Busca leads para exportação (sem paginação)."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = ["1=1"]
        params = []

        if filtros.get("uf"):
            params.append(filtros["uf"].upper())
            where.append("uf = %s")
        if filtros.get("cidade"):
            params.append(filtros["cidade"].upper())
            where.append("cidade = %s")
        if filtros.get("segmento"):
            params.append(filtros["segmento"])
            where.append("segmento = %s")
        if filtros.get("status_pipeline"):
            params.append(filtros["status_pipeline"])
            where.append("status_pipeline = %s")

        where_clause = " AND ".join(where)
        cur.execute(f"""
            SELECT * FROM leads
            WHERE {where_clause}
            ORDER BY lead_score DESC
        """, params)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# EMAIL TEMPLATES CRUD
# ============================================================

def listar_email_templates() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM email_templates ORDER BY created_at DESC")
        return [dict(r) for r in cur.fetchall()]


def obter_email_template(template_id: int) -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM email_templates WHERE id = %s", (template_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def criar_email_template(nome: str, assunto: str, corpo_html: str, segmento_alvo: str = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO email_templates (nome, assunto, corpo_html, segmento_alvo)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (nome, assunto, corpo_html, segmento_alvo))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def atualizar_email_template(template_id: int, nome: str, assunto: str,
                              corpo_html: str, segmento_alvo: str = None):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_templates
            SET nome = %s, assunto = %s, corpo_html = %s, segmento_alvo = %s
            WHERE id = %s
        """, (nome, assunto, corpo_html, segmento_alvo, template_id))
        conn.commit()


def deletar_email_template(template_id: int):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM email_templates WHERE id = %s", (template_id,))
        conn.commit()


# ============================================================
# CAMPANHAS CRUD
# ============================================================

def listar_campanhas() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, t.nome as template_nome
            FROM campanhas_email c
            LEFT JOIN email_templates t ON c.template_id = t.id
            ORDER BY c.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def obter_campanha(campanha_id: int) -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, t.nome as template_nome, t.assunto as template_assunto
            FROM campanhas_email c
            LEFT JOIN email_templates t ON c.template_id = t.id
            WHERE c.id = %s
        """, (campanha_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def criar_campanha(nome: str, template_id: int, filtros_json: dict = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO campanhas_email (nome, template_id, filtros_json)
            VALUES (%s, %s, %s) RETURNING id
        """, (nome, template_id, json.dumps(filtros_json) if filtros_json else None))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def atualizar_campanha_contadores(campanha_id: int, campo: str, incremento: int = 1):
    """Incrementa um contador da campanha (total_enviados, total_abertos, etc)."""
    campos_validos = {"total_enviados", "total_abertos", "total_clicados", "total_bounced"}
    if campo not in campos_validos:
        return
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE campanhas_email SET {campo} = {campo} + %s WHERE id = %s
        """, (incremento, campanha_id))
        conn.commit()


def atualizar_status_campanha(campanha_id: int, status: str):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE campanhas_email SET status = %s WHERE id = %s", (status, campanha_id))
        conn.commit()


# ============================================================
# SEQUÊNCIAS
# ============================================================

def listar_sequencias() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT s.*,
                   COUNT(DISTINCT se.id) as total_etapas,
                   COUNT(DISTINCT ls.id) FILTER (WHERE ls.status = 'ativo') as leads_ativos
            FROM sequencias_email s
            LEFT JOIN sequencia_etapas se ON s.id = se.sequencia_id
            LEFT JOIN lead_sequencia ls ON s.id = ls.sequencia_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """)
        return [dict(r) for r in cur.fetchall()]


def obter_sequencia(sequencia_id: int) -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM sequencias_email WHERE id = %s", (sequencia_id,))
        row = cur.fetchone()
        if not row:
            return None
        seq = dict(row)

        cur.execute("""
            SELECT se.*, t.nome as template_nome, t.assunto as template_assunto
            FROM sequencia_etapas se
            JOIN email_templates t ON se.template_id = t.id
            WHERE se.sequencia_id = %s
            ORDER BY se.ordem
        """, (sequencia_id,))
        seq["etapas"] = [dict(r) for r in cur.fetchall()]

        return seq


def criar_sequencia(nome: str, descricao: str = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sequencias_email (nome, descricao) VALUES (%s, %s) RETURNING id
        """, (nome, descricao))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def adicionar_etapa_sequencia(sequencia_id: int, template_id: int,
                               dias_espera: int, condicao: str = "sempre"):
    with get_conn() as conn:
        cur = conn.cursor()
        # Determinar próxima ordem
        cur.execute("""
            SELECT COALESCE(MAX(ordem), 0) + 1 as prox
            FROM sequencia_etapas WHERE sequencia_id = %s
        """, (sequencia_id,))
        prox_ordem = cur.fetchone()["prox"]

        cur.execute("""
            INSERT INTO sequencia_etapas (sequencia_id, ordem, template_id, dias_espera, condicao)
            VALUES (%s, %s, %s, %s, %s)
        """, (sequencia_id, prox_ordem, template_id, dias_espera, condicao))
        conn.commit()


def inscrever_leads_sequencia(lead_ids: list, sequencia_id: int):
    """Inscreve múltiplos leads em uma sequência."""
    with get_conn() as conn:
        cur = conn.cursor()
        for lead_id in lead_ids:
            cur.execute("""
                INSERT INTO lead_sequencia (lead_id, sequencia_id, proximo_envio)
                VALUES (%s, %s, NOW())
                ON CONFLICT (lead_id, sequencia_id) DO NOTHING
            """, (lead_id, sequencia_id))
        conn.commit()


def leads_sequencia_pendentes() -> list:
    """Leads com envio pendente em sequências ativas."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT ls.*, l.cnpj, l.nome_fantasia, l.email,
                   s.nome as sequencia_nome,
                   se.template_id, se.condicao
            FROM lead_sequencia ls
            JOIN leads l ON ls.lead_id = l.id
            JOIN sequencias_email s ON ls.sequencia_id = s.id
            JOIN sequencia_etapas se ON se.sequencia_id = ls.sequencia_id
                AND se.ordem = ls.etapa_atual
            WHERE ls.status = 'ativo'
            AND ls.proximo_envio <= NOW()
            AND s.ativo = TRUE
            AND l.email IS NOT NULL
            AND l.email_invalido = 0
            ORDER BY ls.proximo_envio
            LIMIT 100
        """)
        return [dict(r) for r in cur.fetchall()]


def avancar_etapa_sequencia(lead_sequencia_id: int, dias_proxima: int):
    """Avança lead para próxima etapa da sequência."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE lead_sequencia
            SET etapa_atual = etapa_atual + 1,
                proximo_envio = NOW() + INTERVAL '%s days'
            WHERE id = %s
        """, (dias_proxima, lead_sequencia_id))

        # Verificar se passou da última etapa
        cur.execute("""
            SELECT ls.etapa_atual, COUNT(se.id) as total_etapas
            FROM lead_sequencia ls
            JOIN sequencia_etapas se ON se.sequencia_id = ls.sequencia_id
            WHERE ls.id = %s
            GROUP BY ls.etapa_atual
        """, (lead_sequencia_id,))
        row = cur.fetchone()
        if row and row["etapa_atual"] > row["total_etapas"]:
            cur.execute("""
                UPDATE lead_sequencia SET status = 'concluido' WHERE id = %s
            """, (lead_sequencia_id,))

        conn.commit()


# ============================================================
# WEBHOOK HELPERS
# ============================================================

def marcar_email_invalido(lead_id: int):
    """Marca email de um lead como inválido (bounced)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE leads SET email_invalido = 1 WHERE id = %s", (lead_id,))
        conn.commit()


def buscar_interacao_por_email_id(email_message_id: str) -> Optional[dict]:
    """Busca interação pelo email_message_id do Resend."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT i.*, l.id as lead_id_fk
            FROM interacoes i
            JOIN leads l ON i.lead_id = l.id
            WHERE i.email_message_id = %s
        """, (email_message_id,))
        row = cur.fetchone()
        return dict(row) if row else None


# ============================================================
# CONFIGURAÇÕES DO SISTEMA
# ============================================================

def obter_configuracao(chave: str) -> Optional[str]:
    """Retorna valor de uma configuração ou None."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT valor FROM configuracoes WHERE chave = %s", (chave,))
        row = cur.fetchone()
        return row["valor"] if row else None


def obter_configuracoes_todas() -> dict:
    """Retorna todas as configurações como dict {chave: valor}."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT chave, valor FROM configuracoes")
        return {r["chave"]: r["valor"] for r in cur.fetchall()}


def salvar_configuracao(chave: str, valor: str):
    """UPSERT de uma configuração."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO configuracoes (chave, valor, updated_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor, updated_at = NOW()
        """, (chave, valor))
        conn.commit()


def cidade_tem_delivery_verificado(cidade: str, uf: str) -> bool:
    """Verifica se pelo menos 1 lead da cidade tem delivery verificado (tem_ifood=1 ou tem_rappi=1 ou tem_99food=1)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM leads
            WHERE cidade = %s AND uf = %s
            AND (tem_ifood = 1 OR tem_rappi = 1 OR tem_99food = 1)
        """, (cidade.upper(), uf.upper()))
        return cur.fetchone()["c"] > 0


# ============================================================
# OUTREACH — EMAILS ENVIADOS
# ============================================================

def criar_email_enviado(lead_id: int, template_id: int, assunto: str,
                        tracking_id: str, pixel_url: str,
                        resend_message_id: str = None,
                        campanha_id: int = None) -> int:
    """Registra email enviado com tracking. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO emails_enviados
                (lead_id, template_id, assunto, tracking_id, pixel_url,
                 resend_message_id, campanha_id, horario_enviado)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            RETURNING id
        """, (lead_id, template_id, assunto, tracking_id, pixel_url,
              resend_message_id, campanha_id))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def marcar_email_aberto(tracking_id: str) -> bool:
    """Marca email como aberto. Incrementa contador. Retorna True se encontrado."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE emails_enviados
            SET aberto = TRUE,
                aberto_at = COALESCE(aberto_at, NOW()),
                aberturas_count = aberturas_count + 1
            WHERE tracking_id = %s::uuid
            RETURNING id
        """, (tracking_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def marcar_email_clique(tracking_id: str, tipo_clique: str) -> bool:
    """Marca clique no email (site|wa|unsub). Retorna True se encontrado."""
    campos = {"site": "clicou_site", "wa": "clicou_wa", "unsub": "clicou_unsub"}
    campo = campos.get(tipo_clique)
    if not campo:
        return False
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE emails_enviados
            SET {campo} = TRUE
            WHERE tracking_id = %s::uuid
            RETURNING id
        """, (tracking_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def marcar_email_bounce(tracking_id: str) -> bool:
    """Marca email como bounced. Retorna True se encontrado."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE emails_enviados SET bounced = TRUE
            WHERE tracking_id = %s::uuid
            RETURNING id, lead_id
        """, (tracking_id,))
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE leads SET email_invalido = 1 WHERE id = %s", (row["lead_id"],))
        conn.commit()
        return row is not None


def buscar_email_por_tracking(tracking_id: str) -> Optional[dict]:
    """Busca email enviado pelo tracking_id."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.*, l.nome_fantasia, l.email as lead_email
            FROM emails_enviados e
            JOIN leads l ON e.lead_id = l.id
            WHERE e.tracking_id = %s::uuid
        """, (tracking_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def buscar_email_por_resend_id(resend_message_id: str) -> Optional[dict]:
    """Busca email enviado pelo resend_message_id."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.*, l.nome_fantasia, l.email as lead_email
            FROM emails_enviados e
            JOIN leads l ON e.lead_id = l.id
            WHERE e.resend_message_id = %s
        """, (resend_message_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def emails_enviados_hoje() -> int:
    """Conta emails enviados nas últimas 24h (guardrail warmup)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM emails_enviados
            WHERE horario_enviado >= NOW() - INTERVAL '24 hours'
        """)
        return cur.fetchone()["c"]


def emails_enviados_mes() -> int:
    """Conta emails enviados no mês corrente (quota Resend)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM emails_enviados
            WHERE horario_enviado >= DATE_TRUNC('month', NOW())
        """)
        return cur.fetchone()["c"]


def email_quota_resend() -> dict:
    """Retorna quota Resend: enviados hoje, mês, limites e restante.
    Free plan: 3000/mês, 100/dia."""
    hoje = emails_enviados_hoje()
    mes = emails_enviados_mes()
    limite_dia = 100
    limite_mes = 3000
    return {
        "enviados_hoje": hoje,
        "enviados_mes": mes,
        "limite_dia": limite_dia,
        "limite_mes": limite_mes,
        "restante_hoje": max(limite_dia - hoje, 0),
        "restante_mes": max(limite_mes - mes, 0),
        "percentual_mes": round(mes / limite_mes * 100, 1),
    }


def stats_outreach(periodo_dias: int = 7) -> dict:
    """Stats de outreach do período: emails enviados, abertos, clicados, bounced."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) as total_enviados,
                COUNT(*) FILTER (WHERE aberto = TRUE) as total_abertos,
                COUNT(*) FILTER (WHERE clicou_site = TRUE OR clicou_wa = TRUE) as total_clicados,
                COUNT(*) FILTER (WHERE bounced = TRUE) as total_bounced,
                COUNT(*) FILTER (WHERE clicou_unsub = TRUE) as total_unsub
            FROM emails_enviados
            WHERE horario_enviado >= NOW() - INTERVAL '%s days'
        """, (periodo_dias,))
        row = cur.fetchone()
        result = dict(row) if row else {}
        enviados = result.get("total_enviados", 0)
        result["open_rate"] = round(result.get("total_abertos", 0) / max(enviados, 1) * 100, 1)
        result["ctr"] = round(result.get("total_clicados", 0) / max(enviados, 1) * 100, 1)
        result["bounce_rate"] = round(result.get("total_bounced", 0) / max(enviados, 1) * 100, 1)
        return result


# ============================================================
# OUTREACH — SEQUÊNCIA
# ============================================================

def criar_outreach_acao(lead_id: int, acao: str, tier: str,
                        agendado_para, template_id: int = None) -> int:
    """Cria ação de outreach agendada. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO outreach_sequencia
                (lead_id, acao, tier, agendado_para, template_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (lead_id, acao, tier, agendado_para, template_id))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def listar_outreach_pendentes(limite: int = 50) -> list:
    """Lista ações de outreach pendentes (agendado_para <= NOW ou retry pronto)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.*, l.nome_fantasia, l.email, l.telefone1,
                   l.lead_score, l.opt_out_email, l.opt_out_wa,
                   l.email_invalido, l.canal_primario, l.email_tipo
            FROM outreach_sequencia o
            JOIN leads l ON o.lead_id = l.id
            WHERE o.executado = FALSE AND o.cancelado = FALSE
            AND (
                o.agendado_para <= NOW()
                OR (o.retry_count > 0 AND o.proximo_retry IS NOT NULL AND o.proximo_retry <= NOW())
            )
            ORDER BY o.agendado_para
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def listar_outreach_futuras(limite: int = 50) -> list:
    """Lista próximas ações agendadas (futuras, para dashboard)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT o.*, l.nome_fantasia, l.email, l.lead_score, l.tier
            FROM outreach_sequencia o
            JOIN leads l ON o.lead_id = l.id
            WHERE o.executado = FALSE AND o.cancelado = FALSE
            AND o.agendado_para > NOW()
            ORDER BY o.agendado_para
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def marcar_outreach_executado(acao_id: int, resultado: str, erro_detalhe: str = None) -> bool:
    """Marca ação como executada com resultado."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE outreach_sequencia
            SET executado = TRUE, executado_at = NOW(), resultado = %s, erro_detalhe = %s
            WHERE id = %s
            RETURNING id
        """, (resultado, erro_detalhe, acao_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def reagendar_retry(acao_id: int, retry_count: int, proximo_retry) -> bool:
    """Reagenda ação com backoff exponencial. NÃO marca como executado."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE outreach_sequencia
            SET retry_count = %s, proximo_retry = %s, agendado_para = %s
            WHERE id = %s AND executado = FALSE
            RETURNING id
        """, (retry_count, proximo_retry, proximo_retry, acao_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def contar_acoes_lead_sem_resposta(lead_id: int, dias: int = 7) -> int:
    """Conta ações enviadas ao lead nos últimos N dias SEM resposta do lead.
    Usado pelo cooling period para evitar fadiga."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT COUNT(*) as c FROM outreach_sequencia
            WHERE lead_id = %s AND resultado = 'enviado'
            AND executado_at >= NOW() - INTERVAL '%s days'
            AND lead_id NOT IN (
                SELECT DISTINCT wc.lead_id FROM wa_mensagens wm
                JOIN wa_conversas wc ON wm.conversa_id = wc.id
                WHERE wc.lead_id = %s AND wm.direcao = 'recebida'
                AND wm.created_at >= NOW() - INTERVAL '%s days'
            )
        """, (lead_id, dias, lead_id, dias))
        return cur.fetchone()["c"]


def cancelar_outreach_lead(lead_id: int) -> int:
    """Cancela todas ações pendentes de um lead. Retorna quantidade cancelada."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE outreach_sequencia
            SET cancelado = TRUE
            WHERE lead_id = %s AND executado = FALSE AND cancelado = FALSE
        """, (lead_id,))
        count = cur.rowcount
        conn.commit()
        return count


def opt_out_lead(lead_id: int, canal: str) -> bool:
    """Marca opt-out do lead e cancela ações pendentes. canal: 'email' ou 'wa'."""
    with get_conn() as conn:
        cur = conn.cursor()
        if canal == "email":
            cur.execute("""
                UPDATE leads SET opt_out_email = TRUE, opt_out_at = NOW() WHERE id = %s
            """, (lead_id,))
        elif canal == "wa":
            cur.execute("""
                UPDATE leads SET opt_out_wa = TRUE, opt_out_at = NOW() WHERE id = %s
            """, (lead_id,))
        else:
            return False
        # Cancelar ações pendentes
        cur.execute("""
            UPDATE outreach_sequencia
            SET cancelado = TRUE
            WHERE lead_id = %s AND executado = FALSE AND cancelado = FALSE
        """, (lead_id,))
        conn.commit()
        return True


# ============================================================
# OUTREACH REGRAS — CRUD
# ============================================================

def listar_outreach_regras() -> list:
    """Lista regras de outreach ativas, ordenadas por prioridade DESC."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM outreach_regras
            WHERE ativo = TRUE
            ORDER BY prioridade DESC, id ASC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if isinstance(r.get("condicao"), str):
                r["condicao"] = json.loads(r["condicao"])
            if isinstance(r.get("acoes"), str):
                r["acoes"] = json.loads(r["acoes"])
        return rows


def listar_outreach_regras_todas() -> list:
    """Lista TODAS as regras (incluindo inativas), para UI admin."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM outreach_regras ORDER BY prioridade DESC, id ASC")
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            if isinstance(r.get("condicao"), str):
                r["condicao"] = json.loads(r["condicao"])
            if isinstance(r.get("acoes"), str):
                r["acoes"] = json.loads(r["acoes"])
        return rows


def criar_outreach_regra(nome: str, condicao: dict, acoes: list = None,
                          prioridade: int = 0) -> int:
    """Cria regra de outreach. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO outreach_regras (nome, prioridade, condicao, acoes)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (nome, prioridade,
              json.dumps(condicao), json.dumps(acoes) if acoes else None))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def atualizar_outreach_regra(regra_id: int, **campos) -> bool:
    """Atualiza campos de uma regra. Campos válidos: nome, prioridade, condicao, acoes, ativo."""
    campos_validos = {"nome", "prioridade", "condicao", "acoes", "ativo"}
    sets = []
    params = []
    for k, v in campos.items():
        if k not in campos_validos:
            continue
        if k in ("condicao", "acoes"):
            v = json.dumps(v) if v is not None else None
        sets.append(f"{k} = %s")
        params.append(v)
    if not sets:
        return False
    params.append(regra_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE outreach_regras SET {', '.join(sets)} WHERE id = %s RETURNING id
        """, params)
        found = cur.fetchone() is not None
        conn.commit()
        return found


def deletar_outreach_regra(regra_id: int) -> bool:
    """Deleta regra de outreach. Retorna True se encontrou."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM outreach_regras WHERE id = %s RETURNING id", (regra_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def leads_novos_sem_outreach(limite: int = 50) -> list:
    """Leads SEM ações na outreach_sequencia.
    Elegíveis: com email, sem opt_out, sem email_invalido.
    Ordenados por lead_score DESC — melhores leads primeiro.
    SEM filtro de data: processa toda a base progressivamente."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.email, l.telefone1,
                   l.lead_score, l.segmento, l.tier,
                   l.tem_ifood, l.tem_rappi, l.tem_99food
            FROM leads l
            WHERE l.opt_out_email = FALSE
              AND l.lead_falso = FALSE
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
              AND l.email IS NOT NULL AND l.email != ''
              AND l.email_invalido = 0
              AND NOT EXISTS (
                  SELECT 1 FROM outreach_sequencia o
                  WHERE o.lead_id = l.id AND o.cancelado = FALSE
              )
            ORDER BY l.lead_score DESC NULLS LAST
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def leads_novos_sem_outreach_v2(limite: int = 50) -> list:
    """Leads SEM ações de outreach — TODA a base, sem filtro de data.
    Inclui leads com email E/OU telefone (não só email).
    Usado pelo Brain Loop para orquestrar outreach multi-canal.
    Ordenados por lead_score DESC — processa os melhores primeiro."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.bairro, l.email, l.telefone1,
                   l.telefone_proprietario,
                   l.lead_score, l.segmento, l.tier,
                   l.tem_ifood, l.tem_rappi, l.tem_99food,
                   l.wa_verificado, l.wa_existe, l.canal_primario
            FROM leads l
            WHERE l.opt_out_email = FALSE
              AND l.opt_out_wa = FALSE
              AND l.lead_falso = FALSE
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
              AND (
                  (l.email IS NOT NULL AND l.email != '' AND l.email_invalido = 0)
                  OR (l.telefone1 IS NOT NULL AND l.telefone1 != '')
                  OR (l.telefone_proprietario IS NOT NULL AND l.telefone_proprietario != '')
              )
              AND NOT EXISTS (
                  SELECT 1 FROM outreach_sequencia o
                  WHERE o.lead_id = l.id AND o.cancelado = FALSE
              )
              AND NOT EXISTS (
                  SELECT 1 FROM wa_conversas c
                  WHERE c.lead_id = l.id
              )
            ORDER BY l.lead_score DESC NULLS LAST
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def leads_pendentes_validacao(limite: int = 50) -> list:
    """Leads sem contato validado (contato_validado_at IS NULL).
    Usado pelo Brain Loop para etapa de validação.
    Exclui leads falsos, perdidos e opt-out."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.email, l.telefone1, l.telefone_proprietario
            FROM leads l
            WHERE l.contato_validado_at IS NULL
              AND l.lead_falso = FALSE
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
              AND l.opt_out_wa = FALSE
              AND (
                  (l.email IS NOT NULL AND l.email != '')
                  OR (l.telefone1 IS NOT NULL AND l.telefone1 != '')
                  OR (l.telefone_proprietario IS NOT NULL AND l.telefone_proprietario != '')
              )
            ORDER BY l.lead_score DESC NULLS LAST
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def leads_para_outreach_manual(limite: int = 50, cidade: str = None) -> list:
    """Leads COM telefone para outreach manual via WhatsApp.
    Exclui leads já contatados por WA nos últimos 7 dias.
    Retorna dados completos incluindo sócios para personalização."""
    with get_conn() as conn:
        cur = conn.cursor()
        where_extra = ""
        params = []
        if cidade:
            where_extra = "AND UPPER(l.cidade) = %s"
            params.append(cidade.upper())
        params.append(limite)
        cur.execute(f"""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.bairro, l.email, l.telefone1,
                   l.telefone_proprietario, l.telefone2,
                   l.lead_score, l.segmento, l.tier,
                   l.tem_ifood, l.tem_rappi, l.tem_99food,
                   l.rating, l.total_reviews, l.socios_json,
                   l.ifood_rating, l.ifood_categorias,
                   l.porte, l.capital_social,
                   l.wa_outreach_manual_at
            FROM leads l
            WHERE l.lead_falso = FALSE
              AND l.opt_out_wa = FALSE
              AND (l.telefone1 IS NOT NULL AND l.telefone1 != '')
              AND l.wa_outreach_manual_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM wa_conversas c
                  WHERE c.lead_id = l.id
                    AND c.created_at >= NOW() - INTERVAL '7 days'
              )
              {where_extra}
            ORDER BY l.lead_score DESC NULLS LAST
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def marcar_outreach_manual_enviado(lead_id: int) -> bool:
    """Marca lead como contatado via outreach manual WA (timestamp)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET wa_outreach_manual_at = NOW(), updated_at = NOW()
            WHERE id = %s RETURNING id
        """, (lead_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def inserir_outreach_fila(lead_id: int, mensagem: str, wa_enviar_link: str,
                          wa_ana_link: str = "", nome_lead: str = "",
                          cidade: str = "", uf: str = "", telefone: str = "",
                          tem_ifood: bool = False, lead_score: int = 0,
                          gerado_por: str = "brain_loop") -> int:
    """Insere mensagem WA na fila de outreach autônomo (pendente de envio manual).
    Retorna o ID da fila ou 0 se já existe pendente para este lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        # Evitar duplicata — só 1 pendente por lead
        cur.execute("""
            SELECT id FROM wa_outreach_fila
            WHERE lead_id = %s AND status = 'pendente'
        """, (lead_id,))
        if cur.fetchone():
            return 0
        cur.execute("""
            INSERT INTO wa_outreach_fila
                (lead_id, mensagem, wa_enviar_link, wa_ana_link, nome_lead,
                 cidade, uf, telefone, tem_ifood, lead_score, gerado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (lead_id, mensagem, wa_enviar_link, wa_ana_link, nome_lead,
              cidade, uf, telefone, tem_ifood, lead_score, gerado_por))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0


def listar_outreach_fila(status: str = "pendente", limite: int = 50) -> list:
    """Lista mensagens na fila de outreach autônomo (mais recentes primeiro)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT f.*, l.rating, l.nome_fantasia as nome_fantasia_atual,
                   l.socios_json, l.bairro
            FROM wa_outreach_fila f
            JOIN leads l ON l.id = f.lead_id
            WHERE f.status = %s
            ORDER BY f.lead_score DESC, f.created_at DESC
            LIMIT %s
        """, (status, limite))
        return [dict(r) for r in cur.fetchall()]


def marcar_outreach_fila_enviado(fila_id: int) -> bool:
    """Marca item da fila como enviado (dono clicou no wa.me link)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_outreach_fila
            SET status = 'enviado', enviado_at = NOW()
            WHERE id = %s AND status = 'pendente'
            RETURNING lead_id
        """, (fila_id,))
        row = cur.fetchone()
        if row:
            # Atualizar lead wa_outreach_manual_at
            cur.execute("""
                UPDATE leads SET wa_outreach_manual_at = NOW() WHERE id = %s
            """, (row["lead_id"],))
            conn.commit()
            return True
        conn.commit()
        return False


def descartar_outreach_fila(fila_id: int) -> bool:
    """Descarta item da fila (dono decidiu não enviar)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_outreach_fila SET status = 'descartado'
            WHERE id = %s AND status = 'pendente' RETURNING id
        """, (fila_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def contar_outreach_fila_pendente() -> int:
    """Conta total de mensagens pendentes na fila."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as n FROM wa_outreach_fila WHERE status = 'pendente'")
        return cur.fetchone()["n"]


def limpar_outreach_fila_expirados(dias: int = 7) -> int:
    """Marca como expirados itens pendentes com mais de N dias."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_outreach_fila SET status = 'expirado'
            WHERE status = 'pendente'
              AND created_at < NOW() - INTERVAL '%s days'
        """, (dias,))
        n = cur.rowcount
        conn.commit()
        return n


# ============================================================
# EMAIL OUTREACH FILA — Emails pendentes de aprovação
# ============================================================

def inserir_email_fila(lead_id: int, assunto: str, corpo_html: str,
                       email_destino: str, nome_lead: str = "",
                       cidade: str = "", uf: str = "",
                       lead_score: int = 0, tem_ifood: bool = False,
                       metodo: str = "grok", template_id: int = None,
                       gerado_por: str = "outreach_engine") -> int:
    """Insere email na fila de aprovação (pendente de envio pelo dono).
    Retorna o ID da fila ou 0 se já existe pendente para este lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM email_outreach_fila
            WHERE lead_id = %s AND status = 'pendente'
        """, (lead_id,))
        if cur.fetchone():
            return 0
        cur.execute("""
            INSERT INTO email_outreach_fila
                (lead_id, assunto, corpo_html, email_destino, nome_lead,
                 cidade, uf, lead_score, tem_ifood, metodo, template_id, gerado_por)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (lead_id, assunto, corpo_html, email_destino, nome_lead,
              cidade, uf, lead_score, tem_ifood, metodo, template_id, gerado_por))
        row = cur.fetchone()
        conn.commit()
        return row["id"] if row else 0


def listar_email_fila(status: str = "pendente", limite: int = 50) -> list:
    """Lista emails na fila de aprovação."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT f.*, l.rating, l.nome_fantasia as nome_fantasia_atual,
                   l.bairro
            FROM email_outreach_fila f
            JOIN leads l ON l.id = f.lead_id
            WHERE f.status = %s
            ORDER BY f.lead_score DESC, f.created_at DESC
            LIMIT %s
        """, (status, limite))
        return [dict(r) for r in cur.fetchall()]


def marcar_email_fila_enviado(fila_id: int) -> dict:
    """Marca email da fila como enviado. Retorna dados para envio real."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_outreach_fila
            SET status = 'enviado', enviado_at = NOW()
            WHERE id = %s AND status = 'pendente'
            RETURNING lead_id, assunto, corpo_html, email_destino, template_id
        """, (fila_id,))
        row = cur.fetchone()
        conn.commit()
        return dict(row) if row else {}


def descartar_email_fila(fila_id: int) -> bool:
    """Descarta email da fila."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_outreach_fila SET status = 'descartado'
            WHERE id = %s AND status = 'pendente' RETURNING id
        """, (fila_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def atualizar_email_fila(fila_id: int, assunto: str, corpo_html: str) -> bool:
    """Atualiza assunto/corpo de um email pendente (edição antes de enviar)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_outreach_fila SET assunto = %s, corpo_html = %s
            WHERE id = %s AND status = 'pendente' RETURNING id
        """, (assunto, corpo_html, fila_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def contar_email_fila_pendente() -> int:
    """Conta total de emails pendentes na fila."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as n FROM email_outreach_fila WHERE status = 'pendente'")
        return cur.fetchone()["n"]


def limpar_email_fila_expirados(dias: int = 7) -> int:
    """Marca como expirados emails pendentes com mais de N dias."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_outreach_fila SET status = 'expirado'
            WHERE status = 'pendente'
              AND created_at < NOW() - INTERVAL '%s days'
        """, (dias,))
        n = cur.rowcount
        conn.commit()
        return n


def conversas_wa_quentes(score_minimo: int = 80, limite: int = 50) -> list:
    """Conversas WA ativas com lead_score alto — candidatas a handoff.
    Usado pelo Brain Loop para monitorar e notificar dono.
    Retorna também campos de rastreio de notificação para evitar duplicar alerta."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.lead_id, c.numero_envio,
                   l.lead_score as intent_score,
                   c.intencao_detectada, c.status, c.updated_at,
                   c.handoff_notificado_em, c.handoff_notificado_score, c.handoff_notificado_tipo,
                   l.nome_fantasia, l.razao_social, l.cidade
            FROM wa_conversas c
            JOIN leads l ON l.id = c.lead_id
            WHERE c.status = 'ativo'
              AND l.lead_score >= %s
              AND l.lead_falso = FALSE
              AND l.opt_out_wa = FALSE
            ORDER BY l.lead_score DESC
            LIMIT %s
        """, (score_minimo, limite))
        return [dict(r) for r in cur.fetchall()]


def leads_para_outreach(cidade: str = None, uf: str = None,
                        score_min: int = 30, limite: int = 100) -> list:
    """Leads elegíveis para outreach: com email, sem opt_out, score >= min."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = [
            "l.opt_out_email = FALSE",
            "l.lead_falso = FALSE",
            "l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')",
            "l.email IS NOT NULL",
            "l.email != ''",
            "l.email_invalido = 0",
            "l.lead_score >= %s",
        ]
        params = [score_min]

        if cidade:
            where.append("l.cidade = %s")
            params.append(cidade.upper())
        if uf:
            where.append("l.uf = %s")
            params.append(uf.upper())

        # Excluir leads que já têm ação pendente ou executada recente (7 dias)
        where.append("""
            NOT EXISTS (
                SELECT 1 FROM outreach_sequencia o
                WHERE o.lead_id = l.id
                AND (o.cancelado = FALSE)
                AND (o.created_at >= NOW() - INTERVAL '7 days')
            )
        """)

        where_clause = " AND ".join(where)
        params.append(limite)

        cur.execute(f"""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.email, l.telefone1,
                   l.lead_score, l.segmento, l.tier,
                   l.rating, l.total_reviews,
                   l.tem_ifood, l.tem_rappi, l.tem_99food,
                   l.ifood_rating, l.ifood_reviews, l.ifood_preco,
                   l.ifood_categorias, l.ifood_tempo_entrega
            FROM leads l
            WHERE {where_clause}
            ORDER BY l.lead_score DESC
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def atualizar_tier_lead(lead_id: int, tier: str) -> bool:
    """Atualiza tier de um lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE leads SET tier = %s WHERE id = %s RETURNING id", (tier, lead_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


# ============================================================
# WHATSAPP — CONVERSAS E MENSAGENS
# ============================================================

def buscar_lead_por_telefone(numero: str) -> Optional[dict]:
    """Busca lead existente por número de telefone (qualquer campo).
    Normaliza número removendo +, espaços, hífens para comparação.
    Retorna dict com dados do lead ou None."""
    num_limpo = re.sub(r'\D', '', numero)
    if len(num_limpo) < 8:
        return None

    # Variantes de busca: com/sem prefixo 55, com/sem 9 extra
    variantes = {num_limpo}
    if num_limpo.startswith("55") and len(num_limpo) > 10:
        variantes.add(num_limpo[2:])  # sem 55
    else:
        variantes.add(f"55{num_limpo}")  # com 55

    with get_conn() as conn:
        cur = conn.cursor()
        for num in variantes:
            cur.execute("""
                SELECT * FROM leads
                WHERE REPLACE(REPLACE(REPLACE(COALESCE(telefone1,''), '-', ''), ' ', ''), '+', '') LIKE %s
                   OR REPLACE(REPLACE(REPLACE(COALESCE(telefone2,''), '-', ''), ' ', ''), '+', '') LIKE %s
                   OR REPLACE(REPLACE(REPLACE(COALESCE(telefone_proprietario,''), '-', ''), ' ', ''), '+', '') LIKE %s
                   OR REPLACE(REPLACE(REPLACE(COALESCE(telefone_maps,''), '-', ''), ' ', ''), '+', '') LIKE %s
                LIMIT 1
            """, (f"%{num[-8:]}",) * 4)
            row = cur.fetchone()
            if row:
                return dict(row)
    return None


def criar_lead_inbound(numero: str) -> int:
    """Cria ou vincula lead a partir de número WhatsApp inbound.
    PRIMEIRO busca por telefone no banco (lead existente).
    Se não encontrar, cria placeholder com CNPJ = 'WA_' + numero.
    Retorna lead_id."""
    # 1. Buscar lead existente por telefone
    lead_existente = buscar_lead_por_telefone(numero)
    if lead_existente:
        log.info(f"Lead existente encontrado para {numero}: #{lead_existente['id']} "
                 f"({lead_existente.get('nome_fantasia') or lead_existente.get('razao_social')})")
        return lead_existente["id"]

    # 2. Buscar por CNPJ placeholder (conversa anterior)
    cnpj_placeholder = f"WA_{numero}"[:14]
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM leads WHERE cnpj = %s", (cnpj_placeholder,))
        row = cur.fetchone()
        if row:
            return row["id"]

        # 3. Criar lead mínimo
        cur.execute("""
            INSERT INTO leads (cnpj, nome_fantasia, telefone1, status_pipeline, segmento, tier)
            VALUES (%s, %s, %s, 'novo', 'inbound_wa', 'hot')
            RETURNING id
        """, (cnpj_placeholder, f"WhatsApp {numero[-4:]}", numero))
        new_id = cur.fetchone()["id"]
        conn.commit()
        log.info(f"Novo lead inbound criado: #{new_id} para {numero}")
        return new_id


def criar_conversa_wa(lead_id: int, numero_envio: str,
                      tom: str = None, voz: str = None) -> int:
    """Cria conversa WA. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO wa_conversas (lead_id, numero_envio, tom_usado, voz_usada)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (lead_id, numero_envio, tom, voz))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def registrar_msg_wa(conversa_id: int, direcao: str, conteudo: str,
                     tipo: str = "texto", intencao: str = None,
                     grok: bool = False) -> int:
    """Registra mensagem em conversa WA. Atualiza contadores."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO wa_mensagens (conversa_id, direcao, conteudo, tipo, intencao, grok_resposta)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (conversa_id, direcao, conteudo, tipo, intencao, grok))
        msg_id = cur.fetchone()["id"]
        campo = "msgs_enviadas" if direcao == "enviada" else "msgs_recebidas"
        cur.execute(f"""
            UPDATE wa_conversas SET {campo} = {campo} + 1 WHERE id = %s
        """, (conversa_id,))
        conn.commit()
        return msg_id


def listar_conversas_wa(status: str = None, limite: int = 50) -> list:
    """Lista conversas WA com dados do lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = "WHERE 1=1"
        params = []
        if status:
            where += " AND c.status = %s"
            params.append(status)
        params.append(limite)
        cur.execute(f"""
            SELECT c.*, l.nome_fantasia, l.razao_social, l.cidade, l.uf, l.lead_score,
                   (SELECT conteudo FROM wa_mensagens WHERE conversa_id = c.id ORDER BY created_at DESC LIMIT 1) as ultima_msg
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            {where}
            ORDER BY c.updated_at DESC
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def obter_conversa_wa(conversa_id: int) -> Optional[dict]:
    """Retorna conversa com todas as mensagens."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.*, l.nome_fantasia, l.razao_social, l.cidade, l.uf,
                   l.lead_score, l.email, l.telefone1, l.rating, l.total_reviews
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            WHERE c.id = %s
        """, (conversa_id,))
        row = cur.fetchone()
        if not row:
            return None
        conv = dict(row)
        cur.execute("""
            SELECT * FROM wa_mensagens WHERE conversa_id = %s ORDER BY created_at
        """, (conversa_id,))
        conv["mensagens"] = [dict(r) for r in cur.fetchall()]
        return conv


def obter_conversa_wa_por_lead(lead_id: int) -> Optional[dict]:
    """Retorna última conversa ativa do lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id FROM wa_conversas
            WHERE lead_id = %s AND status = 'ativo'
            ORDER BY created_at DESC LIMIT 1
        """, (lead_id,))
        row = cur.fetchone()
        if row:
            return obter_conversa_wa(row["id"])
        return None


def atualizar_conversa_wa(conversa_id: int, **kwargs) -> bool:
    """Atualiza campos da conversa WA."""
    campos_validos = {"status", "intencao_detectada", "handoff_at", "handoff_motivo",
                      "voz_usada", "tom_usado", "usou_audio",
                      "cache_ids_usados", "intents_usadas",
                      "persona_detectada", "followup_handoff_etapa", "followup_handoff_at",
                      "notas",
                      "handoff_notificado_em", "handoff_notificado_score", "handoff_notificado_tipo"}
    sets = []
    params = []
    for k, v in kwargs.items():
        if k in campos_validos:
            sets.append(f"{k} = %s")
            params.append(v)
    if not sets:
        return False
    params.append(conversa_id)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE wa_conversas SET {', '.join(sets)} WHERE id = %s RETURNING id
        """, params)
        found = cur.fetchone() is not None
        conn.commit()
        return found


def stats_wa(periodo_dias: int = 7) -> dict:
    """Stats de WhatsApp do período."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) as total_conversas,
                COUNT(*) FILTER (WHERE msgs_recebidas > 0) as com_resposta,
                COUNT(*) FILTER (WHERE status = 'handoff') as handoffs,
                SUM(msgs_enviadas) as total_enviadas,
                SUM(msgs_recebidas) as total_recebidas
            FROM wa_conversas
            WHERE created_at >= NOW() - INTERVAL '%s days'
        """, (periodo_dias,))
        row = cur.fetchone()
        result = dict(row) if row else {}
        total = result.get("total_conversas", 0)
        result["response_rate"] = round(
            result.get("com_resposta", 0) / max(total, 1) * 100, 1)
        return result


# ============================================================
# AGENTE AUTÔNOMO — EXPERIMENTOS, DECISÕES, RELATÓRIOS
# ============================================================

def criar_experimento(variavel: str, variante_a: str, variante_b: str,
                      metrica_alvo: str) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agente_experimentos (variavel, variante_a, variante_b, metrica_alvo)
            VALUES (%s, %s, %s, %s) RETURNING id
        """, (variavel, variante_a, variante_b, metrica_alvo))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def registrar_resultado_experimento(exp_id: int, variante: str, sucesso: bool) -> bool:
    campo_amostras = "amostras_a" if variante == "a" else "amostras_b"
    campo_sucessos = "sucessos_a" if variante == "a" else "sucessos_b"
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"""
            UPDATE agente_experimentos
            SET {campo_amostras} = {campo_amostras} + 1
                {', ' + campo_sucessos + ' = ' + campo_sucessos + ' + 1' if sucesso else ''}
            WHERE id = %s RETURNING id
        """, (exp_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def obter_experimento_ativo(variavel: str) -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM agente_experimentos
            WHERE variavel = %s AND ativo = TRUE AND vencedor IS NULL
            ORDER BY created_at DESC LIMIT 1
        """, (variavel,))
        row = cur.fetchone()
        return dict(row) if row else None


def listar_experimentos(ativo: bool = True) -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        if ativo:
            cur.execute("SELECT * FROM agente_experimentos WHERE ativo = TRUE ORDER BY created_at DESC")
        else:
            cur.execute("SELECT * FROM agente_experimentos ORDER BY created_at DESC LIMIT 50")
        return [dict(r) for r in cur.fetchall()]


def declarar_vencedor(exp_id: int, vencedor: str, confianca_pct: float) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE agente_experimentos
            SET vencedor = %s, confianca_pct = %s, decidido_at = NOW()
            WHERE id = %s RETURNING id
        """, (vencedor, confianca_pct, exp_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def criar_decisao(tipo: str, descricao: str, dados: dict = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agente_decisoes (tipo, descricao, dados)
            VALUES (%s, %s, %s) RETURNING id
        """, (tipo, descricao, json.dumps(dados) if dados else None))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def listar_decisoes_pendentes(limite: int = 100) -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM agente_decisoes
            WHERE aprovado IS NULL
            ORDER BY created_at DESC LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def aprovar_decisao(decisao_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE agente_decisoes SET aprovado = TRUE, aprovado_at = NOW()
            WHERE id = %s RETURNING id
        """, (decisao_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def rejeitar_decisao(decisao_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE agente_decisoes SET aprovado = FALSE, aprovado_at = NOW()
            WHERE id = %s RETURNING id
        """, (decisao_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def criar_relatorio(periodo_inicio, periodo_fim, metricas: dict,
                    descobertas: list = None, recomendacoes: list = None,
                    resumo: str = None) -> int:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agente_relatorios
                (periodo_inicio, periodo_fim, metricas, descobertas, recomendacoes, resumo_texto)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (periodo_inicio, periodo_fim,
              json.dumps(metricas),
              json.dumps(descobertas) if descobertas else None,
              json.dumps(recomendacoes) if recomendacoes else None,
              resumo))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def obter_ultimo_relatorio() -> Optional[dict]:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM agente_relatorios ORDER BY created_at DESC LIMIT 1")
        row = cur.fetchone()
        return dict(row) if row else None


def metricas_outreach_periodo(inicio, fim) -> dict:
    """Métricas agregadas de outreach para um período."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                COUNT(*) as emails_enviados,
                COUNT(*) FILTER (WHERE aberto = TRUE) as emails_abertos,
                COUNT(*) FILTER (WHERE clicou_site OR clicou_wa) as emails_clicados,
                COUNT(*) FILTER (WHERE bounced) as emails_bounced,
                COUNT(*) FILTER (WHERE clicou_unsub) as emails_unsub
            FROM emails_enviados
            WHERE horario_enviado BETWEEN %s AND %s
        """, (inicio, fim))
        email_stats = dict(cur.fetchone())

        cur.execute("""
            SELECT
                COUNT(*) as wa_conversas,
                COUNT(*) FILTER (WHERE msgs_recebidas > 0) as wa_com_resposta,
                COUNT(*) FILTER (WHERE status = 'handoff') as wa_handoffs
            FROM wa_conversas
            WHERE created_at BETWEEN %s AND %s
        """, (inicio, fim))
        wa_stats = dict(cur.fetchone())

        email_stats.update(wa_stats)
        env = email_stats.get("emails_enviados", 0)
        email_stats["open_rate"] = round(email_stats.get("emails_abertos", 0) / max(env, 1) * 100, 1)
        email_stats["ctr"] = round(email_stats.get("emails_clicados", 0) / max(env, 1) * 100, 1)
        wa_total = email_stats.get("wa_conversas", 0)
        email_stats["wa_response_rate"] = round(
            email_stats.get("wa_com_resposta", 0) / max(wa_total, 1) * 100, 1)
        return email_stats


# ============================================================
# AUTOPILOT — MÉTRICAS CONSOLIDADAS
# ============================================================

def autopilot_metricas() -> dict:
    """Métricas consolidadas para o painel do Sales Autopilot."""
    with get_conn() as conn:
        cur = conn.cursor()

        # KPIs de leads
        cur.execute("SELECT COUNT(*) as total FROM leads")
        total_leads = cur.fetchone()["total"]

        # Emails (7 dias)
        cur.execute("""
            SELECT
                COUNT(*) as enviados,
                COUNT(*) FILTER (WHERE aberto = TRUE) as abertos,
                COUNT(*) FILTER (WHERE clicou_site OR clicou_wa) as clicados,
                COUNT(*) FILTER (WHERE bounced) as bounced
            FROM emails_enviados
            WHERE horario_enviado >= NOW() - INTERVAL '7 days'
        """)
        emails = dict(cur.fetchone())

        # Emails hoje
        cur.execute("""
            SELECT COUNT(*) as total FROM emails_enviados
            WHERE horario_enviado >= CURRENT_DATE
        """)
        emails_hoje = cur.fetchone()["total"]

        # WA (7 dias)
        cur.execute("""
            SELECT
                COUNT(*) as conversas,
                COUNT(*) FILTER (WHERE msgs_recebidas > 0) as com_resposta,
                COUNT(*) FILTER (WHERE status = 'handoff') as handoffs,
                COALESCE(SUM(msgs_enviadas), 0) as enviadas,
                COALESCE(SUM(msgs_recebidas), 0) as recebidas
            FROM wa_conversas
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        wa = dict(cur.fetchone())

        # Demos e clientes
        cur.execute("""
            SELECT
                COUNT(*) FILTER (WHERE status_pipeline = 'demo_agendada') as demos,
                COUNT(*) FILTER (WHERE status_pipeline = 'cliente') as clientes
            FROM leads
        """)
        pipeline = dict(cur.fetchone())

        # Decisões do agente
        cur.execute("SELECT COUNT(*) as total FROM agente_decisoes")
        total_decisoes = cur.fetchone()["total"]

        # Dias ativo (desde primeiro relatório)
        cur.execute("SELECT MIN(created_at) as inicio FROM agente_relatorios")
        inicio = cur.fetchone()["inicio"]
        dias_ativo = 0
        if inicio:
            from datetime import datetime
            dias_ativo = max(1, (datetime.now(inicio.tzinfo) - inicio).days)

        env = emails.get("enviados", 0) or 1
        return {
            "total_leads": total_leads,
            "emails_enviados_7d": emails.get("enviados", 0),
            "emails_abertos_7d": emails.get("abertos", 0),
            "taxa_abertura": round(emails.get("abertos", 0) / env * 100, 1),
            "emails_clicados_7d": emails.get("clicados", 0),
            "taxa_clique": round(emails.get("clicados", 0) / env * 100, 1),
            "taxa_bounce": round(emails.get("bounced", 0) / env * 100, 1),
            "emails_hoje": emails_hoje,
            "wa_enviados_7d": wa.get("enviadas", 0),
            "wa_respondidos_7d": wa.get("com_resposta", 0),
            "taxa_resposta_wa": round(wa.get("com_resposta", 0) / max(wa.get("conversas", 0), 1) * 100, 1),
            "demos": pipeline.get("demos", 0),
            "clientes": pipeline.get("clientes", 0),
            "receita": pipeline.get("clientes", 0) * 149,  # MRR estimado
            "custo": 0,  # Créditos xAI grátis
            "total_decisoes": total_decisoes,
            "dias_ativo": dias_ativo or 1,
            "gasto_voz": 0,  # TODO: rastrear gastos TTS
        }


def autopilot_funil() -> list:
    """Dados do funil de conversão para o autopilot."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM leads")
        total = cur.fetchone()["total"] or 1

        cur.execute("""
            SELECT COUNT(*) as n FROM emails_enviados
            WHERE horario_enviado >= NOW() - INTERVAL '30 days'
        """)
        emails = cur.fetchone()["n"]

        cur.execute("""
            SELECT COUNT(*) as n FROM emails_enviados
            WHERE aberto = TRUE AND horario_enviado >= NOW() - INTERVAL '30 days'
        """)
        abriu = cur.fetchone()["n"]

        cur.execute("""
            SELECT COUNT(*) as n FROM emails_enviados
            WHERE (clicou_site OR clicou_wa) AND horario_enviado >= NOW() - INTERVAL '30 days'
        """)
        clicou = cur.fetchone()["n"]

        cur.execute("""
            SELECT COUNT(*) as n FROM wa_conversas
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        wa = cur.fetchone()["n"]

        cur.execute("""
            SELECT COUNT(*) as n FROM wa_conversas
            WHERE msgs_recebidas > 0 AND created_at >= NOW() - INTERVAL '30 days'
        """)
        respondeu = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM leads WHERE status_pipeline = 'demo_agendada'")
        demos = cur.fetchone()["n"]

        cur.execute("SELECT COUNT(*) as n FROM leads WHERE status_pipeline = 'cliente'")
        fechou = cur.fetchone()["n"]

        etapas = [
            {"estagio": "Leads", "numero": total},
            {"estagio": "Email", "numero": emails},
            {"estagio": "Abriu", "numero": abriu},
            {"estagio": "Clicou", "numero": clicou},
            {"estagio": "WA", "numero": wa},
            {"estagio": "Respondeu", "numero": respondeu},
            {"estagio": "Demo", "numero": demos},
            {"estagio": "Fechou", "numero": fechou},
        ]

        for e in etapas:
            e["pct"] = round(e["numero"] / total * 100, 1) if total else 0

        return etapas


def autopilot_config() -> dict:
    """Configurações aprendidas pelo agente (da tabela configuracoes)."""
    defaults = {
        "horario_envio": "18:00-20:00",
        "tom_conversa": "Consultivo",
        "voz_audio": "Ara",
        "momento_audio": "1ª mensagem",
        "recontato": "D+2",
        "aquecimento_diario": "35",
        "nota_minima_wa": "60",
        "limite_emails_dia": "100",
        "limite_gasto_voz": "5",
    }
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT chave, valor FROM configuracoes")
        rows = cur.fetchall()
        for row in rows:
            k = row["chave"]
            if k in defaults:
                defaults[k] = row["valor"]
    return defaults


def autopilot_decisoes_recentes(limite: int = 10) -> list:
    """Decisões autônomas recentes do agente."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tipo, descricao, dados, aprovado, created_at
            FROM agente_decisoes
            ORDER BY created_at DESC LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def autopilot_leads_quentes(limite: int = 10) -> list:
    """Top leads por score com último evento."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, COALESCE(l.nome_fantasia, l.razao_social, 'Lead') as nome,
                   l.lead_score as score, l.cidade, l.uf, l.status_pipeline,
                   (SELECT conteudo FROM interacoes WHERE lead_id = l.id ORDER BY created_at DESC LIMIT 1) as ultimo_evento
            FROM leads l
            WHERE l.lead_score >= 60
              AND l.status_pipeline NOT IN ('perdido', 'cliente', 'lead_falso')
            ORDER BY l.lead_score DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def autopilot_conversas_formatadas(limite: int = 30) -> list:
    """Conversas WA formatadas para o autopilot."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.status, c.msgs_enviadas, c.msgs_recebidas,
                   c.intencao_detectada, c.handoff_at, c.voz_usada,
                   c.created_at, c.updated_at,
                   COALESCE(l.nome_fantasia, l.razao_social, 'Lead') as lead_nome,
                   l.lead_score as score, l.cidade, l.uf,
                   (SELECT conteudo FROM wa_mensagens WHERE conversa_id = c.id ORDER BY created_at DESC LIMIT 1) as preview
            FROM wa_conversas c
            JOIN leads l ON c.lead_id = l.id
            ORDER BY c.updated_at DESC
            LIMIT %s
        """, (limite,))
        result = []
        for r in cur.fetchall():
            d = dict(r)
            # Determinar situacao
            if d.get("handoff_at"):
                d["situacao"] = "demo_agendada"
            elif d.get("intencao_detectada") == "interesse":
                d["situacao"] = "engajado"
            elif d.get("msgs_recebidas", 0) > 0:
                d["situacao"] = "respondeu"
            elif d.get("msgs_enviadas", 0) > 0:
                d["situacao"] = "WA enviado"
            else:
                d["situacao"] = "sem resposta"
            # Modo e canal
            d["modo"] = "manual" if d.get("handoff_at") else "auto"
            d["canal"] = "whatsapp"
            d["nova_msg"] = (d.get("msgs_recebidas", 0) > 0 and
                             d.get("status") == "ativo")
            # Preview
            d["preview"] = (d.get("preview") or "")[:50]
            result.append(d)
        return result


def autopilot_conversa_detalhe(conversa_id: int) -> Optional[dict]:
    """Detalhe de conversa formatado para o autopilot."""
    conv = obter_conversa_wa(conversa_id)
    if not conv:
        return None

    # Formatar para o autopilot
    resultado = {
        "id": conv["id"],
        "lead_nome": conv.get("nome_fantasia") or conv.get("razao_social") or "Lead",
        "score": conv.get("lead_score", 0),
        "situacao": "ativa",
        "modo": "manual" if conv.get("handoff_at") else "auto",
        "status": conv.get("status", "ativo"),
        "mensagens": [],
    }

    for m in conv.get("mensagens", []):
        msg = {
            "conteudo": m.get("conteudo", ""),
            "hora": str(m.get("created_at", ""))[:16].replace("T", " ") if m.get("created_at") else "",
        }
        tipo_msg = m.get("tipo", "texto")
        direcao = m.get("direcao", "enviada")

        if tipo_msg == "audio":
            msg["tipo"] = "audio"
            msg["duracao"] = 28
            msg["voz"] = conv.get("voz_usada", "Ara")
        elif direcao == "recebida":
            msg["tipo"] = "lead"
        elif m.get("grok_resposta"):
            msg["tipo"] = "bot"
        else:
            msg["tipo"] = "bot"

        resultado["mensagens"].append(msg)

    return resultado


def leads_com_mais_dados(cidade: str = None, limite: int = 50) -> list:
    """Retorna leads com mais dados disponíveis (para geração de emails com concorrentes).
    Prioriza: tem iFood + Maps + RF + contato."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = "WHERE l.status_pipeline NOT IN ('perdido', 'cliente', 'lead_falso')"
        params = []
        if cidade:
            where += " AND l.cidade = %s"
            params.append(cidade)
        params.append(limite)
        cur.execute(f"""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.bairro,
                   l.rating, l.total_reviews, l.lead_score,
                   l.tem_ifood, l.tem_rappi, l.tem_99food,
                   l.ifood_rating, l.ifood_reviews, l.ifood_preco,
                   l.ifood_categorias, l.email, l.telefone1,
                   l.capital_social, l.porte,
                   -- Score de completude dos dados
                   (CASE WHEN l.rating IS NOT NULL THEN 1 ELSE 0 END
                    + CASE WHEN l.ifood_rating IS NOT NULL THEN 2 ELSE 0 END
                    + CASE WHEN l.email IS NOT NULL AND l.email != '' THEN 1 ELSE 0 END
                    + CASE WHEN l.telefone1 IS NOT NULL AND l.telefone1 != '' THEN 1 ELSE 0 END
                    + CASE WHEN l.capital_social > 0 THEN 1 ELSE 0 END
                    + CASE WHEN l.total_reviews > 0 THEN 1 ELSE 0 END
                    + CASE WHEN l.ifood_reviews > 0 THEN 1 ELSE 0 END
                   ) as completude
            FROM leads l
            {where}
            ORDER BY completude DESC, l.lead_score DESC
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def concorrentes_do_lead(lead_id: int, limite: int = 5) -> list:
    """Encontra concorrentes diretos de um lead (mesmo bairro/cidade, com dados).
    Prioriza: mesmo bairro > mesma cidade, com dados iFood/Maps."""
    with get_conn() as conn:
        cur = conn.cursor()
        # Pegar dados do lead alvo
        cur.execute("""
            SELECT id, cidade, uf, bairro, ifood_categorias
            FROM leads WHERE id = %s
        """, (lead_id,))
        lead = cur.fetchone()
        if not lead:
            return []

        cidade = lead["cidade"]
        bairro = lead["bairro"]
        categorias = lead["ifood_categorias"]

        params = [lead_id, cidade]
        order_parts = []

        # Priorizar mesmo bairro
        if bairro:
            order_parts.append("(CASE WHEN l.bairro = %s THEN 0 ELSE 1 END)")
            params.append(bairro)

        # Priorizar mesma categoria iFood
        if categorias:
            cat_principal = categorias.split(",")[0].strip()
            if cat_principal:
                order_parts.append("(CASE WHEN l.ifood_categorias ILIKE %s THEN 0 ELSE 1 END)")
                params.append(f"%{cat_principal}%")

        order_clause = ", ".join(order_parts) + ", " if order_parts else ""
        params.append(limite)

        cur.execute(f"""
            SELECT l.id, COALESCE(l.nome_fantasia, l.razao_social) as nome,
                   l.bairro, l.rating, l.total_reviews,
                   l.tem_ifood, l.ifood_rating, l.ifood_reviews,
                   l.ifood_preco, l.ifood_categorias,
                   l.tem_rappi, l.tem_99food
            FROM leads l
            WHERE l.id != %s
              AND l.cidade = %s
              AND (l.rating IS NOT NULL OR l.ifood_rating IS NOT NULL)
              AND l.status_pipeline != 'perdido'
            ORDER BY {order_clause}
                     COALESCE(l.ifood_rating, 0) DESC,
                     COALESCE(l.rating, 0) DESC
            LIMIT %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


# ============================================================
# EMAIL INBOX — Threads + Mensagens recebidas/enviadas
# ============================================================

def auto_categorizar_email(email_remetente: str) -> tuple:
    """Categoriza email automaticamente.
    Retorna (categoria, lead_id).
    - urgente: já tem thread com resposta enviada
    - cliente: email existe na tabela leads
    - desconhecido: sem referência
    """
    email_lower = email_remetente.lower().strip()
    with get_conn() as conn:
        cur = conn.cursor()

        # 1. Verificar se já tem thread com resposta nossa (urgente)
        cur.execute("""
            SELECT t.id, t.lead_id FROM email_threads t
            WHERE LOWER(t.email_remetente) = %s
            AND EXISTS (
                SELECT 1 FROM emails_inbox ei
                WHERE ei.thread_id = t.id AND ei.direcao = 'enviado'
            )
            ORDER BY t.ultima_mensagem_at DESC LIMIT 1
        """, (email_lower,))
        row = cur.fetchone()
        if row:
            return ("urgente", row.get("lead_id"))

        # 2. Verificar se é um lead conhecido (cliente)
        cur.execute("""
            SELECT id FROM leads
            WHERE LOWER(email) = %s
               OR LOWER(email_proprietario) = %s
            LIMIT 1
        """, (email_lower, email_lower))
        lead = cur.fetchone()
        if lead:
            return ("cliente", lead["id"])

        # 3. Desconhecido
        return ("desconhecido", None)


def buscar_thread_por_email_e_assunto(email_remetente: str, assunto: str) -> Optional[dict]:
    """Busca thread existente pelo remetente + assunto similar (para agrupar)."""
    email_lower = email_remetente.lower().strip()
    # Normalizar assunto (remover Re:, Fwd:, etc.)
    assunto_limpo = assunto or ""
    for prefix in ["re:", "fwd:", "fw:", "enc:", "res:"]:
        while assunto_limpo.lower().startswith(prefix):
            assunto_limpo = assunto_limpo[len(prefix):].strip()

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM email_threads
            WHERE LOWER(email_remetente) = %s
            AND (
                assunto = %s
                OR assunto = %s
                OR assunto ILIKE %s
            )
            AND arquivado = FALSE
            ORDER BY ultima_mensagem_at DESC LIMIT 1
        """, (email_lower, assunto, assunto_limpo, f"%{assunto_limpo}%"))
        row = cur.fetchone()
        return dict(row) if row else None


def criar_email_thread(assunto: str, email_remetente: str,
                       nome_remetente: str = None,
                       categoria: str = "desconhecido",
                       lead_id: int = None) -> int:
    """Cria nova thread de email. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO email_threads
                (assunto, email_remetente, nome_remetente, categoria, lead_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (assunto, email_remetente.lower().strip(),
              nome_remetente, categoria, lead_id))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def criar_email_inbox(thread_id: int, direcao: str,
                      de_email: str, de_nome: str,
                      para_email: str, assunto: str,
                      corpo_html: str = None, corpo_texto: str = None,
                      resend_email_id: str = None,
                      anexos_json: list = None) -> int:
    """Insere email na inbox (recebido ou enviado). Atualiza thread."""
    tem_anexos = bool(anexos_json)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO emails_inbox
                (thread_id, direcao, de_email, de_nome, para_email,
                 assunto, corpo_html, corpo_texto, resend_email_id,
                 tem_anexos, anexos_json)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (thread_id, direcao, de_email, de_nome, para_email,
              assunto, corpo_html, corpo_texto, resend_email_id,
              tem_anexos, json.dumps(anexos_json) if anexos_json else None))
        msg_id = cur.fetchone()["id"]

        # Atualizar thread
        cur.execute("""
            UPDATE email_threads
            SET ultima_mensagem_at = NOW(),
                total_mensagens = total_mensagens + 1,
                lido = CASE WHEN %s = 'recebido' THEN FALSE ELSE lido END
            WHERE id = %s
        """, (direcao, thread_id))
        conn.commit()
        return msg_id


def listar_email_threads(categoria: str = None, lido: bool = None,
                         arquivado: bool = False, busca: str = None,
                         limite: int = 50, offset: int = 0) -> list:
    """Lista threads de email com filtros."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = ["t.arquivado = %s"]
        params = [arquivado]

        if categoria:
            where.append("t.categoria = %s")
            params.append(categoria)
        if lido is not None:
            where.append("t.lido = %s")
            params.append(lido)
        if busca:
            where.append("""
                (t.assunto ILIKE %s
                 OR t.email_remetente ILIKE %s
                 OR t.nome_remetente ILIKE %s)
            """)
            termo = f"%{busca}%"
            params.extend([termo, termo, termo])

        where_clause = " AND ".join(where)
        params.extend([limite, offset])

        cur.execute(f"""
            SELECT t.*,
                   l.nome_fantasia as lead_nome,
                   l.razao_social as lead_razao,
                   (SELECT corpo_texto FROM emails_inbox
                    WHERE thread_id = t.id
                    ORDER BY created_at DESC LIMIT 1) as preview
            FROM email_threads t
            LEFT JOIN leads l ON t.lead_id = l.id
            WHERE {where_clause}
            ORDER BY t.starred DESC, t.ultima_mensagem_at DESC
            LIMIT %s OFFSET %s
        """, params)
        return [dict(r) for r in cur.fetchall()]


def obter_email_thread(thread_id: int) -> Optional[dict]:
    """Retorna thread com todas as mensagens."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.*,
                   l.nome_fantasia as lead_nome,
                   l.razao_social as lead_razao,
                   l.cidade as lead_cidade,
                   l.uf as lead_uf,
                   l.lead_score,
                   l.telefone1 as lead_telefone
            FROM email_threads t
            LEFT JOIN leads l ON t.lead_id = l.id
            WHERE t.id = %s
        """, (thread_id,))
        row = cur.fetchone()
        if not row:
            return None
        thread = dict(row)

        cur.execute("""
            SELECT * FROM emails_inbox
            WHERE thread_id = %s
            ORDER BY created_at ASC
        """, (thread_id,))
        thread["mensagens"] = [dict(r) for r in cur.fetchall()]
        return thread


def marcar_thread_lida(thread_id: int) -> bool:
    """Marca thread como lida."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_threads SET lido = TRUE WHERE id = %s RETURNING id
        """, (thread_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def marcar_thread_starred(thread_id: int, starred: bool = True) -> bool:
    """Marca/desmarca thread como favorita."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_threads SET starred = %s WHERE id = %s RETURNING id
        """, (starred, thread_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def arquivar_thread(thread_id: int) -> bool:
    """Arquiva thread."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_threads SET arquivado = TRUE WHERE id = %s RETURNING id
        """, (thread_id,))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def categorizar_thread(thread_id: int, categoria: str) -> bool:
    """Altera categoria de uma thread."""
    if categoria not in ("urgente", "cliente", "desconhecido"):
        return False
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE email_threads SET categoria = %s WHERE id = %s RETURNING id
        """, (categoria, thread_id))
        found = cur.fetchone() is not None
        conn.commit()
        return found


def contar_threads_por_categoria() -> dict:
    """Conta threads não-lidas por categoria."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT categoria,
                   COUNT(*) as total,
                   COUNT(*) FILTER (WHERE lido = FALSE) as nao_lidas
            FROM email_threads
            WHERE arquivado = FALSE
            GROUP BY categoria
        """)
        result = {"urgente": {"total": 0, "nao_lidas": 0},
                  "cliente": {"total": 0, "nao_lidas": 0},
                  "desconhecido": {"total": 0, "nao_lidas": 0}}
        for row in cur.fetchall():
            cat = row["categoria"]
            if cat in result:
                result[cat] = {"total": row["total"], "nao_lidas": row["nao_lidas"]}
        return result


# ============================================================
# QUIZ DIAGNÓSTICO — INBOUND LANDING PAGE
# ============================================================

def criar_lead_quiz(dados: dict) -> int:
    """Cria lead a partir do quiz diagnóstico da landing page.
    Usa cnpj placeholder QZ_+whatsapp. Retorna lead_id."""
    whatsapp = dados["whatsapp"]
    cnpj_placeholder = f"QZ_{whatsapp}"[:14]

    with get_conn() as conn:
        cur = conn.cursor()

        # Verificar duplicata por cnpj ou telefone1
        cur.execute(
            "SELECT id FROM leads WHERE cnpj = %s OR telefone1 = %s",
            (cnpj_placeholder, whatsapp)
        )
        row = cur.fetchone()
        if row:
            # Atualizar notas com dados do quiz
            notas_json = json.dumps({
                "quiz_tipo": dados.get("tipo_restaurante"),
                "quiz_pedidos_dia": dados.get("pedidos_dia"),
                "quiz_respostas": dados.get("respostas"),
                "quiz_diagnostico": dados.get("diagnostico"),
                "quiz_nome_contato": dados.get("nome"),
                "quiz_email": dados.get("email"),
            }, ensure_ascii=False)
            cur.execute(
                "UPDATE leads SET notas = %s WHERE id = %s",
                (notas_json, row["id"])
            )
            conn.commit()
            return row["id"]

        # Novo lead
        notas_json = json.dumps({
            "quiz_tipo": dados.get("tipo_restaurante"),
            "quiz_pedidos_dia": dados.get("pedidos_dia"),
            "quiz_respostas": dados.get("respostas"),
            "quiz_diagnostico": dados.get("diagnostico"),
            "quiz_nome_contato": dados.get("nome"),
            "quiz_email": dados.get("email"),
        }, ensure_ascii=False)

        cur.execute("""
            INSERT INTO leads (
                cnpj, nome_fantasia, telefone1, email,
                status_pipeline, segmento, tier, lead_score, notas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            cnpj_placeholder,
            dados.get("nome_restaurante") or f"Quiz {whatsapp[-4:]}",
            whatsapp,
            dados.get("email") or None,
            "contactado",
            "inbound_quiz",
            "hot",
            85,
            notas_json,
        ))
        new_id = cur.fetchone()["id"]

        # Registrar interação
        cur.execute("""
            INSERT INTO interacoes (lead_id, tipo, canal, conteudo, resultado)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            new_id, "inbound", "quiz",
            f"Quiz diagnóstico: {dados.get('tipo_restaurante')} - {dados.get('pedidos_dia')} pedidos/dia",
            "lead_criado",
        ))

        conn.commit()
        return new_id


# ============================================================
# SYNC API — Upsert batch de leads (scraper remoto → CRM)
# ============================================================

# Colunas permitidas no sync (whitelist)
_SYNC_COLUNAS_PERMITIDAS = {
    "cnpj", "razao_social", "nome_fantasia", "logradouro", "numero",
    "complemento", "bairro", "cidade", "uf", "cep",
    "telefone1", "telefone2", "email", "cnae_principal", "data_abertura",
    "situacao_cadastral", "tipo_empresa", "tipo_negocio", "capital_social",
    "porte", "natureza_juridica", "simples", "mei", "data_opcao_simples",
    "telefone_proprietario", "email_proprietario", "socios_json",
    "tem_ifood", "nome_ifood", "url_ifood",
    "ifood_rating", "ifood_reviews", "ifood_preco",
    "ifood_categorias", "ifood_tempo_entrega", "ifood_aberto",
    "tem_rappi", "nome_rappi", "url_rappi",
    "tem_99food", "nome_99food", "url_99food",
    "multi_restaurante", "matched", "detalhado", "score_match",
    "nome_maps", "endereco_maps", "telefone_maps",
    "website", "rating", "total_reviews", "google_maps_url", "categoria",
}

# Campos CRM protegidos — NUNCA sobrescrever via sync
_SYNC_PROTEGIDOS = {
    "id", "lead_score", "segmento", "status_pipeline",
    "motivo_perda", "notas", "data_ultimo_contato",
    "data_proximo_contato", "email_invalido",
    "opt_out_email", "opt_out_wa", "opt_out_at", "tier",
    "created_at",
}

_SYNC_CAMPOS_INT = {"tem_ifood", "tem_rappi", "tem_99food", "multi_restaurante",
                     "ifood_reviews", "total_reviews", "matched", "detalhado",
                     "ifood_aberto"}
_SYNC_CAMPOS_FLOAT = {"capital_social", "rating", "ifood_rating", "score_match"}


def _sync_safe_int(val):
    if val is None:
        return None
    try:
        return int(float(str(val).strip().replace(",", ".")))
    except (ValueError, TypeError):
        return None


def _sync_safe_float(val):
    if val is None:
        return None
    try:
        return float(str(val).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


## ============================================================
# P2-P5: CRM TRUE AUTO SALES — NOVAS QUERIES
# ============================================================

# --- P2: Funil Completo ---

def marcar_trial_link_enviado(lead_id: int):
    """Marca que o trial link foi enviado ao lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET trial_link_enviado_at = NOW() WHERE id = %s
        """, (lead_id,))
        conn.commit()


def conversas_handoff_sem_resposta(horas: int = 24, limite: int = 50) -> list:
    """Conversas em status 'handoff' sem resposta do humano há N horas.
    Usadas para follow-up automático pós-handoff."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.lead_id, c.numero_envio, c.handoff_at,
                   c.followup_handoff_etapa, c.followup_handoff_at,
                   l.nome_fantasia, l.razao_social, l.email, l.lead_score,
                   l.trial_link_enviado_at
            FROM wa_conversas c
            JOIN leads l ON l.id = c.lead_id
            WHERE c.status = 'handoff'
              AND c.handoff_at IS NOT NULL
              AND c.handoff_at <= NOW() - INTERVAL '%s hours'
              AND COALESCE(c.followup_handoff_etapa, 0) < 3
              AND l.opt_out_wa = FALSE
              AND l.lead_falso = FALSE
            ORDER BY c.handoff_at ASC
            LIMIT %s
        """, (horas, limite))
        return [dict(r) for r in cur.fetchall()]


def registrar_followup_handoff(conversa_id: int, etapa: int):
    """Registra etapa de follow-up pós-handoff (1=D+1, 2=D+3, 3=D+7)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE wa_conversas
            SET followup_handoff_etapa = %s, followup_handoff_at = NOW()
            WHERE id = %s
        """, (etapa, conversa_id))
        conn.commit()


# --- P3: Brain Loop Inteligente ---

def leads_para_reengajamento(limite: int = 10) -> list:
    """Leads frios com potencial para reengajamento.
    Critérios: score > 40, tem contato, sem opt-out, sem contato há 30+ dias,
    sem reengajamento recente (30+ dias)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.email, l.telefone1,
                   l.lead_score, l.segmento, l.tier,
                   l.data_ultimo_contato, l.ultimo_reengajamento_at,
                   l.wa_existe
            FROM leads l
            WHERE l.lead_score > 40
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
              AND l.opt_out_email = FALSE AND l.opt_out_wa = FALSE
              AND (l.email IS NOT NULL AND l.email != '' OR l.telefone1 IS NOT NULL AND l.telefone1 != '')
              AND (l.data_ultimo_contato IS NULL OR l.data_ultimo_contato <= NOW() - INTERVAL '30 days')
              AND (l.ultimo_reengajamento_at IS NULL OR l.ultimo_reengajamento_at <= NOW() - INTERVAL '30 days')
              AND NOT EXISTS (
                  SELECT 1 FROM outreach_sequencia o
                  WHERE o.lead_id = l.id AND o.cancelado = FALSE
                  AND o.created_at >= NOW() - INTERVAL '14 days'
              )
            ORDER BY l.lead_score DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def marcar_reengajamento(lead_id: int):
    """Marca que o lead foi reengajado."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET ultimo_reengajamento_at = NOW() WHERE id = %s
        """, (lead_id,))
        conn.commit()


def leads_para_desistencia(max_tentativas: int = 5) -> list:
    """Leads com N+ tentativas de outreach (WA + email) sem nenhuma resposta.
    Candidatos a 'frio_permanente'. Exclui opt-out (já optaram por sair)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.nome_fantasia, l.lead_score, l.status_pipeline,
                   COUNT(o.id) as total_tentativas
            FROM leads l
            JOIN outreach_sequencia o ON o.lead_id = l.id
            WHERE o.executado = TRUE
              AND o.resultado IN ('enviado', 'erro')
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso', 'respondeu', 'demo_agendada')
              AND l.lead_falso = FALSE
              AND l.opt_out_wa = FALSE
              AND l.opt_out_email = FALSE
              AND NOT EXISTS (
                  SELECT 1 FROM wa_conversas wc
                  WHERE wc.lead_id = l.id AND wc.msgs_recebidas > 0
              )
              AND NOT EXISTS (
                  SELECT 1 FROM emails_enviados ee
                  WHERE ee.lead_id = l.id AND (ee.aberto = TRUE OR ee.clicou_site = TRUE)
              )
            GROUP BY l.id, l.nome_fantasia, l.lead_score, l.status_pipeline
            HAVING COUNT(o.id) >= %s
            ORDER BY COUNT(o.id) DESC
            LIMIT 50
        """, (max_tentativas,))
        return [dict(r) for r in cur.fetchall()]


def stats_horario_resposta(cidade: str = None, uf: str = None) -> dict:
    """Agregação de respostas WA por hora do dia (para horário ótimo)."""
    with get_conn() as conn:
        cur = conn.cursor()
        where_extra = ""
        params = []
        if cidade:
            where_extra += " AND l.cidade = %s"
            params.append(cidade)
        if uf:
            where_extra += " AND l.uf = %s"
            params.append(uf)
        cur.execute(f"""
            SELECT EXTRACT(HOUR FROM wm.created_at)::int as hora, COUNT(*) as total
            FROM wa_mensagens wm
            JOIN wa_conversas wc ON wm.conversa_id = wc.id
            JOIN leads l ON wc.lead_id = l.id
            WHERE wm.direcao = 'recebida'
              AND wm.created_at >= NOW() - INTERVAL '30 days'
              {where_extra}
            GROUP BY hora ORDER BY hora
        """, params)
        return {r["hora"]: r["total"] for r in cur.fetchall()}


# --- P4: Event-Driven Scoring ---

def registrar_evento_lead(lead_id: int, evento: str, valor: int = 0,
                           score_antes: int = None, score_depois: int = None,
                           metadata: dict = None) -> int:
    """Registra evento no histórico de scoring do lead. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        import json as _json
        cur.execute("""
            INSERT INTO lead_eventos (lead_id, evento, valor, score_antes, score_depois, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (lead_id, evento, valor, score_antes, score_depois,
              _json.dumps(metadata) if metadata else None))
        new_id = cur.fetchone()["id"]
        conn.commit()
        return new_id


def leads_sem_interacao_recente(dias: int = 7) -> list:
    """Leads com updated_at > N dias sem interação — para score decay."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.lead_score, l.tier, l.segmento
            FROM leads l
            WHERE l.lead_score > 10
              AND l.status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
              AND (l.data_ultimo_contato IS NULL OR l.data_ultimo_contato < NOW() - INTERVAL '%s days')
              AND NOT EXISTS (
                  SELECT 1 FROM lead_eventos le
                  WHERE le.lead_id = l.id AND le.created_at >= NOW() - INTERVAL '%s days'
              )
            ORDER BY l.id
        """, (dias, dias))
        return [dict(r) for r in cur.fetchall()]


def atualizar_score_lead(lead_id: int, score: int, tier: str):
    """Atualiza score e tier de um lead."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET lead_score = %s, tier = %s WHERE id = %s
        """, (score, tier, lead_id))
        conn.commit()


# --- P5: Tracking de Conversão ---

def registrar_conversao(lead_id: int, plano: str, valor_mensal: float,
                         canal: str, cnpj: str = None) -> int:
    """Registra conversão de lead para cliente. Retorna ID."""
    with get_conn() as conn:
        cur = conn.cursor()
        # Buscar primeira interação do lead
        cur.execute("""
            SELECT MIN(created_at) as primeira FROM interacoes WHERE lead_id = %s
        """, (lead_id,))
        row = cur.fetchone()
        primeira = row["primeira"] if row else None

        if not cnpj:
            cur.execute("SELECT cnpj FROM leads WHERE id = %s", (lead_id,))
            row = cur.fetchone()
            cnpj = row["cnpj"] if row else None

        cur.execute("""
            INSERT INTO conversoes (lead_id, cnpj, plano, valor_mensal,
                                     canal_atribuicao, primeira_interacao_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (lead_id, cnpj, plano, valor_mensal, canal, primeira))
        new_id = cur.fetchone()["id"]

        # Atualizar status do lead
        cur.execute("""
            UPDATE leads SET status_pipeline = 'cliente' WHERE id = %s
        """, (lead_id,))

        conn.commit()
        return new_id


def atualizar_receita_conversao(lead_id: int, meses: int, receita: float):
    """Atualiza meses ativos e receita total de uma conversão."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE conversoes
            SET meses_ativo = %s, receita_total = %s
            WHERE lead_id = %s
        """, (meses, receita, lead_id))
        conn.commit()


def buscar_lead_por_cnpj(cnpj: str) -> Optional[dict]:
    """Busca lead pelo CNPJ."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM leads WHERE cnpj = %s", (cnpj,))
        row = cur.fetchone()
        return dict(row) if row else None


def leads_similares(lead_id: int, limite: int = 10) -> list:
    """Busca leads similares (mesma cidade, mesmo porte, mesmo segmento)."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT cidade, uf, porte, segmento FROM leads WHERE id = %s", (lead_id,))
        ref = cur.fetchone()
        if not ref:
            return []

        cur.execute("""
            SELECT id, nome_fantasia, lead_score, segmento, tier
            FROM leads
            WHERE id != %s
              AND cidade = %s AND uf = %s
              AND status_pipeline NOT IN ('cliente', 'perdido', 'lead_falso')
            ORDER BY
                (CASE WHEN porte = %s THEN 0 ELSE 1 END),
                (CASE WHEN segmento = %s THEN 0 ELSE 1 END),
                lead_score DESC
            LIMIT %s
        """, (lead_id, ref["cidade"], ref["uf"],
              ref.get("porte") or "", ref.get("segmento") or "",
              limite))
        return [dict(r) for r in cur.fetchall()]


def upsert_leads_batch(leads_data: list, source: str = "sync_api") -> dict:
    """Upsert batch de leads no PostgreSQL.
    INSERT ... ON CONFLICT (cnpj) DO UPDATE — só campos não-protegidos.
    Usa SAVEPOINT por lead (erro em 1 não cancela o batch).

    Returns:
        {"inseridos": N, "atualizados": N, "erros": N, "detalhes_erros": [...]}
    """
    stats = {"inseridos": 0, "atualizados": 0, "erros": 0, "detalhes_erros": []}

    if not leads_data:
        return stats

    with get_conn() as conn:
        cur = conn.cursor()

        for i, lead in enumerate(leads_data):
            cnpj = (lead.get("cnpj") or "").strip()
            if not cnpj or len(cnpj) < 11:
                stats["erros"] += 1
                stats["detalhes_erros"].append(f"Lead {i}: CNPJ inválido '{cnpj}'")
                continue

            try:
                # Filtrar apenas colunas permitidas
                dados = {}
                for k, v in lead.items():
                    if k in _SYNC_COLUNAS_PERMITIDAS and k not in _SYNC_PROTEGIDOS:
                        if v is not None and str(v).strip() != "":
                            if k in _SYNC_CAMPOS_INT:
                                v = _sync_safe_int(v)
                            elif k in _SYNC_CAMPOS_FLOAT:
                                v = _sync_safe_float(v)
                            elif k == "socios_json":
                                if isinstance(v, (list, dict)):
                                    v = json.dumps(v, ensure_ascii=False)
                            dados[k] = v

                if "cnpj" not in dados:
                    dados["cnpj"] = cnpj

                # Construir INSERT ... ON CONFLICT DO UPDATE
                colunas = list(dados.keys())
                placeholders = ["%s"] * len(colunas)
                valores = [dados[c] for c in colunas]

                # SET clause: apenas colunas não-protegidas, skip cnpj
                update_cols = [c for c in colunas if c != "cnpj"]
                if not update_cols:
                    stats["erros"] += 1
                    stats["detalhes_erros"].append(f"Lead {i} ({cnpj}): sem dados para atualizar")
                    continue

                set_clause = ", ".join(
                    f"{c} = EXCLUDED.{c}" for c in update_cols
                )

                # SAVEPOINT para isolar erros
                cur.execute(f"SAVEPOINT sp_lead_{i}")

                sql = f"""
                    INSERT INTO leads ({', '.join(colunas)}, synced_at)
                    VALUES ({', '.join(placeholders)}, NOW())
                    ON CONFLICT (cnpj) DO UPDATE SET
                        {set_clause},
                        synced_at = NOW()
                    RETURNING (xmax = 0) AS inserted
                """
                cur.execute(sql, valores)
                row = cur.fetchone()
                if row and row["inserted"]:
                    stats["inseridos"] += 1
                else:
                    stats["atualizados"] += 1

                cur.execute(f"RELEASE SAVEPOINT sp_lead_{i}")

            except Exception as e:
                stats["erros"] += 1
                stats["detalhes_erros"].append(f"Lead {i} ({cnpj}): {str(e)[:100]}")
                try:
                    cur.execute(f"ROLLBACK TO SAVEPOINT sp_lead_{i}")
                except Exception:
                    pass

        conn.commit()

    return stats


# ============================================================
# TTS PRONÚNCIA APRENDIDA — auto-aprendizado de fala
# ============================================================

_pronuncias_cache: list = []
_pronuncias_cache_ts: float = 0


def obter_pronuncias_aprendidas() -> list:
    """Retorna lista de (escrita, pronuncia) aprendidas. Cache 5 min."""
    import time
    global _pronuncias_cache, _pronuncias_cache_ts
    agora = time.time()
    if _pronuncias_cache and (agora - _pronuncias_cache_ts) < 300:
        return _pronuncias_cache

    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT escrita, pronuncia FROM tts_pronuncia_aprendida
                ORDER BY vezes_corrigido DESC
            """)
            _pronuncias_cache = [(r["escrita"], r["pronuncia"]) for r in cur.fetchall()]
            _pronuncias_cache_ts = agora
            return _pronuncias_cache
    except Exception as e:
        log.warning(f"Erro ao carregar pronúncias aprendidas: {e}")
        return _pronuncias_cache or []


def salvar_pronuncia_aprendida(escrita: str, pronuncia: str, contexto: str = "") -> bool:
    """UPSERT pronúncia aprendida. Incrementa vezes_corrigido se já existe."""
    global _pronuncias_cache_ts
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tts_pronuncia_aprendida (escrita, pronuncia, exemplo_contexto)
                VALUES (%s, %s, %s)
                ON CONFLICT (escrita) DO UPDATE SET
                    pronuncia = EXCLUDED.pronuncia,
                    vezes_corrigido = tts_pronuncia_aprendida.vezes_corrigido + 1,
                    exemplo_contexto = EXCLUDED.exemplo_contexto,
                    atualizado_em = NOW()
                RETURNING id
            """, (escrita, pronuncia, contexto[:200] if contexto else None))
            conn.commit()
            _pronuncias_cache_ts = 0  # Invalidar cache
            log.info(f"Pronúncia aprendida: '{escrita}' → '{pronuncia}'")
            return True
    except Exception as e:
        log.warning(f"Erro ao salvar pronúncia: {e}")
        return False
