"""
Teste de Estresse — 100 Conversas Simuladas do Bot Humanoide
=============================================================
Simula 100 clientes fictícios interagindo com o bot do restaurante Pizza Tuga.
Cada conversa segue um fluxo realista (pedido, rastreamento, avaliação, etc.).
Testa as 22 capacidades em cenários variados e reporta resultados.

Execução: python tests/test_bot_100_conversas.py
"""
import asyncio
import hashlib
import json
import os
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key"

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database.base import Base
from database import models
from backend.app.bot.function_calls import executar_funcao


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# ==================== DADOS FICTÍCIOS ====================

NOMES = [
    "Ana Silva", "Bruno Costa", "Carla Mendes", "Diego Rocha", "Elena Souza",
    "Felipe Oliveira", "Gabi Santos", "Hugo Lima", "Isabela Ferreira", "João Alves",
    "Karen Martins", "Lucas Pereira", "Maria Rodrigues", "Nelson Barbosa", "Olívia Cardoso",
    "Pedro Gomes", "Quésia Nunes", "Rafael Dias", "Sara Monteiro", "Thiago Araújo",
    "Úrsula Pinto", "Victor Cunha", "Wanda Teixeira", "Xande Moreira", "Yara Nascimento",
    "Zeca Ribeiro", "Adriana Campos", "Bernardo Vieira", "Camila Freitas", "Daniel Correia",
    "Eduarda Ramos", "Fábio Lopes", "Gisele Borges", "Heitor Nogueira", "Inês Carvalho",
    "Juliana Azevedo", "Kaio Machado", "Larissa Melo", "Marcos Fontes", "Natália Castro",
    "Oscar Bezerra", "Patrícia Duarte", "Quirino Fonseca", "Renata Guedes", "Samuel Brito",
    "Tatiana Moura", "Ulisses Tavares", "Vitória Prado", "Wagner Siqueira", "Xuxa Miranda",
    "Alice Baptista", "Bento Magalhães", "Cíntia Andrade", "Dante Vasconcelos", "Eva Soares",
    "Flávio Rezende", "Graça Sampaio", "Humberto Alencar", "Irina Valente", "Josué Barreto",
    "Kátia Bonfim", "Leandro Quiroz", "Melissa Dantas", "Norberto Espíndola", "Otávia Serra",
    "Paulo Henrique", "Rosa Amaral", "Silvio Leal", "Teresa Braga", "Ubiratan Franco",
    "Valéria Pires", "Wesley Montes", "Yago Coelho", "Zilda Pacheco", "Amanda Figueiredo",
    "Braz Lourenço", "Célia Medeiros", "Davi Saldanha", "Elaine Xavier", "Fernando Assis",
    "Glória Padilha", "Henrique Uchôa", "Ivone Mota", "Jéssica Toledo", "Kleber Rangel",
    "Luana Afonso", "Márcio Galvão", "Nara Bueno", "Otávio Rabelo", "Priscila Veloso",
    "Quirino Neto", "Regiane Coutinho", "Sérgio Bastos", "Tereza Dornelles", "Umberto Paz",
    "Viviane Lago", "Wendel Cabral", "Yolanda Paiva", "Zenon Esteves", "Aparecida Fontoura",
]

BAIRROS = ["Centro", "Jardim", "Vila Nova", "Liberdade", "Consolação"]
PROBLEMAS_TIPO = ["atraso", "item_errado", "item_faltando", "qualidade", "outro"]
FORMAS_PAGAMENTO = ["dinheiro", "cartao", "pix", "vale_refeicao"]

# Fluxos possíveis para cada conversa
FLUXOS = [
    "novo_cliente_pedido",       # buscar(404) → cadastrar → cardápio → criar_pedido
    "cliente_repete",            # buscar(200) → repetir_ultimo
    "cliente_rastreia",          # buscar(200) → consultar_status → rastrear
    "cliente_cancela",           # buscar(200) → cancelar_pedido
    "cliente_altera",            # buscar(200) → alterar_pedido
    "cliente_troca_item",        # buscar(200) → trocar_item
    "cliente_avalia",            # buscar(200) → registrar_avaliacao
    "cliente_reclama",           # buscar(200) → registrar_problema
    "cliente_usa_cupom",         # buscar(200) → aplicar_cupom → criar_pedido
    "cliente_pergunta_info",     # verificar_horario → buscar_categorias → consultar_bairros → tempo_entrega
    "cliente_atualiza_endereco", # buscar(200) → atualizar_endereco
    "cliente_escala_humano",     # buscar(200) → escalar_humano
    "cliente_valida_endereco",   # buscar(200) → validar_endereco → confirmar_endereco
    "cliente_pedido_retirada",   # buscar(200) → cardápio → criar_pedido (retirada)
    "cliente_busca_promos",      # buscar(200) → buscar_promocoes
]


# ==================== SETUP ====================

def criar_base(db):
    """Cria restaurante, config, produtos, bairros, promoção."""
    now = datetime.utcnow()

    rest = models.Restaurante(
        id=1, nome="Pizza Tuga Test", nome_fantasia="Pizza Tuga",
        email="test@pizzatuga.com", senha=hashlib.sha256(b"123456").hexdigest(),
        telefone="5511999999999", endereco_completo="Rua Teste 100, Centro, São Paulo - SP",
        cidade="São Paulo", estado="SP", pais="BR", codigo_acesso="TESTBOT",
        plano="premium", plano_tier=4, ativo=True,
        latitude=-23.5505, longitude=-46.6333,
    )
    db.add(rest)
    db.flush()

    db.add(models.ConfigRestaurante(
        restaurante_id=1, tempo_medio_preparo=30, raio_entrega_km=10.0,
        taxa_entrega_base=5.0, distancia_base_km=3.0, taxa_km_extra=1.5,
        horario_abertura="10:00", horario_fechamento="23:00",
        dias_semana_abertos="segunda,terca,quarta,quinta,sexta,sabado,domingo",
    ))
    db.add(models.SiteConfig(restaurante_id=1, tipo_restaurante="pizzaria", tempo_entrega_estimado=50))

    bot_config = models.BotConfig(
        restaurante_id=1, bot_ativo=True, nome_atendente="Bia",
        pode_criar_pedido=True, pode_alterar_pedido=True, pode_cancelar_pedido=True,
        avaliacao_ativa=True, avaliacao_perguntar_problemas=True,
        impressao_automatica_bot=False,
        politica_atraso={"acao": "desconto_proximo", "desconto_pct": 10, "mensagem": ""},
        politica_pedido_errado={"acao": "brinde_reenviar", "desconto_pct": 0, "mensagem": ""},
        politica_item_faltando={"acao": "desculpar", "desconto_pct": 0, "mensagem": ""},
        politica_qualidade={"acao": "desculpar", "desconto_pct": 0, "mensagem": ""},
    )
    db.add(bot_config)

    # Categorias
    db.add(models.CategoriaMenu(id=1, restaurante_id=1, nome="Pizzas", ativo=True, ordem_exibicao=1))
    db.add(models.CategoriaMenu(id=2, restaurante_id=1, nome="Bebidas", ativo=True, ordem_exibicao=2))
    db.add(models.CategoriaMenu(id=3, restaurante_id=1, nome="Sobremesas", ativo=True, ordem_exibicao=3))
    db.flush()

    # Produtos (8 itens variados)
    produtos = [
        models.Produto(id=1, restaurante_id=1, categoria_id=1, nome="Pizza Calabresa", preco=45.0, disponivel=True),
        models.Produto(id=2, restaurante_id=1, categoria_id=1, nome="Pizza Marguerita", preco=40.0, disponivel=True),
        models.Produto(id=3, restaurante_id=1, categoria_id=1, nome="Pizza Portuguesa", preco=48.0, disponivel=True),
        models.Produto(id=4, restaurante_id=1, categoria_id=1, nome="Pizza Frango Catupiry", preco=42.0, disponivel=True),
        models.Produto(id=5, restaurante_id=1, categoria_id=2, nome="Coca-Cola 2L", preco=12.0, disponivel=True),
        models.Produto(id=6, restaurante_id=1, categoria_id=2, nome="Guaraná Antárctica 2L", preco=10.0, disponivel=True),
        models.Produto(id=7, restaurante_id=1, categoria_id=3, nome="Pudim", preco=8.0, disponivel=True),
        models.Produto(id=8, restaurante_id=1, categoria_id=3, nome="Petit Gâteau", preco=15.0, disponivel=True),
    ]
    db.add_all(produtos)
    db.flush()

    # Bairros
    bairros_db = [
        models.BairroEntrega(id=1, restaurante_id=1, nome="Centro", taxa_entrega=5.0, tempo_estimado_min=20, ativo=True),
        models.BairroEntrega(id=2, restaurante_id=1, nome="Jardim", taxa_entrega=8.0, tempo_estimado_min=35, ativo=True),
        models.BairroEntrega(id=3, restaurante_id=1, nome="Vila Nova", taxa_entrega=7.0, tempo_estimado_min=30, ativo=True),
        models.BairroEntrega(id=4, restaurante_id=1, nome="Liberdade", taxa_entrega=6.0, tempo_estimado_min=25, ativo=True),
        models.BairroEntrega(id=5, restaurante_id=1, nome="Consolação", taxa_entrega=4.0, tempo_estimado_min=15, ativo=True),
    ]
    db.add_all(bairros_db)

    # Promoção
    db.add(models.Promocao(
        restaurante_id=1, nome="Desconto 10%", tipo_desconto="percentual",
        valor_desconto=10, codigo_cupom="DESC10", ativo=True, uso_limitado=False,
    ))
    db.add(models.Promocao(
        restaurante_id=1, nome="Frete Grátis", tipo_desconto="fixo",
        valor_desconto=5, codigo_cupom="FRETEGRATIS", ativo=True, uso_limitado=False,
    ))

    # Motoboy
    db.add(models.Motoboy(
        id=1, restaurante_id=1, nome="Carlos Motoboy", usuario="carlos",
        telefone="5511888880001", status="aprovado", disponivel=True,
        latitude_atual=-23.55, longitude_atual=-46.63,
    ))

    db.commit()
    return bot_config


def telefone_ficticio(i):
    """Gera telefone único para cliente #i."""
    return f"55119{i:08d}"


def criar_cliente_existente(db, idx, nome, telefone):
    """Cria cliente + endereço + pedido entregue (para fluxos que precisam)."""
    bairro = random.choice(BAIRROS[:3])  # Só bairros cadastrados
    cliente = models.Cliente(
        restaurante_id=1, nome=nome, telefone=telefone,
        senha_hash=hashlib.sha256(telefone[:6].encode()).hexdigest(),
    )
    db.add(cliente)
    db.flush()

    db.add(models.EnderecoCliente(
        cliente_id=cliente.id,
        endereco_completo=f"Rua Fictícia {idx}, {bairro}, São Paulo - SP",
        bairro=bairro, padrao=True,
    ))

    # Pedido entregue (para repetir, avaliar, rastrear)
    produto = random.choice([1, 2, 3, 4])
    preco = {1: 45.0, 2: 40.0, 3: 48.0, 4: 42.0}[produto]
    nome_prod = {1: "Pizza Calabresa", 2: "Pizza Marguerita", 3: "Pizza Portuguesa", 4: "Pizza Frango Catupiry"}[produto]

    now = datetime.utcnow()
    pedido = models.Pedido(
        restaurante_id=1, cliente_id=cliente.id,
        comanda=f"SIM{idx:04d}", tipo="delivery", origem="whatsapp_bot",
        tipo_entrega="entrega", cliente_nome=nome, cliente_telefone=telefone,
        endereco_entrega=f"Rua Fictícia {idx}, {bairro}",
        itens=f"1x {nome_prod} (R${preco:.2f})",
        carrinho_json=[{"produto_id": produto, "nome": nome_prod, "quantidade": 1, "preco_unitario": preco}],
        valor_subtotal=preco, valor_taxa_entrega=5.0, valor_total=preco + 5.0,
        forma_pagamento="dinheiro", status="entregue",
        historico_status=[{"status": "entregue", "timestamp": now.isoformat()}],
        data_criacao=now - timedelta(hours=random.randint(1, 48)),
        atualizado_em=now - timedelta(hours=1),
    )
    db.add(pedido)
    db.flush()

    db.add(models.ItemPedido(pedido_id=pedido.id, produto_id=produto, quantidade=1, preco_unitario=preco))

    return cliente, pedido


def criar_pedido_ativo(db, cliente, idx):
    """Cria pedido pendente/em_preparo para cenários de alteração/cancelamento."""
    produto_id = random.choice([1, 2, 3, 4])
    preco = {1: 45.0, 2: 40.0, 3: 48.0, 4: 42.0}[produto_id]
    nome_prod = {1: "Pizza Calabresa", 2: "Pizza Marguerita", 3: "Pizza Portuguesa", 4: "Pizza Frango Catupiry"}[produto_id]
    status = random.choice(["pendente", "em_preparo"])
    now = datetime.utcnow()

    pedido = models.Pedido(
        restaurante_id=1, cliente_id=cliente.id,
        comanda=f"ATV{idx:04d}", tipo="delivery", origem="whatsapp_bot",
        tipo_entrega="entrega", cliente_nome=cliente.nome, cliente_telefone=cliente.telefone,
        endereco_entrega=f"Rua Fictícia {idx}",
        itens=f"1x {nome_prod} (R${preco:.2f})",
        carrinho_json=[{"produto_id": produto_id, "nome": nome_prod, "quantidade": 1, "preco_unitario": preco}],
        valor_subtotal=preco, valor_taxa_entrega=5.0, valor_total=preco + 5.0,
        forma_pagamento="dinheiro", status=status,
        historico_status=[{"status": status, "timestamp": now.isoformat()}],
        data_criacao=now - timedelta(minutes=random.randint(5, 30)),
        atualizado_em=now - timedelta(minutes=3),
    )
    db.add(pedido)
    db.flush()

    db.add(models.ItemPedido(pedido_id=pedido.id, produto_id=produto_id, quantidade=1, preco_unitario=preco))
    db.add(models.PedidoCozinha(restaurante_id=1, pedido_id=pedido.id, status="NOVO", pausado=False))

    return pedido, produto_id


def criar_pedido_em_rota(db, cliente, idx):
    """Cria pedido em_rota com entrega+motoboy para rastreamento."""
    now = datetime.utcnow()
    pedido = models.Pedido(
        restaurante_id=1, cliente_id=cliente.id,
        comanda=f"ROT{idx:04d}", tipo="delivery", origem="whatsapp_bot",
        tipo_entrega="entrega", cliente_nome=cliente.nome, cliente_telefone=cliente.telefone,
        endereco_entrega=f"Rua Fictícia {idx}",
        itens="1x Pizza Calabresa (R$45.00)",
        valor_subtotal=45.0, valor_taxa_entrega=5.0, valor_total=50.0,
        forma_pagamento="dinheiro", status="em_rota",
        historico_status=[
            {"status": "pendente", "timestamp": (now - timedelta(minutes=40)).isoformat()},
            {"status": "em_rota", "timestamp": (now - timedelta(minutes=5)).isoformat()},
        ],
        data_criacao=now - timedelta(minutes=40), atualizado_em=now - timedelta(minutes=5),
    )
    db.add(pedido)
    db.flush()
    db.add(models.ItemPedido(pedido_id=pedido.id, produto_id=1, quantidade=1, preco_unitario=45.0))
    db.add(models.Entrega(pedido_id=pedido.id, motoboy_id=1, status="em_rota", tempo_entrega=25))
    return pedido


# ==================== EXECUTOR ====================

async def call(db, nome, args, bot_config, conversa=None):
    result_str = await executar_funcao(nome, args, db, 1, bot_config, conversa)
    return json.loads(result_str)


# ==================== FLUXOS ====================

async def fluxo_novo_cliente_pedido(db, bot_config, idx, nome, tel):
    """Cliente novo: buscar(404) → cadastrar → cardápio → criar_pedido."""
    erros = []

    r = await call(db, "buscar_cliente", {"telefone": tel}, bot_config)
    if r.get("encontrado") is not False:
        erros.append(f"buscar_cliente deveria retornar encontrado=False para {tel}")

    r = await call(db, "cadastrar_cliente", {"nome": nome, "telefone": tel}, bot_config)
    if not (isinstance(r.get("id"), int) and r["id"] > 0):
        erros.append(f"cadastrar_cliente falhou: {r}")

    r = await call(db, "buscar_cardapio", {"busca": random.choice(["pizza", "coca", "pudim"])}, bot_config)
    if r.get("encontrados", 0) < 1:
        erros.append(f"buscar_cardapio 0 resultados")

    produto = random.choice([1, 2, 3, 4, 5])
    preco = {1: 45.0, 2: 40.0, 3: 48.0, 4: 42.0, 5: 12.0}[produto]
    nome_p = {1: "Pizza Calabresa", 2: "Pizza Marguerita", 3: "Pizza Portuguesa", 4: "Pizza Frango Catupiry", 5: "Coca-Cola 2L"}[produto]

    conversa = models.BotConversa(
        restaurante_id=1, telefone=tel, nome_cliente=nome,
        status="ativa", session_data={},
    )
    db.add(conversa)
    db.flush()

    r = await call(db, "criar_pedido", {
        "cliente_nome": nome, "cliente_telefone": tel,
        "itens": [{"produto_id": produto, "nome": nome_p, "quantidade": 1, "preco_unitario": preco}],
        "forma_pagamento": random.choice(FORMAS_PAGAMENTO),
        "tipo_entrega": "entrega",
        "endereco_entrega": f"Rua Fictícia {idx}, Centro, São Paulo",
    }, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"criar_pedido falhou: {r.get('erro', r)}")

    return ["buscar_cliente", "cadastrar_cliente", "buscar_cardapio", "criar_pedido"], erros


async def fluxo_cliente_repete(db, bot_config, cliente, pedido_entregue):
    """Cliente repete último pedido."""
    erros = []
    conversa = models.BotConversa(
        restaurante_id=1, cliente_id=cliente.id, telefone=cliente.telefone,
        nome_cliente=cliente.nome, status="ativa", session_data={},
    )
    db.add(conversa)
    db.flush()

    r = await call(db, "buscar_cliente", {"telefone": cliente.telefone}, bot_config)
    if r.get("encontrado") is not True:
        erros.append(f"buscar_cliente deveria encontrar {cliente.nome}")

    r = await call(db, "repetir_ultimo_pedido", {"cliente_telefone": cliente.telefone}, bot_config, conversa)
    if r.get("ultimo_pedido") is None and "erro" not in r:
        erros.append(f"repetir_ultimo_pedido sem resultado")

    return ["buscar_cliente", "repetir_ultimo_pedido"], erros


async def fluxo_cliente_rastreia(db, bot_config, cliente, pedido_rota):
    """Cliente rastreia pedido em rota."""
    erros = []

    r = await call(db, "consultar_status_pedido", {"pedido_id": pedido_rota.id}, bot_config)
    if r.get("pedido_id") != pedido_rota.id:
        erros.append(f"consultar_status retornou pedido_id={r.get('pedido_id')} (esperado {pedido_rota.id})")

    r = await call(db, "rastrear_pedido", {"pedido_id": pedido_rota.id}, bot_config)
    if r.get("pedido_id") != pedido_rota.id:
        erros.append(f"rastrear retornou pedido_id={r.get('pedido_id')} (esperado {pedido_rota.id})")
    if r.get("status") != "em_rota":
        erros.append(f"rastrear status={r.get('status')} (esperado em_rota)")
    if r.get("motoboy_nome") is None:
        erros.append("rastrear sem motoboy_nome")

    return ["consultar_status_pedido", "rastrear_pedido"], erros


async def fluxo_cliente_cancela(db, bot_config, cliente, pedido_ativo, conversa):
    """Cliente cancela pedido ativo."""
    erros = []
    r = await call(db, "cancelar_pedido", {
        "pedido_id": pedido_ativo.id, "motivo": "Mudei de ideia"
    }, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"cancelar_pedido falhou: {r}")
    # Verificar BD
    db.refresh(pedido_ativo)
    if pedido_ativo.status != "cancelado":
        erros.append(f"BD: pedido {pedido_ativo.id} status={pedido_ativo.status} (esperado cancelado)")
    return ["cancelar_pedido"], erros


async def fluxo_cliente_altera(db, bot_config, cliente, pedido_ativo):
    """Cliente adiciona item ao pedido."""
    erros = []
    valor_original = pedido_ativo.valor_total  # Capturar ANTES da alteração
    bebida = random.choice([5, 6])
    preco_bebida = 12.0 if bebida == 5 else 10.0
    r = await call(db, "alterar_pedido", {
        "pedido_id": pedido_ativo.id,
        "adicionar_itens": [{"produto_id": bebida, "quantidade": 1, "preco_unitario": preco_bebida}],
    }, bot_config)
    if r.get("sucesso") is not True:
        erros.append(f"alterar_pedido falhou: {r}")
    else:
        esperado = valor_original + preco_bebida
        if abs(r.get("novo_total", 0) - esperado) > 0.01:
            erros.append(f"novo_total={r.get('novo_total')} (esperado ~{esperado})")
    return ["alterar_pedido"], erros


async def fluxo_cliente_troca_item(db, bot_config, cliente, pedido_ativo, produto_original_id, conversa):
    """Cliente troca item do pedido."""
    erros = []
    nome_original = {1: "calabresa", 2: "marguerita", 3: "portuguesa", 4: "frango"}[produto_original_id]
    nomes_alt = {1: "calabresa", 2: "marguerita", 3: "portuguesa", 4: "frango"}
    novo_nome = random.choice([n for pid, n in nomes_alt.items() if pid != produto_original_id])

    r = await call(db, "trocar_item_pedido", {
        "pedido_id": pedido_ativo.id,
        "item_remover": nome_original,
        "item_novo": novo_nome,
        "quantidade": 1,
    }, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"trocar_item falhou: {r}")
    return ["trocar_item_pedido"], erros


async def fluxo_cliente_avalia(db, bot_config, cliente, conversa):
    """Cliente avalia pedido."""
    erros = []
    nota = random.randint(1, 5)
    cat = random.choice(["entrega", "comida", "atendimento"])
    r = await call(db, "registrar_avaliacao", {"nota": nota, "categoria": cat, "detalhe": "Teste"}, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"registrar_avaliacao falhou: {r}")
    if r.get("nota") != nota:
        erros.append(f"nota retornada={r.get('nota')} (esperado {nota})")
    return ["registrar_avaliacao"], erros


async def fluxo_cliente_reclama(db, bot_config, cliente, conversa):
    """Cliente reporta problema."""
    erros = []
    tipo = random.choice(PROBLEMAS_TIPO)
    r = await call(db, "registrar_problema", {
        "tipo": tipo, "descricao": f"Problema de teste tipo {tipo}",
    }, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"registrar_problema falhou: {r}")
    if not isinstance(r.get("problema_id"), int):
        erros.append(f"problema_id ausente ou inválido: {r.get('problema_id')}")
    return ["registrar_problema"], erros


async def fluxo_cliente_usa_cupom(db, bot_config, cliente, conversa):
    """Cliente aplica cupom e depois faz pedido."""
    erros = []
    cupom = random.choice(["DESC10", "FRETEGRATIS"])
    valor = random.choice([40.0, 45.0, 48.0, 50.0])
    r = await call(db, "aplicar_cupom", {"codigo_cupom": cupom, "valor_pedido": valor}, bot_config, conversa)
    if r.get("valido") is not True:
        erros.append(f"aplicar_cupom {cupom} falhou: {r}")
    if r.get("desconto", 0) <= 0:
        erros.append(f"desconto={r.get('desconto')} (esperado > 0)")
    return ["aplicar_cupom"], erros


async def fluxo_cliente_pergunta_info(db, bot_config):
    """Cliente pergunta horário, categorias, bairros, tempo."""
    erros = []

    r = await call(db, "verificar_horario", {}, bot_config)
    if "erro" in r or "horarios_semana" not in r:
        erros.append(f"verificar_horario falhou: {r}")

    r = await call(db, "buscar_categorias", {}, bot_config)
    if len(r.get("categorias", [])) < 2:
        erros.append(f"buscar_categorias < 2")

    r = await call(db, "consultar_bairros", {}, bot_config)
    if r.get("encontrados", 0) < 1:
        erros.append(f"consultar_bairros 0 resultados")

    bairro = random.choice(BAIRROS[:3])
    r = await call(db, "consultar_tempo_entrega", {"bairro": bairro}, bot_config)
    if r.get("tempo_preparo_min", 0) <= 0:
        erros.append(f"consultar_tempo_entrega tempo_preparo=0")

    return ["verificar_horario", "buscar_categorias", "consultar_bairros", "consultar_tempo_entrega"], erros


async def fluxo_cliente_atualiza_endereco(db, bot_config, cliente):
    """Cliente atualiza endereço."""
    erros = []
    bairro = random.choice(BAIRROS[:3])
    r = await call(db, "atualizar_endereco_cliente", {
        "telefone": cliente.telefone,
        "endereco_completo": f"Rua Nova {random.randint(1, 999)}, {bairro}, São Paulo - SP",
        "bairro": bairro,
    }, bot_config)
    if r.get("sucesso") is not True:
        erros.append(f"atualizar_endereco falhou: {r}")
    return ["atualizar_endereco_cliente"], erros


async def fluxo_cliente_escala_humano(db, bot_config, conversa):
    """Cliente pede atendimento humano."""
    erros = []
    r = await call(db, "escalar_humano", {"motivo": "Quero falar com o gerente"}, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"escalar_humano falhou: {r}")
    # Restaurar conversa
    conversa.status = "ativa"
    conversa.handoff_motivo = None
    return ["escalar_humano"], erros


async def fluxo_cliente_valida_endereco(db, bot_config, cliente, conversa):
    """Cliente valida endereço via Mapbox (mock) e confirma."""
    erros = []
    mock_sugestoes = [{
        "place_name": f"Rua Mock {random.randint(1, 999)}, Centro, São Paulo - SP, Brasil",
        "coordinates": (-23.55 + random.uniform(-0.01, 0.01), -46.63 + random.uniform(-0.01, 0.01)),
    }]

    with patch("utils.mapbox_api.autocomplete_address", return_value=mock_sugestoes), \
         patch("utils.mapbox_api._cache_key_dist", return_value=f"mock_{random.randint(1, 9999)}"), \
         patch("backend.app.cache.cache_get", return_value=None), \
         patch("backend.app.cache.cache_set"):
        r = await call(db, "validar_endereco", {"endereco_texto": f"Rua Teste {random.randint(1, 999)}"}, bot_config, conversa)

    if r.get("encontrado") is not True:
        erros.append(f"validar_endereco encontrado=False: {r.get('mensagem', '')}")
        return ["validar_endereco"], erros

    # Agora confirmar
    conversa_db = db.query(models.BotConversa).get(conversa.id)
    sd = conversa_db.session_data or {}
    sugestoes = sd.get("endereco_sugestoes", [])
    if sugestoes:
        r2 = await call(db, "confirmar_endereco_validado", {
            "telefone": cliente.telefone, "opcao_index": 0,
        }, bot_config, conversa_db)
        if r2.get("sucesso") is not True:
            erros.append(f"confirmar_endereco falhou: {r2}")
        return ["validar_endereco", "confirmar_endereco_validado"], erros
    else:
        erros.append("session_data.endereco_sugestoes vazio após validar_endereco")
        return ["validar_endereco"], erros


async def fluxo_cliente_pedido_retirada(db, bot_config, cliente, conversa):
    """Cliente faz pedido para retirada (sem taxa entrega)."""
    erros = []
    r = await call(db, "buscar_cardapio", {"busca": "pizza"}, bot_config)
    if r.get("encontrados", 0) < 1:
        erros.append("buscar_cardapio sem resultados")

    r = await call(db, "criar_pedido", {
        "cliente_nome": cliente.nome, "cliente_telefone": cliente.telefone,
        "itens": [{"produto_id": 2, "nome": "Pizza Marguerita", "quantidade": 1, "preco_unitario": 40.0}],
        "forma_pagamento": "cartao",
        "tipo_entrega": "retirada",
    }, bot_config, conversa)
    if r.get("sucesso") is not True:
        erros.append(f"criar_pedido retirada falhou: {r.get('erro', r)}")
    elif r.get("valor_total") != 40.0:
        erros.append(f"retirada valor_total={r.get('valor_total')} (esperado 40.0 sem taxa)")
    return ["buscar_cardapio", "criar_pedido"], erros


async def fluxo_cliente_busca_promos(db, bot_config, conversa):
    """Cliente busca promoções."""
    erros = []
    r = await call(db, "buscar_promocoes", {}, bot_config, conversa)
    if "erro" in r:
        erros.append(f"buscar_promocoes erro: {r}")
    if len(r.get("promocoes", [])) < 1:
        erros.append(f"nenhuma promoção encontrada")
    return ["buscar_promocoes"], erros


# ==================== ORQUESTRADOR ====================

async def executar_100_conversas():
    Base.metadata.create_all(bind=engine)
    db = Session()
    bot_config = criar_base(db)
    bot_config = db.query(models.BotConfig).filter_by(restaurante_id=1).first()

    random.seed(42)  # Reprodutível

    print("=" * 70)
    print("BOT HUMANOIDE — 100 CONVERSAS SIMULADAS")
    print("=" * 70)

    stats = {
        "total": 100,
        "sucesso": 0,
        "falhas": 0,
        "funcoes_testadas": Counter(),
        "funcoes_ok": Counter(),
        "funcoes_falha": Counter(),
        "erros_por_fluxo": defaultdict(list),
        "detalhes_falhas": [],
    }

    for i in range(100):
        nome = NOMES[i]
        tel = telefone_ficticio(i + 1)
        fluxo = FLUXOS[i % len(FLUXOS)]  # Distribuir fluxos uniformemente

        try:
            if fluxo == "novo_cliente_pedido":
                funcoes, erros = await fluxo_novo_cliente_pedido(db, bot_config, i, nome, tel)

            elif fluxo in ("cliente_repete", "cliente_rastreia", "cliente_cancela",
                          "cliente_altera", "cliente_troca_item", "cliente_avalia",
                          "cliente_reclama", "cliente_usa_cupom", "cliente_atualiza_endereco",
                          "cliente_escala_humano", "cliente_valida_endereco",
                          "cliente_pedido_retirada", "cliente_busca_promos"):
                # Criar cliente existente
                cliente, pedido_entregue = criar_cliente_existente(db, i, nome, tel)
                db.commit()

                conversa = models.BotConversa(
                    restaurante_id=1, cliente_id=cliente.id, telefone=tel,
                    nome_cliente=nome, status="ativa", pedido_ativo_id=pedido_entregue.id,
                    session_data={},
                )
                db.add(conversa)
                db.flush()

                if fluxo == "cliente_repete":
                    funcoes, erros = await fluxo_cliente_repete(db, bot_config, cliente, pedido_entregue)
                elif fluxo == "cliente_rastreia":
                    pedido_rota = criar_pedido_em_rota(db, cliente, i)
                    db.commit()
                    funcoes, erros = await fluxo_cliente_rastreia(db, bot_config, cliente, pedido_rota)
                elif fluxo == "cliente_cancela":
                    pedido_ativo, _ = criar_pedido_ativo(db, cliente, i)
                    db.commit()
                    funcoes, erros = await fluxo_cliente_cancela(db, bot_config, cliente, pedido_ativo, conversa)
                elif fluxo == "cliente_altera":
                    pedido_ativo, _ = criar_pedido_ativo(db, cliente, i)
                    db.commit()
                    funcoes, erros = await fluxo_cliente_altera(db, bot_config, cliente, pedido_ativo)
                elif fluxo == "cliente_troca_item":
                    pedido_ativo, prod_id = criar_pedido_ativo(db, cliente, i)
                    db.commit()
                    funcoes, erros = await fluxo_cliente_troca_item(db, bot_config, cliente, pedido_ativo, prod_id, conversa)
                elif fluxo == "cliente_avalia":
                    funcoes, erros = await fluxo_cliente_avalia(db, bot_config, cliente, conversa)
                elif fluxo == "cliente_reclama":
                    funcoes, erros = await fluxo_cliente_reclama(db, bot_config, cliente, conversa)
                elif fluxo == "cliente_usa_cupom":
                    funcoes, erros = await fluxo_cliente_usa_cupom(db, bot_config, cliente, conversa)
                elif fluxo == "cliente_atualiza_endereco":
                    funcoes, erros = await fluxo_cliente_atualiza_endereco(db, bot_config, cliente)
                elif fluxo == "cliente_escala_humano":
                    funcoes, erros = await fluxo_cliente_escala_humano(db, bot_config, conversa)
                elif fluxo == "cliente_valida_endereco":
                    funcoes, erros = await fluxo_cliente_valida_endereco(db, bot_config, cliente, conversa)
                elif fluxo == "cliente_pedido_retirada":
                    funcoes, erros = await fluxo_cliente_pedido_retirada(db, bot_config, cliente, conversa)
                elif fluxo == "cliente_busca_promos":
                    funcoes, erros = await fluxo_cliente_busca_promos(db, bot_config, conversa)
                else:
                    funcoes, erros = [], [f"fluxo desconhecido: {fluxo}"]

            elif fluxo == "cliente_pergunta_info":
                funcoes, erros = await fluxo_cliente_pergunta_info(db, bot_config)

            else:
                funcoes, erros = [], [f"fluxo desconhecido: {fluxo}"]

            # Contabilizar
            for f in funcoes:
                stats["funcoes_testadas"][f] += 1
                if not erros:
                    stats["funcoes_ok"][f] += 1

            if erros:
                stats["falhas"] += 1
                for f in funcoes:
                    stats["funcoes_falha"][f] += len(erros)
                stats["erros_por_fluxo"][fluxo].extend(erros)
                stats["detalhes_falhas"].append((i + 1, nome, fluxo, erros))
                print(f"  ❌ #{i+1:3d} {nome[:20]:20s} [{fluxo}] → {erros[0][:60]}")
            else:
                stats["sucesso"] += 1
                if (i + 1) % 10 == 0:
                    print(f"  ✅ #{i+1:3d} conversas processadas... ({stats['sucesso']} OK)")

            db.commit()

        except Exception as e:
            stats["falhas"] += 1
            stats["detalhes_falhas"].append((i + 1, nome, fluxo, [str(e)]))
            print(f"  ❌ #{i+1:3d} {nome[:20]:20s} [{fluxo}] → EXCEPTION: {str(e)[:60]}")
            db.rollback()

    # ==================== RELATÓRIO ====================
    print("\n" + "=" * 70)
    print("RELATÓRIO FINAL")
    print("=" * 70)

    print(f"\nConversas: {stats['sucesso']}/{stats['total']} OK ({stats['falhas']} falhas)")

    print(f"\nCobertura por função ({len(stats['funcoes_testadas'])} funções testadas):")
    todas_funcoes = sorted(stats["funcoes_testadas"].keys())
    for fn in todas_funcoes:
        total = stats["funcoes_testadas"][fn]
        falhas = stats["funcoes_falha"].get(fn, 0)
        status = "✅" if falhas == 0 else "❌"
        print(f"  {status} {fn:35s} {total:3d} chamadas, {falhas} falhas")

    # Funções NÃO testadas (das 22)
    todas_22 = {
        "buscar_cliente", "cadastrar_cliente", "buscar_cardapio", "buscar_categorias",
        "criar_pedido", "alterar_pedido", "cancelar_pedido", "repetir_ultimo_pedido",
        "consultar_status_pedido", "verificar_horario", "buscar_promocoes",
        "registrar_avaliacao", "registrar_problema", "aplicar_cupom", "escalar_humano",
        "rastrear_pedido", "trocar_item_pedido", "consultar_tempo_entrega",
        "consultar_bairros", "atualizar_endereco_cliente", "validar_endereco",
        "confirmar_endereco_validado",
    }
    nao_testadas = todas_22 - set(stats["funcoes_testadas"].keys())
    if nao_testadas:
        print(f"\n⚠️  Funções NÃO testadas: {', '.join(sorted(nao_testadas))}")

    if stats["detalhes_falhas"]:
        print(f"\nDetalhes das falhas ({len(stats['detalhes_falhas'])}):")
        for num, nome, fluxo, errs in stats["detalhes_falhas"][:20]:
            print(f"  #{num:3d} {nome[:20]:20s} [{fluxo}]")
            for e in errs:
                print(f"       → {e[:80]}")

    print("\n" + "=" * 70)
    if stats["falhas"] == 0:
        print(f"🏆 100/100 CONVERSAS OK — 22/22 FUNÇÕES TESTADAS ✅")
    else:
        cobertura = len(stats["funcoes_testadas"])
        print(f"RESULTADO: {stats['sucesso']}/100 OK, {cobertura}/22 funções cobertas")
    print("=" * 70)

    db.close()
    return stats["falhas"] == 0


if __name__ == "__main__":
    success = asyncio.run(executar_100_conversas())
    sys.exit(0 if success else 1)
