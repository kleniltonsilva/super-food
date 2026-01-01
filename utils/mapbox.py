# arquivo: utils/mapbox.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

def geocode(address: str):
    if not MAPBOX_TOKEN:
        return None
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(address)}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data["features"]:
            return data["features"][0]["center"]  # [lng, lat]
    except Exception:
        return None
    return None