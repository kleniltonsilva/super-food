"""
agente_autonomo.py - Cérebro auto-otimizador do Sales Autopilot
Multi-Armed Bandit (epsilon-greedy), A/B testing, relatório diário.
"""
import logging
import random
import math
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from crm.database import (
    get_conn, obter_configuracao, salvar_configuracao,
    stats_outreach, stats_wa,
    criar_experimento, registrar_resultado_experimento,
    obter_experimento_ativo, listar_experimentos,
    declarar_vencedor, criar_decisao, listar_decisoes_pendentes,
    criar_relatorio, obter_ultimo_relatorio,
    metricas_outreach_periodo,
)

log = logging.getLogger("agente")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[AGENTE] %(message)s"))
    log.addHandler(_h)


# ============================================================
# MULTI-ARMED BANDIT (Epsilon-Greedy)
# ============================================================

def multi_armed_bandit(variavel: str) -> Optional[str]:
    """Epsilon-greedy: retorna variante escolhida (a ou b).
    Epsilon decai com amostras: 0.20 → 0.10 → 0.05."""
    exp = obter_experimento_ativo(variavel)
    if not exp:
        return None

    total = exp["amostras_a"] + exp["amostras_b"]

    # Epsilon decay
    if total < 50:
        epsilon = 0.20
    elif total < 200:
        epsilon = 0.10
    else:
        epsilon = 0.05

    # Explorar (random)
    if random.random() < epsilon:
        return random.choice(["a", "b"])

    # Exploitar (melhor taxa de sucesso)
    rate_a = exp["sucessos_a"] / max(exp["amostras_a"], 1)
    rate_b = exp["sucessos_b"] / max(exp["amostras_b"], 1)

    if rate_a > rate_b:
        return "a"
    elif rate_b > rate_a:
        return "b"
    else:
        return random.choice(["a", "b"])


def avaliar_experimento(exp_id: int) -> dict:
    """Avalia se experimento tem vencedor via z-test de proporção.
    Precisa de amostras >= 30 cada e p < 0.05."""
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM agente_experimentos WHERE id = %s", (exp_id,))
        exp = cur.fetchone()

    if not exp:
        return {"erro": "Experimento não encontrado"}

    na, sa = exp["amostras_a"], exp["sucessos_a"]
    nb, sb = exp["amostras_b"], exp["sucessos_b"]

    # Amostras insuficientes
    if na < 30 or nb < 30:
        return {"status": "amostras_insuficientes", "na": na, "nb": nb}

    # Z-test de proporção
    pa = sa / na
    pb = sb / nb
    p_pool = (sa + sb) / (na + nb)

    if p_pool == 0 or p_pool == 1:
        return {"status": "sem_variancia"}

    se = math.sqrt(p_pool * (1 - p_pool) * (1/na + 1/nb))
    if se == 0:
        return {"status": "sem_variancia"}

    z = (pa - pb) / se
    # Tabela z simplificada: |z| > 1.96 → p < 0.05
    p_value = 2 * (1 - _norm_cdf(abs(z)))
    confianca = round((1 - p_value) * 100, 1)

    result = {
        "z": round(z, 3),
        "p_value": round(p_value, 4),
        "confianca": confianca,
        "rate_a": round(pa * 100, 1),
        "rate_b": round(pb * 100, 1),
    }

    if p_value < 0.05:
        vencedor = "a" if pa > pb else "b"
        declarar_vencedor(exp_id, vencedor, confianca)
        result["vencedor"] = vencedor
        result["status"] = "decidido"
        log.info(f"Experimento {exp_id}: vencedor={vencedor} (confiança {confianca}%)")
    elif na + nb >= 200:
        # Muitas amostras sem resultado → empate
        declarar_vencedor(exp_id, "empate", confianca)
        result["vencedor"] = "empate"
        result["status"] = "empate"
    else:
        result["status"] = "inconclusivo"

    return result


def _norm_cdf(x: float) -> float:
    """Aproximação da CDF normal padrão (sem scipy)."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


# ============================================================
# SUGERIR ESTRATÉGIA
# ============================================================

def sugerir_estrategia(lead: dict) -> dict:
    """Retorna estratégia otimizada para um lead baseada nos experimentos."""
    estrategia = {
        "horario": "14:00-17:00",
        "tom": "informal",
        "voz": "ara",
        "usar_audio": False,
        "max_followups": 3,
    }

    # Verificar experimentos ativos
    for var in ("horario", "tom", "voz", "audio_timing", "followup_limit"):
        variante = multi_armed_bandit(var)
        if variante:
            exp = obter_experimento_ativo(var)
            if exp:
                valor = exp["variante_a"] if variante == "a" else exp["variante_b"]
                if var == "horario":
                    estrategia["horario"] = valor
                elif var == "tom":
                    estrategia["tom"] = valor
                elif var == "voz":
                    estrategia["voz"] = valor
                elif var == "audio_timing":
                    estrategia["usar_audio"] = valor == "primeira_msg"
                elif var == "followup_limit":
                    try:
                        estrategia["max_followups"] = int(valor)
                    except ValueError:
                        pass

    return estrategia


# ============================================================
# CICLO DIÁRIO
# ============================================================

def ciclo_diario() -> dict:
    """Ciclo diário do agente: analisa, avalia, recomenda.
    Retorna relatório."""
    log.info("Iniciando ciclo diário...")

    ontem = date.today() - timedelta(days=1)
    inicio = datetime.combine(ontem, datetime.min.time())
    fim = datetime.combine(date.today(), datetime.min.time())

    # 1. Coletar métricas
    metricas = metricas_outreach_periodo(inicio, fim)
    log.info(f"Métricas de {ontem}: {metricas}")

    # 1.5. Extrair padrões vencedores + decaimento
    try:
        from crm.pattern_library import extrair_padroes_diario, decaimento_diario
        pattern_stats = extrair_padroes_diario()
        decay_stats = decaimento_diario()
        log.info(f"Pattern Library: {pattern_stats} | Decaimento: {decay_stats}")
    except Exception as e:
        log.warning(f"Pattern Library erro: {e}")
        pattern_stats = {}
        decay_stats = {}

    # 2. Avaliar experimentos ativos
    experimentos = listar_experimentos(ativo=True)
    avaliacoes = []
    for exp in experimentos:
        if exp.get("vencedor") is None:
            resultado = avaliar_experimento(exp["id"])
            avaliacoes.append({
                "variavel": exp["variavel"],
                "resultado": resultado,
            })

    # 3. Gerar descobertas
    descobertas = []
    env = metricas.get("emails_enviados", 0)

    if env > 0:
        open_rate = metricas.get("open_rate", 0)
        if open_rate > 35:
            descobertas.append(f"Open rate acima da meta ({open_rate}% > 35%)")
        elif open_rate < 20:
            descobertas.append(f"Open rate baixo ({open_rate}%) — revisar assuntos")

        bounce_rate = round(metricas.get("emails_bounced", 0) / max(env, 1) * 100, 1)
        if bounce_rate > 4:
            descobertas.append(f"Bounce rate alto ({bounce_rate}%) — PAUSAR warmup")

    for av in avaliacoes:
        if av["resultado"].get("status") == "decidido":
            v = av["resultado"]["vencedor"]
            var = av["variavel"]
            descobertas.append(f"Experimento '{var}': variante {v} venceu")

    # 4. Gerar recomendações
    recomendacoes = []

    # Warmup automático
    max_email = int(obter_configuracao("outreach_max_email_dia") or "20")
    if env > 0:
        bounce_rate = round(metricas.get("emails_bounced", 0) / max(env, 1) * 100, 1)
        if bounce_rate < 2 and max_email < 100:
            novo_limite = min(int(max_email * 1.2), 100)
            recomendacoes.append({
                "tipo": "warmup",
                "descricao": f"Aumentar limite de {max_email} para {novo_limite} emails/dia (bounce {bounce_rate}% < 2%)",
                "acao": {"chave": "outreach_max_email_dia", "valor": str(novo_limite)},
            })
        elif bounce_rate > 4:
            novo_limite = max(int(max_email * 0.5), 10)
            # Auto-aplicar (guardrail de segurança)
            salvar_configuracao("outreach_max_email_dia", str(novo_limite))
            criar_decisao("ajuste_auto",
                          f"Limite reduzido de {max_email} para {novo_limite} (bounce {bounce_rate}%)",
                          {"bounce_rate": bounce_rate, "novo_limite": novo_limite})
            recomendacoes.append({
                "tipo": "guardrail",
                "descricao": f"APLICADO: Limite reduzido para {novo_limite} (bounce {bounce_rate}%)",
            })

    # Criar decisões pendentes para recomendações que precisam aprovação
    for rec in recomendacoes:
        if rec["tipo"] == "warmup":
            criar_decisao("recomendacao", rec["descricao"], rec.get("acao"))

    # 5. Resumo texto
    resumo_parts = [
        f"Relatório {ontem.strftime('%d/%m/%Y')}:",
        f"Emails: {env} enviados, {metricas.get('open_rate', 0)}% abertos, {metricas.get('ctr', 0)}% clicaram.",
    ]
    wa = metricas.get("wa_conversas", 0)
    if wa > 0:
        resumo_parts.append(
            f"WhatsApp: {wa} conversas, {metricas.get('wa_response_rate', 0)}% responderam."
        )
    if descobertas:
        resumo_parts.append("Descobertas: " + "; ".join(descobertas))
    if recomendacoes:
        resumo_parts.append(f"{len(recomendacoes)} recomendação(ões) pendente(s).")

    resumo = "\n".join(resumo_parts)

    # 6. Salvar relatório
    rel_id = criar_relatorio(
        ontem, date.today(), metricas,
        descobertas, [r["descricao"] for r in recomendacoes],
        resumo
    )

    log.info(f"Ciclo diário concluído. Relatório #{rel_id}")
    return {
        "relatorio_id": rel_id,
        "metricas": metricas,
        "descobertas": descobertas,
        "recomendacoes": [r["descricao"] for r in recomendacoes],
        "avaliacoes": avaliacoes,
        "resumo": resumo,
    }


def gerar_relatorio_diario() -> dict:
    """Alias para ciclo_diario()."""
    return ciclo_diario()
