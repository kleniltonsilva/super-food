"""
Seed: Criar planos de assinatura padrão.

Derekh Food SaaS - Sistema de Inicialização de Dados

Planos disponíveis:
- Básico: Para pequenos restaurantes
- Essencial: Para restaurantes médios
- Avançado: Para restaurantes com alto volume
- Premium: Para grandes operações

Descontos por período:
- Mensal: 0%
- Trimestral: 5%
- Semestral: 15%
- Anual: 30%
"""

from typing import Optional
from database.seed.base_seed import BaseSeed

# Definição dos planos (usado em outras partes do sistema)
PLANOS_CONFIG = {
    'basico': {
        'nome': 'Básico',
        'valor_mensal': 99.90,
        'limite_motoboys': 3,
        'limite_pedidos_dia': 50,
        'descricao': 'Ideal para pequenos restaurantes'
    },
    'essencial': {
        'nome': 'Essencial',
        'valor_mensal': 199.90,
        'limite_motoboys': 10,
        'limite_pedidos_dia': 150,
        'descricao': 'Para restaurantes em crescimento'
    },
    'avancado': {
        'nome': 'Avançado',
        'valor_mensal': 349.90,
        'limite_motoboys': 30,
        'limite_pedidos_dia': 500,
        'descricao': 'Para alto volume de entregas'
    },
    'premium': {
        'nome': 'Premium',
        'valor_mensal': 599.90,
        'limite_motoboys': 999,
        'limite_pedidos_dia': 9999,
        'descricao': 'Sem limites, suporte prioritário'
    }
}

DESCONTOS_PERIODO = {
    'mensal': 0.0,
    'trimestral': 0.05,
    'semestral': 0.15,
    'anual': 0.30
}


class PlanosSeed(BaseSeed):
    """
    Seed para configuração de planos.

    Nota: Os planos são definidos como constantes neste arquivo
    e usados diretamente pelo sistema. Este seed apenas garante
    que a configuração está documentada e acessível.
    """

    order = 2
    name = "Configuração de Planos"
    skip_if_exists = True

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """Planos são constantes, sempre existem."""
        return True

    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """
        Os planos são definidos como constantes.
        Este método apenas valida a configuração.
        """
        # Validação básica
        for plano_id, config in PLANOS_CONFIG.items():
            assert 'valor_mensal' in config, f"Plano {plano_id} sem valor_mensal"
            assert 'limite_motoboys' in config, f"Plano {plano_id} sem limite_motoboys"

        return 0


def calcular_valor_com_desconto(plano: str, periodo: str) -> float:
    """
    Calcula o valor do plano com desconto por período.

    Args:
        plano: ID do plano (basico, essencial, avancado, premium)
        periodo: Período de pagamento (mensal, trimestral, semestral, anual)

    Returns:
        Valor total com desconto aplicado
    """
    if plano not in PLANOS_CONFIG:
        raise ValueError(f"Plano inválido: {plano}")
    if periodo not in DESCONTOS_PERIODO:
        raise ValueError(f"Período inválido: {periodo}")

    valor_mensal = PLANOS_CONFIG[plano]['valor_mensal']
    desconto = DESCONTOS_PERIODO[periodo]

    meses = {
        'mensal': 1,
        'trimestral': 3,
        'semestral': 6,
        'anual': 12
    }

    valor_total = valor_mensal * meses[periodo]
    valor_com_desconto = valor_total * (1 - desconto)

    return round(valor_com_desconto, 2)


def get_limite_motoboys(plano: str) -> int:
    """Retorna o limite de motoboys para um plano."""
    return PLANOS_CONFIG.get(plano, {}).get('limite_motoboys', 3)


def get_limite_pedidos_dia(plano: str) -> int:
    """Retorna o limite de pedidos diários para um plano."""
    return PLANOS_CONFIG.get(plano, {}).get('limite_pedidos_dia', 50)


# Instância do seed para registro
seed = PlanosSeed()
