"""
Módulo de Seeds - Super Food SaaS

Registro centralizado de todos os seeds para inicialização do banco.

Uso:
    from database.seed import get_all_seeds, run_all_seeds

    # Executar todos os seeds
    run_all_seeds(session)

    # Obter lista de seeds
    seeds = get_all_seeds()
"""

from typing import List, Dict, Optional
from database.seed.base_seed import BaseSeed

# Imports dos seeds (ordem alfabética para organização)
from database.seed import seed_001_super_admin
from database.seed import seed_002_planos
from database.seed import seed_003_restaurante_teste
from database.seed import seed_004_categorias_padrao
from database.seed import seed_005_config_padrao
from database.seed import seed_006_produtos_pizzaria

# Re-exports úteis
from database.seed.seed_002_planos import (
    PLANOS_CONFIG,
    DESCONTOS_PERIODO,
    calcular_valor_com_desconto,
    get_limite_motoboys,
    get_limite_pedidos_dia
)
from database.seed.seed_004_categorias_padrao import (
    CATEGORIAS_PADRAO,
    criar_categorias_para_restaurante
)
from database.seed.seed_005_config_padrao import (
    CONFIG_PADRAO,
    criar_config_para_restaurante,
    get_config_padrao
)
from database.seed.seed_006_produtos_pizzaria import (
    criar_produtos_pizzaria,
)


def get_all_seeds() -> List[BaseSeed]:
    """
    Retorna todos os seeds ordenados por prioridade.

    Returns:
        Lista de instâncias BaseSeed ordenadas pelo atributo 'order'
    """
    seeds = [
        seed_001_super_admin.seed,
        seed_002_planos.seed,
        seed_003_restaurante_teste.seed,
        seed_004_categorias_padrao.seed,
        seed_005_config_padrao.seed,
        seed_006_produtos_pizzaria.seed,
    ]

    return sorted(seeds, key=lambda s: s.order)


def run_all_seeds(
    session,
    verbose: bool = True,
    restaurante_id: Optional[int] = None
) -> Dict[str, int]:
    """
    Executa todos os seeds em ordem.

    Args:
        session: Sessão SQLAlchemy ativa
        verbose: Se True, exibe logs de progresso
        restaurante_id: ID do restaurante (para seeds multi-tenant)

    Returns:
        Dict com resultados: {seed_name: registros_criados}
    """
    results = {}

    for seed in get_all_seeds():
        try:
            count = seed.run(session, restaurante_id)
            results[seed.name] = count

            if verbose:
                if count > 0:
                    print(f"  ✅ {seed.name}: {count} registro(s) criado(s)")
                else:
                    print(f"  ⏭️  {seed.name}: já existe ou pulado")

        except Exception as e:
            results[seed.name] = -1
            if verbose:
                print(f"  ❌ {seed.name}: erro - {e}")

    return results


def run_seed_by_name(
    session,
    seed_name: str,
    restaurante_id: Optional[int] = None
) -> int:
    """
    Executa um seed específico pelo nome.

    Args:
        session: Sessão SQLAlchemy ativa
        seed_name: Nome do seed (ex: "Super Admin Padrão")
        restaurante_id: ID do restaurante (para seeds multi-tenant)

    Returns:
        Número de registros criados (-1 se não encontrado)
    """
    for seed in get_all_seeds():
        if seed.name == seed_name:
            return seed.run(session, restaurante_id)

    return -1


# Exportações do módulo
__all__ = [
    # Funções principais
    'get_all_seeds',
    'run_all_seeds',
    'run_seed_by_name',

    # Classe base
    'BaseSeed',

    # Configurações de planos
    'PLANOS_CONFIG',
    'DESCONTOS_PERIODO',
    'calcular_valor_com_desconto',
    'get_limite_motoboys',
    'get_limite_pedidos_dia',

    # Configurações de categorias
    'CATEGORIAS_PADRAO',
    'criar_categorias_para_restaurante',

    # Configurações padrão
    'CONFIG_PADRAO',
    'criar_config_para_restaurante',
    'get_config_padrao',

    # Produtos pizzaria
    'criar_produtos_pizzaria',
]
