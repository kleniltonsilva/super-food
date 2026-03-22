"""
Seed: Criar 1 restaurante de cada tipo para testes visuais dos layouts temáticos.

Cria 8 restaurantes (1 por tipo) com:
- SiteConfig com tipo_restaurante e cores corretas
- Categorias relevantes ao tipo
- Produtos com descrições, preços, imagens e ingredientes
- Variações de produto (tamanhos, bordas, adicionais)
- Combos (incluindo do_dia para restaurante e kit_festa para salgados)
- Bairros de entrega

Uso: python -m database.seed.seed_011_restaurantes_por_tipo

Super Food SaaS - Sprint 9.14 - Testes Visuais (v2: variações + imagens)
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
    CategoriaMenu, Produto, VariacaoProduto, Combo, ComboItem, BairroEntrega
)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")
# Fly.io PostgreSQL usa "postgres://" mas SQLAlchemy 2.0 precisa de "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ==================== HELPER IMAGENS UNSPLASH ====================
# Formato CDN: https://images.unsplash.com/{photo_id}?w=400&h=400&fit=crop&auto=format&q=80
U = "https://images.unsplash.com"

def img(photo_id: str) -> str:
    return f"{U}/{photo_id}?w=400&h=400&fit=crop&auto=format&q=80"


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
                "eh_pizza": True,
                "produtos": [
                    {
                        "nome": "Margherita",
                        "descricao": "Molho de tomate, mussarela, manjericão fresco e azeite",
                        "preco": 39.90,
                        "imagem": img("photo-1574071318508-1cdbab80d002"),
                        "ingredientes": ["Molho de tomate", "Mussarela", "Manjericão", "Azeite"],
                    },
                    {
                        "nome": "Calabresa",
                        "descricao": "Calabresa fatiada, cebola, azeitona e orégano",
                        "preco": 42.90,
                        "imagem": img("photo-1565299624946-b28f40a0ae38"),
                        "ingredientes": ["Calabresa", "Cebola", "Azeitona", "Orégano", "Mussarela"],
                    },
                    {
                        "nome": "Portuguesa",
                        "descricao": "Presunto, ovos, cebola, ervilha, azeitona e mussarela",
                        "preco": 45.90,
                        "imagem": img("photo-1565299624946-b28f40a0ae38"),
                        "ingredientes": ["Presunto", "Ovos", "Cebola", "Ervilha", "Azeitona", "Mussarela"],
                    },
                    {
                        "nome": "Quatro Queijos",
                        "descricao": "Mussarela, provolone, gorgonzola e parmesão",
                        "preco": 49.90,
                        "imagem": img("photo-1571407970349-bc81e7e96d47"),
                        "ingredientes": ["Mussarela", "Provolone", "Gorgonzola", "Parmesão"],
                    },
                    {
                        "nome": "Pepperoni",
                        "descricao": "Pepperoni premium importado com mussarela e molho especial",
                        "preco": 52.90,
                        "imagem": img("photo-1513104890138-7c749659a591"),
                        "ingredientes": ["Pepperoni", "Mussarela", "Molho de tomate", "Orégano"],
                    },
                    {
                        "nome": "Frango com Catupiry",
                        "descricao": "Frango desfiado com catupiry original e milho",
                        "preco": 44.90,
                        "imagem": img("photo-1565299624946-b28f40a0ae38"),
                        "ingredientes": ["Frango desfiado", "Catupiry", "Milho", "Mussarela"],
                    },
                    {
                        "nome": "Napolitana",
                        "descricao": "Tomate fatiado, mussarela, parmesão e manjericão",
                        "preco": 41.90,
                        "imagem": img("photo-1574071318508-1cdbab80d002"),
                        "ingredientes": ["Tomate", "Mussarela", "Parmesão", "Manjericão"],
                    },
                    {
                        "nome": "Bacon",
                        "descricao": "Bacon crocante, mussarela, cebola caramelizada e molho barbecue",
                        "preco": 47.90,
                        "imagem": img("photo-1513104890138-7c749659a591"),
                        "ingredientes": ["Bacon", "Mussarela", "Cebola caramelizada", "Molho barbecue"],
                    },
                ],
            },
            {
                "nome": "Pizzas Especiais",
                "emoji": "⭐",
                "eh_pizza": True,
                "produtos": [
                    {
                        "nome": "Pizza do Chef",
                        "descricao": "Rúcula, tomate seco, parmesão e presunto de Parma",
                        "preco": 59.90,
                        "imagem": img("photo-1574071318508-1cdbab80d002"),
                        "ingredientes": ["Rúcula", "Tomate seco", "Parmesão", "Presunto de Parma"],
                    },
                    {
                        "nome": "Camarão",
                        "descricao": "Camarões ao alho, mussarela e catupiry com cebolinha",
                        "preco": 65.90,
                        "imagem": img("photo-1565299624946-b28f40a0ae38"),
                        "ingredientes": ["Camarão", "Alho", "Mussarela", "Catupiry", "Cebolinha"],
                    },
                    {
                        "nome": "Filé Mignon",
                        "descricao": "Filé mignon em tiras, cebola roxa e cream cheese",
                        "preco": 62.90,
                        "imagem": img("photo-1513104890138-7c749659a591"),
                        "ingredientes": ["Filé mignon", "Cebola roxa", "Cream cheese", "Mussarela"],
                    },
                    {
                        "nome": "Salmão",
                        "descricao": "Salmão defumado, cream cheese, alcaparras e cebolinha",
                        "preco": 69.90,
                        "imagem": img("photo-1571407970349-bc81e7e96d47"),
                        "ingredientes": ["Salmão defumado", "Cream cheese", "Alcaparras", "Cebolinha"],
                    },
                ],
            },
            {
                "nome": "Pizzas Doces",
                "emoji": "🍫",
                "eh_pizza": True,
                "produtos": [
                    {
                        "nome": "Chocolate",
                        "descricao": "Chocolate ao leite com granulado e leite condensado",
                        "preco": 38.90,
                        "imagem": img("photo-1588315029754-2dd089d39a1a"),
                        "ingredientes": ["Chocolate ao leite", "Granulado", "Leite condensado"],
                    },
                    {
                        "nome": "Banana com Canela",
                        "descricao": "Banana, canela, leite condensado e mussarela",
                        "preco": 36.90,
                        "imagem": img("photo-1588315029754-2dd089d39a1a"),
                        "ingredientes": ["Banana", "Canela", "Leite condensado", "Mussarela"],
                    },
                    {
                        "nome": "Brigadeiro",
                        "descricao": "Brigadeiro artesanal com granulado belga",
                        "preco": 39.90,
                        "imagem": img("photo-1588315029754-2dd089d39a1a"),
                        "ingredientes": ["Brigadeiro", "Granulado belga", "Leite condensado"],
                    },
                    {
                        "nome": "Romeu e Julieta",
                        "descricao": "Goiabada cremosa com queijo minas derretido",
                        "preco": 37.90,
                        "imagem": img("photo-1588315029754-2dd089d39a1a"),
                        "ingredientes": ["Goiabada", "Queijo minas"],
                    },
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🥤",
                "produtos": [
                    {
                        "nome": "Coca-Cola 2L",
                        "descricao": "Coca-Cola original 2 litros",
                        "preco": 14.90,
                        "imagem": img("photo-1567696911980-2eed69a46042"),
                    },
                    {
                        "nome": "Guaraná Antarctica 2L",
                        "descricao": "Guaraná Antarctica 2 litros",
                        "preco": 12.90,
                        "imagem": img("photo-1567696911980-2eed69a46042"),
                    },
                    {
                        "nome": "Suco Natural 500ml",
                        "descricao": "Laranja, limão, maracujá ou abacaxi",
                        "preco": 9.90,
                        "imagem": img("photo-1563729784474-d77dbb933a9e"),
                    },
                    {
                        "nome": "Água Mineral 500ml",
                        "descricao": "Com ou sem gás",
                        "preco": 4.90,
                        "imagem": None,
                    },
                ],
            },
        ],
        # Variações de tamanho para todas as pizzas (adicionadas automaticamente)
        "pizza_tamanhos": [
            {"nome": "Pequena (4 fatias)", "preco_adicional": 0, "max_sabores": 1, "ordem": 1},
            {"nome": "Média (6 fatias)", "preco_adicional": 10.0, "max_sabores": 2, "ordem": 2},
            {"nome": "Grande (8 fatias)", "preco_adicional": 20.0, "max_sabores": 3, "ordem": 3},
            {"nome": "Família (12 fatias)", "preco_adicional": 35.0, "max_sabores": 4, "ordem": 4},
        ],
        "pizza_bordas": [
            {"nome": "Sem borda", "preco_adicional": 0, "ordem": 1},
            {"nome": "Catupiry", "preco_adicional": 8.90, "ordem": 2},
            {"nome": "Cheddar", "preco_adicional": 8.90, "ordem": 3},
            {"nome": "Chocolate", "preco_adicional": 9.90, "ordem": 4},
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
                "adicionais": [
                    {"nome": "Bacon extra", "preco": 5.00},
                    {"nome": "Queijo extra", "preco": 4.00},
                    {"nome": "Ovo", "preco": 3.00},
                    {"nome": "Cebola caramelizada", "preco": 4.00},
                ],
                "ponto_carne": True,
                "produtos": [
                    {
                        "nome": "Classic Smash",
                        "descricao": "Blend 120g, queijo cheddar, alface, tomate e molho especial",
                        "preco": 28.90,
                        "imagem": img("photo-1568901346375-23c9450c58cd"),
                        "ingredientes": ["Blend 120g", "Cheddar", "Alface", "Tomate", "Molho especial"],
                    },
                    {
                        "nome": "Double Smash",
                        "descricao": "2x blend 120g, cheddar duplo, cebola caramelizada e pickles",
                        "preco": 38.90,
                        "imagem": img("photo-1586190848861-99aa4a171e90"),
                        "ingredientes": ["2x Blend 120g", "Cheddar duplo", "Cebola caramelizada", "Pickles"],
                    },
                    {
                        "nome": "Bacon Burger",
                        "descricao": "Blend 150g, bacon crocante, cheddar, alface e molho barbecue",
                        "preco": 34.90,
                        "imagem": img("photo-1553979459-d2229ba7433b"),
                        "ingredientes": ["Blend 150g", "Bacon", "Cheddar", "Alface", "Molho barbecue"],
                    },
                    {
                        "nome": "Cheese Burger",
                        "descricao": "Blend 150g, cheddar triplo derretido e cebola crispy",
                        "preco": 32.90,
                        "imagem": img("photo-1550547660-d9450f859349"),
                        "ingredientes": ["Blend 150g", "Cheddar triplo", "Cebola crispy"],
                    },
                    {
                        "nome": "Egg Burger",
                        "descricao": "Blend 150g, ovo com gema mole, bacon e cheddar",
                        "preco": 35.90,
                        "imagem": img("photo-1568901346375-23c9450c58cd"),
                        "ingredientes": ["Blend 150g", "Ovo", "Bacon", "Cheddar"],
                    },
                ],
            },
            {
                "nome": "Burgers Premium",
                "emoji": "👑",
                "adicionais": [
                    {"nome": "Bacon extra", "preco": 5.00},
                    {"nome": "Queijo extra", "preco": 4.00},
                ],
                "ponto_carne": True,
                "produtos": [
                    {
                        "nome": "Wagyu Burger",
                        "descricao": "Blend wagyu 180g, gruyère, rúcula, tomate confit e aioli trufado",
                        "preco": 52.90,
                        "imagem": img("photo-1550547660-d9450f859349"),
                        "ingredientes": ["Blend wagyu 180g", "Gruyère", "Rúcula", "Tomate confit", "Aioli trufado"],
                    },
                    {
                        "nome": "Pulled Pork",
                        "descricao": "Carne de porco desfiada 12h, coleslaw e molho barbecue defumado",
                        "preco": 42.90,
                        "imagem": img("photo-1586190848861-99aa4a171e90"),
                        "ingredientes": ["Porco desfiado", "Coleslaw", "Molho barbecue defumado"],
                    },
                    {
                        "nome": "Blue Cheese",
                        "descricao": "Blend 180g, gorgonzola, cebola caramelizada no vinho e rúcula",
                        "preco": 45.90,
                        "imagem": img("photo-1553979459-d2229ba7433b"),
                        "ingredientes": ["Blend 180g", "Gorgonzola", "Cebola caramelizada", "Rúcula"],
                    },
                    {
                        "nome": "Chicken Crispy",
                        "descricao": "Frango empanado crocante, maionese de ervas e salada",
                        "preco": 36.90,
                        "imagem": img("photo-1604908176997-125f25cc6f3d"),
                        "ingredientes": ["Frango empanado", "Maionese de ervas", "Alface", "Tomate"],
                    },
                ],
            },
            {
                "nome": "Acompanhamentos",
                "emoji": "🍟",
                "produtos": [
                    {
                        "nome": "Batata Frita P",
                        "descricao": "Porção pequena com sal e ketchup",
                        "preco": 12.90,
                        "imagem": img("photo-1573080496219-bb080dd4f877"),
                    },
                    {
                        "nome": "Batata Frita G",
                        "descricao": "Porção grande com sal e ketchup",
                        "preco": 18.90,
                        "imagem": img("photo-1573080496219-bb080dd4f877"),
                    },
                    {
                        "nome": "Onion Rings",
                        "descricao": "Anéis de cebola empanados crocantes",
                        "preco": 16.90,
                        "imagem": img("photo-1573080496219-bb080dd4f877"),
                    },
                    {
                        "nome": "Nuggets 10un",
                        "descricao": "Nuggets de frango crocantes com molho",
                        "preco": 19.90,
                        "imagem": img("photo-1573080496219-bb080dd4f877"),
                    },
                    {
                        "nome": "Batata com Cheddar e Bacon",
                        "descricao": "Batata frita coberta com cheddar e bacon",
                        "preco": 24.90,
                        "imagem": img("photo-1573080496219-bb080dd4f877"),
                    },
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🥤",
                "produtos": [
                    {
                        "nome": "Milkshake Chocolate",
                        "descricao": "Milkshake cremoso de chocolate belga 400ml",
                        "preco": 18.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                    {
                        "nome": "Milkshake Morango",
                        "descricao": "Milkshake de morango com calda 400ml",
                        "preco": 18.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                    {
                        "nome": "Coca-Cola Lata",
                        "descricao": "Coca-Cola 350ml",
                        "preco": 6.90,
                        "imagem": img("photo-1567696911980-2eed69a46042"),
                    },
                    {
                        "nome": "Suco Natural",
                        "descricao": "Laranja ou limão 300ml",
                        "preco": 8.90,
                        "imagem": img("photo-1563729784474-d77dbb933a9e"),
                    },
                    {
                        "nome": "Cerveja Artesanal",
                        "descricao": "IPA ou Pilsen 473ml",
                        "preco": 14.90,
                        "imagem": img("photo-1608270586620-248524c67de9"),
                    },
                ],
            },
            {
                "nome": "Sobremesas",
                "emoji": "🍰",
                "produtos": [
                    {
                        "nome": "Brownie com Sorvete",
                        "descricao": "Brownie quentinho com sorvete de baunilha e calda",
                        "preco": 22.90,
                        "imagem": img("photo-1562440499-64c9a111f713"),
                    },
                    {
                        "nome": "Petit Gateau",
                        "descricao": "Bolo de chocolate com centro derretido e sorvete",
                        "preco": 24.90,
                        "imagem": img("photo-1562440499-64c9a111f713"),
                    },
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
                    {
                        "nome": "Combinado 15 peças",
                        "descricao": "5 sashimis + 5 niguiris + 5 uramakis variados",
                        "preco": 49.90,
                        "imagem": img("photo-1579871494447-9811cf80d66c"),
                    },
                    {
                        "nome": "Combinado 20 peças",
                        "descricao": "Mix do chef com sashimis, niguiris e rolls",
                        "preco": 62.90,
                        "imagem": img("photo-1579871494447-9811cf80d66c"),
                    },
                    {
                        "nome": "Combinado 30 peças",
                        "descricao": "Seleção premium com salmão, atum e camarão",
                        "preco": 89.90,
                        "imagem": img("photo-1579871494447-9811cf80d66c"),
                    },
                    {
                        "nome": "Combinado 50 peças",
                        "descricao": "Banquete completo para 2 pessoas",
                        "preco": 139.90,
                        "imagem": img("photo-1579871494447-9811cf80d66c"),
                    },
                    {
                        "nome": "Combo Salmão Premium",
                        "descricao": "20 peças exclusivas de salmão em diversas preparações",
                        "preco": 79.90,
                        "imagem": img("photo-1553621042-f6e147245754"),
                    },
                ],
            },
            {
                "nome": "Sashimis",
                "emoji": "🐟",
                "produtos": [
                    {
                        "nome": "Sashimi Salmão 5pç",
                        "descricao": "Fatias frescas de salmão norueguês",
                        "preco": 24.90,
                        "imagem": img("photo-1553621042-f6e147245754"),
                    },
                    {
                        "nome": "Sashimi Atum 5pç",
                        "descricao": "Fatias de atum fresco selecionado",
                        "preco": 29.90,
                        "imagem": img("photo-1553621042-f6e147245754"),
                    },
                    {
                        "nome": "Sashimi Peixe Branco 5pç",
                        "descricao": "Peixe branco fresco do dia",
                        "preco": 22.90,
                        "imagem": img("photo-1553621042-f6e147245754"),
                    },
                    {
                        "nome": "Sashimi Polvo 5pç",
                        "descricao": "Polvo macio ao ponto",
                        "preco": 34.90,
                        "imagem": img("photo-1553621042-f6e147245754"),
                    },
                ],
            },
            {
                "nome": "Hot Rolls",
                "emoji": "🔥",
                "produtos": [
                    {
                        "nome": "Hot Philadelphia",
                        "descricao": "Salmão, cream cheese empanado e frito, 8 peças",
                        "preco": 32.90,
                        "imagem": img("photo-1617196034796-73dfa7b1fd56"),
                    },
                    {
                        "nome": "Hot Skin",
                        "descricao": "Pele de salmão crocante com cream cheese, 8 peças",
                        "preco": 28.90,
                        "imagem": img("photo-1617196034796-73dfa7b1fd56"),
                    },
                    {
                        "nome": "Hot Camarão",
                        "descricao": "Camarão empanado com cream cheese e cebolinha, 8 peças",
                        "preco": 36.90,
                        "imagem": img("photo-1617196034796-73dfa7b1fd56"),
                    },
                    {
                        "nome": "Hot Banana",
                        "descricao": "Banana com chocolate e canela empanada, 8 peças",
                        "preco": 26.90,
                        "imagem": img("photo-1617196034796-73dfa7b1fd56"),
                    },
                ],
            },
            {
                "nome": "Temakis",
                "emoji": "🌮",
                "produtos": [
                    {
                        "nome": "Temaki Salmão",
                        "descricao": "Cone de nori com salmão, arroz, cream cheese e cebolinha",
                        "preco": 26.90,
                        "imagem": img("photo-1585032226651-759b368d7246"),
                    },
                    {
                        "nome": "Temaki Atum",
                        "descricao": "Cone de nori com atum fresco, arroz e gergelim",
                        "preco": 28.90,
                        "imagem": img("photo-1585032226651-759b368d7246"),
                    },
                    {
                        "nome": "Temaki Camarão",
                        "descricao": "Cone com camarão empanado e molho tarê",
                        "preco": 29.90,
                        "imagem": img("photo-1585032226651-759b368d7246"),
                    },
                    {
                        "nome": "Temaki Skin",
                        "descricao": "Cone com pele de salmão crocante e cream cheese",
                        "preco": 24.90,
                        "imagem": img("photo-1585032226651-759b368d7246"),
                    },
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🍵",
                "produtos": [
                    {
                        "nome": "Saquê Quente",
                        "descricao": "Saquê tradicional aquecido 180ml",
                        "preco": 18.90,
                        "imagem": img("photo-1555949258-eb67b1ef0ceb"),
                    },
                    {
                        "nome": "Saquê Gelado",
                        "descricao": "Saquê premium gelado 180ml",
                        "preco": 22.90,
                        "imagem": img("photo-1555949258-eb67b1ef0ceb"),
                    },
                    {
                        "nome": "Chá Verde",
                        "descricao": "Chá verde japonês 300ml",
                        "preco": 8.90,
                        "imagem": None,
                    },
                    {
                        "nome": "Cerveja Asahi",
                        "descricao": "Cerveja japonesa 330ml",
                        "preco": 16.90,
                        "imagem": img("photo-1608270586620-248524c67de9"),
                    },
                    {
                        "nome": "Refrigerante Lata",
                        "descricao": "Coca-Cola, Guaraná ou Sprite",
                        "preco": 6.90,
                        "imagem": img("photo-1567696911980-2eed69a46042"),
                    },
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
                    {
                        "nome": "Açaí 300ml",
                        "descricao": "Açaí puro batido na hora — adicione seus toppings favoritos",
                        "preco": 14.90,
                        "imagem": img("photo-1590301157890-4810ed352733"),
                    },
                    {
                        "nome": "Açaí 500ml",
                        "descricao": "Açaí puro batido na hora — tamanho médio",
                        "preco": 19.90,
                        "imagem": img("photo-1590301157890-4810ed352733"),
                    },
                    {
                        "nome": "Açaí 700ml",
                        "descricao": "Açaí puro batido na hora — tamanho grande",
                        "preco": 24.90,
                        "imagem": img("photo-1590301157890-4810ed352733"),
                    },
                    {
                        "nome": "Açaí 1 Litro",
                        "descricao": "Açaí puro batido, serve até 2 pessoas",
                        "preco": 32.90,
                        "imagem": img("photo-1590301157890-4810ed352733"),
                    },
                    {
                        "nome": "Bowl Tropical",
                        "descricao": "Açaí com banana, morango, granola e mel",
                        "preco": 26.90,
                        "imagem": img("photo-1504674900247-0877df9cc836"),
                    },
                    {
                        "nome": "Bowl Fitness",
                        "descricao": "Açaí com banana, aveia, whey protein e pasta de amendoim",
                        "preco": 29.90,
                        "imagem": img("photo-1504674900247-0877df9cc836"),
                    },
                    {
                        "nome": "Bowl Premium",
                        "descricao": "Açaí com frutas vermelhas, granola, leite ninho e nutella",
                        "preco": 34.90,
                        "imagem": img("photo-1504674900247-0877df9cc836"),
                    },
                ],
            },
            {
                "nome": "Sorvetes",
                "emoji": "🍦",
                "produtos": [
                    {
                        "nome": "Sorvete 1 Bola",
                        "descricao": "Escolha o sabor: chocolate, baunilha, morango ou creme",
                        "preco": 8.90,
                        "imagem": img("photo-1563729784474-d77dbb933a9e"),
                    },
                    {
                        "nome": "Sorvete 2 Bolas",
                        "descricao": "Duas bolas de sabores à escolha",
                        "preco": 14.90,
                        "imagem": img("photo-1563729784474-d77dbb933a9e"),
                    },
                    {
                        "nome": "Sorvete 3 Bolas",
                        "descricao": "Três bolas com calda e chantilly",
                        "preco": 18.90,
                        "imagem": img("photo-1563729784474-d77dbb933a9e"),
                    },
                    {
                        "nome": "Sundae",
                        "descricao": "Sorvete com calda quente de chocolate, chantilly e amendoim",
                        "preco": 19.90,
                        "imagem": img("photo-1562440499-64c9a111f713"),
                    },
                    {
                        "nome": "Banana Split",
                        "descricao": "3 bolas de sorvete com banana, caldas e chantilly",
                        "preco": 22.90,
                        "imagem": img("photo-1562440499-64c9a111f713"),
                    },
                ],
            },
            {
                "nome": "Milkshakes",
                "emoji": "🥤",
                "produtos": [
                    {
                        "nome": "Milkshake Chocolate",
                        "descricao": "Milkshake cremoso de chocolate 400ml",
                        "preco": 16.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                    {
                        "nome": "Milkshake Morango",
                        "descricao": "Milkshake de morango com pedaços 400ml",
                        "preco": 16.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                    {
                        "nome": "Milkshake Ovomaltine",
                        "descricao": "Milkshake com Ovomaltine crocante 400ml",
                        "preco": 18.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                    {
                        "nome": "Milkshake Nutella",
                        "descricao": "Milkshake com Nutella premium 400ml",
                        "preco": 19.90,
                        "imagem": img("photo-1563805042-7684c019e1cb"),
                    },
                ],
            },
            {
                "nome": "Complementos",
                "emoji": "🥜",
                "produtos": [
                    {"nome": "Granola", "descricao": "Porção extra de granola crocante", "preco": 3.00, "imagem": None},
                    {"nome": "Leite Ninho", "descricao": "Porção extra de leite ninho", "preco": 3.50, "imagem": None},
                    {"nome": "Nutella", "descricao": "Porção extra de Nutella", "preco": 5.00, "imagem": None},
                    {"nome": "Paçoca", "descricao": "Porção extra de paçoca triturada", "preco": 3.00, "imagem": None},
                    {"nome": "Morango", "descricao": "Porção extra de morangos frescos", "preco": 4.00, "imagem": None},
                    {"nome": "Banana", "descricao": "Porção extra de banana fatiada", "preco": 2.50, "imagem": None},
                    {"nome": "Whey Protein", "descricao": "Dose de whey protein (chocolate ou baunilha)", "preco": 5.00, "imagem": None},
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
                    {"nome": "Skol Lata 350ml", "descricao": "Cerveja Skol pilsen lata gelada", "preco": 4.49, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Brahma Lata 350ml", "descricao": "Cerveja Brahma pilsen lata gelada", "preco": 4.49, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Heineken Long Neck", "descricao": "Cerveja Heineken premium 330ml", "preco": 7.90, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Corona Long Neck", "descricao": "Cerveja Corona Extra 330ml", "preco": 8.90, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Budweiser Long Neck", "descricao": "Cerveja Budweiser 330ml", "preco": 6.90, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Stella Artois Long Neck", "descricao": "Cerveja Stella Artois 330ml", "preco": 7.90, "imagem": img("photo-1608270586620-248524c67de9")},
                    {"nome": "Skol Litrão", "descricao": "Cerveja Skol 1 litro retornável", "preco": 9.90, "imagem": img("photo-1525351484163-7529414344d8")},
                    {"nome": "Brahma Litrão", "descricao": "Cerveja Brahma 1 litro retornável", "preco": 9.90, "imagem": img("photo-1525351484163-7529414344d8")},
                ],
            },
            {
                "nome": "Refrigerantes",
                "emoji": "🥤",
                "produtos": [
                    {"nome": "Coca-Cola 2L", "descricao": "Coca-Cola original 2 litros", "preco": 11.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Coca-Cola Lata 350ml", "descricao": "Coca-Cola lata gelada", "preco": 5.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Guaraná Antarctica 2L", "descricao": "Guaraná Antarctica 2 litros", "preco": 9.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Fanta Laranja 2L", "descricao": "Fanta Laranja 2 litros", "preco": 9.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Sprite 2L", "descricao": "Sprite limão 2 litros", "preco": 9.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Coca-Cola Zero Lata", "descricao": "Coca-Cola zero açúcar 350ml", "preco": 5.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                ],
            },
            {
                "nome": "Destilados",
                "emoji": "🥃",
                "produtos": [
                    {"nome": "Vodka Absolut 750ml", "descricao": "Vodka Absolut Original importada", "preco": 69.90, "imagem": img("photo-1527281400683-1aae777175f8")},
                    {"nome": "Whisky Red Label 1L", "descricao": "Johnnie Walker Red Label", "preco": 89.90, "imagem": img("photo-1527281400683-1aae777175f8")},
                    {"nome": "Cachaça 51 965ml", "descricao": "Cachaça 51 tradicional", "preco": 12.90, "imagem": img("photo-1527281400683-1aae777175f8")},
                    {"nome": "Gin Tanqueray 750ml", "descricao": "Gin Tanqueray London Dry", "preco": 99.90, "imagem": img("photo-1527281400683-1aae777175f8")},
                    {"nome": "Rum Bacardi 980ml", "descricao": "Rum Bacardi carta branca", "preco": 39.90, "imagem": img("photo-1527281400683-1aae777175f8")},
                ],
            },
            {
                "nome": "Águas e Sucos",
                "emoji": "💧",
                "produtos": [
                    {"nome": "Água Mineral 500ml", "descricao": "Água mineral sem gás", "preco": 3.00, "imagem": None},
                    {"nome": "Água com Gás 500ml", "descricao": "Água mineral com gás", "preco": 3.50, "imagem": None},
                    {"nome": "Suco Del Valle 1L", "descricao": "Sabores: uva, laranja, pêssego, maçã", "preco": 8.90, "imagem": img("photo-1563729784474-d77dbb933a9e")},
                    {"nome": "Água de Coco 1L", "descricao": "Água de coco natural", "preco": 9.90, "imagem": None},
                ],
            },
            {
                "nome": "Energéticos e Isotônicos",
                "emoji": "⚡",
                "produtos": [
                    {"nome": "Red Bull 250ml", "descricao": "Energético Red Bull original", "preco": 12.90, "imagem": img("photo-1614313913007-2b4ae8ce32d6")},
                    {"nome": "Monster 473ml", "descricao": "Energético Monster Energy", "preco": 11.90, "imagem": img("photo-1614313913007-2b4ae8ce32d6")},
                    {"nome": "Gatorade 500ml", "descricao": "Isotônico Gatorade sabores variados", "preco": 7.90, "imagem": None},
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
                    {"nome": "Esfiha Carne", "descricao": "Carne moída temperada com especiarias árabes", "preco": 5.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha Frango", "descricao": "Frango desfiado com tempero especial", "preco": 5.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha Queijo", "descricao": "Mussarela derretida com orégano", "preco": 5.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha Calabresa", "descricao": "Calabresa fatiada com cebola e queijo", "preco": 6.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha 4 Queijos", "descricao": "Mussarela, provolone, catupiry e parmesão", "preco": 7.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha Beirute", "descricao": "Carne, tomate, cebola e temperos árabes", "preco": 6.90, "imagem": img("photo-1560512823-829485b8bf24")},
                    {"nome": "Esfiha de Escarola", "descricao": "Escarola refogada com alho e azeite", "preco": 5.90, "imagem": img("photo-1560512823-829485b8bf24")},
                ],
            },
            {
                "nome": "Esfihas Doces",
                "emoji": "🍯",
                "produtos": [
                    {"nome": "Esfiha Chocolate", "descricao": "Chocolate ao leite cremoso", "preco": 5.90, "imagem": img("photo-1588315029754-2dd089d39a1a")},
                    {"nome": "Esfiha Doce de Leite", "descricao": "Doce de leite artesanal", "preco": 5.90, "imagem": img("photo-1588315029754-2dd089d39a1a")},
                    {"nome": "Esfiha Romeu e Julieta", "descricao": "Goiabada com queijo minas", "preco": 6.90, "imagem": img("photo-1588315029754-2dd089d39a1a")},
                    {"nome": "Esfiha Nutella", "descricao": "Nutella premium com morango", "preco": 7.90, "imagem": img("photo-1588315029754-2dd089d39a1a")},
                ],
            },
            {
                "nome": "Kibes",
                "emoji": "🫓",
                "produtos": [
                    {"nome": "Kibe Frito", "descricao": "Kibe de carne frito crocante, unidade", "preco": 6.90, "imagem": img("photo-1534604973900-c43ab4c2e0ab")},
                    {"nome": "Kibe Assado", "descricao": "Kibe assado tradicional, unidade", "preco": 6.90, "imagem": img("photo-1534604973900-c43ab4c2e0ab")},
                    {"nome": "Kibe de Queijo", "descricao": "Kibe frito recheado com queijo", "preco": 7.90, "imagem": img("photo-1534604973900-c43ab4c2e0ab")},
                    {"nome": "Kibe Cru", "descricao": "Kibe cru com azeite e hortelã", "preco": 12.90, "imagem": img("photo-1534604973900-c43ab4c2e0ab")},
                ],
            },
            {
                "nome": "Beirutes",
                "emoji": "🥖",
                "produtos": [
                    {"nome": "Beirute de Carne", "descricao": "Pão sírio com carne, alface, tomate e molho tahine", "preco": 22.90, "imagem": img("photo-1585238342024-78d387f4a707")},
                    {"nome": "Beirute de Frango", "descricao": "Pão sírio com frango desfiado e salada", "preco": 21.90, "imagem": img("photo-1585238342024-78d387f4a707")},
                    {"nome": "Beirute Misto", "descricao": "Pão sírio com presunto, queijo e salada", "preco": 19.90, "imagem": img("photo-1585238342024-78d387f4a707")},
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "🥤",
                "produtos": [
                    {"nome": "Suco de Laranja", "descricao": "Suco natural de laranja 300ml", "preco": 8.90, "imagem": img("photo-1563729784474-d77dbb933a9e")},
                    {"nome": "Refrigerante Lata", "descricao": "Coca-Cola, Guaraná ou Sprite 350ml", "preco": 6.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                    {"nome": "Chá Mate", "descricao": "Chá mate gelado com limão 300ml", "preco": 6.90, "imagem": None},
                    {"nome": "Água Mineral", "descricao": "Água mineral 500ml", "preco": 4.00, "imagem": None},
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
                    {"nome": "Filé Grelhado", "descricao": "Filé mignon grelhado com arroz, feijão, salada e fritas", "preco": 39.90, "imagem": img("photo-1555939594-58d7cb561ad1")},
                    {"nome": "Frango à Parmegiana", "descricao": "Frango empanado com queijo e molho, arroz e fritas", "preco": 34.90, "imagem": img("photo-1632778149955-e80f8ceca2e8")},
                    {"nome": "Picanha na Chapa", "descricao": "Picanha grelhada com arroz, farofa, vinagrete e fritas", "preco": 49.90, "imagem": img("photo-1601050690117-94f5f6fa8bd7")},
                    {"nome": "Peixe Grelhado", "descricao": "Filé de tilápia grelhado com legumes e arroz", "preco": 36.90, "imagem": img("photo-1467003909585-2f8a72700288")},
                    {"nome": "Strogonoff de Frango", "descricao": "Strogonoff cremoso com arroz, batata palha e salada", "preco": 32.90, "imagem": img("photo-1467003909585-2f8a72700288")},
                    {"nome": "Feijoada Completa", "descricao": "Feijoada com arroz, couve, farofa, torresmo e laranja", "preco": 38.90, "imagem": img("photo-1546069901-ba9599a7e63c")},
                ],
            },
            {
                "nome": "Massas",
                "emoji": "🍝",
                "produtos": [
                    {"nome": "Espaguete à Bolonhesa", "descricao": "Espaguete com molho bolonhesa caseiro e parmesão", "preco": 28.90, "imagem": img("photo-1551183053-bf91a1d81141")},
                    {"nome": "Lasanha de Carne", "descricao": "Lasanha de carne moída com molho branco e queijo", "preco": 34.90, "imagem": img("photo-1529692236671-f1f6cf9683ba")},
                    {"nome": "Nhoque ao Sugo", "descricao": "Nhoque de batata com molho sugo e manjericão", "preco": 26.90, "imagem": img("photo-1551183053-bf91a1d81141")},
                    {"nome": "Fettuccine Alfredo", "descricao": "Fettuccine com molho alfredo cremoso e frango", "preco": 32.90, "imagem": img("photo-1551183053-bf91a1d81141")},
                ],
            },
            {
                "nome": "Carnes",
                "emoji": "🥩",
                "produtos": [
                    {"nome": "Costela no Bafo", "descricao": "Costela cozida lentamente com mandioca e salada", "preco": 52.90, "imagem": img("photo-1555939594-58d7cb561ad1")},
                    {"nome": "Bife à Cavalo", "descricao": "Bife de alcatra com ovo frito, arroz e feijão", "preco": 35.90, "imagem": img("photo-1414235077428-338989a2e8c0")},
                    {"nome": "Escalope ao Madeira", "descricao": "Medalhões de filé mignon ao molho madeira", "preco": 48.90, "imagem": img("photo-1414235077428-338989a2e8c0")},
                    {"nome": "Churrasco Misto", "descricao": "Mix de carnes grelhadas com acompanhamentos", "preco": 59.90, "imagem": img("photo-1601050690117-94f5f6fa8bd7")},
                ],
            },
            {
                "nome": "Saladas",
                "emoji": "🥗",
                "produtos": [
                    {"nome": "Salada Caesar", "descricao": "Alface romana, croutons, parmesão e molho caesar com frango", "preco": 24.90, "imagem": img("photo-1563379926898-05f4575a45d8")},
                    {"nome": "Salada Tropical", "descricao": "Mix de folhas, manga, abacaxi e molho de maracujá", "preco": 22.90, "imagem": img("photo-1563379926898-05f4575a45d8")},
                    {"nome": "Salada Caprese", "descricao": "Tomate, mussarela de búfala, manjericão e azeite", "preco": 26.90, "imagem": img("photo-1563379926898-05f4575a45d8")},
                ],
            },
            {
                "nome": "Sobremesas",
                "emoji": "🍮",
                "produtos": [
                    {"nome": "Pudim de Leite", "descricao": "Pudim de leite condensado caseiro", "preco": 12.90, "imagem": img("photo-1562440499-64c9a111f713")},
                    {"nome": "Mousse de Maracujá", "descricao": "Mousse cremosa de maracujá", "preco": 10.90, "imagem": img("photo-1562440499-64c9a111f713")},
                    {"nome": "Sorvete 2 Bolas", "descricao": "Sabores: chocolate, baunilha, morango ou creme", "preco": 14.90, "imagem": img("photo-1563729784474-d77dbb933a9e")},
                ],
            },
        ],
        "combos": [
            {"nome": "Segunda - Feijoada", "descricao": "Feijoada completa + Caipirinha de limão", "preco_combo": 39.90, "preco_original": 52.80, "tipo_combo": "do_dia", "dia_semana": 0},
            {"nome": "Terça - Filé Grelhado", "descricao": "Filé grelhado completo + Suco natural", "preco_combo": 36.90, "preco_original": 48.80, "tipo_combo": "do_dia", "dia_semana": 1},
            {"nome": "Quarta - Massa", "descricao": "Lasanha de carne + Refrigerante", "preco_combo": 32.90, "preco_original": 41.80, "tipo_combo": "do_dia", "dia_semana": 2},
            {"nome": "Quinta - Picanha", "descricao": "Picanha na chapa + Cerveja artesanal", "preco_combo": 49.90, "preco_original": 63.80, "tipo_combo": "do_dia", "dia_semana": 3},
            {"nome": "Sexta - Peixe", "descricao": "Peixe grelhado com legumes + Suco natural", "preco_combo": 34.90, "preco_original": 45.80, "tipo_combo": "do_dia", "dia_semana": 4},
            {"nome": "Sábado - Churrasco", "descricao": "Churrasco misto completo + Cerveja long neck", "preco_combo": 55.90, "preco_original": 73.80, "tipo_combo": "do_dia", "dia_semana": 5},
            {"nome": "Domingo - Strogonoff", "descricao": "Strogonoff de frango + Suco natural + Pudim", "preco_combo": 42.90, "preco_original": 56.70, "tipo_combo": "do_dia", "dia_semana": 6},
            {"nome": "Combo Família", "descricao": "2 Pratos Executivos + 2 Sobremesas + 1 Refrigerante 2L", "preco_combo": 89.90, "preco_original": 112.60, "tipo_combo": "padrao"},
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
                    {"nome": "Coxinha Assada", "descricao": "Coxinha de frango assada crocante, unidade", "preco": 5.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Empada de Frango", "descricao": "Empada caseira de frango com catupiry", "preco": 6.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Enroladinho de Salsicha", "descricao": "Massa folhada com salsicha, unidade", "preco": 4.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Pão de Queijo", "descricao": "Pão de queijo mineiro, unidade", "preco": 4.50, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Croissant Misto", "descricao": "Croissant recheado com presunto e queijo", "preco": 7.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Esfiha de Carne", "descricao": "Esfiha aberta de carne temperada", "preco": 5.90, "imagem": img("photo-1560512823-829485b8bf24")},
                ],
            },
            {
                "nome": "Salgados Fritos",
                "emoji": "🍤",
                "produtos": [
                    {"nome": "Coxinha de Frango", "descricao": "Coxinha cremosa de frango com catupiry, unidade", "preco": 5.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Risole de Presunto", "descricao": "Risole crocante de presunto e queijo, unidade", "preco": 5.50, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Bolinha de Queijo", "descricao": "Bolinha de queijo frita crocante, unidade", "preco": 4.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Pastel de Carne", "descricao": "Pastel frito de carne moída, unidade", "preco": 6.90, "imagem": img("photo-1599487488170-d11ec9c172f0")},
                    {"nome": "Pastel de Queijo", "descricao": "Pastel frito de queijo mussarela, unidade", "preco": 6.90, "imagem": img("photo-1599487488170-d11ec9c172f0")},
                    {"nome": "Kibe Frito", "descricao": "Kibe de carne frito crocante, unidade", "preco": 5.90, "imagem": img("photo-1534604973900-c43ab4c2e0ab")},
                ],
            },
            {
                "nome": "Doces",
                "emoji": "🍬",
                "produtos": [
                    {"nome": "Brigadeiro Gourmet", "descricao": "Brigadeiro artesanal, unidade", "preco": 4.50, "imagem": img("photo-1558961363-fa8fdf82db35")},
                    {"nome": "Beijinho", "descricao": "Beijinho de coco, unidade", "preco": 4.50, "imagem": img("photo-1558961363-fa8fdf82db35")},
                    {"nome": "Cajuzinho", "descricao": "Cajuzinho de amendoim, unidade", "preco": 4.50, "imagem": img("photo-1558961363-fa8fdf82db35")},
                    {"nome": "Trufa de Chocolate", "descricao": "Trufa de chocolate belga, unidade", "preco": 6.90, "imagem": img("photo-1558961363-fa8fdf82db35")},
                    {"nome": "Mini Churros", "descricao": "Mini churros recheado com doce de leite, 5 unidades", "preco": 12.90, "imagem": img("photo-1562967915-92ae0c320a01")},
                    {"nome": "Bolo de Pote", "descricao": "Bolo no pote: chocolate, ninho ou red velvet", "preco": 12.90, "imagem": img("photo-1558961363-fa8fdf82db35")},
                ],
            },
            {
                "nome": "Tortas",
                "emoji": "🥧",
                "produtos": [
                    {"nome": "Torta de Frango", "descricao": "Torta de frango com catupiry, fatia", "preco": 9.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Torta de Palmito", "descricao": "Torta de palmito com mussarela, fatia", "preco": 10.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                    {"nome": "Quiche de Bacon", "descricao": "Quiche de bacon com queijo gruyère, fatia", "preco": 11.90, "imagem": img("photo-1606755456206-b25206cde27e")},
                ],
            },
            {
                "nome": "Bebidas",
                "emoji": "☕",
                "produtos": [
                    {"nome": "Café Expresso", "descricao": "Café expresso curto ou longo", "preco": 5.90, "imagem": None},
                    {"nome": "Cappuccino", "descricao": "Cappuccino cremoso 200ml", "preco": 8.90, "imagem": None},
                    {"nome": "Suco Natural", "descricao": "Laranja, limão ou maracujá 300ml", "preco": 8.90, "imagem": img("photo-1563729784474-d77dbb933a9e")},
                    {"nome": "Refrigerante Lata", "descricao": "Coca-Cola, Guaraná ou Sprite 350ml", "preco": 6.90, "imagem": img("photo-1567696911980-2eed69a46042")},
                ],
            },
        ],
        "combos": [
            {"nome": "Kit Festa 10 Pessoas", "descricao": "30 salgados assados + 30 salgados fritos + 20 docinhos", "preco_combo": 89.90, "preco_original": 130.00, "tipo_combo": "kit_festa", "quantidade_pessoas": 10},
            {"nome": "Kit Festa 20 Pessoas", "descricao": "60 salgados assados + 60 salgados fritos + 40 docinhos + 1 bolo", "preco_combo": 169.90, "preco_original": 250.00, "tipo_combo": "kit_festa", "quantidade_pessoas": 20},
            {"nome": "Kit Festa 50 Pessoas", "descricao": "150 salgados assados + 150 salgados fritos + 100 docinhos + 2 bolos + 5 refrigerantes 2L", "preco_combo": 399.90, "preco_original": 600.00, "tipo_combo": "kit_festa", "quantidade_pessoas": 50},
            {"nome": "Combo Lanche", "descricao": "3 Salgados (assado/frito à escolha) + 1 Suco Natural", "preco_combo": 19.90, "preco_original": 26.60, "tipo_combo": "padrao"},
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
        dias_semana_abertos="segunda,terca,quarta,quinta,sexta,sabado,domingo",
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

    # Dados de pizza (tamanhos e bordas)
    pizza_tamanhos = dados.get("pizza_tamanhos", [])
    pizza_bordas = dados.get("pizza_bordas", [])

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

        is_pizza_category = cat_data.get("eh_pizza", False)
        cat_adicionais = cat_data.get("adicionais", [])
        has_ponto_carne = cat_data.get("ponto_carne", False)

        for j, prod_data in enumerate(cat_data["produtos"]):
            # Suporte formato novo (dict) e legado (tuple)
            if isinstance(prod_data, dict):
                nome_prod = prod_data["nome"]
                descricao = prod_data.get("descricao", "")
                preco = prod_data["preco"]
                imagem_url = prod_data.get("imagem")
                ingredientes = prod_data.get("ingredientes")
            else:
                nome_prod, descricao, preco = prod_data
                imagem_url = None
                ingredientes = None

            produto = Produto(
                restaurante_id=rid,
                categoria_id=categoria.id,
                nome=nome_prod,
                descricao=descricao,
                preco=preco,
                imagem_url=imagem_url,
                ingredientes_json=ingredientes,
                disponivel=True,
                destaque=(j == 0),  # Primeiro produto de cada categoria é destaque
                ordem_exibicao=j + 1,
                eh_pizza=is_pizza_category,
            )
            db.add(produto)
            db.flush()
            produto_ids.append(produto.id)

            # Adicionar variações de tamanho para pizzas
            if is_pizza_category and pizza_tamanhos:
                for tam in pizza_tamanhos:
                    variacao = VariacaoProduto(
                        produto_id=produto.id,
                        tipo_variacao="tamanho",
                        nome=tam["nome"],
                        preco_adicional=tam["preco_adicional"],
                        max_sabores=tam["max_sabores"],
                        ordem=tam["ordem"],
                        ativo=True,
                        estoque_disponivel=True,
                    )
                    db.add(variacao)

                # Adicionar variações de borda para pizzas
                for borda in pizza_bordas:
                    variacao = VariacaoProduto(
                        produto_id=produto.id,
                        tipo_variacao="borda",
                        nome=borda["nome"],
                        preco_adicional=borda["preco_adicional"],
                        ordem=borda["ordem"],
                        ativo=True,
                        estoque_disponivel=True,
                    )
                    db.add(variacao)

            # Adicionar variações de adicionais para burgers etc.
            for k_ad, adicional in enumerate(cat_adicionais):
                variacao = VariacaoProduto(
                    produto_id=produto.id,
                    tipo_variacao="adicional",
                    nome=adicional["nome"],
                    preco_adicional=adicional["preco"],
                    ordem=k_ad + 1,
                    ativo=True,
                    estoque_disponivel=True,
                )
                db.add(variacao)

            # Ponto da carne (burger)
            if has_ponto_carne:
                for k_pc, ponto in enumerate(["Mal passado", "Ao ponto", "Bem passado"]):
                    variacao = VariacaoProduto(
                        produto_id=produto.id,
                        tipo_variacao="ponto_carne",
                        nome=ponto,
                        preco_adicional=0,
                        ordem=k_pc + 1,
                        ativo=True,
                        estoque_disponivel=True,
                    )
                    db.add(variacao)

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

    # Commit principal (restaurante + config + produtos + variações + combos)
    db.commit()

    # Bairros (skip se tabela não existe — são opcionais para demo)
    try:
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
    except Exception:
        db.rollback()
        print(f"  [{tipo}] Bairros ignorados (tabela pode não existir)")
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
    print("SEED: 1 Restaurante de Cada Tipo (8 tipos) — v2")
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
