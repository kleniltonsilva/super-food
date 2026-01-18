"""
Integração Mapbox + Motoboy App
ATUALIZAÇÃO: Autocomplete e Validação de Zona de Cobertura
CORREÇÃO: Import correto do database.session
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote
from typing import Optional, Tuple, List, Dict
import requests

# Adiciona raiz do projeto ao path
sys.path.append(str(Path(__file__).resolve().parent.parent))

# ========== CORREÇÃO: IMPORT CORRETO ==========
from database.session import get_db_session
# ==============================================

from utils.haversine import haversine

# Carrega .env
from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
if not MAPBOX_TOKEN:
    print("[WARNING] MAPBOX_TOKEN não configurado. API Mapbox não funcionará.")


# ==================== GEOCODING ====================
def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Geocodifica endereço usando Mapbox Geocoding API.
    Retorna (lat, lng) ou None se falhar.
    """
    if not address or not MAPBOX_TOKEN:
        print(f"[ERRO] Endereço vazio ou MAPBOX_TOKEN não configurado: {address}")
        return None

    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(address)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1,
        "country": "BR",
        "language": "pt",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])

        if features:
            lng, lat = features[0]["center"]
            return lat, lng
        else:
            print(f"[ERRO] Nenhuma coordenada encontrada para: {address}")
            return None
    except requests.RequestException as e:
        print(f"[ERRO] Falha na requisição Mapbox Geocoding: {e}")
        return None


# ==================== NOVO: AUTOCOMPLETE DE ENDEREÇOS ====================
def autocomplete_address(query: str, proximity: Optional[Tuple[float, float]] = None) -> List[Dict]:
    """
    Retorna sugestões de endereços conforme o usuário digita
    
    Args:
        query: Texto parcial digitado pelo usuário
        proximity: (lat, lon) para priorizar resultados próximos
    
    Returns:
        Lista de sugestões: [{'place_name': str, 'coordinates': (lat, lon)}, ...]
    
    Exemplo:
        sugestoes = autocomplete_address("Rua Augusta 123")
        # [{'place_name': 'Rua Augusta, 123, São Paulo, SP', 'coordinates': (-23.55, -46.63)}, ...]
    """
    
    if not query or not MAPBOX_TOKEN:
        return []
    
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json"
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 5,
        "country": "BR",
        "language": "pt",
        "types": "address,poi"  # Endereços e pontos de interesse
    }
    
    # Prioriza resultados próximos ao restaurante
    if proximity:
        params["proximity"] = f"{proximity[1]},{proximity[0]}"  # lon,lat
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        sugestoes = []
        for feature in data.get("features", []):
            lng, lat = feature["center"]
            sugestoes.append({
                'place_name': feature['place_name'],
                'coordinates': (lat, lng)
            })
        
        return sugestoes
        
    except Exception as e:
        print(f"[WARNING] Falha no autocomplete: {e}")
        return []


# ==================== NOVO: VALIDAÇÃO DE ZONA DE COBERTURA ====================
def check_coverage_zone(
    restaurante_coords: Tuple[float, float],
    cliente_coords: Tuple[float, float],
    raio_maximo_km: float
) -> Dict:
    """
    Verifica se o cliente está dentro da zona de cobertura do restaurante
    
    Args:
        restaurante_coords: (lat, lon) do restaurante
        cliente_coords: (lat, lon) do cliente
        raio_maximo_km: Raio máximo de entrega
    
    Returns:
        {
            'dentro_zona': bool,
            'distancia_km': float,
            'mensagem': str
        }
    """
    
    distancia = haversine(restaurante_coords, cliente_coords)
    dentro_zona = distancia <= raio_maximo_km
    
    if dentro_zona:
        mensagem = f"✅ Endereço dentro da zona de cobertura ({distancia:.2f} km)"
    else:
        mensagem = f"❌ Endereço fora da zona de cobertura (Distância: {distancia:.2f} km, Máximo: {raio_maximo_km} km)"
    
    return {
        'dentro_zona': dentro_zona,
        'distancia_km': round(distancia, 2),
        'mensagem': mensagem
    }


# ==================== CÁLCULO DE DISTÂNCIA / ROTA ====================
def get_directions(origin: Tuple[float, float], destination: Tuple[float, float]) -> Optional[dict]:
    """
    Retorna rota via Mapbox Driving API: distância (m) e duração (s)
    Fallback para None se falhar.
    """
    if not origin or not destination or not MAPBOX_TOKEN:
        return None

    origin_str = f"{origin[1]},{origin[0]}"  # lng, lat
    dest_str = f"{destination[1]},{destination[0]}"
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin_str};{dest_str}"
    params = {"access_token": MAPBOX_TOKEN, "geometries": "geojson", "overview": "full", "steps": "false"}

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        routes = data.get("routes", [])
        if routes:
            route = routes[0]
            return {"distance": route.get("distance", 0), "duration": route.get("duration", 0)}
    except Exception as e:
        print(f"[WARNING] Falha ao obter rota Mapbox: {e}")
    return None


def get_distance(origin: Tuple[float, float], destination: Tuple[float, float]) -> float:
    """
    Calcula distância em km. Usa Mapbox Driving API se disponível, senão fallback Haversine.
    """
    rota = get_directions(origin, destination)
    if rota:
        return rota['distance'] / 1000.0
    return haversine(origin, destination)


# ==================== CACHE INTELIGENTE ====================
def calcular_distancia_tempo(
    restaurante_id: int,
    endereco_origem: str,
    endereco_destino: str,
    usar_cache: bool = True
) -> Tuple[Optional[float], Optional[int]]:
    """
    Calcula distância (km) e tempo (min) entre dois endereços com cache inteligente.
    """
    coords_origem = geocode_address(endereco_origem)
    coords_destino = geocode_address(endereco_destino)

    if not coords_origem or not coords_destino:
        return None, None

    rota = get_directions(coords_origem, coords_destino)
    if not rota:
        # fallback Haversine
        distancia_km = haversine(coords_origem, coords_destino)
        tempo_min = round(distancia_km / 0.4)  # assume média 25 km/h (~0.4 km/min)
    else:
        distancia_km = round(rota['distance'] / 1000, 2)
        tempo_min = round(rota['duration'] / 60)

    return distancia_km, tempo_min


# ==================== VALOR DE ENTREGA ====================
def calcular_valor_entrega(restaurante_id: int, distancia_km: float) -> float:
    """Calcula valor da entrega baseado na configuração do restaurante"""
    from database.models import ConfigRestaurante
    
    session = get_db_session()
    try:
        config = session.query(ConfigRestaurante).filter(
            ConfigRestaurante.restaurante_id == restaurante_id
        ).first()
        
        if not config:
            return 0.0
        
        taxa_base = config.taxa_entrega_base
        distancia_base = config.distancia_base_km
        taxa_extra = config.taxa_km_extra
        
        if distancia_km <= distancia_base:
            return taxa_base
        
        return round(taxa_base + (distancia_km - distancia_base) * taxa_extra, 2)
    finally:
        session.close()


# ==================== FUNÇÃO COMPLETA ====================
def processar_entrega_completa(restaurante_id: int, endereco_restaurante: str, endereco_cliente: str) -> Optional[dict]:
    """Processa entrega completa com distância, tempo e valor"""
    distancia_km, tempo_min = calcular_distancia_tempo(restaurante_id, endereco_restaurante, endereco_cliente)
    if distancia_km is None or tempo_min is None:
        return None
    valor_entrega = calcular_valor_entrega(restaurante_id, distancia_km)
    return {"distancia_km": distancia_km, "tempo_estimado_min": tempo_min, "valor_entrega": valor_entrega}