# Substitua o arquivo completo backend/app/routers/restaurantes.py (handling completo de exceções + sempre retorna JSON válido, mesmo em erros internos)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import requests
import os
from .. import models, schemas, database, auth

router = APIRouter(prefix="/restaurantes", tags=["Restaurantes"])

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")

def geocode_address(endereco: str):
    if not MAPBOX_TOKEN:
        raise HTTPException(status_code=500, detail="MAPBOX_TOKEN não configurado no .env (necessário para geocodificação)")

    try:
        encoded = requests.utils.quote(endereco)
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{encoded}.json"
        params = {"access_token": MAPBOX_TOKEN, "limit": 1, "country": "BR"}
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()

        data = response.json()
        if not data.get("features"):
            raise HTTPException(status_code=400, detail=f"Endereço não encontrado: '{endereco}'. Simplifique ou verifique o texto.")

        coords = data["features"][0]["center"]
        return coords[1], coords[0]  # lat, lon
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Timeout na geocodificação Mapbox (endereço muito complexo ou conexão lenta)")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Erro de comunicação com Mapbox: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro inesperado na geocodificação: {str(e)}")

@router.post("/signup", response_model=schemas.RestaurantePublic, status_code=status.HTTP_201_CREATED)
def signup_restaurante(restaurante_in: schemas.RestauranteCreate, db: Session = Depends(database.get_db)):
    try:
        # Verifica email duplicado
        if db.query(models.Restaurante).filter(models.Restaurante.email == restaurante_in.email).first():
            raise HTTPException(status_code=400, detail="Email já cadastrado")

        # Geocodifica (exceções já convertidas em HTTPException com JSON)
        lat, lon = geocode_address(restaurante_in.endereco_completo)

        # Cria restaurante (Pydantic v2)
        plano = (restaurante_in.plano or "basico").lower()
        novo_rest = models.Restaurante(
            **restaurante_in.model_dump(exclude={"senha", "plano"}),
            hashed_password=auth.get_password_hash(restaurante_in.senha),
            lat=lat,
            lon=lon,
            plano=plano
        )
        novo_rest.gerar_codigo_acesso()

        db.add(novo_rest)
        db.commit()
        db.refresh(novo_rest)
        return novo_rest

    except HTTPException:
        # Re-raise HTTPException (FastAPI já retorna JSON válido)
        raise
    except Exception as e:
        # Captura qualquer erro não tratado → retorna JSON claro (evita resposta vazia/text)
        raise HTTPException(status_code=500, detail=f"Erro interno ao criar restaurante: {str(e)}")

@router.get("/", response_model=List[schemas.RestaurantePublic])
def listar_restaurantes(db: Session = Depends(database.get_db)):
    return db.query(models.Restaurante).all()

@router.get("/{restaurante_id}", response_model=schemas.RestaurantePublic)
def get_restaurante(restaurante_id: int, db: Session = Depends(database.get_db)):
    rest = db.query(models.Restaurante).filter(models.Restaurante.id == restaurante_id).first()
    if not rest:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    return rest
