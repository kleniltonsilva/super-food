# backend/app/demo_autopilot.py

"""
Demo Autopilot — Progride pedidos de restaurantes demo automaticamente.

Restaurantes demo são identificados por email *@superfood.test.
Quando um cliente faz pedido em restaurante demo:
  pendente → (2s) → confirmado → (2s) → em_preparo → (2s) → pronto
  → (2s) → em_entrega (animação frontend 60s) → entregue

A animação de entrega é 100% frontend (DemoMapAnimation.tsx).
O backend apenas espera 60s e marca como entregue.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from .database import SessionLocal
from . import models

logger = logging.getLogger("superfood.demo")

# Delays entre transições de status (em segundos)
DEMO_DELAYS = {
    "pendente": 2,
    "confirmado": 2,
    "em_preparo": 2,
    "pronto": 2,
    "em_entrega": 60,  # 1 minuto — animação frontend
}

# Intervalo do loop principal
LOOP_INTERVAL = 1  # segundo (para capturar transições de 2s)

# Nome do motoboy virtual
DEMO_MOTOBOY_NOME = "Carlos Demo"
DEMO_MOTOBOY_USUARIO = "demo_motoboy"
DEMO_MOTOBOY_TELEFONE = "11999999999"


def _get_demo_restaurant_ids(db) -> list[int]:
    """Retorna IDs dos restaurantes demo (email *@superfood.test)."""
    restaurantes = db.query(models.Restaurante.id).filter(
        models.Restaurante.email.like("%@superfood.test")
    ).all()
    return [r.id for r in restaurantes]


def _get_or_create_demo_motoboy(db, restaurante_id: int) -> models.Motoboy:
    """Retorna ou cria um motoboy virtual para o restaurante demo."""
    motoboy = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == restaurante_id,
        models.Motoboy.usuario == DEMO_MOTOBOY_USUARIO,
    ).first()
    if not motoboy:
        motoboy = models.Motoboy(
            restaurante_id=restaurante_id,
            nome=DEMO_MOTOBOY_NOME,
            usuario=DEMO_MOTOBOY_USUARIO,
            telefone=DEMO_MOTOBOY_TELEFONE,
            status="ativo",
            disponivel=True,
            senha="demo",
        )
        db.add(motoboy)
        db.commit()
        db.refresh(motoboy)
    return motoboy


def _update_status(db, pedido, new_status: str, ws_manager=None):
    """Atualiza status do pedido com histórico."""
    pedido.status = new_status
    pedido.atualizado_em = datetime.utcnow()

    # Atualiza histórico
    historico = pedido.historico_status or []
    historico.append({
        "status": new_status,
        "timestamp": datetime.utcnow().isoformat(),
    })
    pedido.historico_status = historico
    # Force SQLAlchemy to detect JSON change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(pedido, "historico_status")

    db.commit()
    logger.debug(f"Demo pedido #{pedido.id} → {new_status}")


def _seconds_since(dt: datetime | None) -> float:
    """Retorna segundos desde dt até agora."""
    if not dt:
        return 999999
    return (datetime.utcnow() - dt).total_seconds()


async def _broadcast_demo_update(ws_manager, restaurante_id: int, pedido_id: int, status: str):
    """Envia WebSocket broadcast para o restaurante e cliente."""
    if not ws_manager:
        return
    try:
        await ws_manager.broadcast({
            "tipo": "pedido_atualizado",
            "dados": {
                "pedido_id": pedido_id,
                "status": status,
            }
        }, restaurante_id)
    except Exception:
        pass


async def demo_autopilot_loop(ws_manager=None):
    """Loop principal do demo autopilot. Roda como background task."""
    logger.info("Demo autopilot iniciado")

    while True:
        try:
            await asyncio.sleep(LOOP_INTERVAL)
            db = SessionLocal()
            try:
                demo_ids = _get_demo_restaurant_ids(db)
                if not demo_ids:
                    continue

                # Busca pedidos ativos em restaurantes demo
                pedidos = db.query(models.Pedido).filter(
                    models.Pedido.restaurante_id.in_(demo_ids),
                    models.Pedido.status.in_(["pendente", "confirmado", "em_preparo", "pronto", "em_entrega"]),
                ).all()

                for pedido in pedidos:
                    status = pedido.status
                    elapsed = _seconds_since(pedido.atualizado_em)
                    delay = DEMO_DELAYS.get(status, 999999)

                    if elapsed >= delay:
                        next_status = _next_status(status)
                        if next_status:
                            if next_status == "em_entrega":
                                await _start_delivery(db, pedido, ws_manager)
                            elif next_status == "entregue":
                                await _finish_delivery(db, pedido, ws_manager)
                            else:
                                _update_status(db, pedido, next_status)
                                await _broadcast_demo_update(
                                    ws_manager, pedido.restaurante_id, pedido.id, next_status
                                )

                # Limpa pedidos demo antigos (mais de 1 hora)
                cutoff = datetime.utcnow() - timedelta(hours=1)
                old_pedidos = db.query(models.Pedido).filter(
                    models.Pedido.restaurante_id.in_(demo_ids),
                    models.Pedido.status.in_(["entregue", "finalizado", "cancelado"]),
                    models.Pedido.data_criacao < cutoff,
                ).all()
                for p in old_pedidos:
                    db.delete(p)
                if old_pedidos:
                    db.commit()

            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("Demo autopilot encerrado")
            break
        except Exception as e:
            logger.debug(f"Demo autopilot erro: {e}")
            await asyncio.sleep(5)


def _next_status(current: str) -> str | None:
    """Retorna o próximo status na sequência demo."""
    flow = ["pendente", "confirmado", "em_preparo", "pronto", "em_entrega", "entregue"]
    try:
        idx = flow.index(current)
        return flow[idx + 1] if idx + 1 < len(flow) else None
    except ValueError:
        return None


async def _start_delivery(db, pedido, ws_manager):
    """Inicia a simulação de entrega: cria motoboy + entrega."""
    motoboy = _get_or_create_demo_motoboy(db, pedido.restaurante_id)

    # Pega coordenadas do restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.id == pedido.restaurante_id
    ).first()

    # Posição do motoboy = restaurante (para tracking.motoboy não ser null)
    if restaurante and restaurante.latitude:
        motoboy.latitude_atual = restaurante.latitude
        motoboy.longitude_atual = restaurante.longitude
        motoboy.ultima_atualizacao_gps = datetime.utcnow()
        motoboy.disponivel = False
        motoboy.em_rota = True

    # Cria ou atualiza entrega
    entrega = db.query(models.Entrega).filter(
        models.Entrega.pedido_id == pedido.id
    ).first()
    if not entrega:
        entrega = models.Entrega(
            pedido_id=pedido.id,
            motoboy_id=motoboy.id,
            status="em_rota",
            delivery_started_at=datetime.utcnow(),
        )
        db.add(entrega)
    else:
        entrega.motoboy_id = motoboy.id
        entrega.status = "em_rota"
        entrega.delivery_started_at = datetime.utcnow()

    _update_status(db, pedido, "em_entrega")
    db.commit()
    await _broadcast_demo_update(ws_manager, pedido.restaurante_id, pedido.id, "em_entrega")


async def _finish_delivery(db, pedido, ws_manager):
    """Finaliza a entrega demo após 60s."""
    _update_status(db, pedido, "entregue")

    entrega = db.query(models.Entrega).filter(
        models.Entrega.pedido_id == pedido.id
    ).first()
    if entrega:
        entrega.status = "entregue"
        entrega.delivery_finished_at = datetime.utcnow()

    # Libera motoboy
    if entrega and entrega.motoboy_id:
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == entrega.motoboy_id
        ).first()
        if motoboy:
            motoboy.disponivel = True
            motoboy.em_rota = False

    db.commit()
    await _broadcast_demo_update(ws_manager, pedido.restaurante_id, pedido.id, "entregue")
