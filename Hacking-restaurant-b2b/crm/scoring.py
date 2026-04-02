"""
scoring.py - Lead scoring, segmentação automática, personalização de abordagem,
event-driven scoring e score decay.

P4: Scoring Dinâmico — eventos em tempo real + decaimento temporal + feedback conversão.
"""
import json
import logging
from datetime import datetime, date

from crm.database import get_conn
from crm.models import TIERS

log = logging.getLogger("scoring")

# Pontuação por tipo de evento (P4 Etapa 4.1)
EVENTO_PONTUACAO = {
    "email_aberto": 5,
    "email_clicado": 10,
    "wa_respondeu": 15,
    "wa_pediu_demo": 25,
    "trial_ativado": 30,
    "proposta_enviada": 10,
    "proposta_visualizada": 15,
    "opt_out": -50,
    "bounce_email": -10,
    "hard_no": -30,
    "conversa_reativada": 10,
    "conversao": 100,
}


# ============================================================
# CÁLCULO DE SCORE
# ============================================================

def calcular_score(lead: dict) -> int:
    """Calcula lead score (0-100) com base nos atributos do lead."""
    score = 0

    # --- Delivery (oportunidade) ---
    tem_ifood = lead.get("tem_ifood") or 0
    tem_rappi = lead.get("tem_rappi") or 0
    tem_99food = lead.get("tem_99food") or 0
    total_delivery = tem_ifood + tem_rappi + tem_99food

    if total_delivery == 0:
        score += 20  # Sem nenhuma plataforma = OPORTUNIDADE MÁXIMA
    elif total_delivery > 0:
        score += 15  # Já entende delivery, lead educado

    # --- Rating Google Maps ---
    rating = lead.get("rating") or 0
    if rating >= 4.5:
        score += 25  # 15 (>= 4.0) + 10 (>= 4.5)
    elif rating >= 4.0:
        score += 15

    # --- Reviews ---
    total_reviews = lead.get("total_reviews") or 0
    if total_reviews >= 100:
        score += 15

    # --- iFood Enriquecido ---
    ifood_rating = lead.get("ifood_rating") or 0
    ifood_reviews = lead.get("ifood_reviews") or 0
    if ifood_rating >= 4.5:
        score += 5  # Restaurante de qualidade no iFood
    if ifood_reviews >= 500:
        score += 5  # Restaurante popular no iFood
    elif ifood_reviews >= 100:
        score += 3  # Restaurante com boa base de clientes

    # --- Capital Social ---
    capital = lead.get("capital_social") or 0
    if capital >= 100000:
        score += 10

    # --- Porte ---
    porte = lead.get("porte") or ""
    if porte and porte.upper() not in ("MEI", "MICRO EMPREENDEDOR INDIVIDUAL", ""):
        score += 5  # Mais estruturado que MEI

    # --- Negócio novo ---
    data_abertura = lead.get("data_abertura")
    if data_abertura:
        try:
            if isinstance(data_abertura, str):
                # Formato pode ser YYYY-MM-DD ou YYYYMMDD
                data_abertura = data_abertura.replace("-", "")
                if len(data_abertura) == 8:
                    dt = datetime.strptime(data_abertura, "%Y%m%d")
                    meses = (datetime.now() - dt).days / 30
                    if meses <= 12:
                        score += 10  # Negócio novo, precisa de tudo
        except (ValueError, TypeError):
            pass

    # --- Canais de contato ---
    if lead.get("email") and lead["email"].strip():
        score += 5
    if lead.get("telefone1") and lead["telefone1"].strip():
        score += 5

    # --- Penalidades ---
    status = lead.get("status_pipeline") or "novo"
    if status == "perdido":
        score -= 20
    if lead.get("email_invalido"):
        score -= 10
    # Email de contador = contato indireto, penalizar
    if lead.get("email_tipo") == "contador":
        score -= 15

    return max(0, min(100, score))


def calcular_tier(score: int) -> str:
    """Retorna tier baseado no score: hot (>=80), warm (>=50), cool (>=30), cold (<30)."""
    for tier_name in ("hot", "warm", "cool"):
        if score >= TIERS[tier_name]:
            return tier_name
    return "cold"


# ============================================================
# SEGMENTAÇÃO AUTOMÁTICA
# ============================================================

def determinar_segmento(lead: dict, score: int) -> str:
    """Determina segmento do lead baseado em score + atributos."""

    # Rede: múltiplos restaurantes
    if lead.get("multi_restaurante"):
        return "rede"

    # Premium: capital alto + não MEI + múltiplos sócios
    capital = lead.get("capital_social") or 0
    porte = lead.get("porte") or ""
    socios_json = lead.get("socios_json")
    num_socios = 0
    if socios_json:
        try:
            if isinstance(socios_json, str):
                socios = json.loads(socios_json)
            else:
                socios = socios_json
            num_socios = len(socios) if isinstance(socios, list) else 0
        except (json.JSONDecodeError, TypeError):
            pass

    if capital >= 200000 and porte.upper() not in ("MEI",) and num_socios >= 2:
        return "premium"

    # Novo: aberto há menos de 6 meses
    data_abertura = lead.get("data_abertura")
    if data_abertura:
        try:
            if isinstance(data_abertura, str):
                da = data_abertura.replace("-", "")
                if len(da) == 8:
                    dt = datetime.strptime(da, "%Y%m%d")
                    meses = (datetime.now() - dt).days / 30
                    if meses <= 6:
                        return "novo"
        except (ValueError, TypeError):
            pass

    # Quente: score alto + sem delivery + com contato
    tem_delivery = (lead.get("tem_ifood") or 0) + (lead.get("tem_rappi") or 0) + (lead.get("tem_99food") or 0)
    tem_contato = bool(lead.get("email") or lead.get("telefone1"))
    if score >= 70 and tem_delivery == 0 and tem_contato:
        return "quente"

    # Frio: score baixo ou sem contato
    if score < 30 or not tem_contato:
        return "frio"

    # Default
    return "novo"


# ============================================================
# PERSONALIZAÇÃO DE ABORDAGEM
# ============================================================

def personalizar_abordagem(lead: dict) -> dict:
    """Gera contexto de personalização para abordagem do lead."""
    resultado = {
        "nome_dono": "",
        "contexto": "",
        "abordagem": "",
        "tom": "padrao",
    }

    # Extrair nome do proprietário
    socios_json = lead.get("socios_json")
    if socios_json:
        try:
            if isinstance(socios_json, str):
                socios = json.loads(socios_json)
            else:
                socios = socios_json
            if isinstance(socios, list):
                # Procurar administrador/sócio-administrador
                for socio in socios:
                    qual = (socio.get("qualificacao") or "").lower()
                    if "administrador" in qual:
                        resultado["nome_dono"] = _formatar_nome(socio.get("nome", ""))
                        break
                # Fallback: primeiro sócio
                if not resultado["nome_dono"] and socios:
                    resultado["nome_dono"] = _formatar_nome(socios[0].get("nome", ""))
        except (json.JSONDecodeError, TypeError):
            pass

    # Contexto baseado em dados disponíveis
    nome_fantasia = lead.get("nome_fantasia") or lead.get("razao_social") or "seu restaurante"
    rating = lead.get("rating") or 0
    reviews = lead.get("total_reviews") or 0
    ifood_rating = lead.get("ifood_rating") or 0
    ifood_reviews = lead.get("ifood_reviews") or 0
    ifood_categorias = lead.get("ifood_categorias") or ""
    ifood_preco = lead.get("ifood_preco") or ""

    # Contexto — priorizar dados iFood (mais relevante para vendas)
    if ifood_rating > 0 and ifood_reviews > 0:
        resultado["contexto"] = (
            f"Vi que o {nome_fantasia} tem {ifood_rating} estrelas no iFood "
            f"com {ifood_reviews} avaliações — qualidade comprovada!"
        )
        if ifood_categorias:
            resultado["contexto"] += f" Especialistas em {ifood_categorias.split(',')[0].strip()}."
    elif rating > 0 and reviews > 0:
        resultado["contexto"] = (
            f"Vi que o {nome_fantasia} tem {rating} estrelas e "
            f"{reviews} avaliações no Google — parabéns!"
        )

    # Abordagem baseada em delivery + dados iFood enriquecidos
    tem_ifood = lead.get("tem_ifood") or 0
    tem_rappi = lead.get("tem_rappi") or 0
    tem_99food = lead.get("tem_99food") or 0
    total_delivery = tem_ifood + tem_rappi + tem_99food

    if total_delivery == 0:
        resultado["abordagem"] = (
            "Percebi que vocês ainda não estão em plataformas de delivery. "
            "A Derekh cria seu delivery próprio em 48h, sem comissões."
        )
    elif tem_ifood and ifood_rating >= 4.5:
        resultado["abordagem"] = (
            f"Com nota {ifood_rating} no iFood, vocês já provaram qualidade. "
            "Agora imagina um delivery próprio onde você fica com 100% do faturamento, "
            "sem os 27% de comissão do iFood."
        )
    elif tem_ifood and ifood_reviews >= 500:
        resultado["abordagem"] = (
            f"Com mais de {ifood_reviews} avaliações no iFood, seus clientes já te conhecem. "
            "Falta o canal direto — delivery próprio por WhatsApp, sem comissão."
        )
    elif tem_ifood and ifood_preco in ("$$$", "$$$$"):
        resultado["abordagem"] = (
            "Restaurantes premium como vocês perdem muito com comissão do iFood. "
            "Em cada pedido de R$80, R$22 vai pro iFood. Com delivery próprio, fica tudo com vocês."
        )
    elif tem_ifood:
        resultado["abordagem"] = (
            "Vi que vocês já estão no iFood — a Derekh funciona como complemento. "
            "Delivery próprio, sem comissão de 27%."
        )
    else:
        resultado["abordagem"] = (
            "Vi que vocês já trabalham com delivery — a Derekh cria seu "
            "canal próprio para ter mais controle e margem."
        )

    # Tom baseado em porte
    porte = lead.get("porte") or ""
    mei = lead.get("mei") or ""
    if mei == "S" or "MEI" in porte.upper():
        resultado["tom"] = "informal"
    elif (lead.get("capital_social") or 0) >= 200000:
        resultado["tom"] = "formal"

    return resultado


def avaliar_qualidade_dados(lead: dict, delivery_verificado: bool = False) -> dict:
    """Avalia qualidade dos dados disponíveis de um lead.
    Retorna dict com nivel (completo/parcial/basico) e flags individuais."""
    tem_maps = bool(lead.get("rating") and lead.get("nome_maps"))
    tem_delivery_check = delivery_verificado
    tem_contato = bool(lead.get("email") or lead.get("telefone1"))
    tem_telefone = bool(lead.get("telefone1") or lead.get("telefone_proprietario"))
    tem_email = bool(lead.get("email") and lead["email"].strip())
    tem_socios = False
    socios_json = lead.get("socios_json")
    if socios_json:
        try:
            if isinstance(socios_json, str):
                socios = json.loads(socios_json)
            else:
                socios = socios_json
            tem_socios = isinstance(socios, list) and len(socios) > 0
        except (json.JSONDecodeError, TypeError):
            pass

    # Determinar nivel
    if tem_maps and tem_contato and tem_socios:
        nivel = "completo"
    elif tem_maps or (tem_contato and tem_socios):
        nivel = "parcial"
    else:
        nivel = "basico"

    return {
        "nivel": nivel,
        "tem_maps": tem_maps,
        "tem_delivery_check": tem_delivery_check,
        "tem_contato": tem_contato,
        "tem_telefone": tem_telefone,
        "tem_email": tem_email,
        "tem_socios": tem_socios,
    }


def _formatar_nome(nome: str) -> str:
    """Formata nome para título (primeira letra maiúscula)."""
    if not nome:
        return ""
    return " ".join(p.capitalize() for p in nome.lower().split()[:2])


# ============================================================
# CÁLCULO EM BATCH
# ============================================================

def calcular_scores_todos(batch_size: int = 5000) -> dict:
    """Calcula e atualiza lead_score + segmento + tier para todos os leads.
    Processa em batches para não sobrecarregar memória.
    Retorna estatísticas."""
    stats = {"total": 0, "atualizados": 0, "por_segmento": {}}

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total FROM leads")
        stats["total"] = cur.fetchone()["total"]

        offset = 0
        while True:
            cur.execute("""
                SELECT id, tem_ifood, tem_rappi, tem_99food,
                       rating, total_reviews, capital_social, porte,
                       data_abertura, email, telefone1,
                       status_pipeline, email_invalido,
                       multi_restaurante, socios_json, mei,
                       nome_fantasia, razao_social, email_tipo,
                       ifood_rating, ifood_reviews, ifood_preco,
                       ifood_categorias
                FROM leads
                ORDER BY id
                LIMIT %s OFFSET %s
            """, (batch_size, offset))

            rows = cur.fetchall()
            if not rows:
                break

            updates = []
            for lead in rows:
                score = calcular_score(lead)
                segmento = determinar_segmento(lead, score)
                tier = calcular_tier(score)
                updates.append((score, segmento, tier, lead["id"]))
                stats["por_segmento"][segmento] = stats["por_segmento"].get(segmento, 0) + 1

            cur.executemany("""
                UPDATE leads SET lead_score = %s, segmento = %s, tier = %s WHERE id = %s
            """, updates)
            conn.commit()

            stats["atualizados"] += len(updates)
            offset += batch_size

    return stats


def calcular_score_lead(lead_id: int) -> dict:
    """Calcula e atualiza score, segmento e tier de um lead específico."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, tem_ifood, tem_rappi, tem_99food,
                   rating, total_reviews, capital_social, porte,
                   data_abertura, email, telefone1,
                   status_pipeline, email_invalido,
                   multi_restaurante, socios_json, mei,
                   nome_fantasia, razao_social, email_tipo,
                   ifood_rating, ifood_reviews, ifood_preco,
                   ifood_categorias
            FROM leads WHERE id = %s
        """, (lead_id,))
        lead = cur.fetchone()
        if not lead:
            return {"erro": "Lead não encontrado"}

        score = calcular_score(lead)
        segmento = determinar_segmento(lead, score)
        tier = calcular_tier(score)

        cur.execute("""
            UPDATE leads SET lead_score = %s, segmento = %s, tier = %s WHERE id = %s
        """, (score, segmento, tier, lead_id))
        conn.commit()

        return {"lead_id": lead_id, "score": score, "segmento": segmento, "tier": tier}


# ============================================================
# P4: EVENT-DRIVEN SCORING
# ============================================================

def atualizar_score_evento(lead_id: int, evento: str, valor: int = 0) -> dict:
    """Atualiza score do lead baseado em um evento.
    Registra evento no histórico e recalcula tier.
    Retorna {"score_antes", "score_depois", "tier"}."""
    from crm.database import registrar_evento_lead, atualizar_score_lead

    if not valor:
        valor = EVENTO_PONTUACAO.get(evento, 0)

    if valor == 0:
        return {"erro": f"Evento '{evento}' sem pontuação definida"}

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT lead_score FROM leads WHERE id = %s", (lead_id,))
        row = cur.fetchone()
        if not row:
            return {"erro": "Lead não encontrado"}

        score_antes = row["lead_score"] or 0
        score_depois = max(0, min(100, score_antes + valor))
        tier = calcular_tier(score_depois)

    # Atualizar score e tier
    atualizar_score_lead(lead_id, score_depois, tier)

    # Registrar evento
    registrar_evento_lead(lead_id, evento, valor, score_antes, score_depois)

    log.info(f"Score evento: lead {lead_id} '{evento}' {score_antes}→{score_depois} (tier={tier})")
    return {"score_antes": score_antes, "score_depois": score_depois, "tier": tier}


# ============================================================
# P4: SCORE DECAY (DECAIMENTO TEMPORAL)
# ============================================================

def aplicar_decaimento_scores() -> dict:
    """Aplica decaimento de 5% por semana para leads sem interação recente.
    Rodar diariamente (brain_loop chama 1x/dia).
    Mínimo: 10 (nunca zera). Retorna stats."""
    from crm.database import leads_sem_interacao_recente, atualizar_score_lead, registrar_evento_lead

    stats = {"processados": 0, "decaidos": 0}

    leads = leads_sem_interacao_recente(dias=7)
    if not leads:
        return stats

    for lead in leads:
        lead_id = lead["id"]
        score_atual = lead["lead_score"] or 0

        if score_atual <= 10:
            continue  # Já no mínimo

        # Decaimento de 5%
        decaimento = max(1, int(score_atual * 0.05))
        novo_score = max(10, score_atual - decaimento)
        novo_tier = calcular_tier(novo_score)

        atualizar_score_lead(lead_id, novo_score, novo_tier)
        registrar_evento_lead(lead_id, "score_decay", -decaimento, score_atual, novo_score)

        stats["processados"] += 1
        if novo_score < score_atual:
            stats["decaidos"] += 1

    if stats["decaidos"] > 0:
        log.info(f"Score decay: {stats['decaidos']}/{stats['processados']} leads decaíram")

    return stats


# ============================================================
# P4: FEEDBACK DE CONVERSÃO
# ============================================================

def feedback_conversao(lead_cnpj: str) -> dict:
    """Quando lead vira cliente: registra evento, marca pipeline, boost similares.
    Chamado pelo backend principal via API."""
    from crm.database import buscar_lead_por_cnpj, registrar_evento_lead, leads_similares

    lead = buscar_lead_por_cnpj(lead_cnpj)
    if not lead:
        return {"erro": f"Lead com CNPJ {lead_cnpj} não encontrado"}

    lead_id = lead["id"]

    # 1. Registrar evento de conversão (+100)
    atualizar_score_evento(lead_id, "conversao", 100)

    # 2. Marcar pipeline como 'cliente'
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET status_pipeline = 'cliente' WHERE id = %s
        """, (lead_id,))
        conn.commit()

    # 3. Retroalimentar: boost leads similares (+10)
    similares = leads_similares(lead_id, limite=10)
    boosted = 0
    for sim in similares:
        atualizar_score_evento(sim["id"], "similar_converteu", 10)
        boosted += 1

    log.info(f"Conversão: lead {lead_id} ({lead_cnpj}) → +{boosted} leads boosted")

    return {
        "lead_id": lead_id,
        "boosted": boosted,
        "similares": [s["id"] for s in similares[:5]],
    }
