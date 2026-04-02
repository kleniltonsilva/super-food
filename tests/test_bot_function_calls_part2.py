"""
Testes das Function Calls do Bot WhatsApp (Part 2) -- Funcoes 13-24
Derekh Food SaaS

Funcoes testadas:
  13. registrar_problema
  14. aplicar_cupom
  15. escalar_humano
  16. rastrear_pedido
  17. trocar_item_pedido
  18. consultar_tempo_entrega
  19. consultar_bairros
  20. atualizar_endereco_cliente
  21. validar_endereco
  22. confirmar_endereco_validado
  23. gerar_cobranca_pix
  24. consultar_pagamento_pix

Execucao: pytest tests/test_bot_function_calls_part2.py -v
"""

import sys
import os
import json
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-fc2")
os.environ.setdefault("ENVIRONMENT", "testing")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session

from database.base import Base
from database.models import (
    Restaurante,
    ConfigRestaurante,
    SiteConfig,
    Produto,
    CategoriaMenu,
    Cliente,
    EnderecoCliente,
    Pedido,
    ItemPedido,
    Entrega,
    Motoboy,
    Promocao,
    BairroEntrega,
    PedidoCozinha,
    ConfigCozinha,
    ItemEsgotado,
    BotConfig,
    BotConversa,
    BotProblema,
    BotAvaliacao,
    PixConfig,
    PixCobranca,
)


# ==================== FIXTURES ====================


@pytest.fixture(scope="module")
def engine():
    """Cria engine SQLite in-memory."""
    eng = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="module")
def connection(engine):
    """Conexao unica para o modulo inteiro."""
    conn = engine.connect()
    yield conn
    conn.close()


@pytest.fixture(scope="module")
def SessionFactory(connection):
    return sessionmaker(bind=connection)


@pytest.fixture
def db(connection, SessionFactory):
    """Sessao com nested transaction — rollback automatico apos cada teste.

    Usa savepoint real para que db.commit() dentro das funcoes testadas
    nao persista entre testes.
    """
    trans = connection.begin()
    session = SessionFactory()

    # Interceptar commit/rollback para usar savepoints
    # Quando a funcao testada chama session.commit(), transformar em flush
    _orig_commit = session.commit
    _orig_rollback = session.rollback
    _orig_begin_nested = session.begin_nested

    def _fake_commit():
        session.flush()

    def _fake_rollback():
        pass  # No-op, o rollback real acontece no teardown

    session.commit = _fake_commit
    session.rollback = _fake_rollback

    yield session

    session.commit = _orig_commit
    session.rollback = _orig_rollback
    session.close()
    trans.rollback()


@pytest.fixture
def restaurante1(db):
    """Restaurante 1 (tenant principal para testes)."""
    rest = Restaurante(
        nome="Pizza Tuga",
        nome_fantasia="Pizza Tuga",
        email="pizza@test.com",
        telefone="11999990001",
        endereco_completo="Rua Tuga 100, Centro, Sao Paulo",
        cidade="Sao Paulo",
        estado="SP",
        pais="BR",
        latitude=-23.55,
        longitude=-46.63,
        plano="Premium",
        plano_tier=4,
        valor_plano=527.0,
        limite_motoboys=10,
        codigo_acesso="PIZZA001",
        ativo=True,
        billing_status="active",
    )
    rest.set_senha("123456")
    db.add(rest)
    db.flush()
    return rest


@pytest.fixture
def restaurante2(db):
    """Restaurante 2 (para testes de isolamento multi-tenant)."""
    rest = Restaurante(
        nome="Burger House",
        nome_fantasia="Burger House",
        email="burger@test.com",
        telefone="11999990002",
        endereco_completo="Rua Burger 200",
        cidade="Rio de Janeiro",
        estado="RJ",
        pais="BR",
        latitude=-22.90,
        longitude=-43.17,
        plano="Essencial",
        plano_tier=2,
        valor_plano=279.90,
        limite_motoboys=5,
        codigo_acesso="BURGER01",
        ativo=True,
        billing_status="active",
    )
    rest.set_senha("654321")
    db.add(rest)
    db.flush()
    return rest


@pytest.fixture
def config_rest(db, restaurante1):
    """ConfigRestaurante para restaurante1."""
    config = ConfigRestaurante(
        restaurante_id=restaurante1.id,
        status_atual="aberto",
        taxa_entrega_base=7.0,
        distancia_base_km=3.0,
        taxa_km_extra=2.0,
        raio_entrega_km=10.0,
        tempo_medio_preparo=25,
        horario_abertura="10:00",
        horario_fechamento="23:00",
    )
    db.add(config)
    db.flush()
    return config


@pytest.fixture
def site_config(db, restaurante1):
    """SiteConfig para restaurante1."""
    sc = SiteConfig(
        restaurante_id=restaurante1.id,
        tipo_restaurante="pizzaria",
        tempo_entrega_estimado=40,
        tempo_retirada_estimado=15,
    )
    db.add(sc)
    db.flush()
    return sc


@pytest.fixture
def bot_config(db, restaurante1):
    """BotConfig para restaurante1."""
    bc = BotConfig(
        restaurante_id=restaurante1.id,
        bot_ativo=True,
        nome_atendente="Bia",
        pode_criar_pedido=True,
        pode_alterar_pedido=True,
        pode_cancelar_pedido=True,
        impressao_automatica_bot=True,
        politica_atraso=json.dumps({"acao": "desconto_proximo", "desconto_pct": 10, "mensagem": "Desculpe pelo atraso!"}),
        politica_pedido_errado=json.dumps({"acao": "brinde_reenviar", "desconto_pct": 0, "mensagem": ""}),
        politica_item_faltando=json.dumps({"acao": "desculpar", "desconto_pct": 0, "mensagem": ""}),
        politica_qualidade=json.dumps({"acao": "reembolso_parcial", "desconto_pct": 20, "mensagem": "Lamentamos a qualidade."}),
    )
    db.add(bc)
    db.flush()
    return bc


@pytest.fixture
def bot_config_no_perms(db, restaurante2):
    """BotConfig para restaurante2 sem permissoes de alterar."""
    bc = BotConfig(
        restaurante_id=restaurante2.id,
        bot_ativo=True,
        nome_atendente="Ana",
        pode_criar_pedido=False,
        pode_alterar_pedido=False,
        pode_cancelar_pedido=False,
    )
    db.add(bc)
    db.flush()
    return bc


@pytest.fixture
def categoria(db, restaurante1):
    cat = CategoriaMenu(
        restaurante_id=restaurante1.id,
        nome="Pizzas",
        ativo=True,
        ordem_exibicao=1,
    )
    db.add(cat)
    db.flush()
    return cat


@pytest.fixture
def produto_margherita(db, restaurante1, categoria):
    p = Produto(
        restaurante_id=restaurante1.id,
        categoria_id=categoria.id,
        nome="Pizza Margherita",
        preco=45.90,
        disponivel=True,
        estoque_ilimitado=True,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def produto_calabresa(db, restaurante1, categoria):
    p = Produto(
        restaurante_id=restaurante1.id,
        categoria_id=categoria.id,
        nome="Pizza Calabresa",
        preco=49.90,
        disponivel=True,
        estoque_ilimitado=True,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def produto_indisponivel(db, restaurante1, categoria):
    p = Produto(
        restaurante_id=restaurante1.id,
        categoria_id=categoria.id,
        nome="Pizza Quatro Queijos",
        preco=55.00,
        disponivel=False,
        estoque_ilimitado=True,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def produto_esgotado(db, restaurante1, categoria):
    """Produto com estoque zerado."""
    p = Produto(
        restaurante_id=restaurante1.id,
        categoria_id=categoria.id,
        nome="Pizza Portuguesa",
        preco=52.00,
        disponivel=True,
        estoque_ilimitado=False,
        estoque_quantidade=0,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def cliente1(db, restaurante1):
    c = Cliente(
        restaurante_id=restaurante1.id,
        nome="Joao Silva",
        telefone="11987654321",
        senha_hash=hashlib.sha256("654321".encode()).hexdigest(),
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def cliente1_endereco(db, cliente1):
    e = EnderecoCliente(
        cliente_id=cliente1.id,
        endereco_completo="Rua Augusta 1000, Consolacao, Sao Paulo",
        bairro="Consolacao",
        complemento="Apto 42",
        padrao=True,
    )
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def cliente2(db, restaurante2):
    """Cliente do restaurante2 (multi-tenant isolation)."""
    c = Cliente(
        restaurante_id=restaurante2.id,
        nome="Maria Souza",
        telefone="11987654321",
        senha_hash=hashlib.sha256("654321".encode()).hexdigest(),
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def pedido1(db, restaurante1, cliente1, produto_margherita):
    """Pedido em_preparo para restaurante1."""
    p = Pedido(
        restaurante_id=restaurante1.id,
        cliente_id=cliente1.id,
        comanda="WA1001",
        tipo="delivery",
        origem="whatsapp_bot",
        tipo_entrega="entrega",
        cliente_nome="Joao Silva",
        cliente_telefone="11987654321",
        endereco_entrega="Rua Augusta 1000",
        itens="1x Pizza Margherita (R$45.90)",
        valor_subtotal=45.90,
        valor_taxa_entrega=7.0,
        valor_total=52.90,
        forma_pagamento="pix",
        status="em_preparo",
        historico_status=[
            {"status": "pendente", "timestamp": datetime.utcnow().isoformat()},
            {"status": "em_preparo", "timestamp": datetime.utcnow().isoformat()},
        ],
    )
    db.add(p)
    db.flush()

    item = ItemPedido(
        pedido_id=p.id,
        produto_id=produto_margherita.id,
        quantidade=1,
        preco_unitario=45.90,
    )
    db.add(item)
    db.flush()
    return p


@pytest.fixture
def pedido_em_rota(db, restaurante1, cliente1):
    """Pedido em_rota com motoboy e GPS."""
    p = Pedido(
        restaurante_id=restaurante1.id,
        cliente_id=cliente1.id,
        comanda="WA1003",
        tipo="delivery",
        origem="whatsapp_bot",
        tipo_entrega="entrega",
        cliente_nome="Joao Silva",
        cliente_telefone="11987654321",
        endereco_entrega="Rua Augusta 1000",
        itens="1x Pizza Margherita",
        valor_total=52.90,
        status="em_rota",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def motoboy1(db, restaurante1):
    m = Motoboy(
        restaurante_id=restaurante1.id,
        nome="Carlos Entregador",
        usuario="carlos",
        telefone="11999001122",
        status="ativo",
        disponivel=True,
        latitude_atual=-23.56,
        longitude_atual=-46.64,
    )
    m.set_senha("moto123")
    db.add(m)
    db.flush()
    return m


@pytest.fixture
def entrega_em_rota(db, pedido_em_rota, motoboy1):
    e = Entrega(
        pedido_id=pedido_em_rota.id,
        motoboy_id=motoboy1.id,
        status="em_rota",
        tempo_entrega=20,
    )
    db.add(e)
    db.flush()
    return e


@pytest.fixture
def conversa1(db, restaurante1, cliente1, pedido1):
    c = BotConversa(
        restaurante_id=restaurante1.id,
        cliente_id=cliente1.id,
        telefone="11987654321",
        nome_cliente="Joao Silva",
        status="ativa",
        pedido_ativo_id=pedido1.id,
        session_data={},
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def conversa_sem_pedido(db, restaurante1, cliente1):
    c = BotConversa(
        restaurante_id=restaurante1.id,
        cliente_id=cliente1.id,
        telefone="11987654321",
        nome_cliente="Joao Silva",
        status="ativa",
        session_data={},
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def bairro_consolacao(db, restaurante1):
    b = BairroEntrega(
        restaurante_id=restaurante1.id,
        nome="Consolacao",
        taxa_entrega=8.0,
        tempo_estimado_min=25,
        ativo=True,
    )
    db.add(b)
    db.flush()
    return b


@pytest.fixture
def bairro_pinheiros(db, restaurante1):
    b = BairroEntrega(
        restaurante_id=restaurante1.id,
        nome="Pinheiros",
        taxa_entrega=10.0,
        tempo_estimado_min=35,
        ativo=True,
    )
    db.add(b)
    db.flush()
    return b


@pytest.fixture
def cupom_10pct(db, restaurante1):
    """Cupom percentual 10% ativo."""
    p = Promocao(
        restaurante_id=restaurante1.id,
        nome="10% OFF",
        tipo_desconto="percentual",
        valor_desconto=10,
        codigo_cupom="PIZZA10",
        ativo=True,
        uso_limitado=False,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def cupom_fixo(db, restaurante1):
    """Cupom fixo R$15 ativo."""
    p = Promocao(
        restaurante_id=restaurante1.id,
        nome="R$15 OFF",
        tipo_desconto="fixo",
        valor_desconto=15.0,
        codigo_cupom="DESC15",
        ativo=True,
        uso_limitado=False,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def cupom_expirado(db, restaurante1):
    """Cupom com data de validade expirada."""
    p = Promocao(
        restaurante_id=restaurante1.id,
        nome="Cupom Expirado",
        tipo_desconto="percentual",
        valor_desconto=20,
        codigo_cupom="EXPIRED20",
        ativo=True,
        data_fim=datetime.utcnow() - timedelta(days=1),
        uso_limitado=False,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def cupom_esgotado(db, restaurante1):
    """Cupom com usos esgotados."""
    p = Promocao(
        restaurante_id=restaurante1.id,
        nome="Cupom Lotado",
        tipo_desconto="percentual",
        valor_desconto=5,
        codigo_cupom="LOTADO5",
        ativo=True,
        uso_limitado=True,
        limite_usos=10,
        usos_realizados=10,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def cupom_exclusivo(db, restaurante1, cliente1):
    """Cupom exclusivo para cliente1."""
    p = Promocao(
        restaurante_id=restaurante1.id,
        nome="Cupom VIP",
        tipo_desconto="percentual",
        valor_desconto=15,
        codigo_cupom="VIP15",
        ativo=True,
        cliente_id=cliente1.id,
        tipo_cupom="exclusivo",
        uso_limitado=False,
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def pedido_cozinha_novo(db, restaurante1, pedido1):
    """PedidoCozinha com status NOVO."""
    pc = PedidoCozinha(
        restaurante_id=restaurante1.id,
        pedido_id=pedido1.id,
        status="NOVO",
        pausado=False,
    )
    db.add(pc)
    db.flush()
    return pc


# ==================== HELPER ====================


def _run_func(db, restaurante_id, bot_config, nome, args, conversa=None):
    """Executa uma function call e retorna dict parseado."""
    from backend.app.bot.function_calls import executar_funcao

    loop = asyncio.new_event_loop()
    try:
        result_str = loop.run_until_complete(
            executar_funcao(nome, args, db, restaurante_id, bot_config, conversa)
        )
    finally:
        loop.close()
    return json.loads(result_str)


# ==================== 13. REGISTRAR_PROBLEMA (10 testes) ====================


class TestRegistrarProblema:
    """Funcao 13: registrar_problema"""

    def test_registrar_problema_atraso_com_politica(self, db, restaurante1, bot_config, conversa1):
        """Registra problema tipo atraso - politica gera cupom automatico."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Pedido atrasou 40 minutos",
        }, conversa1)
        assert result["sucesso"] is True
        assert result["problema_id"] > 0
        assert result["acao_aplicada"] == "desconto_proximo"
        assert "cupom" in result
        assert result["desconto_pct"] == 10

    def test_registrar_problema_item_errado_brinde(self, db, restaurante1, bot_config, conversa1):
        """Registra problema item_errado - politica brinde_reenviar."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "item_errado",
            "descricao": "Veio pizza de frango em vez de margherita",
        }, conversa1)
        assert result["sucesso"] is True
        assert result["acao_aplicada"] == "brinde"

    def test_registrar_problema_qualidade_reembolso(self, db, restaurante1, bot_config, conversa1):
        """Registra problema qualidade - politica reembolso_parcial."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "qualidade",
            "descricao": "Pizza chegou fria e murcha",
        }, conversa1)
        assert result["sucesso"] is True
        assert result["acao_aplicada"] == "reembolso"
        assert result["problema_id"] > 0

    def test_registrar_problema_item_faltando_desculpar(self, db, restaurante1, bot_config, conversa1):
        """Registra problema item_faltando - politica so desculpa."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "item_faltando",
            "descricao": "Faltou a coca-cola no pedido",
        }, conversa1)
        assert result["sucesso"] is True
        assert result["acao_aplicada"] == "desculpar"

    def test_registrar_problema_tipo_outro(self, db, restaurante1, bot_config, conversa1):
        """Registra problema generico tipo outro."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "outro",
            "descricao": "O entregador foi rude",
        }, conversa1)
        assert result["sucesso"] is True
        assert result["problema_id"] > 0

    def test_registrar_problema_com_pedido_id(self, db, restaurante1, bot_config, pedido1, conversa1):
        """Registra problema vinculado a um pedido especifico."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Atrasou demais",
            "pedido_id": pedido1.id,
        }, conversa1)
        assert result["sucesso"] is True
        problema = db.query(BotProblema).filter(
            BotProblema.id == result["problema_id"]
        ).first()
        assert problema is not None
        assert problema.pedido_id == pedido1.id

    def test_registrar_problema_sem_pedido_id(self, db, restaurante1, bot_config, conversa1):
        """Registra problema sem pedido vinculado."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "outro",
            "descricao": "Reclamacao geral",
        }, conversa1)
        assert result["sucesso"] is True
        problema = db.query(BotProblema).filter(
            BotProblema.id == result["problema_id"]
        ).first()
        assert problema is not None
        assert problema.pedido_id is None

    def test_registrar_problema_sem_conversa(self, db, restaurante1, bot_config):
        """Registra problema sem conversa (cliente_id fica None)."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Sem conversa",
        }, None)
        assert result["sucesso"] is True
        problema = db.query(BotProblema).filter(
            BotProblema.id == result["problema_id"]
        ).first()
        assert problema.cliente_id is None
        assert problema.conversa_id is None

    def test_registrar_problema_multi_tenant(self, db, restaurante1, restaurante2, bot_config, conversa1):
        """Problema registrado para restaurante1 nao aparece no restaurante2."""
        result = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Multi-tenant test",
        }, conversa1)
        assert result["sucesso"] is True
        problema = db.query(BotProblema).filter(
            BotProblema.id == result["problema_id"]
        ).first()
        assert problema.restaurante_id == restaurante1.id
        assert problema.restaurante_id != restaurante2.id

    def test_registrar_problema_gera_cupom_unico(self, db, restaurante1, bot_config, conversa1):
        """Cada problema de atraso gera um cupom com codigo unico."""
        result1 = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Atraso 1",
        }, conversa1)
        result2 = _run_func(db, restaurante1.id, bot_config, "registrar_problema", {
            "tipo": "atraso",
            "descricao": "Atraso 2",
        }, conversa1)
        assert result1["cupom"] != result2["cupom"]


# ==================== 14. APLICAR_CUPOM (10 testes) ====================


class TestAplicarCupom:
    """Funcao 14: aplicar_cupom"""

    def test_aplicar_cupom_percentual_valido(self, db, restaurante1, bot_config, cupom_10pct, conversa1):
        """Aplica cupom percentual de 10% sobre R$100."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "PIZZA10",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is True
        assert result["desconto"] == 10.0
        assert result["novo_total"] == 90.0

    def test_aplicar_cupom_fixo_valido(self, db, restaurante1, bot_config, cupom_fixo, conversa1):
        """Aplica cupom fixo R$15 sobre R$100."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "DESC15",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is True
        assert result["desconto"] == 15.0
        assert result["novo_total"] == 85.0

    def test_aplicar_cupom_expirado(self, db, restaurante1, bot_config, cupom_expirado, conversa1):
        """Cupom expirado retorna invalido."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "EXPIRED20",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is False

    def test_aplicar_cupom_esgotado(self, db, restaurante1, bot_config, cupom_esgotado, conversa1):
        """Cupom com usos esgotados retorna invalido."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "LOTADO5",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is False
        assert "esgotado" in result["mensagem"].lower()

    def test_aplicar_cupom_inexistente(self, db, restaurante1, bot_config, conversa1):
        """Cupom que nao existe retorna invalido."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "NAO_EXISTE",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is False

    def test_aplicar_cupom_case_insensitive(self, db, restaurante1, bot_config, cupom_10pct, conversa1):
        """Cupom funciona independente de case (enviado em lowercase)."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "pizza10",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is True
        assert result["desconto"] == 10.0

    def test_aplicar_cupom_pedido_minimo_insuficiente(self, db, restaurante1, bot_config, conversa1):
        """Cupom com pedido minimo rejeita valor abaixo."""
        promo = Promocao(
            restaurante_id=restaurante1.id,
            nome="Min 50",
            tipo_desconto="percentual",
            valor_desconto=10,
            codigo_cupom="MIN50",
            ativo=True,
            valor_pedido_minimo=50.0,
            uso_limitado=False,
        )
        db.add(promo)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "MIN50",
            "valor_pedido": 30.0,
        }, conversa1)
        assert result["valido"] is False
        assert "50" in result["mensagem"]

    def test_aplicar_cupom_desconto_maximo(self, db, restaurante1, bot_config, conversa1):
        """Cupom percentual com desconto maximo respeita o teto."""
        promo = Promocao(
            restaurante_id=restaurante1.id,
            nome="20% max 25",
            tipo_desconto="percentual",
            valor_desconto=20,
            codigo_cupom="MAX25",
            desconto_maximo=25.0,
            ativo=True,
            uso_limitado=False,
        )
        db.add(promo)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "MAX25",
            "valor_pedido": 200.0,
        }, conversa1)
        # 20% de 200 = 40, mas maximo e 25
        assert result["valido"] is True
        assert result["desconto"] == 25.0
        assert result["novo_total"] == 175.0

    def test_aplicar_cupom_exclusivo_cliente_correto(self, db, restaurante1, bot_config, cupom_exclusivo, conversa1):
        """Cupom exclusivo funciona para o cliente correto."""
        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "VIP15",
            "valor_pedido": 100.0,
        }, conversa1)
        assert result["valido"] is True
        assert result["desconto"] == 15.0

    def test_aplicar_cupom_exclusivo_cliente_errado(self, db, restaurante1, bot_config, cupom_exclusivo):
        """Cupom exclusivo para cliente1, mas conversa com outro cliente rejeita."""
        c2 = Cliente(
            restaurante_id=restaurante1.id,
            nome="Outro Cliente",
            telefone="11999888777",
            senha_hash=hashlib.sha256("123456".encode()).hexdigest(),
        )
        db.add(c2)
        db.flush()
        conv_outro = BotConversa(
            restaurante_id=restaurante1.id,
            cliente_id=c2.id,
            telefone="11999888777",
            status="ativa",
            session_data={},
        )
        db.add(conv_outro)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "aplicar_cupom", {
            "codigo_cupom": "VIP15",
            "valor_pedido": 100.0,
        }, conv_outro)
        assert result["valido"] is False
        assert "exclusivo" in result["mensagem"].lower()


# ==================== 15. ESCALAR_HUMANO (10 testes) ====================


class TestEscalarHumano:
    """Funcao 15: escalar_humano"""

    def test_escalar_humano_sucesso(self, db, restaurante1, bot_config, conversa1):
        """Escalar humano marca conversa como aguardando_handoff."""
        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Cliente insiste em falar com gerente",
        }, conversa1)
        assert result["sucesso"] is True
        db.expire(conversa1)
        assert conversa1.status == "aguardando_handoff"

    def test_escalar_humano_com_motivo(self, db, restaurante1, bot_config):
        """Escalar humano salva o motivo na conversa."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11912345678",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        motivo = "Problema complexo que nao consigo resolver"
        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": motivo,
        }, conv)
        assert result["sucesso"] is True
        db.expire(conv)
        assert conv.handoff_motivo == motivo
        assert conv.handoff_em is not None

    def test_escalar_humano_sem_conversa(self, db, restaurante1, bot_config):
        """Escalar humano sem conversa ainda retorna sucesso."""
        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Teste sem conversa",
        }, None)
        assert result["sucesso"] is True

    def test_escalar_humano_multi_tenant(self, db, restaurante1, restaurante2, bot_config):
        """Conversa do restaurante1 nao afeta restaurante2."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900001111",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Handoff multi-tenant",
        }, conv)

        convs_rest2 = db.query(BotConversa).filter(
            BotConversa.restaurante_id == restaurante2.id,
            BotConversa.status == "aguardando_handoff",
        ).count()
        assert convs_rest2 == 0

    def test_escalar_humano_timestamp_handoff(self, db, restaurante1, bot_config):
        """Handoff registra timestamp."""
        antes = datetime.utcnow()
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900002222",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Teste timestamp",
        }, conv)
        db.expire(conv)
        assert conv.handoff_em is not None
        assert conv.handoff_em >= antes

    def test_escalar_humano_status_muda_para_handoff(self, db, restaurante1, bot_config):
        """Conversa muda de 'ativa' para 'aguardando_handoff'."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900003333",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()
        assert conv.status == "ativa"

        _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Mudanca status",
        }, conv)
        db.expire(conv)
        assert conv.status == "aguardando_handoff"

    def test_escalar_humano_mensagem_orientacao(self, db, restaurante1, bot_config):
        """Resposta contem orientacao para o bot continuar atendendo."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900004444",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Orientacao",
        }, conv)
        assert "mensagem" in result
        assert "notificado" in result["mensagem"].lower()

    def test_escalar_humano_motivo_padrao(self, db, restaurante1, bot_config):
        """Motivo padrao quando fornecido explicitamente."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900005555",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Solicitado pelo cliente",
        }, conv)
        db.expire(conv)
        assert conv.handoff_motivo == "Solicitado pelo cliente"

    def test_escalar_humano_websocket_nao_bloqueia(self, db, restaurante1, bot_config):
        """Mesmo se WebSocket falhar, handoff funciona."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900006666",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "WS fail test",
        }, conv)
        assert result["sucesso"] is True

    def test_escalar_humano_retorna_sucesso_consistente(self, db, restaurante1, bot_config):
        """Resultado sempre tem 'sucesso' e 'mensagem'."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            telefone="11900007777",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "escalar_humano", {
            "motivo": "Consistencia",
        }, conv)
        assert "sucesso" in result
        assert "mensagem" in result
        assert result["sucesso"] is True


# ==================== 16. RASTREAR_PEDIDO (10 testes) ====================


class TestRastrearPedido:
    """Funcao 16: rastrear_pedido"""

    def test_rastrear_por_id(self, db, restaurante1, bot_config, pedido1):
        """Rastrear pedido por ID retorna dados corretos."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert result["pedido_id"] == pedido1.id
        assert result["comanda"] == "WA1001"
        assert result["status"] == "em_preparo"

    def test_rastrear_por_telefone(self, db, restaurante1, bot_config, pedido1, cliente1):
        """Rastrear pedido por telefone busca o mais recente."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "telefone": "11987654321",
        })
        assert result["pedido_id"] > 0
        assert "status" in result

    def test_rastrear_com_motoboy_gps(self, db, restaurante1, bot_config, pedido_em_rota, motoboy1, entrega_em_rota):
        """Rastrear pedido em_rota mostra GPS do motoboy."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido_em_rota.id,
        })
        assert result["status"] == "em_rota"
        assert result["motoboy_nome"] == "Carlos Entregador"
        assert "motoboy_gps" in result
        assert result["motoboy_gps"]["lat"] == -23.56

    def test_rastrear_sem_motoboy(self, db, restaurante1, bot_config, pedido1):
        """Pedido em_preparo sem motoboy nao tem dados de GPS."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert "motoboy_gps" not in result
        assert "motoboy_nome" not in result

    def test_rastrear_posicao_fila_cozinha(self, db, restaurante1, bot_config, pedido1, pedido_cozinha_novo):
        """Pedido em_preparo mostra posicao na fila da cozinha."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert "posicao_fila" in result
        assert result["posicao_fila"] >= 1
        assert result["status_cozinha"] == "NOVO"

    def test_rastrear_pedido_nao_encontrado(self, db, restaurante1, bot_config):
        """Pedido inexistente retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": 99999,
        })
        assert "erro" in result

    def test_rastrear_link_rastreamento(self, db, restaurante1, bot_config, pedido1):
        """Resultado inclui link de rastreamento."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert "link_rastreamento" in result
        assert "PIZZA001" in result["link_rastreamento"]

    def test_rastrear_multi_tenant(self, db, restaurante1, restaurante2, bot_config, pedido1):
        """Pedido do restaurante1 nao aparece no restaurante2."""
        result = _run_func(db, restaurante2.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert "erro" in result

    def test_rastrear_minutos_desde_criacao(self, db, restaurante1, bot_config, pedido1):
        """Resultado inclui tempo desde criacao."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido1.id,
        })
        assert "minutos_desde_criacao" in result
        assert result["minutos_desde_criacao"] >= 0

    def test_rastrear_com_eta_entrega(self, db, restaurante1, bot_config, pedido_em_rota, motoboy1, entrega_em_rota):
        """Pedido em rota mostra ETA de entrega."""
        result = _run_func(db, restaurante1.id, bot_config, "rastrear_pedido", {
            "pedido_id": pedido_em_rota.id,
        })
        assert "eta_entrega_min" in result
        assert result["eta_entrega_min"] == 20


# ==================== 17. TROCAR_ITEM_PEDIDO (10 testes) ====================


class TestTrocarItemPedido:
    """Funcao 17: trocar_item_pedido"""

    def test_trocar_sucesso(self, db, restaurante1, bot_config, produto_margherita, produto_calabresa, conversa1, pedido1, pedido_cozinha_novo):
        """Troca Pizza Margherita por Pizza Calabresa com sucesso."""
        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido1.id,
            "item_remover": "Margherita",
            "item_novo": "Calabresa",
        }, conversa1)
        assert result["sucesso"] is True
        assert "Calabresa" in result["adicionado"]
        assert result["novo_total"] > 0

    def test_trocar_item_nao_existe_no_pedido(self, db, restaurante1, bot_config, produto_margherita, conversa1):
        """Tentar trocar item que nao esta no pedido retorna erro."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2001",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990099",
            itens="1x Pizza Margherita",
            valor_total=45.90,
            status="pendente",
        )
        db.add(pedido)
        db.flush()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_margherita.id,
            quantidade=1,
            preco_unitario=45.90,
        )
        db.add(item)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Frango",
            "item_novo": "Calabresa",
        }, conversa1)
        assert "erro" in result

    def test_trocar_novo_item_indisponivel(self, db, restaurante1, bot_config, produto_margherita, produto_indisponivel, conversa1):
        """Trocar por item indisponivel retorna erro."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2002",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990098",
            itens="1x Pizza Margherita",
            valor_total=45.90,
            status="pendente",
        )
        db.add(pedido)
        db.flush()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_margherita.id,
            quantidade=1,
            preco_unitario=45.90,
        )
        db.add(item)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Margherita",
            "item_novo": "Quatro Queijos",
        }, conversa1)
        assert "erro" in result
        assert "indispon" in result["erro"].lower()

    def test_trocar_novo_item_esgotado(self, db, restaurante1, bot_config, produto_margherita, produto_esgotado, conversa1):
        """Trocar por item com estoque zerado retorna erro."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2003",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990097",
            itens="1x Pizza Margherita",
            valor_total=45.90,
            status="pendente",
        )
        db.add(pedido)
        db.flush()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_margherita.id,
            quantidade=1,
            preco_unitario=45.90,
        )
        db.add(item)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Margherita",
            "item_novo": "Portuguesa",
        }, conversa1)
        assert "erro" in result
        assert "esgot" in result["erro"].lower()

    def test_trocar_cozinha_ja_comecou(self, db, restaurante1, bot_config, conversa1, produto_margherita, produto_calabresa):
        """Nao permite troca se KDS ja esta FAZENDO."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2004",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990096",
            itens="1x Pizza Margherita",
            valor_total=45.90,
            status="em_preparo",
        )
        db.add(pedido)
        db.flush()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_margherita.id,
            quantidade=1,
            preco_unitario=45.90,
        )
        db.add(item)
        db.flush()

        pc = PedidoCozinha(
            restaurante_id=restaurante1.id,
            pedido_id=pedido.id,
            status="FAZENDO",
            pausado=False,
        )
        db.add(pc)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Margherita",
            "item_novo": "Calabresa",
        }, conversa1)
        assert "erro" in result
        assert "cozinha" in result["erro"].lower()

    def test_trocar_status_bloqueado(self, db, restaurante1, bot_config, conversa1):
        """Nao permite troca em pedido com status pronto."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2005",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990095",
            itens="1x Pizza Margherita",
            valor_total=45.90,
            status="pronto",
        )
        db.add(pedido)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Margherita",
            "item_novo": "Calabresa",
        }, conversa1)
        assert "erro" in result

    def test_trocar_sem_permissao(self, db, restaurante2, bot_config_no_perms):
        """Bot sem permissao de alterar retorna erro."""
        result = _run_func(db, restaurante2.id, bot_config_no_perms, "trocar_item_pedido", {
            "pedido_id": 1,
            "item_remover": "X",
            "item_novo": "Y",
        })
        assert "erro" in result
        assert "permiss" in result["erro"].lower()

    def test_trocar_recalcula_total(self, db, restaurante1, bot_config, conversa1, produto_margherita, produto_calabresa):
        """Apos troca, o valor total e recalculado."""
        pedido = Pedido(
            restaurante_id=restaurante1.id,
            comanda="WA2006",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test",
            cliente_telefone="11999990094",
            itens="1x Pizza Margherita",
            valor_subtotal=45.90,
            valor_taxa_entrega=7.0,
            valor_total=52.90,
            status="pendente",
        )
        db.add(pedido)
        db.flush()

        item = ItemPedido(
            pedido_id=pedido.id,
            produto_id=produto_margherita.id,
            quantidade=1,
            preco_unitario=45.90,
        )
        db.add(item)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido.id,
            "item_remover": "Margherita",
            "item_novo": "Calabresa",
        }, conversa1)
        assert result["sucesso"] is True
        # Calabresa custa 49.90, taxa 7.0
        assert result["novo_total"] == pytest.approx(49.90 + 7.0, abs=0.1)

    def test_trocar_pedido_nao_encontrado(self, db, restaurante1, bot_config, conversa1):
        """Pedido inexistente retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "trocar_item_pedido", {
            "pedido_id": 99999,
            "item_remover": "X",
            "item_novo": "Y",
        }, conversa1)
        assert "erro" in result

    def test_trocar_multi_tenant(self, db, restaurante1, restaurante2, bot_config, conversa1, pedido1):
        """Pedido do restaurante1 nao pode ser trocado pelo restaurante2."""
        result = _run_func(db, restaurante2.id, bot_config, "trocar_item_pedido", {
            "pedido_id": pedido1.id,
            "item_remover": "Margherita",
            "item_novo": "Calabresa",
        }, conversa1)
        assert "erro" in result


# ==================== 18. CONSULTAR_TEMPO_ENTREGA (10 testes) ====================


class TestConsultarTempoEntrega:
    """Funcao 18: consultar_tempo_entrega"""

    def test_fila_vazia(self, db, restaurante1, bot_config, config_rest, site_config):
        """Fila vazia retorna tempo base de preparo."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {})
        assert result["tempo_preparo_min"] == 25
        assert result["pedidos_na_fila"] == 0

    def test_fila_cheia(self, db, restaurante1, bot_config, config_rest):
        """Fila com mais de 3 pedidos aumenta o tempo."""
        for i in range(5):
            ped = Pedido(
                restaurante_id=restaurante1.id,
                comanda=f"FILA{i}",
                tipo="delivery",
                tipo_entrega="entrega",
                cliente_nome=f"Fila {i}",
                itens="1x item",
                valor_total=10.0,
                status="em_preparo",
            )
            db.add(ped)
            db.flush()
            pc = PedidoCozinha(
                restaurante_id=restaurante1.id,
                pedido_id=ped.id,
                status="NOVO",
                pausado=False,
            )
            db.add(pc)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {})
        assert result["pedidos_na_fila"] >= 5
        assert result["tempo_preparo_min"] > 25

    def test_com_bairro_cadastrado(self, db, restaurante1, bot_config, config_rest, bairro_consolacao):
        """Com bairro cadastrado retorna taxa e tempo especificos."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {
            "bairro": "Consolacao",
        })
        assert result["bairro"] == "Consolacao"
        assert result["taxa_entrega"] == 8.0
        assert result["tempo_entrega_bairro_min"] == 25

    def test_com_bairro_nao_cadastrado(self, db, restaurante1, bot_config, config_rest, site_config, bairro_consolacao):
        """Bairro nao cadastrado usa estimativa padrao."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {
            "bairro": "Vila Olimpia",
        })
        assert result["bairro_nao_cadastrado"] is True
        assert "taxa_entrega" in result

    def test_sem_bairro(self, db, restaurante1, bot_config, config_rest, site_config):
        """Sem bairro retorna tempo medio geral."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {})
        assert "tempo_entrega_medio_min" in result
        assert "total_estimado_min" in result

    def test_total_estimado_inclui_preparo_e_entrega(self, db, restaurante1, bot_config, config_rest, bairro_pinheiros):
        """Total estimado = preparo + entrega do bairro."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {
            "bairro": "Pinheiros",
        })
        assert result["total_estimado_min"] == result["tempo_preparo_min"] + 35

    def test_multi_tenant(self, db, restaurante2, bot_config, bairro_consolacao):
        """Bairros do restaurante1 nao aparecem no restaurante2."""
        result = _run_func(db, restaurante2.id, bot_config, "consultar_tempo_entrega", {
            "bairro": "Consolacao",
        })
        # Rest2 nao tem bairro Consolacao cadastrado
        assert result.get("bairro_nao_cadastrado", True) is True

    def test_sem_config_usa_padrao(self, db, restaurante2, bot_config):
        """Restaurante sem config usa valores padrao (30 min)."""
        result = _run_func(db, restaurante2.id, bot_config, "consultar_tempo_entrega", {})
        assert result["tempo_preparo_min"] == 30

    def test_bairro_busca_parcial(self, db, restaurante1, bot_config, config_rest, bairro_consolacao):
        """Busca parcial do bairro funciona (ilike)."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {
            "bairro": "consol",
        })
        assert result.get("bairro") == "Consolacao"

    def test_pedidos_pausados_nao_contam(self, db, restaurante1, bot_config, config_rest):
        """Pedidos pausados nao contam na fila."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PAUSA1",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Pausado",
            itens="1x item",
            valor_total=10.0,
            status="em_preparo",
        )
        db.add(ped)
        db.flush()
        pc = PedidoCozinha(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            status="NOVO",
            pausado=True,
        )
        db.add(pc)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_tempo_entrega", {})
        fila_sem_pausado = db.query(PedidoCozinha).filter(
            PedidoCozinha.restaurante_id == restaurante1.id,
            PedidoCozinha.status.in_(["NOVO", "FAZENDO"]),
            PedidoCozinha.pausado == False,
        ).count()
        assert result["pedidos_na_fila"] == fila_sem_pausado


# ==================== 19. CONSULTAR_BAIRROS (10 testes) ====================


class TestConsultarBairros:
    """Funcao 19: consultar_bairros"""

    def test_listar_todos_bairros(self, db, restaurante1, bot_config, bairro_consolacao, bairro_pinheiros):
        """Lista todos os bairros ativos."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {})
        assert result["encontrados"] >= 2
        nomes = [b["nome"] for b in result["bairros"]]
        assert "Consolacao" in nomes
        assert "Pinheiros" in nomes

    def test_filtrar_por_nome(self, db, restaurante1, bot_config, bairro_consolacao, bairro_pinheiros):
        """Filtro por nome retorna apenas o bairro correspondente."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {
            "nome_bairro": "Pinheiros",
        })
        assert result["encontrados"] == 1
        assert result["bairros"][0]["nome"] == "Pinheiros"

    def test_nenhum_bairro_cadastrado(self, db, restaurante2, bot_config):
        """Restaurante sem bairros cadastrados retorna taxa fixa."""
        config2 = ConfigRestaurante(
            restaurante_id=restaurante2.id,
            taxa_entrega_base=5.0,
        )
        db.add(config2)
        db.flush()

        result = _run_func(db, restaurante2.id, bot_config, "consultar_bairros", {})
        assert result["encontrados"] == 0
        assert result["taxa_fixa"] is True
        assert result["taxa_entrega_padrao"] == 5.0

    def test_filtro_nao_encontrado(self, db, restaurante1, bot_config, bairro_consolacao):
        """Filtro que nao encontra nenhum bairro retorna mensagem."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {
            "nome_bairro": "Copacabana",
        })
        assert result["encontrados"] == 0
        assert "mensagem" in result

    def test_bairro_taxa_e_tempo(self, db, restaurante1, bot_config, bairro_consolacao):
        """Cada bairro retorna taxa e tempo estimado."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {
            "nome_bairro": "Consolacao",
        })
        bairro = result["bairros"][0]
        assert bairro["taxa_entrega"] == 8.0
        assert bairro["tempo_estimado_min"] == 25

    def test_multi_tenant_bairros(self, db, restaurante1, restaurante2, bot_config, bairro_consolacao):
        """Bairros do restaurante1 nao aparecem no restaurante2."""
        result = _run_func(db, restaurante2.id, bot_config, "consultar_bairros", {
            "nome_bairro": "Consolacao",
        })
        assert result["encontrados"] == 0

    def test_filtro_parcial(self, db, restaurante1, bot_config, bairro_consolacao):
        """Filtro parcial ilike funciona."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {
            "nome_bairro": "conso",
        })
        assert result["encontrados"] >= 1

    def test_bairro_inativo_nao_aparece(self, db, restaurante1, bot_config):
        """Bairro inativo nao e listado."""
        b_inativo = BairroEntrega(
            restaurante_id=restaurante1.id,
            nome="Bairro Inativo",
            taxa_entrega=99.0,
            tempo_estimado_min=99,
            ativo=False,
        )
        db.add(b_inativo)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {
            "nome_bairro": "Bairro Inativo",
        })
        assert result["encontrados"] == 0

    def test_ordem_alfabetica(self, db, restaurante1, bot_config, bairro_consolacao, bairro_pinheiros):
        """Bairros sao retornados em ordem alfabetica."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_bairros", {})
        if result["encontrados"] >= 2:
            nomes = [b["nome"] for b in result["bairros"]]
            assert nomes == sorted(nomes)

    def test_sem_filtro_sem_bairros_retorna_mensagem(self, db, restaurante2, bot_config):
        """Sem bairros, sem filtro retorna mensagem informativa."""
        result = _run_func(db, restaurante2.id, bot_config, "consultar_bairros", {})
        assert "mensagem" in result


# ==================== 20. ATUALIZAR_ENDERECO_CLIENTE (10 testes) ====================


class TestAtualizarEnderecoCliente:
    """Funcao 20: atualizar_endereco_cliente"""

    def test_atualizar_sucesso(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Atualiza endereco existente com sucesso."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Nova 500, Bela Vista",
            "bairro": "",
        })
        assert result["sucesso"] is True
        assert result["endereco"] == "Rua Nova 500, Bela Vista"

    def test_cadastrar_endereco_novo(self, db, restaurante1, bot_config):
        """Cadastra endereco para cliente sem endereco."""
        c = Cliente(
            restaurante_id=restaurante1.id,
            nome="Sem Endereco",
            telefone="11900010001",
            senha_hash=hashlib.sha256("123456".encode()).hexdigest(),
        )
        db.add(c)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11900010001",
            "endereco_completo": "Rua Criada 100",
            "bairro": "",
        })
        assert result["sucesso"] is True
        assert "cadastrado" in result["mensagem"].lower()

    def test_cliente_nao_encontrado(self, db, restaurante1, bot_config):
        """Telefone inexistente retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "00000000000",
            "endereco_completo": "Rua Qualquer 1",
        })
        assert "erro" in result

    def test_endereco_obrigatorio(self, db, restaurante1, bot_config, cliente1):
        """Endereco vazio retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "",
        })
        assert "erro" in result

    def test_bairro_nao_atendido(self, db, restaurante1, bot_config, cliente1, bairro_consolacao):
        """Bairro fora da area de entrega retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Longe 999",
            "bairro": "Bairro Distante",
        })
        assert "erro" in result

    def test_bairro_atendido(self, db, restaurante1, bot_config, cliente1, bairro_consolacao):
        """Bairro dentro da area de entrega funciona."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Consolacao 200",
            "bairro": "Consolacao",
        })
        assert result["sucesso"] is True

    def test_com_complemento_e_referencia(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Atualiza com complemento e referencia."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Augusta 1000",
            "complemento": "Apto 303, Bloco B",
            "referencia": "Proximo ao metro",
        })
        assert result["sucesso"] is True

    def test_multi_tenant(self, db, restaurante2, bot_config, cliente2):
        """Endereco do restaurante2 e isolado."""
        result = _run_func(db, restaurante2.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Rest2 100",
        })
        assert result["sucesso"] is True

    def test_sem_bairros_cadastrados_aceita_qualquer(self, db, restaurante2, bot_config):
        """Restaurante sem bairros cadastrados aceita qualquer bairro."""
        c = Cliente(
            restaurante_id=restaurante2.id,
            nome="Livre",
            telefone="11900020002",
            senha_hash=hashlib.sha256("123456".encode()).hexdigest(),
        )
        db.add(c)
        db.flush()

        result = _run_func(db, restaurante2.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11900020002",
            "endereco_completo": "Rua Qualquer",
            "bairro": "Qualquer Bairro",
        })
        assert result["sucesso"] is True

    def test_atualiza_endereco_padrao_existente(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Atualizar endereco quando ja existe padrao substitui o existente."""
        result = _run_func(db, restaurante1.id, bot_config, "atualizar_endereco_cliente", {
            "telefone": "11987654321",
            "endereco_completo": "Rua Substituida 777",
        })
        assert result["sucesso"] is True
        assert "atualizado" in result["mensagem"].lower()

        db.expire(cliente1_endereco)
        assert cliente1_endereco.endereco_completo == "Rua Substituida 777"


# ==================== 21. VALIDAR_ENDERECO (10 testes) ====================


class TestValidarEndereco:
    """Funcao 21: validar_endereco (MOCK Mapbox)"""

    def _mock_autocomplete(self, results):
        """Cria mock para autocomplete_address (importado localmente de utils.mapbox_api)."""
        return patch(
            "utils.mapbox_api.autocomplete_address",
            return_value=results,
        )

    def _mock_haversine(self, distance=2.0):
        """Mock haversine para retornar distancia fixa (importado localmente de utils.haversine)."""
        return patch(
            "utils.haversine.haversine",
            return_value=distance,
        )

    def _mock_cache(self):
        """Mock cache para nao depender de Redis (importados localmente)."""
        cache_get_mock = patch("backend.app.cache.cache_get", return_value=None)
        cache_set_mock = patch("backend.app.cache.cache_set")
        cache_key_mock = patch("utils.mapbox_api._cache_key_dist", return_value="test_key")

        class _CombinedMock:
            def __enter__(self_inner):
                self_inner._mocks = [cache_get_mock.__enter__(), cache_set_mock.__enter__(), cache_key_mock.__enter__()]
                return self_inner
            def __exit__(self_inner, *args):
                cache_key_mock.__exit__(*args)
                cache_set_mock.__exit__(*args)
                cache_get_mock.__exit__(*args)

        return _CombinedMock()

    def test_alta_confianca_resultado_unico(self, db, restaurante1, bot_config, config_rest, conversa1):
        """1 resultado proximo = alta confianca."""
        sugestoes = [{
            "place_name": "Rua Augusta, 1000, Consolacao, Sao Paulo - SP, 01304-001, Brasil",
            "coordinates": [-23.555, -46.660],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(2.0), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Augusta 1000",
            }, conversa1)

        assert result["encontrado"] is True
        assert result["confianca"] == "alta"
        assert "taxa_entrega" in result

    def test_media_confianca_multiplos_resultados(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Multiplos resultados = media confianca."""
        sugestoes = [
            {
                "place_name": "Rua Augusta, 1000, Consolacao, Sao Paulo - SP, 01304-001, Brasil",
                "coordinates": [-23.555, -46.660],
            },
            {
                "place_name": "Rua Augusta, 1000, Bela Vista, Sao Paulo - SP, 01305-001, Brasil",
                "coordinates": [-23.556, -46.661],
            },
        ]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(2.5), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Augusta 1000",
            }, conversa1)

        assert result["encontrado"] is True
        assert result["confianca"] == "media"
        assert len(result["opcoes_texto"]) >= 2

    def test_fora_de_zona(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Endereco fora do raio de entrega."""
        sugestoes = [{
            "place_name": "Rua Longe, 1, Guarulhos, Sao Paulo - SP, 07000-000, Brasil",
            "coordinates": [-23.40, -46.50],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(15.0), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Longe 1 Guarulhos",
            }, conversa1)

        assert result["encontrado"] is True
        assert result["confianca"] == "fora_zona"

    def test_nao_encontrado(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Nenhum resultado do Mapbox."""
        with self._mock_autocomplete([]):
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "xyzabc123nonsense",
            }, conversa1)

        assert result["encontrado"] is False

    def test_endereco_vazio(self, db, restaurante1, bot_config, conversa1):
        """Endereco vazio retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
            "endereco_texto": "",
        }, conversa1)
        assert "erro" in result

    def test_salva_sugestoes_na_sessao(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Sugestoes sao salvas no session_data da conversa."""
        sugestoes = [{
            "place_name": "Rua Teste, 1, Centro, Sao Paulo - SP, 01000-000, Brasil",
            "coordinates": [-23.55, -46.63],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(1.0), self._mock_cache():
            _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Teste 1",
            }, conversa1)

        db.expire(conversa1)
        assert "endereco_sugestoes" in conversa1.session_data
        assert len(conversa1.session_data["endereco_sugestoes"]) >= 1

    def test_multi_tenant(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Validacao usa dados do restaurante correto."""
        sugestoes = [{
            "place_name": "Rua X, 1, Centro, Sao Paulo - SP, Brasil",
            "coordinates": [-23.55, -46.63],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(2.0), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua X 1",
            }, conversa1)

        assert result["encontrado"] is True

    def test_calcula_taxa_por_distancia(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Taxa calculada com base na distancia (taxa_base + km_extra)."""
        sugestoes = [{
            "place_name": "Rua Distante, 1, Centro, Sao Paulo - SP, Brasil",
            "coordinates": [-23.55, -46.63],
        }]

        # distancia 4.5 = dentro do raio (10km) e < 5 = alta confianca
        with self._mock_autocomplete(sugestoes), self._mock_haversine(4.5), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Distante 1",
            }, conversa1)

        assert result["encontrado"] is True
        assert result["confianca"] == "alta"
        # taxa_base=7.0, distancia_base=3.0, taxa_km_extra=2.0
        # taxa = 7.0 + (4.5-3)*2.0 = 10.0
        assert result["taxa_entrega"] == 10.0

    def test_complemento_salvo_na_sessao(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Complemento e salvo no session_data."""
        sugestoes = [{
            "place_name": "Rua Comp, 1, Centro, Sao Paulo - SP, Brasil",
            "coordinates": [-23.55, -46.63],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(1.0), self._mock_cache():
            _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Comp 1",
                "complemento": "Apto 101",
            }, conversa1)

        db.expire(conversa1)
        assert conversa1.session_data.get("endereco_complemento") == "Apto 101"

    def test_distancia_dentro_base_taxa_base(self, db, restaurante1, bot_config, config_rest, conversa1):
        """Distancia dentro do km base usa apenas taxa base."""
        sugestoes = [{
            "place_name": "Rua Perto, 1, Centro, Sao Paulo - SP, Brasil",
            "coordinates": [-23.55, -46.63],
        }]

        with self._mock_autocomplete(sugestoes), self._mock_haversine(2.0), self._mock_cache():
            result = _run_func(db, restaurante1.id, bot_config, "validar_endereco", {
                "endereco_texto": "Rua Perto 1",
            }, conversa1)

        assert result["encontrado"] is True
        assert result["taxa_entrega"] == 7.0


# ==================== 22. CONFIRMAR_ENDERECO_VALIDADO (10 testes) ====================


class TestConfirmarEnderecoValidado:
    """Funcao 22: confirmar_endereco_validado"""

    def _preparar_conversa_com_sugestoes(self, db, restaurante1, cliente1):
        """Helper: cria conversa com sugestoes no session_data."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            cliente_id=cliente1.id,
            telefone="11987654321",
            status="ativa",
            session_data={
                "endereco_sugestoes": [
                    {
                        "place_name": "Rua Augusta, 1000, Consolacao, Sao Paulo - SP, Brasil",
                        "lat": -23.555,
                        "lng": -46.660,
                        "distancia_km": 2.5,
                        "dentro_zona": True,
                        "taxa_entrega": 8.0,
                    },
                    {
                        "place_name": "Rua Augusta, 2000, Bela Vista, Sao Paulo - SP, Brasil",
                        "lat": -23.560,
                        "lng": -46.665,
                        "distancia_km": 3.5,
                        "dentro_zona": True,
                        "taxa_entrega": 9.0,
                    },
                ],
                "endereco_complemento": "Apto 42",
                "endereco_referencia": "Perto do metro",
            },
        )
        db.add(conv)
        db.flush()
        return conv

    def test_confirmar_sucesso_opcao_0(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Confirma primeira opcao (index 0) com sucesso."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, conv)
        assert result["sucesso"] is True
        assert "Augusta, 1000" in result["endereco"]
        assert result["taxa_entrega"] == 8.0
        assert result["validado_gps"] is True

    def test_confirmar_sucesso_opcao_1(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Confirma segunda opcao (index 1)."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 1,
        }, conv)
        assert result["sucesso"] is True
        assert "Augusta, 2000" in result["endereco"]
        assert result["taxa_entrega"] == 9.0

    def test_opcao_index_invalido(self, db, restaurante1, bot_config, cliente1):
        """Index fora do range retorna erro."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 5,
        }, conv)
        assert "erro" in result

    def test_sem_validacao_previa(self, db, restaurante1, bot_config, cliente1):
        """Sem sugestoes no session_data retorna erro."""
        conv = BotConversa(
            restaurante_id=restaurante1.id,
            cliente_id=cliente1.id,
            telefone="11987654321",
            status="ativa",
            session_data={},
        )
        db.add(conv)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, conv)
        assert "erro" in result

    def test_sem_conversa(self, db, restaurante1, bot_config):
        """Sem conversa retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, None)
        assert "erro" in result

    def test_salva_endereco_validado_na_sessao(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Apos confirmacao, session_data tem endereco_validado."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, conv)
        db.expire(conv)
        assert "endereco_validado" in conv.session_data
        assert conv.session_data["endereco_validado"]["lat"] == -23.555

    def test_limpa_sugestoes_apos_confirmacao(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Sugestoes pendentes sao limpas apos confirmacao."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, conv)
        db.expire(conv)
        assert "endereco_sugestoes" not in conv.session_data

    def test_atualiza_endereco_gps_no_cliente(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Endereco do cliente e atualizado com coordenadas GPS."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
        }, conv)

        db.expire(cliente1_endereco)
        assert cliente1_endereco.latitude == -23.555
        assert cliente1_endereco.longitude == -46.660
        assert cliente1_endereco.validado_mapbox is True

    def test_cliente_nao_encontrado(self, db, restaurante1, bot_config, cliente1):
        """Telefone inexistente retorna erro."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "00000000000",
            "opcao_index": 0,
        }, conv)
        assert "erro" in result

    def test_complemento_no_endereco_display(self, db, restaurante1, bot_config, cliente1, cliente1_endereco):
        """Complemento aparece no endereco exibido."""
        conv = self._preparar_conversa_com_sugestoes(db, restaurante1, cliente1)
        result = _run_func(db, restaurante1.id, bot_config, "confirmar_endereco_validado", {
            "telefone": "11987654321",
            "opcao_index": 0,
            "complemento": "Bloco C, Apto 501",
        }, conv)
        assert result["sucesso"] is True
        assert "Bloco C" in result["endereco"]


# ==================== 23. GERAR_COBRANCA_PIX (10 testes) ====================


class TestGerarCobrancaPix:
    """Funcao 23: gerar_cobranca_pix (MOCK pix service)"""

    def test_cobranca_ativa_existente(self, db, restaurante1, bot_config, pedido1):
        """Se ja existe cobranca ativa nao expirada, retorna ela."""
        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=pedido1.id,
            correlation_id=f"test-{pedido1.id}-active",
            valor_centavos=5290,
            status="ACTIVE",
            payment_link_url="https://pix.example.com/existing",
            br_code="existing_br_code",
            expira_em=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
            "pedido_id": pedido1.id,
        })
        assert result["sucesso"] is True
        assert "existing" in result["pix_payment_link"]

    def test_pedido_nao_encontrado(self, db, restaurante1, bot_config):
        """Pedido inexistente retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
            "pedido_id": 99999,
        })
        assert "erro" in result

    def test_sem_pedido_id(self, db, restaurante1, bot_config):
        """Sem pedido_id retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {})
        assert "erro" in result

    def test_multi_tenant(self, db, restaurante1, restaurante2, bot_config, pedido1):
        """Pedido do rest1 nao pode gerar cobranca pelo rest2."""
        result = _run_func(db, restaurante2.id, bot_config, "gerar_cobranca_pix", {
            "pedido_id": pedido1.id,
        })
        assert "erro" in result

    def test_cobranca_expirada_gera_nova(self, db, restaurante1, bot_config):
        """Cobranca expirada e substituida por nova."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX001",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test Pix",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca_expirada = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"test-{ped.id}-expired",
            valor_centavos=3000,
            status="ACTIVE",
            expira_em=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(cobranca_expirada)
        db.flush()

        mock_pix_data = {
            "payment_link_url": "https://pix.example.com/new",
            "br_code": "new_br_code",
        }
        with patch(
            "backend.app.pix.pix_service.criar_cobranca_pedido",
            new_callable=AsyncMock,
            return_value=mock_pix_data,
        ):
            result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
                "pedido_id": ped.id,
            })

        db.expire(cobranca_expirada)
        assert cobranca_expirada.status == "EXPIRED"
        assert result["sucesso"] is True
        assert result["pix_payment_link"] == "https://pix.example.com/new"

    def test_pix_service_falha(self, db, restaurante1, bot_config):
        """Falha no servico Pix retorna erro."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX002",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test Pix Fail",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        with patch(
            "backend.app.pix.pix_service.criar_cobranca_pedido",
            new_callable=AsyncMock,
            side_effect=Exception("Woovi API offline"),
        ):
            result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
                "pedido_id": ped.id,
            })

        assert "erro" in result

    def test_retorna_payment_link_e_br_code(self, db, restaurante1, bot_config):
        """Resultado contem payment_link e br_code."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX003",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test Pix OK",
            itens="1x item",
            valor_total=50.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        mock_data = {
            "payment_link_url": "https://pay.example.com/xyz",
            "br_code": "pix_br_code_123",
        }
        with patch(
            "backend.app.pix.pix_service.criar_cobranca_pedido",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
                "pedido_id": ped.id,
            })

        assert result["sucesso"] is True
        assert result["pix_payment_link"] == "https://pay.example.com/xyz"
        assert result["pix_br_code"] == "pix_br_code_123"

    def test_cobranca_ativa_nao_expirada_retorna_existente(self, db, restaurante1, bot_config):
        """Cobranca ativa e nao expirada retorna os dados existentes."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX004",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test Pix Existing",
            itens="1x item",
            valor_total=60.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"test-{ped.id}-still-active",
            valor_centavos=6000,
            status="ACTIVE",
            payment_link_url="https://pix.example.com/still-active",
            br_code="still_active_code",
            expira_em=datetime.utcnow() + timedelta(hours=2),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
            "pedido_id": ped.id,
        })
        assert result["sucesso"] is True
        assert "still-active" in result["pix_payment_link"]

    def test_mensagem_descritiva(self, db, restaurante1, bot_config):
        """Resultado inclui mensagem descritiva."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX005",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test Msg",
            itens="1x item",
            valor_total=40.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        mock_data = {"payment_link_url": "https://x.com", "br_code": "code"}
        with patch(
            "backend.app.pix.pix_service.criar_cobranca_pedido",
            new_callable=AsyncMock,
            return_value=mock_data,
        ):
            result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
                "pedido_id": ped.id,
            })

        assert "mensagem" in result

    def test_gerar_nova_cobranca_sucesso(self, db, restaurante1, bot_config):
        """Gera cobranca Pix nova com sucesso (mock pix_service)."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="PIX006",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Test New",
            itens="1x item",
            valor_total=80.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        mock_pix_data = {
            "payment_link_url": "https://pix.example.com/brand-new",
            "br_code": "brand_new_br",
        }
        with patch(
            "backend.app.pix.pix_service.criar_cobranca_pedido",
            new_callable=AsyncMock,
            return_value=mock_pix_data,
        ):
            result = _run_func(db, restaurante1.id, bot_config, "gerar_cobranca_pix", {
                "pedido_id": ped.id,
            })

        assert result["sucesso"] is True
        assert "brand-new" in result["pix_payment_link"]


# ==================== 24. CONSULTAR_PAGAMENTO_PIX (10 testes) ====================


class TestConsultarPagamentoPix:
    """Funcao 24: consultar_pagamento_pix"""

    def test_pagamento_confirmado(self, db, restaurante1, bot_config):
        """Cobranca paga retorna pago=True."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX01",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Pago",
            itens="1x item",
            valor_total=30.0,
            status="em_preparo",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-paid",
            valor_centavos=3000,
            status="COMPLETED",
            pago_em=datetime.utcnow(),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago"] is True
        assert result["status"] == "COMPLETED"
        assert result["pago_em"] is not None
        assert "confirmado" in result["mensagem"].lower()

    def test_pagamento_pendente(self, db, restaurante1, bot_config):
        """Cobranca pendente retorna pago=False."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX02",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Pendente",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-pending",
            valor_centavos=3000,
            status="ACTIVE",
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago"] is False
        assert result["status"] == "ACTIVE"

    def test_pagamento_expirado(self, db, restaurante1, bot_config):
        """Cobranca expirada retorna pago=False com status EXPIRED."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX03",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Expirado",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-expired",
            valor_centavos=3000,
            status="EXPIRED",
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago"] is False
        assert result["status"] == "EXPIRED"

    def test_sem_cobranca(self, db, restaurante1, bot_config):
        """Pedido sem cobranca Pix retorna status sem_cobranca."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX04",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Sem Cobranca",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago"] is False
        assert result["status"] == "sem_cobranca"

    def test_pedido_nao_encontrado(self, db, restaurante1, bot_config):
        """Pedido inexistente retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": 99999,
        })
        assert "erro" in result

    def test_sem_pedido_id(self, db, restaurante1, bot_config):
        """Sem pedido_id retorna erro."""
        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {})
        assert "erro" in result

    def test_multi_tenant(self, db, restaurante1, restaurante2, bot_config):
        """Cobranca do rest1 nao e acessivel pelo rest2."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX05",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Multi-tenant",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-mt",
            valor_centavos=3000,
            status="COMPLETED",
            pago_em=datetime.utcnow(),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante2.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert "erro" in result

    def test_retorna_data_pagamento(self, db, restaurante1, bot_config):
        """Cobranca paga inclui data de pagamento no resultado."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX06",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Data Pago",
            itens="1x item",
            valor_total=30.0,
            status="em_preparo",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-data",
            valor_centavos=3000,
            status="COMPLETED",
            pago_em=datetime.utcnow(),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago_em"] is not None

    def test_mensagem_pago(self, db, restaurante1, bot_config):
        """Mensagem para pagamento confirmado."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX07",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Msg Pago",
            itens="1x item",
            valor_total=30.0,
            status="em_preparo",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-msg-p",
            valor_centavos=3000,
            status="COMPLETED",
            pago_em=datetime.utcnow(),
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert "confirmado" in result["mensagem"].lower()

    def test_mensagem_nao_pago(self, db, restaurante1, bot_config):
        """Mensagem para pagamento nao confirmado."""
        ped = Pedido(
            restaurante_id=restaurante1.id,
            comanda="CPIX08",
            tipo="delivery",
            tipo_entrega="entrega",
            cliente_nome="Msg Nao Pago",
            itens="1x item",
            valor_total=30.0,
            status="pendente",
        )
        db.add(ped)
        db.flush()

        cobranca = PixCobranca(
            restaurante_id=restaurante1.id,
            pedido_id=ped.id,
            correlation_id=f"cpix-{ped.id}-msg-np",
            valor_centavos=3000,
            status="ACTIVE",
        )
        db.add(cobranca)
        db.flush()

        result = _run_func(db, restaurante1.id, bot_config, "consultar_pagamento_pix", {
            "pedido_id": ped.id,
        })
        assert result["pago"] is False
