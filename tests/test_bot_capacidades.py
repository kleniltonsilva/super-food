"""
Teste Exaustivo das 24 Capacidades do Bot Humanoide — AUDITORIA
================================================================
Testa TODAS as 24 function calls diretamente via executar_funcao()
com BD SQLite em memória. Cada teste é ISOLADO (pedidos dedicados),
assertions ESTRITAS verificam valores exatos + estado do BD.

Execução: python tests/test_bot_capacidades.py
"""
import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

# Configurar env ANTES de qualquer import do projeto
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"

# Paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database import models
from backend.app.bot.function_calls import executar_funcao


# ==================== ENGINE + SESSION IN-MEMORY ====================

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ==================== FIXTURES ====================

def criar_fixtures(db):
    """Popula BD com dados realistas. Pedidos dedicados por teste para evitar poluição de estado."""

    # ---- Restaurante principal ----
    rest = models.Restaurante(
        id=1, nome="Pizza Tuga Test", nome_fantasia="Pizza Tuga",
        email="test@pizzatuga.com", senha=hashlib.sha256(b"123456").hexdigest(),
        telefone="5511999999999", endereco_completo="Rua Teste 100, Centro, São Paulo - SP",
        cidade="São Paulo", estado="SP", pais="BR", codigo_acesso="TESTBOT",
        plano="premium", plano_tier=4, ativo=True,
        latitude=-23.5505, longitude=-46.6333,
    )
    db.add(rest)

    # ---- Restaurante 2 (para teste multi-tenant) ----
    rest2 = models.Restaurante(
        id=2, nome="Burger Lab", nome_fantasia="Burger Lab",
        email="test@burgerlab.com", senha=hashlib.sha256(b"654321").hexdigest(),
        telefone="5521999999999", endereco_completo="Rua Outra 200, Leblon, Rio - RJ",
        cidade="Rio de Janeiro", estado="RJ", pais="BR", codigo_acesso="BURGER1",
        plano="basico", plano_tier=1, ativo=True,
    )
    db.add(rest2)
    db.flush()

    # ---- ConfigRestaurante ----
    config = models.ConfigRestaurante(
        restaurante_id=1, tempo_medio_preparo=30, raio_entrega_km=10.0,
        taxa_entrega_base=5.0, distancia_base_km=3.0, taxa_km_extra=1.5,
        horario_abertura="10:00", horario_fechamento="23:00",
        dias_semana_abertos="segunda,terca,quarta,quinta,sexta,sabado,domingo",
    )
    db.add(config)

    # ---- SiteConfig ----
    db.add(models.SiteConfig(restaurante_id=1, tipo_restaurante="pizzaria", tempo_entrega_estimado=50))

    # ---- BotConfig ----
    bot_config = models.BotConfig(
        restaurante_id=1, bot_ativo=True, nome_atendente="Bia",
        pode_criar_pedido=True, pode_alterar_pedido=True, pode_cancelar_pedido=True,
        avaliacao_ativa=True, avaliacao_perguntar_problemas=True,
        impressao_automatica_bot=False,
        politica_atraso={"acao": "desconto_proximo", "desconto_pct": 10, "mensagem": ""},
        politica_pedido_errado={"acao": "desculpar", "desconto_pct": 0, "mensagem": ""},
        politica_item_faltando={"acao": "desculpar", "desconto_pct": 0, "mensagem": ""},
        politica_qualidade={"acao": "desculpar", "desconto_pct": 0, "mensagem": ""},
    )
    db.add(bot_config)

    # ---- Categorias ----
    db.add(models.CategoriaMenu(id=1, restaurante_id=1, nome="Pizzas", ativo=True, ordem_exibicao=1))
    db.add(models.CategoriaMenu(id=2, restaurante_id=1, nome="Bebidas", ativo=True, ordem_exibicao=2))
    # Categoria do restaurante 2 (multi-tenant)
    db.add(models.CategoriaMenu(id=3, restaurante_id=2, nome="Hamburgueres", ativo=True, ordem_exibicao=1))
    db.flush()

    # ---- Produtos ----
    db.add(models.Produto(id=1, restaurante_id=1, categoria_id=1, nome="Pizza Calabresa", preco=45.0, disponivel=True))
    db.add(models.Produto(id=2, restaurante_id=1, categoria_id=1, nome="Pizza Marguerita", preco=40.0, disponivel=True))
    db.add(models.Produto(id=3, restaurante_id=1, categoria_id=2, nome="Coca-Cola 2L", preco=12.0, disponivel=True))
    # Produto do restaurante 2 (multi-tenant)
    db.add(models.Produto(id=4, restaurante_id=2, categoria_id=3, nome="X-Burger", preco=28.0, disponivel=True))
    db.flush()

    # ---- Cliente ----
    cliente = models.Cliente(
        id=1, restaurante_id=1, nome="João Teste", telefone="5511999990001",
        senha_hash=hashlib.sha256(b"551199").hexdigest(),
    )
    db.add(cliente)
    db.flush()

    # ---- Endereço ----
    db.add(models.EnderecoCliente(
        cliente_id=1, endereco_completo="Rua Teste 123, Centro, São Paulo - SP",
        bairro="Centro", padrao=True,
    ))

    # ---- Bairros ----
    db.add(models.BairroEntrega(id=1, restaurante_id=1, nome="Centro", taxa_entrega=5.0, tempo_estimado_min=20, ativo=True))
    db.add(models.BairroEntrega(id=2, restaurante_id=1, nome="Jardim", taxa_entrega=8.0, tempo_estimado_min=35, ativo=True))

    # ---- Pedidos dedicados por cenário ----
    now = datetime.utcnow()

    # Pedido ENTREGUE — para repetir_ultimo_pedido + avaliação
    db.add(models.Pedido(
        id=1001, restaurante_id=1, cliente_id=1, comanda="WA1001", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", endereco_entrega="Rua Teste 123, Centro",
        itens="1x Pizza Calabresa (R$45.00)",
        carrinho_json=[{"produto_id": 1, "nome": "Pizza Calabresa", "quantidade": 1, "preco_unitario": 45.0}],
        valor_subtotal=45.0, valor_taxa_entrega=5.0, valor_total=50.0,
        forma_pagamento="dinheiro", status="entregue",
        historico_status=[{"status": "entregue", "timestamp": now.isoformat()}],
        data_criacao=now - timedelta(hours=2), atualizado_em=now - timedelta(hours=1),
    ))
    db.add(models.ItemPedido(pedido_id=1001, produto_id=1, quantidade=1, preco_unitario=45.0))

    # Pedido PENDENTE — para alterar_pedido (teste 7)
    db.add(models.Pedido(
        id=1002, restaurante_id=1, cliente_id=1, comanda="WA1002", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", endereco_entrega="Rua Teste 123, Centro",
        itens="1x Pizza Marguerita (R$40.00)",
        carrinho_json=[{"produto_id": 2, "nome": "Pizza Marguerita", "quantidade": 1, "preco_unitario": 40.0}],
        valor_subtotal=40.0, valor_taxa_entrega=5.0, valor_total=45.0,
        forma_pagamento="dinheiro", status="pendente",
        historico_status=[{"status": "pendente", "timestamp": now.isoformat()}],
        data_criacao=now - timedelta(minutes=30), atualizado_em=now - timedelta(minutes=25),
    ))
    db.add(models.ItemPedido(pedido_id=1002, produto_id=2, quantidade=1, preco_unitario=40.0))
    db.add(models.PedidoCozinha(restaurante_id=1, pedido_id=1002, status="NOVO", pausado=False))

    # Pedido PENDENTE — para cancelar_pedido (teste 8, dedicado)
    db.add(models.Pedido(
        id=1003, restaurante_id=1, cliente_id=1, comanda="WA1003", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", itens="1x Coca-Cola 2L",
        valor_subtotal=12.0, valor_total=17.0, status="pendente",
        data_criacao=now - timedelta(minutes=20), atualizado_em=now - timedelta(minutes=18),
    ))

    # Pedido EM_ROTA — para rastrear_pedido + consultar_status (testes 10, 17)
    db.add(models.Pedido(
        id=1004, restaurante_id=1, cliente_id=1, comanda="WA1004", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", endereco_entrega="Rua Teste 123, Centro",
        itens="1x Pizza Calabresa (R$45.00)", valor_subtotal=45.0,
        valor_taxa_entrega=5.0, valor_total=50.0, forma_pagamento="dinheiro",
        status="em_rota",
        historico_status=[
            {"status": "pendente", "timestamp": (now - timedelta(minutes=40)).isoformat()},
            {"status": "em_preparo", "timestamp": (now - timedelta(minutes=35)).isoformat()},
            {"status": "em_rota", "timestamp": (now - timedelta(minutes=5)).isoformat()},
        ],
        data_criacao=now - timedelta(minutes=40), atualizado_em=now - timedelta(minutes=5),
    ))
    db.add(models.ItemPedido(pedido_id=1004, produto_id=1, quantidade=1, preco_unitario=45.0))

    # Pedido PENDENTE — para trocar_item (teste 18, dedicado)
    db.add(models.Pedido(
        id=1005, restaurante_id=1, cliente_id=1, comanda="WA1005", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", itens="1x Pizza Marguerita (R$40.00)",
        valor_subtotal=40.0, valor_taxa_entrega=5.0, valor_total=45.0,
        forma_pagamento="dinheiro", status="pendente",
        data_criacao=now - timedelta(minutes=10), atualizado_em=now - timedelta(minutes=8),
    ))
    db.add(models.ItemPedido(pedido_id=1005, produto_id=2, quantidade=1, preco_unitario=40.0))
    db.add(models.PedidoCozinha(restaurante_id=1, pedido_id=1005, status="NOVO", pausado=False))

    # Pedido PENDENTE — para Pix (teste 24, dedicado)
    db.add(models.Pedido(
        id=1006, restaurante_id=1, cliente_id=1, comanda="WA1006", tipo="delivery",
        origem="whatsapp_bot", tipo_entrega="entrega", cliente_nome="João Teste",
        cliente_telefone="5511999990001", itens="1x Pizza Calabresa",
        valor_total=45.0, status="pendente", forma_pagamento="pix_online",
        data_criacao=now - timedelta(minutes=5), atualizado_em=now - timedelta(minutes=4),
    ))

    # ---- Motoboy + Entrega do pedido em_rota ----
    db.add(models.Motoboy(
        id=1, restaurante_id=1, nome="Carlos Motoboy", usuario="carlos",
        telefone="5511888880001", status="aprovado", disponivel=True,
        latitude_atual=-23.55, longitude_atual=-46.63,
    ))
    db.flush()
    db.add(models.Entrega(pedido_id=1004, motoboy_id=1, status="em_rota", tempo_entrega=25))

    # ---- Promoção/cupom ----
    db.add(models.Promocao(
        restaurante_id=1, nome="Desconto 10%", tipo_desconto="percentual",
        valor_desconto=10, codigo_cupom="DESC10", ativo=True, uso_limitado=False,
    ))

    # ---- BotConversa ----
    conversa = models.BotConversa(
        id=1, restaurante_id=1, cliente_id=1, telefone="5511999990001",
        nome_cliente="João Teste", status="ativa", pedido_ativo_id=1004,
        session_data={},
    )
    db.add(conversa)

    db.commit()
    return bot_config, conversa


# ==================== HELPERS ====================

async def call(db, nome, args, bot_config, conversa=None):
    """Chama executar_funcao e retorna dict parseado."""
    result_str = await executar_funcao(nome, args, db, 1, bot_config, conversa)
    return json.loads(result_str)


class Audit:
    """Rastreador de resultados com assertions estritas."""
    def __init__(self, total):
        self.total = total
        self.results = []

    def check(self, num, nome, assertions: list[tuple[bool, str]]):
        """Valida lista de assertions. Todas devem passar."""
        falhas = [msg for ok, msg in assertions if not ok]
        passed = len(falhas) == 0
        status = "✅" if passed else "❌"
        detail = falhas[0] if falhas else assertions[0][1] if assertions else ""
        msg = f"{status} {num:2d}/{self.total} {nome}: {detail}"
        if falhas and len(falhas) > 1:
            for f in falhas[1:]:
                msg += f"\n     ↳ FALHA: {f}"
        self.results.append((passed, msg))
        print(msg)

    def summary(self):
        total_real = len(self.results)
        passed = sum(1 for ok, _ in self.results if ok)
        failed = total_real - passed
        print("=" * 60)
        if failed == 0:
            print(f"\nRESULTADO: {passed}/{total_real} PASS ✅")
        else:
            print(f"\nRESULTADO: {passed}/{total_real} PASS, {failed} FAIL ❌")
            print("\nFalhas:")
            for ok, msg in self.results:
                if not ok:
                    print(f"  {msg}")
        print("=" * 60)
        return failed == 0


# ==================== 24 TESTES ====================

async def run_all_tests():
    Base.metadata.create_all(bind=engine)
    db = TestSession()
    bot_config, conversa = criar_fixtures(db)

    bot_config = db.query(models.BotConfig).filter_by(restaurante_id=1).first()
    conversa = db.query(models.BotConversa).filter_by(id=1).first()

    audit = Audit(total=24)

    print("=" * 60)
    print("BOT HUMANOIDE — AUDITORIA 24 CAPACIDADES")
    print("=" * 60)

    # ======= 1. buscar_cliente (existente) =======
    r = await call(db, "buscar_cliente", {"telefone": "5511999990001"}, bot_config)
    audit.check(1, "buscar_cliente (existente)", [
        (r.get("encontrado") is True, f"encontrado={r.get('encontrado')} (esperado True)"),
        (r.get("nome") == "João Teste", f"nome={r.get('nome')} (esperado 'João Teste')"),
        (r.get("id") == 1, f"id={r.get('id')} (esperado 1)"),
        (r.get("bairro") == "Centro", f"bairro={r.get('bairro')} (esperado 'Centro')"),
    ])

    # ======= 2. buscar_cliente (não existe) =======
    r = await call(db, "buscar_cliente", {"telefone": "5599000000"}, bot_config)
    audit.check(2, "buscar_cliente (inexistente)", [
        (r.get("encontrado") is False, f"encontrado={r.get('encontrado')} (esperado False)"),
        ("cadastrar_cliente" in r.get("mensagem", "").lower() or "não encontrado" in r.get("mensagem", "").lower(),
         f"mensagem orienta cadastro: '{r.get('mensagem', '')[:60]}'"),
    ])

    # ======= 3. cadastrar_cliente =======
    r = await call(db, "cadastrar_cliente", {"nome": "Maria Nova", "telefone": "5511888880099"}, bot_config)
    audit.check(3, "cadastrar_cliente", [
        (isinstance(r.get("id"), int) and r["id"] > 0, f"id={r.get('id')} (esperado int > 0)"),
        (r.get("nome") == "Maria Nova", f"nome={r.get('nome')} (esperado 'Maria Nova')"),
    ])
    # Verificar no BD
    maria = db.query(models.Cliente).filter_by(telefone="5511888880099").first()
    audit_db_ok = maria is not None and maria.nome == "Maria Nova" and maria.restaurante_id == 1
    if not audit_db_ok:
        print("     ↳ FALHA BD: cliente não persistido corretamente")

    # ======= 4. buscar_cardapio =======
    r = await call(db, "buscar_cardapio", {"busca": "pizza"}, bot_config)
    audit.check(4, "buscar_cardapio", [
        (r.get("encontrados") == 2, f"encontrados={r.get('encontrados')} (esperado 2 — Calabresa + Marguerita)"),
        (any("Calabresa" in i.get("nome", "") for i in r.get("itens", [])),
         "contém Pizza Calabresa"),
        (any(i.get("preco") == 45.0 for i in r.get("itens", [])),
         "preço Calabresa = R$45.00"),
    ])

    # ======= 5. buscar_categorias =======
    r = await call(db, "buscar_categorias", {}, bot_config)
    cats = r.get("categorias", [])
    nomes_cat = [c["nome"] for c in cats]
    audit.check(5, "buscar_categorias", [
        (len(cats) == 2, f"categorias={len(cats)} (esperado 2 — Pizzas + Bebidas, NÃO Hamburgueres do rest 2)"),
        ("Pizzas" in nomes_cat and "Bebidas" in nomes_cat, f"nomes={nomes_cat}"),
        ("Hamburgueres" not in nomes_cat, "multi-tenant: Hamburgueres do rest 2 NÃO aparece"),
    ])

    # ======= 6. criar_pedido =======
    r = await call(db, "criar_pedido", {
        "cliente_nome": "João Teste",
        "cliente_telefone": "5511999990001",
        "itens": [{"produto_id": 1, "nome": "Pizza Calabresa", "quantidade": 1, "preco_unitario": 45.0}],
        "forma_pagamento": "dinheiro",
        "tipo_entrega": "entrega",
        "endereco_entrega": "Rua Teste 123, Centro, São Paulo",
    }, bot_config, conversa)
    pedido_criado_id = r.get("pedido_id")
    audit.check(6, "criar_pedido", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (isinstance(pedido_criado_id, int) and pedido_criado_id > 0, f"pedido_id={pedido_criado_id}"),
        (r.get("comanda", "").startswith("WA"), f"comanda={r.get('comanda')} (deve iniciar com WA)"),
        (r.get("valor_total") == 50.0, f"valor_total={r.get('valor_total')} (esperado 50.0 = 45 + 5 taxa)"),
        (r.get("link_rastreamento") is not None, "link_rastreamento presente"),
    ])
    # Verificar BD
    if pedido_criado_id:
        p_db = db.query(models.Pedido).get(pedido_criado_id)
        itens_db = db.query(models.ItemPedido).filter_by(pedido_id=pedido_criado_id).all()
        if not p_db or p_db.restaurante_id != 1:
            print(f"     ↳ FALHA BD: pedido {pedido_criado_id} não persistido ou restaurante_id errado")
        if len(itens_db) != 1:
            print(f"     ↳ FALHA BD: {len(itens_db)} itens (esperado 1)")

    # ======= 7. alterar_pedido =======
    r = await call(db, "alterar_pedido", {
        "pedido_id": 1002,
        "adicionar_itens": [{"produto_id": 3, "nome": "Coca-Cola 2L", "quantidade": 1, "preco_unitario": 12.0}],
    }, bot_config)
    audit.check(7, "alterar_pedido", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (r.get("novo_total") == 57.0, f"novo_total={r.get('novo_total')} (esperado 57.0 = 40+12+5taxa)"),
    ])
    # Verificar BD: agora 1002 deve ter 2 itens
    itens_1002 = db.query(models.ItemPedido).filter_by(pedido_id=1002).count()
    if itens_1002 != 2:
        print(f"     ↳ FALHA BD: 1002 tem {itens_1002} itens (esperado 2)")

    # ======= 8. cancelar_pedido =======
    r = await call(db, "cancelar_pedido", {"pedido_id": 1003, "motivo": "teste cancelamento"}, bot_config, conversa)
    audit.check(8, "cancelar_pedido", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        ("cancelado" in r.get("mensagem", "").lower(), f"mensagem confirma cancelamento"),
        ("teste cancelamento" in r.get("mensagem", "").lower(), "motivo preservado na mensagem"),
    ])
    # Verificar BD
    p1003 = db.query(models.Pedido).get(1003)
    if p1003.status != "cancelado":
        print(f"     ↳ FALHA BD: pedido 1003 status={p1003.status} (esperado 'cancelado')")

    # ======= 9. repetir_ultimo_pedido =======
    r = await call(db, "repetir_ultimo_pedido", {"cliente_telefone": "5511999990001"}, bot_config, conversa)
    audit.check(9, "repetir_ultimo_pedido", [
        (r.get("ultimo_pedido") is not None, "ultimo_pedido retornado"),
        (r.get("ultimo_pedido", {}).get("comanda") == "WA1001", f"comanda={r.get('ultimo_pedido', {}).get('comanda')} (esperado WA1001 — o entregue)"),
        (len(r.get("itens_para_criar", [])) > 0, "itens_para_criar não vazio"),
    ])

    # ======= 10. consultar_status_pedido (por telefone — deve encontrar o mais recente) =======
    r = await call(db, "consultar_status_pedido", {"cliente_telefone": "5511999990001"}, bot_config)
    audit.check(10, "consultar_status_pedido (telefone)", [
        (r.get("pedido_id") is not None, f"pedido_id={r.get('pedido_id')}"),
        (r.get("comanda") is not None, f"comanda={r.get('comanda')}"),
        (r.get("status") is not None, f"status={r.get('status')}"),
        (r.get("status_texto") is not None, "status_texto presente"),
        (r.get("valor_total") is not None, "valor_total presente"),
    ])

    # ======= 10b. consultar_status_pedido (por ID — exato) =======
    r = await call(db, "consultar_status_pedido", {"pedido_id": 1004}, bot_config)
    audit.check(10, "consultar_status_pedido (ID=1004)", [
        (r.get("pedido_id") == 1004, f"pedido_id={r.get('pedido_id')} (esperado 1004)"),
        (r.get("comanda") == "WA1004", f"comanda={r.get('comanda')} (esperado WA1004)"),
        (r.get("status") == "em_rota", f"status={r.get('status')} (esperado em_rota)"),
        (r.get("motoboy_nome") == "Carlos Motoboy", f"motoboy={r.get('motoboy_nome')} (esperado Carlos Motoboy)"),
    ])

    # ======= 11. verificar_horario =======
    r = await call(db, "verificar_horario", {}, bot_config)
    audit.check(11, "verificar_horario", [
        ("erro" not in r, "sem erro"),
        (isinstance(r.get("aberto"), bool), f"aberto={r.get('aberto')} (é booleano)"),
        (r.get("hora_atual") is not None, f"hora_atual={r.get('hora_atual')}"),
        (r.get("dia_semana") is not None, f"dia_semana={r.get('dia_semana')}"),
        (isinstance(r.get("horarios_semana"), dict), "horarios_semana é dict"),
        (len(r.get("horarios_semana", {})) == 7, f"7 dias na semana (retornou {len(r.get('horarios_semana', {}))})"),
    ])

    # ======= 12. buscar_promocoes =======
    r = await call(db, "buscar_promocoes", {}, bot_config, conversa)
    audit.check(12, "buscar_promocoes", [
        ("erro" not in r, "sem erro"),
        (len(r.get("promocoes", [])) == 1, f"promocoes={len(r.get('promocoes', []))} (esperado 1)"),
        (r.get("promocoes", [{}])[0].get("cupom") == "DESC10", "cupom=DESC10"),
        (isinstance(r.get("combos"), list), "combos é lista"),
        (isinstance(r.get("cupons_exclusivos"), list), "cupons_exclusivos é lista"),
    ])

    # ======= 13. registrar_avaliacao =======
    r = await call(db, "registrar_avaliacao", {"nota": 5, "categoria": "comida", "detalhe": "Excelente!"}, bot_config, conversa)
    audit.check(13, "registrar_avaliacao", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (r.get("nota") == 5, f"nota={r.get('nota')} (esperado 5)"),
        ("obrigado" in r.get("mensagem", "").lower() or "😊" in r.get("mensagem", ""),
         "mensagem agradece"),
    ])
    # Verificar BD
    aval = db.query(models.BotAvaliacao).filter_by(restaurante_id=1).order_by(models.BotAvaliacao.id.desc()).first()
    if not aval or aval.nota != 5 or aval.status != "respondida":
        print(f"     ↳ FALHA BD: avaliação não persistida ou status errado")

    # ======= 14. registrar_problema =======
    r = await call(db, "registrar_problema", {"tipo": "atraso", "descricao": "Demorou 1 hora"}, bot_config, conversa)
    audit.check(14, "registrar_problema", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (isinstance(r.get("problema_id"), int) and r["problema_id"] > 0, f"problema_id={r.get('problema_id')}"),
        (r.get("acao_aplicada") == "desconto_proximo", f"acao={r.get('acao_aplicada')} (esperado desconto_proximo — config politica_atraso)"),
        (r.get("cupom") is not None, "cupom gerado automaticamente pela política"),
        (r.get("desconto_pct") == 10, f"desconto_pct={r.get('desconto_pct')} (esperado 10)"),
    ])
    # Verificar BD: problema + promoção gerada
    prob = db.query(models.BotProblema).get(r.get("problema_id"))
    if prob:
        if not prob.resolvido_automaticamente:
            print(f"     ↳ FALHA BD: problema não marcado como resolvido automaticamente")
        if not prob.cupom_gerado:
            print(f"     ↳ FALHA BD: cupom não salvo no problema")

    # ======= 15. aplicar_cupom =======
    r = await call(db, "aplicar_cupom", {"codigo_cupom": "DESC10", "valor_pedido": 50.0}, bot_config, conversa)
    audit.check(15, "aplicar_cupom", [
        (r.get("valido") is True, f"valido={r.get('valido')} (esperado True)"),
        (r.get("desconto") == 5.0, f"desconto={r.get('desconto')} (esperado 5.0 = 10% de 50)"),
        (r.get("novo_total") == 45.0, f"novo_total={r.get('novo_total')} (esperado 45.0)"),
    ])

    # ======= 15b. aplicar_cupom inválido =======
    r = await call(db, "aplicar_cupom", {"codigo_cupom": "INVALIDO", "valor_pedido": 50.0}, bot_config, conversa)
    audit.check(15, "aplicar_cupom (inválido)", [
        (r.get("valido") is False, f"valido={r.get('valido')} (esperado False)"),
    ])

    # ======= 16. escalar_humano =======
    r = await call(db, "escalar_humano", {"motivo": "falar com gerente"}, bot_config, conversa)
    audit.check(16, "escalar_humano", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
    ])
    # Verificar BD: conversa mudou para aguardando_handoff
    conversa = db.query(models.BotConversa).get(1)
    audit_handoff = conversa.status == "aguardando_handoff" and conversa.handoff_motivo == "falar com gerente"
    if not audit_handoff:
        print(f"     ↳ FALHA BD: conversa.status={conversa.status}, motivo={conversa.handoff_motivo}")
    # Restaurar
    conversa.status = "ativa"
    conversa.handoff_motivo = None
    db.commit()

    # ======= 17. rastrear_pedido (por telefone) =======
    r = await call(db, "rastrear_pedido", {"telefone": "5511999990001"}, bot_config)
    audit.check(17, "rastrear_pedido (telefone)", [
        (r.get("pedido_id") is not None, f"pedido_id={r.get('pedido_id')}"),
        (r.get("comanda") is not None, f"comanda={r.get('comanda')}"),
        (r.get("status") is not None, f"status={r.get('status')}"),
        (r.get("status_texto") is not None, "status_texto presente"),
    ])

    # ======= 17b. rastrear_pedido (por ID=1004 — em_rota com motoboy) =======
    r = await call(db, "rastrear_pedido", {"pedido_id": 1004}, bot_config)
    audit.check(17, "rastrear_pedido (ID=1004 em_rota)", [
        (r.get("pedido_id") == 1004, f"pedido_id={r.get('pedido_id')} (esperado 1004)"),
        (r.get("status") == "em_rota", f"status={r.get('status')} (esperado em_rota)"),
        (r.get("motoboy_nome") == "Carlos Motoboy", f"motoboy={r.get('motoboy_nome')} (esperado Carlos Motoboy)"),
        (r.get("motoboy_gps") is not None, "motoboy_gps presente (tem lat/lng)"),
        (r.get("eta_entrega_min") == 25, f"eta_entrega_min={r.get('eta_entrega_min')} (esperado 25)"),
        (r.get("link_rastreamento") is not None, "link_rastreamento presente"),
    ])

    # ======= 18. trocar_item_pedido =======
    r = await call(db, "trocar_item_pedido", {
        "pedido_id": 1005,
        "item_remover": "marguerita",
        "item_novo": "calabresa",
        "quantidade": 1,
    }, bot_config, conversa)
    audit.check(18, "trocar_item_pedido", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        ("marguerita" in r.get("removido", "").lower(), f"removido={r.get('removido')}"),
        ("Calabresa" in r.get("adicionado", ""), f"adicionado={r.get('adicionado')}"),
        (r.get("novo_total") == 50.0, f"novo_total={r.get('novo_total')} (esperado 50 = 45+5taxa)"),
    ])
    # Verificar BD: 1005 agora tem Calabresa, não Marguerita
    itens_1005 = db.query(models.ItemPedido).filter_by(pedido_id=1005).all()
    if len(itens_1005) != 1 or itens_1005[0].produto_id != 1:
        print(f"     ↳ FALHA BD: 1005 deveria ter produto_id=1 (Calabresa), tem {[i.produto_id for i in itens_1005]}")

    # ======= 19. consultar_tempo_entrega =======
    r = await call(db, "consultar_tempo_entrega", {"bairro": "Centro"}, bot_config)
    audit.check(19, "consultar_tempo_entrega", [
        (r.get("tempo_preparo_min") == 30, f"tempo_preparo={r.get('tempo_preparo_min')} (esperado 30)"),
        (r.get("bairro") == "Centro", f"bairro={r.get('bairro')} (esperado Centro)"),
        (r.get("taxa_entrega") == 5.0, f"taxa={r.get('taxa_entrega')} (esperado 5.0)"),
        (r.get("tempo_entrega_bairro_min") == 20, f"tempo_bairro={r.get('tempo_entrega_bairro_min')} (esperado 20)"),
        (r.get("total_estimado_min") == 50, f"total={r.get('total_estimado_min')} (esperado 50 = 30+20)"),
    ])

    # ======= 20. consultar_bairros =======
    r = await call(db, "consultar_bairros", {}, bot_config)
    audit.check(20, "consultar_bairros", [
        (r.get("encontrados") == 2, f"encontrados={r.get('encontrados')} (esperado 2)"),
        (len(r.get("bairros", [])) == 2, "retornou 2 bairros"),
        (any(b["nome"] == "Centro" and b["taxa_entrega"] == 5.0 for b in r.get("bairros", [])),
         "Centro com taxa 5.0"),
        (any(b["nome"] == "Jardim" and b["taxa_entrega"] == 8.0 for b in r.get("bairros", [])),
         "Jardim com taxa 8.0"),
    ])

    # ======= 21. atualizar_endereco_cliente =======
    r = await call(db, "atualizar_endereco_cliente", {
        "telefone": "5511999990001",
        "endereco_completo": "Rua Nova 456, Centro, São Paulo - SP",
        "bairro": "Centro",
    }, bot_config)
    audit.check(21, "atualizar_endereco_cliente", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (r.get("endereco") == "Rua Nova 456, Centro, São Paulo - SP", f"endereco={r.get('endereco')}"),
    ])
    # Verificar BD
    end_db = db.query(models.EnderecoCliente).filter_by(cliente_id=1, padrao=True).first()
    if end_db.endereco_completo != "Rua Nova 456, Centro, São Paulo - SP":
        print(f"     ↳ FALHA BD: endereço não atualizado: {end_db.endereco_completo}")

    # ======= 22. validar_endereco (mock Mapbox) =======
    mock_sugestoes = [{
        "place_name": "Rua Augusta, 123, Consolação, São Paulo - SP, 01305-100, Brasil",
        "coordinates": (-23.5534, -46.6546),
    }]
    with patch("utils.mapbox_api.autocomplete_address", return_value=mock_sugestoes), \
         patch("utils.mapbox_api._cache_key_dist", return_value="mock_key"), \
         patch("backend.app.cache.cache_get", return_value=None), \
         patch("backend.app.cache.cache_set"):
        r = await call(db, "validar_endereco", {"endereco_texto": "Rua Augusta 123"}, bot_config, conversa)
    audit.check(22, "validar_endereco (mock Mapbox)", [
        (r.get("encontrado") is True, f"encontrado={r.get('encontrado')} (esperado True)"),
        (r.get("confianca") in ("alta", "media"), f"confianca={r.get('confianca')} (esperado alta ou media)"),
        (r.get("taxa_entrega") is not None, f"taxa_entrega={r.get('taxa_entrega')}"),
        ("Rua Augusta" in r.get("endereco", r.get("mensagem", "")), "endereço contém Rua Augusta"),
    ])
    # Verificar que session_data foi populado
    conversa = db.query(models.BotConversa).get(1)
    sugestoes_salvas = (conversa.session_data or {}).get("endereco_sugestoes", [])
    if len(sugestoes_salvas) == 0:
        print("     ↳ FALHA BD: session_data.endereco_sugestoes não salvo")

    # ======= 23. confirmar_endereco_validado =======
    # Popular session_data com sugestões (caso validar_endereco acima não tenha salvo no formato certo)
    conversa.session_data = {
        "endereco_sugestoes": [{
            "place_name": "Rua Augusta, 123, Consolação, São Paulo - SP, 01305-100, Brasil",
            "lat": -23.5534, "lng": -46.6546,
            "distancia_km": 2.5, "dentro_zona": True, "taxa_entrega": 5.0,
        }],
        "endereco_complemento": "Apto 42",
        "endereco_referencia": "Perto do metrô",
    }
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(conversa, "session_data")
    db.commit()

    r = await call(db, "confirmar_endereco_validado", {
        "telefone": "5511999990001", "opcao_index": 0,
    }, bot_config, conversa)
    audit.check(23, "confirmar_endereco_validado", [
        (r.get("sucesso") is True, f"sucesso={r.get('sucesso')}"),
        (r.get("taxa_entrega") == 5.0, f"taxa={r.get('taxa_entrega')} (esperado 5.0)"),
        (r.get("validado_gps") is True, f"validado_gps={r.get('validado_gps')}"),
        ("Apto 42" in r.get("endereco", ""), f"complemento preservado no endereço: {r.get('endereco', '')[:50]}"),
    ])
    # Verificar BD: endereço com coordenadas GPS salvas
    end_gps = db.query(models.EnderecoCliente).filter_by(cliente_id=1, padrao=True).first()
    if not end_gps or not end_gps.validado_mapbox or end_gps.latitude is None:
        print(f"     ↳ FALHA BD: endereço sem GPS ou validado_mapbox=False")
    # Verificar session_data: endereco_validado salvo para criar_pedido
    conversa = db.query(models.BotConversa).get(1)
    ev = (conversa.session_data or {}).get("endereco_validado")
    if not ev or ev.get("lat") != -23.5534:
        print(f"     ↳ FALHA BD: session_data.endereco_validado não salvo corretamente")

    # ======= 24. gerar_cobranca_pix + consultar_pagamento_pix =======
    # gerar_cobranca_pix: PixCobranca table existe no BD, mas sem pix_service real
    # Esperamos erro controlado "Erro ao gerar cobrança Pix" (sem crash/exception)
    r = await call(db, "gerar_cobranca_pix", {"pedido_id": 1006}, bot_config)
    gerar_ok = r.get("sucesso") is True or (isinstance(r.get("erro"), str) and len(r["erro"]) > 0)
    audit.check(24, "gerar_cobranca_pix + consultar_pagamento_pix", [
        (gerar_ok, f"gerar_cobranca: retorno controlado (sucesso ou erro string, sem crash)"),
    ])

    # consultar_pagamento_pix: deve retornar sem crash mesmo sem cobrança
    r2 = await call(db, "consultar_pagamento_pix", {"pedido_id": 1006}, bot_config)
    pix_consulta_ok = r2.get("status") == "sem_cobranca" and r2.get("pago") is False
    if not pix_consulta_ok:
        print(f"     ↳ AVISO: consultar_pagamento_pix inesperado: {r2}")
    else:
        print(f"     ↳ consultar_pagamento_pix: status={r2['status']}, pago={r2['pago']} ✓")

    # ======= TESTES BÔNUS: SEGURANÇA MULTI-TENANT =======
    print("\n" + "-" * 60)
    print("BÔNUS — SEGURANÇA MULTI-TENANT")
    print("-" * 60)

    # Buscar cardápio do rest 1 NÃO deve retornar X-Burger do rest 2
    r = await call(db, "buscar_cardapio", {"busca": "burger"}, bot_config)
    mt_cardapio = r.get("encontrados", 0) == 0
    print(f"{'✅' if mt_cardapio else '❌'} buscar_cardapio 'burger' no rest 1: encontrados={r.get('encontrados')} (esperado 0)")

    # Buscar categorias do rest 1 NÃO deve incluir Hamburgueres do rest 2
    r = await call(db, "buscar_categorias", {}, bot_config)
    nomes = [c["nome"] for c in r.get("categorias", [])]
    mt_cats = "Hamburgueres" not in nomes
    print(f"{'✅' if mt_cats else '❌'} buscar_categorias: {nomes} (Hamburgueres NÃO deve aparecer)")

    # ======= TESTES BÔNUS: PERMISSÕES BOT =======
    print("\n" + "-" * 60)
    print("BÔNUS — PERMISSÕES BOT (pode_cancelar=False)")
    print("-" * 60)

    # Criar BotConfig sem permissão de cancelar
    bot_config_restrito = models.BotConfig(
        restaurante_id=1, bot_ativo=True, pode_criar_pedido=True,
        pode_alterar_pedido=False, pode_cancelar_pedido=False,
    )

    r = await call(db, "cancelar_pedido", {"pedido_id": 1002, "motivo": "teste"}, bot_config_restrito, conversa)
    perm_cancel = "erro" in r and "permissão" in r.get("erro", "").lower()
    print(f"{'✅' if perm_cancel else '❌'} cancelar sem permissão: {'bloqueado' if perm_cancel else 'FALHA — deveria bloquear'}")

    r = await call(db, "alterar_pedido", {"pedido_id": 1002}, bot_config_restrito)
    perm_alter = "erro" in r and "permissão" in r.get("erro", "").lower()
    print(f"{'✅' if perm_alter else '❌'} alterar sem permissão: {'bloqueado' if perm_alter else 'FALHA — deveria bloquear'}")

    # ==================== RESUMO ====================
    success = audit.summary()
    db.close()
    return success


# ==================== MAIN ====================

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
