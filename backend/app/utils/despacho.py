import requests
from datetime import datetime
from typing import List
from haversine import haversine, Unit
from sqlalchemy.orm import Session
import os

from .. import models
# from ..main import manager  # Importa o manager do main.py

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

def calcular_distancia(coord1, coord2):
    return haversine(coord1, coord2, unit=Unit.KILOMETERS)

def get_rota_otimizada(origem: tuple, destinos: List[tuple]):
    if not destinos:
        return {"distancia_total_km": 0, "tempo_total_min": 0}
    waypoints = ";".join([f"{lon},{lat}" for lat, lon in [origem] + destinos])
    url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{waypoints}"
    params = {"access_token": MAPBOX_TOKEN, "geometries": "geojson", "overview": "full"}
    response = requests.get(url, params=params)
    if response.status_code == 200 and response.json()["routes"]:
        route = response.json()["routes"][0]
        return {
            "distancia_total_km": route["distance"] / 1000,
            "tempo_total_min": route["duration"] / 60,
            "geometry": route["geometry"]
        }
    return {"distancia_total_km": 999, "tempo_total_min": 999}

def atribuir_pedidos(db: Session, novos_pedidos: List[models.Pedido]):
    restaurante = novos_pedidos[0].restaurante
    endereco_rest = (restaurante.lat, restaurante.lon)

    pendentes = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == restaurante.id,
        models.Pedido.status == models.StatusPedido.pendente
    ).all()
    todos = pendentes + novos_pedidos

    if not todos:
        return {"mensagem": "Nenhum pedido pendente"}

    destinos = [(p.lat_cliente, p.lon_cliente) for p in todos]

    motoboys = db.query(models.Motoboy).filter(models.Motoboy.restaurante_id == restaurante.id, models.Motoboy.ativo == True).all()

    disponiveis = [m for m in motoboys if m.status == models.StatusMotoboy.disponivel]
    if disponiveis:
        disponiveis.sort(key=lambda m: m.ultimo_disponivel or datetime.min)
        motoboy = disponiveis[0]
    else:
        for m in motoboys:
            pos = (m.lat_atual or restaurante.lat, m.lon_atual or restaurante.lon)
            m.dist_temp = calcular_distancia(pos, endereco_rest)
            m.pendentes = len([p for p in todos if p.motoboy_id == m.id])
        motoboys.sort(key=lambda m: (m.dist_temp, m.pendentes))
        motoboy = motoboys[0] if motoboys else None

    if not motoboy:
        return {"mensagem": "Nenhum motoboy disponível"}

    rota = get_rota_otimizada(endereco_rest, destinos)

    for i, pedido in enumerate(todos):
        pedido.motoboy_id = motoboy.id
        pedido.status = models.StatusPedido.atribuido
        pedido.sequencia_entrega = i + 1
        pedido.distancia_estimada = rota["distancia_total_km"] / len(todos)
        pedido.data_atribuicao = datetime.utcnow()

    motoboy.status = models.StatusMotoboy.ocupado
    motoboy.entregas_hoje += len(todos)

    db.commit()

    # Broadcast realtime para dashboard e PWA motoboy conectados ao restaurante
    import asyncio
    asyncio.create_task(manager.broadcast({
        "type": "nova_atribuicao",
        "motoboy_id": motoboy.id,
        "motoboy_nome": motoboy.nome,
        "pedidos_ids": [p.id for p in todos],
        "total_pedidos": len(todos),
        "tempo_estimado_min": round(rota["tempo_total_min"]),
        "distancia_total_km": round(rota["distancia_total_km"], 1),
        "timestamp": datetime.utcnow().isoformat()
    }, restaurante.id))

    return {
        "motoboy": motoboy.nome,
        "total_pedidos": len(todos),
        "tempo_estimado_min": round(rota["tempo_total_min"]),
        "distancia_total_km": round(rota["distancia_total_km"], 1)
    }
