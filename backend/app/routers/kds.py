"""
Router KDS - Kitchen Display System endpoints
Sprint 18 — KDS / Comanda Digital
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .. import models, database, auth

router = APIRouter(prefix="/kds", tags=["KDS"])


# ========== Schemas ==========

class StatusUpdateKds(BaseModel):
    status: str  # NOVO, FAZENDO, FEITO, PRONTO


# ========== Helpers ==========

def _pedido_cozinha_to_dict(pc: models.PedidoCozinha, pedido: models.Pedido) -> dict:
    """Converte PedidoCozinha + Pedido para dict de resposta."""
    itens = []
    if pedido.carrinho_json:
        for item in pedido.carrinho_json:
            itens.append({
                "nome": item.get("nome", ""),
                "quantidade": item.get("quantidade", 1),
                "observacoes": item.get("observacoes") or item.get("observacao") or "",
                "variacoes": item.get("variacoes", []),
                "produto_id": item.get("produto_id"),
            })
    elif pedido.itens:
        # Fallback: itens é texto livre
        for linha in pedido.itens.split("\n"):
            linha = linha.strip()
            if linha:
                itens.append({"nome": linha, "quantidade": 1, "observacoes": "", "variacoes": [], "produto_id": None})

    return {
        "id": pc.id,
        "pedido_id": pc.pedido_id,
        "status": pc.status,
        "cozinheiro_id": pc.cozinheiro_id,
        "urgente": pc.urgente or False,
        "pausado": pc.pausado or False,
        "pausado_em": pc.pausado_em.isoformat() if pc.pausado_em else None,
        "despausado_em": pc.despausado_em.isoformat() if pc.despausado_em else None,
        "posicao_original": pc.posicao_original,
        "criado_em": pc.criado_em.isoformat() if pc.criado_em else None,
        "iniciado_em": pc.iniciado_em.isoformat() if pc.iniciado_em else None,
        "feito_em": pc.feito_em.isoformat() if pc.feito_em else None,
        "pronto_em": pc.pronto_em.isoformat() if pc.pronto_em else None,
        "comanda": pedido.comanda,
        "tipo": pedido.tipo,
        "tipo_entrega": pedido.tipo_entrega,
        "numero_mesa": pedido.numero_mesa,
        "cliente_nome": pedido.cliente_nome,
        "observacoes": pedido.observacoes,
        "itens": itens,
    }


def _produto_ids_do_pedido(pedido: models.Pedido) -> set:
    """Extrai os produto_ids do carrinho_json do pedido."""
    ids = set()
    if pedido.carrinho_json:
        for item in pedido.carrinho_json:
            pid = item.get("produto_id")
            if pid:
                ids.add(int(pid))
    return ids


# ========== Endpoints ==========

@router.get("/pedidos")
def listar_pedidos_kds(
    status_filter: Optional[str] = None,
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Lista pedidos no KDS. Filtra por produtos se cozinheiro é modo individual."""
    rest_id = current_cozinheiro.restaurante_id

    query = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.restaurante_id == rest_id
    )

    if status_filter:
        statuses = [s.strip().upper() for s in status_filter.split(",")]
        query = query.filter(models.PedidoCozinha.status.in_(statuses))
    else:
        # Por padrão, não mostrar PRONTO com mais de 2h
        query = query.filter(
            models.PedidoCozinha.status.in_(['NOVO', 'FAZENDO', 'FEITO', 'PRONTO'])
        )

    query = query.order_by(models.PedidoCozinha.criado_em.asc())
    pedidos_cozinha = query.all()

    # Buscar pedidos associados
    pedido_ids = [pc.pedido_id for pc in pedidos_cozinha]
    pedidos = {}
    if pedido_ids:
        for p in db.query(models.Pedido).filter(models.Pedido.id.in_(pedido_ids)).all():
            pedidos[p.id] = p

    # Filtrar por produtos se modo individual
    resultado = []
    if current_cozinheiro.modo == 'individual':
        meus_produto_ids = {cp.produto_id for cp in current_cozinheiro.produtos}
        for pc in pedidos_cozinha:
            pedido = pedidos.get(pc.pedido_id)
            if not pedido:
                continue
            produto_ids_pedido = _produto_ids_do_pedido(pedido)
            # Mostrar se pelo menos 1 produto do pedido está nos meus
            if meus_produto_ids & produto_ids_pedido:
                resultado.append(_pedido_cozinha_to_dict(pc, pedido))
    else:
        for pc in pedidos_cozinha:
            pedido = pedidos.get(pc.pedido_id)
            if pedido:
                resultado.append(_pedido_cozinha_to_dict(pc, pedido))

    return resultado


@router.patch("/pedidos/{pedido_cozinha_id}/status")
async def atualizar_status_kds(
    pedido_cozinha_id: int,
    dados: StatusUpdateKds,
    request: Request,
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Atualiza status do pedido no KDS: NOVO→FAZENDO→FEITO→PRONTO."""
    pc = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.id == pedido_cozinha_id,
        models.PedidoCozinha.restaurante_id == current_cozinheiro.restaurante_id
    ).first()

    if not pc:
        raise HTTPException(404, "Pedido não encontrado no KDS")

    agora = datetime.utcnow()
    novo_status = dados.status.upper()

    # Validar transições
    transicoes_validas = {
        'NOVO': ['FAZENDO'],
        'FAZENDO': ['FEITO'],
        'FEITO': ['PRONTO', 'NOVO'],  # NOVO = refazer
        'PRONTO': [],
    }

    if novo_status not in transicoes_validas.get(pc.status, []):
        raise HTTPException(400, f"Transição inválida: {pc.status} → {novo_status}")

    # Bloquear ações em pedidos pausados
    if pc.pausado and novo_status != 'NOVO':
        raise HTTPException(400, "Pedido pausado pelo admin — não é possível alterar status")

    pc.status = novo_status

    if novo_status == 'FAZENDO':
        pc.iniciado_em = agora
        pc.cozinheiro_id = current_cozinheiro.id
    elif novo_status == 'FEITO':
        pc.feito_em = agora
    elif novo_status == 'PRONTO':
        pc.pronto_em = agora
        # Sincronizar: atualizar status do Pedido para 'pronto'
        pedido_sync = db.query(models.Pedido).filter(models.Pedido.id == pc.pedido_id).first()
        if pedido_sync:
            pedido_sync.status = 'pronto'
            pedido_sync.atualizado_em = agora
            # Calcular tempo_preparo_real_min
            if pedido_sync.historico_status:
                ts_pendente = None
                for h in pedido_sync.historico_status:
                    if h.get("status") == "pendente":
                        ts_pendente = h.get("timestamp")
                        break
                if ts_pendente:
                    try:
                        dt_pendente = datetime.fromisoformat(ts_pendente)
                        delta = (agora - dt_pendente).total_seconds() / 60
                        pedido_sync.tempo_preparo_real_min = int(delta)
                    except (ValueError, TypeError):
                        pass
            historico = list(pedido_sync.historico_status or [])
            historico.append({"status": "pronto", "timestamp": agora.isoformat()})
            pedido_sync.historico_status = historico
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(pedido_sync, "historico_status")
    elif novo_status == 'NOVO':
        # Refazer — limpa timestamps
        pc.iniciado_em = None
        pc.feito_em = None
        pc.pronto_em = None
        pc.cozinheiro_id = None

    db.commit()

    # Broadcast KDS WebSocket
    kds_ws = getattr(request.app.state, 'kds_manager', None)
    if kds_ws:
        pedido = db.query(models.Pedido).filter(models.Pedido.id == pc.pedido_id).first()
        await kds_ws.broadcast({
            "tipo": "kds:pedido_atualizado",
            "dados": {
                "id": pc.id,
                "pedido_id": pc.pedido_id,
                "status": pc.status,
                "cozinheiro_id": pc.cozinheiro_id,
                "comanda": pedido.comanda if pedido else None,
            }
        }, current_cozinheiro.restaurante_id)

    # Também notificar o painel admin
    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        pedido = db.query(models.Pedido).filter(models.Pedido.id == pc.pedido_id).first()
        await ws.broadcast({
            "tipo": "kds_status_atualizado",
            "dados": {
                "pedido_cozinha_id": pc.id,
                "pedido_id": pc.pedido_id,
                "status": pc.status,
                "comanda": pedido.comanda if pedido else None,
            }
        }, current_cozinheiro.restaurante_id)

    return {"id": pc.id, "status": pc.status}


@router.post("/pedidos/{pedido_cozinha_id}/assumir")
async def assumir_pedido_kds(
    pedido_cozinha_id: int,
    request: Request,
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Cozinheiro assume pedido NOVO (set cozinheiro_id + FAZENDO)."""
    pc = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.id == pedido_cozinha_id,
        models.PedidoCozinha.restaurante_id == current_cozinheiro.restaurante_id
    ).first()

    if not pc:
        raise HTTPException(404, "Pedido não encontrado no KDS")

    if pc.status != 'NOVO':
        raise HTTPException(400, "Só é possível assumir pedidos com status NOVO")

    agora = datetime.utcnow()
    pc.status = 'FAZENDO'
    pc.cozinheiro_id = current_cozinheiro.id
    pc.iniciado_em = agora
    db.commit()

    # Broadcast
    kds_ws = getattr(request.app.state, 'kds_manager', None)
    if kds_ws:
        pedido = db.query(models.Pedido).filter(models.Pedido.id == pc.pedido_id).first()
        await kds_ws.broadcast({
            "tipo": "kds:pedido_atualizado",
            "dados": {
                "id": pc.id,
                "pedido_id": pc.pedido_id,
                "status": pc.status,
                "cozinheiro_id": pc.cozinheiro_id,
                "comanda": pedido.comanda if pedido else None,
            }
        }, current_cozinheiro.restaurante_id)

    return {"id": pc.id, "status": pc.status, "cozinheiro_id": pc.cozinheiro_id}


@router.post("/pedidos/{pedido_cozinha_id}/refazer")
async def refazer_pedido_kds(
    pedido_cozinha_id: int,
    request: Request,
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Reset FEITO→NOVO: limpa timestamps, remove cozinheiro_id."""
    pc = db.query(models.PedidoCozinha).filter(
        models.PedidoCozinha.id == pedido_cozinha_id,
        models.PedidoCozinha.restaurante_id == current_cozinheiro.restaurante_id
    ).first()

    if not pc:
        raise HTTPException(404, "Pedido não encontrado no KDS")

    if pc.status != 'FEITO':
        raise HTTPException(400, "Só é possível refazer pedidos com status FEITO")

    pc.status = 'NOVO'
    pc.iniciado_em = None
    pc.feito_em = None
    pc.pronto_em = None
    pc.cozinheiro_id = None
    db.commit()

    # Broadcast
    kds_ws = getattr(request.app.state, 'kds_manager', None)
    if kds_ws:
        pedido = db.query(models.Pedido).filter(models.Pedido.id == pc.pedido_id).first()
        await kds_ws.broadcast({
            "tipo": "kds:pedido_atualizado",
            "dados": {
                "id": pc.id,
                "pedido_id": pc.pedido_id,
                "status": 'NOVO',
                "cozinheiro_id": None,
                "comanda": pedido.comanda if pedido else None,
            }
        }, current_cozinheiro.restaurante_id)

    return {"id": pc.id, "status": pc.status}


@router.get("/config")
def get_config_kds(
    current_cozinheiro: models.Cozinheiro = Depends(auth.get_current_cozinheiro),
    db: Session = Depends(database.get_db)
):
    """Retorna config KDS do restaurante."""
    config = db.query(models.ConfigCozinha).filter(
        models.ConfigCozinha.restaurante_id == current_cozinheiro.restaurante_id
    ).first()

    if not config:
        return {
            "kds_ativo": False,
            "tempo_alerta_min": 15,
            "tempo_critico_min": 25,
            "som_novo_pedido": True,
        }

    return {
        "kds_ativo": config.kds_ativo,
        "tempo_alerta_min": config.tempo_alerta_min,
        "tempo_critico_min": config.tempo_critico_min,
        "som_novo_pedido": config.som_novo_pedido,
    }
