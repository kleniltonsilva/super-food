"""
Router de GPS - Endpoints para rastreamento em tempo real de motoboys
Super Food SaaS v2.8.1
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from ..database import get_db
from .. import models, auth

router = APIRouter(prefix="/api/gps", tags=["GPS"])


class GPSUpdate(BaseModel):
    """Schema para atualização de GPS (endpoint legado sem auth)"""
    motoboy_id: int
    restaurante_id: int
    latitude: float
    longitude: float
    velocidade: Optional[float] = 0.0
    precisao: Optional[float] = None
    heading: Optional[float] = None  # Direção em graus


class GPSUpdateAuth(BaseModel):
    """Schema para atualização de GPS (endpoint JWT — motoboy_id e restaurante_id vêm do token)"""
    latitude: float
    longitude: float
    velocidade: Optional[float] = 0.0
    precisao: Optional[float] = None
    heading: Optional[float] = None


class GPSResponse(BaseModel):
    """Resposta de atualização GPS"""
    sucesso: bool
    mensagem: str
    timestamp: Optional[str] = None


class MotoboyGPSInfo(BaseModel):
    """Informações de GPS de um motoboy"""
    motoboy_id: int
    nome: str
    latitude: float
    longitude: float
    velocidade: float
    ultima_atualizacao: str
    em_rota: bool
    entregas_pendentes: int


@router.post("/update", response_model=GPSResponse)
async def atualizar_gps(
    gps_data: GPSUpdate,
    db: Session = Depends(get_db)
):
    """
    Atualiza a localização GPS de um motoboy.

    Este endpoint é chamado pelo App Motoboy a cada 10 segundos
    quando o motoboy está online.
    """
    try:
        # Verificar se motoboy existe e está ativo
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == gps_data.motoboy_id,
            models.Motoboy.restaurante_id == gps_data.restaurante_id,
            models.Motoboy.status == 'ativo'
        ).first()

        if not motoboy:
            raise HTTPException(status_code=404, detail="Motoboy não encontrado")

        # Verificar se motoboy está online
        if not motoboy.disponivel:
            return GPSResponse(
                sucesso=False,
                mensagem="Motoboy está offline"
            )

        timestamp = datetime.now()

        # Criar registro de GPS
        gps_record = models.GPSMotoboy(
            motoboy_id=gps_data.motoboy_id,
            restaurante_id=gps_data.restaurante_id,
            latitude=gps_data.latitude,
            longitude=gps_data.longitude,
            velocidade=gps_data.velocidade or 0.0,
            timestamp=timestamp
        )
        db.add(gps_record)

        # Atualizar posição atual no motoboy
        motoboy.latitude_atual = gps_data.latitude
        motoboy.longitude_atual = gps_data.longitude
        motoboy.ultima_atualizacao_gps = timestamp

        db.commit()

        return GPSResponse(
            sucesso=True,
            mensagem="Localização atualizada",
            timestamp=timestamp.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        return GPSResponse(
            sucesso=False,
            mensagem=f"Erro ao atualizar GPS: {str(e)}"
        )


@router.get("/motoboys/{restaurante_id}", response_model=List[MotoboyGPSInfo])
async def listar_motoboys_gps(
    restaurante_id: int,
    db: Session = Depends(get_db)
):
    """
    Lista todos os motoboys online com suas posições GPS.

    Usado pelo mapa em tempo real no painel do restaurante.
    """
    try:
        # Buscar motoboys online
        motoboys = db.query(models.Motoboy).filter(
            models.Motoboy.restaurante_id == restaurante_id,
            models.Motoboy.status == 'ativo',
            models.Motoboy.disponivel == True
        ).all()

        resultado = []
        for m in motoboys:
            # Verificar se tem posição GPS
            if m.latitude_atual and m.longitude_atual:
                resultado.append(MotoboyGPSInfo(
                    motoboy_id=m.id,
                    nome=m.nome,
                    latitude=m.latitude_atual,
                    longitude=m.longitude_atual,
                    velocidade=0.0,  # Será atualizado com último registro
                    ultima_atualizacao=m.ultima_atualizacao_gps.isoformat() if m.ultima_atualizacao_gps else "",
                    em_rota=m.em_rota or False,
                    entregas_pendentes=m.entregas_pendentes or 0
                ))

        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update-auth", response_model=GPSResponse)
async def atualizar_gps_auth(
    gps_data: GPSUpdateAuth,
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(get_db)
):
    """
    Atualiza GPS com autenticação JWT.

    motoboy_id e restaurante_id são extraídos do token JWT.
    Endpoint seguro para o app React PWA.
    """
    try:
        if not current_motoboy.disponivel:
            return GPSResponse(sucesso=False, mensagem="Motoboy está offline")

        timestamp = datetime.now()

        gps_record = models.GPSMotoboy(
            motoboy_id=current_motoboy.id,
            restaurante_id=current_motoboy.restaurante_id,
            latitude=gps_data.latitude,
            longitude=gps_data.longitude,
            velocidade=gps_data.velocidade or 0.0,
            timestamp=timestamp
        )
        db.add(gps_record)

        current_motoboy.latitude_atual = gps_data.latitude
        current_motoboy.longitude_atual = gps_data.longitude
        current_motoboy.ultima_atualizacao_gps = timestamp

        db.commit()

        return GPSResponse(
            sucesso=True,
            mensagem="Localização atualizada",
            timestamp=timestamp.isoformat()
        )

    except Exception as e:
        db.rollback()
        return GPSResponse(sucesso=False, mensagem=f"Erro ao atualizar GPS: {str(e)}")


@router.get("/historico/{motoboy_id}")
async def historico_gps(
    motoboy_id: int,
    limite: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retorna histórico de posições GPS de um motoboy.
    """
    try:
        registros = db.query(models.GPSMotoboy).filter(
            models.GPSMotoboy.motoboy_id == motoboy_id
        ).order_by(
            models.GPSMotoboy.timestamp.desc()
        ).limit(limite).all()

        return [{
            "id": r.id,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "velocidade": r.velocidade,
            "timestamp": r.timestamp.isoformat()
        } for r in registros]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
