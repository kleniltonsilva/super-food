"""
seed_006_produtos_pizzaria.py - Seed de Produtos para Pizzaria
Super Food SaaS

Cria produtos modelo (pizzas, bebidas, sobremesas) com variações
(tamanhos, bordas, adicionais) para restaurantes tipo pizzaria.
"""

from typing import Optional
from database.seed.base_seed import BaseSeed
from database.models import Produto, VariacaoProduto, CategoriaMenu


# ==================== DADOS DOS PRODUTOS ====================

PIZZAS_SALGADAS = [
    {"nome": "Calabresa", "descricao": "Calabresa fatiada, cebola e azeitonas", "preco": 45.00},
    {"nome": "Margherita", "descricao": "Molho de tomate, mussarela, manjericão fresco e azeite", "preco": 42.00},
    {"nome": "Portuguesa", "descricao": "Presunto, ovos, cebola, azeitona, ervilha e mussarela", "preco": 48.00},
    {"nome": "Frango c/ Catupiry", "descricao": "Frango desfiado temperado com catupiry cremoso", "preco": 47.00},
    {"nome": "4 Queijos", "descricao": "Mussarela, provolone, parmesão e gorgonzola", "preco": 46.00},
    {"nome": "Pepperoni", "descricao": "Pepperoni importado com mussarela e orégano", "preco": 49.00},
    {"nome": "Lombo c/ Catupiry", "descricao": "Lombo canadense fatiado com catupiry", "preco": 48.00},
    {"nome": "Bacon", "descricao": "Bacon crocante, mussarela e orégano", "preco": 47.00},
    {"nome": "Napolitana", "descricao": "Tomate fatiado, mussarela, parmesão e manjericão", "preco": 44.00},
    {"nome": "Mussarela", "descricao": "Mussarela de qualidade, tomate e orégano", "preco": 40.00},
]

PIZZAS_DOCES = [
    {"nome": "Chocolate c/ Morango", "descricao": "Chocolate ao leite com morangos frescos", "preco": 42.00},
    {"nome": "Banana c/ Canela", "descricao": "Banana caramelizada com canela e açúcar", "preco": 38.00},
    {"nome": "Romeu e Julieta", "descricao": "Goiabada com queijo minas derretido", "preco": 40.00},
    {"nome": "Prestígio", "descricao": "Chocolate ao leite com coco ralado", "preco": 42.00},
    {"nome": "Brigadeiro", "descricao": "Brigadeiro cremoso com granulado", "preco": 40.00},
]

BEBIDAS = [
    {"nome": "Coca-Cola 2L", "descricao": "Refrigerante Coca-Cola 2 litros", "preco": 14.00},
    {"nome": "Guaraná 2L", "descricao": "Refrigerante Guaraná Antarctica 2 litros", "preco": 12.00},
    {"nome": "Coca-Cola Lata", "descricao": "Refrigerante Coca-Cola lata 350ml", "preco": 7.00},
    {"nome": "Suco Natural 500ml", "descricao": "Suco natural da fruta 500ml", "preco": 10.00},
    {"nome": "Água 500ml", "descricao": "Água mineral 500ml", "preco": 4.00},
]

SOBREMESAS = [
    {"nome": "Petit Gateau", "descricao": "Bolinho de chocolate com sorvete de creme", "preco": 22.00},
    {"nome": "Brownie c/ Sorvete", "descricao": "Brownie de chocolate com sorvete de baunilha", "preco": 18.00},
    {"nome": "Pudim", "descricao": "Pudim de leite condensado caseiro", "preco": 12.00},
]

# Variações padrão para pizzas
TAMANHOS_PIZZA = [
    {"nome": "Broto (25cm)", "preco_adicional": -20.00, "ordem": 1},
    {"nome": "Média (30cm)", "preco_adicional": -10.00, "ordem": 2},
    {"nome": "Grande (35cm)", "preco_adicional": 0.00, "ordem": 3},
    {"nome": "Gigante (40cm)", "preco_adicional": 10.00, "ordem": 4},
]

BORDAS_PIZZA = [
    {"nome": "Sem borda", "preco_adicional": 0.00, "ordem": 1},
    {"nome": "Catupiry", "preco_adicional": 5.00, "ordem": 2},
    {"nome": "Cheddar", "preco_adicional": 5.00, "ordem": 3},
    {"nome": "Chocolate", "preco_adicional": 6.00, "ordem": 4},
]

ADICIONAIS_PIZZA = [
    {"nome": "Azeitona extra", "preco_adicional": 2.00, "ordem": 1},
    {"nome": "Orégano extra", "preco_adicional": 0.00, "ordem": 2},
    {"nome": "Pimenta", "preco_adicional": 0.00, "ordem": 3},
]


def criar_produtos_pizzaria(session, restaurante_id: int) -> int:
    """
    Cria produtos modelo de pizzaria com variações.

    Args:
        session: Sessão SQLAlchemy ativa
        restaurante_id: ID do restaurante

    Returns:
        Número total de registros criados (produtos + variações)
    """
    # Buscar categorias do restaurante
    categorias = session.query(CategoriaMenu).filter(
        CategoriaMenu.restaurante_id == restaurante_id,
        CategoriaMenu.ativo == True
    ).order_by(CategoriaMenu.ordem_exibicao).all()

    if not categorias:
        return 0

    # Mapear categorias por nome aproximado
    cat_map = {}
    for cat in categorias:
        nome_lower = cat.nome.lower()
        if "salgad" in nome_lower or ("pizza" in nome_lower and "doce" not in nome_lower):
            cat_map["salgadas"] = cat.id
        elif "doce" in nome_lower:
            cat_map["doces"] = cat.id
        elif "bebid" in nome_lower:
            cat_map["bebidas"] = cat.id
        elif "sobremes" in nome_lower:
            cat_map["sobremesas"] = cat.id

    # Fallback: se não encontrou, usar a primeira categoria
    if not cat_map:
        cat_map["salgadas"] = categorias[0].id
        if len(categorias) > 1:
            cat_map["doces"] = categorias[1].id
        if len(categorias) > 2:
            cat_map["bebidas"] = categorias[2].id
        if len(categorias) > 3:
            cat_map["sobremesas"] = categorias[3].id

    total_criados = 0

    # Criar pizzas salgadas
    cat_id = cat_map.get("salgadas")
    if cat_id:
        for i, dados in enumerate(PIZZAS_SALGADAS):
            produto = Produto(
                restaurante_id=restaurante_id,
                categoria_id=cat_id,
                nome=dados["nome"],
                descricao=dados["descricao"],
                preco=dados["preco"],
                disponivel=True,
                destaque=(i < 3),
                ordem_exibicao=i + 1,
            )
            session.add(produto)
            session.flush()
            total_criados += 1

            # Variações de tamanho
            for t in TAMANHOS_PIZZA:
                session.add(VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="tamanho",
                    nome=t["nome"],
                    preco_adicional=t["preco_adicional"],
                    ordem=t["ordem"],
                    ativo=True,
                ))
                total_criados += 1

            # Variações de borda
            for b in BORDAS_PIZZA:
                session.add(VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="borda",
                    nome=b["nome"],
                    preco_adicional=b["preco_adicional"],
                    ordem=b["ordem"],
                    ativo=True,
                ))
                total_criados += 1

            # Adicionais
            for a in ADICIONAIS_PIZZA:
                session.add(VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="adicional",
                    nome=a["nome"],
                    preco_adicional=a["preco_adicional"],
                    ordem=a["ordem"],
                    ativo=True,
                ))
                total_criados += 1

    # Criar pizzas doces
    cat_id = cat_map.get("doces")
    if cat_id:
        for i, dados in enumerate(PIZZAS_DOCES):
            produto = Produto(
                restaurante_id=restaurante_id,
                categoria_id=cat_id,
                nome=dados["nome"],
                descricao=dados["descricao"],
                preco=dados["preco"],
                disponivel=True,
                ordem_exibicao=i + 1,
            )
            session.add(produto)
            session.flush()
            total_criados += 1

            # Variações de tamanho
            for t in TAMANHOS_PIZZA:
                session.add(VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="tamanho",
                    nome=t["nome"],
                    preco_adicional=t["preco_adicional"],
                    ordem=t["ordem"],
                    ativo=True,
                ))
                total_criados += 1

            # Bordas
            for b in BORDAS_PIZZA:
                session.add(VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="borda",
                    nome=b["nome"],
                    preco_adicional=b["preco_adicional"],
                    ordem=b["ordem"],
                    ativo=True,
                ))
                total_criados += 1

    # Criar bebidas (sem variações)
    cat_id = cat_map.get("bebidas")
    if cat_id:
        for i, dados in enumerate(BEBIDAS):
            produto = Produto(
                restaurante_id=restaurante_id,
                categoria_id=cat_id,
                nome=dados["nome"],
                descricao=dados["descricao"],
                preco=dados["preco"],
                disponivel=True,
                ordem_exibicao=i + 1,
            )
            session.add(produto)
            total_criados += 1

    # Criar sobremesas (sem variações)
    cat_id = cat_map.get("sobremesas")
    if cat_id:
        for i, dados in enumerate(SOBREMESAS):
            produto = Produto(
                restaurante_id=restaurante_id,
                categoria_id=cat_id,
                nome=dados["nome"],
                descricao=dados["descricao"],
                preco=dados["preco"],
                disponivel=True,
                ordem_exibicao=i + 1,
            )
            session.add(produto)
            total_criados += 1

    session.flush()
    return total_criados


class ProdutosPizzariaSeed(BaseSeed):
    """Seed de produtos modelo para pizzarias"""
    order = 6
    name = "Produtos Modelo Pizzaria"
    skip_if_exists = True

    def check_exists(self, session, restaurante_id=None):
        if not restaurante_id:
            return True
        count = session.query(Produto).filter(
            Produto.restaurante_id == restaurante_id
        ).count()
        return count > 0

    def run(self, session, restaurante_id=None):
        if not restaurante_id:
            return 0
        if self.skip_if_exists and self.check_exists(session, restaurante_id):
            return 0
        return criar_produtos_pizzaria(session, restaurante_id)


# Instância do seed para registro
seed = ProdutosPizzariaSeed()
