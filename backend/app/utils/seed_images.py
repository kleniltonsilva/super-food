"""
Dicionario de imagens de produtos para seed/demo por tipo de restaurante.
Todas as URLs sao do Unsplash (CDN publico, hotlink-friendly, sem autenticacao).

Formato URL: https://images.unsplash.com/photo-{ID}?w=400&h=400&fit=crop
- w=400, h=400: tamanho adequado para cards de produto
- fit=crop: garante proporcao quadrada sem distorcao

Licenca Unsplash: uso gratuito comercial, sem atribuicao obrigatoria.
Todas as URLs foram testadas e validadas (HTTP 200).
"""

# Formato padrao para montar URLs Unsplash com tamanho customizado
UNSPLASH_BASE = "https://images.unsplash.com"


def _u(photo_id: str, w: int = 400, h: int = 400) -> str:
    """Monta URL Unsplash com resize e crop."""
    return f"{UNSPLASH_BASE}/photo-{photo_id}?w={w}&h={h}&fit=crop&auto=format&q=80"


# ============================================================
# PIZZARIA
# ============================================================
PIZZARIA_IMAGES = {
    # Pizza Margherita — mozzarella, tomate, manjericao
    "Pizza Margherita": _u("1574071318508-1cdbab80d002"),
    # Pizza Calabresa — calabresa fatiada, cebola
    "Pizza Calabresa": _u("1565299624946-b28f40a0ae38"),
    # Pizza Portuguesa — presunto, ovo, cebola, azeitona
    "Pizza Portuguesa": _u("1571407970349-bc81e7e96d47"),
    # Pizza Quatro Queijos — mozzarella, gorgonzola, parmesao, provolone
    "Pizza Quatro Queijos": _u("1513104890138-7c749659a591"),
    # Pizza Pepperoni — fatias de pepperoni
    "Pizza Pepperoni": _u("1628840042765-356cda07504e"),
    # Pizza Frango com Catupiry — frango desfiado, catupiry
    "Pizza Frango com Catupiry": _u("1590947132387-155cc02f3212"),
    # Pizza Napolitana — tomate, mozzarella, anchovas, alcaparras
    "Pizza Napolitana": _u("1604382354936-07c5d9983bd3"),
    # Pizza Bacon — bacon crocante, mozzarella
    "Pizza Bacon": _u("1571407970349-bc81e7e96d47"),
    # Pizza do Chef — gourmet artesanal
    "Pizza do Chef": _u("1593560708920-61dd98c46a4e"),
    # Pizza de Camarao — camaroes, catupiry
    "Pizza de Camarao": _u("1565299624946-b28f40a0ae38"),
    # Pizza File Mignon — file mignon, cebola caramelizada
    "Pizza File Mignon": _u("1565299624946-b28f40a0ae38"),
    # Pizza Salmao — salmao defumado, cream cheese
    "Pizza Salmao": _u("1576458088443-04a19bb13da6"),
    # Pizza Chocolate (doce) — chocolate, granulado
    "Pizza Chocolate": _u("1606313564200-e75d5e30476c"),
    # Pizza Banana com Canela (doce) — banana, canela, acucar
    "Pizza Banana com Canela": _u("1565299585323-38d6b0865b47"),
    # Pizza Brigadeiro (doce) — brigadeiro, granulado
    "Pizza Brigadeiro": _u("1606313564200-e75d5e30476c"),
    # Pizza Romeu e Julieta (doce) — goiabada, queijo minas
    "Pizza Romeu e Julieta": _u("1513104890138-7c749659a591"),
}

# ============================================================
# HAMBURGUERIA
# ============================================================
HAMBURGUERIA_IMAGES = {
    # Classic Smash Burger — smash patty, queijo, alface, tomate
    "Classic Smash Burger": _u("1568901346375-23c9450c58cd"),
    # Double Smash Burger — dois smash patties, queijo duplo
    "Double Smash Burger": _u("1553979459-d2229ba7433b"),
    # Bacon Burger — bacon crocante, queijo cheddar
    "Bacon Burger": _u("1553979459-d2229ba7433b"),
    # Cheese Burger — queijo cheddar derretido classico
    "Cheese Burger": _u("1571091718767-18b5b1457add"),
    # Egg Burger — ovo frito, queijo, salada
    "Egg Burger": _u("1561758033-d89a9ad46330"),
    # Wagyu Burger — carne wagyu premium
    "Wagyu Burger": _u("1594212699903-ec8a3eca50f5"),
    # Pulled Pork Burger — carne de porco desfiada
    "Pulled Pork Burger": _u("1550547660-d9450f859349"),
    # Blue Cheese Burger — gorgonzola, cebola caramelizada
    "Blue Cheese Burger": _u("1586190848861-99aa4a171e90"),
    # Chicken Crispy Burger — frango empanado crocante
    "Chicken Crispy Burger": _u("1606755962773-d324e0a13086"),
    # Batata Frita — porcao de batata frita
    "Batata Frita": _u("1630384060421-cb20d0e0649d"),
    # Onion Rings — aneis de cebola empanados
    "Onion Rings": _u("1639024471283-03518883512d"),
    # Nuggets — nuggets de frango
    "Nuggets": _u("1585937421612-70a008356fbe"),
    # Milkshake Chocolate — milkshake cremoso de chocolate
    "Milkshake Chocolate": _u("1572490122747-3968b75cc699"),
    # Brownie com Sorvete — brownie quente com bola de sorvete
    "Brownie com Sorvete": _u("1564355808539-22fda35bed7e"),
}

# ============================================================
# SUSHI / JAPONESA
# ============================================================
SUSHI_IMAGES = {
    # Combinado sushi — variedade de nigiris e makis
    "Combinado 15 Pecas": _u("1579871494447-9811cf80d66c"),
    "Combinado 20 Pecas": _u("1579871494447-9811cf80d66c"),
    "Combinado 30 Pecas": _u("1553621042-f6e147245754"),
    "Combinado 50 Pecas": _u("1553621042-f6e147245754"),
    # Sashimi Salmao — fatias frescas de salmao
    "Sashimi Salmao": _u("1579584425555-c3ce17fd4351"),
    # Sashimi Atum — fatias frescas de atum
    "Sashimi Atum": _u("1534256958597-7fe685cbd745"),
    # Hot Philadelphia — hot roll frito com cream cheese
    "Hot Philadelphia": _u("1617196034796-73dfa7b1fd56"),
    # Hot Roll — roll empanado e frito
    "Hot Roll": _u("1617196034796-73dfa7b1fd56"),
    # Temaki Salmao — cone de alga com salmao
    "Temaki Salmao": _u("1579871494447-9811cf80d66c"),
    # Temaki Atum — cone de alga com atum
    "Temaki Atum": _u("1579871494447-9811cf80d66c"),
}

# ============================================================
# ACAI
# ============================================================
ACAI_IMAGES = {
    # Acai bowl — acai com granola, banana, morango
    "Acai 300ml": _u("1590301157890-4810ed352733"),
    "Acai 500ml": _u("1590301157890-4810ed352733"),
    "Acai 700ml": _u("1590301157890-4810ed352733"),
    "Acai 1L": _u("1590301157890-4810ed352733"),
    # Bowl Tropical — acai com frutas tropicais
    "Bowl Tropical": _u("1590301157890-4810ed352733"),
    # Bowl Fitness — acai com granola, whey, banana
    "Bowl Fitness": _u("1546039907-7fa05f864c02"),
    # Bowl Premium — acai premium com toppings especiais
    "Bowl Premium": _u("1502741338009-cac2772e18bc"),
    # Sorvete — bola de sorvete em casquinha ou pote
    "Sorvete": _u("1497034825429-c343d7c6a68f"),
    # Milkshake — milkshake cremoso
    "Milkshake": _u("1572490122747-3968b75cc699"),
    # Sundae — sundae com calda e chantilly
    "Sundae": _u("1563805042-7684c019e1cb"),
}

# ============================================================
# BEBIDAS
# ============================================================
BEBIDAS_IMAGES = {
    # === Cervejas ===
    "Cerveja Skol": _u("1535958636474-b021ee887b13"),
    "Cerveja Heineken": _u("1558642452-9d2a7deb7f62"),
    "Cerveja Corona": _u("1560512823-829485b8bf24"),
    "Cerveja Brahma": _u("1535958636474-b021ee887b13"),
    "Cerveja Original": _u("1558642452-9d2a7deb7f62"),
    "Cerveja Stella Artois": _u("1558642452-9d2a7deb7f62"),
    # === Refrigerantes ===
    "Coca-Cola Lata": _u("1554866585-cd94860890b7"),
    "Coca-Cola 600ml": _u("1554866585-cd94860890b7"),
    "Guarana Antarctica": _u("1625772299848-391b6a87d7b3"),
    "Fanta Laranja": _u("1625772299848-391b6a87d7b3"),
    "Sprite": _u("1625772299848-391b6a87d7b3"),
    # === Destilados ===
    "Vodka Absolut": _u("1569529465841-dfecdab7503b"),
    "Whisky Jack Daniels": _u("1569529465841-dfecdab7503b"),
    "Gin Tanqueray": _u("1569529465841-dfecdab7503b"),
    # === Energeticos ===
    "Red Bull": _u("1527960471264-932f39eb5846"),
    "Monster Energy": _u("1527960471264-932f39eb5846"),
}

# ============================================================
# ESFIHARIA
# ============================================================
ESFIHARIA_IMAGES = {
    # Esfiha de carne — massa aberta com carne moida temperada
    "Esfiha Carne": _u("1565299624946-b28f40a0ae38"),
    # Esfiha de queijo — massa aberta com queijo derretido
    "Esfiha Queijo": _u("1565299624946-b28f40a0ae38"),
    # Kibe — bolinho frito de trigo com carne
    "Kibe": _u("1529042410759-befb1204b468"),
    # Beirute — sanduiche no pao sirio
    "Beirute": _u("1529042410759-befb1204b468"),
}

# ============================================================
# RESTAURANTE (comida caseira)
# ============================================================
RESTAURANTE_IMAGES = {
    # File Grelhado — file de carne grelhado
    "File Grelhado": _u("1558030006-450675393462"),
    # Frango a Parmegiana — frango empanado com molho e queijo
    "Frango a Parmegiana": _u("1604908176997-125f25cc6f3d"),
    # Picanha na Chapa — picanha fatiada na chapa
    "Picanha na Chapa": _u("1558030006-450675393462"),
    # Strogonoff — strogonoff de carne com arroz e batata palha
    "Strogonoff": _u("1574484284002-952d92456975"),
    # Feijoada — feijoada completa com arroz e farofa
    "Feijoada": _u("1589302168068-964664d93dc0"),
    # Espaguete a Bolonhesa — espaguete com molho bolonhesa
    "Espaguete a Bolonhesa": _u("1563379926898-05f4575a45d8"),
    # Lasanha — lasanha gratinada
    "Lasanha": _u("1574894709920-11b28e7367e3"),
    # Salada Caesar — salada com frango, croutons, parmesao
    "Salada Caesar": _u("1546793665-c74683f339c1"),
}

# ============================================================
# SALGADOS / LANCHONETE
# ============================================================
SALGADOS_IMAGES = {
    # Coxinha — coxinha de frango frita
    "Coxinha": _u("1601050690597-df0568f70950"),
    # Empada — empada de palmito/frango
    "Empada": _u("1529042410759-befb1204b468"),
    # Pao de Queijo — pao de queijo mineiro
    "Pao de Queijo": _u("1558961363-fa8fdf82db35"),
    # Pastel — pastel frito de carne/queijo
    "Pastel": _u("1529042410759-befb1204b468"),
    # Brigadeiro — brigadeiro de chocolate
    "Brigadeiro": _u("1606313564200-e75d5e30476c"),
    # Mini Churros — churros com doce de leite
    "Mini Churros": _u("1586040140378-b5634cb4c8fc"),
    # Torta de Frango — torta salgada de frango
    "Torta de Frango": _u("1621996346565-e3dbc646d9a9"),
}


# ============================================================
# MAPA GERAL: tipo_restaurante -> dict de imagens
# ============================================================
PRODUCT_IMAGES_BY_TYPE = {
    "pizzaria": PIZZARIA_IMAGES,
    "hamburgueria": HAMBURGUERIA_IMAGES,
    "sushi": SUSHI_IMAGES,
    "japonesa": SUSHI_IMAGES,
    "acai": ACAI_IMAGES,
    "acaiteria": ACAI_IMAGES,
    "bebidas": BEBIDAS_IMAGES,
    "bar": BEBIDAS_IMAGES,
    "esfiharia": ESFIHARIA_IMAGES,
    "restaurante": RESTAURANTE_IMAGES,
    "comida_caseira": RESTAURANTE_IMAGES,
    "salgados": SALGADOS_IMAGES,
    "lanchonete": SALGADOS_IMAGES,
}


def get_product_image(tipo_restaurante: str, nome_produto: str) -> str | None:
    """
    Retorna URL de imagem para um produto dado o tipo de restaurante.
    Busca exata primeiro, depois busca parcial (contains).
    Retorna None se nao encontrar.
    """
    tipo = tipo_restaurante.lower().strip()
    images = PRODUCT_IMAGES_BY_TYPE.get(tipo)
    if not images:
        return None

    # Busca exata
    if nome_produto in images:
        return images[nome_produto]

    # Busca parcial (case-insensitive)
    nome_lower = nome_produto.lower()
    for key, url in images.items():
        if key.lower() in nome_lower or nome_lower in key.lower():
            return url

    return None


def get_all_images_for_type(tipo_restaurante: str) -> dict[str, str]:
    """Retorna todas as imagens para um tipo de restaurante."""
    tipo = tipo_restaurante.lower().strip()
    return PRODUCT_IMAGES_BY_TYPE.get(tipo, {})
