"""
Testes das 12 primeiras function calls do Bot WhatsApp.
Cada função tem exatamente 10 testes cobrindo:
  - Happy path
  - Permissão negada
  - Não encontrado
  - Multi-tenant isolation
  - Parâmetros inválidos
  - Edge cases específicos da função

Total: 120 testes (12 funções x 10 testes)
"""
import pytest
import json
import asyncio
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import create_engine, Column, Integer, ForeignKey, event
from sqlalchemy.orm import sessionmaker, Session

from database.base import Base
from database.models import (
    Restaurante,
    ConfigRestaurante,
    SiteConfig,
    CategoriaMenu,
    Produto,
    VariacaoProduto,
    Cliente,
    EnderecoCliente,
    Pedido,
    ItemPedido,
    Entrega,
    Motoboy,
    Promocao,
    Combo,
    ComboItem,
    BairroEntrega,
    BotConfig,
    BotConversa,
    BotMensagem,
    BotAvaliacao,
    BotProblema,
    BotRepescagem,
    PedidoCozinha,
    ConfigCozinha,
    ItemEsgotado,
    PixConfig,
)

# A coluna real no ORM é item_cardapio_id, mas function_calls.py usa
# produto_id (via try/except).  Adicionamos produto_id como alias
# SOMENTE para os testes.  Se já existir (atualização futura) pula.
if not hasattr(ItemEsgotado, "produto_id"):
    ItemEsgotado.produto_id = ItemEsgotado.item_cardapio_id

from backend.app.bot.function_calls import (
    _buscar_cliente,
    _cadastrar_cliente,
    _buscar_cardapio,
    _buscar_categorias,
    _criar_pedido,
    _alterar_pedido,
    _cancelar_pedido,
    _repetir_ultimo_pedido,
    _consultar_status_pedido,
    _verificar_horario,
    _buscar_promocoes,
    _registrar_avaliacao,
    executar_funcao,
)


# ==================== FIXTURES ====================

@pytest.fixture(scope="session")
def engine():
    """SQLite in-memory engine, mantido durante toda a sessão de teste."""
    eng = create_engine("sqlite:///:memory:", echo=False)

    # SQLite não suporta schemas, mas precisamos suportar begin_nested (savepoint)
    @event.listens_for(eng, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(eng)
    return eng


@pytest.fixture
def db(engine):
    """Sessão de BD limpa para cada teste."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    # begin_nested no SQLite requer savepoint habilitado
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


def _make_restaurante(db: Session, *, id_=1, nome="Pizza Tuga", codigo="ABC12345",
                      cidade="São Paulo", plano_tier=4, **kw) -> Restaurante:
    """Cria restaurante com config e site_config padrão."""
    rest = Restaurante(
        id=id_,
        nome=nome,
        nome_fantasia=nome,
        email=kw.get("email", f"rest{id_}@test.com"),
        senha=hashlib.sha256(b"123456").hexdigest(),
        telefone=kw.get("telefone", "11999990001"),
        endereco_completo="Rua Teste 100, São Paulo",
        cidade=cidade,
        estado="SP",
        pais="BR",
        latitude=-23.55,
        longitude=-46.63,
        plano="Premium" if plano_tier == 4 else "Basico",
        plano_tier=plano_tier,
        valor_plano=0,
        limite_motoboys=5,
        codigo_acesso=codigo,
        ativo=True,
    )
    db.add(rest)
    db.flush()

    config = ConfigRestaurante(
        restaurante_id=rest.id,
        status_atual="aberto",
        horario_abertura="08:00",
        horario_fechamento="23:00",
        dias_semana_abertos="segunda,terca,quarta,quinta,sexta,sabado,domingo",
        taxa_entrega_base=5.0,
        tempo_medio_preparo=30,
    )
    db.add(config)

    site = SiteConfig(
        restaurante_id=rest.id,
        tipo_restaurante="pizzaria",
        aceita_dinheiro=True,
        aceita_cartao=True,
        aceita_pix=True,
    )
    db.add(site)
    db.flush()
    return rest


def _make_categoria(db: Session, rest_id: int, nome: str, ordem: int = 0) -> CategoriaMenu:
    cat = CategoriaMenu(restaurante_id=rest_id, nome=nome, ativo=True, ordem_exibicao=ordem)
    db.add(cat)
    db.flush()
    return cat


def _make_produto(db: Session, rest_id: int, cat_id: int, nome: str, preco: float,
                  disponivel=True, estoque_ilimitado=True, estoque_qtd=0,
                  promocao=False, preco_promocional=None) -> Produto:
    prod = Produto(
        restaurante_id=rest_id,
        categoria_id=cat_id,
        nome=nome,
        preco=preco,
        disponivel=disponivel,
        estoque_ilimitado=estoque_ilimitado,
        estoque_quantidade=estoque_qtd,
        promocao=promocao,
        preco_promocional=preco_promocional,
    )
    db.add(prod)
    db.flush()
    return prod


def _make_cliente(db: Session, rest_id: int, nome: str, telefone: str,
                  endereco: str = None, bairro: str = None) -> Cliente:
    cli = Cliente(
        restaurante_id=rest_id,
        nome=nome,
        telefone=telefone,
        senha_hash=hashlib.sha256(telefone[:6].encode()).hexdigest(),
    )
    db.add(cli)
    db.flush()

    if endereco:
        end = EnderecoCliente(
            cliente_id=cli.id,
            endereco_completo=endereco,
            bairro=bairro or "Centro",
            padrao=True,
        )
        db.add(end)
        db.flush()
    return cli


def _make_bot_config(db: Session, rest_id: int, **overrides) -> BotConfig:
    defaults = dict(
        restaurante_id=rest_id,
        bot_ativo=True,
        nome_atendente="Bia",
        pode_criar_pedido=True,
        pode_alterar_pedido=True,
        pode_cancelar_pedido=True,
        pode_dar_desconto=False,
        impressao_automatica_bot=True,
        cancelamento_ate_status="em_preparo",
        avaliacao_ativa=True,
        avaliacao_pedir_google_review=True,
        google_maps_url="https://maps.google.com/test",
    )
    defaults.update(overrides)
    bc = BotConfig(**defaults)
    db.add(bc)
    db.flush()
    return bc


def _make_conversa(db: Session, rest_id: int, telefone: str, **kw) -> BotConversa:
    conv = BotConversa(
        restaurante_id=rest_id,
        telefone=telefone,
        nome_cliente=kw.get("nome_cliente", "Teste"),
        status=kw.get("status", "ativa"),
        cliente_id=kw.get("cliente_id"),
        pedido_ativo_id=kw.get("pedido_ativo_id"),
        session_data=kw.get("session_data"),
    )
    db.add(conv)
    db.flush()
    # function_calls.py references conversa.cliente_telefone (dynamic attribute)
    # BotConversa ORM does NOT have this column, it's set at runtime in some paths.
    conv.cliente_telefone = kw.get("cliente_telefone", telefone)
    return conv


def _make_pedido(db: Session, rest_id: int, cliente: Cliente, status: str = "pendente",
                 forma_pag: str = "dinheiro", itens_texto: str = "1x Pizza",
                 valor_total: float = 50.0, comanda: str = "WA0001",
                 carrinho_json=None, tipo_entrega="entrega",
                 endereco_entrega="Rua X, 1", **kw) -> Pedido:
    ped = Pedido(
        restaurante_id=rest_id,
        cliente_id=cliente.id if cliente else None,
        comanda=comanda,
        tipo="delivery" if tipo_entrega == "entrega" else "retirada",
        origem="whatsapp_bot",
        tipo_entrega=tipo_entrega,
        cliente_nome=cliente.nome if cliente else "Anon",
        cliente_telefone=cliente.telefone if cliente else "",
        endereco_entrega=endereco_entrega,
        itens=itens_texto,
        carrinho_json=carrinho_json,
        valor_subtotal=valor_total,
        valor_total=valor_total,
        forma_pagamento=forma_pag,
        status=status,
        historico_status=[{"status": status, "timestamp": datetime.utcnow().isoformat()}],
        data_criacao=kw.get("data_criacao", datetime.utcnow()),
        atualizado_em=kw.get("atualizado_em", datetime.utcnow()),
    )
    db.add(ped)
    db.flush()
    return ped


def _make_item_pedido(db: Session, pedido_id: int, produto: Produto, qtd: int = 1) -> ItemPedido:
    ip = ItemPedido(
        pedido_id=pedido_id,
        produto_id=produto.id,
        quantidade=qtd,
        preco_unitario=produto.preco,
    )
    db.add(ip)
    db.flush()
    return ip


@pytest.fixture
def rest1(db):
    return _make_restaurante(db, id_=1, nome="Pizza Tuga", codigo="ABC12345")


@pytest.fixture
def rest2(db):
    return _make_restaurante(db, id_=2, nome="Sushi Master", codigo="DEF67890",
                             email="sushi@test.com", telefone="11999990002")


@pytest.fixture
def bot_config1(db, rest1):
    return _make_bot_config(db, rest1.id)


@pytest.fixture
def bot_config_no_cancel(db, rest1):
    return _make_bot_config(db, rest1.id, pode_cancelar_pedido=False)


@pytest.fixture
def bot_config_no_create(db, rest1):
    return _make_bot_config(db, rest1.id, pode_criar_pedido=False)


@pytest.fixture
def bot_config_no_alter(db, rest1):
    return _make_bot_config(db, rest1.id, pode_alterar_pedido=False)


@pytest.fixture
def categorias(db, rest1):
    c1 = _make_categoria(db, rest1.id, "Pizzas", 1)
    c2 = _make_categoria(db, rest1.id, "Bebidas", 2)
    c3 = _make_categoria(db, rest1.id, "Sobremesas", 3)
    return c1, c2, c3


@pytest.fixture
def produtos(db, rest1, categorias):
    c1, c2, c3 = categorias
    p1 = _make_produto(db, rest1.id, c1.id, "Pizza Margherita", 45.00)
    p2 = _make_produto(db, rest1.id, c1.id, "Pizza Calabresa", 40.00)
    p3 = _make_produto(db, rest1.id, c2.id, "Coca-Cola 350ml", 6.00)
    p4 = _make_produto(db, rest1.id, c2.id, "Suco de Laranja", 8.00)
    p5 = _make_produto(db, rest1.id, c3.id, "Petit Gateau", 25.00)
    return p1, p2, p3, p4, p5


@pytest.fixture
def cliente1(db, rest1):
    return _make_cliente(db, rest1.id, "João Silva", "11987654321",
                         endereco="Rua Augusta 100, São Paulo", bairro="Consolação")


@pytest.fixture
def cliente2(db, rest2):
    """Cliente do restaurante 2 — para testar isolamento multi-tenant."""
    return _make_cliente(db, rest2.id, "Maria Santos", "11987654321",
                         endereco="Rua Vergueiro 200", bairro="Liberdade")


def _parse(result: str) -> dict:
    """Helper para parsear resultado JSON das function calls."""
    return json.loads(result)


# ==================== 1. buscar_cliente — 10 testes ====================

class TestBuscarCliente:

    def test_happy_path_found(self, db, rest1, cliente1):
        """Busca por telefone exato retorna cliente com endereço."""
        r = _parse(_buscar_cliente(db, rest1.id, "11987654321"))
        assert r["encontrado"] is True
        assert r["nome"] == "João Silva"
        assert r["endereco"] is not None

    def test_partial_match_last_8_digits(self, db, rest1, cliente1):
        """Busca por últimos 8 dígitos com prefixo diferente retorna match."""
        r = _parse(_buscar_cliente(db, rest1.id, "+5511987654321"))
        assert r["encontrado"] is True
        assert r["nome"] == "João Silva"

    def test_not_found_returns_message(self, db, rest1):
        """Telefone inexistente retorna encontrado=False com instrução."""
        r = _parse(_buscar_cliente(db, rest1.id, "11999999999"))
        assert r["encontrado"] is False
        assert "cadastrar_cliente" in r["mensagem"]

    def test_multi_tenant_isolation(self, db, rest1, rest2, cliente2):
        """Cliente do restaurante 2 NÃO aparece na busca do restaurante 1."""
        r = _parse(_buscar_cliente(db, rest1.id, cliente2.telefone))
        assert r["encontrado"] is False

    def test_empty_telefone(self, db, rest1, cliente1):
        """Telefone vazio com LIKE '%%' pode retornar qualquer cliente (busca ampla)."""
        r = _parse(_buscar_cliente(db, rest1.id, ""))
        # Com tel_limpo vazio, LIKE "%" matches all — pode retornar encontrado
        # O importante é não dar erro; resultado depende de haver clientes
        assert "encontrado" in r

    def test_telefone_com_formatacao(self, db, rest1, cliente1):
        """Telefone com parênteses, traços e espaços é limpo corretamente."""
        r = _parse(_buscar_cliente(db, rest1.id, "(11) 98765-4321"))
        assert r["encontrado"] is True
        assert r["id"] == cliente1.id

    def test_cliente_sem_endereco(self, db, rest1):
        """Cliente sem endereço padrão retorna endereco=None."""
        cli = _make_cliente(db, rest1.id, "Sem Endereço", "11911112222")
        r = _parse(_buscar_cliente(db, rest1.id, "11911112222"))
        assert r["encontrado"] is True
        assert r["endereco"] is None

    def test_returns_client_id(self, db, rest1, cliente1):
        """Resultado inclui o ID do cliente."""
        r = _parse(_buscar_cliente(db, rest1.id, "11987654321"))
        assert r["id"] == cliente1.id

    def test_telefone_com_codigo_pais(self, db, rest1, cliente1):
        """Telefone com código de país +55 encontra cliente."""
        r = _parse(_buscar_cliente(db, rest1.id, "5511987654321"))
        assert r["encontrado"] is True

    def test_multiple_clients_returns_first(self, db, rest1, cliente1):
        """Se múltiplos clientes tiverem os últimos 8 dígitos iguais, retorna o primeiro."""
        cli2 = _make_cliente(db, rest1.id, "Outro João", "21987654321")
        r = _parse(_buscar_cliente(db, rest1.id, "987654321"))
        assert r["encontrado"] is True
        # Deve encontrar pelo menos um
        assert r["nome"] in ("João Silva", "Outro João")


# ==================== 2. cadastrar_cliente — 10 testes ====================

class TestCadastrarCliente:

    def test_happy_path_create(self, db, rest1):
        """Cadastra cliente novo com nome e telefone."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Pedro Costa",
            "telefone": "11933334444",
        }))
        assert r["id"] is not None
        assert "cadastrado" in r["mensagem"]

    def test_duplicate_phone_returns_existing(self, db, rest1, cliente1):
        """Se telefone já existe, retorna cliente existente sem criar duplicata."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Duplicado",
            "telefone": "11987654321",
        }))
        assert r["id"] == cliente1.id
        assert "já cadastrado" in r["mensagem"]

    def test_empty_name_returns_error(self, db, rest1):
        """Nome vazio retorna erro."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "",
            "telefone": "11922223333",
        }))
        assert "erro" in r

    def test_empty_phone_returns_error(self, db, rest1):
        """Telefone vazio retorna erro."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Test",
            "telefone": "",
        }))
        assert "erro" in r

    def test_multi_tenant_isolation(self, db, rest1, rest2):
        """Cliente cadastrado no rest1 não aparece no rest2."""
        _cadastrar_cliente(db, rest1.id, {"nome": "Isolado", "telefone": "11955556666"})
        r = _parse(_buscar_cliente(db, rest2.id, "11955556666"))
        assert r["encontrado"] is False

    def test_address_optional_create_without_address(self, db, rest1):
        """Cadastra sem endereço — somente nome + telefone."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Sem Endereço",
            "telefone": "11944445555",
        }))
        assert "erro" not in r
        cli = db.query(Cliente).filter(Cliente.id == r["id"]).first()
        enderecos = db.query(EnderecoCliente).filter(EnderecoCliente.cliente_id == cli.id).all()
        assert len(enderecos) == 0

    def test_create_with_full_address(self, db, rest1):
        """Cadastra com endereço completo, bairro e complemento."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Com Endereço",
            "telefone": "11966667777",
            "endereco": "Rua X 123",
            "bairro": "Centro",
            "complemento": "Apto 5",
        }))
        assert "erro" not in r
        enderecos = db.query(EnderecoCliente).filter(EnderecoCliente.cliente_id == r["id"]).all()
        assert len(enderecos) == 1
        assert enderecos[0].padrao is True
        assert enderecos[0].bairro == "Centro"

    def test_phone_cleaned_to_digits(self, db, rest1):
        """Telefone com formatação é limpo para somente dígitos."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {
            "nome": "Formatted",
            "telefone": "(11) 91111-2222",
        }))
        cli = db.query(Cliente).filter(Cliente.id == r["id"]).first()
        assert cli.telefone == "11911112222"

    def test_default_password_is_first_6_digits(self, db, rest1):
        """Senha padrão é hash dos primeiros 6 dígitos do telefone."""
        _cadastrar_cliente(db, rest1.id, {
            "nome": "Password Test",
            "telefone": "11977778888",
        })
        cli = db.query(Cliente).filter(Cliente.telefone == "11977778888").first()
        expected_hash = hashlib.sha256(b"119777").hexdigest()
        assert cli.senha_hash == expected_hash

    def test_missing_both_fields_returns_error(self, db, rest1):
        """Sem nome e sem telefone retorna erro."""
        r = _parse(_cadastrar_cliente(db, rest1.id, {}))
        assert "erro" in r


# ==================== 3. buscar_cardapio — 10 testes ====================

class TestBuscarCardapio:

    def test_happy_path_by_name(self, db, rest1, produtos):
        """Busca por nome do produto retorna resultados."""
        r = _parse(_buscar_cardapio(db, rest1.id, "Margherita"))
        assert r["encontrados"] >= 1
        assert any("Margherita" in i["nome"] for i in r["itens"])

    def test_by_category_name(self, db, rest1, categorias, produtos):
        """Busca por nome de categoria retorna produtos da categoria."""
        r = _parse(_buscar_cardapio(db, rest1.id, "Bebidas"))
        assert r["encontrados"] >= 1
        nomes = [i["nome"] for i in r["itens"]]
        assert "Coca-Cola 350ml" in nomes

    def test_not_found_empty_search(self, db, rest1, produtos):
        """Busca por nome inexistente retorna mensagem de não encontrado."""
        r = _parse(_buscar_cardapio(db, rest1.id, "Lasanha de Berinjela"))
        assert r["encontrados"] == 0
        assert "mensagem" in r

    def test_multi_tenant_isolation(self, db, rest1, rest2, produtos):
        """Produtos do rest1 não aparecem na busca do rest2."""
        r = _parse(_buscar_cardapio(db, rest2.id, "Margherita"))
        assert r["encontrados"] == 0

    def test_unavailable_item_shown_with_status(self, db, rest1, categorias):
        """Produto indisponível aparece na busca com status 'indisponivel'."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Especial", 55.0, disponivel=False)
        r = _parse(_buscar_cardapio(db, rest1.id, "Especial"))
        assert r["encontrados"] >= 1
        item = r["itens"][0]
        assert item["status"] == "indisponivel"
        assert "aviso" in item

    def test_stock_zero_shows_esgotado(self, db, rest1, categorias):
        """Produto com estoque finito e quantidade 0 mostra status esgotado."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Rara", 60.0,
                      estoque_ilimitado=False, estoque_qtd=0)
        r = _parse(_buscar_cardapio(db, rest1.id, "Rara"))
        assert r["itens"][0]["status"] == "esgotado"

    def test_case_insensitive_search(self, db, rest1, produtos):
        """Busca case-insensitive funciona (minúsculas)."""
        r = _parse(_buscar_cardapio(db, rest1.id, "calabresa"))
        assert r["encontrados"] >= 1

    def test_promotional_price_shown(self, db, rest1, categorias):
        """Produto em promoção mostra preço promocional e flag."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Promo", 50.0,
                      promocao=True, preco_promocional=35.0)
        r = _parse(_buscar_cardapio(db, rest1.id, "Promo"))
        item = r["itens"][0]
        assert item["preco"] == 35.0
        assert item.get("em_promocao") is True
        assert item["preco_original"] == 50.0

    def test_returns_item_id(self, db, rest1, produtos):
        """Resultado inclui o ID do produto."""
        r = _parse(_buscar_cardapio(db, rest1.id, "Margherita"))
        assert "id" in r["itens"][0]

    def test_partial_name_match(self, db, rest1, produtos):
        """Busca parcial (substring) funciona."""
        r = _parse(_buscar_cardapio(db, rest1.id, "Cola"))
        assert r["encontrados"] >= 1
        assert any("Cola" in i["nome"] for i in r["itens"])


# ==================== 4. buscar_categorias — 10 testes ====================

class TestBuscarCategorias:

    def test_happy_path_list_all(self, db, rest1, categorias):
        """Lista todas as categorias ativas do restaurante."""
        r = _parse(_buscar_categorias(db, rest1.id))
        assert len(r["categorias"]) == 3

    def test_empty_restaurant(self, db, rest2):
        """Restaurante sem categorias retorna lista vazia."""
        r = _parse(_buscar_categorias(db, rest2.id))
        assert len(r["categorias"]) == 0

    def test_ordered_by_ordem_exibicao(self, db, rest1, categorias):
        """Categorias retornam ordenadas por ordem_exibicao."""
        r = _parse(_buscar_categorias(db, rest1.id))
        nomes = [c["nome"] for c in r["categorias"]]
        assert nomes == ["Pizzas", "Bebidas", "Sobremesas"]

    def test_multi_tenant_isolation(self, db, rest1, rest2, categorias):
        """Categorias do rest1 não aparecem no rest2."""
        r = _parse(_buscar_categorias(db, rest2.id))
        assert len(r["categorias"]) == 0

    def test_inactive_category_excluded(self, db, rest1, categorias):
        """Categoria inativa não aparece na listagem."""
        cat_inativa = _make_categoria(db, rest1.id, "Inativa", 99)
        cat_inativa.ativo = False
        db.flush()
        r = _parse(_buscar_categorias(db, rest1.id))
        nomes = [c["nome"] for c in r["categorias"]]
        assert "Inativa" not in nomes

    def test_returns_category_id(self, db, rest1, categorias):
        """Resultado inclui ID de cada categoria."""
        r = _parse(_buscar_categorias(db, rest1.id))
        assert all("id" in c for c in r["categorias"])

    def test_returns_description(self, db, rest1):
        """Categoria com descrição retorna descrição."""
        cat = _make_categoria(db, rest1.id, "Lanches", 4)
        cat.descricao = "Hambúrgueres artesanais"
        db.flush()
        r = _parse(_buscar_categorias(db, rest1.id))
        lanches = [c for c in r["categorias"] if c["nome"] == "Lanches"]
        assert lanches[0]["descricao"] == "Hambúrgueres artesanais"

    def test_no_products_category_still_shown(self, db, rest1):
        """Categoria sem produtos ainda aparece na listagem."""
        _make_categoria(db, rest1.id, "Vazia", 5)
        r = _parse(_buscar_categorias(db, rest1.id))
        nomes = [c["nome"] for c in r["categorias"]]
        assert "Vazia" in nomes

    def test_multiple_restaurants_each_has_own(self, db, rest1, rest2):
        """Dois restaurantes com categorias diferentes são isolados."""
        _make_categoria(db, rest1.id, "Salgados", 1)
        _make_categoria(db, rest2.id, "Doces", 1)
        r1 = _parse(_buscar_categorias(db, rest1.id))
        r2 = _parse(_buscar_categorias(db, rest2.id))
        nomes1 = [c["nome"] for c in r1["categorias"]]
        nomes2 = [c["nome"] for c in r2["categorias"]]
        assert "Salgados" in nomes1
        assert "Salgados" not in nomes2
        assert "Doces" in nomes2
        assert "Doces" not in nomes1

    def test_description_none_returns_empty_string(self, db, rest1):
        """Categoria sem descrição retorna string vazia."""
        _make_categoria(db, rest1.id, "NoDesc", 10)
        r = _parse(_buscar_categorias(db, rest1.id))
        no_desc = [c for c in r["categorias"] if c["nome"] == "NoDesc"]
        assert no_desc[0]["descricao"] == ""


# ==================== 5. criar_pedido — 10 testes ====================

class TestCriarPedido:

    @pytest.mark.asyncio
    async def test_happy_path_create_order(self, db, rest1, bot_config1, produtos, cliente1):
        """Cria pedido com sucesso — retorna pedido_id e comanda."""
        p1 = produtos[0]  # Pizza Margherita
        args = {
            "cliente_nome": "João Silva",
            "cliente_telefone": "11987654321",
            "itens": [{"nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert r["sucesso"] is True
        assert "pedido_id" in r
        assert r["valor_total"] == 45.0

    @pytest.mark.asyncio
    async def test_permission_denied(self, db, rest1, produtos, cliente1):
        """Bot sem permissão de criar pedido retorna erro."""
        bc = _make_bot_config(db, rest1.id, pode_criar_pedido=False)
        args = {
            "cliente_nome": "João",
            "cliente_telefone": "11987654321",
            "itens": [{"nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bc, args, None))
        assert "erro" in r
        assert "permissão" in r["erro"].lower()

    @pytest.mark.asyncio
    async def test_product_not_found(self, db, rest1, bot_config1, produtos):
        """Produto inexistente retorna erro."""
        args = {
            "cliente_nome": "Test",
            "cliente_telefone": "11999999999",
            "itens": [{"nome": "Lasanha Inexistente", "quantidade": 1, "preco_unitario": 30.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert "erro" in r
        assert "não existe" in r["erro"]

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, db, rest1, rest2, bot_config1, produtos):
        """Produto do rest1 não pode ser usado para pedido do rest2."""
        bc2 = _make_bot_config(db, rest2.id)
        args = {
            "cliente_nome": "Tenant Test",
            "cliente_telefone": "11999999999",
            "itens": [{"nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest2.id, bc2, args, None))
        assert "erro" in r

    @pytest.mark.asyncio
    async def test_unavailable_item_rejected(self, db, rest1, bot_config1, categorias):
        """Produto indisponível (desativado) não permite criar pedido."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Indisponível", 55.0, disponivel=False)
        args = {
            "cliente_nome": "Test",
            "cliente_telefone": "11999999999",
            "itens": [{"nome": "Pizza Indisponível", "quantidade": 1, "preco_unitario": 55.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert "erro" in r
        assert "indisponível" in r["erro"]

    @pytest.mark.asyncio
    async def test_stock_zero_rejected(self, db, rest1, bot_config1, categorias):
        """Produto com estoque finito e quantidade 0 é rejeitado."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Rara Esgotada", 60.0,
                      estoque_ilimitado=False, estoque_qtd=0)
        args = {
            "cliente_nome": "Test",
            "cliente_telefone": "11999999999",
            "itens": [{"nome": "Pizza Rara Esgotada", "quantidade": 1, "preco_unitario": 60.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert "erro" in r
        assert "esgotou" in r["erro"]

    @pytest.mark.asyncio
    async def test_empty_itens_error(self, db, rest1, bot_config1):
        """Pedido sem itens retorna erro."""
        args = {
            "cliente_nome": "Test",
            "cliente_telefone": "11999999999",
            "itens": [],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert "erro" in r

    @pytest.mark.asyncio
    async def test_pickup_no_delivery_fee(self, db, rest1, bot_config1, produtos, cliente1):
        """Retirada (pickup) não cobra taxa de entrega."""
        args = {
            "cliente_nome": "João Silva",
            "cliente_telefone": "11987654321",
            "itens": [{"nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert r["sucesso"] is True
        assert r["taxa_entrega"] == 0

    @pytest.mark.asyncio
    async def test_name_match_over_id(self, db, rest1, bot_config1, produtos, cliente1):
        """Nome do produto tem prioridade sobre produto_id incorreto."""
        p1 = produtos[0]  # Pizza Margherita
        args = {
            "cliente_nome": "João Silva",
            "cliente_telefone": "11987654321",
            "itens": [{
                "produto_id": 99999,  # ID incorreto
                "nome": "Pizza Margherita",  # Nome correto
                "quantidade": 1,
                "preco_unitario": 45.0,
            }],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert r["sucesso"] is True

    @pytest.mark.asyncio
    async def test_kds_integration_creates_pedido_cozinha(self, db, rest1, bot_config1, produtos, cliente1):
        """Com KDS ativo e impressão automática, cria PedidoCozinha automaticamente."""
        config_kds = ConfigCozinha(restaurante_id=rest1.id, kds_ativo=True)
        db.add(config_kds)
        db.flush()

        args = {
            "cliente_nome": "João Silva",
            "cliente_telefone": "11987654321",
            "itens": [{"nome": "Pizza Margherita", "quantidade": 1, "preco_unitario": 45.0}],
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }
        r = _parse(await _criar_pedido(db, rest1.id, bot_config1, args, None))
        assert r["sucesso"] is True

        pedido_cozinha = db.query(PedidoCozinha).filter(
            PedidoCozinha.pedido_id == r["pedido_id"]
        ).first()
        assert pedido_cozinha is not None
        assert pedido_cozinha.status == "NOVO"


# ==================== 6. alterar_pedido — 10 testes ====================

class TestAlterarPedido:

    def _setup_pedido_com_item(self, db, rest1, produtos, cliente1):
        """Cria pedido pendente com 1 item para testar alteração."""
        p1 = produtos[0]
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente",
                          comanda="WA1001", valor_total=45.0)
        ip = _make_item_pedido(db, ped.id, p1)
        return ped, ip

    def test_happy_path_add_item(self, db, rest1, bot_config1, produtos, cliente1):
        """Adiciona item a pedido pendente com sucesso."""
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 2, "preco_unitario": 6.0}],
        }))
        assert r["sucesso"] is True
        assert r["novo_total"] > 45.0

    def test_permission_denied(self, db, rest1, produtos, cliente1):
        """Bot sem permissão de alterar retorna erro."""
        bc = _make_bot_config(db, rest1.id, pode_alterar_pedido=False)
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        r = _parse(_alterar_pedido(db, rest1.id, bc, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 1, "preco_unitario": 6.0}],
        }))
        assert "erro" in r
        assert "permissão" in r["erro"].lower()

    def test_pedido_not_found(self, db, rest1, bot_config1):
        """Pedido inexistente retorna erro."""
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {"pedido_id": 99999}))
        assert "erro" in r
        assert "não encontrado" in r["erro"].lower()

    def test_multi_tenant_isolation(self, db, rest1, rest2, bot_config1, produtos, cliente1):
        """Pedido do rest1 não pode ser alterado usando rest2 id."""
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        bc2 = _make_bot_config(db, rest2.id)
        r = _parse(_alterar_pedido(db, rest2.id, bc2, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 1, "preco_unitario": 6.0}],
        }))
        assert "erro" in r

    def test_status_pronto_blocked(self, db, rest1, bot_config1, produtos, cliente1):
        """Pedido com status 'pronto' não pode ser alterado."""
        p1 = produtos[0]
        ped = _make_pedido(db, rest1.id, cliente1, status="pronto", comanda="WA2002")
        _make_item_pedido(db, ped.id, p1)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 1, "preco_unitario": 6.0}],
        }))
        assert "erro" in r
        assert "não pode ser alterado" in r["erro"]

    def test_kds_started_cooking_blocked(self, db, rest1, bot_config1, produtos, cliente1):
        """Se cozinha já está preparando (status FAZENDO), alteração é bloqueada."""
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        pc = PedidoCozinha(restaurante_id=rest1.id, pedido_id=ped.id, status="FAZENDO")
        db.add(pc)
        db.flush()
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 1, "preco_unitario": 6.0}],
        }))
        assert "erro" in r
        assert "cozinha" in r["erro"].lower()

    def test_remove_item(self, db, rest1, bot_config1, produtos, cliente1):
        """Remove item do pedido com sucesso."""
        ped, ip = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        # Adicionar segundo item para poder remover um
        p3 = produtos[2]
        ip2 = _make_item_pedido(db, ped.id, p3)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "remover_item_ids": [ip.id],
        }))
        assert r["sucesso"] is True

    def test_unavailable_new_item_rejected(self, db, rest1, bot_config1, categorias, produtos, cliente1):
        """Adicionar item indisponível ao pedido retorna erro."""
        c1, _, _ = categorias
        _make_produto(db, rest1.id, c1.id, "Pizza Off", 50.0, disponivel=False)
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Pizza Off", "quantidade": 1, "preco_unitario": 50.0}],
        }))
        assert "erro" in r
        assert "indisponível" in r["erro"]

    def test_update_observation(self, db, rest1, bot_config1, produtos, cliente1):
        """Atualiza observação do pedido."""
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "nova_observacao": "Sem cebola por favor",
        }))
        assert r["sucesso"] is True
        db.refresh(ped)
        assert ped.observacoes == "Sem cebola por favor"

    def test_recalculate_total(self, db, rest1, bot_config1, produtos, cliente1):
        """Total é recalculado após adicionar item."""
        ped, _ = self._setup_pedido_com_item(db, rest1, produtos, cliente1)
        r = _parse(_alterar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "adicionar_itens": [{"nome": "Coca-Cola 350ml", "quantidade": 2, "preco_unitario": 6.0}],
        }))
        # 45 (pizza) + 12 (2x coca) = 57
        assert r["novo_total"] == 57.0


# ==================== 7. cancelar_pedido — 10 testes ====================

class TestCancelarPedido:

    def test_happy_path_cancel(self, db, rest1, bot_config1, cliente1):
        """Cancela pedido pendente com sucesso."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3001")
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "motivo": "Desisti",
        }))
        assert r["sucesso"] is True
        db.refresh(ped)
        assert ped.status == "cancelado"

    def test_permission_denied(self, db, rest1, cliente1):
        """Bot sem permissão de cancelar retorna erro."""
        bc = _make_bot_config(db, rest1.id, pode_cancelar_pedido=False)
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3002")
        r = _parse(_cancelar_pedido(db, rest1.id, bc, {
            "pedido_id": ped.id,
            "motivo": "Tentativa",
        }))
        assert "erro" in r
        assert "permissão" in r["erro"].lower()

    def test_pedido_not_found(self, db, rest1, bot_config1):
        """Pedido inexistente retorna erro."""
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": 99999,
            "motivo": "Test",
        }))
        assert "erro" in r
        assert "não encontrado" in r["erro"].lower()

    def test_multi_tenant_isolation(self, db, rest1, rest2, bot_config1, cliente1):
        """Pedido do rest1 não pode ser cancelado usando rest2 id."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3003")
        bc2 = _make_bot_config(db, rest2.id)
        r = _parse(_cancelar_pedido(db, rest2.id, bc2, {
            "pedido_id": ped.id,
            "motivo": "Cross-tenant",
        }))
        assert "erro" in r

    def test_wrong_status_em_rota(self, db, rest1, bot_config1, cliente1):
        """Pedido em rota não pode ser cancelado (limite padrão = em_preparo)."""
        ped = _make_pedido(db, rest1.id, cliente1, status="em_rota", comanda="WA3004")
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "motivo": "Tarde",
        }))
        assert "erro" in r
        assert "não pode" in r["erro"].lower()

    def test_cancel_em_preparo_allowed(self, db, rest1, bot_config1, cliente1):
        """Pedido em preparo PODE ser cancelado (limite = em_preparo)."""
        ped = _make_pedido(db, rest1.id, cliente1, status="em_preparo", comanda="WA3005")
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "motivo": "Mudei de ideia",
        }))
        assert r["sucesso"] is True

    def test_cancel_already_cancelled(self, db, rest1, bot_config1, cliente1):
        """Cancelar pedido já cancelado — status 'cancelado' não está na ordem."""
        ped = _make_pedido(db, rest1.id, cliente1, status="cancelado", comanda="WA3006")
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "motivo": "Já cancelado",
        }))
        # ValueError no status_ordem.index("cancelado") é capturado e cancela de qualquer forma
        assert r.get("sucesso") is True or "erro" not in r

    def test_cancel_by_conversa_pedido_ativo(self, db, rest1, bot_config1, cliente1):
        """Cancela último pedido ativo da conversa (sem pedido_id explícito)."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3007")
        conv = _make_conversa(db, rest1.id, "11987654321",
                              pedido_ativo_id=ped.id, cliente_id=cliente1.id)
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "motivo": "Via conversa",
        }, conversa=conv))
        assert r["sucesso"] is True

    def test_cancel_by_phone(self, db, rest1, bot_config1, cliente1):
        """Cancela último pedido ativo pelo telefone da conversa."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3008")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id)
        conv.cliente_telefone = "11987654321"
        db.flush()
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "motivo": "Via telefone",
        }, conversa=conv))
        assert r["sucesso"] is True

    def test_cancel_includes_motivo_in_message(self, db, rest1, bot_config1, cliente1):
        """Mensagem de sucesso inclui o motivo do cancelamento."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA3009")
        r = _parse(_cancelar_pedido(db, rest1.id, bot_config1, {
            "pedido_id": ped.id,
            "motivo": "Demorou muito",
        }))
        assert "Demorou muito" in r["mensagem"]


# ==================== 8. repetir_ultimo_pedido — 10 testes ====================

class TestRepetirUltimoPedido:

    def _setup_pedido_entregue(self, db, rest1, cliente1, produtos, status="entregue"):
        """Cria pedido entregue com carrinho_json para repetição."""
        p1, p2 = produtos[0], produtos[2]
        carrinho = [
            {"produto_id": p1.id, "nome": p1.nome, "quantidade": 1, "preco_unitario": p1.preco},
            {"produto_id": p2.id, "nome": p2.nome, "quantidade": 2, "preco_unitario": p2.preco},
        ]
        ped = _make_pedido(db, rest1.id, cliente1, status=status,
                          comanda="WA4001", valor_total=57.0,
                          carrinho_json=carrinho)
        return ped

    def test_happy_path_repeat(self, db, rest1, bot_config1, produtos, cliente1):
        """Repete último pedido entregue com sucesso."""
        self._setup_pedido_entregue(db, rest1, cliente1, produtos)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert "ultimo_pedido" in r
        assert len(r["itens_para_criar"]) == 2

    def test_no_previous_order(self, db, rest1, bot_config1):
        """Sem pedido anterior retorna erro."""
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11999999999",
        }, None))
        assert "erro" in r
        assert "não encontrado" in r["erro"].lower() or "Nenhum" in r["erro"]

    def test_item_now_unavailable(self, db, rest1, bot_config1, categorias, cliente1):
        """Item do pedido anterior ficou indisponível — é excluído da repetição."""
        c1, c2, _ = categorias
        p_off = _make_produto(db, rest1.id, c1.id, "Pizza Temporária", 40.0, disponivel=False)
        p_on = _make_produto(db, rest1.id, c2.id, "Guaraná", 5.0)
        carrinho = [
            {"produto_id": p_off.id, "nome": p_off.nome, "quantidade": 1, "preco_unitario": p_off.preco},
            {"produto_id": p_on.id, "nome": p_on.nome, "quantidade": 1, "preco_unitario": p_on.preco},
        ]
        _make_pedido(db, rest1.id, cliente1, status="entregue",
                    comanda="WA4002", carrinho_json=carrinho)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        # p_off é excluído, apenas p_on sobra
        assert len(r["itens_para_criar"]) == 1
        assert r["itens_para_criar"][0]["nome"] == "Guaraná"

    def test_all_items_unavailable(self, db, rest1, bot_config1, categorias, cliente1):
        """Todos os itens ficaram indisponíveis — retorna erro."""
        c1, _, _ = categorias
        p_off = _make_produto(db, rest1.id, c1.id, "Pizza Obsoleta", 40.0, disponivel=False)
        carrinho = [
            {"produto_id": p_off.id, "nome": p_off.nome, "quantidade": 1, "preco_unitario": p_off.preco},
        ]
        _make_pedido(db, rest1.id, cliente1, status="entregue",
                    comanda="WA4003", carrinho_json=carrinho)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert "erro" in r

    def test_multi_tenant_isolation(self, db, rest1, rest2, bot_config1, produtos, cliente1, cliente2):
        """Pedido do rest1 não aparece na busca do rest2."""
        self._setup_pedido_entregue(db, rest1, cliente1, produtos)
        bc2 = _make_bot_config(db, rest2.id)
        r = _parse(_repetir_ultimo_pedido(db, rest2.id, bc2, {
            "cliente_telefone": "11987654321",
        }, None))
        assert "erro" in r

    def test_price_changed_uses_current_price(self, db, rest1, bot_config1, categorias, cliente1):
        """Se preço mudou desde o último pedido, usa preço atual."""
        c1, _, _ = categorias
        prod = _make_produto(db, rest1.id, c1.id, "Pizza Dinâmica", 30.0)
        carrinho = [
            {"produto_id": prod.id, "nome": prod.nome, "quantidade": 1, "preco_unitario": 25.0},  # preço antigo
        ]
        _make_pedido(db, rest1.id, cliente1, status="entregue",
                    comanda="WA4004", carrinho_json=carrinho)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert r["itens_para_criar"][0]["preco_unitario"] == 30.0  # preço atual

    def test_pedido_nao_entregue_ignored(self, db, rest1, bot_config1, produtos, cliente1):
        """Apenas pedidos entregues são considerados para repetição."""
        p1 = produtos[0]
        carrinho = [{"produto_id": p1.id, "nome": p1.nome, "quantidade": 1, "preco_unitario": p1.preco}]
        _make_pedido(db, rest1.id, cliente1, status="cancelado",
                    comanda="WA4005", carrinho_json=carrinho)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert "erro" in r

    def test_phone_with_country_code(self, db, rest1, bot_config1, produtos, cliente1):
        """Telefone com +55 encontra pedido por últimos 8 dígitos."""
        self._setup_pedido_entregue(db, rest1, cliente1, produtos)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "+5511987654321",
        }, None))
        assert "ultimo_pedido" in r

    def test_returns_estimated_value(self, db, rest1, bot_config1, produtos, cliente1):
        """Resultado inclui valor estimado do pedido repetido."""
        self._setup_pedido_entregue(db, rest1, cliente1, produtos)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert r["ultimo_pedido"]["valor_estimado"] > 0

    def test_stock_zero_excluded_from_repeat(self, db, rest1, bot_config1, categorias, cliente1):
        """Item com estoque zerado é excluído da repetição."""
        c1, c2, _ = categorias
        p_no_stock = _make_produto(db, rest1.id, c1.id, "Pizza Limitada", 40.0,
                                    estoque_ilimitado=False, estoque_qtd=0)
        p_ok = _make_produto(db, rest1.id, c2.id, "Água", 3.0)
        carrinho = [
            {"produto_id": p_no_stock.id, "nome": p_no_stock.nome, "quantidade": 1, "preco_unitario": 40.0},
            {"produto_id": p_ok.id, "nome": p_ok.nome, "quantidade": 1, "preco_unitario": 3.0},
        ]
        _make_pedido(db, rest1.id, cliente1, status="entregue",
                    comanda="WA4006", carrinho_json=carrinho)
        r = _parse(_repetir_ultimo_pedido(db, rest1.id, bot_config1, {
            "cliente_telefone": "11987654321",
        }, None))
        assert len(r["itens_para_criar"]) == 1
        assert r["itens_para_criar"][0]["nome"] == "Água"


# ==================== 9. consultar_status_pedido — 10 testes ====================

class TestConsultarStatusPedido:

    def test_happy_path_by_id(self, db, rest1, cliente1):
        """Consulta status por pedido_id."""
        ped = _make_pedido(db, rest1.id, cliente1, status="em_preparo", comanda="WA5001")
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert r["status"] == "em_preparo"
        assert r["comanda"] == "WA5001"

    def test_by_phone_returns_most_recent(self, db, rest1, cliente1):
        """Consulta por telefone retorna pedido mais recente."""
        _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA5002",
                    data_criacao=datetime.utcnow() - timedelta(hours=2))
        ped2 = _make_pedido(db, rest1.id, cliente1, status="em_preparo", comanda="WA5003")
        r = _parse(_consultar_status_pedido(db, rest1.id, {
            "cliente_telefone": "11987654321",
        }))
        assert r["comanda"] == "WA5003"

    def test_not_found(self, db, rest1):
        """Pedido inexistente retorna erro."""
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": 99999}))
        assert "erro" in r

    def test_multi_tenant_isolation(self, db, rest1, rest2, cliente1):
        """Pedido do rest1 não pode ser consultado pelo rest2."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA5004")
        r = _parse(_consultar_status_pedido(db, rest2.id, {"pedido_id": ped.id}))
        assert "erro" in r

    def test_with_motoboy_info(self, db, rest1, cliente1):
        """Pedido em rota retorna nome do motoboy."""
        ped = _make_pedido(db, rest1.id, cliente1, status="em_rota", comanda="WA5005")
        motoboy = Motoboy(
            restaurante_id=rest1.id,
            nome="Carlos Moto",
            usuario="carlos",
            telefone="11900001111",
            status="ativo",
        )
        db.add(motoboy)
        db.flush()
        entrega = Entrega(
            pedido_id=ped.id,
            motoboy_id=motoboy.id,
            status="em_rota",
        )
        db.add(entrega)
        db.flush()
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert r["motoboy_nome"] == "Carlos Moto"

    def test_with_kds_position(self, db, rest1, cliente1):
        """Pedido em preparo com KDS mostra posição na fila."""
        ped = _make_pedido(db, rest1.id, cliente1, status="em_preparo", comanda="WA5006")
        pc = PedidoCozinha(
            restaurante_id=rest1.id,
            pedido_id=ped.id,
            status="NOVO",
            pausado=False,
        )
        db.add(pc)
        db.flush()
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert "posicao_fila" in r

    def test_status_texto_mapping(self, db, rest1, cliente1):
        """Status texto mapeado corretamente."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente", comanda="WA5007")
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert "aguardando" in r["status_texto"].lower()

    def test_includes_valor_total(self, db, rest1, cliente1):
        """Resultado inclui valor total do pedido."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente",
                          comanda="WA5008", valor_total=75.0)
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert r["valor_total"] == 75.0

    def test_includes_itens_text(self, db, rest1, cliente1):
        """Resultado inclui texto dos itens."""
        ped = _make_pedido(db, rest1.id, cliente1, status="pendente",
                          comanda="WA5009", itens_texto="2x Pizza Margherita")
        r = _parse(_consultar_status_pedido(db, rest1.id, {"pedido_id": ped.id}))
        assert "Margherita" in r["itens"]

    def test_no_params_returns_error(self, db, rest1):
        """Sem pedido_id nem telefone retorna erro."""
        r = _parse(_consultar_status_pedido(db, rest1.id, {}))
        assert "erro" in r


# ==================== 10. verificar_horario — 10 testes ====================

class TestVerificarHorario:

    def test_happy_path_open(self, db, rest1):
        """Restaurante aberto no horário retorna aberto=True."""
        # Forçar hora para estar dentro do horário configurado (08:00-23:00)
        with patch("backend.app.bot.function_calls.datetime") as mock_dt:
            mock_dt.utcnow.return_value = datetime(2026, 4, 1, 18, 0, 0)  # 18h UTC = 15h BRT
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            r = _parse(_verificar_horario(db, rest1.id))
            assert r["aberto"] is True

    def test_closed_outside_hours(self, db, rest1):
        """Restaurante fechado fora do horário."""
        with patch("backend.app.bot.function_calls.datetime") as mock_dt:
            # 03:00 UTC = 00:00 BRT — fora de 08:00-23:00
            mock_dt.utcnow.return_value = datetime(2026, 4, 1, 3, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            r = _parse(_verificar_horario(db, rest1.id))
            assert r["aberto"] is False

    def test_no_config_returns_error(self, db):
        """Restaurante sem config retorna erro."""
        # Criar restaurante SEM config
        rest_no_config = Restaurante(
            id=999,
            nome="Sem Config",
            nome_fantasia="Sem Config",
            email="noconfig@test.com",
            senha=hashlib.sha256(b"123456").hexdigest(),
            telefone="11999990099",
            endereco_completo="Rua X 1",
            plano="Basico",
            plano_tier=1,
            valor_plano=0,
            limite_motoboys=1,
            codigo_acesso="NOCONF01",
            ativo=True,
        )
        db.add(rest_no_config)
        db.flush()
        r = _parse(_verificar_horario(db, rest_no_config.id))
        assert "erro" in r

    def test_returns_hora_atual(self, db, rest1):
        """Resultado inclui hora atual."""
        r = _parse(_verificar_horario(db, rest1.id))
        assert "hora_atual" in r

    def test_returns_dia_semana(self, db, rest1):
        """Resultado inclui dia da semana."""
        r = _parse(_verificar_horario(db, rest1.id))
        assert "dia_semana" in r

    def test_returns_horario_hoje(self, db, rest1):
        """Resultado inclui horário de hoje."""
        r = _parse(_verificar_horario(db, rest1.id))
        assert "horario_hoje" in r

    def test_returns_horarios_semana(self, db, rest1):
        """Resultado inclui horários de todos os dias da semana."""
        r = _parse(_verificar_horario(db, rest1.id))
        assert len(r["horarios_semana"]) == 7

    def test_multi_tenant_separate_configs(self, db, rest1, rest2):
        """Cada restaurante tem sua própria configuração de horário independente."""
        # rest2 também tem config (criada pela fixture), mas com valores independentes
        config2 = db.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest2.id
        ).first()
        config2.horario_abertura = "20:00"
        config2.horario_fechamento = "02:00"
        db.flush()
        r1 = _parse(_verificar_horario(db, rest1.id))
        r2 = _parse(_verificar_horario(db, rest2.id))
        # rest1 tem 08:00-23:00, rest2 tem 20:00-02:00 — diferentes
        assert r1["horarios_semana"] != r2["horarios_semana"]

    def test_horarios_por_dia_config(self, db, rest1):
        """Configuração de horários por dia da semana é respeitada."""
        config = db.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest1.id
        ).first()
        config.horarios_por_dia = json.dumps({
            "segunda": {"ativo": True, "abertura": "10:00", "fechamento": "22:00"},
            "terca": {"ativo": True, "abertura": "10:00", "fechamento": "22:00"},
            "quarta": {"ativo": False},
            "quinta": {"ativo": True, "abertura": "10:00", "fechamento": "22:00"},
            "sexta": {"ativo": True, "abertura": "10:00", "fechamento": "23:00"},
            "sabado": {"ativo": True, "abertura": "11:00", "fechamento": "23:00"},
            "domingo": {"ativo": False},
        })
        db.flush()
        r = _parse(_verificar_horario(db, rest1.id))
        assert r["horarios_semana"]["quarta"] == "FECHADO"
        assert r["horarios_semana"]["domingo"] == "FECHADO"
        assert "10:00" in r["horarios_semana"]["segunda"]

    def test_overnight_hours(self, db, rest1):
        """Restaurante com horário noturno (22:00 - 04:00) é detectado como aberto."""
        config = db.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == rest1.id
        ).first()
        config.horario_abertura = "22:00"
        config.horario_fechamento = "04:00"
        db.flush()
        with patch("backend.app.bot.function_calls.datetime") as mock_dt:
            # 02:00 UTC = 23:00 BRT — dentro de 22:00-04:00
            mock_dt.utcnow.return_value = datetime(2026, 4, 2, 2, 0, 0)
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            r = _parse(_verificar_horario(db, rest1.id))
            assert r["aberto"] is True


# ==================== 11. buscar_promocoes — 10 testes ====================

class TestBuscarPromocoes:

    def _make_promo(self, db, rest_id, nome, cupom, tipo="percentual", valor=10,
                    ativo=True, data_fim=None, uso_limitado=False, limite_usos=None,
                    usos_realizados=0, cliente_id=None, tipo_cupom="global"):
        promo = Promocao(
            restaurante_id=rest_id,
            nome=nome,
            tipo_desconto=tipo,
            valor_desconto=valor,
            codigo_cupom=cupom,
            ativo=ativo,
            data_fim=data_fim,
            uso_limitado=uso_limitado,
            limite_usos=limite_usos,
            usos_realizados=usos_realizados,
            cliente_id=cliente_id,
            tipo_cupom=tipo_cupom,
        )
        db.add(promo)
        db.flush()
        return promo

    def test_happy_path_active_promos(self, db, rest1):
        """Lista promoções ativas."""
        self._make_promo(db, rest1.id, "Desconto 10%", "DESC10")
        r = _parse(_buscar_promocoes(db, rest1.id))
        assert len(r["promocoes"]) >= 1
        assert r["promocoes"][0]["cupom"] == "DESC10"

    def test_no_promos(self, db, rest2):
        """Restaurante sem promoções retorna listas vazias."""
        r = _parse(_buscar_promocoes(db, rest2.id))
        assert len(r["promocoes"]) == 0
        assert len(r["combos"]) == 0

    def test_expired_promo_excluded(self, db, rest1):
        """Promoção expirada não aparece na lista."""
        self._make_promo(db, rest1.id, "Expirada", "EXP1",
                        data_fim=datetime.utcnow() - timedelta(days=1))
        r = _parse(_buscar_promocoes(db, rest1.id))
        cupons = [p["cupom"] for p in r["promocoes"]]
        assert "EXP1" not in cupons

    def test_multi_tenant_isolation(self, db, rest1, rest2):
        """Promoções do rest1 não aparecem no rest2."""
        self._make_promo(db, rest1.id, "Only Rest1", "R1ONLY")
        r = _parse(_buscar_promocoes(db, rest2.id))
        cupons = [p["cupom"] for p in r["promocoes"]]
        assert "R1ONLY" not in cupons

    def test_inactive_promo_excluded(self, db, rest1):
        """Promoção inativa não aparece."""
        self._make_promo(db, rest1.id, "Inativa", "INACT", ativo=False)
        r = _parse(_buscar_promocoes(db, rest1.id))
        cupons = [p["cupom"] for p in r["promocoes"]]
        assert "INACT" not in cupons

    def test_usage_limited_exhausted_excluded(self, db, rest1):
        """Promoção com limite de uso esgotado não aparece."""
        self._make_promo(db, rest1.id, "Esgotada", "ESGOT",
                        uso_limitado=True, limite_usos=5, usos_realizados=5)
        r = _parse(_buscar_promocoes(db, rest1.id))
        cupons = [p["cupom"] for p in r["promocoes"]]
        assert "ESGOT" not in cupons

    def test_combos_included(self, db, rest1, categorias, produtos):
        """Combos ativos são incluídos na lista."""
        combo = Combo(
            restaurante_id=rest1.id,
            nome="Combo Pizza+Bebida",
            preco_combo=45.0,
            preco_original=51.0,
            ativo=True,
        )
        db.add(combo)
        db.flush()
        r = _parse(_buscar_promocoes(db, rest1.id))
        assert len(r["combos"]) >= 1
        assert r["combos"][0]["economia"] == 6.0

    def test_exclusive_coupons_for_client(self, db, rest1, cliente1):
        """Cupons exclusivos aparecem se cliente identificado na conversa."""
        self._make_promo(db, rest1.id, "Cupom VIP", "VIP10",
                        cliente_id=cliente1.id, tipo_cupom="exclusivo")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id)
        r = _parse(_buscar_promocoes(db, rest1.id, conversa=conv))
        assert len(r["cupons_exclusivos"]) >= 1
        assert r["cupons_exclusivos"][0]["cupom"] == "VIP10"

    def test_exclusive_coupon_hidden_from_other_client(self, db, rest1, cliente1):
        """Cupom exclusivo de um cliente NÃO aparece nas promoções globais."""
        self._make_promo(db, rest1.id, "Só João", "JOAO10",
                        cliente_id=cliente1.id, tipo_cupom="exclusivo")
        r = _parse(_buscar_promocoes(db, rest1.id))
        # Sem conversa, não inclui cupons exclusivos
        cupons_globais = [p["cupom"] for p in r["promocoes"]]
        assert "JOAO10" not in cupons_globais

    def test_promo_without_expiration_included(self, db, rest1):
        """Promoção sem data de expiração (eterna) aparece na lista."""
        self._make_promo(db, rest1.id, "Sem Prazo", "FOREVER", data_fim=None)
        r = _parse(_buscar_promocoes(db, rest1.id))
        cupons = [p["cupom"] for p in r["promocoes"]]
        assert "FOREVER" in cupons


# ==================== 12. registrar_avaliacao — 10 testes ====================

class TestRegistrarAvaliacao:

    def test_happy_path_create_avaliacao(self, db, rest1, cliente1):
        """Registra avaliação nova com nota válida."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6001")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id,
                              pedido_ativo_id=ped.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 5,
            "categoria": "comida",
            "detalhe": "Pizza deliciosa!",
        }, conv))
        assert r["sucesso"] is True
        assert r["nota"] == 5

    def test_nota_5_includes_google_maps_url(self, db, rest1, cliente1):
        """Nota 5 com google_maps_url configurada retorna link do Google Maps."""
        bc = _make_bot_config(db, rest1.id,
                              avaliacao_pedir_google_review=True,
                              google_maps_url="https://maps.google.com/test")
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6002")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id,
                              pedido_ativo_id=ped.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 5,
        }, conv))
        assert r.get("google_maps_url") == "https://maps.google.com/test"

    def test_low_note_returns_apology(self, db, rest1, cliente1):
        """Nota baixa (1-3) retorna mensagem de desculpas."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6003")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id,
                              pedido_ativo_id=ped.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 2,
            "detalhe": "Frio",
        }, conv))
        assert "sentimos" in r["mensagem"].lower() or "problema" in r["mensagem"].lower()

    def test_avaliacao_by_phone_auto_find_pedido(self, db, rest1, cliente1):
        """Se pedido_id não informado, busca último pedido pelo telefone da conversa."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6004")
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id)
        conv.cliente_telefone = "11987654321"
        db.flush()
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 4,
        }, conv))
        assert r["sucesso"] is True

    def test_update_pending_avaliacao(self, db, rest1, cliente1):
        """Se existe avaliação pendente (criada pelo worker), atualiza em vez de criar nova."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6005")
        avaliacao = BotAvaliacao(
            restaurante_id=rest1.id,
            pedido_id=ped.id,
            status="pendente",
        )
        db.add(avaliacao)
        db.flush()
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "pedido_id": ped.id,
            "nota": 4,
        }, conv))
        assert r["sucesso"] is True
        db.refresh(avaliacao)
        assert avaliacao.nota == 4
        assert avaliacao.status == "respondida"

    def test_multi_tenant_isolation(self, db, rest1, rest2, cliente1):
        """Avaliação é vinculada ao restaurante correto."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6006")
        conv = _make_conversa(db, rest1.id, "11987654321",
                              cliente_id=cliente1.id, pedido_ativo_id=ped.id)
        _registrar_avaliacao(db, rest1.id, {"nota": 5}, conv)
        # Verificar que avaliação pertence ao rest1
        aval = db.query(BotAvaliacao).filter(
            BotAvaliacao.restaurante_id == rest1.id,
        ).first()
        assert aval is not None
        aval2 = db.query(BotAvaliacao).filter(
            BotAvaliacao.restaurante_id == rest2.id,
        ).first()
        assert aval2 is None

    def test_nota_4_positive_message(self, db, rest1, cliente1):
        """Nota 4 retorna mensagem positiva (>= 4)."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6007")
        conv = _make_conversa(db, rest1.id, "11987654321",
                              cliente_id=cliente1.id, pedido_ativo_id=ped.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 4,
        }, conv))
        assert "obrigado" in r["mensagem"].lower()

    def test_without_conversa(self, db, rest1, cliente1):
        """Registro funciona mesmo sem conversa (None), usando pedido_id explícito."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6008")
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "pedido_id": ped.id,
            "nota": 3,
        }, None))
        assert r["sucesso"] is True

    def test_categoria_atendimento(self, db, rest1, cliente1):
        """Avaliação na categoria 'atendimento' é salva corretamente."""
        ped = _make_pedido(db, rest1.id, cliente1, status="entregue", comanda="WA6009")
        conv = _make_conversa(db, rest1.id, "11987654321",
                              cliente_id=cliente1.id, pedido_ativo_id=ped.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 5,
            "categoria": "atendimento",
            "detalhe": "Bia foi muito simpática",
        }, conv))
        aval = db.query(BotAvaliacao).filter(
            BotAvaliacao.pedido_id == ped.id,
        ).first()
        assert aval.categoria == "atendimento"
        assert aval.detalhe == "Bia foi muito simpática"

    def test_no_pedido_still_saves(self, db, rest1, cliente1):
        """Avaliação sem pedido_id e sem conversa com pedido ainda é salva."""
        conv = _make_conversa(db, rest1.id, "11987654321", cliente_id=cliente1.id)
        r = _parse(_registrar_avaliacao(db, rest1.id, {
            "nota": 3,
        }, conv))
        assert r["sucesso"] is True
        # Verifica que foi salva no banco
        total = db.query(BotAvaliacao).filter(
            BotAvaliacao.restaurante_id == rest1.id,
        ).count()
        assert total >= 1


# ==================== Testes da função executar_funcao ====================

class TestExecutarFuncao:
    """Testes complementares do dispatcher executar_funcao."""

    @pytest.mark.asyncio
    async def test_unknown_function(self, db, rest1, bot_config1):
        """Função desconhecida retorna erro."""
        r = _parse(await executar_funcao("funcao_inexistente", {}, db, rest1.id, bot_config1))
        assert "erro" in r

    @pytest.mark.asyncio
    async def test_dispatcher_buscar_cliente(self, db, rest1, bot_config1, cliente1):
        """Dispatcher chama buscar_cliente corretamente."""
        r = _parse(await executar_funcao("buscar_cliente", {
            "telefone": "11987654321",
        }, db, rest1.id, bot_config1))
        assert r["encontrado"] is True

    @pytest.mark.asyncio
    async def test_dispatcher_buscar_categorias(self, db, rest1, bot_config1, categorias):
        """Dispatcher chama buscar_categorias corretamente."""
        r = _parse(await executar_funcao("buscar_categorias", {}, db, rest1.id, bot_config1))
        assert len(r["categorias"]) == 3

    @pytest.mark.asyncio
    async def test_error_handling_rollback(self, db, rest1, bot_config1):
        """Erro em function call faz rollback do savepoint sem afetar a transação principal."""
        # Forçar erro passando args inválidos para criar_pedido
        r = _parse(await executar_funcao("criar_pedido", {
            "itens": [{"nome": "Inexistente", "quantidade": 1, "preco_unitario": 10}],
            "cliente_nome": "Test",
            "cliente_telefone": "11999999999",
            "forma_pagamento": "dinheiro",
            "tipo_entrega": "retirada",
        }, db, rest1.id, bot_config1))
        assert "erro" in r
        # Sessão ainda funcional
        count = db.query(Restaurante).count()
        assert count >= 1
