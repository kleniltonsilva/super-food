"""
seed_produtos_padrao.py — Produtos padrão para todos os 8 tipos de restaurante.

Chamado automaticamente ao criar um novo restaurante via SuperAdmin.
Cria categorias + produtos + combos para que o site não fique vazio.

Super Food SaaS - Sprint 11
"""

from datetime import datetime, timedelta
from database.models import Produto, VariacaoProduto, CategoriaMenu, Combo, ComboItem


# ==================== DADOS POR TIPO ====================

DADOS_PRODUTOS = {
    "pizzaria": {
        "categorias": [
            {
                "nome": "Pizzas Tradicionais",
                "produtos": [
                    ("Margherita", "Molho de tomate, mussarela, manjericão fresco e azeite", 39.90),
                    ("Calabresa", "Calabresa fatiada, cebola, azeitona e orégano", 42.90),
                    ("Portuguesa", "Presunto, ovos, cebola, ervilha, azeitona e mussarela", 45.90),
                    ("Quatro Queijos", "Mussarela, provolone, gorgonzola e parmesão", 49.90),
                    ("Pepperoni", "Pepperoni premium importado com mussarela e molho especial", 52.90),
                    ("Frango com Catupiry", "Frango desfiado com catupiry original e milho", 44.90),
                    ("Napolitana", "Tomate fatiado, mussarela, parmesão e manjericão", 41.90),
                    ("Bacon", "Bacon crocante, mussarela, cebola caramelizada e molho barbecue", 47.90),
                ],
                "variacoes": {
                    "tamanho": [
                        ("Broto (25cm)", -20.00),
                        ("Média (30cm)", -10.00),
                        ("Grande (35cm)", 0.00),
                        ("Gigante (40cm)", 10.00),
                    ],
                    "borda": [
                        ("Sem borda", 0.00),
                        ("Catupiry", 5.00),
                        ("Cheddar", 5.00),
                        ("Chocolate", 6.00),
                    ],
                },
            },
            {
                "nome": "Pizzas Especiais",
                "produtos": [
                    ("Pizza do Chef", "Rúcula, tomate seco, parmesão e presunto de Parma", 59.90),
                    ("Camarão", "Camarões ao alho, mussarela e catupiry com cebolinha", 65.90),
                    ("Filé Mignon", "Filé mignon em tiras, cebola roxa e cream cheese", 62.90),
                    ("Salmão", "Salmão defumado, cream cheese, alcaparras e cebolinha", 69.90),
                ],
                "variacoes": {
                    "tamanho": [
                        ("Broto (25cm)", -20.00),
                        ("Média (30cm)", -10.00),
                        ("Grande (35cm)", 0.00),
                        ("Gigante (40cm)", 10.00),
                    ],
                    "borda": [
                        ("Sem borda", 0.00),
                        ("Catupiry", 5.00),
                        ("Cheddar", 5.00),
                    ],
                },
            },
            {
                "nome": "Pizzas Doces",
                "produtos": [
                    ("Chocolate", "Chocolate ao leite com granulado e leite condensado", 38.90),
                    ("Banana com Canela", "Banana, canela, leite condensado e mussarela", 36.90),
                    ("Brigadeiro", "Brigadeiro artesanal com granulado belga", 39.90),
                    ("Romeu e Julieta", "Goiabada cremosa com queijo minas derretido", 37.90),
                ],
                "variacoes": {
                    "tamanho": [
                        ("Broto (25cm)", -20.00),
                        ("Média (30cm)", -10.00),
                        ("Grande (35cm)", 0.00),
                    ],
                    "borda": [
                        ("Sem borda", 0.00),
                        ("Chocolate", 6.00),
                    ],
                },
            },
            {
                "nome": "Bebidas",
                "produtos": [
                    ("Coca-Cola 2L", "Coca-Cola original 2 litros", 14.90),
                    ("Guaraná Antarctica 2L", "Guaraná Antarctica 2 litros", 12.90),
                    ("Suco Natural 500ml", "Laranja, limão, maracujá ou abacaxi", 9.90),
                    ("Água Mineral 500ml", "Com ou sem gás", 4.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Combo Família",
                "descricao": "1 Pizza Grande + 1 Pizza Média + 1 Refrigerante 2L",
                "preco_combo": 89.90,
                "preco_original": 109.70,
                "tipo_combo": "padrao",
            },
            {
                "nome": "Combo Casal",
                "descricao": "1 Pizza Grande + Borda Recheada + 2 Refrigerantes",
                "preco_combo": 59.90,
                "preco_original": 72.70,
                "tipo_combo": "padrao",
            },
        ],
    },

    "hamburgueria": {
        "categorias": [
            {
                "nome": "Burgers Clássicos",
                "produtos": [
                    ("Classic Smash", "Blend 120g, queijo cheddar, alface, tomate e molho especial", 28.90),
                    ("Double Smash", "2x blend 120g, cheddar duplo, cebola caramelizada e pickles", 38.90),
                    ("Bacon Burger", "Blend 150g, bacon crocante, cheddar, alface e molho barbecue", 34.90),
                    ("Cheese Burger", "Blend 150g, cheddar triplo derretido e cebola crispy", 32.90),
                    ("Egg Burger", "Blend 150g, ovo com gema mole, bacon e cheddar", 35.90),
                ],
            },
            {
                "nome": "Burgers Premium",
                "produtos": [
                    ("Wagyu Burger", "Blend wagyu 180g, gruyère, rúcula, tomate confit e aioli trufado", 52.90),
                    ("Pulled Pork", "Carne de porco desfiada 12h, coleslaw e molho barbecue defumado", 42.90),
                    ("Blue Cheese", "Blend 180g, gorgonzola, cebola caramelizada no vinho e rúcula", 45.90),
                    ("Chicken Crispy", "Frango empanado crocante, maionese de ervas e salada", 36.90),
                ],
            },
            {
                "nome": "Acompanhamentos",
                "produtos": [
                    ("Batata Frita P", "Porção pequena com sal e ketchup", 12.90),
                    ("Batata Frita G", "Porção grande com sal e ketchup", 18.90),
                    ("Onion Rings", "Anéis de cebola empanados crocantes", 16.90),
                    ("Nuggets 10un", "Nuggets de frango crocantes com molho", 19.90),
                    ("Batata com Cheddar e Bacon", "Batata frita coberta com cheddar e bacon", 24.90),
                ],
            },
            {
                "nome": "Bebidas",
                "produtos": [
                    ("Milkshake Chocolate", "Milkshake cremoso de chocolate belga 400ml", 18.90),
                    ("Milkshake Morango", "Milkshake de morango com calda 400ml", 18.90),
                    ("Coca-Cola Lata", "Coca-Cola 350ml", 6.90),
                    ("Suco Natural", "Laranja ou limão 300ml", 8.90),
                    ("Cerveja Artesanal", "IPA ou Pilsen 473ml", 14.90),
                ],
            },
            {
                "nome": "Sobremesas",
                "produtos": [
                    ("Brownie com Sorvete", "Brownie quentinho com sorvete de baunilha e calda", 22.90),
                    ("Petit Gateau", "Bolo de chocolate com centro derretido e sorvete", 24.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Combo Smash",
                "descricao": "Classic Smash + Batata Frita P + Refrigerante Lata",
                "preco_combo": 39.90,
                "preco_original": 48.70,
                "tipo_combo": "padrao",
            },
            {
                "nome": "Combo Double",
                "descricao": "Double Smash + Batata Frita G + Milkshake",
                "preco_combo": 62.90,
                "preco_original": 76.70,
                "tipo_combo": "padrao",
            },
        ],
    },

    "sushi": {
        "categorias": [
            {
                "nome": "Combinados",
                "produtos": [
                    ("Combinado 15 peças", "5 sashimis + 5 niguiris + 5 uramakis variados", 49.90),
                    ("Combinado 20 peças", "Mix do chef com sashimis, niguiris e rolls", 62.90),
                    ("Combinado 30 peças", "Seleção premium com salmão, atum e camarão", 89.90),
                    ("Combinado 50 peças", "Banquete completo para 2 pessoas", 139.90),
                    ("Combo Salmão Premium", "20 peças exclusivas de salmão em diversas preparações", 79.90),
                ],
            },
            {
                "nome": "Sashimis",
                "produtos": [
                    ("Sashimi Salmão 5pç", "Fatias frescas de salmão norueguês", 24.90),
                    ("Sashimi Atum 5pç", "Fatias de atum fresco selecionado", 29.90),
                    ("Sashimi Peixe Branco 5pç", "Peixe branco fresco do dia", 22.90),
                    ("Sashimi Polvo 5pç", "Polvo macio ao ponto", 34.90),
                ],
            },
            {
                "nome": "Hot Rolls",
                "produtos": [
                    ("Hot Philadelphia", "Salmão, cream cheese empanado e frito, 8 peças", 32.90),
                    ("Hot Skin", "Pele de salmão crocante com cream cheese, 8 peças", 28.90),
                    ("Hot Camarão", "Camarão empanado com cream cheese e cebolinha, 8 peças", 36.90),
                    ("Hot Banana", "Banana com chocolate e canela empanada, 8 peças", 26.90),
                ],
            },
            {
                "nome": "Temakis",
                "produtos": [
                    ("Temaki Salmão", "Cone de nori com salmão, arroz, cream cheese e cebolinha", 26.90),
                    ("Temaki Atum", "Cone de nori com atum fresco, arroz e gergelim", 28.90),
                    ("Temaki Camarão", "Cone com camarão empanado e molho tarê", 29.90),
                    ("Temaki Skin", "Cone com pele de salmão crocante e cream cheese", 24.90),
                ],
            },
            {
                "nome": "Bebidas",
                "produtos": [
                    ("Saquê Quente", "Saquê tradicional aquecido 180ml", 18.90),
                    ("Saquê Gelado", "Saquê premium gelado 180ml", 22.90),
                    ("Chá Verde", "Chá verde japonês 300ml", 8.90),
                    ("Cerveja Asahi", "Cerveja japonesa 330ml", 16.90),
                    ("Refrigerante Lata", "Coca-Cola, Guaraná ou Sprite", 6.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Combo Dupla",
                "descricao": "Combinado 30pç + 2 Saquês + 2 Hot Rolls",
                "preco_combo": 129.90,
                "preco_original": 158.60,
                "tipo_combo": "padrao",
            },
        ],
    },

    "acai": {
        "categorias": [
            {
                "nome": "Açaí Bowls",
                "produtos": [
                    ("Açaí 300ml", "Açaí puro batido na hora — adicione seus toppings favoritos", 14.90),
                    ("Açaí 500ml", "Açaí puro batido na hora — tamanho médio", 19.90),
                    ("Açaí 700ml", "Açaí puro batido na hora — tamanho grande", 24.90),
                    ("Açaí 1 Litro", "Açaí puro batido, serve até 2 pessoas", 32.90),
                    ("Bowl Tropical", "Açaí com banana, morango, granola e mel", 26.90),
                    ("Bowl Fitness", "Açaí com banana, aveia, whey protein e pasta de amendoim", 29.90),
                    ("Bowl Premium", "Açaí com frutas vermelhas, granola, leite ninho e nutella", 34.90),
                ],
            },
            {
                "nome": "Sorvetes",
                "produtos": [
                    ("Sorvete 1 Bola", "Escolha o sabor: chocolate, baunilha, morango ou creme", 8.90),
                    ("Sorvete 2 Bolas", "Duas bolas de sabores à escolha", 14.90),
                    ("Sorvete 3 Bolas", "Três bolas com calda e chantilly", 18.90),
                    ("Sundae", "Sorvete com calda quente de chocolate, chantilly e amendoim", 19.90),
                    ("Banana Split", "3 bolas de sorvete com banana, caldas e chantilly", 22.90),
                ],
            },
            {
                "nome": "Milkshakes",
                "produtos": [
                    ("Milkshake Chocolate", "Milkshake cremoso de chocolate 400ml", 16.90),
                    ("Milkshake Morango", "Milkshake de morango com pedaços 400ml", 16.90),
                    ("Milkshake Ovomaltine", "Milkshake com Ovomaltine crocante 400ml", 18.90),
                    ("Milkshake Nutella", "Milkshake com Nutella premium 400ml", 19.90),
                ],
            },
            {
                "nome": "Complementos",
                "produtos": [
                    ("Granola Extra", "Porção extra de granola crocante", 3.00),
                    ("Leite Ninho", "Porção extra de leite ninho", 3.50),
                    ("Nutella", "Porção extra de Nutella", 5.00),
                    ("Paçoca", "Porção extra de paçoca triturada", 3.00),
                    ("Morangos Frescos", "Porção extra de morangos frescos", 4.00),
                    ("Banana Fatiada", "Porção extra de banana fatiada", 2.50),
                    ("Whey Protein", "Dose de whey protein (chocolate ou baunilha)", 5.00),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Combo Verão",
                "descricao": "Açaí 500ml + 3 Complementos à escolha",
                "preco_combo": 24.90,
                "preco_original": 31.40,
                "tipo_combo": "padrao",
            },
            {
                "nome": "Combo Casal",
                "descricao": "2 Açaís 500ml + 4 Complementos + 2 Milkshakes",
                "preco_combo": 69.90,
                "preco_original": 85.80,
                "tipo_combo": "padrao",
            },
        ],
    },

    "bebidas": {
        "categorias": [
            {
                "nome": "Cervejas",
                "produtos": [
                    ("Skol Lata 350ml", "Cerveja Skol pilsen lata gelada", 4.49),
                    ("Brahma Lata 350ml", "Cerveja Brahma pilsen lata gelada", 4.49),
                    ("Heineken Long Neck", "Cerveja Heineken premium 330ml", 7.90),
                    ("Corona Long Neck", "Cerveja Corona Extra 330ml", 8.90),
                    ("Budweiser Long Neck", "Cerveja Budweiser 330ml", 6.90),
                    ("Stella Artois Long Neck", "Cerveja Stella Artois 330ml", 7.90),
                    ("Skol Litrão", "Cerveja Skol 1 litro retornável", 9.90),
                    ("Brahma Litrão", "Cerveja Brahma 1 litro retornável", 9.90),
                ],
            },
            {
                "nome": "Refrigerantes",
                "produtos": [
                    ("Coca-Cola 2L", "Coca-Cola original 2 litros", 11.90),
                    ("Coca-Cola Lata 350ml", "Coca-Cola lata gelada", 5.90),
                    ("Guaraná Antarctica 2L", "Guaraná Antarctica 2 litros", 9.90),
                    ("Fanta Laranja 2L", "Fanta Laranja 2 litros", 9.90),
                    ("Sprite 2L", "Sprite limão 2 litros", 9.90),
                    ("Coca-Cola Zero Lata", "Coca-Cola zero açúcar 350ml", 5.90),
                ],
            },
            {
                "nome": "Destilados",
                "produtos": [
                    ("Vodka Absolut 750ml", "Vodka Absolut Original importada", 69.90),
                    ("Whisky Red Label 1L", "Johnnie Walker Red Label", 89.90),
                    ("Cachaça 51 965ml", "Cachaça 51 tradicional", 12.90),
                    ("Gin Tanqueray 750ml", "Gin Tanqueray London Dry", 99.90),
                    ("Rum Bacardi 980ml", "Rum Bacardi carta branca", 39.90),
                ],
            },
            {
                "nome": "Águas e Sucos",
                "produtos": [
                    ("Água Mineral 500ml", "Água mineral sem gás", 3.00),
                    ("Água com Gás 500ml", "Água mineral com gás", 3.50),
                    ("Suco Del Valle 1L", "Sabores: uva, laranja, pêssego, maçã", 8.90),
                    ("Água de Coco 1L", "Água de coco natural", 9.90),
                ],
            },
            {
                "nome": "Energéticos e Isotônicos",
                "produtos": [
                    ("Red Bull 250ml", "Energético Red Bull original", 12.90),
                    ("Monster 473ml", "Energético Monster Energy", 11.90),
                    ("Gatorade 500ml", "Isotônico Gatorade sabores variados", 7.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Kit Churrasco",
                "descricao": "6 Cervejas Lata + 1 Refrigerante 2L",
                "preco_combo": 39.90,
                "preco_original": 50.84,
                "tipo_combo": "padrao",
            },
        ],
    },

    "esfiharia": {
        "categorias": [
            {
                "nome": "Esfihas Salgadas",
                "produtos": [
                    ("Esfiha Carne", "Carne moída temperada com especiarias árabes", 5.90),
                    ("Esfiha Frango", "Frango desfiado com tempero especial", 5.90),
                    ("Esfiha Queijo", "Mussarela derretida com orégano", 5.90),
                    ("Esfiha Calabresa", "Calabresa fatiada com cebola e queijo", 6.90),
                    ("Esfiha 4 Queijos", "Mussarela, provolone, catupiry e parmesão", 7.90),
                    ("Esfiha Beirute", "Carne, tomate, cebola e temperos árabes", 6.90),
                    ("Esfiha de Escarola", "Escarola refogada com alho e azeite", 5.90),
                ],
            },
            {
                "nome": "Esfihas Doces",
                "produtos": [
                    ("Esfiha Chocolate", "Chocolate ao leite cremoso", 5.90),
                    ("Esfiha Doce de Leite", "Doce de leite artesanal", 5.90),
                    ("Esfiha Romeu e Julieta", "Goiabada com queijo minas", 6.90),
                    ("Esfiha Nutella", "Nutella premium com morango", 7.90),
                ],
            },
            {
                "nome": "Kibes",
                "produtos": [
                    ("Kibe Frito", "Kibe de carne frito crocante, unidade", 6.90),
                    ("Kibe Assado", "Kibe assado tradicional, unidade", 6.90),
                    ("Kibe de Queijo", "Kibe frito recheado com queijo", 7.90),
                    ("Kibe Cru", "Kibe cru com azeite e hortelã", 12.90),
                ],
            },
            {
                "nome": "Beirutes",
                "produtos": [
                    ("Beirute de Carne", "Pão sírio com carne, alface, tomate e molho tahine", 22.90),
                    ("Beirute de Frango", "Pão sírio com frango desfiado e salada", 21.90),
                    ("Beirute Misto", "Pão sírio com presunto, queijo e salada", 19.90),
                ],
            },
            {
                "nome": "Bebidas",
                "produtos": [
                    ("Suco de Laranja", "Suco natural de laranja 300ml", 8.90),
                    ("Refrigerante Lata", "Coca-Cola, Guaraná ou Sprite 350ml", 6.90),
                    ("Chá Mate", "Chá mate gelado com limão 300ml", 6.90),
                    ("Água Mineral", "Água mineral 500ml", 4.00),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Combo 10 Esfihas",
                "descricao": "10 esfihas salgadas sortidas + 1 Refrigerante 2L",
                "preco_combo": 54.90,
                "preco_original": 70.90,
                "tipo_combo": "padrao",
            },
            {
                "nome": "Combo Árabe",
                "descricao": "1 Beirute + 2 Kibes + 1 Refrigerante",
                "preco_combo": 34.90,
                "preco_original": 43.60,
                "tipo_combo": "padrao",
            },
        ],
    },

    "restaurante": {
        "categorias": [
            {
                "nome": "Pratos Executivos",
                "produtos": [
                    ("Filé Grelhado", "Filé mignon grelhado com arroz, feijão, salada e fritas", 39.90),
                    ("Frango à Parmegiana", "Frango empanado com queijo e molho, arroz e fritas", 34.90),
                    ("Picanha na Chapa", "Picanha grelhada com arroz, farofa, vinagrete e fritas", 49.90),
                    ("Peixe Grelhado", "Filé de tilápia grelhado com legumes e arroz", 36.90),
                    ("Strogonoff de Frango", "Strogonoff cremoso com arroz, batata palha e salada", 32.90),
                    ("Feijoada Completa", "Feijoada com arroz, couve, farofa, torresmo e laranja", 38.90),
                ],
            },
            {
                "nome": "Massas",
                "produtos": [
                    ("Espaguete à Bolonhesa", "Espaguete com molho bolonhesa caseiro e parmesão", 28.90),
                    ("Lasanha de Carne", "Lasanha de carne moída com molho branco e queijo", 34.90),
                    ("Nhoque ao Sugo", "Nhoque de batata com molho sugo e manjericão", 26.90),
                    ("Fettuccine Alfredo", "Fettuccine com molho alfredo cremoso e frango", 32.90),
                ],
            },
            {
                "nome": "Carnes",
                "produtos": [
                    ("Costela no Bafo", "Costela cozida lentamente com mandioca e salada", 52.90),
                    ("Bife à Cavalo", "Bife de alcatra com ovo frito, arroz e feijão", 35.90),
                    ("Escalope ao Madeira", "Medalhões de filé mignon ao molho madeira", 48.90),
                    ("Churrasco Misto", "Mix de carnes grelhadas com acompanhamentos", 59.90),
                ],
            },
            {
                "nome": "Saladas",
                "produtos": [
                    ("Salada Caesar", "Alface romana, croutons, parmesão e molho caesar com frango", 24.90),
                    ("Salada Tropical", "Mix de folhas, manga, abacaxi e molho de maracujá", 22.90),
                    ("Salada Caprese", "Tomate, mussarela de búfala, manjericão e azeite", 26.90),
                ],
            },
            {
                "nome": "Sobremesas",
                "produtos": [
                    ("Pudim de Leite", "Pudim de leite condensado caseiro", 12.90),
                    ("Mousse de Maracujá", "Mousse cremosa de maracujá", 10.90),
                    ("Sorvete 2 Bolas", "Sabores: chocolate, baunilha, morango ou creme", 14.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Segunda - Feijoada",
                "descricao": "Feijoada completa + Caipirinha de limão",
                "preco_combo": 39.90,
                "preco_original": 52.80,
                "tipo_combo": "do_dia",
                "dia_semana": 0,
            },
            {
                "nome": "Terça - Filé Grelhado",
                "descricao": "Filé grelhado completo + Suco natural",
                "preco_combo": 36.90,
                "preco_original": 48.80,
                "tipo_combo": "do_dia",
                "dia_semana": 1,
            },
            {
                "nome": "Quarta - Massa",
                "descricao": "Lasanha de carne + Refrigerante",
                "preco_combo": 32.90,
                "preco_original": 41.80,
                "tipo_combo": "do_dia",
                "dia_semana": 2,
            },
            {
                "nome": "Quinta - Picanha",
                "descricao": "Picanha na chapa + Cerveja artesanal",
                "preco_combo": 49.90,
                "preco_original": 63.80,
                "tipo_combo": "do_dia",
                "dia_semana": 3,
            },
            {
                "nome": "Sexta - Peixe",
                "descricao": "Peixe grelhado com legumes + Suco natural",
                "preco_combo": 34.90,
                "preco_original": 45.80,
                "tipo_combo": "do_dia",
                "dia_semana": 4,
            },
            {
                "nome": "Sábado - Churrasco",
                "descricao": "Churrasco misto completo + Cerveja long neck",
                "preco_combo": 55.90,
                "preco_original": 73.80,
                "tipo_combo": "do_dia",
                "dia_semana": 5,
            },
            {
                "nome": "Domingo - Strogonoff",
                "descricao": "Strogonoff de frango + Suco natural + Pudim",
                "preco_combo": 42.90,
                "preco_original": 56.70,
                "tipo_combo": "do_dia",
                "dia_semana": 6,
            },
            {
                "nome": "Combo Família",
                "descricao": "2 Pratos Executivos + 2 Sobremesas + 1 Refrigerante 2L",
                "preco_combo": 89.90,
                "preco_original": 112.60,
                "tipo_combo": "padrao",
            },
        ],
    },

    "salgados": {
        "categorias": [
            {
                "nome": "Salgados Assados",
                "produtos": [
                    ("Coxinha Assada", "Coxinha de frango assada crocante, unidade", 5.90),
                    ("Empada de Frango", "Empada caseira de frango com catupiry", 6.90),
                    ("Enroladinho de Salsicha", "Massa folhada com salsicha, unidade", 4.90),
                    ("Pão de Queijo", "Pão de queijo mineiro, unidade", 4.50),
                    ("Croissant Misto", "Croissant recheado com presunto e queijo", 7.90),
                    ("Esfiha de Carne", "Esfiha aberta de carne temperada", 5.90),
                ],
            },
            {
                "nome": "Salgados Fritos",
                "produtos": [
                    ("Coxinha de Frango", "Coxinha cremosa de frango com catupiry, unidade", 5.90),
                    ("Risole de Presunto", "Risole crocante de presunto e queijo, unidade", 5.50),
                    ("Bolinha de Queijo", "Bolinha de queijo frita crocante, unidade", 4.90),
                    ("Pastel de Carne", "Pastel frito de carne moída, unidade", 6.90),
                    ("Pastel de Queijo", "Pastel frito de queijo mussarela, unidade", 6.90),
                    ("Kibe Frito", "Kibe de carne frito crocante, unidade", 5.90),
                ],
            },
            {
                "nome": "Doces",
                "produtos": [
                    ("Brigadeiro Gourmet", "Brigadeiro artesanal, unidade", 4.50),
                    ("Beijinho", "Beijinho de coco, unidade", 4.50),
                    ("Cajuzinho", "Cajuzinho de amendoim, unidade", 4.50),
                    ("Trufa de Chocolate", "Trufa de chocolate belga, unidade", 6.90),
                    ("Mini Churros", "Mini churros recheado com doce de leite, 5 unidades", 12.90),
                    ("Bolo de Pote", "Bolo no pote: chocolate, ninho ou red velvet", 12.90),
                ],
            },
            {
                "nome": "Tortas",
                "produtos": [
                    ("Torta de Frango", "Torta de frango com catupiry, fatia", 9.90),
                    ("Torta de Palmito", "Torta de palmito com mussarela, fatia", 10.90),
                    ("Quiche de Bacon", "Quiche de bacon com queijo gruyère, fatia", 11.90),
                ],
            },
            {
                "nome": "Bebidas",
                "produtos": [
                    ("Café Expresso", "Café expresso curto ou longo", 5.90),
                    ("Cappuccino", "Cappuccino cremoso 200ml", 8.90),
                    ("Suco Natural", "Laranja, limão ou maracujá 300ml", 8.90),
                    ("Refrigerante Lata", "Coca-Cola, Guaraná ou Sprite 350ml", 6.90),
                ],
            },
        ],
        "combos": [
            {
                "nome": "Kit Festa 10 Pessoas",
                "descricao": "30 salgados assados + 30 salgados fritos + 20 docinhos",
                "preco_combo": 89.90,
                "preco_original": 130.00,
                "tipo_combo": "kit_festa",
                "quantidade_pessoas": 10,
            },
            {
                "nome": "Kit Festa 20 Pessoas",
                "descricao": "60 salgados assados + 60 salgados fritos + 40 docinhos + 1 bolo",
                "preco_combo": 169.90,
                "preco_original": 250.00,
                "tipo_combo": "kit_festa",
                "quantidade_pessoas": 20,
            },
            {
                "nome": "Kit Festa 50 Pessoas",
                "descricao": "150 salgados assados + 150 salgados fritos + 100 docinhos + 2 bolos",
                "preco_combo": 399.90,
                "preco_original": 600.00,
                "tipo_combo": "kit_festa",
                "quantidade_pessoas": 50,
            },
            {
                "nome": "Combo Lanche",
                "descricao": "3 Salgados (assado/frito à escolha) + 1 Suco Natural",
                "preco_combo": 19.90,
                "preco_original": 26.60,
                "tipo_combo": "padrao",
            },
        ],
    },
}


def criar_produtos_padrao(session, restaurante_id: int, tipo_restaurante: str) -> int:
    """
    Cria produtos padrão para um restaurante recém-criado.

    Chamado automaticamente ao criar um novo restaurante via SuperAdmin.
    Pula se o restaurante já tiver produtos.

    Args:
        session: Sessão SQLAlchemy ativa
        restaurante_id: ID do restaurante
        tipo_restaurante: Tipo (pizzaria, hamburgueria, sushi, acai, bebidas,
                          esfiharia, restaurante, salgados)

    Returns:
        Número de produtos criados
    """
    # Verificar se já tem produtos
    count_existente = session.query(Produto).filter(
        Produto.restaurante_id == restaurante_id
    ).count()
    if count_existente > 0:
        return 0

    # Obter dados para o tipo
    dados = DADOS_PRODUTOS.get(tipo_restaurante)
    if not dados:
        return 0

    # Buscar categorias já criadas (em ordem)
    categorias_db = session.query(CategoriaMenu).filter(
        CategoriaMenu.restaurante_id == restaurante_id,
        CategoriaMenu.ativo == True
    ).order_by(CategoriaMenu.ordem_exibicao).all()

    if not categorias_db:
        return 0

    # Mapear pelo índice: dados["categorias"][i] → categorias_db[i]
    total_criados = 0
    produto_ids = []

    for i, cat_dados in enumerate(dados["categorias"]):
        if i >= len(categorias_db):
            break
        categoria_id = categorias_db[i].id

        for j, (nome, descricao, preco) in enumerate(cat_dados["produtos"]):
            produto = Produto(
                restaurante_id=restaurante_id,
                categoria_id=categoria_id,
                nome=nome,
                descricao=descricao,
                preco=preco,
                disponivel=True,
                destaque=(j == 0),  # Primeiro de cada categoria é destaque
                ordem_exibicao=j + 1,
            )
            session.add(produto)
            session.flush()
            produto_ids.append(produto.id)
            total_criados += 1

            # Criar variações se houver
            variacoes = cat_dados.get("variacoes", {})
            for tipo_var, lista_var in variacoes.items():
                for ordem_v, (nome_v, preco_add) in enumerate(lista_var, start=1):
                    session.add(VariacaoProduto(
                        produto_id=produto.id,
                        tipo_variacao=tipo_var,
                        nome=nome_v,
                        preco_adicional=preco_add,
                        ordem=ordem_v,
                        ativo=True,
                    ))

    # Criar combos
    for k, combo_dados in enumerate(dados.get("combos", [])):
        combo = Combo(
            restaurante_id=restaurante_id,
            nome=combo_dados["nome"],
            descricao=combo_dados["descricao"],
            preco_combo=combo_dados["preco_combo"],
            preco_original=combo_dados["preco_original"],
            ativo=True,
            ordem_exibicao=k + 1,
            tipo_combo=combo_dados.get("tipo_combo", "padrao"),
            dia_semana=combo_dados.get("dia_semana"),
            quantidade_pessoas=combo_dados.get("quantidade_pessoas"),
            data_inicio=datetime.utcnow() - timedelta(days=1),
            data_fim=datetime.utcnow() + timedelta(days=365),
        )
        session.add(combo)
        session.flush()

        # Adicionar itens ao combo (até 3 produtos)
        if produto_ids:
            import random
            num_itens = min(3, len(produto_ids))
            itens = random.sample(produto_ids, num_itens)
            for prod_id in itens:
                session.add(ComboItem(
                    combo_id=combo.id,
                    produto_id=prod_id,
                    quantidade=1,
                ))

    session.flush()
    return total_criados
