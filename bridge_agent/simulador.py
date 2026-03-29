# bridge_agent/simulador.py

"""
Simulador de recibos de plataformas (iFood, Rappi, 99Food, Uber Eats).
Usado no modo teste para testar o fluxo completo sem impressora real.
Gera texto que imita o formato real dos recibos impressos por cada plataforma.
"""

import random
from datetime import datetime


def _hora_atual():
    return datetime.now().strftime("%d/%m/%Y %H:%M")


def _pedido_id():
    return f"{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"


def _telefone():
    return f"(11) 9{random.randint(1000,9999)}-{random.randint(1000,9999)}"


# ─── Cardápios simulados ────────────────────────────

ITENS_PIZZA = [
    ("Pizza Calabresa G", 45.90),
    ("Pizza Margherita G", 42.90),
    ("Pizza Portuguesa M", 38.90),
    ("Pizza Frango c/ Catupiry G", 48.90),
    ("Pizza 4 Queijos M", 40.90),
]

ITENS_LANCHE = [
    ("X-Bacon", 22.90),
    ("X-Tudo", 28.90),
    ("X-Salada", 18.90),
    ("Combo Hamburguer + Fritas + Refri", 35.90),
    ("Coxinha (6 un)", 15.90),
]

ITENS_BEBIDA = [
    ("Coca-Cola 2L", 12.90),
    ("Guarana Antarctica 1L", 8.90),
    ("Suco Natural Laranja 500ml", 10.90),
    ("Agua Mineral 500ml", 4.50),
]

NOMES_CLIENTES = [
    "João Silva", "Maria Santos", "Pedro Oliveira", "Ana Costa",
    "Lucas Ferreira", "Juliana Lima", "Carlos Souza", "Fernanda Ribeiro",
]

ENDERECOS = [
    "Rua das Flores 123, Apto 45 - Centro",
    "Av. Paulista 1000, Bloco B - Bela Vista",
    "Rua Augusta 500 - Consolação",
    "Alameda Santos 200, Casa 3 - Jardins",
    "Rua Oscar Freire 800 - Pinheiros",
]

PAGAMENTOS = ["Cartão de Crédito", "PIX", "Cartão de Débito", "Dinheiro"]


def _random_itens(n=None):
    """Gera N itens aleatórios do cardápio."""
    if n is None:
        n = random.randint(1, 4)
    todos = ITENS_PIZZA + ITENS_LANCHE + ITENS_BEBIDA
    itens = random.sample(todos, min(n, len(todos)))
    result = []
    for nome, preco in itens:
        qtd = random.choice([1, 1, 1, 2])
        result.append((nome, qtd, preco))
    return result


# ─── Geradores de Recibos ────────────────────────────

def gerar_recibo_ifood() -> str:
    """Gera recibo simulado no formato iFood."""
    pedido = _pedido_id()
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    telefone = _telefone()
    pagamento = random.choice(PAGAMENTOS)
    itens = _random_itens()
    subtotal = sum(q * p for _, q, p in itens)
    taxa = random.choice([0, 5.99, 7.99, 9.99])
    total = subtotal + taxa

    lines = [
        "=" * 42,
        "          *** IFOOD ***",
        "=" * 42,
        f"Pedido: #{pedido}",
        f"Data: {_hora_atual()}",
        "-" * 42,
        f"Cliente: {cliente}",
        f"Tel: {telefone}",
        f"Endereco: {endereco}",
        "-" * 42,
        "ITENS DO PEDIDO:",
        "-" * 42,
    ]

    for nome, qtd, preco in itens:
        valor = qtd * preco
        lines.append(f"  {qtd}x {nome}")
        lines.append(f"{'':>30}R$ {valor:.2f}")

    lines.append("-" * 42)
    lines.append(f"{'Subtotal:':>30} R$ {subtotal:.2f}")
    if taxa > 0:
        lines.append(f"{'Taxa de entrega:':>30} R$ {taxa:.2f}")
    lines.append(f"{'TOTAL:':>30} R$ {total:.2f}")
    lines.append("-" * 42)
    lines.append(f"Pagamento: {pagamento}")
    if pagamento == "Dinheiro":
        troco = round(total + random.choice([0.10, 5.00, 10.00, 20.00]), 2)
        lines.append(f"Troco para: R$ {troco:.2f}")
    lines.append("-" * 42)
    lines.append("ENTREGA")
    lines.append(f"Previsao: {random.randint(30, 60)} min")
    lines.append("=" * 42)
    lines.append("   Obrigado por pedir no iFood!")
    lines.append("=" * 42)

    return "\n".join(lines)


def gerar_recibo_rappi() -> str:
    """Gera recibo simulado no formato Rappi."""
    pedido = f"RPP-{random.randint(100000, 999999)}"
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    pagamento = random.choice(PAGAMENTOS)
    itens = _random_itens()
    subtotal = sum(q * p for _, q, p in itens)
    taxa = random.choice([0, 3.99, 6.99])
    total = subtotal + taxa

    lines = [
        "*" * 42,
        "            RAPPI",
        f"         Pedido {pedido}",
        "*" * 42,
        f"Data/Hora: {_hora_atual()}",
        "",
        f"CLIENTE: {cliente}",
        f"ENTREGA: {endereco}",
        "",
        "─" * 42,
        "PRODUTOS",
        "─" * 42,
    ]

    for nome, qtd, preco in itens:
        valor = qtd * preco
        lines.append(f"{qtd} x {nome} ........... R${valor:.2f}")

    lines.append("─" * 42)
    lines.append(f"Subtotal .................. R${subtotal:.2f}")
    if taxa > 0:
        lines.append(f"Entrega ................... R${taxa:.2f}")
    lines.append(f"TOTAL ..................... R${total:.2f}")
    lines.append("─" * 42)
    lines.append(f"PAGAMENTO: {pagamento.upper()}")
    lines.append("")
    lines.append(f"Tempo estimado: {random.randint(25, 55)} minutos")
    lines.append("*" * 42)

    return "\n".join(lines)


def gerar_recibo_99food() -> str:
    """Gera recibo simulado no formato 99Food."""
    pedido = f"99F{random.randint(10000, 99999)}"
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    telefone = _telefone()
    pagamento = random.choice(PAGAMENTOS)
    itens = _random_itens()
    subtotal = sum(q * p for _, q, p in itens)
    desconto = round(subtotal * random.choice([0, 0, 0.1, 0.15]), 2)
    taxa = random.choice([0, 4.99, 8.99])
    total = subtotal - desconto + taxa

    lines = [
        "+" * 42,
        "          99 FOOD",
        f"       Pedido #{pedido}",
        "+" * 42,
        f"  {_hora_atual()}",
        "",
        f"  Nome: {cliente}",
        f"  Fone: {telefone}",
        f"  End.: {endereco}",
        "",
        "  PEDIDO:",
        "  " + "-" * 38,
    ]

    for nome, qtd, preco in itens:
        valor = qtd * preco
        lines.append(f"  {qtd}x {nome}")
        lines.append(f"     R$ {valor:.2f}")

    lines.append("  " + "-" * 38)
    lines.append(f"  Subtotal:     R$ {subtotal:.2f}")
    if desconto > 0:
        lines.append(f"  Desconto:    -R$ {desconto:.2f}")
    if taxa > 0:
        lines.append(f"  Entrega:      R$ {taxa:.2f}")
    lines.append(f"  TOTAL:        R$ {total:.2f}")
    lines.append("  " + "-" * 38)
    lines.append(f"  Pgto: {pagamento}")
    lines.append("+" * 42)

    return "\n".join(lines)


def gerar_recibo_uber_eats() -> str:
    """Gera recibo simulado no formato Uber Eats."""
    pedido = f"UE-{random.randint(10000, 99999)}"
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    pagamento = random.choice(["Cartão", "Uber Cash", "PIX"])
    itens = _random_itens()
    subtotal = sum(q * p for _, q, p in itens)
    taxa = random.choice([0, 5.49, 7.99, 11.99])
    total = subtotal + taxa

    lines = [
        "=" * 42,
        "         UBER EATS",
        f"      Pedido {pedido}",
        "=" * 42,
        f"{_hora_atual()}",
        "",
        f"Cliente: {cliente}",
        f"Entrega: {endereco}",
        "",
        "--- Itens ---",
    ]

    for nome, qtd, preco in itens:
        valor = qtd * preco
        lines.append(f"  {qtd}x {nome}: R${valor:.2f}")

    lines.append("")
    lines.append(f"Subtotal: R${subtotal:.2f}")
    if taxa > 0:
        lines.append(f"Taxa entrega: R${taxa:.2f}")
    lines.append(f"Total: R${total:.2f}")
    lines.append("")
    lines.append(f"Pagamento: {pagamento}")
    lines.append("=" * 42)

    return "\n".join(lines)


# Mapa de geradores
SIMULADORES = {
    "iFood": gerar_recibo_ifood,
    "Rappi": gerar_recibo_rappi,
    "99Food": gerar_recibo_99food,
    "Uber Eats": gerar_recibo_uber_eats,
}


def gerar_recibo(plataforma: str) -> str:
    """Gera recibo simulado para a plataforma dada."""
    gerador = SIMULADORES.get(plataforma)
    if not gerador:
        raise ValueError(f"Plataforma desconhecida: {plataforma}. Opções: {list(SIMULADORES.keys())}")
    return gerador()
