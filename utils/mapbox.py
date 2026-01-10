# utils/mapbox.py
# Código completo para substituir o arquivo atual em utils/mapbox.py
# Atualizações:
# - Carregamento automático e seguro do .env a partir da raiz do projeto (independente do cwd)
# - Uso de MAPBOX_TOKEN carregado do .env
# - Função de geocodificação obrigatória (levanta erro claro se token ausente)
# - Função de distância com Mapbox Driving API (distância real por estrada) quando token disponível
# - Fallback automático para Haversine (linha reta) se token indisponível ou falha na API
# - Código limpo, tipado, com tratamento de erros e comentários
# - Dependência necessária: python-dotenv (instale com pip install python-dotenv se ainda não tiver)

import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from typing import Tuple

from .haversine import haversine  # fallback para distância em linha reta

# Carrega o .env localizado na raiz do projeto (dois níveis acima de utils/)
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")


def geocode_address(address: str) -> Tuple[float, float]:
    """
    Geocodifica um endereço usando a API Mapbox Geocoding.
    Retorna (latitude, longitude).
    Levanta exceção se o token não estiver configurado ou endereço não encontrado.
    """
    if not MAPBOX_TOKEN:
        raise ValueError("MAPBOX_TOKEN não configurado no .env (necessário para geocodificação)")

    url = "https://api.mapbox.com/geocoding/v5/mapbox.places/{}.json".format(
        address.replace(" ", "%20")
    )
    params = {
        "access_token": MAPBOX_TOKEN,
        "limit": 1,
        "country": "BR",  # otimiza para Brasil (ajuste se necessário)
        "language": "pt",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data.get("features"):
            lng, lat = data["features"][0]["center"]
            return lat, lng
        else:
            raise ValueError(f"Endereço não encontrado: {address}")
    except requests.RequestException as e:
        raise ValueError(f"Erro na comunicação com Mapbox Geocoding: {str(e)}")


def get_distance(
    origin: Tuple[float, float], destination: Tuple[float, float]
) -> float:
    """
    Calcula distância em quilômetros entre dois pontos (lat, lng).
    Usa Mapbox Directions (distância real por estrada) se token disponível.
    Fallback para Haversine (linha reta) em caso de falha ou token ausente.
    """
    if MAPBOX_TOKEN:
        try:
            origin_str = f"{origin[1]},{origin[0]}"  # lng,lat
            dest_str = f"{destination[1]},{destination[0]}"
            url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin_str};{dest_str}"

            params = {
                "access_token": MAPBOX_TOKEN,
                "geometries": "geojson",
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("routes"):
                distance_meters = data["routes"][0]["distance"]
                return distance_meters / 1000.0  # retorna em km
        except Exception:
            # Silenciosamente usa fallback em caso de erro na API
            pass

    # Fallback: distância em linha reta
    return haversine(origin, destination)


# Funções adicionais podem ser acrescentadas aqui (ex: matrix de distâncias para despacho inteligente)