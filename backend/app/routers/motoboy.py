# backend/app/routers/motoboy.py

"""
Router App Motoboy - Entregas, status, estatísticas, ganhos
Sprint 3 da migração v4.0

Endpoints consumidos pelo app React PWA do motoboy.
Reutiliza funções utilitárias existentes de utils/motoboy_selector.py e utils/calculos.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date

from .. import models, database, auth

# Importar funções utilitárias existentes — NÃO reescrever lógica
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from utils.motoboy_selector import (
    finalizar_entrega_motoboy,
    marcar_motoboy_disponivel,
    obter_estatisticas_motoboy,
)
from utils.calculos import obter_ganhos_dia_motoboy

router = APIRouter(prefix="/motoboy", tags=["App Motoboy"])


# ========== Schemas ==========

class EntregaResponse(BaseModel):
    id: int
    pedido_id: int
    status: str
    distancia_km: Optional[float] = None
    atribuido_em: Optional[datetime] = None
    delivery_started_at: Optional[datetime] = None
    entregue_em: Optional[datetime] = None
    valor_motoboy: Optional[float] = None
    motivo_finalizacao: Optional[str] = None
    # Dados do pedido
    cliente_nome: Optional[str] = None
    cliente_telefone: Optional[str] = None
    endereco_entrega: Optional[str] = None
    latitude_entrega: Optional[float] = None
    longitude_entrega: Optional[float] = None
    valor_total: Optional[float] = None
    forma_pagamento: Optional[str] = None
    troco_para: Optional[float] = None
    observacoes: Optional[str] = None
    itens: Optional[str] = None
    comanda: Optional[str] = None


class FinalizarEntregaRequest(BaseModel):
    motivo: str = 'entregue'  # entregue, cliente_ausente, cancelado_cliente
    distancia_km: Optional[float] = None
    lat_atual: Optional[float] = None
    lon_atual: Optional[float] = None
    observacao: Optional[str] = None
    forma_pagamento_real: Optional[str] = None  # Dinheiro, Cartão/Pix, Misto
    valor_pago_dinheiro: Optional[float] = None
    valor_pago_cartao: Optional[float] = None


class StatusUpdateRequest(BaseModel):
    disponivel: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None


# ========== Helpers ==========

def _entrega_to_response(entrega: models.Entrega, pedido: models.Pedido = None, db: Session = None) -> dict:
    """Converte Entrega + Pedido para dict de resposta."""
    data = {
        "id": entrega.id,
        "pedido_id": entrega.pedido_id,
        "status": entrega.status,
        "distancia_km": entrega.distancia_km,
        "atribuido_em": entrega.atribuido_em.isoformat() if entrega.atribuido_em else None,
        "delivery_started_at": entrega.delivery_started_at.isoformat() if entrega.delivery_started_at else None,
        "entregue_em": entrega.entregue_em.isoformat() if entrega.entregue_em else None,
        "valor_motoboy": entrega.valor_motoboy,
        "valor_base_motoboy": getattr(entrega, 'valor_base_motoboy', None),
        "valor_extra_motoboy": getattr(entrega, 'valor_extra_motoboy', None),
        "motivo_finalizacao": entrega.motivo_finalizacao,
    }
    if pedido:
        pago_online = bool(pedido.pago_online)

        data.update({
            "cliente_nome": pedido.cliente_nome,
            "cliente_telefone": pedido.cliente_telefone,
            "endereco_entrega": pedido.endereco_entrega,
            "latitude_entrega": pedido.latitude_entrega,
            "longitude_entrega": pedido.longitude_entrega,
            "valor_total": pedido.valor_total,
            "forma_pagamento": pedido.forma_pagamento,
            "pago_online": pago_online,
            "pix_pago": pago_online,  # compatibilidade com app existente
            "troco_para": pedido.troco_para,
            "observacoes": pedido.observacoes,
            "itens": pedido.itens,
            "comanda": pedido.comanda,
        })
    return data


# ========== Endpoints ==========

@router.get("/entregas/pendentes")
def listar_entregas_pendentes(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Lista entregas atribuídas ao motoboy que ainda não foram iniciadas ou estão em rota."""
    entregas = db.query(models.Entrega).filter(
        models.Entrega.motoboy_id == current_motoboy.id,
        models.Entrega.status.in_(['pendente', 'em_rota'])
    ).order_by(
        models.Entrega.atribuido_em.asc()
    ).all()

    resultado = []
    for e in entregas:
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == e.pedido_id,
            models.Pedido.restaurante_id == current_motoboy.restaurante_id
        ).first()
        resultado.append(_entrega_to_response(e, pedido, db))

    return resultado


@router.get("/entregas/em-rota")
def listar_entregas_em_rota(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Lista entregas atualmente em rota do motoboy."""
    entregas = db.query(models.Entrega).filter(
        models.Entrega.motoboy_id == current_motoboy.id,
        models.Entrega.status == 'em_rota'
    ).order_by(
        models.Entrega.posicao_rota_otimizada.asc().nullslast(),
        models.Entrega.posicao_rota_original.asc().nullslast(),
        models.Entrega.atribuido_em.asc()
    ).all()

    resultado = []
    for e in entregas:
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == e.pedido_id,
            models.Pedido.restaurante_id == current_motoboy.restaurante_id
        ).first()
        resultado.append(_entrega_to_response(e, pedido, db))

    return resultado


@router.post("/entregas/{entrega_id}/iniciar")
def iniciar_entrega(
    entrega_id: int,
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Inicia a entrega — motoboy clicou 'Iniciar Entregas'."""
    entrega = db.query(models.Entrega).filter(
        models.Entrega.id == entrega_id,
        models.Entrega.motoboy_id == current_motoboy.id
    ).first()

    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    if entrega.status not in ['pendente', 'em_rota']:
        raise HTTPException(status_code=400, detail=f"Entrega não pode ser iniciada (status: {entrega.status})")

    # Atualizar entrega
    entrega.status = 'em_rota'
    entrega.delivery_started_at = datetime.utcnow()

    # Atualizar motoboy
    current_motoboy.em_rota = True

    # Atualizar pedido
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == entrega.pedido_id,
        models.Pedido.restaurante_id == current_motoboy.restaurante_id
    ).first()
    if pedido:
        pedido.status = 'em_entrega'

    db.commit()

    return {
        "sucesso": True,
        "entrega_id": entrega_id,
        "status": "em_rota",
        "delivery_started_at": entrega.delivery_started_at.isoformat()
    }


@router.post("/entregas/{entrega_id}/finalizar")
async def finalizar_entrega(
    entrega_id: int,
    dados: FinalizarEntregaRequest,
    request: Request,
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """
    Finaliza uma entrega com motivo e dados de pagamento.

    Motivos: 'entregue', 'cliente_ausente', 'cancelado_cliente'
    O motoboy SEMPRE recebe pagamento (exceto cancelado_restaurante que só o painel faz).
    """
    # Verificar que a entrega pertence ao motoboy
    entrega = db.query(models.Entrega).filter(
        models.Entrega.id == entrega_id,
        models.Entrega.motoboy_id == current_motoboy.id
    ).first()

    if not entrega:
        raise HTTPException(status_code=404, detail="Entrega não encontrada")

    # Validar motivo (motoboy não pode cancelar como restaurante)
    motivos_validos = ['entregue', 'cliente_ausente', 'cancelado_cliente']
    if dados.motivo not in motivos_validos:
        raise HTTPException(status_code=400, detail=f"Motivo inválido. Use: {', '.join(motivos_validos)}")

    # Buscar pedido para atualizar historico_status e broadcast
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == entrega.pedido_id,
        models.Pedido.restaurante_id == current_motoboy.restaurante_id
    ).first()

    # Reutilizar função existente de utils/motoboy_selector.py
    resultado = finalizar_entrega_motoboy(
        entrega_id=entrega_id,
        distancia_km=dados.distancia_km,
        session=db,
        motivo_finalizacao=dados.motivo,
        observacao=dados.observacao,
        lat_atual=dados.lat_atual,
        lon_atual=dados.lon_atual
    )

    if not resultado.get('sucesso'):
        raise HTTPException(status_code=400, detail=resultado.get('erro', 'Erro ao finalizar entrega'))

    # Atualizar dados de pagamento real e historico_status no pedido
    if pedido:
        if dados.forma_pagamento_real:
            pedido.forma_pagamento_real = dados.forma_pagamento_real
            if dados.valor_pago_dinheiro is not None:
                pedido.valor_pago_dinheiro = dados.valor_pago_dinheiro
            if dados.valor_pago_cartao is not None:
                pedido.valor_pago_cartao = dados.valor_pago_cartao

        # Registrar status no histórico
        historico = list(pedido.historico_status or [])
        historico.append({"status": dados.motivo, "timestamp": datetime.utcnow().isoformat()})
        pedido.historico_status = historico
        db.commit()

    # Broadcast para admin: entrega finalizada
    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "entrega_finalizada",
            "dados": {
                "pedido_id": entrega.pedido_id,
                "entrega_id": entrega.id,
                "comanda": pedido.comanda if pedido else None,
                "motoboy_nome": current_motoboy.nome,
                "motivo": dados.motivo,
            }
        }, current_motoboy.restaurante_id)

    return resultado


@router.get("/entregas/historico")
def historico_entregas(
    data_inicio: Optional[date] = Query(None),
    data_fim: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Histórico de entregas finalizadas do motoboy com paginação."""
    # Status que aparecem no histórico (todos que geram pagamento + cancelado_restaurante)
    status_historico = ['entregue', 'cliente_ausente', 'cancelado_cliente', 'cancelado_restaurante']

    query = db.query(models.Entrega).filter(
        models.Entrega.motoboy_id == current_motoboy.id,
        models.Entrega.status.in_(status_historico)
    )

    if data_inicio:
        query = query.filter(models.Entrega.entregue_em >= datetime.combine(data_inicio, datetime.min.time()))
    if data_fim:
        query = query.filter(models.Entrega.entregue_em <= datetime.combine(data_fim, datetime.max.time()))

    total = query.count()
    entregas = query.order_by(
        models.Entrega.entregue_em.desc()
    ).offset((page - 1) * limit).limit(limit).all()

    resultado = []
    for e in entregas:
        pedido = db.query(models.Pedido).filter(
            models.Pedido.id == e.pedido_id,
            models.Pedido.restaurante_id == current_motoboy.restaurante_id
        ).first()
        resultado.append(_entrega_to_response(e, pedido, db))

    return {
        "entregas": resultado,
        "total": total,
        "page": page,
        "pages": (total + limit - 1) // limit if total > 0 else 1
    }


@router.put("/status")
def atualizar_status(
    dados: StatusUpdateRequest,
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Alterna disponibilidade do motoboy (online/offline)."""
    resultado = marcar_motoboy_disponivel(
        motoboy_id=current_motoboy.id,
        disponivel=dados.disponivel,
        latitude=dados.latitude,
        longitude=dados.longitude,
        session=db
    )

    if not resultado.get('sucesso'):
        raise HTTPException(status_code=400, detail=resultado.get('erro', 'Erro ao atualizar status'))

    return resultado


@router.get("/config")
def get_config_motoboy(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Retorna config do restaurante relevante para o motoboy."""
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == current_motoboy.restaurante_id
    ).first()

    return {
        "permitir_ver_saldo": config.permitir_ver_saldo_motoboy if config else True,
    }


@router.get("/estatisticas")
def get_estatisticas(
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Estatísticas completas do motoboy (totais + dia)."""
    resultado = obter_estatisticas_motoboy(
        motoboy_id=current_motoboy.id,
        session=db
    )

    if resultado is None:
        raise HTTPException(status_code=404, detail="Motoboy não encontrado")

    return resultado


@router.get("/ganhos/detalhado")
def get_ganhos_detalhado(
    data: Optional[date] = Query(None, description="Data no formato YYYY-MM-DD (default: hoje)"),
    current_motoboy: models.Motoboy = Depends(auth.get_current_motoboy),
    db: Session = Depends(database.get_db)
):
    """Ganhos detalhados do dia com lista de entregas."""
    resultado = obter_ganhos_dia_motoboy(
        motoboy_id=current_motoboy.id,
        data=data,
        session=db
    )

    return resultado
