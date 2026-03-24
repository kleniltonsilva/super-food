# backend/app/routers/bridge.py

"""
Router Bridge Printer — Intercepta impressões de plataformas externas,
parseia com padrões aprendidos ou IA (Grok), e cria pedidos no Derekh Food.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import re
import json
import logging
import os
import httpx

from .. import models, database, auth

logger = logging.getLogger("superfood.bridge")

router = APIRouter(prefix="/painel/bridge", tags=["Bridge Printer"])


def get_rest(current_restaurante=Depends(auth.get_current_restaurante)):
    return current_restaurante


# ============================================================
# SCHEMAS
# ============================================================

class ParseRequest(BaseModel):
    texto_bruto: str
    impressora_origem: Optional[str] = None


class CriarPedidoFromBridgeRequest(BaseModel):
    intercepted_order_id: int


class CriarPatternRequest(BaseModel):
    plataforma: str
    nome_pattern: Optional[str] = None
    regex_detectar: str
    mapeamento_json: dict
    confianca: float = 0.5


class ValidarOrdemRequest(BaseModel):
    """Valida um parse IA e opcionalmente gera pattern automático."""
    gerar_pattern: bool = True  # Se True, auto-gera regex pattern a partir do parse


# ============================================================
# DETECÇÃO DE PLATAFORMA
# ============================================================

PLATAFORMA_KEYWORDS = {
    "ifood": ["ifood", "i-food", "ifd-", "www.ifood.com"],
    "rappi": ["rappi", "rappipay"],
    "99food": ["99food", "99 food", "99foods"],
    "aiqfome": ["aiqfome", "aiq fome"],
    "ubereats": ["uber eats", "ubereats"],
    "keeta": ["keeta"],
    "zdelivery": ["zdelivery", "z delivery", "ze delivery", "zé delivery"],
    "anota_ai": ["anota ai", "anotaai", "anota.ai"],
    "goomer": ["goomer"],
    "neemo": ["neemo"],
    "deliverymuch": ["delivery much", "deliverymuch"],
    "menudigital": ["menu digital"],
    "cardapio_digital": ["cardápio digital", "cardapio digital"],
    "james": ["james delivery", "jamesdelivery"],
}


def detectar_plataforma(texto: str) -> str:
    """Detecta plataforma por keywords no texto bruto."""
    texto_lower = texto.lower()
    for plataforma, keywords in PLATAFORMA_KEYWORDS.items():
        if any(kw in texto_lower for kw in keywords):
            return plataforma
    return "desconhecido"


# ============================================================
# PARSER REGEX (padrões aprendidos)
# ============================================================

def tentar_patterns(texto: str, patterns: list) -> Optional[dict]:
    """Tenta aplicar padrões salvos para extrair dados estruturados."""
    for pattern in patterns:
        try:
            # Verifica se o regex de detecção casa
            if not re.search(pattern.regex_detectar, texto, re.IGNORECASE | re.DOTALL):
                continue

            mapeamento = pattern.mapeamento_json
            dados = {}
            for campo, regex_extrator in mapeamento.items():
                match = re.search(regex_extrator, texto, re.IGNORECASE | re.DOTALL)
                if match:
                    dados[campo] = match.group(1).strip() if match.lastindex else match.group(0).strip()

            if dados:
                return {
                    "dados": dados,
                    "pattern_id": pattern.id,
                    "confianca": pattern.confianca,
                }
        except re.error:
            continue
    return None


# ============================================================
# AUTO-APRENDIZADO — Gera regex patterns a partir de dados IA
# ============================================================

def gerar_regex_para_campo(texto: str, valor: str) -> Optional[str]:
    """Gera um regex que captura um valor específico no texto bruto.

    Analisa o contexto ao redor do valor para criar um regex robusto.
    """
    if not valor or not texto:
        return None

    valor_str = str(valor).strip()
    if not valor_str or len(valor_str) < 2:
        return None

    # Escapar caracteres especiais no valor para buscar no texto
    valor_escaped = re.escape(valor_str)

    # Tentar encontrar o valor no texto (case-insensitive)
    match = re.search(valor_escaped, texto, re.IGNORECASE)
    if not match:
        # Tentar sem acentos / normalizado
        return None

    pos = match.start()

    # Olhar para trás para encontrar o rótulo/label antes do valor
    # Exemplo: "Cliente: João Silva" → label="Cliente:" → regex=r"Cliente:\s*(.+?)(?:\n|$)"
    antes = texto[:pos]

    # Pegar última linha ou rótulo antes do valor
    linhas_antes = antes.split('\n')
    ultima_linha = linhas_antes[-1].strip() if linhas_antes else ""

    if ultima_linha:
        # Rótulo está na mesma linha, antes do valor
        label_escaped = re.escape(ultima_linha)
        regex = f"{label_escaped}\\s*(.+?)(?:\\n|$)"
    else:
        # Valor está no início de uma linha, olhar linha anterior como rótulo
        if len(linhas_antes) >= 2:
            label = linhas_antes[-2].strip()
            if label:
                label_escaped = re.escape(label)
                regex = f"{label_escaped}\\s*\\n\\s*(.+?)(?:\\n|$)"
            else:
                return None
        else:
            return None

    # Validar que o regex funciona
    try:
        test = re.search(regex, texto, re.IGNORECASE | re.DOTALL)
        if test and test.group(1).strip():
            return regex
    except re.error:
        pass

    return None


def gerar_regex_detectar(texto: str, plataforma: str) -> str:
    """Gera regex de detecção da plataforma baseado no texto.

    Combina keywords da plataforma que aparecem no texto para criar
    um regex único que identifica este formato de cupom.
    """
    texto_lower = texto.lower()

    # Pegar keywords da plataforma que aparecem no texto
    keywords_encontradas = []
    if plataforma in PLATAFORMA_KEYWORDS:
        for kw in PLATAFORMA_KEYWORDS[plataforma]:
            if kw in texto_lower:
                keywords_encontradas.append(kw)

    if keywords_encontradas:
        # Usar a keyword mais específica (mais longa)
        keywords_encontradas.sort(key=len, reverse=True)
        kw = keywords_encontradas[0]
        return f"(?i){re.escape(kw)}"

    # Fallback: usar as primeiras palavras significativas do texto
    primeiras = texto.strip().split('\n')[0].strip()
    if primeiras and len(primeiras) > 5:
        return f"(?i){re.escape(primeiras[:50])}"

    return f"(?i){re.escape(plataforma)}"


def auto_gerar_pattern(texto: str, dados_parseados: dict, plataforma: str) -> Optional[dict]:
    """Gera automaticamente um BridgePattern a partir de um parse IA bem-sucedido.

    Analisa o texto original + dados extraídos pela IA para gerar regex reutilizáveis.

    Returns:
        Dict com regex_detectar e mapeamento_json, ou None se não conseguir.
    """
    if not dados_parseados or not texto:
        return None

    mapeamento = {}
    campos_mapeados = 0

    # Campos que queremos mapear
    campos_simples = {
        "cliente_nome": dados_parseados.get("cliente_nome"),
        "cliente_telefone": dados_parseados.get("cliente_telefone"),
        "endereco": dados_parseados.get("endereco"),
        "valor_total": str(dados_parseados.get("valor_total")) if dados_parseados.get("valor_total") else None,
        "forma_pagamento": dados_parseados.get("forma_pagamento"),
    }

    for campo, valor in campos_simples.items():
        if valor and str(valor).strip() and str(valor).lower() != "null":
            regex = gerar_regex_para_campo(texto, str(valor))
            if regex:
                mapeamento[campo] = regex
                campos_mapeados += 1

    # Precisa mapear pelo menos 2 campos para ser útil
    if campos_mapeados < 2:
        return None

    regex_detectar = gerar_regex_detectar(texto, plataforma)

    return {
        "regex_detectar": regex_detectar,
        "mapeamento_json": mapeamento,
        "campos_mapeados": campos_mapeados,
    }


# ============================================================
# PARSER IA (Groq — LLM ultra-rápido para parsing)
# ============================================================

GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # Principal — melhor qualidade
    "llama-3.1-8b-instant",      # Fallback rápido
]


async def parsear_com_ia(texto: str) -> Optional[dict]:
    """Chama Groq API (Llama 3.3 70B) para extrair dados estruturados de um cupom.

    Groq usa LPU (Language Processing Unit) — inferência ultra-rápida.
    Free tier: 30 req/min, 14.4k tokens/min no 70B.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        # Fallback para xAI/Grok se Groq não configurado
        api_key = os.getenv("XAI_API_KEY")
        if api_key:
            return await _parsear_com_grok_fallback(texto, api_key)
        logger.warning("GROQ_API_KEY não configurada — parsing IA indisponível")
        return None

    prompt = f"""Você é um parser especialista de cupons de delivery brasileiro.
Extraia os dados do texto abaixo em JSON.

Campos obrigatórios:
- cliente_nome (string ou null)
- cliente_telefone (string ou null)
- endereco (string completo ou null)
- itens (lista de objetos com: nome, quantidade, preco)
- valor_total (number ou null)
- forma_pagamento (string ou null)

REGRAS:
- Se um campo não existir no cupom, retorne null
- Preços devem ser números (sem R$)
- Telefone com DDD se disponível
- Responda APENAS com JSON válido, sem markdown, sem explicações

TEXTO DO CUPOM:
{texto}"""

    for model in GROQ_MODELS:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 1000,
                        "response_format": {"type": "json_object"},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Limpa possível markdown ```json ... ```
                if content.startswith("```"):
                    content = re.sub(r"^```(?:json)?\s*", "", content)
                    content = re.sub(r"\s*```$", "", content)

                parsed = json.loads(content)
                logger.info(f"Parse IA OK (Groq/{model}) — {len(parsed)} campos extraídos")
                return {"dados": parsed, "pattern_id": None, "confianca": 0.3, "fonte": f"groq/{model}"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning(f"Groq rate limit no modelo {model}, tentando próximo...")
                continue
            logger.error(f"Erro Groq HTTP ({model}): {e.response.status_code}")
            continue
        except Exception as e:
            logger.error(f"Erro parsing IA Groq ({model}): {e}")
            continue

    return None


async def _parsear_com_grok_fallback(texto: str, api_key: str) -> Optional[dict]:
    """Fallback para xAI Grok se Groq não estiver disponível."""
    prompt = f"""Você é um parser de cupons de delivery. Extraia os dados do texto abaixo em JSON.
Campos: cliente_nome, cliente_telefone, endereco, itens (lista de {{nome, quantidade, preco}}), valor_total, forma_pagamento.
Se algum campo não existir, retorne null.
Responda APENAS com JSON válido.

TEXTO DO CUPOM:
{texto}"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-3-mini-fast",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 1000,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
            parsed = json.loads(content)
            return {"dados": parsed, "pattern_id": None, "confianca": 0.3, "fonte": "grok_fallback"}
    except Exception as e:
        logger.error(f"Erro parsing Grok fallback: {e}")
        return None


# ============================================================
# ENDPOINTS
# ============================================================

@router.post("/parse")
async def parse_texto(
    req: ParseRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Recebe texto bruto de cupom, tenta pattern → senão IA → salva registro."""
    texto = req.texto_bruto.strip()
    if not texto:
        raise HTTPException(status_code=400, detail="Texto bruto vazio")

    # Detecção de duplicata: mesmo texto bruto já processado recentemente
    import hashlib as _hl
    texto_hash = _hl.md5(texto.encode()).hexdigest()
    duplicata = db.query(models.BridgeInterceptedOrder).filter(
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
        models.BridgeInterceptedOrder.texto_bruto == texto,
        models.BridgeInterceptedOrder.status.in_(["pendente", "processado"]),
    ).first()
    if duplicata:
        return {
            "id": duplicata.id,
            "plataforma": duplicata.plataforma_detectada,
            "status": duplicata.status,
            "dados_parseados": duplicata.dados_parseados,
            "fonte": "duplicata",
            "confianca": 1.0,
            "duplicata_de": duplicata.id,
        }

    plataforma = detectar_plataforma(texto)

    # 1. Tenta padrões salvos (ordem decrescente por confiança)
    patterns = db.query(models.BridgePattern).filter(
        models.BridgePattern.restaurante_id == rest.id,
    ).order_by(desc(models.BridgePattern.confianca)).all()

    resultado = tentar_patterns(texto, patterns)
    fonte = "pattern"

    # 2. Se nenhum casou → IA
    if not resultado:
        resultado = await parsear_com_ia(texto)
        fonte = "ia"

    # 3. Salva registro
    intercepted = models.BridgeInterceptedOrder(
        restaurante_id=rest.id,
        impressora_origem=req.impressora_origem,
        plataforma_detectada=plataforma,
        texto_bruto=texto,
        dados_parseados=resultado["dados"] if resultado else None,
        pattern_id=resultado.get("pattern_id") if resultado else None,
        status="pendente" if resultado else "falhou",
        erro_mensagem=None if resultado else "Nenhum padrão ou IA conseguiu parsear",
    )
    db.add(intercepted)

    # Atualiza usos do pattern se usou
    if resultado and resultado.get("pattern_id"):
        pattern = db.query(models.BridgePattern).filter(
            models.BridgePattern.id == resultado["pattern_id"]
        ).first()
        if pattern:
            pattern.usos = (pattern.usos or 0) + 1
            pattern.atualizado_em = datetime.utcnow()

    db.commit()
    db.refresh(intercepted)

    return {
        "id": intercepted.id,
        "plataforma": plataforma,
        "status": intercepted.status,
        "dados_parseados": resultado["dados"] if resultado else None,
        "fonte": fonte,
        "confianca": resultado.get("confianca") if resultado else 0,
    }


@router.post("/orders")
async def criar_pedido_from_bridge(
    req: CriarPedidoFromBridgeRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Cria pedido Derekh a partir de um intercepted_order processado."""
    intercepted = db.query(models.BridgeInterceptedOrder).filter(
        models.BridgeInterceptedOrder.id == req.intercepted_order_id,
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
    ).first()

    if not intercepted:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    if intercepted.status == "processado":
        raise HTTPException(status_code=400, detail="Pedido já criado para este registro")
    if not intercepted.dados_parseados:
        raise HTTPException(status_code=400, detail="Dados parseados não disponíveis")

    dados = intercepted.dados_parseados
    cliente_nome = dados.get("cliente_nome") or "Cliente Bridge"
    cliente_telefone = dados.get("cliente_telefone")
    endereco = dados.get("endereco")

    # Tenta match de cliente por telefone
    cliente_id = None
    if cliente_telefone:
        tel_limpo = re.sub(r"\D", "", cliente_telefone)
        if tel_limpo:
            cliente = db.query(models.Cliente).filter(
                models.Cliente.restaurante_id == rest.id,
                models.Cliente.telefone.ilike(f"%{tel_limpo[-8:]}%"),
                models.Cliente.ativo == True
            ).first()
            if cliente:
                cliente_id = cliente.id
                cliente_nome = cliente.nome

    # Formata itens como texto
    itens_lista = dados.get("itens") or []
    if isinstance(itens_lista, list):
        itens_texto = ", ".join(
            f"{i.get('quantidade', 1)}x {i.get('nome', '?')}"
            for i in itens_lista
        )
    else:
        itens_texto = str(itens_lista)

    valor_total = 0.0
    try:
        vt = dados.get("valor_total")
        if vt:
            valor_total = float(str(vt).replace(",", ".").replace("R$", "").strip())
    except (ValueError, TypeError):
        pass

    # Gerar comanda
    ultima = db.query(func.max(models.Pedido.comanda)).filter(
        models.Pedido.restaurante_id == rest.id
    ).scalar()
    try:
        proxima = str(int(ultima) + 1) if ultima else "1"
    except (ValueError, TypeError):
        proxima = "1"

    plataforma = intercepted.plataforma_detectada or "bridge"
    origem = f"bridge_{plataforma}"

    pedido = models.Pedido(
        restaurante_id=rest.id,
        comanda=proxima,
        tipo="Entrega" if endereco else "Retirada",
        origem=origem,
        tipo_entrega="entrega" if endereco else "retirada",
        cliente_nome=cliente_nome,
        cliente_telefone=cliente_telefone,
        endereco_entrega=endereco,
        itens=itens_texto or "Ver dados parseados",
        valor_total=valor_total,
        forma_pagamento=dados.get("forma_pagamento"),
        cliente_id=cliente_id,
        status="pendente",
        historico_status=[{"status": "pendente", "timestamp": datetime.utcnow().isoformat()}],
        data_criacao=datetime.utcnow(),
    )
    db.add(pedido)
    db.flush()

    intercepted.pedido_id = pedido.id
    intercepted.status = "processado"
    db.commit()
    db.refresh(pedido)

    return {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "cliente_nome": pedido.cliente_nome,
        "cliente_vinculado": cliente_id is not None,
        "origem": origem,
        "valor_total": pedido.valor_total,
    }


@router.get("/patterns")
def listar_patterns(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Lista padrões aprendidos do restaurante."""
    patterns = db.query(models.BridgePattern).filter(
        models.BridgePattern.restaurante_id == rest.id
    ).order_by(desc(models.BridgePattern.confianca)).all()

    return [
        {
            "id": p.id,
            "plataforma": p.plataforma,
            "nome_pattern": p.nome_pattern,
            "regex_detectar": p.regex_detectar,
            "mapeamento_json": p.mapeamento_json,
            "confianca": p.confianca,
            "usos": p.usos,
            "validado": p.validado,
            "criado_em": p.criado_em.isoformat() if p.criado_em else None,
            "atualizado_em": p.atualizado_em.isoformat() if p.atualizado_em else None,
        }
        for p in patterns
    ]


@router.post("/patterns")
def criar_pattern(
    req: CriarPatternRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Cria um padrão de parsing manualmente."""
    # Validar regex
    try:
        re.compile(req.regex_detectar)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"regex_detectar inválido: {e}")

    for campo, regex in req.mapeamento_json.items():
        try:
            re.compile(regex)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Regex do campo '{campo}' inválido: {e}")

    pattern = models.BridgePattern(
        restaurante_id=rest.id,
        plataforma=req.plataforma,
        nome_pattern=req.nome_pattern or f"Manual — {req.plataforma}",
        regex_detectar=req.regex_detectar,
        mapeamento_json=req.mapeamento_json,
        confianca=req.confianca,
        validado=True,
    )
    db.add(pattern)
    db.commit()
    db.refresh(pattern)

    return {
        "id": pattern.id,
        "plataforma": pattern.plataforma,
        "nome_pattern": pattern.nome_pattern,
        "campos_mapeados": len(req.mapeamento_json),
    }


@router.put("/patterns/{pattern_id}")
def editar_pattern(
    pattern_id: int,
    confianca: Optional[float] = None,
    validado: Optional[bool] = None,
    nome_pattern: Optional[str] = None,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Edita confiança/validação de um padrão."""
    pattern = db.query(models.BridgePattern).filter(
        models.BridgePattern.id == pattern_id,
        models.BridgePattern.restaurante_id == rest.id
    ).first()

    if not pattern:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")

    if confianca is not None:
        pattern.confianca = max(0.0, min(1.0, confianca))
    if validado is not None:
        pattern.validado = validado
    if nome_pattern is not None:
        pattern.nome_pattern = nome_pattern
    pattern.atualizado_em = datetime.utcnow()

    db.commit()
    return {"ok": True, "confianca": pattern.confianca, "validado": pattern.validado}


@router.delete("/patterns/{pattern_id}")
def deletar_pattern(
    pattern_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Remove padrão aprendido."""
    pattern = db.query(models.BridgePattern).filter(
        models.BridgePattern.id == pattern_id,
        models.BridgePattern.restaurante_id == rest.id
    ).first()

    if not pattern:
        raise HTTPException(status_code=404, detail="Padrão não encontrado")

    db.delete(pattern)
    db.commit()
    return {"ok": True}


@router.post("/orders/{order_id}/validar")
def validar_e_aprender(
    order_id: int,
    req: ValidarOrdemRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Valida um parse IA e opcionalmente gera um pattern regex automático.

    Ciclo de aprendizado:
    1. Cupom chega → Groq IA parseia (confiança 0.3)
    2. Admin vê no painel e clica "Validar e Aprender"
    3. Sistema gera regex a partir do texto + dados parseados
    4. Salva como BridgePattern (confiança 0.7 — validado humano)
    5. Próximos cupons iguais → regex pega direto, sem IA
    """
    intercepted = db.query(models.BridgeInterceptedOrder).filter(
        models.BridgeInterceptedOrder.id == order_id,
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
    ).first()

    if not intercepted:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    if not intercepted.dados_parseados:
        raise HTTPException(status_code=400, detail="Sem dados parseados para aprender")

    resultado = {"order_id": order_id, "validado": True, "pattern_criado": False}

    if req.gerar_pattern and intercepted.texto_bruto:
        plataforma = intercepted.plataforma_detectada or "desconhecido"
        pattern_data = auto_gerar_pattern(
            intercepted.texto_bruto,
            intercepted.dados_parseados,
            plataforma
        )

        if pattern_data:
            # Verificar se já existe pattern similar (mesmo regex de detecção)
            existente = db.query(models.BridgePattern).filter(
                models.BridgePattern.restaurante_id == rest.id,
                models.BridgePattern.regex_detectar == pattern_data["regex_detectar"],
            ).first()

            if existente:
                # Atualizar existente com mais campos se possível
                mapeamento_atual = existente.mapeamento_json or {}
                mapeamento_novo = pattern_data["mapeamento_json"]
                atualizado = False
                for campo, regex in mapeamento_novo.items():
                    if campo not in mapeamento_atual:
                        mapeamento_atual[campo] = regex
                        atualizado = True
                if atualizado:
                    existente.mapeamento_json = mapeamento_atual
                    existente.atualizado_em = datetime.utcnow()
                existente.usos = (existente.usos or 0) + 1
                # Aumentar confiança por validação humana
                existente.confianca = min(1.0, (existente.confianca or 0.5) + 0.1)
                existente.validado = True
                resultado["pattern_id"] = existente.id
                resultado["pattern_atualizado"] = True
            else:
                # Criar novo pattern
                pattern = models.BridgePattern(
                    restaurante_id=rest.id,
                    plataforma=plataforma,
                    nome_pattern=f"Auto — {plataforma.capitalize()} #{order_id}",
                    regex_detectar=pattern_data["regex_detectar"],
                    mapeamento_json=pattern_data["mapeamento_json"],
                    confianca=0.7,  # Validado por humano
                    usos=1,
                    validado=True,
                )
                db.add(pattern)
                db.flush()
                resultado["pattern_id"] = pattern.id
                resultado["pattern_criado"] = True
                resultado["campos_mapeados"] = pattern_data["campos_mapeados"]

            logger.info(
                f"Pattern {'atualizado' if resultado.get('pattern_atualizado') else 'criado'} "
                f"para {plataforma} — {pattern_data['campos_mapeados']} campos"
            )
        else:
            resultado["pattern_erro"] = "Não foi possível gerar regex automático para este formato"

    # Marcar intercepted como validado (aumenta confiança do registro)
    intercepted.status = "validado"
    db.commit()

    return resultado


@router.post("/orders/{order_id}/reparse")
async def reparse_com_ia(
    order_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Re-parseia um registro que falhou usando IA (Groq/Grok)."""
    intercepted = db.query(models.BridgeInterceptedOrder).filter(
        models.BridgeInterceptedOrder.id == order_id,
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
    ).first()

    if not intercepted:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    if not intercepted.texto_bruto:
        raise HTTPException(status_code=400, detail="Sem texto bruto para re-parsear")

    resultado = await parsear_com_ia(intercepted.texto_bruto)
    if not resultado:
        raise HTTPException(status_code=422, detail="IA não conseguiu parsear o texto")

    intercepted.dados_parseados = resultado["dados"]
    intercepted.status = "pendente"
    intercepted.erro_mensagem = None
    db.commit()

    return {
        "id": intercepted.id,
        "dados_parseados": resultado["dados"],
        "fonte": resultado.get("fonte", "ia"),
        "confianca": resultado.get("confianca", 0.3),
    }


@router.get("/status")
def bridge_status(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Status geral do Bridge: estatísticas + config IA."""
    total = db.query(func.count(models.BridgeInterceptedOrder.id)).filter(
        models.BridgeInterceptedOrder.restaurante_id == rest.id
    ).scalar() or 0

    processados = db.query(func.count(models.BridgeInterceptedOrder.id)).filter(
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
        models.BridgeInterceptedOrder.status == "processado",
    ).scalar() or 0

    falhou = db.query(func.count(models.BridgeInterceptedOrder.id)).filter(
        models.BridgeInterceptedOrder.restaurante_id == rest.id,
        models.BridgeInterceptedOrder.status == "falhou",
    ).scalar() or 0

    patterns_count = db.query(func.count(models.BridgePattern.id)).filter(
        models.BridgePattern.restaurante_id == rest.id
    ).scalar() or 0

    patterns_validados = db.query(func.count(models.BridgePattern.id)).filter(
        models.BridgePattern.restaurante_id == rest.id,
        models.BridgePattern.validado == True,
    ).scalar() or 0

    # Detectar qual IA está disponível
    ia_disponivel = "nenhuma"
    if os.getenv("GROQ_API_KEY"):
        ia_disponivel = "groq"
    elif os.getenv("XAI_API_KEY"):
        ia_disponivel = "grok_fallback"

    return {
        "total_interceptados": total,
        "processados": processados,
        "falhou": falhou,
        "pendentes": total - processados - falhou,
        "patterns_total": patterns_count,
        "patterns_validados": patterns_validados,
        "ia_disponivel": ia_disponivel,
        "ia_modelos": GROQ_MODELS if ia_disponivel == "groq" else (["grok-3-mini-fast"] if ia_disponivel == "grok_fallback" else []),
    }


@router.get("/orders")
def listar_orders(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Lista pedidos interceptados."""
    q = db.query(models.BridgeInterceptedOrder).filter(
        models.BridgeInterceptedOrder.restaurante_id == rest.id
    )

    if status:
        q = q.filter(models.BridgeInterceptedOrder.status == status)

    total = q.count()
    orders = q.order_by(desc(models.BridgeInterceptedOrder.criado_em)).offset(offset).limit(limit).all()

    return {
        "total": total,
        "orders": [
            {
                "id": o.id,
                "impressora_origem": o.impressora_origem,
                "plataforma_detectada": o.plataforma_detectada,
                "texto_bruto": o.texto_bruto[:500],
                "dados_parseados": o.dados_parseados,
                "pattern_id": o.pattern_id,
                "pedido_id": o.pedido_id,
                "status": o.status,
                "erro_mensagem": o.erro_mensagem,
                "criado_em": o.criado_em.isoformat() if o.criado_em else None,
            }
            for o in orders
        ],
    }
