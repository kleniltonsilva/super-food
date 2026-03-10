"""
Seed: Criar 1 restaurante de cada tipo para testes visuais dos layouts temáticos.

Cria 8 restaurantes (1 por tipo) com:
- SiteConfig com tipo_restaurante e cores corretas
- Categorias relevantes ao tipo
- Produtos com descrições e preços realistas
- Combos (incluindo do_dia para restaurante e kit_festa para salgados)

Uso: python -m database.seed.seed_011_restaurantes_por_tipo

Super Food SaaS - Sprint 9.14 - Testes Visuais
"""

import sys
import os
import hashlib
import random
import string
from datetime import datetime, timedelta

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import (
    Restaurante, ConfigRestaurante, SiteConfig,
    CategoriaMenu, Produto, Combo, ComboItem, BairroEntrega
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")

# ==================== DADOS POR TIPO ====================

TIPOS = {
    "pizzaria": {
        "nome": "Don Massimo Pizzaria",
        "nome_fantasia": "Don Massimo",
        "email": "teste-pizzaria@superfood.test",
        "telefone": "11987654321",
        "cor_primaria": "#e4002e",
        "cor_secundaria": "#ffefef",
        "whatsapp": "5511987654321",
        "categorias": [
            {
                "nome": "Pizzas Tradicionais",
                "emoji": "🍕",
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
            },
            {
                "nome": "Pizzas Especiais",
                "emoji": "⭐",
                "produtos": [
                    ("Pizza do Chef", "Rúcula, tomate seco, parmesão e presunto de Parma", 59.90),
                    ("Camarão", "Camarões ao alho, mussarela e catupiry com cebolinha", 65.90),
                    ("Filé Mignon", "Filé mignon em tiras, cebola roxa e cream cheese", 62.90),
                    ("Salmão", "Salmão defumado, cream cheese, alcaparras e cebolinha", 69.90),
                ],
            },
            {
                "nome": "Pizzas Doces",
                "emoji": "🍫",
                "produtos": [
                    ("Chocolate", "Chocolate ao leite com granulado e leite condensado", 38.90),
                    ("Banana com Canela", "Banana, canela, leite condensado e mussarela", 36.90),
                    ("Brigadeiro", "Brigadeiro artesanal com granulado belga", 39.90),
                    ("Romeu e Julieta", "Goiabada cremosa com queijo minas derretido", 37.90),
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🥤",
                "produtos": [
                    ("Coca-Cola 2L", "Coca-Cola original 2 litros", 14.90),
                    ("Guaraná Antarctica 2L", "Guaraná Antarctica 2 litros", 12.90),
                    ("Suco Natural 500ml", "Laranja, limão, maracujá ou abacaxi", 9.90),
                    ("Água Mineral 500ml", "Com ou sem gás", 4.90),
                ],
            },
            {
                "nome": "Bordas Recheadas",
                "emoji": "🧀",
                "produtos": [
                    ("Borda Catupiry", "Borda recheada com catupiry original", 8.90),
                    ("Borda Cheddar", "Borda recheada com cheddar cremoso", 8.90),
                    ("Borda Chocolate", "Borda recheada com chocolate ao leite", 9.90),
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
                "descricao": "1 Pizza Grande + 1 Borda Recheada + 2 Refrigerantes",
                "preco_combo": 59.90,
                "preco_original": 72.70,
                "tipo_combo": "padrao",
            },
        ],
    },

    "hamburgueria": {
        "nome": "Smash Bros Burgers",
        "nome_fantasia": "Smash Bros",
        "email": "teste-hamburgueria@superfood.test",
        "telefone": "11987654322",
        "cor_primaria": "#ffcd00",
        "cor_secundaria": "#161616",
        "whatsapp": "5511987654322",
        "categorias": [
            {
                "nome": "Burgers Clássicos",
                "emoji": "🍔",
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
                "emoji": "👑",
                "produtos": [
                    ("Wagyu Burger", "Blend wagyu 180g, gruyère, rúcula, tomate confit e aioli trufado", 52.90),
                    ("Pulled Pork", "Carne de porco desfiada 12h, coleslaw e molho barbecue defumado", 42.90),
                    ("Blue Cheese", "Blend 180g, gorgonzola, cebola caramelizada no vinho e rúcula", 45.90),
                    ("Chicken Crispy", "Frango empanado crocante, maionese de ervas e salada", 36.90),
                ],
            },
            {
                "nome": "Acompanhamentos",
                "emoji": "🍟",
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
                "emoji": "🥤",
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
                "emoji": "🍰",
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
        "nome": "Sakura Sushi House",
        "nome_fantasia": "Sakura Sushi",
        "email": "teste-sushi@superfood.test",
        "telefone": "11987654323",
        "cor_primaria": "#a40000",
        "cor_secundaria": "#1d1c1c",
        "whatsapp": "5511987654323",
        "categorias": [
            {
                "nome": "Combinados",
                "emoji": "🍱",
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
                "emoji": "🐟",
                "produtos": [
                    ("Sashimi Salmão 5pç", "Fatias frescas de salmão norueguês", 24.90),
                    ("Sashimi Atum 5pç", "Fatias de atum fresco selecionado", 29.90),
                    ("Sashimi Peixe Branco 5pç", "Peixe branco fresco do dia", 22.90),
                    ("Sashimi Polvo 5pç", "Polvo macio ao ponto", 34.90),
                ],
            },
            {
                "nome": "Hot Rolls",
                "emoji": "🔥",
                "produtos": [
                    ("Hot Philadelphia", "Salmão, cream cheese empanado e frito, 8 peças", 32.90),
                    ("Hot Skin", "Pele de salmão crocante com cream cheese, 8 peças", 28.90),
                    ("Hot Camarão", "Camarão empanado com cream cheese e cebolinha, 8 peças", 36.90),
                    ("Hot Banana", "Banana com chocolate e canela empanada, 8 peças", 26.90),
                ],
            },
            {
                "nome": "Temakis",
                "emoji": "🌮",
                "produtos": [
                    ("Temaki Salmão", "Cone de nori com salmão, arroz, cream cheese e cebolinha", 26.90),
                    ("Temaki Atum", "Cone de nori com atum fresco, arroz e gergelim", 28.90),
                    ("Temaki Camarão", "Cone com camarão empanado e molho tarê", 29.90),
                    ("Temaki Skin", "Cone com pele de salmão crocante e cream cheese", 24.90),
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🍵",
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
        "nome": "Açaí Tropical Point",
        "nome_fantasia": "Tropical Point",
        "email": "teste-acai@superfood.test",
        "telefone": "11987654324",
        "cor_primaria": "#61269c",
        "cor_secundaria": "#2a7e3f",
        "whatsapp": "5511987654324",
        "categorias": [
            {
                "nome": "Açaí Bowls",
                "emoji": "🫐",
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
                "emoji": "🍦",
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
                "emoji": "🥤",
                "produtos": [
                    ("Milkshake Chocolate", "Milkshake cremoso de chocolate 400ml", 16.90),
                    ("Milkshake Morango", "Milkshake de morango com pedaços 400ml", 16.90),
                    ("Milkshake Ovomaltine", "Milkshake com Ovomaltine crocante 400ml", 18.90),
                    ("Milkshake Nutella", "Milkshake com Nutella premium 400ml", 19.90),
                ],
            },
            {
                "nome": "Complementos",
                "emoji": "🥜",
                "produtos": [
                    ("Granola", "Porção extra de granola crocante", 3.00),
                    ("Leite Ninho", "Porção extra de leite ninho", 3.50),
                    ("Nutella", "Porção extra de Nutella", 5.00),
                    ("Paçoca", "Porção extra de paçoca triturada", 3.00),
                    ("Morango", "Porção extra de morangos frescos", 4.00),
                    ("Banana", "Porção extra de banana fatiada", 2.50),
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
        "nome": "Gelou Distribuidora",
        "nome_fantasia": "Gelou Bebidas",
        "email": "teste-bebidas@superfood.test",
        "telefone": "11987654325",
        "cor_primaria": "#e50e16",
        "cor_secundaria": "#f6f5f5",
        "whatsapp": "5511987654325",
        "categorias": [
            {
                "nome": "Cervejas",
                "emoji": "🍺",
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
                "emoji": "🥤",
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
                "emoji": "🥃",
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
                "emoji": "💧",
                "produtos": [
                    ("Água Mineral 500ml", "Água mineral sem gás", 3.00),
                    ("Água com Gás 500ml", "Água mineral com gás", 3.50),
                    ("Suco Del Valle 1L", "Sabores: uva, laranja, pêssego, maçã", 8.90),
                    ("Água de Coco 1L", "Água de coco natural", 9.90),
                ],
            },
            {
                "nome": "Energéticos e Isotônicos",
                "emoji": "⚡",
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
                "descricao": "6 Cervejas Lata + 1 Refrigerante 2L + 1 Gelo 5kg",
                "preco_combo": 39.90,
                "preco_original": 50.84,
                "tipo_combo": "padrao",
            },
        ],
    },

    "esfiharia": {
        "nome": "Habibs da Vila",
        "nome_fantasia": "Habibs da Vila",
        "email": "teste-esfiharia@superfood.test",
        "telefone": "11987654326",
        "cor_primaria": "#d4880f",
        "cor_secundaria": "#5c3310",
        "whatsapp": "5511987654326",
        "categorias": [
            {
                "nome": "Esfihas Salgadas",
                "emoji": "🥟",
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
                "emoji": "🍯",
                "produtos": [
                    ("Esfiha Chocolate", "Chocolate ao leite cremoso", 5.90),
                    ("Esfiha Doce de Leite", "Doce de leite artesanal", 5.90),
                    ("Esfiha Romeu e Julieta", "Goiabada com queijo minas", 6.90),
                    ("Esfiha Nutella", "Nutella premium com morango", 7.90),
                ],
            },
            {
                "nome": "Kibes",
                "emoji": "🫓",
                "produtos": [
                    ("Kibe Frito", "Kibe de carne frito crocante, unidade", 6.90),
                    ("Kibe Assado", "Kibe assado tradicional, unidade", 6.90),
                    ("Kibe de Queijo", "Kibe frito recheado com queijo", 7.90),
                    ("Kibe Cru", "Kibe cru com azeite e hortelã", 12.90),
                ],
            },
            {
                "nome": "Beirutes",
                "emoji": "🥖",
                "produtos": [
                    ("Beirute de Carne", "Pão sírio com carne, alface, tomate e molho tahine", 22.90),
                    ("Beirute de Frango", "Pão sírio com frango desfiado e salada", 21.90),
                    ("Beirute Misto", "Pão sírio com presunto, queijo e salada", 19.90),
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🥤",
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
        "nome": "Cantina da Praça",
        "nome_fantasia": "Cantina da Praça",
        "email": "teste-restaurante@superfood.test",
        "telefone": "11987654327",
        "cor_primaria": "#ff990a",
        "cor_secundaria": "#2b2723",
        "whatsapp": "5511987654327",
        "categorias": [
            {
                "nome": "Pratos Executivos",
                "emoji": "🍽️",
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
                "emoji": "🍝",
                "produtos": [
                    ("Espaguete à Bolonhesa", "Espaguete com molho bolonhesa caseiro e parmesão", 28.90),
                    ("Lasanha de Carne", "Lasanha de carne moída com molho branco e queijo", 34.90),
                    ("Nhoque ao Sugo", "Nhoque de batata com molho sugo e manjericão", 26.90),
                    ("Fettuccine Alfredo", "Fettuccine com molho alfredo cremoso e frango", 32.90),
                ],
            },
            {
                "nome": "Carnes",
                "emoji": "🥩",
                "produtos": [
                    ("Costela no Bafo", "Costela cozida lentamente com mandioca e salada", 52.90),
                    ("Bife à Cavalo", "Bife de alcatra com ovo frito, arroz e feijão", 35.90),
                    ("Escalope ao Madeira", "Medalhões de filé mignon ao molho madeira", 48.90),
                    ("Churrasco Misto", "Mix de carnes grelhadas com acompanhamentos", 59.90),
                ],
            },
            {
                "nome": "Saladas",
                "emoji": "🥗",
                "produtos": [
                    ("Salada Caesar", "Alface romana, croutons, parmesão e molho caesar com frango", 24.90),
                    ("Salada Tropical", "Mix de folhas, manga, abacaxi e molho de maracujá", 22.90),
                    ("Salada Caprese", "Tomate, mussarela de búfala, manjericão e azeite", 26.90),
                ],
            },
            {
                "nome": "Sobremesas",
                "emoji": "🍮",
                "produtos": [
                    ("Pudim de Leite", "Pudim de leite condensado caseiro", 12.90),
                    ("Mousse de Maracujá", "Mousse cremosa de maracujá", 10.90),
                    ("Sorvete 2 Bolas", "Sabores: chocolate, baunilha, morango ou creme", 14.90),
                ],
            },
        ],
        "combos": [
            # Combos do dia (tipo do_dia) — um para cada dia da semana
            {
                "nome": "Segunda - Feijoada",
                "descricao": "Feijoada completa + Caipirinha de limão",
                "preco_combo": 39.90,
                "preco_original": 52.80,
                "tipo_combo": "do_dia",
                "dia_semana": 0,  # Segunda
            },
            {
                "nome": "Terça - Filé Grelhado",
                "descricao": "Filé grelhado completo + Suco natural",
                "preco_combo": 36.90,
                "preco_original": 48.80,
                "tipo_combo": "do_dia",
                "dia_semana": 1,  # Terça
            },
            {
                "nome": "Quarta - Massa",
                "descricao": "Lasanha de carne + Refrigerante",
                "preco_combo": 32.90,
                "preco_original": 41.80,
                "tipo_combo": "do_dia",
                "dia_semana": 2,  # Quarta
            },
            {
                "nome": "Quinta - Picanha",
                "descricao": "Picanha na chapa + Cerveja artesanal",
                "preco_combo": 49.90,
                "preco_original": 63.80,
                "tipo_combo": "do_dia",
                "dia_semana": 3,  # Quinta
            },
            {
                "nome": "Sexta - Peixe",
                "descricao": "Peixe grelhado com legumes + Suco natural",
                "preco_combo": 34.90,
                "preco_original": 45.80,
                "tipo_combo": "do_dia",
                "dia_semana": 4,  # Sexta
            },
            {
                "nome": "Sábado - Churrasco",
                "descricao": "Churrasco misto completo + Cerveja long neck",
                "preco_combo": 55.90,
                "preco_original": 73.80,
                "tipo_combo": "do_dia",
                "dia_semana": 5,  # Sábado
            },
            {
                "nome": "Domingo - Strogonoff",
                "descricao": "Strogonoff de frango + Suco natural + Pudim",
                "preco_combo": 42.90,
                "preco_original": 56.70,
                "tipo_combo": "do_dia",
                "dia_semana": 6,  # Domingo
            },
            # Combo padrão
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
        "nome": "Delícias da Vovó",
        "nome_fantasia": "Delícias da Vovó",
        "email": "teste-salgados@superfood.test",
        "telefone": "11987654328",
        "cor_primaria": "#ff883a",
        "cor_secundaria": "#fff5eb",
        "whatsapp": "5511987654328",
        "categorias": [
            {
                "nome": "Salgados Assados",
                "emoji": "🥐",
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
                "emoji": "🍤",
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
                "emoji": "🍬",
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
                "emoji": "🥧",
                "produtos": [
                    ("Torta de Frango", "Torta de frango com catupiry, fatia", 9.90),
                    ("Torta de Palmito", "Torta de palmito com mussarela, fatia", 10.90),
                    ("Quiche de Bacon", "Quiche de bacon com queijo gruyère, fatia", 11.90),
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "☕",
                "produtos": [
                    ("Café Expresso", "Café expresso curto ou longo", 5.90),
                    ("Cappuccino", "Cappuccino cremoso 200ml", 8.90),
                    ("Suco Natural", "Laranja, limão ou maracujá 300ml", 8.90),
                    ("Refrigerante Lata", "Coca-Cola, Guaraná ou Sprite 350ml", 6.90),
                ],
            },
        ],
        "combos": [
            # Kits festa (tipo kit_festa)
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
                "descricao": "150 salgados assados + 150 salgados fritos + 100 docinhos + 2 bolos + 5 refrigerantes 2L",
                "preco_combo": 399.90,
                "preco_original": 600.00,
                "tipo_combo": "kit_festa",
                "quantidade_pessoas": 50,
            },
            # Combo padrão
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

# Bairros padrão para todos
BAIRROS_PADRAO = [
    ("Centro", 5.00, 25),
    ("Jardim América", 7.00, 35),
    ("Vila Nova", 6.00, 30),
    ("Bela Vista", 8.00, 40),
    ("Moema", 9.00, 45),
]


def gerar_codigo_acesso():
    """Gera codigo de 8 chars unico"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


def criar_restaurante_tipo(db, tipo: str, dados: dict, codigos_usados: set):
    """Cria 1 restaurante completo de um tipo específico"""
    # Gerar código único
    codigo = gerar_codigo_acesso()
    while codigo in codigos_usados:
        codigo = gerar_codigo_acesso()
    codigos_usados.add(codigo)

    # Verificar se já existe (por email)
    existente = db.query(Restaurante).filter(Restaurante.email == dados["email"]).first()
    if existente:
        print(f"  [{tipo}] Já existe: {dados['email']} (código: {existente.codigo_acesso})")
        return existente

    # Criar restaurante
    restaurante = Restaurante(
        nome=dados["nome"],
        nome_fantasia=dados["nome_fantasia"],
        email=dados["email"],
        senha=hash_senha("123456"),
        telefone=dados["telefone"],
        endereco_completo="Rua dos Testes, 100, Centro, São Paulo, SP, 01310-100",
        cidade="São Paulo",
        estado="SP",
        cep="01310-100",
        latitude=-23.550520,
        longitude=-46.633308,
        codigo_acesso=codigo,
        plano="premium",
        valor_plano=599.90,
        limite_motoboys=999,
        ativo=True,
        status="ativo",
        data_vencimento=datetime.now() + timedelta(days=365),
    )
    db.add(restaurante)
    db.flush()
    rid = restaurante.id

    # ConfigRestaurante
    config = ConfigRestaurante(
        restaurante_id=rid,
        status_atual="aberto",
        modo_despacho="auto_economico",
        raio_entrega_km=15.0,
        tempo_medio_preparo=30,
        despacho_automatico=True,
        taxa_entrega_base=5.00,
        distancia_base_km=3.0,
        taxa_km_extra=1.50,
        valor_base_motoboy=5.00,
        valor_km_extra_motoboy=1.00,
        taxa_diaria=50.0,
        valor_lanche=15.0,
        max_pedidos_por_rota=5,
        permitir_ver_saldo_motoboy=True,
        horario_abertura="10:00",
        horario_fechamento="23:00",
        dias_semana_abertos="seg,ter,qua,qui,sex,sab,dom",
    )
    db.add(config)

    # SiteConfig
    site_config = SiteConfig(
        restaurante_id=rid,
        site_ativo=True,
        tipo_restaurante=tipo,
        tema_cor_primaria=dados["cor_primaria"],
        tema_cor_secundaria=dados["cor_secundaria"],
        whatsapp_numero=dados.get("whatsapp"),
        whatsapp_ativo=True,
        whatsapp_mensagem_padrao=f"Olá! Gostaria de fazer um pedido no {dados['nome_fantasia']}.",
        pedido_minimo=15.00,
        tempo_entrega_estimado=45,
        tempo_retirada_estimado=20,
        aceita_dinheiro=True,
        aceita_cartao=True,
        aceita_pix=True,
        aceita_vale_refeicao=False,
    )
    db.add(site_config)

    # Categorias e Produtos
    produto_ids = []  # Para usar nos combos
    for i, cat_data in enumerate(dados["categorias"]):
        categoria = CategoriaMenu(
            restaurante_id=rid,
            nome=cat_data["nome"],
            icone=cat_data.get("emoji", "📦"),
            ordem_exibicao=i + 1,
            ativo=True,
        )
        db.add(categoria)
        db.flush()

        for j, (nome_prod, descricao, preco) in enumerate(cat_data["produtos"]):
            produto = Produto(
                restaurante_id=rid,
                categoria_id=categoria.id,
                nome=nome_prod,
                descricao=descricao,
                preco=preco,
                disponivel=True,
                destaque=(j == 0),  # Primeiro produto de cada categoria é destaque
                ordem_exibicao=j + 1,
            )
            db.add(produto)
            db.flush()
            produto_ids.append(produto.id)

    # Combos
    for k, combo_data in enumerate(dados.get("combos", [])):
        combo = Combo(
            restaurante_id=rid,
            nome=combo_data["nome"],
            descricao=combo_data["descricao"],
            preco_combo=combo_data["preco_combo"],
            preco_original=combo_data["preco_original"],
            ativo=True,
            ordem_exibicao=k + 1,
            tipo_combo=combo_data.get("tipo_combo", "padrao"),
            dia_semana=combo_data.get("dia_semana"),
            quantidade_pessoas=combo_data.get("quantidade_pessoas"),
            data_inicio=datetime.now() - timedelta(days=30),
            data_fim=datetime.now() + timedelta(days=365),
        )
        db.add(combo)
        db.flush()

        # Adicionar 2-3 itens do combo (produtos aleatórios do restaurante)
        if produto_ids:
            num_itens = min(3, len(produto_ids))
            itens_selecionados = random.sample(produto_ids, num_itens)
            for prod_id in itens_selecionados:
                combo_item = ComboItem(
                    combo_id=combo.id,
                    produto_id=prod_id,
                    quantidade=1,
                )
                db.add(combo_item)

    # Bairros
    for nome_bairro, taxa, tempo in BAIRROS_PADRAO:
        bairro = BairroEntrega(
            restaurante_id=rid,
            nome=nome_bairro,
            taxa_entrega=taxa,
            tempo_estimado_min=tempo,
            ativo=True,
        )
        db.add(bairro)

    db.commit()
    print(f"  [{tipo}] Criado: {dados['nome_fantasia']} | email: {dados['email']} | senha: 123456 | código: {codigo}")
    return restaurante


def main():
    print(f"Conectando ao banco: {DATABASE_URL[:50]}...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Coletar códigos existentes
    codigos_usados = set(
        r[0] for r in db.query(Restaurante.codigo_acesso).all()
    )

    print(f"\n{'='*60}")
    print("SEED: 1 Restaurante de Cada Tipo (8 tipos)")
    print(f"{'='*60}\n")

    total_criados = 0
    resultados = []

    for tipo, dados in TIPOS.items():
        rest = criar_restaurante_tipo(db, tipo, dados, codigos_usados)
        if rest:
            total_criados += 1
            resultados.append({
                "tipo": tipo,
                "nome": dados["nome_fantasia"],
                "email": dados["email"],
                "codigo": rest.codigo_acesso,
            })

    print(f"\n{'='*60}")
    print(f"Total: {total_criados} restaurantes")
    print(f"{'='*60}\n")

    # Tabela resumo
    print(f"{'Tipo':<15} {'Nome':<25} {'Email':<35} {'Código':<10}")
    print("-" * 85)
    for r in resultados:
        print(f"{r['tipo']:<15} {r['nome']:<25} {r['email']:<35} {r['codigo']:<10}")

    print(f"\nSenha padrão para todos: 123456")
    print(f"Acesso site: /cliente/{{codigo_acesso}}")
    print(f"Acesso painel: /admin (login com email + senha)")

    db.close()


if __name__ == "__main__":
    main()
