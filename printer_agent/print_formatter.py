# printer_agent/print_formatter.py

"""
Formatador ESC/POS para impressoras térmicas.
Gera bytes prontos para envio RAW via win32print.
Suporta 80mm (48 colunas) e 58mm (32 colunas).
"""

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger("printer_agent.formatter")

# ─── Comandos ESC/POS ────────────────────────────
ESC = b'\x1b'
GS = b'\x1d'

INIT = ESC + b'@'                    # Reset impressora
ALIGN_CENTER = ESC + b'a\x01'       # Alinhamento centralizado
ALIGN_LEFT = ESC + b'a\x00'         # Alinhamento esquerda
ALIGN_RIGHT = ESC + b'a\x02'        # Alinhamento direita
BOLD_ON = ESC + b'!\x08'            # Negrito
BOLD_OFF = ESC + b'!\x00'           # Normal
DOUBLE_WIDTH = GS + b'!\x10'        # Largura dupla
DOUBLE_HEIGHT = GS + b'!\x01'       # Altura dupla
DOUBLE_BOTH = GS + b'!\x11'         # Largura + altura dupla
NORMAL_SIZE = GS + b'!\x00'         # Tamanho normal
CUT_FULL = GS + b'V\x00'           # Corte total
CUT_PARTIAL = GS + b'V\x01'        # Corte parcial
FEED_3 = b'\n\n\n'                   # 3 linhas em branco
CODEPAGE_CP860 = ESC + b't\x03'     # Codepage CP860 (português)
CODEPAGE_CP850 = ESC + b't\x02'     # Codepage CP850 (alternativa)


def _encode(text: str, codepage: str = "CP860") -> bytes:
    """Codifica texto para bytes no codepage da impressora."""
    try:
        return text.encode(codepage)
    except (UnicodeEncodeError, LookupError):
        # Fallback: remove acentos ou usa latin-1
        try:
            return text.encode("latin-1", errors="replace")
        except Exception:
            return text.encode("ascii", errors="replace")


def _line(text: str, cols: int, codepage: str = "CP860") -> bytes:
    """Uma linha de texto com quebra."""
    return _encode(text[:cols], codepage) + b'\n'


def _separator(cols: int, char: str = "=") -> bytes:
    """Linha separadora."""
    return _encode(char * cols) + b'\n'


def _separator_dash(cols: int) -> bytes:
    return _separator(cols, "-")


def _center(text: str, cols: int, codepage: str = "CP860") -> bytes:
    """Texto centralizado."""
    padded = text.center(cols)
    return _encode(padded, codepage) + b'\n'


def _right_align(left: str, right: str, cols: int, codepage: str = "CP860") -> bytes:
    """Texto com alinhamento esquerda/direita na mesma linha."""
    space = cols - len(left) - len(right)
    if space < 1:
        space = 1
    line = left + " " * space + right
    return _encode(line[:cols], codepage) + b'\n'


def _format_money(valor: float) -> str:
    """Formata valor monetário."""
    if valor == 0:
        return "GRATIS"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_pizza_sabores(observacoes: str) -> Tuple[List[str], Optional[str]]:
    """Parse de observações de pizza multi-sabor.
    Input: 'Sabores: Calabresa / Caipira | Sem cebola'
    Output: (['Calabresa', 'Caipira'], 'Sem cebola')
    """
    if not observacoes or not observacoes.startswith("Sabores:"):
        return [], observacoes

    parts = observacoes.split("|", 1)
    sabores_str = parts[0].replace("Sabores:", "").strip()
    sabores = [s.strip() for s in sabores_str.split("/")]
    obs_extra = parts[1].strip() if len(parts) > 1 else None
    return sabores, obs_extra


def format_full_receipt(data: dict, largura_mm: int = 80, codepage: str = "CP860") -> bytes:
    """Formata recibo completo (1 impressora — todos os itens)."""
    cols = 48 if largura_mm >= 80 else 32
    buf = bytearray()

    # Init + codepage
    buf += INIT
    if codepage == "CP860":
        buf += CODEPAGE_CP860
    else:
        buf += CODEPAGE_CP850

    rest = data.get("restaurante", {})
    nome_rest = rest.get("nome", "DEREKH FOOD")

    # ─── Header ───
    buf += _separator(cols)
    buf += ALIGN_CENTER
    buf += BOLD_ON
    buf += _encode(f" {nome_rest.upper()}\n", codepage)
    buf += BOLD_OFF
    buf += NORMAL_SIZE
    buf += _center(f"Pedido #{data.get('pedido_id', data.get('comanda', '?'))}", cols, codepage)
    if data.get("data_criacao"):
        # Formata data ISO para legível
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(data["data_criacao"].replace("Z", "+00:00"))
            buf += _center(dt.strftime("%d/%m/%Y %H:%M"), cols, codepage)
        except Exception:
            buf += _center(str(data["data_criacao"])[:16], cols, codepage)
    buf += ALIGN_LEFT
    buf += _separator(cols)

    # ─── Itens agrupados por setor ───
    itens = data.get("itens", [])
    setores: dict = {}
    for item in itens:
        setor = item.get("setor_impressao", "geral")
        setores.setdefault(setor, []).append(item)

    setor_labels = {
        "cozinha": "COZINHA",
        "bar": "BEBIDAS",
        "caixa": "CAIXA",
        "geral": "ITENS",
    }

    for setor, setor_itens in setores.items():
        buf += ALIGN_CENTER
        buf += BOLD_ON
        buf += _center(f"( {setor_labels.get(setor, setor.upper())} )", cols, codepage)
        buf += BOLD_OFF
        buf += ALIGN_LEFT
        buf += _separator(cols)

        for item in setor_itens:
            buf += _format_item(item, cols, codepage)

    # ─── Endereço / Mesa ───
    tipo_entrega = data.get("tipo_entrega", "")
    if tipo_entrega == "mesa":
        buf += _separator(cols)
        buf += ALIGN_CENTER
        buf += BOLD_ON
        buf += _center(f"MESA {data.get('numero_mesa', '?')}", cols, codepage)
        buf += BOLD_OFF
        buf += ALIGN_LEFT
    elif data.get("endereco_entrega"):
        buf += _separator(cols)
        buf += ALIGN_CENTER
        buf += _center("ENDERECO DE ENTREGA", cols, codepage)
        buf += ALIGN_LEFT
        buf += _separator(cols)
        if data.get("cliente_nome"):
            buf += _line(f"Cliente: {data['cliente_nome']}", cols, codepage)
        if data.get("cliente_telefone"):
            buf += _line(f"Tel: {data['cliente_telefone']}", cols, codepage)
        buf += _line(f"End: {data['endereco_entrega']}", cols, codepage)
    elif data.get("cliente_nome"):
        buf += _separator(cols)
        if data.get("cliente_nome"):
            buf += _line(f"Cliente: {data['cliente_nome']}", cols, codepage)
        if data.get("cliente_telefone"):
            buf += _line(f"Tel: {data['cliente_telefone']}", cols, codepage)

    # ─── Valores ───
    buf += _separator(cols)
    buf += ALIGN_CENTER
    buf += _center("VALORES A COBRAR", cols, codepage)
    buf += ALIGN_LEFT
    buf += _separator(cols)

    for item in itens:
        nome = item.get("nome", "?")
        qtd = item.get("quantidade", 1)
        preco = item.get("preco_total", 0) or (item.get("preco", 0) * qtd)
        obs = item.get("observacoes", "")

        sabores, _ = _parse_pizza_sabores(obs)
        nome_display = f"{qtd}x {nome.upper()}"
        preco_display = _format_money(preco)
        buf += _right_align(nome_display, preco_display, cols, codepage)
        if sabores:
            buf += _line(f"      {len(sabores)} SABORES", cols, codepage)

    # Subtotal
    subtotal = data.get("valor_subtotal", 0) or 0
    if subtotal > 0:
        buf += _separator_dash(cols)
        buf += _right_align("SUBTOTAL", _format_money(subtotal), cols, codepage)

    # Desconto
    desconto = data.get("valor_desconto", 0) or 0
    if desconto > 0:
        buf += _right_align("DESCONTO", f"-{_format_money(desconto)}", cols, codepage)

    # Taxa de entrega
    taxa = data.get("valor_taxa_entrega", 0) or 0
    if taxa > 0:
        buf += _right_align("TAXA ENTREGA", _format_money(taxa), cols, codepage)

    # Total
    buf += _separator_dash(cols)
    buf += BOLD_ON
    buf += DOUBLE_BOTH
    buf += _right_align("TOTAL", _format_money(data.get("valor_total", 0)), cols, codepage)
    buf += NORMAL_SIZE
    buf += BOLD_OFF

    # ─── Pagamento ───
    buf += _separator(cols)
    pagamento = data.get("forma_pagamento", "Não informado")
    buf += _line(f"Pagamento: {pagamento.upper()}", cols, codepage)
    troco = data.get("troco_para")
    if troco and troco > 0:
        buf += _line(f"Troco para: {_format_money(troco)}", cols, codepage)
    else:
        buf += _line("Troco: ---", cols, codepage)
    buf += _separator(cols)

    # Observações gerais
    if data.get("observacoes"):
        buf += _line(f"Obs: {data['observacoes']}", cols, codepage)
        buf += _separator(cols)

    # Feed + corte
    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


def format_sector_receipt(
    data: dict,
    setor: str,
    itens_setor: List[dict],
    largura_mm: int = 80,
    codepage: str = "CP860",
) -> bytes:
    """Formata recibo parcial por setor (para impressoras separadas)."""
    cols = 48 if largura_mm >= 80 else 32
    buf = bytearray()

    buf += INIT
    if codepage == "CP860":
        buf += CODEPAGE_CP860
    else:
        buf += CODEPAGE_CP850

    setor_labels = {
        "cozinha": "COZINHA",
        "bar": "BEBIDAS",
        "caixa": "CAIXA",
        "geral": "GERAL",
    }

    rest = data.get("restaurante", {})

    # Header
    buf += _separator(cols)
    buf += ALIGN_CENTER
    buf += BOLD_ON
    buf += _center(setor_labels.get(setor, setor.upper()), cols, codepage)
    buf += BOLD_OFF
    buf += NORMAL_SIZE
    buf += _center(f"Pedido #{data.get('pedido_id', data.get('comanda', '?'))}", cols, codepage)
    if data.get("data_criacao"):
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(data["data_criacao"].replace("Z", "+00:00"))
            buf += _center(dt.strftime("%d/%m/%Y %H:%M"), cols, codepage)
        except Exception:
            pass
    buf += ALIGN_LEFT
    buf += _separator(cols)

    # Itens do setor
    for item in itens_setor:
        buf += _format_item(item, cols, codepage)

    # Se é caixa, incluir valores e pagamento
    if setor == "caixa":
        buf += _separator(cols)
        # Todos os itens com preço
        for item in data.get("itens", []):
            nome = item.get("nome", "?")
            qtd = item.get("quantidade", 1)
            preco = item.get("preco_total", 0) or (item.get("preco", 0) * qtd)
            buf += _right_align(f"{qtd}x {nome}", _format_money(preco), cols, codepage)

        # Subtotal
        subtotal = data.get("valor_subtotal", 0) or 0
        if subtotal > 0:
            buf += _separator_dash(cols)
            buf += _right_align("SUBTOTAL", _format_money(subtotal), cols, codepage)

        # Desconto
        desconto = data.get("valor_desconto", 0) or 0
        if desconto > 0:
            buf += _right_align("DESCONTO", f"-{_format_money(desconto)}", cols, codepage)

        # Taxa entrega
        taxa = data.get("valor_taxa_entrega", 0) or 0
        if taxa > 0:
            buf += _right_align("TAXA ENTREGA", _format_money(taxa), cols, codepage)

        buf += _separator_dash(cols)
        buf += BOLD_ON
        buf += _right_align("TOTAL", _format_money(data.get("valor_total", 0)), cols, codepage)
        buf += BOLD_OFF

        buf += _separator(cols)
        pagamento = data.get("forma_pagamento", "Não informado")
        buf += _line(f"Pagamento: {pagamento.upper()}", cols, codepage)
        troco = data.get("troco_para")
        if troco and troco > 0:
            buf += _line(f"Troco para: {_format_money(troco)}", cols, codepage)

        # Cliente
        if data.get("cliente_nome"):
            buf += _line(f"Cliente: {data['cliente_nome']}", cols, codepage)
        if data.get("cliente_telefone"):
            buf += _line(f"Tel: {data['cliente_telefone']}", cols, codepage)
        if data.get("endereco_entrega"):
            buf += _line(f"End: {data['endereco_entrega']}", cols, codepage)

    # Observações gerais
    if data.get("observacoes"):
        buf += _separator_dash(cols)
        buf += _line(f"Obs: {data['observacoes']}", cols, codepage)

    # Tipo entrega / mesa
    tipo_entrega = data.get("tipo_entrega", "")
    if tipo_entrega == "mesa":
        buf += _separator_dash(cols)
        buf += BOLD_ON
        buf += _center(f"MESA {data.get('numero_mesa', '?')}", cols, codepage)
        buf += BOLD_OFF

    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


def _format_item(item: dict, cols: int, codepage: str = "CP860") -> bytes:
    """Formata um item individual."""
    buf = bytearray()
    nome = item.get("nome", "?")
    qtd = item.get("quantidade", 1)
    obs = item.get("observacoes", "") or ""

    # Nome do item com quantidade
    buf += BOLD_ON
    buf += _line(f"{qtd}x {nome}", cols, codepage)
    buf += BOLD_OFF

    # Variações
    variacoes = item.get("variacoes", []) or []
    for var in variacoes:
        var_nome = var.get("nome", "")
        if var_nome:
            buf += _line(f"   + {var_nome}", cols, codepage)

    # Pizza multi-sabor
    sabores, obs_extra = _parse_pizza_sabores(obs)
    if sabores:
        total = len(sabores)
        for i, sabor in enumerate(sabores):
            buf += _line(f"     {i+1}/{total} {sabor}", cols, codepage)
            if obs_extra and i == 0:
                buf += _line(f"        {obs_extra}", cols, codepage)
    elif obs:
        buf += _line(f"   obs: {obs}", cols, codepage)

    return bytes(buf)
