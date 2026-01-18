"""
TSP Optimizer - Algoritmo de Otimização de Rotas
Implementa Nearest Neighbor Heuristic para resolver o problema do caixeiro viajante
"""

from typing import List, Tuple, Dict
from haversine import haversine, Unit


def calcular_distancia(ponto1: Tuple[float, float], ponto2: Tuple[float, float]) -> float:
    """
    Calcula distância entre dois pontos (lat, lon) em km
    """
    return haversine(ponto1, ponto2, unit=Unit.KILOMETERS)


def otimizar_rota_tsp(
    origem: Tuple[float, float],
    destinos: List[Dict]
) -> List[Dict]:
    """
    Otimiza rota usando algoritmo Nearest Neighbor (TSP simplificado)
    
    Parâmetros:
        origem: Tupla com latitude e longitude do ponto inicial
        destinos: Lista de dicionários com 'nome' e 'coordenadas' de cada destino
    Retorna:
        Lista de destinos na ordem otimizada
    """
    if not destinos:
        return []

    # Inicializa variáveis
    rota_otimizada = []
    visitados = set()
    ponto_atual = origem

    # Enquanto houver destinos não visitados
    while len(visitados) < len(destinos):
        # Seleciona o destino mais próximo ainda não visitado
        mais_proximo = None
        distancia_minima = float('inf')
        for i, destino in enumerate(destinos):
            if i in visitados:
                continue
            dist = calcular_distancia(ponto_atual, destino['coordenadas'])
            if dist < distancia_minima:
                distancia_minima = dist
                mais_proximo = i

        # Atualiza rota e ponto atual
        visitados.add(mais_proximo)
        rota_otimizada.append(destinos[mais_proximo])
        ponto_atual = destinos[mais_proximo]['coordenadas']

    return rota_otimizada
"""
Otimiza rota usando algoritmo Nearest Neighbor (TSP simplificado)

Args:
    origem: (lat, lon) do restaurante
    destinos: Lista de dicts com {id, lat, lon, pedido_id, ...}

Returns:
    Lista ordenada de destinos (ordem otimizada)

Exemplo:
    origem = (-23.550520, -46.633308)
    destinos = [
        {'pedido_id': 1, 'lat': -23.55, 'lon': -46.64},
        {'pedido_id': 2, 'lat': -23.56, 'lon': -46.62},
        {'pedido_id': 3, 'lat': -23.54, 'lon': -46.63}
    ]
    rota_otimizada = otimizar_rota_tsp(origem, destinos)
    # Retorna destinos reordenados pela menor distância
"""

def otimizar_rota_tsp(origem: Tuple[float, float], destinos: List[Dict]) -> List[Dict]:
    if not destinos:
        return []

    if len(destinos) == 1:
        return destinos

    # Cópia para não modificar original
    nao_visitados = destinos.copy()
    rota_otimizada = []
    ponto_atual = origem

    # Algoritmo Nearest Neighbor
    while nao_visitados:
        # Encontra o destino mais próximo do ponto atual
        mais_proximo = None
        menor_distancia = float('inf')
        
        for destino in nao_visitados:
            ponto_destino = (destino['lat'], destino['lon'])
            dist = calcular_distancia(ponto_atual, ponto_destino)
            
            if dist < menor_distancia:
                menor_distancia = dist
                mais_proximo = destino
        
        # Adiciona à rota e remove de não visitados
        rota_otimizada.append(mais_proximo)
        nao_visitados.remove(mais_proximo)
        
        # Atualiza ponto atual para o destino recém-adicionado
        ponto_atual = (mais_proximo['lat'], mais_proximo['lon'])

    return rota_otimizada


def calcular_metricas_rota(origem: Tuple[float, float], rota_ordenada: List[Dict]) -> Dict:
    """
    Calcula distância total e tempo estimado da rota

    Args:
        origem: (lat, lon) do restaurante
        rota_ordenada: Lista de destinos já ordenados

    Returns:
        {'distancia_total_km': float, 'tempo_total_min': int}
    """
    if not rota_ordenada:
        return {'distancia_total_km': 0.0, 'tempo_total_min': 0}

    distancia_total = 0.0
    ponto_atual = origem

    for destino in rota_ordenada:
        ponto_destino = (destino['lat'], destino['lon'])
        distancia_total += calcular_distancia(ponto_atual, ponto_destino)
        ponto_atual = ponto_destino

    # Velocidade média: 25 km/h (trânsito urbano)
    VELOCIDADE_MEDIA_KMH = 25
    tempo_total_min = int((distancia_total / VELOCIDADE_MEDIA_KMH) * 60)

    return {
        'distancia_total_km': round(distancia_total, 2),
        'tempo_total_min': tempo_total_min
    }
    