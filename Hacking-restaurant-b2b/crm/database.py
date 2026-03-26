"""
database.py - Conexão PostgreSQL + queries do CRM Derekh
Usa pool de conexões psycopg2. DATABASE_URL via env var.
"""
import json
import os
from datetime import date, datetime
from typing import Optional
from contextlib import contextmanager

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
    """Leads criados nos últimos 7 dias SEM ações na outreach_sequencia.
    Elegíveis: com email, sem opt_out, sem email_invalido."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT l.id, l.cnpj, l.nome_fantasia, l.razao_social,
                   l.cidade, l.uf, l.email, l.telefone1,
                   l.lead_score, l.segmento, l.tier,
                   l.tem_ifood, l.tem_rappi, l.tem_99food
            FROM leads l
            WHERE l.created_at >= NOW() - INTERVAL '7 days'
              AND l.opt_out_email = FALSE
              AND l.email IS NOT NULL AND l.email != ''
              AND l.email_invalido = 0
              AND NOT EXISTS (
                  SELECT 1 FROM outreach_sequencia o
                  WHERE o.lead_id = l.id AND o.cancelado = FALSE
              )
            ORDER BY l.lead_score DESC
            LIMIT %s
        """, (limite,))
        return [dict(r) for r in cur.fetchall()]


def leads_para_outreach(cidade: str = None, uf: str = None,
                        score_min: int = 30, limite: int = 100) -> list:
    """Leads elegíveis para outreach: com email, sem opt_out, score >= min."""
    with get_conn() as conn:
        cur = conn.cursor()
        where = [
            "l.opt_out_email = FALSE",
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

def criar_lead_inbound(numero: str) -> int:
    """Cria lead mínimo a partir de número WhatsApp inbound.
    CNPJ = 'WA_' + numero (placeholder). Retorna lead_id."""
    cnpj_placeholder = f"WA_{numero}"[:14]
    with get_conn() as conn:
        cur = conn.cursor()
        # Verificar se já existe
        cur.execute("SELECT id FROM leads WHERE cnpj = %s", (cnpj_placeholder,))
        row = cur.fetchone()
        if row:
            return row["id"]
        cur.execute("""
            INSERT INTO leads (cnpj, nome_fantasia, telefone1, status_pipeline, segmento, tier)
            VALUES (%s, %s, %s, 'novo', 'inbound_wa', 'hot')
            RETURNING id
        """, (cnpj_placeholder, f"WhatsApp {numero[-4:]}", numero))
        new_id = cur.fetchone()["id"]
        conn.commit()
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
                      "voz_usada", "tom_usado", "usou_audio"}
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


def listar_decisoes_pendentes() -> list:
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT * FROM agente_decisoes
            WHERE aprovado IS NULL
            ORDER BY created_at DESC LIMIT 20
        """)
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
              AND l.status_pipeline NOT IN ('perdido', 'cliente')
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
        where = "WHERE l.status_pipeline NOT IN ('perdido', 'cliente')"
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
