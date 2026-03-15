# backend/app/routers/pedidos.py

"""
Router Pedidos - Gerenciamento de pedidos do restaurante
Corrigido: campos alinhados com models.py (cliente_nome, endereco_entrega, etc)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import requests
import os

from .. import models, schemas, database, auth

try:
    from backend.app.utils.despacho import despachar_pedidos_automatico
    DESPACHO_DISPONIVEL = True
except ImportError:
    DESPACHO_DISPONIVEL = False

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
    lat, lon = geocode_address(pedido.endereco_entrega)
    if lat is None:
        raise HTTPException(status_code=400, detail="Endereço cliente inválido")

    # Gerar comanda sequencial
    ultimo_pedido = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == current_restaurante.id
    ).order_by(models.Pedido.id.desc()).first()
    proxima_comanda = (ultimo_pedido.comanda + 1) if ultimo_pedido and ultimo_pedido.comanda else 1

    novo_pedido = models.Pedido(
        restaurante_id=current_restaurante.id,
        comanda=proxima_comanda,
        cliente_nome=pedido.cliente_nome,
        cliente_telefone=pedido.cliente_telefone,
        endereco_entrega=pedido.endereco_entrega,
        latitude_entrega=lat,
        longitude_entrega=lon,
        itens=pedido.itens,
        valor_total=pedido.valor_total,
        tipo="Entrega",
        origem="manual",
        tipo_entrega="entrega",
        status='pendente',
        historico_status=[{"status": "pendente", "timestamp": datetime.utcnow().isoformat()}],
        data_criacao=datetime.utcnow()
    )
    db.add(novo_pedido)
    db.commit()
    db.refresh(novo_pedido)

    if DESPACHO_DISPONIVEL:
        try:
            despachar_pedidos_automatico(db, current_restaurante.id)
        except Exception as e:
            print(f"Erro no despacho automático: {e}")

    return novo_pedido


@router.get("/", response_model=List[schemas.PedidoPublic])
def listar_pedidos(
    current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    db: Session = Depends(database.get_db)
):
    pedidos = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == current_restaurante.id
    ).order_by(models.Pedido.data_criacao.desc()).all()
    return pedidos
