"""
Seed: Criar categorias de menu padrão para restaurantes.

Super Food SaaS - Sistema de Inicialização de Dados
"""

from typing import Optional
from database.seed.base_seed import BaseSeed
from database.models import CategoriaMenu


# Categorias padrão disponíveis para todos os restaurantes
CATEGORIAS_PADRAO = [
    {'nome': 'Lanches', 'descricao': 'Hambúrgueres, sanduíches e similares', 'ordem': 1},
    {'nome': 'Pizzas', 'descricao': 'Pizzas tradicionais e especiais', 'ordem': 2},
    {'nome': 'Porções', 'descricao': 'Porções para compartilhar', 'ordem': 3},
    {'nome': 'Bebidas', 'descricao': 'Refrigerantes, sucos e bebidas', 'ordem': 4},
    {'nome': 'Sobremesas', 'descricao': 'Doces e sobremesas', 'ordem': 5},
    {'nome': 'Combos', 'descricao': 'Combos promocionais', 'ordem': 6},
    {'nome': 'Pratos', 'descricao': 'Pratos executivos e refeições', 'ordem': 7},
    {'nome': 'Promoções', 'descricao': 'Ofertas especiais', 'ordem': 8},
]


class CategoriasPadraoSeed(BaseSeed):
    """
    Cria categorias de menu padrão para um restaurante.

    Este seed é multi-tenant e requer restaurante_id.
    """

    order = 4
    name = "Categorias de Menu Padrão"
    skip_if_exists = True

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """Verifica se o restaurante já tem categorias."""
        if restaurante_id is None:
            return True  # Sem restaurante, pula

        return session.query(CategoriaMenu).filter(
            CategoriaMenu.restaurante_id == restaurante_id
        ).first() is not None

    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """Cria categorias padrão para o restaurante."""
        if restaurante_id is None:
            return 0

        if self.skip_if_exists and self.check_exists(session, restaurante_id):
            return 0

        count = 0
        for cat_data in CATEGORIAS_PADRAO:
            categoria = CategoriaMenu(
                restaurante_id=restaurante_id,
                nome=cat_data['nome'],
                descricao=cat_data.get('descricao', ''),
                ordem_exibicao=cat_data.get('ordem', 99),
                ativo=True
            )
            session.add(categoria)
            count += 1

        session.commit()
        return count


def criar_categorias_para_restaurante(session, restaurante_id: int) -> int:
    """
    Função auxiliar para criar categorias para um restaurante específico.

    Pode ser chamada de qualquer lugar do sistema.
    """
    seed = CategoriasPadraoSeed()
    seed.skip_if_exists = True
    return seed.run(session, restaurante_id)


# Instância do seed para registro
seed = CategoriasPadraoSeed()
