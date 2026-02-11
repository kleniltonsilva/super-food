# backend/app/utils/menu_templates.py

"""
Templates de Menu por Tipo de Restaurante
Define categorias padrão e configurações de produtos
"""

TEMPLATES_RESTAURANTE = {
    "pizzaria": {
        "nome_display": "Pizzaria",
        "categorias_padrao": [
            {"nome": "🍕 Pizzas Salgadas", "icone": "🍕", "ordem": 1},
            {"nome": "🍰 Pizzas Doces", "icone": "🍰", "ordem": 2},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 3},
            {"nome": "🍨 Sobremesas", "icone": "🍨", "ordem": 4},
        ],
        "config_produto": {
            "permite_tamanhos": True,
            "tamanhos_padrao": [
                {"nome": "Broto (25cm)", "preco_base": 25.0},
                {"nome": "Média (30cm)", "preco_base": 35.0},
                {"nome": "Grande (35cm)", "preco_base": 45.0},
                {"nome": "Gigante (40cm)", "preco_base": 55.0},
            ],
            "permite_sabores": True,
            "max_sabores": 4,
            "permite_bordas": True,
            "bordas_padrao": [
                {"nome": "Sem borda", "preco": 0.0},
                {"nome": "Catupiry", "preco": 5.0},
                {"nome": "Cheddar", "preco": 5.0},
                {"nome": "Chocolate", "preco": 6.0},
            ],
            "permite_adicionais": True,
            "adicionais_padrao": [
                {"nome": "Azeitona extra", "preco": 2.0},
                {"nome": "Orégano extra", "preco": 0.0},
                {"nome": "Pimenta", "preco": 0.0},
            ],
        },
    },
    "hamburgueria": {
        "nome_display": "Hamburgueria",
        "categorias_padrao": [
            {"nome": "🍔 Hambúrgueres", "icone": "🍔", "ordem": 1},
            {"nome": "🍟 Porções", "icone": "🍟", "ordem": 2},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 3},
            {"nome": "🍨 Sobremesas", "icone": "🍨", "ordem": 4},
        ],
        "config_produto": {
            "permite_tamanhos": True,
            "tamanhos_padrao": [
                {"nome": "Simples (1 carne)", "preco_base": 18.0},
                {"nome": "Duplo (2 carnes)", "preco_base": 25.0},
                {"nome": "Triplo (3 carnes)", "preco_base": 32.0},
            ],
            "permite_ponto_carne": True,
            "pontos_carne": ["Mal passado", "Ao ponto", "Bem passado"],
            "permite_adicionais": True,
            "adicionais_padrao": [
                {"nome": "Bacon", "preco": 3.0},
                {"nome": "Queijo extra", "preco": 2.0},
                {"nome": "Ovo", "preco": 2.0},
                {"nome": "Salada (alface, tomate)", "preco": 1.0},
            ],
            "permite_acompanhamentos": True,
            "acompanhamentos_padrao": [
                {"nome": "Batata frita (150g)", "preco": 8.0},
                {"nome": "Onion rings", "preco": 10.0},
            ],
        },
    },
    "japones": {
        "nome_display": "Culinária Japonesa",
        "categorias_padrao": [
            {"nome": "🍣 Sushi", "icone": "🍣", "ordem": 1},
            {"nome": "🍱 Combos", "icone": "🍱", "ordem": 2},
            {"nome": "🍜 Hot Rolls", "icone": "🍜", "ordem": 3},
            {"nome": "🥟 Temakis", "icone": "🥟", "ordem": 4},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 5},
        ],
        "config_produto": {
            "permite_combos": True,
            "combos_padrao": [
                {"nome": "10 peças", "preco_base": 25.0},
                {"nome": "20 peças", "preco_base": 45.0},
                {"nome": "30 peças", "preco_base": 65.0},
                {"nome": "50 peças", "preco_base": 100.0},
            ],
            "permite_adicionais": True,
            "adicionais_padrao": [
                {"nome": "Shoyu extra", "preco": 0.0},
                {"nome": "Wasabi extra", "preco": 0.0},
                {"nome": "Gengibre extra", "preco": 0.0},
                {"nome": "Hashi descartável", "preco": 0.0},
            ],
        },
    },
    "churrascaria": {
        "nome_display": "Churrascaria",
        "categorias_padrao": [
            {"nome": "🥩 Carnes", "icone": "🥩", "ordem": 1},
            {"nome": "🍚 Acompanhamentos", "icone": "🍚", "ordem": 2},
            {"nome": "🥗 Saladas", "icone": "🥗", "ordem": 3},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 4},
        ],
        "config_produto": {
            "permite_ponto_carne": True,
            "pontos_carne": ["Mal passado", "Ao ponto", "Bem passado"],
            "permite_porcoes": True,
            "porcoes_padrao": [
                {"nome": "Individual (300g)", "preco_base": 25.0},
                {"nome": "Para 2 pessoas (600g)", "preco_base": 45.0},
                {"nome": "Para 4 pessoas (1.2kg)", "preco_base": 80.0},
            ],
            "permite_acompanhamentos": True,
            "acompanhamentos_padrao": [
                {"nome": "Arroz", "preco": 5.0},
                {"nome": "Farofa", "preco": 4.0},
                {"nome": "Vinagrete", "preco": 3.0},
            ],
        },
    },
    "la_carte": {
        "nome_display": "À La Carte",
        "categorias_padrao": [
            {"nome": "🍽️ Entradas", "icone": "🍽️", "ordem": 1},
            {"nome": "🍝 Pratos Principais", "icone": "🍝", "ordem": 2},
            {"nome": "🍰 Sobremesas", "icone": "🍰", "ordem": 3},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 4},
        ],
        "config_produto": {
            "permite_porcoes": True,
            "porcoes_padrao": [
                {"nome": "Individual", "preco_base": 30.0},
                {"nome": "Para 2 pessoas", "preco_base": 55.0},
                {"nome": "Para 4 pessoas", "preco_base": 100.0},
            ],
        },
    },
    "acai": {
        "nome_display": "Açaí e Sorvetes",
        "categorias_padrao": [
            {"nome": "🍇 Açaí", "icone": "🍇", "ordem": 1},
            {"nome": "🍦 Sorvetes", "icone": "🍦", "ordem": 2},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 3},
        ],
        "config_produto": {
            "permite_tamanhos": True,
            "tamanhos_padrao": [
                {"nome": "300ml", "preco_base": 12.0},
                {"nome": "500ml", "preco_base": 18.0},
                {"nome": "700ml", "preco_base": 24.0},
                {"nome": "1L", "preco_base": 32.0},
            ],
            "permite_adicionais": True,
            "adicionais_padrao": [
                {"nome": "Morango", "preco": 2.0},
                {"nome": "Banana", "preco": 1.5},
                {"nome": "Granola", "preco": 2.0},
                {"nome": "Leite em pó", "preco": 2.5},
                {"nome": "Paçoca", "preco": 2.0},
                {"nome": "Chocolate granulado", "preco": 1.5},
                {"nome": "Leite condensado", "preco": 2.0},
            ],
        },
    },
    "marmitex": {
        "nome_display": "Marmitex",
        "categorias_padrao": [
            {"nome": "🍱 Marmitas", "icone": "🍱", "ordem": 1},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 2},
        ],
        "config_produto": {
            "permite_tamanhos": True,
            "tamanhos_padrao": [
                {"nome": "P (até 400g)", "preco_base": 15.0},
                {"nome": "M (até 600g)", "preco_base": 20.0},
                {"nome": "G (até 800g)", "preco_base": 25.0},
            ],
            "permite_proteinas": True,
            "proteinas_padrao": [
                {"nome": "Frango grelhado", "preco": 0.0},
                {"nome": "Carne bovina", "preco": 2.0},
                {"nome": "Peixe", "preco": 3.0},
                {"nome": "Calabresa", "preco": 1.0},
            ],
            "permite_acompanhamentos": True,
            "acompanhamentos_padrao": [
                {"nome": "Arroz", "preco": 0.0},
                {"nome": "Feijão", "preco": 0.0},
                {"nome": "Salada", "preco": 0.0},
                {"nome": "Batata frita", "preco": 2.0},
                {"nome": "Macarrão", "preco": 2.0},
            ],
        },
    },
    "geral": {
        "nome_display": "Geral",
        "categorias_padrao": [
            {"nome": "🍽️ Todos os Produtos", "icone": "🍽️", "ordem": 1},
            {"nome": "🥤 Bebidas", "icone": "🥤", "ordem": 2},
        ],
        "config_produto": {},
    },
}


def get_template(tipo_restaurante: str):
    """Retorna template do tipo de restaurante"""
    return TEMPLATES_RESTAURANTE.get(tipo_restaurante.lower(), TEMPLATES_RESTAURANTE["geral"])


def criar_categorias_padrao(restaurante_id: int, tipo_restaurante: str, db_session):
    """
    Cria categorias padrão para um restaurante baseado no tipo

    Args:
        restaurante_id: ID do restaurante
        tipo_restaurante: Tipo (pizza, burger, etc)
        db_session: Sessão do banco SQLAlchemy
    """
    from database.models import CategoriaMenu

    template = get_template(tipo_restaurante)
    categorias_criadas = []

    for cat_def in template["categorias_padrao"]:
        categoria = CategoriaMenu(
            restaurante_id=restaurante_id,
            nome=cat_def["nome"],
            icone=cat_def.get("icone"),
            ordem_exibicao=cat_def.get("ordem", 0),
            ativo=True
        )
        db_session.add(categoria)
        categorias_criadas.append(categoria)

    db_session.flush()
    return categorias_criadas


def criar_produtos_modelo(restaurante_id: int, tipo_restaurante: str, db_session) -> int:
    """
    Cria produtos modelo para um restaurante baseado no tipo.
    Atualmente suporta pizzaria. Outros tipos retornam 0.

    Args:
        restaurante_id: ID do restaurante
        tipo_restaurante: Tipo (pizzaria, hamburgueria, etc)
        db_session: Sessão do banco SQLAlchemy

    Returns:
        Número de registros criados
    """
    tipo = tipo_restaurante.lower()
    if tipo == "pizzaria":
        from database.seed.seed_006_produtos_pizzaria import criar_produtos_pizzaria
        return criar_produtos_pizzaria(db_session, restaurante_id)
    return 0


def criar_site_config_padrao(restaurante_id: int, tipo_restaurante: str, dados_personalizados: dict, db_session):
    """
    Cria configuração padrão do site para um restaurante

    Args:
        restaurante_id: ID do restaurante
        tipo_restaurante: Tipo (pizza, burger, etc)
        dados_personalizados: Dict com cores, whatsapp, etc
        db_session: Sessão do banco SQLAlchemy
    """
    from database.models import SiteConfig

    site_config = SiteConfig(
        restaurante_id=restaurante_id,
        tipo_restaurante=tipo_restaurante.lower(),
        tema_cor_primaria=dados_personalizados.get("cor_primaria", "#FF6B35"),
        tema_cor_secundaria=dados_personalizados.get("cor_secundaria", "#004E89"),
        whatsapp_numero=dados_personalizados.get("whatsapp"),
        whatsapp_ativo=bool(dados_personalizados.get("whatsapp")),
        pedido_minimo=dados_personalizados.get("pedido_minimo", 15.0),
        tempo_entrega_estimado=dados_personalizados.get("tempo_entrega", 50),
        tempo_retirada_estimado=dados_personalizados.get("tempo_retirada", 20),
        site_ativo=True,
        aceita_dinheiro=True,
        aceita_cartao=True,
        aceita_pix=True
    )

    db_session.add(site_config)
    db_session.flush()
    return site_config