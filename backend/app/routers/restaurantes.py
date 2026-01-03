from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import requests
import os

from .. import models, schemas, database, auth

router = APIRouter(prefix="/restaurantes", tags=["Restaurantes"])

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

def geocode_address(endereco: str):
    if not MAPBOX_TOKEN:
        raise HTTPException(status_code=500, detail="MAPBOX_TOKEN não configurado")
    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{requests.utils.quote(endereco)}.json"
    params = {"access_token": MAPBOX_TOKEN, "limit": 1, "country": "BR"}
    response = requests.get(url, params=params)
    if response.status_code != 200 or not response.json()["features"]:
        return None, None
    coords = response.json()["features"][0]["center"]
    return coords[1], coords[0]  # lat, lon

@router.post("/signup", response_model=schemas.RestaurantePublic, status_code=status.HTTP_201_CREATED)
def signup_restaurante(restaurante: schemas.RestauranteCreate, db: Session = Depends(database.get_db)):
    if db.query(models.Restaurante).filter(models.Restaurante.email == restaurante.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    if db.query(models.Restaurante).filter(models.Restaurante.nome_fantasia == restaurante.nome_fantasia).first():
        raise HTTPException(status_code=400, detail="Nome fantasia já em uso")

    lat, lon = geocode_address(restaurante.endereco_completo)
    if lat is None:
        raise HTTPException(status_code=400, detail="Endereço não encontrado")

    hashed_password = auth.get_password_hash(restaurante.senha)
    novo_restaurante = models.Restaurante(
        **restaurante.dict(exclude={"senha"}),
        hashed_password=hashed_password,
        lat=lat,
        lon=lon
    )
    db.add(novo_restaurante)
    db.commit()
    db.refresh(novo_restaurante)

    access_token = auth.create_access_token(data={"sub": novo_restaurante.id, "role": "restaurante"})
    return {**schemas.RestaurantePublic.from_orm(novo_restaurante).dict(), "access_token": access_token, "token_type": "bearer"}

@router.post("/login")
def login_restaurante(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    restaurante = db.query(models.Restaurante).filter(models.Restaurante.email == form_data.username).first()
    if not restaurante or not auth.verify_password(form_data.password, restaurante.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    access_token = auth.create_access_token(data={"sub": restaurante.id, "role": "restaurante"})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.RestaurantePublic)
def get_me(current: models.Restaurante = Depends(auth.get_current_restaurante)):
    return current

@router.patch("/me", response_model=schemas.RestaurantePublic)
def update_me(update: schemas.RestauranteUpdate, current: models.Restaurante = Depends(auth.get_current_restaurante), db: Session = Depends(database.get_db)):
    if update.endereco_completo and update.endereco_completo != current.endereco_completo:
        lat, lon = geocode_address(update.endereco_completo)
        if lat is None:
            raise HTTPException(status_code=400, detail="Novo endereço inválido")
        current.lat = lat
        current.lon = lon
        current.endereco_completo = update.endereco_completo

    for field, value in update.dict(exclude_unset=True).items():
        if field not in ["endereco_completo"]:
            setattr(current, field, value)

    db.commit()
    db.refresh(current)
    return current
