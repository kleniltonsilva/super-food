# arquivo: utils/haversine.py
from math import radians, sin, cos, sqrt, atan2

def haversine(coord1: tuple, coord2: tuple) -> float:
    """
    Calcula distância entre dois pontos (lat, lon) em km usando fórmula de Haversine
    
    Args:
        coord1: (lat, lon) do ponto 1
        coord2: (lat, lon) do ponto 2
    
    Returns:
        Distância em km
    """
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    R = 6371  # raio da Terra em km
    
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c