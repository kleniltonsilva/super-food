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


# ==================== MODOS DE DESPACHO ====================

def otimizar_rota_rapido_economico(
    origem: Tuple[float, float],
    destinos: List[Dict]
) -> List[Dict]:
    """
    Modo Rápido Econômico (Padrão)

    Usa TSP para otimizar rotas por proximidade.
    Não considera ordem cronológica.
    Prioriza economia de combustível.

    Args:
        origem: (lat, lon) do restaurante
        destinos: Lista de dicts com {pedido_id, lat, lon, data_criacao, ...}

    Returns:
        Lista ordenada por proximidade (TSP)
    """
    return otimizar_rota_tsp(origem, destinos)


def otimizar_rota_cronologico_inteligente(
    origem: Tuple[float, float],
    destinos: List[Dict],
    intervalo_agrupamento_min: int = 10
) -> List[Dict]:
    """
    Modo Cronológico Inteligente

    Agrupa pedidos com diferença <= intervalo_agrupamento_min.
    Dentro do grupo: usa modo rápido econômico (TSP).
    Entre grupos: respeita ordem cronológica de saída.

    Args:
        origem: (lat, lon) do restaurante
        destinos: Lista de dicts com {pedido_id, lat, lon, data_criacao, ...}
        intervalo_agrupamento_min: Intervalo máximo para agrupar pedidos (padrão: 10 min)

    Returns:
        Lista ordenada respeitando cronologia entre grupos e TSP dentro dos grupos
    """
    from datetime import timedelta

    if not destinos:
        return []

    if len(destinos) == 1:
        return destinos

    # Ordenar por data de criação
    destinos_ordenados = sorted(destinos, key=lambda x: x.get('data_criacao') or 0)

    # Agrupar pedidos por intervalo de tempo
    grupos = []
    grupo_atual = [destinos_ordenados[0]]

    for i in range(1, len(destinos_ordenados)):
        destino_atual = destinos_ordenados[i]
        destino_anterior = destinos_ordenados[i - 1]

        data_atual = destino_atual.get('data_criacao')
        data_anterior = destino_anterior.get('data_criacao')

        # Calcular diferença de tempo
        if data_atual and data_anterior:
            diferenca = (data_atual - data_anterior).total_seconds() / 60
        else:
            diferenca = 0

        if diferenca <= intervalo_agrupamento_min:
            # Mesmo grupo
            grupo_atual.append(destino_atual)
        else:
            # Novo grupo
            grupos.append(grupo_atual)
            grupo_atual = [destino_atual]

    # Adicionar último grupo
    if grupo_atual:
        grupos.append(grupo_atual)

    # Otimizar cada grupo com TSP e concatenar
    rota_final = []
    ponto_atual = origem

    for grupo in grupos:
        if len(grupo) == 1:
            rota_final.extend(grupo)
            ponto_atual = (grupo[0]['lat'], grupo[0]['lon'])
        else:
            # Otimizar grupo com TSP
            grupo_otimizado = otimizar_rota_tsp(ponto_atual, grupo)
            rota_final.extend(grupo_otimizado)
            if grupo_otimizado:
                ponto_atual = (grupo_otimizado[-1]['lat'], grupo_otimizado[-1]['lon'])

    return rota_final


def otimizar_rota_por_modo(
    origem: Tuple[float, float],
    destinos: List[Dict],
    modo: str = 'rapido_economico',
    intervalo_agrupamento_min: int = 10
) -> List[Dict]:
    """
    Função principal que seleciona o algoritmo de otimização baseado no modo.

    Args:
        origem: (lat, lon) do restaurante
        destinos: Lista de dicts com {pedido_id, lat, lon, data_criacao, ...}
        modo: 'rapido_economico', 'cronologico_inteligente', ou 'manual'
        intervalo_agrupamento_min: Para modo cronológico, intervalo de agrupamento

    Returns:
        Lista ordenada conforme o modo selecionado
    """
    if not destinos:
        return []

    if modo == 'rapido_economico':
        return otimizar_rota_rapido_economico(origem, destinos)

    elif modo == 'cronologico_inteligente':
        return otimizar_rota_cronologico_inteligente(
            origem, destinos, intervalo_agrupamento_min
        )

    elif modo == 'manual':
        # Modo manual: retorna na ordem original (sem otimização)
        return destinos

    else:
        # Fallback para modo padrão
        return otimizar_rota_rapido_economico(origem, destinos)
