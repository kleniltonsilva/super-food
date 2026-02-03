# utils/__init__.py
"""
Módulo de Utilitários - Super Food SaaS

Contém funções auxiliares para:
- Cálculos de distância (Haversine, Mapbox)
- Cálculos de taxa e ganhos
- Seleção justa de motoboys
- Integração com APIs externas
"""

# Haversine - cálculo de distância offline
from .haversine import haversine

# Cálculos - taxa de entrega, ganhos do motoboy
from .calculos import (
    calcular_taxa_entrega,
    calcular_ganho_motoboy,
    registrar_ganho_motoboy,
    obter_ganhos_dia_motoboy,
    detectar_cidade_endereco,
    atualizar_cidade_restaurante,
    calcular_entrega_completa,
)

# Seleção justa de motoboys
from .motoboy_selector import (
    selecionar_motoboy_para_rota,
    atribuir_rota_motoboy,
    finalizar_entrega_motoboy,
    marcar_motoboy_disponivel,
    listar_motoboys_disponiveis,
    obter_estatisticas_motoboy,
)

# Nota: mapbox_api deve ser importado diretamente quando necessário
# para evitar problemas de import circular
# from utils.mapbox_api import geocode_address, get_directions, etc.

__all__ = [
    # Haversine
    'haversine',

    # Cálculos
    'calcular_taxa_entrega',
    'calcular_ganho_motoboy',
    'registrar_ganho_motoboy',
    'obter_ganhos_dia_motoboy',
    'detectar_cidade_endereco',
    'atualizar_cidade_restaurante',
    'calcular_entrega_completa',

    # Seleção de Motoboys
    'selecionar_motoboy_para_rota',
    'atribuir_rota_motoboy',
    'finalizar_entrega_motoboy',
    'marcar_motoboy_disponivel',
    'listar_motoboys_disponiveis',
    'obter_estatisticas_motoboy',
]
