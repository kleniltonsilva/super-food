# database/seed/seed_010_bulk_restaurantes.py

"""
Seed de 1000 restaurantes para teste de carga
Uso: python -m database.seed.seed_010_bulk_restaurantes
"""

import sys
import os
import random
import hashlib
from datetime import datetime, timedelta

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base
from database.models import (
    Restaurante, ConfigRestaurante, SiteConfig,
    CategoriaMenu, Produto, Motoboy, Pedido
)

try:
    from faker import Faker
    fake = Faker("pt_BR")
except ImportError:
    print("ERRO: instale faker com: pip install Faker>=22.0.0")
    sys.exit(1)

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./super_food.db")
TOTAL_RESTAURANTES = 1000
BATCH_SIZE = 100

# Distribuicao de planos
PLANOS = {
    "basico": 0.50,
    "essencial": 0.25,
    "avancado": 0.15,
    "premium": 0.10,
}

TIPOS_RESTAURANTE = [
    "pizzaria", "hamburgueria", "acai", "bebidas",
    "esfiharia", "restaurante", "salgados", "sushi"
]

CATEGORIAS_POR_TIPO = {
    "pizzaria": ["Pizzas Tradicionais", "Pizzas Especiais", "Pizzas Doces", "Bebidas", "Bordas"],
    "hamburgueria": ["Burgers Classicos", "Burgers Premium", "Acompanhamentos", "Bebidas", "Sobremesas"],
    "acai": ["Acai Bowls", "Sorvetes", "Milkshakes", "Smoothies", "Complementos"],
    "bebidas": ["Sucos", "Refrigerantes", "Cervejas", "Drinks", "Aguas"],
    "esfiharia": ["Esfihas Salgadas", "Esfihas Doces", "Kibes", "Beirutes", "Bebidas"],
    "restaurante": ["Pratos Executivos", "Massas", "Carnes", "Saladas", "Sobremesas"],
    "salgados": ["Salgados Assados", "Salgados Fritos", "Kits Festa", "Doces", "Bebidas"],
    "sushi": ["Combinados", "Sashimis", "Hot Rolls", "Temakis", "Bebidas"],
}

NOMES_PRODUTOS = {
    "pizzaria": ["Margherita", "Calabresa", "Frango", "Quatro Queijos", "Portuguesa", "Pepperoni",
                  "Napolitana", "Bacon", "Atum", "Chocolate", "Banana", "Brigadeiro"],
    "hamburgueria": ["Classic Burger", "Bacon Burger", "Cheese Burger", "Double Smash", "Chicken Burger",
                     "Veggie Burger", "Batata Frita", "Onion Rings", "Milkshake", "Brownie"],
    "acai": ["Acai 300ml", "Acai 500ml", "Acai 700ml", "Bowl Tropical", "Sorvete Baunilha",
             "Sorvete Chocolate", "Milkshake Morango", "Smoothie Verde"],
    "default": ["Produto A", "Produto B", "Produto C", "Produto D", "Produto E"],
}


def gerar_codigo_acesso():
    """Gera codigo de 8 chars unico"""
    import string
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.strip().encode()).hexdigest()


def criar_restaurante(i: int) -> dict:
    """Gera dados de um restaurante ficticio"""
    tipo = random.choice(TIPOS_RESTAURANTE)
    plano = random.choices(
        list(PLANOS.keys()),
        weights=list(PLANOS.values()),
        k=1
    )[0]

    nome = fake.company()
    return {
        "tipo": tipo,
        "plano": plano,
        "restaurante": Restaurante(
            nome=nome,
            nome_fantasia=nome,
            razao_social=f"{nome} LTDA",
            cnpj=fake.cnpj().replace(".", "").replace("/", "").replace("-", ""),
            email=f"restaurante{i}@superfood.test",
            senha=hash_senha("123456"),
            telefone=fake.phone_number(),
            endereco_completo=fake.address(),
            cidade=fake.city(),
            estado=fake.state_abbr(),
            cep=fake.postcode(),
            latitude=float(fake.latitude()),
            longitude=float(fake.longitude()),
            codigo_acesso=gerar_codigo_acesso(),
            ativo=random.random() > 0.05,  # 95% ativos
            plano=plano,
            data_cadastro=fake.date_time_between(start_date="-2y", end_date="now"),
        ),
    }


def criar_dados_restaurante(db, restaurante, tipo, plano):
    """Cria dados complementares para um restaurante"""
    rid = restaurante.id

    # ConfigRestaurante
    config = ConfigRestaurante(
        restaurante_id=rid,
        status_atual=random.choice(["aberto", "fechado"]),
        horario_abertura="10:00",
        horario_fechamento="23:00",
        dias_semana_abertos="seg,ter,qua,qui,sex,sab,dom",
        taxa_entrega_base=round(random.uniform(3, 10), 2),
        distancia_base_km=round(random.uniform(2, 5), 1),
        taxa_km_extra=round(random.uniform(1, 3), 2),
        raio_entrega_km=round(random.uniform(5, 15), 1),
        tempo_preparo_padrao=random.randint(15, 45),
    )
    db.add(config)

    # SiteConfig
    site = SiteConfig(
        restaurante_id=rid,
        site_ativo=True,
        tipo_restaurante=tipo,
        tema_cor_primaria="#e4002e",
        tema_cor_secundaria="#ffefef",
        pedido_minimo=round(random.uniform(10, 30), 2),
        tempo_entrega_estimado=random.randint(30, 60),
        tempo_retirada_estimado=random.randint(15, 30),
        aceita_dinheiro=True,
        aceita_cartao=True,
        aceita_pix=True,
    )
    db.add(site)

    # Categorias + Produtos
    categorias = CATEGORIAS_POR_TIPO.get(tipo, CATEGORIAS_POR_TIPO["restaurante"])
    num_categorias = random.randint(3, len(categorias))

    for j, cat_nome in enumerate(categorias[:num_categorias]):
        categoria = CategoriaMenu(
            restaurante_id=rid,
            nome=cat_nome,
            ordem_exibicao=j + 1,
            ativo=True,
        )
        db.add(categoria)
        db.flush()

        # Produtos por categoria
        nomes = NOMES_PRODUTOS.get(tipo, NOMES_PRODUTOS["default"])
        num_produtos = random.randint(3, 8)
        for k in range(num_produtos):
            nome_prod = random.choice(nomes) if k < len(nomes) else f"{cat_nome} #{k+1}"
            produto = Produto(
                restaurante_id=rid,
                categoria_id=categoria.id,
                nome=nome_prod,
                descricao=fake.sentence(nb_words=8),
                preco=round(random.uniform(8, 80), 2),
                disponivel=random.random() > 0.1,
                destaque=random.random() > 0.8,
                ordem_exibicao=k + 1,
            )
            db.add(produto)

    # Motoboys
    num_motoboys = random.randint(1, 5)
    for m in range(num_motoboys):
        motoboy = Motoboy(
            restaurante_id=rid,
            nome=fake.name(),
            telefone=fake.phone_number(),
            veiculo=random.choice(["Moto", "Bicicleta", "Carro"]),
            placa=fake.license_plate() if random.random() > 0.3 else None,
            ativo=True,
            status=random.choice(["disponivel", "em_entrega", "offline"]),
        )
        db.add(motoboy)

    # Pedidos
    num_pedidos = random.randint(5, 50)
    for p in range(num_pedidos):
        pedido = Pedido(
            restaurante_id=rid,
            comanda=str(p + 1),
            tipo=random.choice(["Entrega", "Retirada na loja"]),
            origem=random.choice(["site", "whatsapp", "telefone"]),
            cliente_nome=fake.name(),
            cliente_telefone=fake.phone_number(),
            endereco_entrega=fake.address() if random.random() > 0.3 else None,
            itens="1x Produto Teste",
            valor_total=round(random.uniform(20, 150), 2),
            forma_pagamento=random.choice(["dinheiro", "cartao", "pix"]),
            status=random.choice(["pendente", "em_preparo", "pronto", "em_entrega", "entregue", "cancelado"]),
            data_criacao=fake.date_time_between(start_date="-90d", end_date="now"),
        )
        db.add(pedido)


def main():
    print(f"Conectando ao banco: {DATABASE_URL[:50]}...")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Verifica quantos restaurantes ja existem
    existentes = db.query(Restaurante).count()
    print(f"Restaurantes existentes: {existentes}")

    if existentes >= TOTAL_RESTAURANTES:
        print(f"Ja existem {existentes} restaurantes. Seed nao necessario.")
        db.close()
        return

    total_criar = TOTAL_RESTAURANTES - existentes
    print(f"Criando {total_criar} restaurantes...")

    codigos_usados = set(
        r[0] for r in db.query(Restaurante.codigo_acesso).all()
    )
    emails_usados = set(
        r[0] for r in db.query(Restaurante.email).all()
    )

    criados = 0
    for batch_start in range(0, total_criar, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, total_criar)
        print(f"  Batch {batch_start+1}-{batch_end}...", end=" ", flush=True)

        for i in range(batch_start, batch_end):
            idx = existentes + i + 1
            dados = criar_restaurante(idx)
            rest = dados["restaurante"]

            # Garante unicidade
            while rest.codigo_acesso in codigos_usados:
                rest.codigo_acesso = gerar_codigo_acesso()
            codigos_usados.add(rest.codigo_acesso)

            while rest.email in emails_usados:
                rest.email = f"restaurante{idx}_{random.randint(1000,9999)}@superfood.test"
            emails_usados.add(rest.email)

            db.add(rest)
            db.flush()

            criar_dados_restaurante(db, rest, dados["tipo"], dados["plano"])
            criados += 1

        db.commit()
        print(f"OK ({criados}/{total_criar})")

    db.close()
    print(f"\nSeed concluido! {criados} restaurantes criados.")
    print(f"Total no banco: {existentes + criados}")


if __name__ == "__main__":
    main()
