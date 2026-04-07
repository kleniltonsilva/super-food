"""
contact_validator.py - Validação e classificação de canais de contato
Detecta emails de contador, verifica WhatsApp via Evolution API,
classifica canal primário/secundário.
"""
import logging
import os
import re
from datetime import datetime, timezone

import httpx

from crm.database import get_conn, obter_configuracao

log = logging.getLogger("contact_validator")
log.setLevel(logging.INFO)
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[VALIDATOR] %(message)s"))
    log.addHandler(_h)


# ============================================================
# DETECÇÃO DE EMAIL DE CONTADOR
# ============================================================

# Padrões que indicam email de escritório contábil / contador
PATTERNS_CONTADOR = [
    r"contab",           # contabilidade, contabil
    r"escritorio",       # escritorio contabil
    r"fiscal",           # departamento fiscal
    r"contad",           # contador, contadora
    r"assessor",         # assessoria contabil
    r"acessor",          # variação com typo
    r"tribut",           # tributario
    r"imposto",          # impostos
    r"financ",           # financeiro (ambíguo, mas comum em contabilidade)
    r"auditoria",
    r"compliance",
    r"societario",       # societário
    r"juridic",          # jurídico
    r"declaracao",       # declaração
    r"ir\b",             # IR (Imposto de Renda)
    r"depto\.?fiscal",
    r"dp@",              # departamento pessoal
    r"rh@",              # recursos humanos (pode ser do restaurante)
]

# Domínios genéricos que NÃO são do proprietário
DOMINIOS_GENERICOS = {
    "gmail.com", "hotmail.com", "yahoo.com", "yahoo.com.br",
    "outlook.com", "live.com", "uol.com.br", "bol.com.br",
    "terra.com.br", "ig.com.br", "globo.com",
}


def _detectar_email_contador(email: str) -> str:
    """Classifica email: 'proprietario', 'contador', 'generico'.

    Returns:
        'contador'      — email pertence a escritório contábil
        'generico'      — email genérico (Gmail, Hotmail, etc.)
        'proprietario'  — email com domínio próprio (provavelmente do restaurante)
    """
    if not email:
        return "generico"

    email_lower = email.lower().strip()

    # Verificar padrões de contador
    for pattern in PATTERNS_CONTADOR:
        if re.search(pattern, email_lower):
            return "contador"

    # Verificar domínio
    if "@" in email_lower:
        dominio = email_lower.split("@")[1]
        if dominio in DOMINIOS_GENERICOS:
            return "generico"
        else:
            return "proprietario"

    return "generico"


# ============================================================
# VERIFICAÇÃO WHATSAPP VIA EVOLUTION API
# ============================================================

def _limpar_telefone(telefone: str) -> str:
    """Remove formatação do telefone, retorna só dígitos com 55."""
    if not telefone:
        return ""
    # Remover tudo que não é dígito
    digits = re.sub(r"\D", "", telefone)
    # Adicionar 55 se não começa com 55
    if digits and not digits.startswith("55"):
        digits = "55" + digits
    # Garantir DDD + número (mínimo 12 dígitos: 55 + DD + 8/9 dígitos)
    if len(digits) < 12:
        return ""
    return digits


async def _verificar_whatsapp(telefone: str) -> bool:
    """Verifica se número tem WhatsApp via Evolution API.

    Returns True/False, ou None se não conseguiu verificar.
    """
    numero = _limpar_telefone(telefone)
    if not numero:
        return None

    evolution_url = obter_configuracao("wa_evolution_url") or os.environ.get("EVOLUTION_API_URL", "")
    evolution_key = obter_configuracao("wa_evolution_key") or os.environ.get("EVOLUTION_API_KEY", "")
    evolution_instance = obter_configuracao("wa_evolution_instance") or os.environ.get("EVOLUTION_INSTANCE", "derekh_sales")

    if not evolution_url or not evolution_key:
        return None  # Evolution API não configurada

    url = f"{evolution_url.rstrip('/')}/chat/whatsappNumbers/{evolution_instance}"

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url,
                json={"numbers": [numero]},
                headers={"apikey": evolution_key},
            )
            if response.status_code == 200:
                data = response.json()
                # Evolution API retorna lista de resultados
                if isinstance(data, list) and data:
                    return data[0].get("exists", False)
                elif isinstance(data, dict):
                    results = data.get("result", data.get("data", []))
                    if isinstance(results, list) and results:
                        return results[0].get("exists", False)
            return None
    except Exception as e:
        log.warning(f"Erro ao verificar WA {numero}: {e}")
        return None


# ============================================================
# CLASSIFICAÇÃO DE CANAL
# ============================================================

def _classificar_canais(lead: dict, wa_existe: bool = None) -> tuple:
    """Classifica canal primário e secundário do lead.

    Returns:
        (canal_primario, canal_secundario)
    """
    canais_disponiveis = []

    # WhatsApp (prioridade máxima)
    if wa_existe is True:
        canais_disponiveis.append("whatsapp")
    elif wa_existe is None:
        # WA não verificado — tratar telefone como possível
        tel = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
        if _limpar_telefone(tel):
            canais_disponiveis.append("telefone")

    # Email (se não é de contador)
    email = lead.get("email") or ""
    email_tipo = _detectar_email_contador(email)
    if email and email_tipo != "contador" and not lead.get("email_invalido"):
        canais_disponiveis.append("email")

    # Telefone (se não tem WA, mas tem telefone)
    if "whatsapp" not in canais_disponiveis and "telefone" not in canais_disponiveis:
        tel = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
        if _limpar_telefone(tel):
            canais_disponiveis.append("telefone")

    primario = canais_disponiveis[0] if canais_disponiveis else None
    secundario = canais_disponiveis[1] if len(canais_disponiveis) > 1 else None

    return primario, secundario


# ============================================================
# VALIDAÇÃO COMPLETA DE UM LEAD
# ============================================================

def validar_contatos_lead(lead_id: int) -> dict:
    """Valida e classifica todos os canais de contato de um lead.

    Returns:
        dict com email_tipo, wa_existe, canal_primario, canal_secundario
    """
    from crm.database import obter_lead

    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    # Classificar email
    email = lead.get("email") or ""
    email_tipo = _detectar_email_contador(email) if email else None

    # Verificar WhatsApp (síncrono wrapper)
    tel = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    wa_existe = None
    if _limpar_telefone(tel):
        try:
            import asyncio
            try:
                asyncio.get_running_loop()
                # Dentro de loop async (uvicorn) — NÃO bloquear
                # A verificação WA será feita em outra oportunidade
                wa_existe = None
            except RuntimeError:
                # Fora de loop async — pode usar asyncio.run
                wa_existe = asyncio.run(_verificar_whatsapp(tel))
        except Exception:
            wa_existe = None

    # Classificar canais
    lead["email_tipo_calc"] = email_tipo
    canal_primario, canal_secundario = _classificar_canais(lead, wa_existe)

    # Salvar no banco
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET
                email_tipo = %s,
                email_validado = TRUE,
                wa_verificado = %s,
                wa_existe = %s,
                canal_primario = %s,
                canal_secundario = %s,
                contato_validado_at = NOW()
            WHERE id = %s
        """, (
            email_tipo,
            wa_existe is not None,
            wa_existe,
            canal_primario,
            canal_secundario,
            lead_id,
        ))
        conn.commit()

    return {
        "lead_id": lead_id,
        "email_tipo": email_tipo,
        "wa_verificado": wa_existe is not None,
        "wa_existe": wa_existe,
        "canal_primario": canal_primario,
        "canal_secundario": canal_secundario,
    }


# ============================================================
# VERSÃO ASYNC — Para uso dentro do event loop (Brain Loop)
# ============================================================

async def verificar_whatsapp_async(telefone: str):
    """Wrapper async direto para verificar WA — usar dentro de event loops."""
    return await _verificar_whatsapp(telefone)


async def validar_contatos_lead_async(lead_id: int) -> dict:
    """Versão async de validar_contatos_lead() — funciona dentro do uvicorn.
    Usa await direto em vez de asyncio.run()."""
    from crm.database import obter_lead

    lead = obter_lead(lead_id)
    if not lead:
        return {"erro": "Lead não encontrado"}

    # Classificar email
    email = lead.get("email") or ""
    email_tipo = _detectar_email_contador(email) if email else None

    # Verificar WhatsApp (async direto)
    tel = lead.get("telefone1") or lead.get("telefone_proprietario") or ""
    wa_existe = None
    if _limpar_telefone(tel):
        try:
            wa_existe = await _verificar_whatsapp(tel)
        except Exception as e:
            log.warning(f"Erro WA async para lead {lead_id}: {e}")
            wa_existe = None

    # Classificar canais
    lead["email_tipo_calc"] = email_tipo
    canal_primario, canal_secundario = _classificar_canais(lead, wa_existe)

    # Salvar no banco
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE leads SET
                email_tipo = %s,
                email_validado = TRUE,
                wa_verificado = %s,
                wa_existe = %s,
                canal_primario = %s,
                canal_secundario = %s,
                contato_validado_at = NOW()
            WHERE id = %s
        """, (
            email_tipo,
            wa_existe is not None,
            wa_existe,
            canal_primario,
            canal_secundario,
            lead_id,
        ))
        conn.commit()

    return {
        "lead_id": lead_id,
        "email_tipo": email_tipo,
        "wa_verificado": wa_existe is not None,
        "wa_existe": wa_existe,
        "canal_primario": canal_primario,
        "canal_secundario": canal_secundario,
    }


# ============================================================
# VALIDAÇÃO EM LOTE
# ============================================================

def validar_lote(cidade: str = None, uf: str = None, limite: int = 500) -> dict:
    """Valida contatos em lote para uma cidade.
    Processa leads que ainda não foram validados (contato_validado_at IS NULL).

    Returns:
        dict com stats de validação
    """
    stats = {
        "total": 0, "validados": 0, "erros": 0,
        "email_proprietario": 0, "email_contador": 0, "email_generico": 0,
        "wa_existe": 0, "wa_nao_existe": 0, "wa_nao_verificado": 0,
    }

    with get_conn() as conn:
        cur = conn.cursor()
        where = ["contato_validado_at IS NULL"]
        params = []

        if cidade:
            where.append("cidade = %s")
            params.append(cidade.upper())
        if uf:
            where.append("uf = %s")
            params.append(uf.upper())

        params.append(limite)
        where_clause = " AND ".join(where)

        cur.execute(f"""
            SELECT id, email, telefone1, telefone_proprietario, email_invalido
            FROM leads
            WHERE {where_clause}
            ORDER BY lead_score DESC
            LIMIT %s
        """, params)
        leads = cur.fetchall()

    stats["total"] = len(leads)
    log.info(f"Validando {len(leads)} leads {f'de {cidade}/{uf}' if cidade else ''}...")

    for lead in leads:
        try:
            result = validar_contatos_lead(lead["id"])
            stats["validados"] += 1

            et = result.get("email_tipo")
            if et == "proprietario":
                stats["email_proprietario"] += 1
            elif et == "contador":
                stats["email_contador"] += 1
            elif et == "generico":
                stats["email_generico"] += 1

            wa = result.get("wa_existe")
            if wa is True:
                stats["wa_existe"] += 1
            elif wa is False:
                stats["wa_nao_existe"] += 1
            else:
                stats["wa_nao_verificado"] += 1

        except Exception as e:
            stats["erros"] += 1
            log.warning(f"Erro validando lead {lead['id']}: {e}")

    log.info(f"Validação concluída: {stats}")
    return stats
