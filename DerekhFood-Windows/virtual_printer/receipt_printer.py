"""
Gerador de recibos ESC/POS reais via win32print (spooler Windows).

Diferente do bridge_agent/simulador.py que envia texto puro, este módulo
gera bytes ESC/POS idênticos aos de uma impressora térmica real e envia
pelo spooler do Windows usando win32print.WritePrinter().

4 plataformas simuladas: iFood, Rappi, 99Food, Uber Eats.
"""

import random
import time
from datetime import datetime
from typing import Optional

# ── Constantes ESC/POS (mesmas do printer_agent/print_formatter.py) ──────────

ESC = b"\x1b"
GS = b"\x1d"

INIT = ESC + b"\x40"                    # ESC @ — Reset
ALIGN_LEFT = ESC + b"\x61\x00"          # ESC a 0
ALIGN_CENTER = ESC + b"\x61\x01"        # ESC a 1
ALIGN_RIGHT = ESC + b"\x61\x02"         # ESC a 2
BOLD_ON = ESC + b"\x21\x08"             # ESC ! 8
BOLD_OFF = ESC + b"\x21\x00"            # ESC ! 0
DOUBLE_WIDTH = GS + b"\x21\x10"         # GS ! 16
DOUBLE_HEIGHT = GS + b"\x21\x01"        # GS ! 1
DOUBLE_BOTH = GS + b"\x21\x11"          # GS ! 17
NORMAL_SIZE = GS + b"\x21\x00"          # GS ! 0
CUT_PARTIAL = GS + b"\x56\x01"          # GS V 1
CUT_FULL = GS + b"\x56\x00"            # GS V 0
FEED_3 = b"\n\n\n"
CODEPAGE_CP860 = ESC + b"\x74\x03"      # ESC t 3
CODEPAGE_CP850 = ESC + b"\x74\x02"      # ESC t 2

PRINTER_NAME = "Termica Virtual 80mm"
COLS = 48  # Colunas para 80mm


def _encode(text: str, codepage: str = "CP860") -> bytes:
    """Codifica texto para bytes com fallback."""
    try:
        return text.encode(codepage)
    except (UnicodeEncodeError, LookupError):
        try:
            return text.encode("CP850")
        except (UnicodeEncodeError, LookupError):
            return text.encode("ascii", errors="replace")


def _line(text: str, codepage: str = "CP860") -> bytes:
    """Codifica uma linha de texto + LF."""
    return _encode(text, codepage) + b"\n"


def _separator(char: str = "-", codepage: str = "CP860") -> bytes:
    """Linha separadora."""
    return _line(char * COLS, codepage)


def _center(text: str, codepage: str = "CP860") -> bytes:
    """Texto centralizado (via ESC/POS alignment)."""
    return ALIGN_CENTER + _line(text, codepage) + ALIGN_LEFT


def _right_align(left: str, right: str, codepage: str = "CP860") -> bytes:
    """Duas colunas: texto à esquerda + valor à direita."""
    spaces = COLS - len(left) - len(right)
    if spaces < 1:
        spaces = 1
    return _line(left + " " * spaces + right, codepage)


# ── Dados de simulação ───────────────────────────────────────────────────────

NOMES_CLIENTES = [
    "Maria Silva", "Joao Santos", "Ana Oliveira", "Pedro Costa",
    "Lucia Ferreira", "Carlos Souza", "Fernanda Lima", "Rafael Pereira",
    "Juliana Alves", "Bruno Rodrigues", "Patricia Mendes", "Marcos Ribeiro",
]

ENDERECOS = [
    "Rua das Flores, 123 - Centro",
    "Av. Brasil, 456 Ap 302 - Jardim America",
    "Rua Sao Paulo, 789 - Vila Nova",
    "Travessa do Comercio, 42 - Boa Vista",
    "Av. Atlantica, 1500 Bl B - Copacabana",
    "Rua Augusta, 234 - Consolacao",
]

ITENS_CARDAPIO = [
    ("Pizza Calabresa G", 45.90),
    ("Pizza Margherita G", 42.90),
    ("Pizza 4 Queijos M", 38.50),
    ("Hamburguer Artesanal", 32.90),
    ("X-Bacon Especial", 28.90),
    ("Coca-Cola 2L", 12.00),
    ("Guarana Antarctica 1L", 8.50),
    ("Suco Natural Laranja", 10.00),
    ("Batata Frita Grande", 18.90),
    ("Onion Rings", 15.90),
    ("Acai 500ml", 22.00),
    ("Pastel Carne G", 9.50),
    ("Coxinha (unid)", 6.50),
    ("Esfiha Carne (3 unid)", 14.90),
    ("Combo Familia (4 hamb + batata + refri)", 99.90),
]


def _random_order_id() -> str:
    return str(random.randint(1000, 9999))


def _random_items(min_items: int = 1, max_items: int = 5) -> list:
    count = random.randint(min_items, max_items)
    items = []
    for _ in range(count):
        name, price = random.choice(ITENS_CARDAPIO)
        qty = random.choice([1, 1, 1, 2, 3])
        items.append((name, qty, price))
    return items


def _random_obs() -> str:
    obs_list = [
        "", "", "",  # Maioria sem obs
        "SEM CEBOLA",
        "BEM PASSADO",
        "EXTRA QUEIJO",
        "SEM TOMATE, SEM ALFACE",
        "TROCO PARA 100",
        "INTERFONE 302",
    ]
    return random.choice(obs_list)


# ── Geradores de recibo por plataforma ────────────────────────────────────────

def gerar_recibo_ifood(codepage: str = "CP860") -> bytes:
    """Gera recibo no formato iFood (header *** IFOOD ***, separadores =)."""
    order_id = _random_order_id()
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    items = _random_items(2, 5)
    obs = _random_obs()
    agora = datetime.now()

    buf = bytearray()
    buf += INIT
    buf += CODEPAGE_CP860

    # Header iFood
    buf += ALIGN_CENTER
    buf += BOLD_ON + DOUBLE_BOTH
    buf += _line("*** IFOOD ***", codepage)
    buf += NORMAL_SIZE + BOLD_OFF
    buf += _line(f"Pedido #{order_id}", codepage)
    buf += ALIGN_LEFT
    buf += _line("=" * COLS, codepage)

    # Data/hora
    buf += _line(f"Data: {agora.strftime('%d/%m/%Y %H:%M')}", codepage)
    buf += _line(f"Cliente: {cliente}", codepage)
    buf += _line(f"Entrega: {endereco}", codepage)
    buf += _line("=" * COLS, codepage)

    # Itens
    buf += BOLD_ON
    buf += _line("ITENS DO PEDIDO", codepage)
    buf += BOLD_OFF
    buf += _line("-" * COLS, codepage)

    subtotal = 0.0
    for name, qty, price in items:
        total = qty * price
        subtotal += total
        buf += _line(f"{qty}x {name}", codepage)
        buf += _right_align("", f"R$ {total:.2f}", codepage)

    buf += _line("-" * COLS, codepage)

    # Totais
    taxa_entrega = random.choice([0.00, 5.99, 7.99, 9.99])
    total_final = subtotal + taxa_entrega

    buf += _right_align("Subtotal:", f"R$ {subtotal:.2f}", codepage)
    buf += _right_align("Taxa entrega:", f"R$ {taxa_entrega:.2f}", codepage)
    buf += BOLD_ON
    buf += _right_align("TOTAL:", f"R$ {total_final:.2f}", codepage)
    buf += BOLD_OFF
    buf += _line("=" * COLS, codepage)

    # Pagamento
    pagamento = random.choice(["Cartao credito", "Cartao debito", "PIX", "Dinheiro"])
    buf += _line(f"Pagamento: {pagamento}", codepage)

    if obs:
        buf += _line("=" * COLS, codepage)
        buf += BOLD_ON
        buf += _line(f"OBS: {obs}", codepage)
        buf += BOLD_OFF

    buf += _line("=" * COLS, codepage)
    buf += ALIGN_CENTER
    buf += _line("iFood - Delivery de Comida", codepage)
    buf += ALIGN_LEFT

    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


def gerar_recibo_rappi(codepage: str = "CP860") -> bytes:
    """Gera recibo no formato Rappi (separadores *, formato Qtd x Item ... R$)."""
    order_id = _random_order_id()
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    items = _random_items(1, 4)
    obs = _random_obs()
    agora = datetime.now()

    buf = bytearray()
    buf += INIT
    buf += CODEPAGE_CP860

    # Header Rappi
    buf += ALIGN_CENTER
    buf += BOLD_ON + DOUBLE_BOTH
    buf += _line("RAPPI", codepage)
    buf += NORMAL_SIZE + BOLD_OFF
    buf += _line("Novo Pedido!", codepage)
    buf += ALIGN_LEFT
    buf += _line("*" * COLS, codepage)

    buf += _line(f"Pedido: RAP-{order_id}", codepage)
    buf += _line(f"{agora.strftime('%d/%m/%Y  %H:%M:%S')}", codepage)
    buf += _line("*" * COLS, codepage)

    buf += _line(f"CLIENTE: {cliente}", codepage)
    buf += _line(f"END: {endereco}", codepage)
    buf += _line("*" * COLS, codepage)

    # Itens
    subtotal = 0.0
    for name, qty, price in items:
        total = qty * price
        subtotal += total
        valor_str = f"R${total:.2f}"
        buf += _right_align(f"{qty} x {name}", valor_str, codepage)

    buf += _line("*" * COLS, codepage)

    taxa = random.choice([0.00, 4.99, 6.99])
    total_final = subtotal + taxa

    buf += _right_align("Subtotal", f"R${subtotal:.2f}", codepage)
    buf += _right_align("Entrega", f"R${taxa:.2f}", codepage)
    buf += BOLD_ON
    buf += _right_align("TOTAL", f"R${total_final:.2f}", codepage)
    buf += BOLD_OFF

    if obs:
        buf += _line("*" * COLS, codepage)
        buf += _line(f"*** {obs} ***", codepage)

    buf += _line("*" * COLS, codepage)
    buf += ALIGN_CENTER
    buf += _line("Rappi - Tudo num toque", codepage)
    buf += ALIGN_LEFT

    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


def gerar_recibo_99food(codepage: str = "CP860") -> bytes:
    """Gera recibo no formato 99Food (separadores +, linhas de desconto)."""
    order_id = _random_order_id()
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    items = _random_items(1, 3)
    agora = datetime.now()

    buf = bytearray()
    buf += INIT
    buf += CODEPAGE_CP860

    # Header 99Food
    buf += ALIGN_CENTER
    buf += BOLD_ON + DOUBLE_BOTH
    buf += _line("99 FOOD", codepage)
    buf += NORMAL_SIZE + BOLD_OFF
    buf += _line(f"Pedido {order_id}", codepage)
    buf += ALIGN_LEFT
    buf += _line("+" * COLS, codepage)

    buf += _line(f"Data: {agora.strftime('%d/%m/%Y %H:%M')}", codepage)
    buf += _line(f"Cliente: {cliente}", codepage)
    buf += _line(f"Endereco: {endereco}", codepage)
    buf += _line("+" * COLS, codepage)

    # Itens
    subtotal = 0.0
    for name, qty, price in items:
        total = qty * price
        subtotal += total
        buf += _line(f"  {qty}x {name}", codepage)
        buf += _right_align("", f"R$ {total:.2f}", codepage)

    buf += _line("+" * COLS, codepage)

    # Desconto aleatório
    desconto = 0.0
    if random.random() < 0.4:
        desconto = round(random.uniform(3.0, 15.0), 2)
        buf += _right_align("Desconto 99:", f"-R$ {desconto:.2f}", codepage)

    taxa = random.choice([0.00, 3.99, 5.99])
    total_final = subtotal - desconto + taxa

    buf += _right_align("Subtotal:", f"R$ {subtotal:.2f}", codepage)
    buf += _right_align("Taxa entrega:", f"R$ {taxa:.2f}", codepage)
    buf += BOLD_ON + DOUBLE_HEIGHT
    buf += _right_align("TOTAL:", f"R$ {total_final:.2f}", codepage)
    buf += NORMAL_SIZE + BOLD_OFF

    buf += _line("+" * COLS, codepage)
    buf += ALIGN_CENTER
    buf += _line("99Food - Pede que chega", codepage)
    buf += ALIGN_LEFT

    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


def gerar_recibo_uber_eats(codepage: str = "CP860") -> bytes:
    """Gera recibo no formato Uber Eats (separadores =, formato simples)."""
    order_id = _random_order_id()
    cliente = random.choice(NOMES_CLIENTES)
    endereco = random.choice(ENDERECOS)
    items = _random_items(1, 4)
    obs = _random_obs()
    agora = datetime.now()

    buf = bytearray()
    buf += INIT
    buf += CODEPAGE_CP860

    # Header Uber Eats
    buf += ALIGN_CENTER
    buf += BOLD_ON + DOUBLE_BOTH
    buf += _line("Uber Eats", codepage)
    buf += NORMAL_SIZE
    buf += _line("NOVO PEDIDO", codepage)
    buf += BOLD_OFF
    buf += ALIGN_LEFT
    buf += _line("=" * COLS, codepage)

    buf += _line(f"Pedido: UE-{order_id}", codepage)
    buf += _line(f"Horario: {agora.strftime('%H:%M')}  {agora.strftime('%d/%m/%Y')}", codepage)
    buf += _line("=" * COLS, codepage)

    buf += BOLD_ON
    buf += _line(cliente.upper(), codepage)
    buf += BOLD_OFF
    buf += _line(endereco, codepage)

    tel = f"(11) 9{random.randint(1000, 9999)}-{random.randint(1000, 9999)}"
    buf += _line(f"Tel: {tel}", codepage)
    buf += _line("=" * COLS, codepage)

    # Itens
    subtotal = 0.0
    for name, qty, price in items:
        total = qty * price
        subtotal += total
        buf += _line(f"{qty}x {name}", codepage)
        buf += ALIGN_RIGHT
        buf += _line(f"R$ {total:.2f}", codepage)
        buf += ALIGN_LEFT

    buf += _line("=" * COLS, codepage)

    taxa = random.choice([0.00, 5.99, 8.99])
    total_final = subtotal + taxa

    buf += _right_align("Subtotal", f"R$ {subtotal:.2f}", codepage)
    buf += _right_align("Entrega", f"R$ {taxa:.2f}", codepage)
    buf += _line("=" * COLS, codepage)
    buf += BOLD_ON + DOUBLE_HEIGHT
    buf += ALIGN_CENTER
    buf += _line(f"TOTAL  R$ {total_final:.2f}", codepage)
    buf += ALIGN_LEFT
    buf += NORMAL_SIZE + BOLD_OFF

    if obs:
        buf += _line("=" * COLS, codepage)
        buf += _line(f"Obs: {obs}", codepage)

    buf += _line("=" * COLS, codepage)
    buf += ALIGN_CENTER
    buf += _line("Uber Eats", codepage)
    buf += ALIGN_LEFT

    buf += FEED_3
    buf += CUT_PARTIAL

    return bytes(buf)


# ── Mapa de plataformas ──────────────────────────────────────────────────────

PLATAFORMAS = {
    "ifood": ("iFood", gerar_recibo_ifood),
    "rappi": ("Rappi", gerar_recibo_rappi),
    "99food": ("99Food", gerar_recibo_99food),
    "ubereats": ("Uber Eats", gerar_recibo_uber_eats),
}


def listar_impressoras_windows() -> list:
    """Lista nomes de todas as impressoras instaladas no Windows."""
    try:
        import win32print
        # PRINTER_ENUM_LOCAL (2) + PRINTER_ENUM_CONNECTIONS (4) = 6
        printers = win32print.EnumPrinters(2 | 4)
        return [p[2] for p in printers]
    except ImportError:
        return []
    except Exception:
        return []


def resolver_impressora(printer_name: str) -> Optional[str]:
    """Verifica se a impressora existe no Windows pelo nome EXATO.

    Retorna o nome se encontrada, None caso contrario.
    Sem fuzzy matching: em producao o Printer Agent usa o nome exato da API
    do Windows, entao o teste cego deve usar as mesmas regras.
    """
    impressoras = listar_impressoras_windows()
    if printer_name in impressoras:
        return printer_name
    return None


def enviar_recibo_spooler(
    raw_bytes: bytes,
    printer_name: str = PRINTER_NAME,
    doc_name: str = "Recibo_Virtual",
) -> bool:
    """Envia bytes ESC/POS pelo spooler do Windows via win32print.

    Returns True se enviou com sucesso, False se falhou.
    """
    try:
        import win32print

        handle = win32print.OpenPrinter(printer_name)
        try:
            win32print.StartDocPrinter(handle, 1, (doc_name, None, "RAW"))
            try:
                win32print.StartPagePrinter(handle)
                win32print.WritePrinter(handle, raw_bytes)
                win32print.EndPagePrinter(handle)
            finally:
                win32print.EndDocPrinter(handle)
        finally:
            win32print.ClosePrinter(handle)
        return True
    except ImportError:
        print("[ERRO] pywin32 nao instalado. Instale com: pip install pywin32")
        return False
    except Exception as e:
        print(f"[ERRO] Falha ao enviar para '{printer_name}': {e}")
        return False


def simular_pedidos(
    platform: Optional[str] = None,
    count: int = 1,
    interval: float = 2.0,
    printer_name: str = PRINTER_NAME,
    save_local: bool = False,
    output_dir: str = "output",
) -> int:
    """Simula pedidos de delivery enviando recibos ESC/POS pelo spooler.

    Args:
        platform: 'ifood', 'rappi', '99food', 'ubereats' ou None (todas).
        count: Número de recibos por plataforma.
        interval: Segundos entre cada envio.
        printer_name: Nome da impressora no Windows.
        save_local: Se True, também salva .bin localmente.
        output_dir: Diretório para salvar .bin se save_local=True.

    Returns:
        Número de recibos enviados com sucesso.
    """
    if platform:
        platforms_to_use = [platform.lower()]
    else:
        platforms_to_use = list(PLATAFORMAS.keys())

    enviados = 0
    total = len(platforms_to_use) * count

    # ── Validar impressora antes de simular ───────────────────────
    # Teste cego: nome EXATO. Em producao o Printer Agent usa o mesmo nome
    # que vem de EnumPrinters — se aqui nao achar, a instalacao falhou.
    if resolver_impressora(printer_name) is None:
        impressoras_disponiveis = listar_impressoras_windows()
        print(f"\n  ═══════════════════════════════════════════════════════════")
        print(f"   [ERRO CRITICO] Impressora '{printer_name}' NAO existe!")
        print(f"  ═══════════════════════════════════════════════════════════")
        print()
        if impressoras_disponiveis:
            print("  Impressoras instaladas no seu Windows:")
            for nome in impressoras_disponiveis:
                print(f"     - {nome}")
        else:
            print("  Nenhuma impressora encontrada no Windows.")
        print()
        print("  Isto significa que INSTALAR.bat NAO foi concluido com sucesso.")
        print()
        print("  SOLUCAO:")
        print("    1. Feche esta janela")
        print("    2. Clique com BOTAO DIREITO em INSTALAR.bat")
        print("    3. Escolha 'Executar como administrador'")
        print("    4. Aceite o UAC e leia TODAS as mensagens")
        print("    5. Se houver erro no driver, siga as instrucoes do script")
        print("    6. So depois volte a rodar SIMULAR.bat")
        print()
        return 0

    print(f"\n  Simulando {total} recibo(s) para '{printer_name}'...\n")

    for plat_key in platforms_to_use:
        if plat_key not in PLATAFORMAS:
            print(f"  [AVISO] Plataforma '{plat_key}' desconhecida. Opcoes: {', '.join(PLATAFORMAS.keys())}")
            continue

        plat_name, generator = PLATAFORMAS[plat_key]

        for i in range(count):
            raw_bytes = generator()
            order_id = f"{plat_name}_Pedido_{random.randint(1000, 9999)}"

            # Tentar enviar pelo spooler
            ok = enviar_recibo_spooler(raw_bytes, printer_name, doc_name=order_id)

            if ok:
                enviados += 1
                print(f"  [{enviados}/{total}] {order_id} -> '{printer_name}' OK ({len(raw_bytes)} bytes)")
            else:
                # Fallback: salvar localmente
                save_local = True
                print(f"  [{enviados}/{total}] {order_id} -> FALHA spooler (salvando local)")

            if save_local:
                from pathlib import Path
                out = Path(output_dir)
                out.mkdir(parents=True, exist_ok=True)
                path = out / f"{order_id}.bin"
                path.write_bytes(raw_bytes)
                print(f"    -> Salvo: {path}")

            if i < count - 1 or plat_key != platforms_to_use[-1]:
                time.sleep(interval)

    print(f"\n  Concluido: {enviados}/{total} recibos enviados.\n")
    return enviados
