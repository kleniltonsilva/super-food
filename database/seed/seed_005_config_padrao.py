"""
Seed: Configurações padrão para novos restaurantes.

Super Food SaaS - Sistema de Inicialização de Dados

Este módulo define as configurações padrão que são aplicadas
quando um novo restaurante é criado no sistema.
"""

from typing import Optional
from database.seed.base_seed import BaseSeed
from database.models import ConfigRestaurante


# Configurações padrão para novos restaurantes
CONFIG_PADRAO = {
    # Status inicial
    'status_atual': 'fechado',
    'modo_despacho': 'auto_economico',

    # Área de entrega
    'raio_entrega_km': 10.0,
    'tempo_medio_preparo': 30,
    'despacho_automatico': True,

    # Taxa de entrega (cobrada do cliente)
    'taxa_entrega_base': 5.00,      # Taxa até distancia_base_km
    'distancia_base_km': 3.0,        # Km incluídos na taxa base
    'taxa_km_extra': 1.50,           # Taxa por km adicional

    # Pagamento do motoboy
    'valor_base_motoboy': 5.00,      # Valor base por entrega
    'valor_km_extra_motoboy': 1.00,  # Adicional por km extra
    'taxa_diaria': 0.0,              # Taxa diária (opcional)
    'valor_lanche': 0.0,             # Valor para lanche (opcional)

    # Configurações de rota
    'max_pedidos_por_rota': 5,       # Máximo de pedidos por rota
    'permitir_ver_saldo_motoboy': True,  # Motoboy pode ver seu saldo

    # Horários padrão
    'horario_abertura': '11:00',
    'horario_fechamento': '23:00',
    'dias_semana_abertos': 'seg,ter,qua,qui,sex,sab,dom'
}


class ConfigPadraoSeed(BaseSeed):
    """
    Seed para configurações padrão.

    Este seed é usado quando um novo restaurante é criado
    e não tem configurações definidas.
    """

    order = 5
    name = "Configurações Padrão"
    skip_if_exists = True

    def check_exists(self, session, restaurante_id: Optional[int] = None) -> bool:
        """Verifica se o restaurante já tem configurações."""
        if restaurante_id is None:
            return True

        return session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante_id
        ).first() is not None

    def run(self, session, restaurante_id: Optional[int] = None) -> int:
        """Cria configurações padrão para o restaurante."""
        if restaurante_id is None:
            return 0

        if self.skip_if_exists and self.check_exists(session, restaurante_id):
            return 0

        config = ConfigRestaurante(
            restaurante_id=restaurante_id,
            **CONFIG_PADRAO
        )

        session.add(config)
        session.commit()
        return 1


def criar_config_para_restaurante(session, restaurante_id: int, **kwargs) -> ConfigRestaurante:
    """
    Cria configuração para um restaurante, permitindo sobrescrever valores padrão.

    Args:
        session: Sessão SQLAlchemy
        restaurante_id: ID do restaurante
        **kwargs: Valores para sobrescrever o padrão

    Returns:
        Instância de ConfigRestaurante criada
    """
    # Mescla padrão com valores customizados
    config_data = {**CONFIG_PADRAO, **kwargs}

    config = ConfigRestaurante(
        restaurante_id=restaurante_id,
        **config_data
    )

    session.add(config)
    session.commit()
    return config


def get_config_padrao() -> dict:
    """Retorna cópia das configurações padrão."""
    return CONFIG_PADRAO.copy()


# Instância do seed para registro
seed = ConfigPadraoSeed()
