from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import requests
import os

from .. import models, schemas, database, auth
from ..utils.despacho import atribuir_pedidos

router = APIRouter(prefix="/pedidos", tags=["Pedidos"])

def geocode_address(endereco: str):
    MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
    if not MAPBOX_TOKEN:
        raise HTTPException(status_code=500, detail="MAPBOX_TOKEN não configurado")
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(endereco)}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1, "country": "BR"}
    response = requests.get(url, params=params)
    if response.status_code != 200 or not response.json()["features"]:
        return None, None
    coords = response.json()["features"][0]["center"]
    return coords[1], coords[0]  # lat, lon

@router.post("/", response_model=schemas.PedidoPublic)
def criar_pedido(
    pedido: schemas.PedidoCreate,
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db)
):
    lat, lon = geocode_address(pedido.endereco)
    if lat is None:
        raise HTTPException(status_code=400, detail="Endereço cliente inválido")

    novo_pedido = models.Pedido(
        restaurante_id=current_restaurante.id,
        nome_cliente=pedido.nome_cliente,
        telefone_cliente=pedido.telefone_cliente,
        endereco=pedido.endereco,
        lat_cliente=lat,
        lon_cliente=lon,
        itens=pedido.itens,
        valor_total=pedido.valor_total,
        status=models.StatusPedido.pendente
    )
    db.add(novo_pedido)
    db.commit()
    db.refresh(novo_pedido)

    atribuir_pedidos(db, [novo_pedido])

    return schemas.PedidoPublic.from_orm(novo_pedido)

@router.get("/", response_model=List[schemas.PedidoPublic])
def listar_pedidos(
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db)
):
    pedidos = db.query(models.Pedido).filter(models.Pedido.restaurante_id == current_restaurante.id).all()
    return pedidos
