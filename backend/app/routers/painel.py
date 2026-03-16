# backend/app/routers/painel.py

"""
Router Painel Restaurante - Todos os endpoints CRUD para o dashboard React
Sprint 1 da migração v4.0
Todos os endpoints requerem auth JWT do restaurante.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta, date

from .. import models, database, auth
from ..cache import invalidate_cardapio

router = APIRouter(prefix="/painel", tags=["Painel Restaurante"])


def get_rest(current_restaurante=Depends(auth.get_current_restaurante)):
    return current_restaurante


def verificar_billing_ativo(rest: models.Restaurante = Depends(get_rest)):
    """Bloqueia operações quando billing suspenso/cancelado. Retorna 403."""
    if rest.billing_status in ("suspended_billing", "canceled_billing"):
        raise HTTPException(
            status_code=403,
            detail="Assinatura suspensa ou cancelada. Regularize seu pagamento para continuar.",
        )
    return rest


def _commit_and_invalidate(db: Session, rest_id: int):
    """Commit + invalida cache do cardapio (para mutacoes em produtos/categorias/combos)"""
    db.commit()
    invalidate_cardapio(rest_id)


async def _broadcast_imprimir_pedido(request: Request, db: Session, pedido, rest_id: int):
    """Envia broadcast de impressão se impressao_automatica está ativa."""
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest_id
    ).first()
    if not config or not config.impressao_automatica:
        return
    pm = getattr(request.app.state, 'printer_manager', None)
    if pm:
        await pm.broadcast({
            "tipo": "imprimir_pedido",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
        }, rest_id)


# ============================================================
# 1.2 DASHBOARD / MÉTRICAS
# ============================================================

@router.get("/dashboard")
def dashboard(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    hoje = date.today()
    inicio_dia = datetime.combine(hoje, datetime.min.time())
    fim_dia = datetime.combine(hoje, datetime.max.time())

    pedidos_hoje = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.data_criacao >= inicio_dia,
        models.Pedido.data_criacao <= fim_dia
    )

    total_pedidos = pedidos_hoje.count()
    pedidos_pendentes = pedidos_hoje.filter(models.Pedido.status == 'pendente').count()
    pedidos_em_preparo = pedidos_hoje.filter(models.Pedido.status == 'em_preparo').count()

    faturamento = db.query(func.coalesce(func.sum(models.Pedido.valor_total), 0.0)).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.data_criacao >= inicio_dia,
        models.Pedido.data_criacao <= fim_dia,
        models.Pedido.status.notin_(['cancelado', 'recusado'])
    ).scalar()

    motoboys_online = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.status == 'ativo',
        models.Motoboy.disponivel == True
    ).count()

    motoboys_em_rota = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.em_rota == True
    ).count()

    return {
        "pedidos_hoje": total_pedidos,
        "pedidos_pendentes": pedidos_pendentes,
        "pedidos_em_preparo": pedidos_em_preparo,
        "faturamento_hoje": round(float(faturamento), 2),
        "motoboys_online": motoboys_online,
        "motoboys_em_rota": motoboys_em_rota,
    }


@router.get("/dashboard/grafico")
def dashboard_grafico(
    dias: int = Query(7, ge=1, le=90),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    inicio = datetime.combine(date.today() - timedelta(days=dias - 1), datetime.min.time())
    pedidos = db.query(
        func.date(models.Pedido.data_criacao).label('data'),
        func.count(models.Pedido.id).label('total'),
        func.coalesce(func.sum(models.Pedido.valor_total), 0.0).label('faturamento')
    ).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.data_criacao >= inicio,
        models.Pedido.status.notin_(['cancelado', 'recusado'])
    ).group_by(func.date(models.Pedido.data_criacao)).all()

    return [{"data": str(p.data), "total": p.total, "faturamento": round(float(p.faturamento), 2)} for p in pedidos]


# ============================================================
# 1.3 PEDIDOS
# ============================================================

@router.get("/pedidos")
def listar_pedidos(
    status: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    tipo: Optional[str] = None,
    busca: Optional[str] = None,
    limite: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    q = db.query(models.Pedido).filter(models.Pedido.restaurante_id == rest.id)
    if status:
        q = q.filter(models.Pedido.status == status)
    if tipo:
        q = q.filter(models.Pedido.tipo_entrega == tipo)
    if busca:
        q = q.filter(or_(
            models.Pedido.cliente_nome.ilike(f"%{busca}%"),
            models.Pedido.comanda.ilike(f"%{busca}%"),
            models.Pedido.cliente_telefone.ilike(f"%{busca}%")
        ))
    if data_inicio:
        q = q.filter(models.Pedido.data_criacao >= data_inicio)
    if data_fim:
        q = q.filter(models.Pedido.data_criacao <= data_fim)

    total = q.count()
    pedidos = q.order_by(desc(models.Pedido.data_criacao)).offset(offset).limit(limite).all()

    return {
        "total": total,
        "pedidos": [{
            "id": p.id, "comanda": p.comanda, "tipo": p.tipo, "tipo_entrega": p.tipo_entrega,
            "origem": p.origem, "cliente_nome": p.cliente_nome, "cliente_telefone": p.cliente_telefone,
            "endereco_entrega": p.endereco_entrega, "numero_mesa": p.numero_mesa,
            "itens": p.itens, "carrinho_json": p.carrinho_json, "observacoes": p.observacoes,
            "valor_total": p.valor_total, "forma_pagamento": p.forma_pagamento,
            "status": p.status, "despachado": p.despachado,
            "data_criacao": p.data_criacao.isoformat() if p.data_criacao else None,
            "marketplace_source": p.marketplace_source,
            "marketplace_display_id": p.marketplace_display_id,
        } for p in pedidos]
    }


@router.get("/pedidos/{pedido_id}")
def detalhe_pedido(
    pedido_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).options(
        joinedload(models.Pedido.entrega),
        joinedload(models.Pedido.itens_detalhados)
    ).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")

    entrega_data = None
    if pedido.entrega:
        e = pedido.entrega
        motoboy = db.query(models.Motoboy).filter(models.Motoboy.id == e.motoboy_id).first() if e.motoboy_id else None
        entrega_data = {
            "id": e.id, "motoboy_id": e.motoboy_id,
            "motoboy_nome": motoboy.nome if motoboy else None,
            "distancia_km": e.distancia_km, "status": e.status,
            "valor_entrega": e.valor_entrega, "valor_motoboy": e.valor_motoboy,
            "atribuido_em": e.atribuido_em.isoformat() if e.atribuido_em else None,
            "entregue_em": e.entregue_em.isoformat() if e.entregue_em else None,
        }

    return {
        "id": pedido.id, "comanda": pedido.comanda, "tipo": pedido.tipo,
        "tipo_entrega": pedido.tipo_entrega, "origem": pedido.origem,
        "cliente_nome": pedido.cliente_nome, "cliente_telefone": pedido.cliente_telefone,
        "endereco_entrega": pedido.endereco_entrega,
        "latitude_entrega": pedido.latitude_entrega, "longitude_entrega": pedido.longitude_entrega,
        "numero_mesa": pedido.numero_mesa,
        "itens": pedido.itens, "carrinho_json": pedido.carrinho_json,
        "observacoes": pedido.observacoes,
        "valor_total": pedido.valor_total, "forma_pagamento": pedido.forma_pagamento,
        "troco_para": pedido.troco_para,
        "forma_pagamento_real": pedido.forma_pagamento_real,
        "cupom_desconto": pedido.cupom_desconto, "valor_desconto": pedido.valor_desconto,
        "status": pedido.status, "despachado": pedido.despachado,
        "data_criacao": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
        "atualizado_em": pedido.atualizado_em.isoformat() if pedido.atualizado_em else None,
        "entrega": entrega_data,
        "itens_detalhados": [{
            "id": i.id, "produto_id": i.produto_id,
            "quantidade": i.quantidade, "preco_unitario": i.preco_unitario,
            "observacoes": i.observacoes
        } for i in pedido.itens_detalhados],
        "marketplace_source": pedido.marketplace_source,
        "marketplace_order_id": pedido.marketplace_order_id,
        "marketplace_display_id": pedido.marketplace_display_id,
    }


class PedidoManualRequest(BaseModel):
    tipo_entrega: str  # entrega, retirada, mesa
    cliente_nome: str
    cliente_telefone: Optional[str] = None
    endereco_entrega: Optional[str] = None
    numero_mesa: Optional[str] = None
    itens: str
    valor_total: float
    forma_pagamento: Optional[str] = None
    troco_para: Optional[float] = None
    tempo_estimado: Optional[int] = None
    observacoes: Optional[str] = None


@router.post("/pedidos")
async def criar_pedido_manual(
    dados: PedidoManualRequest,
    request: Request,
    rest: models.Restaurante = Depends(verificar_billing_ativo),
    db: Session = Depends(database.get_db)
):
    proxima_comanda = _gerar_proxima_comanda(db, rest.id)

    pedido = models.Pedido(
        restaurante_id=rest.id,
        comanda=str(proxima_comanda),
        tipo=dados.tipo_entrega.capitalize(),
        origem="manual",
        tipo_entrega=dados.tipo_entrega,
        cliente_nome=dados.cliente_nome,
        cliente_telefone=dados.cliente_telefone,
        endereco_entrega=dados.endereco_entrega,
        numero_mesa=dados.numero_mesa,
        itens=dados.itens,
        valor_total=dados.valor_total,
        forma_pagamento=dados.forma_pagamento,
        troco_para=dados.troco_para,
        tempo_estimado=dados.tempo_estimado,
        observacoes=dados.observacoes,
        status='pendente',
        historico_status=[{"status": "pendente", "timestamp": datetime.utcnow().isoformat()}],
        data_criacao=datetime.utcnow()
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "novo_pedido",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda, "cliente_nome": pedido.cliente_nome, "valor_total": pedido.valor_total}
        }, rest.id)

    await _broadcast_imprimir_pedido(request, db, pedido, rest.id)

    return {"id": pedido.id, "comanda": pedido.comanda, "status": pedido.status}


class StatusUpdate(BaseModel):
    status: str


@router.put("/pedidos/{pedido_id}/status")
async def atualizar_status_pedido(
    pedido_id: int, dados: StatusUpdate,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    agora = datetime.utcnow()
    pedido.status = dados.status
    pedido.atualizado_em = agora

    # Registrar histórico de status
    historico = list(pedido.historico_status or [])
    historico.append({"status": dados.status, "timestamp": agora.isoformat()})
    pedido.historico_status = historico

    # Auto-calcular tempo_preparo_real_min quando muda para 'pronto'
    if dados.status == 'pronto' and pedido.historico_status:
        ts_pendente = None
        for h in pedido.historico_status:
            if h.get("status") == "pendente":
                ts_pendente = h.get("timestamp")
                break
        if ts_pendente:
            try:
                dt_pendente = datetime.fromisoformat(ts_pendente)
                delta = (agora - dt_pendente).total_seconds() / 60
                pedido.tempo_preparo_real_min = int(delta)
            except (ValueError, TypeError):
                pass

    # Criar alerta de atraso quando pedido é entregue/finalizado
    if dados.status == 'entregue':
        _verificar_e_criar_alerta_atraso(db, rest, pedido)

    # Auto-lançar venda no caixa quando pedido é entregue
    if dados.status == 'entregue' and pedido.valor_total and pedido.valor_total > 0:
        caixa_aberto = db.query(models.Caixa).filter(
            models.Caixa.restaurante_id == rest.id,
            models.Caixa.status == 'aberto'
        ).first()
        if caixa_aberto:
            forma = (pedido.forma_pagamento_real or pedido.forma_pagamento or '').strip().lower()
            # Mapear forma de pagamento para categoria
            if 'pix' in forma:
                campo_pgto = 'pix'
            elif 'cart' in forma or 'credito' in forma or 'debito' in forma or 'cartão' in forma:
                campo_pgto = 'cartao'
            elif 'vale' in forma:
                campo_pgto = 'vale'
            else:
                campo_pgto = 'dinheiro'

            mov = models.MovimentacaoCaixa(
                caixa_id=caixa_aberto.id,
                tipo='venda',
                valor=pedido.valor_total,
                descricao=f"Pedido #{pedido.comanda} — {(pedido.forma_pagamento_real or pedido.forma_pagamento or 'N/I')}",
                forma_pagamento=campo_pgto,
                pedido_id=pedido.id,
            )
            db.add(mov)
            caixa_aberto.total_vendas = (caixa_aberto.total_vendas or 0) + pedido.valor_total
            if campo_pgto == 'dinheiro':
                caixa_aberto.total_dinheiro = (caixa_aberto.total_dinheiro or 0) + pedido.valor_total
            elif campo_pgto == 'cartao':
                caixa_aberto.total_cartao = (caixa_aberto.total_cartao or 0) + pedido.valor_total
            elif campo_pgto == 'pix':
                caixa_aberto.total_pix = (caixa_aberto.total_pix or 0) + pedido.valor_total
            elif campo_pgto == 'vale':
                caixa_aberto.total_vale = (caixa_aberto.total_vale or 0) + pedido.valor_total

    db.commit()

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "pedido_atualizado",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda, "status": pedido.status}
        }, rest.id)
        if dados.status in ('entregue', 'pronto'):
            await ws.broadcast({"tipo": "tempo_medio_atualizado", "dados": {}}, rest.id)

    # Notificar marketplace se pedido veio de integração
    if pedido.marketplace_source:
        im = getattr(request.app.state, 'integration_manager', None)
        if im:
            await im.notify_status_change(db, pedido, dados.status)

    return {"id": pedido.id, "status": pedido.status}


class DespachoRequest(BaseModel):
    motoboy_id: Optional[int] = None


@router.post("/pedidos/{pedido_id}/despachar")
async def despachar_pedido(
    pedido_id: int, dados: DespachoRequest,
    request: Request,
    rest: models.Restaurante = Depends(verificar_billing_ativo),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")

    # Ler modo de prioridade da config
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    modo = config.modo_prioridade_entrega if config else 'rapido_economico'

    # Modo manual: motoboy_id obrigatório
    if modo == 'manual' and not dados.motoboy_id:
        raise HTTPException(400, "Modo manual ativo — selecione um motoboy")

    if dados.motoboy_id:
        # Seleção manual (funciona em qualquer modo)
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == dados.motoboy_id,
            models.Motoboy.restaurante_id == rest.id,
            models.Motoboy.status == 'ativo'
        ).first()
        if not motoboy:
            raise HTTPException(404, "Motoboy não encontrado ou inativo")
    else:
        # Seleção automática com novas regras (GPS + distribuição diária)
        from utils.motoboy_selector import selecionar_motoboy_para_rota
        resultado = selecionar_motoboy_para_rota(rest.id, session=db)
        if not resultado:
            raise HTTPException(
                400,
                "Nenhum motoboy elegível (verificar: ativo, disponível, GPS atualizado, dentro de 50m do restaurante, sem entregas pendentes)"
            )
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == resultado['motoboy_id']
        ).first()

    # Calcular distância restaurante → endereço de entrega
    distancia_km = None
    if rest.latitude and rest.longitude:
        lat_entrega = pedido.latitude_entrega
        lon_entrega = pedido.longitude_entrega
        if (not lat_entrega or not lon_entrega) and pedido.endereco_entrega:
            try:
                from utils.mapbox_api import geocode_address
                coords = geocode_address(pedido.endereco_entrega)
                if coords:
                    lat_entrega, lon_entrega = coords
                    pedido.latitude_entrega = lat_entrega
                    pedido.longitude_entrega = lon_entrega
            except Exception:
                pass
        if lat_entrega and lon_entrega:
            from utils.haversine import haversine
            distancia_km = round(haversine(
                (rest.latitude, rest.longitude),
                (lat_entrega, lon_entrega)
            ), 2)

    # Aplicar TSP se modo automático e há coordenadas
    tempo_estimado_min = None
    if modo != 'manual' and distancia_km is not None:
        try:
            from utils.tsp_optimizer import calcular_metricas_rota
            metricas = calcular_metricas_rota(
                (rest.latitude, rest.longitude),
                [{'lat': pedido.latitude_entrega, 'lon': pedido.longitude_entrega, 'pedido_id': pedido.id}]
            )
            tempo_estimado_min = metricas.get('tempo_total_min')
        except Exception:
            pass

    entrega = models.Entrega(
        pedido_id=pedido.id,
        motoboy_id=motoboy.id,
        status='pendente',
        atribuido_em=datetime.utcnow(),
        distancia_km=distancia_km,
        tempo_entrega=tempo_estimado_min
    )
    db.add(entrega)
    pedido.despachado = True
    pedido.status = 'em_preparo'
    motoboy.entregas_pendentes = (motoboy.entregas_pendentes or 0) + 1
    motoboy.ultima_rota_em = datetime.utcnow()
    db.commit()

    # Broadcast WebSocket
    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "pedido_despachado",
            "dados": {
                "pedido_id": pedido.id, "comanda": pedido.comanda,
                "motoboy_id": motoboy.id, "motoboy_nome": motoboy.nome,
                "distancia_km": distancia_km, "tempo_estimado_min": tempo_estimado_min,
            }
        }, rest.id)

    return {
        "id": pedido.id, "motoboy_id": motoboy.id, "motoboy_nome": motoboy.nome,
        "distancia_km": distancia_km, "tempo_estimado_min": tempo_estimado_min,
        "modo": modo,
    }


class CancelarPedidoRequest(BaseModel):
    senha: Optional[str] = None


@router.put("/pedidos/{pedido_id}/cancelar")
async def cancelar_pedido(
    pedido_id: int,
    request: Request,
    dados: CancelarPedidoRequest = CancelarPedidoRequest(),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")

    # Pedidos entregues/pagos requerem senha do admin
    status_protegidos = ('entregue', 'pago', 'finalizado')
    if pedido.status in status_protegidos:
        if not dados.senha:
            raise HTTPException(400, "Senha do administrador necessária para cancelar pedido já entregue")
        if not rest.verificar_senha(dados.senha.strip()):
            raise HTTPException(403, "Senha incorreta")

    status_anterior = pedido.status
    pedido.status = 'cancelado'
    pedido.atualizado_em = datetime.utcnow()

    # Registrar histórico de status
    historico = list(pedido.historico_status or [])
    historico.append({"status": "cancelado", "timestamp": datetime.utcnow().isoformat()})
    pedido.historico_status = historico

    # Cancelar entrega associada e liberar motoboy
    entrega_cancelada = None
    motoboy_id_cancelado = None
    entrega = db.query(models.Entrega).filter(
        models.Entrega.pedido_id == pedido.id,
        models.Entrega.status.in_(['pendente', 'em_rota'])
    ).first()
    if entrega:
        entrega_cancelada = entrega.id
        motoboy_id_cancelado = entrega.motoboy_id
        entrega.status = 'cancelado'
        entrega.motivo_finalizacao = 'cancelado_restaurante'
        if entrega.motoboy_id:
            motoboy = db.query(models.Motoboy).filter(models.Motoboy.id == entrega.motoboy_id).first()
            if motoboy and motoboy.entregas_pendentes > 0:
                motoboy.entregas_pendentes -= 1

    # Reverter lançamento no caixa se pedido havia sido registrado
    if status_anterior in status_protegidos and pedido.valor_total and pedido.valor_total > 0:
        caixa_aberto = db.query(models.Caixa).filter(
            models.Caixa.restaurante_id == rest.id,
            models.Caixa.status == 'aberto'
        ).first()
        if caixa_aberto:
            # Verificar se existe movimentação de venda para este pedido
            mov_venda = db.query(models.MovimentacaoCaixa).filter(
                models.MovimentacaoCaixa.caixa_id == caixa_aberto.id,
                models.MovimentacaoCaixa.pedido_id == pedido.id,
                models.MovimentacaoCaixa.tipo == 'venda'
            ).first()
            if mov_venda:
                # Criar movimentação de estorno
                estorno = models.MovimentacaoCaixa(
                    caixa_id=caixa_aberto.id,
                    tipo='estorno',
                    valor=mov_venda.valor,
                    descricao=f"Estorno - Pedido #{pedido.comanda} cancelado",
                    forma_pagamento=mov_venda.forma_pagamento,
                    pedido_id=pedido.id,
                )
                db.add(estorno)
                # Reverter totais
                caixa_aberto.total_vendas = (caixa_aberto.total_vendas or 0) - mov_venda.valor
                campo = mov_venda.forma_pagamento or 'dinheiro'
                if campo == 'dinheiro':
                    caixa_aberto.total_dinheiro = (caixa_aberto.total_dinheiro or 0) - mov_venda.valor
                elif campo == 'cartao':
                    caixa_aberto.total_cartao = (caixa_aberto.total_cartao or 0) - mov_venda.valor
                elif campo == 'pix':
                    caixa_aberto.total_pix = (caixa_aberto.total_pix or 0) - mov_venda.valor
                elif campo == 'vale':
                    caixa_aberto.total_vale = (caixa_aberto.total_vale or 0) - mov_venda.valor

    db.commit()

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "pedido_cancelado",
            "dados": {
                "pedido_id": pedido.id,
                "comanda": pedido.comanda,
                "entrega_id": entrega_cancelada,
                "motoboy_id": motoboy_id_cancelado,
            }
        }, rest.id)

    return {"id": pedido.id, "status": "cancelado"}


# ============================================================
# IMPRESSÃO DE COMANDAS
# ============================================================

@router.get("/pedidos/{pedido_id}/print-data")
def get_print_data(
    pedido_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Retorna dados completos do pedido para impressão, enriquecidos com setor_impressao."""
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()

    # Enriquecer itens do carrinho com setor_impressao
    itens_impressao = []
    carrinho = pedido.carrinho_json or []
    for item in carrinho:
        setor = "geral"
        produto_id = item.get("produto_id") or item.get("id")
        if produto_id:
            prod = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
            if prod and prod.categoria_id:
                cat = db.query(models.CategoriaMenu).filter(models.CategoriaMenu.id == prod.categoria_id).first()
                if cat and cat.setor_impressao:
                    setor = cat.setor_impressao
        itens_impressao.append({
            **item,
            "setor_impressao": setor,
        })

    # Calcular subtotal e taxa para pedidos antigos (sem os campos)
    subtotal = getattr(pedido, 'valor_subtotal', 0) or 0
    taxa_entrega = getattr(pedido, 'valor_taxa_entrega', 0) or 0
    if subtotal == 0 and pedido.valor_total:
        # Pedidos antigos: subtotal = total + desconto (taxa embutida)
        subtotal = (pedido.valor_total or 0) + (pedido.valor_desconto or 0)

    return {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "data_criacao": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
        "tipo_entrega": pedido.tipo_entrega,
        "numero_mesa": pedido.numero_mesa,
        "cliente_nome": pedido.cliente_nome,
        "cliente_telefone": pedido.cliente_telefone,
        "endereco_entrega": pedido.endereco_entrega,
        "observacoes": pedido.observacoes,
        "valor_subtotal": subtotal,
        "valor_taxa_entrega": taxa_entrega,
        "valor_total": pedido.valor_total,
        "valor_desconto": pedido.valor_desconto or 0,
        "forma_pagamento": pedido.forma_pagamento,
        "troco_para": pedido.troco_para,
        "itens_texto": pedido.itens,
        "itens": itens_impressao,
        "restaurante": {
            "nome": rest.nome_fantasia or rest.nome,
            "telefone": rest.telefone,
            "endereco": rest.endereco_completo,
        },
        "largura_impressao": config.largura_impressao if config else 80,
        "marketplace_source": pedido.marketplace_source,
        "marketplace_display_id": pedido.marketplace_display_id,
        "pagamento_online": pedido.marketplace_source is not None and pedido.forma_pagamento not in ("Dinheiro", "dinheiro"),
    }


# ============================================================
# ENTREGAS ATIVAS (tempo real + detecção de atraso)
# ============================================================

@router.get("/entregas/ativas")
def entregas_ativas(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """
    Retorna entregas em andamento com cálculos de tempo e atraso.
    Usado pelo Dashboard e Pedidos para visão em tempo real.
    """
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    tolerancia = (config.tolerancia_atraso_min if config else 10) or 10

    entregas = db.query(models.Entrega).join(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Entrega.status.in_(['pendente', 'em_rota'])
    ).options(
        joinedload(models.Entrega.pedido),
        joinedload(models.Entrega.motoboy)
    ).all()

    agora = datetime.utcnow()
    resultado = []
    total_atrasadas = 0

    for e in entregas:
        pedido = e.pedido
        motoboy = e.motoboy

        # Tempo estimado baseado na distância (25 km/h)
        tempo_estimado_min = None
        if e.distancia_km and e.distancia_km > 0:
            tempo_estimado_min = round((e.distancia_km / 25) * 60)
        elif e.tempo_entrega:
            tempo_estimado_min = e.tempo_entrega

        # Tempo decorrido desde início da entrega (ou atribuição)
        referencia = e.delivery_started_at or e.atribuido_em or pedido.data_criacao
        tempo_decorrido_min = round((agora - referencia).total_seconds() / 60) if referencia else 0

        # Detectar atraso
        atrasada = False
        if tempo_estimado_min is not None and tempo_decorrido_min > (tempo_estimado_min + tolerancia):
            atrasada = True
            total_atrasadas += 1

        resultado.append({
            "entrega_id": e.id,
            "pedido_id": pedido.id,
            "comanda": pedido.comanda,
            "cliente_nome": pedido.cliente_nome,
            "endereco": pedido.endereco_entrega,
            "valor_total": pedido.valor_total,
            "status": e.status,
            "distancia_km": e.distancia_km,
            "motoboy_nome": motoboy.nome if motoboy else None,
            "motoboy_lat": motoboy.latitude_atual if motoboy else None,
            "motoboy_lon": motoboy.longitude_atual if motoboy else None,
            "pedido_criado_em": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
            "atribuido_em": e.atribuido_em.isoformat() if e.atribuido_em else None,
            "saiu_em": e.delivery_started_at.isoformat() if e.delivery_started_at else None,
            "tempo_estimado_min": tempo_estimado_min,
            "tempo_decorrido_min": tempo_decorrido_min,
            "atrasada": atrasada,
        })

    return {
        "entregas": resultado,
        "total_ativas": len(resultado),
        "total_atrasadas": total_atrasadas,
        "tolerancia_min": tolerancia,
    }


# ============================================================
# DIAGNÓSTICO DE TEMPO (ajuste automático de tempos)
# ============================================================

@router.get("/entregas/diagnostico-tempo")
def diagnostico_tempo(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """
    Analisa carga atual e sugere ajuste de tempo de entrega/retirada.
    Retorna sugestão quando detecta que tempos prometidos não são viáveis.
    """
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()

    tempo_entrega_atual = site_config.tempo_entrega_estimado if site_config else 50
    tempo_retirada_atual = site_config.tempo_retirada_estimado if site_config else 20
    tempo_preparo = config.tempo_medio_preparo if config else 30

    # Se restaurante está fechado, não sugerir ajustes de tempo
    status_atual = config.status_atual if config else 'fechado'
    if status_atual == 'fechado':
        return {
            "pedidos_ativos": 0,
            "entregas_ativas": 0,
            "motoboys_livres": 0,
            "pedidos_por_motoboy": 0,
            "tempo_medio_real_min": None,
            "tempo_entrega_atual": tempo_entrega_atual,
            "tempo_retirada_atual": tempo_retirada_atual,
            "tempo_sugerido_entrega": tempo_entrega_atual,
            "tempo_sugerido_retirada": tempo_retirada_atual,
            "precisa_aumentar": False,
            "pode_diminuir": False,
            "motivo": "Restaurante fechado",
        }

    agora = datetime.utcnow()

    # Pedidos ativos (pendente + em_preparo + pronto)
    pedidos_ativos = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.status.in_(['pendente', 'em_preparo', 'pronto'])
    ).count()

    # Entregas em andamento
    entregas_ativas = db.query(models.Entrega).join(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Entrega.status.in_(['pendente', 'em_rota'])
    ).count()

    # Motoboys disponíveis (ativos, disponíveis, não em rota)
    motoboys_livres = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.status == 'ativo',
        models.Motoboy.disponivel == True,
        models.Motoboy.em_rota == False
    ).count()

    # Calcular tempo médio real das últimas 10 entregas do dia
    hoje = datetime.combine(date.today(), datetime.min.time())
    ultimas_entregas = db.query(models.Entrega).join(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Entrega.status == 'entregue',
        models.Entrega.entregue_em >= hoje,
        models.Entrega.delivery_started_at.isnot(None)
    ).order_by(models.Entrega.entregue_em.desc()).limit(10).all()

    tempo_medio_real = None
    if ultimas_entregas:
        tempos = []
        for e in ultimas_entregas:
            if e.delivery_started_at and e.entregue_em:
                delta = (e.entregue_em - e.delivery_started_at).total_seconds() / 60
                tempos.append(delta)
        if tempos:
            tempo_medio_real = round(sum(tempos) / len(tempos))

    # Lógica de sugestão
    # Se há mais pedidos que motoboys podem atender, tempo precisa aumentar
    pedidos_por_motoboy = pedidos_ativos / max(motoboys_livres, 1)
    fila_espera_min = max(0, (pedidos_ativos - max(motoboys_livres, 1))) * tempo_preparo

    # Tempo sugerido = tempo_preparo + fila de espera + tempo médio real de entrega
    tempo_entrega_medio = tempo_medio_real or 20
    tempo_sugerido_entrega = tempo_preparo + fila_espera_min + tempo_entrega_medio
    tempo_sugerido_retirada = tempo_preparo + fila_espera_min

    # Arredondar para múltiplos de 5
    tempo_sugerido_entrega = max(30, ((tempo_sugerido_entrega + 4) // 5) * 5)
    tempo_sugerido_retirada = max(15, ((tempo_sugerido_retirada + 4) // 5) * 5)

    # Detectar se precisa ajustar
    precisa_aumentar = (
        tempo_sugerido_entrega > tempo_entrega_atual + 10 or
        tempo_sugerido_retirada > tempo_retirada_atual + 10
    )
    pode_diminuir = (
        pedidos_ativos <= 2 and motoboys_livres >= 1 and
        (tempo_entrega_atual > 50 or tempo_retirada_atual > 25)
    )

    return {
        "pedidos_ativos": pedidos_ativos,
        "entregas_ativas": entregas_ativas,
        "motoboys_livres": motoboys_livres,
        "pedidos_por_motoboy": round(pedidos_por_motoboy, 1),
        "tempo_medio_real_min": tempo_medio_real,
        "tempo_entrega_atual": tempo_entrega_atual,
        "tempo_retirada_atual": tempo_retirada_atual,
        "tempo_sugerido_entrega": int(tempo_sugerido_entrega),
        "tempo_sugerido_retirada": int(tempo_sugerido_retirada),
        "precisa_aumentar": precisa_aumentar,
        "pode_diminuir": pode_diminuir,
        "motivo": (
            f"Fila com {pedidos_ativos} pedidos e {motoboys_livres} motoboy(s) livre(s)"
            if precisa_aumentar else
            "Movimento normalizado, tempos podem voltar ao padrão"
            if pode_diminuir else
            "Tempos adequados para a demanda atual"
        ),
    }


class AjustarTempoRequest(BaseModel):
    tempo_entrega_estimado: Optional[int] = None
    tempo_retirada_estimado: Optional[int] = None


@router.post("/entregas/ajustar-tempo")
async def ajustar_tempo_automatico(
    dados: AjustarTempoRequest,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """
    Aplica ajuste de tempo de entrega/retirada sugerido pelo diagnóstico.
    """
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()
    if not site_config:
        site_config = models.SiteConfig(restaurante_id=rest.id)
        db.add(site_config)

    tempo_entrega = dados.tempo_entrega_estimado
    tempo_retirada = dados.tempo_retirada_estimado

    # Validar limites razoáveis (1 a 300 minutos)
    for val, nome in [(tempo_entrega, 'entrega'), (tempo_retirada, 'retirada')]:
        if val is not None and (val < 1 or val > 300):
            raise HTTPException(400, f"Tempo de {nome} deve ser entre 1 e 300 minutos")

    if tempo_entrega is not None:
        valor_antes_ent = site_config.tempo_entrega_estimado
        site_config.tempo_entrega_estimado = int(tempo_entrega)
        if valor_antes_ent != int(tempo_entrega):
            db.add(models.SugestaoTempo(
                restaurante_id=rest.id, tipo='entrega',
                valor_antes=valor_antes_ent, valor_sugerido=int(tempo_entrega),
                aceita=True, motivo='Aceito via diagnóstico automático',
                respondido_em=datetime.utcnow(),
            ))
    if tempo_retirada is not None:
        valor_antes_ret = site_config.tempo_retirada_estimado
        site_config.tempo_retirada_estimado = int(tempo_retirada)
        if valor_antes_ret != int(tempo_retirada):
            db.add(models.SugestaoTempo(
                restaurante_id=rest.id, tipo='retirada',
                valor_antes=valor_antes_ret, valor_sugerido=int(tempo_retirada),
                aceita=True, motivo='Aceito via diagnóstico automático',
                respondido_em=datetime.utcnow(),
            ))

    db.commit()

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "tempo_ajustado",
            "dados": {
                "tempo_entrega_estimado": site_config.tempo_entrega_estimado,
                "tempo_retirada_estimado": site_config.tempo_retirada_estimado,
            }
        }, rest.id)

    return {
        "mensagem": "Tempos atualizados",
        "tempo_entrega_estimado": site_config.tempo_entrega_estimado,
        "tempo_retirada_estimado": site_config.tempo_retirada_estimado,
    }


# ============================================================
# 1.4 CATEGORIAS
# ============================================================

class CategoriaRequest(BaseModel):
    nome: str
    descricao: Optional[str] = None
    icone: Optional[str] = None
    imagem_url: Optional[str] = None
    ordem_exibicao: Optional[int] = 0
    setor_impressao: Optional[str] = 'geral'


@router.get("/categorias")
def listar_categorias(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    cats = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == rest.id,
        models.CategoriaMenu.ativo == True
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()
    return [{
        "id": c.id, "nome": c.nome, "descricao": c.descricao,
        "icone": c.icone, "imagem_url": c.imagem_url,
        "ordem_exibicao": c.ordem_exibicao,
        "setor_impressao": c.setor_impressao or "geral",
    } for c in cats]


@router.post("/categorias")
def criar_categoria(
    dados: CategoriaRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    cat = models.CategoriaMenu(
        restaurante_id=rest.id,
        nome=dados.nome, descricao=dados.descricao,
        icone=dados.icone, imagem_url=dados.imagem_url,
        ordem_exibicao=dados.ordem_exibicao,
        setor_impressao=dados.setor_impressao or 'geral',
    )
    db.add(cat)
    _commit_and_invalidate(db, rest.id)
    db.refresh(cat)
    return {"id": cat.id, "nome": cat.nome}


@router.put("/categorias/{cat_id}")
def editar_categoria(
    cat_id: int, dados: CategoriaRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    cat = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.id == cat_id, models.CategoriaMenu.restaurante_id == rest.id
    ).first()
    if not cat:
        raise HTTPException(404, "Categoria nao encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(cat, campo, valor)
    _commit_and_invalidate(db, rest.id)
    return {"id": cat.id, "nome": cat.nome}


@router.delete("/categorias/{cat_id}")
def desativar_categoria(
    cat_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    cat = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.id == cat_id, models.CategoriaMenu.restaurante_id == rest.id
    ).first()
    if not cat:
        raise HTTPException(404, "Categoria nao encontrada")
    cat.ativo = False
    _commit_and_invalidate(db, rest.id)
    return {"mensagem": "Categoria desativada"}


class ReordenarRequest(BaseModel):
    ids_ordenados: List[int]


@router.put("/categorias/reordenar")
def reordenar_categorias(
    dados: ReordenarRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    for idx, cat_id in enumerate(dados.ids_ordenados):
        cat = db.query(models.CategoriaMenu).filter(
            models.CategoriaMenu.id == cat_id, models.CategoriaMenu.restaurante_id == rest.id
        ).first()
        if cat:
            cat.ordem_exibicao = idx
    db.commit()
    return {"mensagem": "Categorias reordenadas"}


# ============================================================
# 1.5 PRODUTOS
# ============================================================

class ProdutoRequest(BaseModel):
    categoria_id: Optional[int] = None
    nome: str
    descricao: Optional[str] = None
    preco: float
    imagem_url: Optional[str] = None
    destaque: Optional[bool] = False
    promocao: Optional[bool] = False
    preco_promocional: Optional[float] = None
    ordem_exibicao: Optional[int] = 0
    estoque_ilimitado: Optional[bool] = True
    estoque_quantidade: Optional[int] = 0
    disponivel: Optional[bool] = True
    ingredientes_json: Optional[list] = None
    eh_pizza: Optional[bool] = False


@router.get("/produtos")
def listar_produtos(
    categoria_id: Optional[int] = None,
    busca: Optional[str] = None,
    disponivel: Optional[bool] = None,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    q = db.query(models.Produto).filter(models.Produto.restaurante_id == rest.id)
    if categoria_id:
        q = q.filter(models.Produto.categoria_id == categoria_id)
    if busca:
        q = q.filter(models.Produto.nome.ilike(f"%{busca}%"))
    if disponivel is not None:
        q = q.filter(models.Produto.disponivel == disponivel)
    prods = q.order_by(models.Produto.ordem_exibicao).all()
    return [{
        "id": p.id, "categoria_id": p.categoria_id, "nome": p.nome,
        "descricao": p.descricao, "preco": p.preco, "imagem_url": p.imagem_url,
        "destaque": p.destaque, "promocao": p.promocao,
        "preco_promocional": p.preco_promocional,
        "disponivel": p.disponivel, "ordem_exibicao": p.ordem_exibicao,
        "eh_pizza": p.eh_pizza or False,
    } for p in prods]


@router.get("/produtos/{prod_id}")
def detalhe_produto(
    prod_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).options(
        joinedload(models.Produto.variacoes)
    ).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto não encontrado")
    return {
        "id": prod.id, "categoria_id": prod.categoria_id, "nome": prod.nome,
        "descricao": prod.descricao, "preco": prod.preco, "imagem_url": prod.imagem_url,
        "destaque": prod.destaque, "promocao": prod.promocao,
        "preco_promocional": prod.preco_promocional,
        "disponivel": prod.disponivel, "ordem_exibicao": prod.ordem_exibicao,
        "estoque_ilimitado": prod.estoque_ilimitado, "estoque_quantidade": prod.estoque_quantidade,
        "ingredientes_json": prod.ingredientes_json or [],
        "eh_pizza": prod.eh_pizza or False,
        "variacoes": [{
            "id": v.id, "tipo_variacao": v.tipo_variacao, "nome": v.nome,
            "descricao": v.descricao, "preco_adicional": v.preco_adicional,
            "ordem": v.ordem, "ativo": v.ativo, "max_sabores": v.max_sabores,
        } for v in prod.variacoes if v.ativo],
    }


@router.post("/produtos")
def criar_produto(
    dados: ProdutoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = models.Produto(restaurante_id=rest.id, **dados.model_dump())
    db.add(prod)
    _commit_and_invalidate(db, rest.id)
    db.refresh(prod)
    return {"id": prod.id, "nome": prod.nome}


@router.put("/produtos/{prod_id}")
def editar_produto(
    prod_id: int, dados: ProdutoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto nao encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(prod, campo, valor)
    _commit_and_invalidate(db, rest.id)
    return {"id": prod.id, "nome": prod.nome}


@router.delete("/produtos/{prod_id}")
def desativar_produto(
    prod_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto nao encontrado")
    prod.disponivel = False
    _commit_and_invalidate(db, rest.id)
    return {"mensagem": "Produto desativado"}


class DisponibilidadeRequest(BaseModel):
    disponivel: bool


@router.put("/produtos/{prod_id}/disponibilidade")
def toggle_disponibilidade(
    prod_id: int, dados: DisponibilidadeRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto nao encontrado")
    prod.disponivel = dados.disponivel
    _commit_and_invalidate(db, rest.id)
    return {"id": prod.id, "disponivel": prod.disponivel}


# ============================================================
# 1.6 VARIAÇÕES
# ============================================================

class VariacaoRequest(BaseModel):
    tipo_variacao: str
    nome: str
    descricao: Optional[str] = None
    preco_adicional: Optional[float] = 0.0
    ordem: Optional[int] = 0
    max_sabores: Optional[int] = 1


@router.get("/produtos/{prod_id}/variacoes")
def listar_variacoes(
    prod_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto não encontrado")
    vars = db.query(models.VariacaoProdutoProduto).filter(
        models.VariacaoProdutoProduto.produto_id == prod_id,
        models.VariacaoProdutoProduto.ativo == True
    ).order_by(models.VariacaoProdutoProduto.ordem).all()
    return [{
        "id": v.id, "tipo_variacao": v.tipo_variacao, "nome": v.nome,
        "descricao": v.descricao, "preco_adicional": v.preco_adicional,
        "ordem": v.ordem, "max_sabores": v.max_sabores,
    } for v in vars]


@router.post("/produtos/{prod_id}/variacoes")
def criar_variacao(
    prod_id: int, dados: VariacaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    prod = db.query(models.Produto).filter(
        models.Produto.id == prod_id, models.Produto.restaurante_id == rest.id
    ).first()
    if not prod:
        raise HTTPException(404, "Produto não encontrado")
    var = models.VariacaoProdutoProduto(produto_id=prod_id, **dados.model_dump())
    db.add(var)
    db.commit()
    db.refresh(var)
    return {"id": var.id, "nome": var.nome}


class AplicarMaxSaboresRequest(BaseModel):
    nome_tamanho: str
    max_sabores: int


@router.put("/variacoes/aplicar-max-sabores")
def aplicar_max_sabores_em_massa(
    dados: AplicarMaxSaboresRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Aplica max_sabores a TODAS as variações de tamanho com o mesmo nome no restaurante"""
    # Subquery necessária porque PostgreSQL não suporta UPDATE com JOIN direto
    ids_variacoes = db.query(models.VariacaoProdutoProduto.id).join(models.Produto).filter(
        models.Produto.restaurante_id == rest.id,
        models.VariacaoProdutoProduto.tipo_variacao == "tamanho",
        models.VariacaoProdutoProduto.nome == dados.nome_tamanho,
    ).subquery()
    total = db.query(models.VariacaoProdutoProduto).filter(
        models.VariacaoProdutoProduto.id.in_(ids_variacoes)
    ).update({"max_sabores": dados.max_sabores}, synchronize_session=False)
    db.commit()
    return {"mensagem": f"Atualizado {total} variações '{dados.nome_tamanho}' para {dados.max_sabores} sabores", "total": total}


@router.put("/variacoes/{var_id}")
def editar_variacao(
    var_id: int, dados: VariacaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    var = db.query(models.VariacaoProdutoProduto).join(models.Produto).filter(
        models.VariacaoProdutoProduto.id == var_id,
        models.Produto.restaurante_id == rest.id
    ).first()
    if not var:
        raise HTTPException(404, "Variação não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(var, campo, valor)
    db.commit()
    return {"id": var.id, "nome": var.nome}


@router.delete("/variacoes/{var_id}")
def desativar_variacao(
    var_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    var = db.query(models.VariacaoProdutoProduto).join(models.Produto).filter(
        models.VariacaoProdutoProduto.id == var_id,
        models.Produto.restaurante_id == rest.id
    ).first()
    if not var:
        raise HTTPException(404, "Variação não encontrada")
    var.ativo = False
    db.commit()
    return {"mensagem": "Variação desativada"}


# ============================================================
# 1.7 COMBOS
# ============================================================

class ComboItemRequest(BaseModel):
    produto_id: int
    quantidade: int = 1


class ComboRequest(BaseModel):
    nome: str
    descricao: Optional[str] = None
    preco_combo: float
    preco_original: float
    imagem_url: Optional[str] = None
    ordem_exibicao: Optional[int] = 0
    itens: List[ComboItemRequest] = []
    tipo_combo: Optional[str] = "padrao"
    dia_semana: Optional[int] = None
    quantidade_pessoas: Optional[int] = None


@router.get("/combos")
def listar_combos(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    combos = db.query(models.Combo).options(
        joinedload(models.Combo.itens)
    ).filter(
        models.Combo.restaurante_id == rest.id
    ).order_by(models.Combo.ordem_exibicao).all()
    return [{
        "id": c.id, "nome": c.nome, "descricao": c.descricao,
        "preco_combo": c.preco_combo, "preco_original": c.preco_original,
        "imagem_url": c.imagem_url, "ordem_exibicao": c.ordem_exibicao,
        "ativo": c.ativo, "data_inicio": c.data_inicio, "data_fim": c.data_fim,
        "tipo_combo": c.tipo_combo or "padrao",
        "dia_semana": c.dia_semana, "quantidade_pessoas": c.quantidade_pessoas,
        "itens": [{"produto_id": i.produto_id, "quantidade": i.quantidade} for i in c.itens],
    } for c in combos]


@router.post("/combos")
def criar_combo(
    dados: ComboRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    combo = models.Combo(
        restaurante_id=rest.id, nome=dados.nome, descricao=dados.descricao,
        preco_combo=dados.preco_combo, preco_original=dados.preco_original,
        imagem_url=dados.imagem_url, ordem_exibicao=dados.ordem_exibicao,
        tipo_combo=dados.tipo_combo or "padrao",
        dia_semana=dados.dia_semana, quantidade_pessoas=dados.quantidade_pessoas
    )
    db.add(combo)
    db.flush()
    for item in dados.itens:
        db.add(models.ComboItem(combo_id=combo.id, produto_id=item.produto_id, quantidade=item.quantidade))
    db.commit()
    db.refresh(combo)
    return {"id": combo.id, "nome": combo.nome}


@router.put("/combos/{combo_id}")
def editar_combo(
    combo_id: int, dados: ComboRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    combo = db.query(models.Combo).filter(
        models.Combo.id == combo_id, models.Combo.restaurante_id == rest.id
    ).first()
    if not combo:
        raise HTTPException(404, "Combo não encontrado")
    combo.nome = dados.nome
    combo.descricao = dados.descricao
    combo.preco_combo = dados.preco_combo
    combo.preco_original = dados.preco_original
    combo.imagem_url = dados.imagem_url
    combo.ordem_exibicao = dados.ordem_exibicao
    combo.tipo_combo = dados.tipo_combo or "padrao"
    combo.dia_semana = dados.dia_semana
    combo.quantidade_pessoas = dados.quantidade_pessoas
    # Recriar itens
    db.query(models.ComboItem).filter(models.ComboItem.combo_id == combo.id).delete()
    for item in dados.itens:
        db.add(models.ComboItem(combo_id=combo.id, produto_id=item.produto_id, quantidade=item.quantidade))
    db.commit()
    return {"id": combo.id, "nome": combo.nome}


@router.delete("/combos/{combo_id}")
def desativar_combo(
    combo_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    combo = db.query(models.Combo).filter(
        models.Combo.id == combo_id, models.Combo.restaurante_id == rest.id
    ).first()
    if not combo:
        raise HTTPException(404, "Combo não encontrado")
    combo.ativo = False
    db.commit()
    return {"mensagem": "Combo desativado"}


# ============================================================
# 1.8 MOTOBOYS
# ============================================================

class MotoboyRequest(BaseModel):
    nome: str
    usuario: str
    telefone: str
    senha: Optional[str] = None
    capacidade_entregas: Optional[int] = 5
    cpf: Optional[str] = None


@router.get("/motoboys")
def listar_motoboys(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    motoboys = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.status.in_(['ativo', 'pendente'])
    ).order_by(models.Motoboy.ordem_hierarquia).all()
    return [{
        "id": m.id, "nome": m.nome, "usuario": m.usuario, "telefone": m.telefone,
        "status": m.status, "cpf": m.cpf,
        "disponivel": m.disponivel, "em_rota": m.em_rota,
        "entregas_pendentes": m.entregas_pendentes,
        "total_entregas": m.total_entregas, "total_ganhos": m.total_ganhos,
        "ordem_hierarquia": m.ordem_hierarquia,
        "latitude_atual": m.latitude_atual, "longitude_atual": m.longitude_atual,
        "ultima_atualizacao_gps": m.ultima_atualizacao_gps.isoformat() if m.ultima_atualizacao_gps else None,
        "capacidade_entregas": m.capacidade_entregas,
    } for m in motoboys]


@router.post("/motoboys")
def cadastrar_motoboy(
    dados: MotoboyRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    # Validar CPF se fornecido
    cpf_limpo = None
    if dados.cpf:
        from utils.cpf import validar_cpf
        cpf_limpo = ''.join(filter(str.isdigit, dados.cpf.strip()))
        if not validar_cpf(cpf_limpo):
            raise HTTPException(400, "CPF inválido")

    existente = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.usuario == dados.usuario
    ).first()
    if existente:
        raise HTTPException(400, "Usuário já existe")

    max_ordem = db.query(func.max(models.Motoboy.ordem_hierarquia)).filter(
        models.Motoboy.restaurante_id == rest.id
    ).scalar() or 0

    motoboy = models.Motoboy(
        restaurante_id=rest.id, nome=dados.nome, usuario=dados.usuario,
        telefone=dados.telefone, capacidade_entregas=dados.capacidade_entregas,
        cpf=cpf_limpo, status='ativo', ordem_hierarquia=max_ordem + 1
    )
    if dados.senha:
        motoboy.set_senha(dados.senha)
    db.add(motoboy)
    db.commit()
    db.refresh(motoboy)
    return {"id": motoboy.id, "nome": motoboy.nome}


@router.put("/motoboys/{motoboy_id}")
def editar_motoboy(
    motoboy_id: int, dados: MotoboyRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    motoboy = db.query(models.Motoboy).filter(
        models.Motoboy.id == motoboy_id, models.Motoboy.restaurante_id == rest.id
    ).first()
    if not motoboy:
        raise HTTPException(404, "Motoboy não encontrado")
    # Validar CPF se fornecido
    if dados.cpf:
        from utils.cpf import validar_cpf
        cpf_limpo = ''.join(filter(str.isdigit, dados.cpf.strip()))
        if not validar_cpf(cpf_limpo):
            raise HTTPException(400, "CPF inválido")
        motoboy.cpf = cpf_limpo
    else:
        motoboy.cpf = None
    motoboy.nome = dados.nome
    motoboy.usuario = dados.usuario
    motoboy.telefone = dados.telefone
    motoboy.capacidade_entregas = dados.capacidade_entregas
    if dados.senha:
        motoboy.set_senha(dados.senha)
    db.commit()
    return {"id": motoboy.id, "nome": motoboy.nome}


@router.delete("/motoboys/{motoboy_id}")
def desativar_motoboy(
    motoboy_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    motoboy = db.query(models.Motoboy).filter(
        models.Motoboy.id == motoboy_id, models.Motoboy.restaurante_id == rest.id
    ).first()
    if not motoboy:
        raise HTTPException(404, "Motoboy não encontrado")
    motoboy.status = 'inativo'
    motoboy.disponivel = False
    db.commit()
    return {"mensagem": "Motoboy desativado"}


class HierarquiaRequest(BaseModel):
    ordem: int


@router.put("/motoboys/{motoboy_id}/hierarquia")
def alterar_hierarquia(
    motoboy_id: int, dados: HierarquiaRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    motoboy = db.query(models.Motoboy).filter(
        models.Motoboy.id == motoboy_id, models.Motoboy.restaurante_id == rest.id
    ).first()
    if not motoboy:
        raise HTTPException(404, "Motoboy não encontrado")
    motoboy.ordem_hierarquia = dados.ordem
    db.commit()
    return {"id": motoboy.id, "ordem_hierarquia": motoboy.ordem_hierarquia}


@router.get("/motoboys/ranking")
def ranking_motoboys(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    motoboys = db.query(models.Motoboy).filter(
        models.Motoboy.restaurante_id == rest.id,
        models.Motoboy.status == 'ativo'
    ).order_by(desc(models.Motoboy.total_entregas)).all()
    return [{
        "id": m.id, "nome": m.nome,
        "total_entregas": m.total_entregas,
        "total_ganhos": m.total_ganhos,
        "total_km": m.total_km,
    } for m in motoboys]


@router.get("/motoboys/solicitacoes")
def listar_solicitacoes(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    solic = db.query(models.MotoboySolicitacao).filter(
        models.MotoboySolicitacao.restaurante_id == rest.id,
        models.MotoboySolicitacao.status == 'pendente'
    ).order_by(models.MotoboySolicitacao.data_solicitacao).all()
    return [{
        "id": s.id, "nome": s.nome, "usuario": s.usuario,
        "telefone": s.telefone, "data_solicitacao": s.data_solicitacao.isoformat() if s.data_solicitacao else None,
    } for s in solic]


class SolicitacaoAcaoRequest(BaseModel):
    acao: str  # 'aprovar' ou 'rejeitar'


@router.put("/motoboys/solicitacoes/{solic_id}")
def acao_solicitacao(
    solic_id: int, dados: SolicitacaoAcaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    solic = db.query(models.MotoboySolicitacao).filter(
        models.MotoboySolicitacao.id == solic_id,
        models.MotoboySolicitacao.restaurante_id == rest.id
    ).first()
    if not solic:
        raise HTTPException(404, "Solicitação não encontrada")

    if dados.acao == 'aprovar':
        max_ordem = db.query(func.max(models.Motoboy.ordem_hierarquia)).filter(
            models.Motoboy.restaurante_id == rest.id
        ).scalar() or 0
        motoboy = models.Motoboy(
            restaurante_id=rest.id, nome=solic.nome, usuario=solic.usuario,
            telefone=solic.telefone, status='ativo', ordem_hierarquia=max_ordem + 1
        )
        motoboy.set_senha("123456")
        db.add(motoboy)
        solic.status = 'aprovado'
    else:
        solic.status = 'rejeitado'

    db.commit()
    return {"mensagem": f"Solicitação {dados.acao}da"}


# ============================================================
# 1.9 CAIXA
# ============================================================

@router.get("/caixa/atual")
def caixa_atual(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    caixa = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id,
        models.Caixa.status == 'aberto'
    ).first()
    if not caixa:
        return None

    movs = db.query(models.MovimentacaoCaixa).filter(
        models.MovimentacaoCaixa.caixa_id == caixa.id
    ).order_by(models.MovimentacaoCaixa.data_hora).all()

    return {
        "id": caixa.id, "data_abertura": caixa.data_abertura.isoformat(),
        "operador_abertura": caixa.operador_abertura,
        "valor_abertura": caixa.valor_abertura,
        "total_vendas": caixa.total_vendas,
        "valor_retiradas": caixa.valor_retiradas,
        "total_dinheiro": caixa.total_dinheiro or 0,
        "total_cartao": caixa.total_cartao or 0,
        "total_pix": caixa.total_pix or 0,
        "total_vale": caixa.total_vale or 0,
        "movimentacoes": [{
            "id": m.id, "tipo": m.tipo, "valor": m.valor,
            "descricao": m.descricao,
            "forma_pagamento": m.forma_pagamento,
            "pedido_id": m.pedido_id,
            "data_hora": m.data_hora.isoformat() if m.data_hora else None,
        } for m in movs],
    }


class AbrirCaixaRequest(BaseModel):
    valor_abertura: float = 0.0


@router.post("/caixa/abrir")
def abrir_caixa(
    dados: AbrirCaixaRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    existente = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id, models.Caixa.status == 'aberto'
    ).first()
    if existente:
        raise HTTPException(400, "Já existe um caixa aberto")

    caixa = models.Caixa(
        restaurante_id=rest.id,
        data_abertura=datetime.utcnow(),
        operador_abertura=rest.nome,
        valor_abertura=dados.valor_abertura
    )
    db.add(caixa)
    db.commit()
    db.refresh(caixa)
    return {"id": caixa.id, "status": "aberto"}


class MovimentacaoRequest(BaseModel):
    tipo: str  # entrada, saida, retirada
    valor: float
    descricao: Optional[str] = None


@router.post("/caixa/movimentacao")
def registrar_movimentacao(
    dados: MovimentacaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    caixa = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id, models.Caixa.status == 'aberto'
    ).first()
    if not caixa:
        raise HTTPException(400, "Nenhum caixa aberto")

    mov = models.MovimentacaoCaixa(
        caixa_id=caixa.id, tipo=dados.tipo,
        valor=dados.valor, descricao=dados.descricao
    )
    db.add(mov)

    if dados.tipo == 'entrada':
        caixa.total_vendas = (caixa.total_vendas or 0) + dados.valor
    elif dados.tipo in ('saida', 'retirada'):
        caixa.valor_retiradas = (caixa.valor_retiradas or 0) + dados.valor

    db.commit()
    return {"mensagem": "Movimentação registrada"}


class FecharCaixaRequest(BaseModel):
    valor_contado: float


@router.post("/caixa/fechar")
def fechar_caixa(
    dados: FecharCaixaRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    caixa = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id, models.Caixa.status == 'aberto'
    ).first()
    if not caixa:
        raise HTTPException(400, "Nenhum caixa aberto")

    valor_esperado = (caixa.valor_abertura or 0) + (caixa.total_vendas or 0) - (caixa.valor_retiradas or 0)
    diferenca = dados.valor_contado - valor_esperado

    caixa.status = 'fechado'
    caixa.data_fechamento = datetime.utcnow()
    caixa.operador_fechamento = rest.nome
    caixa.valor_contado = dados.valor_contado
    caixa.diferenca = round(diferenca, 2)
    db.commit()
    return {"id": caixa.id, "valor_esperado": round(valor_esperado, 2), "diferenca": round(diferenca, 2)}


@router.get("/caixa/historico")
def historico_caixa(
    limite: int = Query(30, ge=1, le=100),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    caixas = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id,
        models.Caixa.status == 'fechado'
    ).order_by(desc(models.Caixa.data_abertura)).limit(limite).all()
    return [{
        "id": c.id, "data_abertura": c.data_abertura.isoformat(),
        "data_fechamento": c.data_fechamento.isoformat() if c.data_fechamento else None,
        "operador_abertura": c.operador_abertura,
        "valor_abertura": c.valor_abertura, "total_vendas": c.total_vendas,
        "valor_retiradas": c.valor_retiradas,
        "total_dinheiro": c.total_dinheiro or 0,
        "total_cartao": c.total_cartao or 0,
        "total_pix": c.total_pix or 0,
        "total_vale": c.total_vale or 0,
        "valor_contado": c.valor_contado, "diferenca": c.diferenca,
    } for c in caixas]


# ============================================================
# 1.10 CONFIGURAÇÕES
# ============================================================

@router.get("/config")
def get_config(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    if not config:
        config = models.ConfigRestaurante(restaurante_id=rest.id)
        db.add(config)
        db.commit()
        db.refresh(config)

    import json as _json

    # Parse horarios_por_dia JSON
    horarios_por_dia = None
    if config.horarios_por_dia:
        try:
            horarios_por_dia = _json.loads(config.horarios_por_dia)
        except Exception:
            horarios_por_dia = None

    return {
        "id": config.id, "status_atual": config.status_atual,
        "modo_despacho": config.modo_despacho, "raio_entrega_km": config.raio_entrega_km,
        "tempo_medio_preparo": config.tempo_medio_preparo,
        "despacho_automatico": config.despacho_automatico,
        "modo_prioridade_entrega": config.modo_prioridade_entrega,
        "taxa_entrega_base": config.taxa_entrega_base, "distancia_base_km": config.distancia_base_km,
        "taxa_km_extra": config.taxa_km_extra,
        "valor_base_motoboy": config.valor_base_motoboy,
        "valor_km_extra_motoboy": config.valor_km_extra_motoboy,
        "taxa_diaria": config.taxa_diaria, "valor_lanche": config.valor_lanche,
        "max_pedidos_por_rota": config.max_pedidos_por_rota,
        "permitir_ver_saldo_motoboy": config.permitir_ver_saldo_motoboy,
        "permitir_finalizar_fora_raio": config.permitir_finalizar_fora_raio,
        "distancia_base_motoboy_km": config.distancia_base_motoboy_km,
        "aceitar_pedido_site_auto": config.aceitar_pedido_site_auto,
        "tolerancia_atraso_min": config.tolerancia_atraso_min,
        "horario_abertura": config.horario_abertura,
        "horario_fechamento": config.horario_fechamento,
        "dias_semana_abertos": config.dias_semana_abertos,
        "modo_preco_pizza": config.modo_preco_pizza,
        "horarios_por_dia": horarios_por_dia,
        "pedidos_online_ativos": config.pedidos_online_ativos if config.pedidos_online_ativos is not None else True,
        "entregas_ativas": config.entregas_ativas if config.entregas_ativas is not None else True,
        "controle_pedidos_motivo": config.controle_pedidos_motivo,
        "controle_pedidos_ate": config.controle_pedidos_ate.isoformat() if config.controle_pedidos_ate else None,
        # Impressão
        "impressao_automatica": config.impressao_automatica or False,
        "largura_impressao": config.largura_impressao or 80,
        # Localização do restaurante (de Restaurante, não ConfigRestaurante)
        "endereco_completo": rest.endereco_completo,
        "latitude": rest.latitude,
        "longitude": rest.longitude,
    }


@router.put("/config")
async def atualizar_config(
    dados: dict,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    if not config:
        config = models.ConfigRestaurante(restaurante_id=rest.id)
        db.add(config)

    status_anterior = config.status_atual

    import json as _json

    campos_validos = {
        'status_atual', 'modo_despacho', 'raio_entrega_km', 'tempo_medio_preparo',
        'despacho_automatico', 'modo_prioridade_entrega', 'taxa_entrega_base',
        'distancia_base_km', 'taxa_km_extra', 'valor_base_motoboy', 'valor_km_extra_motoboy',
        'taxa_diaria', 'valor_lanche', 'max_pedidos_por_rota',
        'permitir_ver_saldo_motoboy', 'permitir_finalizar_fora_raio',
        'distancia_base_motoboy_km', 'aceitar_pedido_site_auto',
        'tolerancia_atraso_min', 'horario_abertura', 'horario_fechamento',
        'dias_semana_abertos', 'modo_preco_pizza',
        'pedidos_online_ativos', 'entregas_ativas',
        'controle_pedidos_motivo', 'controle_pedidos_ate',
        'impressao_automatica', 'largura_impressao'
    }

    for campo, valor in dados.items():
        if campo == 'horarios_por_dia':
            # Salvar como JSON string
            if isinstance(valor, dict):
                config.horarios_por_dia = _json.dumps(valor)
            elif valor is None:
                config.horarios_por_dia = None
            else:
                config.horarios_por_dia = str(valor)
        elif campo == 'controle_pedidos_ate':
            # Parse ISO datetime string
            if valor:
                try:
                    config.controle_pedidos_ate = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    config.controle_pedidos_ate = None
            else:
                config.controle_pedidos_ate = None
        elif campo in campos_validos:
            setattr(config, campo, valor)

    db.commit()

    # Invalidar cache do site para que mudanças reflitam imediatamente
    from ..cache import cache_delete_pattern
    cache_delete_pattern(f"site:{rest.codigo_acesso}:*")

    # Broadcast WebSocket para o site cliente atualizar em tempo real
    mudou_status = dados.get('status_atual') and dados['status_atual'] != status_anterior
    mudou_horario = 'horario_abertura' in dados or 'horario_fechamento' in dados or 'horarios_por_dia' in dados
    mudou_pedidos = 'pedidos_online_ativos' in dados or 'entregas_ativas' in dados
    if mudou_status or mudou_horario or mudou_pedidos:
        ws = getattr(request.app.state, 'ws_manager', None)
        if ws:
            await ws.broadcast({
                "tipo": "config_atualizada",
                "dados": {
                    "status_atual": config.status_atual,
                    "horario_abertura": config.horario_abertura,
                    "horario_fechamento": config.horario_fechamento,
                    "pedidos_online_ativos": config.pedidos_online_ativos if config.pedidos_online_ativos is not None else True,
                    "entregas_ativas": config.entregas_ativas if config.entregas_ativas is not None else True,
                    "controle_pedidos_motivo": config.controle_pedidos_motivo,
                }
            }, rest.id)

    return {"mensagem": "Configurações atualizadas"}


@router.get("/config/site")
def get_site_config(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    sc = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()
    if not sc:
        sc = models.SiteConfig(restaurante_id=rest.id)
        db.add(sc)
        db.commit()
        db.refresh(sc)

    return {
        "id": sc.id, "tipo_restaurante": sc.tipo_restaurante,
        "tema_cor_primaria": sc.tema_cor_primaria, "tema_cor_secundaria": sc.tema_cor_secundaria,
        "logo_url": sc.logo_url, "banner_principal_url": sc.banner_principal_url,
        "favicon_url": sc.favicon_url,
        "whatsapp_numero": sc.whatsapp_numero, "whatsapp_ativo": sc.whatsapp_ativo,
        "whatsapp_mensagem_padrao": sc.whatsapp_mensagem_padrao,
        "pedido_minimo": sc.pedido_minimo,
        "tempo_entrega_estimado": sc.tempo_entrega_estimado,
        "tempo_retirada_estimado": sc.tempo_retirada_estimado,
        "site_ativo": sc.site_ativo, "aceita_agendamento": sc.aceita_agendamento,
        "aceita_dinheiro": sc.aceita_dinheiro, "aceita_cartao": sc.aceita_cartao,
        "aceita_pix": sc.aceita_pix, "aceita_vale_refeicao": sc.aceita_vale_refeicao,
        "meta_title": sc.meta_title, "meta_description": sc.meta_description,
        "ingredientes_adicionais_pizza": sc.ingredientes_adicionais_pizza,
    }


@router.put("/config/site")
async def atualizar_site_config(
    dados: dict,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    sc = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()
    if not sc:
        sc = models.SiteConfig(restaurante_id=rest.id)
        db.add(sc)

    campos_validos = {
        'tipo_restaurante', 'tema_cor_primaria', 'tema_cor_secundaria',
        'logo_url', 'banner_principal_url', 'favicon_url',
        'whatsapp_numero', 'whatsapp_ativo', 'whatsapp_mensagem_padrao',
        'pedido_minimo', 'tempo_entrega_estimado', 'tempo_retirada_estimado',
        'site_ativo', 'aceita_agendamento',
        'aceita_dinheiro', 'aceita_cartao', 'aceita_pix', 'aceita_vale_refeicao',
        'meta_title', 'meta_description', 'meta_keywords',
        'ingredientes_adicionais_pizza'
    }
    for campo, valor in dados.items():
        if campo in campos_validos:
            setattr(sc, campo, valor)

    db.commit()

    # Invalidar cache do site
    from ..cache import cache_delete_pattern
    cache_delete_pattern(f"site:{rest.codigo_acesso}:*")
    cache_delete_pattern(f"cardapio:{rest.codigo_acesso}:*")

    # Broadcast para clientes atualizarem
    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "config_atualizada",
            "dados": {"tipo": "site"}
        }, rest.id)

    return {"mensagem": "Configurações do site atualizadas"}


# ============================================================
# 1.11 BAIRROS
# ============================================================

class BairroRequest(BaseModel):
    nome: str
    taxa_entrega: float = 0.0
    tempo_estimado_min: int = 30


@router.get("/bairros")
def listar_bairros(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    bairros = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.restaurante_id == rest.id,
        models.BairroEntrega.ativo == True
    ).order_by(models.BairroEntrega.nome).all()
    return [{
        "id": b.id, "nome": b.nome, "taxa_entrega": b.taxa_entrega,
        "tempo_estimado_min": b.tempo_estimado_min,
    } for b in bairros]


@router.post("/bairros")
def criar_bairro(
    dados: BairroRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    bairro = models.BairroEntrega(
        restaurante_id=rest.id, nome=dados.nome,
        taxa_entrega=dados.taxa_entrega, tempo_estimado_min=dados.tempo_estimado_min
    )
    db.add(bairro)
    db.commit()
    db.refresh(bairro)
    return {"id": bairro.id, "nome": bairro.nome}


@router.put("/bairros/{bairro_id}")
def editar_bairro(
    bairro_id: int, dados: BairroRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    bairro = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.id == bairro_id, models.BairroEntrega.restaurante_id == rest.id
    ).first()
    if not bairro:
        raise HTTPException(404, "Bairro não encontrado")
    bairro.nome = dados.nome
    bairro.taxa_entrega = dados.taxa_entrega
    bairro.tempo_estimado_min = dados.tempo_estimado_min
    db.commit()
    return {"id": bairro.id, "nome": bairro.nome}


@router.delete("/bairros/{bairro_id}")
def desativar_bairro(
    bairro_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    bairro = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.id == bairro_id, models.BairroEntrega.restaurante_id == rest.id
    ).first()
    if not bairro:
        raise HTTPException(404, "Bairro não encontrado")
    bairro.ativo = False
    db.commit()
    return {"mensagem": "Bairro desativado"}


# ============================================================
# 1.12 PROMOÇÕES
# ============================================================

class PromocaoRequest(BaseModel):
    nome: str
    descricao: Optional[str] = None
    tipo_desconto: str  # percentual, fixo
    valor_desconto: float
    valor_pedido_minimo: Optional[float] = 0.0
    desconto_maximo: Optional[float] = None
    codigo_cupom: Optional[str] = None
    data_inicio: Optional[str] = None
    data_fim: Optional[str] = None
    uso_limitado: Optional[bool] = False
    limite_usos: Optional[int] = None


@router.get("/promocoes")
def listar_promocoes(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    promos = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == rest.id,
        models.Promocao.ativo == True
    ).all()
    return [{
        "id": p.id, "nome": p.nome, "descricao": p.descricao,
        "tipo_desconto": p.tipo_desconto, "valor_desconto": p.valor_desconto,
        "valor_pedido_minimo": p.valor_pedido_minimo, "desconto_maximo": p.desconto_maximo,
        "codigo_cupom": p.codigo_cupom,
        "data_inicio": p.data_inicio.isoformat() if p.data_inicio else None,
        "data_fim": p.data_fim.isoformat() if p.data_fim else None,
        "uso_limitado": p.uso_limitado, "limite_usos": p.limite_usos,
        "usos_realizados": p.usos_realizados,
    } for p in promos]


@router.post("/promocoes")
def criar_promocao(
    dados: PromocaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    promo = models.Promocao(
        restaurante_id=rest.id, nome=dados.nome, descricao=dados.descricao,
        tipo_desconto=dados.tipo_desconto, valor_desconto=dados.valor_desconto,
        valor_pedido_minimo=dados.valor_pedido_minimo, desconto_maximo=dados.desconto_maximo,
        codigo_cupom=dados.codigo_cupom, uso_limitado=dados.uso_limitado,
        limite_usos=dados.limite_usos,
        data_inicio=datetime.fromisoformat(dados.data_inicio) if dados.data_inicio else None,
        data_fim=datetime.fromisoformat(dados.data_fim) if dados.data_fim else None,
    )
    db.add(promo)
    db.commit()
    db.refresh(promo)
    return {"id": promo.id, "nome": promo.nome}


@router.put("/promocoes/{promo_id}")
def editar_promocao(
    promo_id: int, dados: PromocaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    promo = db.query(models.Promocao).filter(
        models.Promocao.id == promo_id, models.Promocao.restaurante_id == rest.id
    ).first()
    if not promo:
        raise HTTPException(404, "Promoção não encontrada")
    promo.nome = dados.nome
    promo.descricao = dados.descricao
    promo.tipo_desconto = dados.tipo_desconto
    promo.valor_desconto = dados.valor_desconto
    promo.valor_pedido_minimo = dados.valor_pedido_minimo
    promo.desconto_maximo = dados.desconto_maximo
    promo.codigo_cupom = dados.codigo_cupom
    promo.uso_limitado = dados.uso_limitado
    promo.limite_usos = dados.limite_usos
    promo.data_inicio = datetime.fromisoformat(dados.data_inicio) if dados.data_inicio else None
    promo.data_fim = datetime.fromisoformat(dados.data_fim) if dados.data_fim else None
    db.commit()
    return {"id": promo.id, "nome": promo.nome}


@router.delete("/promocoes/{promo_id}")
def desativar_promocao(
    promo_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    promo = db.query(models.Promocao).filter(
        models.Promocao.id == promo_id, models.Promocao.restaurante_id == rest.id
    ).first()
    if not promo:
        raise HTTPException(404, "Promoção não encontrada")
    promo.ativo = False
    db.commit()
    return {"mensagem": "Promoção desativada"}


# ============================================================
# 1.13 FIDELIDADE
# ============================================================

class PremioRequest(BaseModel):
    nome: str
    descricao: Optional[str] = None
    custo_pontos: int
    tipo_premio: str  # desconto, item_gratis, brinde
    valor_premio: Optional[str] = None
    ordem_exibicao: Optional[int] = 0


@router.get("/fidelidade/premios")
def listar_premios(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    premios = db.query(models.PremioFidelidade).filter(
        models.PremioFidelidade.restaurante_id == rest.id,
        models.PremioFidelidade.ativo == True
    ).order_by(models.PremioFidelidade.ordem_exibicao).all()
    return [{
        "id": p.id, "nome": p.nome, "descricao": p.descricao,
        "custo_pontos": p.custo_pontos, "tipo_premio": p.tipo_premio,
        "valor_premio": p.valor_premio, "ordem_exibicao": p.ordem_exibicao,
    } for p in premios]


@router.post("/fidelidade/premios")
def criar_premio(
    dados: PremioRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    premio = models.PremioFidelidade(
        restaurante_id=rest.id, **dados.model_dump()
    )
    db.add(premio)
    db.commit()
    db.refresh(premio)
    return {"id": premio.id, "nome": premio.nome}


@router.put("/fidelidade/premios/{premio_id}")
def editar_premio(
    premio_id: int, dados: PremioRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    premio = db.query(models.PremioFidelidade).filter(
        models.PremioFidelidade.id == premio_id,
        models.PremioFidelidade.restaurante_id == rest.id
    ).first()
    if not premio:
        raise HTTPException(404, "Prêmio não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(premio, campo, valor)
    db.commit()
    return {"id": premio.id, "nome": premio.nome}


@router.delete("/fidelidade/premios/{premio_id}")
def desativar_premio(
    premio_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    premio = db.query(models.PremioFidelidade).filter(
        models.PremioFidelidade.id == premio_id,
        models.PremioFidelidade.restaurante_id == rest.id
    ).first()
    if not premio:
        raise HTTPException(404, "Prêmio não encontrado")
    premio.ativo = False
    db.commit()
    return {"mensagem": "Prêmio desativado"}


# ============================================================
# 1.14 RELATÓRIOS
# ============================================================

@router.get("/relatorios/vendas")
def relatorio_vendas(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    q = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.status.notin_(['cancelado', 'recusado'])
    )
    if data_inicio:
        q = q.filter(models.Pedido.data_criacao >= data_inicio)
    if data_fim:
        q = q.filter(models.Pedido.data_criacao <= data_fim)

    pedidos = q.order_by(desc(models.Pedido.data_criacao)).all()
    total = sum(p.valor_total or 0 for p in pedidos)

    return {
        "total_pedidos": len(pedidos),
        "faturamento_total": round(total, 2),
        "pedidos": [{
            "id": p.id, "comanda": p.comanda, "cliente_nome": p.cliente_nome,
            "valor_total": p.valor_total, "forma_pagamento": p.forma_pagamento,
            "status": p.status,
            "data_criacao": p.data_criacao.isoformat() if p.data_criacao else None,
        } for p in pedidos]
    }


@router.get("/relatorios/motoboys")
def relatorio_motoboys(
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    q = db.query(models.Entrega).join(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Entrega.status == 'entregue'
    )
    if data_inicio:
        q = q.filter(models.Entrega.entregue_em >= data_inicio)
    if data_fim:
        q = q.filter(models.Entrega.entregue_em <= data_fim)

    entregas = q.all()
    motoboy_ids = set(e.motoboy_id for e in entregas if e.motoboy_id)
    motoboys = {m.id: m.nome for m in db.query(models.Motoboy).filter(
        models.Motoboy.id.in_(motoboy_ids)
    ).all()} if motoboy_ids else {}

    resumo = {}
    for e in entregas:
        mid = e.motoboy_id
        if mid not in resumo:
            resumo[mid] = {"nome": motoboys.get(mid, "?"), "entregas": 0, "ganhos": 0.0, "km": 0.0}
        resumo[mid]["entregas"] += 1
        resumo[mid]["ganhos"] += e.valor_motoboy or 0
        resumo[mid]["km"] += e.distancia_km or 0

    return [{
        "motoboy_id": mid, "nome": d["nome"],
        "total_entregas": d["entregas"],
        "total_ganhos": round(d["ganhos"], 2),
        "total_km": round(d["km"], 2),
    } for mid, d in resumo.items()]


@router.get("/relatorios/produtos")
def relatorio_produtos(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    itens = db.query(
        models.ItemPedido.produto_id,
        func.sum(models.ItemPedido.quantidade).label('total_vendido'),
        func.sum(models.ItemPedido.quantidade * models.ItemPedido.preco_unitario).label('receita')
    ).join(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.status.notin_(['cancelado', 'recusado'])
    ).group_by(models.ItemPedido.produto_id).order_by(
        desc('total_vendido')
    ).limit(50).all()

    produto_ids = [i.produto_id for i in itens if i.produto_id]
    produtos = {p.id: p.nome for p in db.query(models.Produto).filter(
        models.Produto.id.in_(produto_ids)
    ).all()} if produto_ids else {}

    return [{
        "produto_id": i.produto_id,
        "nome": produtos.get(i.produto_id, "Produto removido"),
        "total_vendido": i.total_vendido,
        "receita": round(float(i.receita or 0), 2),
    } for i in itens]


@router.post("/produtos/carregar-modelo")
def carregar_produtos_modelo(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    existentes = db.query(models.Produto).filter(
        models.Produto.restaurante_id == rest.id
    ).count()
    if existentes > 0:
        raise HTTPException(400, "Restaurante já possui produtos cadastrados")

    try:
        from database.seed.seed_006_produtos_pizzaria import criar_produtos_pizzaria
        criar_produtos_pizzaria(db, rest.id)
        return {"mensagem": "Produtos modelo carregados com sucesso"}
    except ImportError:
        raise HTTPException(500, "Seed de produtos não encontrado")
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Erro ao carregar produtos: {str(e)}")


# ============================================================
# DOMINIOS PERSONALIZADOS
# ============================================================

class DominioCreate(BaseModel):
    dominio: str

@router.get("/dominios")
def listar_dominios(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Lista dominios personalizados do restaurante"""
    dominios = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.restaurante_id == rest.id
    ).order_by(models.DominioPersonalizado.criado_em.desc()).all()

    return [
        {
            "id": d.id,
            "dominio": d.dominio,
            "tipo": d.tipo,
            "verificado": d.verificado,
            "dns_verificado_em": d.dns_verificado_em.isoformat() if d.dns_verificado_em else None,
            "ssl_ativo": d.ssl_ativo,
            "ativo": d.ativo,
            "criado_em": d.criado_em.isoformat() if d.criado_em else None,
        }
        for d in dominios
    ]


@router.post("/dominios")
def criar_dominio(
    dados: DominioCreate,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Adiciona dominio personalizado ao restaurante"""
    dominio_limpo = dados.dominio.strip().lower()

    # Valida formato basico
    if not dominio_limpo or "." not in dominio_limpo:
        raise HTTPException(400, "Dominio invalido")

    # Verifica se ja existe
    existente = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.dominio == dominio_limpo
    ).first()
    if existente:
        raise HTTPException(400, "Dominio ja cadastrado no sistema")

    dominio = models.DominioPersonalizado(
        restaurante_id=rest.id,
        dominio=dominio_limpo,
        tipo="cname",
    )
    db.add(dominio)
    db.commit()
    db.refresh(dominio)

    return {
        "id": dominio.id,
        "dominio": dominio.dominio,
        "instrucoes": {
            "tipo": "CNAME",
            "nome": dominio_limpo.split(".")[0],
            "valor": "proxy.superfood.com.br",
            "ttl": 3600,
            "mensagem": f"Adicione um registro CNAME no DNS do seu dominio apontando para proxy.superfood.com.br"
        }
    }


@router.post("/dominios/{dominio_id}/verificar")
def verificar_dns_dominio(
    dominio_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Verifica se o DNS do dominio esta configurado corretamente"""
    dominio = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.id == dominio_id,
        models.DominioPersonalizado.restaurante_id == rest.id,
    ).first()

    if not dominio:
        raise HTTPException(404, "Dominio nao encontrado")

    # Verifica DNS via socket
    import socket
    try:
        result = socket.getaddrinfo(dominio.dominio, 443)
        if result:
            dominio.verificado = True
            dominio.dns_verificado_em = datetime.utcnow()
            dominio.ssl_ativo = True
            db.commit()
            return {
                "verificado": True,
                "mensagem": f"DNS configurado com sucesso! Seu site estara disponivel em https://{dominio.dominio}"
            }
    except socket.gaierror:
        pass

    return {
        "verificado": False,
        "mensagem": "DNS ainda nao propagou. Pode levar ate 48 horas. Tente novamente mais tarde."
    }


@router.delete("/dominios/{dominio_id}")
def remover_dominio(
    dominio_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Remove dominio personalizado"""
    dominio = db.query(models.DominioPersonalizado).filter(
        models.DominioPersonalizado.id == dominio_id,
        models.DominioPersonalizado.restaurante_id == rest.id,
    ).first()

    if not dominio:
        raise HTTPException(404, "Dominio nao encontrado")

    db.delete(dominio)
    db.commit()
    return {"mensagem": f"Dominio {dominio.dominio} removido com sucesso"}


# ============================================================
# RELATÓRIO ANALYTICS AVANÇADO
# ============================================================

@router.get("/relatorios/analytics")
def relatorio_analytics(
    senha: str = Query(..., description="Senha do restaurante para autenticação dupla"),
    periodo: str = Query("30d", description="Período: 30d, 90d, 12m, anual"),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """
    Relatório analytics avançado com faturamento, projeções, tendências,
    produtos mais vendidos, formas de pagamento, clientes e cancelamentos.
    Requer autenticação dupla (JWT + senha).
    """
    # --- Autenticação dupla: validar senha ---
    if not rest.verificar_senha(senha.strip()):
        raise HTTPException(403, "Senha inválida")

    # --- Calcular datas do período ---
    agora = datetime.utcnow()
    hoje = date.today()
    inicio_mes_atual = datetime(hoje.year, hoje.month, 1)
    inicio_ano_atual = datetime(hoje.year, 1, 1)

    if periodo == "90d":
        inicio_periodo = agora - timedelta(days=90)
    elif periodo == "12m":
        inicio_periodo = agora - timedelta(days=365)
    elif periodo == "anual":
        inicio_periodo = inicio_ano_atual
    else:  # 30d padrão
        inicio_periodo = agora - timedelta(days=30)

    NOMES_DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]

    rest_id = rest.id

    # =============================
    # FATURAMENTO
    # =============================

    # Faturamento mês atual
    faturamento_mes = db.query(
        func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_mes_atual
    ).scalar()
    faturamento_mes = round(float(faturamento_mes), 2)

    # Faturamento ano atual
    faturamento_ano = db.query(
        func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_ano_atual
    ).scalar()
    faturamento_ano = round(float(faturamento_ano), 2)

    # Faturamento dos últimos 6 meses (para projeções e comparações)
    faturamento_por_mes = []
    pedidos_por_mes = []
    for i in range(6):
        # Mês i meses atrás
        mes_ref = hoje.month - i
        ano_ref = hoje.year
        while mes_ref <= 0:
            mes_ref += 12
            ano_ref -= 1
        inicio_ref = datetime(ano_ref, mes_ref, 1)
        if mes_ref == 12:
            fim_ref = datetime(ano_ref + 1, 1, 1)
        else:
            fim_ref = datetime(ano_ref, mes_ref + 1, 1)

        fat_mes = db.query(
            func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
        ).filter(
            models.Pedido.restaurante_id == rest_id,
            models.Pedido.status == 'entregue',
            models.Pedido.data_criacao >= inicio_ref,
            models.Pedido.data_criacao < fim_ref
        ).scalar()

        ped_mes = db.query(func.count(models.Pedido.id)).filter(
            models.Pedido.restaurante_id == rest_id,
            models.Pedido.status == 'entregue',
            models.Pedido.data_criacao >= inicio_ref,
            models.Pedido.data_criacao < fim_ref
        ).scalar()

        faturamento_por_mes.append(float(fat_mes))
        pedidos_por_mes.append(int(ped_mes))

    # Projeção anual: média últimos 3 meses × 12
    ultimos_3_fat = [f for f in faturamento_por_mes[:3] if f > 0]
    if ultimos_3_fat:
        projecao_anual = round((sum(ultimos_3_fat) / len(ultimos_3_fat)) * 12, 2)
    else:
        projecao_anual = 0.0

    # Projeção próximo mês: média ponderada (peso 3 para mais recente, 2, 1)
    pesos = [3, 2, 1]
    soma_ponderada = 0.0
    soma_pesos = 0
    for idx, fat in enumerate(faturamento_por_mes[:3]):
        if fat > 0 or idx == 0:  # Sempre inclui o mês atual mesmo se zero
            soma_ponderada += fat * pesos[idx]
            soma_pesos += pesos[idx]
    projecao_proximo_mes = round(soma_ponderada / soma_pesos, 2) if soma_pesos > 0 else 0.0

    # Comparação com mês anterior (%)
    fat_mes_atual = faturamento_por_mes[0]
    fat_mes_anterior = faturamento_por_mes[1]
    if fat_mes_anterior > 0:
        comparacao_mes_anterior = round(((fat_mes_atual - fat_mes_anterior) / fat_mes_anterior) * 100, 2)
    else:
        comparacao_mes_anterior = 100.0 if fat_mes_atual > 0 else 0.0

    # =============================
    # MELHOR/PIOR DIA E HORÁRIO
    # =============================

    # Distribuição por dia da semana — usar Python para compatibilidade SQLite/PostgreSQL
    pedidos_periodo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo
    ).all()

    dias_stats = {}
    for d in range(7):
        dias_stats[d] = {"pedidos": 0, "faturamento": 0.0}

    horas_stats = {}
    for h in range(24):
        horas_stats[h] = {"pedidos": 0, "faturamento": 0.0}

    for p in pedidos_periodo:
        if p.data_criacao:
            dia_semana = p.data_criacao.weekday()  # 0=Segunda ... 6=Domingo
            hora = p.data_criacao.hour
            valor = float(p.valor_total or 0)

            dias_stats[dia_semana]["pedidos"] += 1
            dias_stats[dia_semana]["faturamento"] += valor

            horas_stats[hora]["pedidos"] += 1
            horas_stats[hora]["faturamento"] += valor

    # Distribuição dia da semana
    distribuicao_dia_semana = []
    for d in range(7):
        distribuicao_dia_semana.append({
            "dia": d,
            "nome": NOMES_DIAS[d],
            "pedidos": dias_stats[d]["pedidos"],
            "faturamento": round(dias_stats[d]["faturamento"], 2)
        })

    # Melhor e pior dia
    dias_com_pedidos = [d for d in distribuicao_dia_semana if d["pedidos"] > 0]
    if dias_com_pedidos:
        melhor_dia = max(dias_com_pedidos, key=lambda x: x["faturamento"])
        pior_dia = min(dias_com_pedidos, key=lambda x: x["faturamento"])
        melhor_dia_semana = {"dia": melhor_dia["nome"], "total_pedidos": melhor_dia["pedidos"], "faturamento": melhor_dia["faturamento"]}
        pior_dia_semana = {"dia": pior_dia["nome"], "total_pedidos": pior_dia["pedidos"], "faturamento": pior_dia["faturamento"]}
    else:
        melhor_dia_semana = {"dia": "N/A", "total_pedidos": 0, "faturamento": 0.0}
        pior_dia_semana = {"dia": "N/A", "total_pedidos": 0, "faturamento": 0.0}

    # Distribuição por hora
    distribuicao_hora = []
    for h in range(24):
        distribuicao_hora.append({
            "hora": h,
            "pedidos": horas_stats[h]["pedidos"],
            "faturamento": round(horas_stats[h]["faturamento"], 2)
        })

    # Horário de pico
    horas_com_pedidos = [h for h in distribuicao_hora if h["pedidos"] > 0]
    if horas_com_pedidos:
        pico = max(horas_com_pedidos, key=lambda x: x["pedidos"])
        horario_pico = {"hora": pico["hora"], "total_pedidos": pico["pedidos"]}
    else:
        horario_pico = {"hora": 0, "total_pedidos": 0}

    # =============================
    # PRODUTOS MAIS VENDIDOS (TOP 20)
    # =============================

    itens_vendidos = db.query(
        models.ItemPedido.produto_id,
        func.sum(models.ItemPedido.quantidade).label('quantidade'),
        func.sum(models.ItemPedido.quantidade * models.ItemPedido.preco_unitario).label('receita')
    ).join(models.Pedido, models.ItemPedido.pedido_id == models.Pedido.id).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo
    ).group_by(models.ItemPedido.produto_id).order_by(
        desc('quantidade')
    ).limit(20).all()

    produto_ids = [i.produto_id for i in itens_vendidos if i.produto_id]
    produtos_map = {}
    if produto_ids:
        produtos_db = db.query(models.Produto).options(
            joinedload(models.Produto.categoria)
        ).filter(models.Produto.id.in_(produto_ids)).all()
        for pr in produtos_db:
            produtos_map[pr.id] = {
                "nome": pr.nome,
                "categoria": pr.categoria.nome if pr.categoria else "Sem categoria"
            }

    total_quantidade_vendida = sum(int(i.quantidade or 0) for i in itens_vendidos)

    produtos_mais_vendidos = []
    for i in itens_vendidos:
        info = produtos_map.get(i.produto_id, {"nome": "Produto removido", "categoria": "N/A"})
        qtd = int(i.quantidade or 0)
        produtos_mais_vendidos.append({
            "nome": info["nome"],
            "categoria": info["categoria"],
            "quantidade": qtd,
            "receita": round(float(i.receita or 0), 2),
            "percentual_vendas": round((qtd / total_quantidade_vendida * 100), 2) if total_quantidade_vendida > 0 else 0.0
        })

    # Categorias mais vendidas
    categorias_vendidas_query = db.query(
        models.CategoriaMenu.nome.label('categoria_nome'),
        func.sum(models.ItemPedido.quantidade).label('quantidade'),
        func.sum(models.ItemPedido.quantidade * models.ItemPedido.preco_unitario).label('receita')
    ).join(
        models.Produto, models.ItemPedido.produto_id == models.Produto.id
    ).join(
        models.CategoriaMenu, models.Produto.categoria_id == models.CategoriaMenu.id
    ).join(
        models.Pedido, models.ItemPedido.pedido_id == models.Pedido.id
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo
    ).group_by(models.CategoriaMenu.nome).order_by(desc('receita')).all()

    total_receita_categorias = sum(float(c.receita or 0) for c in categorias_vendidas_query)

    categorias_mais_vendidas = []
    for c in categorias_vendidas_query:
        rec = float(c.receita or 0)
        categorias_mais_vendidas.append({
            "nome": c.categoria_nome,
            "quantidade": int(c.quantidade or 0),
            "receita": round(rec, 2),
            "percentual": round((rec / total_receita_categorias * 100), 2) if total_receita_categorias > 0 else 0.0
        })

    # =============================
    # FORMAS DE PAGAMENTO
    # =============================

    formas_query = db.query(
        models.Pedido.forma_pagamento,
        func.count(models.Pedido.id).label('total'),
        func.coalesce(func.sum(models.Pedido.valor_total), 0.0).label('valor')
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo,
        models.Pedido.forma_pagamento.isnot(None)
    ).group_by(models.Pedido.forma_pagamento).order_by(desc('total')).all()

    total_formas = sum(int(f.total) for f in formas_query)

    formas_pagamento = []
    for f in formas_query:
        formas_pagamento.append({
            "forma": f.forma_pagamento or "Não informado",
            "total": int(f.total),
            "valor": round(float(f.valor), 2),
            "percentual": round((int(f.total) / total_formas * 100), 2) if total_formas > 0 else 0.0
        })

    # =============================
    # CANCELAMENTOS
    # =============================

    cancelamentos_mes = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'cancelado',
        models.Pedido.data_criacao >= inicio_mes_atual
    ).scalar()

    total_pedidos_mes = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= inicio_mes_atual
    ).scalar()

    taxa_cancelamento = round((cancelamentos_mes / total_pedidos_mes * 100), 2) if total_pedidos_mes > 0 else 0.0

    # Tendência de cancelamentos (dia a dia nos últimos 30 dias)
    cancelamentos_periodo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'cancelado',
        models.Pedido.data_criacao >= agora - timedelta(days=30)
    ).all()

    cancelamentos_por_dia = {}
    for p in cancelamentos_periodo:
        if p.data_criacao:
            dia_str = p.data_criacao.strftime("%Y-%m-%d")
            cancelamentos_por_dia[dia_str] = cancelamentos_por_dia.get(dia_str, 0) + 1

    tendencia_cancelamentos = []
    for i in range(30):
        dia = hoje - timedelta(days=29 - i)
        dia_str = dia.strftime("%Y-%m-%d")
        tendencia_cancelamentos.append({
            "data": dia_str,
            "total": cancelamentos_por_dia.get(dia_str, 0)
        })

    # =============================
    # CLIENTES
    # =============================

    # Clientes únicos com pedido no mês
    clientes_unicos_mes = db.query(
        func.count(func.distinct(models.Pedido.cliente_telefone))
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= inicio_mes_atual,
        models.Pedido.cliente_telefone.isnot(None)
    ).scalar() or 0

    # Clientes novos no mês: telefones cujo PRIMEIRO pedido foi neste mês
    # Subquery: primeiro pedido de cada telefone
    primeiro_pedido_subq = db.query(
        models.Pedido.cliente_telefone,
        func.min(models.Pedido.data_criacao).label('primeiro_pedido')
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.cliente_telefone.isnot(None)
    ).group_by(models.Pedido.cliente_telefone).subquery()

    clientes_novos_mes = db.query(
        func.count(primeiro_pedido_subq.c.cliente_telefone)
    ).filter(
        primeiro_pedido_subq.c.primeiro_pedido >= inicio_mes_atual
    ).scalar() or 0

    # Clientes recorrentes (2+ pedidos no período)
    clientes_recorrentes_subq = db.query(
        models.Pedido.cliente_telefone,
        func.count(models.Pedido.id).label('total_pedidos')
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= inicio_periodo,
        models.Pedido.cliente_telefone.isnot(None)
    ).group_by(models.Pedido.cliente_telefone).subquery()

    clientes_recorrentes = db.query(
        func.count(clientes_recorrentes_subq.c.cliente_telefone)
    ).filter(
        clientes_recorrentes_subq.c.total_pedidos >= 2
    ).scalar() or 0

    total_clientes_periodo = db.query(
        func.count(func.distinct(models.Pedido.cliente_telefone))
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= inicio_periodo,
        models.Pedido.cliente_telefone.isnot(None)
    ).scalar() or 0

    taxa_recorrencia = round((clientes_recorrentes / total_clientes_periodo * 100), 2) if total_clientes_periodo > 0 else 0.0

    # Ticket médio
    total_pedidos_entregues_periodo = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo
    ).scalar() or 0

    faturamento_periodo = db.query(
        func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
    ).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.status == 'entregue',
        models.Pedido.data_criacao >= inicio_periodo
    ).scalar()
    faturamento_periodo = float(faturamento_periodo)

    ticket_medio = round(faturamento_periodo / total_pedidos_entregues_periodo, 2) if total_pedidos_entregues_periodo > 0 else 0.0

    # =============================
    # TIPO DE PEDIDO (entregas vs retiradas)
    # =============================

    entregas_count = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.tipo_entrega == 'entrega',
        models.Pedido.data_criacao >= inicio_periodo
    ).scalar() or 0

    retiradas_count = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.tipo_entrega == 'retirada',
        models.Pedido.data_criacao >= inicio_periodo
    ).scalar() or 0

    entregas_vs_retiradas = {"entregas": entregas_count, "retiradas": retiradas_count}

    # =============================
    # TENDÊNCIA (dia a dia no período)
    # =============================

    # Buscar todos os pedidos no período para agrupar por dia em Python (compatível SQLite/PostgreSQL)
    todos_pedidos_periodo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= inicio_periodo
    ).all()

    tendencia_map = {}
    for p in todos_pedidos_periodo:
        if p.data_criacao:
            dia_str = p.data_criacao.strftime("%Y-%m-%d")
            if dia_str not in tendencia_map:
                tendencia_map[dia_str] = {"pedidos": 0, "faturamento": 0.0, "cancelamentos": 0}
            if p.status == 'cancelado':
                tendencia_map[dia_str]["cancelamentos"] += 1
            if p.status == 'entregue':
                tendencia_map[dia_str]["faturamento"] += float(p.valor_total or 0)
            tendencia_map[dia_str]["pedidos"] += 1

    # Gerar lista dia a dia no período
    dias_no_periodo = (hoje - inicio_periodo.date()).days + 1 if hasattr(inicio_periodo, 'date') else (hoje - inicio_periodo.date()).days + 1
    try:
        data_inicio_date = inicio_periodo.date() if hasattr(inicio_periodo, 'date') else inicio_periodo
        dias_no_periodo = (hoje - data_inicio_date).days + 1
    except Exception:
        dias_no_periodo = 30

    tendencia = []
    for i in range(dias_no_periodo):
        dia = data_inicio_date + timedelta(days=i)
        dia_str = dia.strftime("%Y-%m-%d")
        info = tendencia_map.get(dia_str, {"pedidos": 0, "faturamento": 0.0, "cancelamentos": 0})
        tendencia.append({
            "data": dia_str,
            "pedidos": info["pedidos"],
            "faturamento": round(info["faturamento"], 2),
            "cancelamentos": info["cancelamentos"]
        })

    # =============================
    # COMPARAÇÃO ANUAL
    # =============================

    ano_atual = hoje.year
    ano_anterior = ano_atual - 1

    # Verificar se existem pedidos no ano anterior
    pedidos_ano_anterior = db.query(func.count(models.Pedido.id)).filter(
        models.Pedido.restaurante_id == rest_id,
        models.Pedido.data_criacao >= datetime(ano_anterior, 1, 1),
        models.Pedido.data_criacao < datetime(ano_atual, 1, 1)
    ).scalar() or 0

    comparacao_anual = None
    if pedidos_ano_anterior > 0:
        comparacao_anual = []
        for mes in range(1, 13):
            # Faturamento ano atual
            inicio_mes = datetime(ano_atual, mes, 1)
            if mes == 12:
                fim_mes = datetime(ano_atual + 1, 1, 1)
            else:
                fim_mes = datetime(ano_atual, mes + 1, 1)

            fat_atual = db.query(
                func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
            ).filter(
                models.Pedido.restaurante_id == rest_id,
                models.Pedido.status == 'entregue',
                models.Pedido.data_criacao >= inicio_mes,
                models.Pedido.data_criacao < fim_mes
            ).scalar()

            # Faturamento ano anterior
            inicio_mes_ant = datetime(ano_anterior, mes, 1)
            if mes == 12:
                fim_mes_ant = datetime(ano_anterior + 1, 1, 1)
            else:
                fim_mes_ant = datetime(ano_anterior, mes + 1, 1)

            fat_anterior = db.query(
                func.coalesce(func.sum(models.Pedido.valor_total), 0.0)
            ).filter(
                models.Pedido.restaurante_id == rest_id,
                models.Pedido.status == 'entregue',
                models.Pedido.data_criacao >= inicio_mes_ant,
                models.Pedido.data_criacao < fim_mes_ant
            ).scalar()

            comparacao_anual.append({
                "mes": mes,
                "faturamento_atual": round(float(fat_atual), 2),
                "faturamento_anterior": round(float(fat_anterior), 2)
            })

    # =============================
    # PREVISÃO PRÓXIMOS 3 MESES
    # =============================

    # Média ponderada dos últimos 3 meses (peso 3 para mais recente, 2, 1)
    previsao_proximos_3_meses = []
    for offset_mes in range(1, 4):
        mes_futuro = hoje.month + offset_mes
        ano_futuro = hoje.year
        while mes_futuro > 12:
            mes_futuro -= 12
            ano_futuro += 1

        nome_mes = f"{ano_futuro}-{mes_futuro:02d}"

        # Faturamento estimado: média ponderada
        soma_pond_fat = 0.0
        soma_pond_ped = 0.0
        soma_p = 0
        for idx in range(min(3, len(faturamento_por_mes))):
            peso = 3 - idx  # 3, 2, 1
            soma_pond_fat += faturamento_por_mes[idx] * peso
            soma_pond_ped += pedidos_por_mes[idx] * peso
            soma_p += peso

        fat_estimado = round(soma_pond_fat / soma_p, 2) if soma_p > 0 else 0.0
        ped_estimados = round(soma_pond_ped / soma_p) if soma_p > 0 else 0

        previsao_proximos_3_meses.append({
            "mes": nome_mes,
            "faturamento_estimado": fat_estimado,
            "pedidos_estimados": int(ped_estimados)
        })

    # =============================
    # RESPOSTA FINAL
    # =============================

    return {
        # Faturamento
        "faturamento_mes": faturamento_mes,
        "faturamento_ano": faturamento_ano,
        "projecao_anual": projecao_anual,
        "projecao_proximo_mes": projecao_proximo_mes,
        "comparacao_mes_anterior": comparacao_mes_anterior,

        # Melhor/pior dia e horário
        "melhor_dia_semana": melhor_dia_semana,
        "pior_dia_semana": pior_dia_semana,
        "horario_pico": horario_pico,
        "distribuicao_hora": distribuicao_hora,
        "distribuicao_dia_semana": distribuicao_dia_semana,

        # Produtos mais vendidos
        "produtos_mais_vendidos": produtos_mais_vendidos,
        "categorias_mais_vendidas": categorias_mais_vendidas,

        # Formas de pagamento
        "formas_pagamento": formas_pagamento,

        # Cancelamentos
        "cancelamentos_mes": cancelamentos_mes,
        "taxa_cancelamento": taxa_cancelamento,
        "tendencia_cancelamentos": tendencia_cancelamentos,

        # Clientes
        "clientes_unicos_mes": clientes_unicos_mes,
        "clientes_novos_mes": clientes_novos_mes,
        "clientes_recorrentes": clientes_recorrentes,
        "taxa_recorrencia": taxa_recorrencia,
        "ticket_medio": ticket_medio,

        # Tipo de pedido
        "entregas_vs_retiradas": entregas_vs_retiradas,

        # Tendência
        "tendencia": tendencia,

        # Comparação anual
        "comparacao_anual": comparacao_anual,

        # Previsão
        "previsao_proximos_3_meses": previsao_proximos_3_meses,
    }


# ============================================================
# AUTOCOMPLETE ENDEREÇO
# ============================================================

@router.get("/autocomplete-endereco")
def painel_autocomplete_endereco(
    query: str = Query(..., min_length=3),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Autocomplete de endereço via Mapbox, com proximidade do restaurante."""
    from utils.mapbox_api import autocomplete_address

    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()

    proximity = None
    if config and config.latitude and config.longitude:
        proximity = (config.latitude, config.longitude)
    elif rest.latitude and rest.longitude:
        proximity = (rest.latitude, rest.longitude)

    sugestoes = autocomplete_address(query, proximity)
    return {"sugestoes": sugestoes}


# ============================================================
# MESAS — Gerenciamento de mesas presenciais
# ============================================================

@router.get("/mesas")
def listar_mesas(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Lista mesas agrupadas por numero_mesa (pedidos tipo_entrega='mesa' das últimas 24h)."""
    limite = datetime.utcnow() - timedelta(hours=24)
    pedidos = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.tipo_entrega == 'mesa',
        models.Pedido.numero_mesa.isnot(None),
        models.Pedido.numero_mesa != '',
        models.Pedido.data_criacao >= limite,
    ).order_by(models.Pedido.data_criacao.asc()).all()

    agrupado: dict = {}
    for p in pedidos:
        mesa = p.numero_mesa.strip()
        if mesa not in agrupado:
            agrupado[mesa] = []
        agrupado[mesa].append(p)

    mesas = []
    for numero, pedidos_mesa in agrupado.items():
        ativos = [p for p in pedidos_mesa if p.status not in ('entregue', 'cancelado')]
        pagos = [p for p in pedidos_mesa if p.status == 'entregue']
        cancelados = [p for p in pedidos_mesa if p.status == 'cancelado']

        # Mesa paga: todos entregues, mostrar por 30min após último
        if not ativos and pagos:
            ultimo_pago = max(pagos, key=lambda p: p.atualizado_em or p.data_criacao)
            ts = ultimo_pago.atualizado_em or ultimo_pago.data_criacao
            if (datetime.utcnow() - ts).total_seconds() > 1800:
                continue  # Já passou 30min, não mostrar

        # Se só tem cancelados, não mostrar
        if not ativos and not pagos:
            continue

        status = "aberta" if ativos else "paga"
        valor_total = sum(p.valor_total or 0 for p in pedidos_mesa if p.status != 'cancelado')
        data_mais_antiga = min(p.data_criacao for p in pedidos_mesa) if pedidos_mesa else None
        aberta_desde = data_mais_antiga.isoformat() if data_mais_antiga else None
        tempo_aberta_min = int((datetime.utcnow() - data_mais_antiga).total_seconds() / 60) if data_mais_antiga else 0
        total_itens = sum(
            len((p.itens or '').split('\n')) for p in pedidos_mesa if p.status != 'cancelado' and p.itens
        )

        mesas.append({
            "numero_mesa": numero,
            "status": status,
            "valor_total": round(valor_total, 2),
            "aberta_desde": aberta_desde,
            "tempo_aberta_min": tempo_aberta_min,
            "total_itens": total_itens,
            "pedidos": [
                {
                    "id": p.id,
                    "comanda": p.comanda,
                    "itens": p.itens,
                    "valor_total": p.valor_total,
                    "status": p.status,
                    "forma_pagamento": p.forma_pagamento,
                    "observacoes": p.observacoes,
                    "data_criacao": p.data_criacao.isoformat() if p.data_criacao else None,
                }
                for p in pedidos_mesa if p.status != 'cancelado'
            ],
        })

    total_abertas = sum(1 for m in mesas if m["status"] == "aberta")
    total_pagas = sum(1 for m in mesas if m["status"] == "paga")

    return {"mesas": mesas, "total_abertas": total_abertas, "total_pagas": total_pagas}


class PagarMesaRequest(BaseModel):
    forma_pagamento: Optional[str] = None


@router.post("/mesas/{numero_mesa}/pagar")
async def pagar_mesa(
    numero_mesa: str,
    dados: PagarMesaRequest,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Marca todos pedidos ativos da mesa como 'entregue' e lança no caixa."""
    pedidos_ativos = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.tipo_entrega == 'mesa',
        models.Pedido.numero_mesa == numero_mesa.strip(),
        models.Pedido.status.notin_(['entregue', 'cancelado']),
    ).all()

    if not pedidos_ativos:
        raise HTTPException(404, "Nenhum pedido ativo nesta mesa")

    caixa_aberto = db.query(models.Caixa).filter(
        models.Caixa.restaurante_id == rest.id,
        models.Caixa.status == 'aberto'
    ).first()

    forma_raw = (dados.forma_pagamento or '').strip().lower()
    if 'pix' in forma_raw:
        campo_pgto = 'pix'
    elif 'cart' in forma_raw or 'credito' in forma_raw or 'debito' in forma_raw or 'cartão' in forma_raw:
        campo_pgto = 'cartao'
    elif 'vale' in forma_raw:
        campo_pgto = 'vale'
    else:
        campo_pgto = 'dinheiro'

    valor_total_mesa = 0
    agora = datetime.utcnow()
    for pedido in pedidos_ativos:
        pedido.status = 'entregue'
        pedido.atualizado_em = agora
        pedido.mesa_fechada_em = agora
        if dados.forma_pagamento:
            pedido.forma_pagamento_real = dados.forma_pagamento

        historico = list(pedido.historico_status or [])
        historico.append({"status": "entregue", "timestamp": agora.isoformat()})
        pedido.historico_status = historico

        # Calcular tempo_preparo_real_min se ainda não foi calculado
        if pedido.tempo_preparo_real_min is None and pedido.data_criacao:
            pedido.tempo_preparo_real_min = int((agora - pedido.data_criacao).total_seconds() / 60)

        val = pedido.valor_total or 0
        valor_total_mesa += val

        # Auto-lançar no caixa
        if caixa_aberto and val > 0:
            mov = models.MovimentacaoCaixa(
                caixa_id=caixa_aberto.id,
                tipo='venda',
                valor=val,
                descricao=f"Mesa {numero_mesa} — Pedido #{pedido.comanda} — {dados.forma_pagamento or 'N/I'}",
                forma_pagamento=campo_pgto,
                pedido_id=pedido.id,
            )
            db.add(mov)
            caixa_aberto.total_vendas = (caixa_aberto.total_vendas or 0) + val
            if campo_pgto == 'dinheiro':
                caixa_aberto.total_dinheiro = (caixa_aberto.total_dinheiro or 0) + val
            elif campo_pgto == 'cartao':
                caixa_aberto.total_cartao = (caixa_aberto.total_cartao or 0) + val
            elif campo_pgto == 'pix':
                caixa_aberto.total_pix = (caixa_aberto.total_pix or 0) + val
            elif campo_pgto == 'vale':
                caixa_aberto.total_vale = (caixa_aberto.total_vale or 0) + val

    # Verificar se mesa ficou aberta demais → criar alerta
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    limite_mesa_min = (config.tempo_alerta_mesa_min if config else 60) or 60
    primeiro_pedido = min(pedidos_ativos, key=lambda p: p.data_criacao)
    tempo_total = int((agora - primeiro_pedido.data_criacao).total_seconds() / 60)
    if tempo_total > limite_mesa_min:
        atraso_min = tempo_total - limite_mesa_min
        alerta = models.AlertaAtraso(
            restaurante_id=rest.id,
            pedido_id=primeiro_pedido.id,
            tipo_alerta='atraso_mesa',
            tipo_pedido='mesa',
            tempo_estimado_min=limite_mesa_min,
            tempo_real_min=tempo_total,
            atraso_min=atraso_min,
        )
        db.add(alerta)
        notif_mesa = models.Notificacao(
            restaurante_id=rest.id,
            tipo='alerta_atraso',
            titulo=f'Mesa {numero_mesa} ficou aberta {tempo_total}min',
            mensagem=f'Limite: {limite_mesa_min}min, atraso: {atraso_min}min',
            dados_json={"numero_mesa": numero_mesa, "atraso_min": atraso_min, "tipo_pedido": "mesa"},
        )
        db.add(notif_mesa)

    db.commit()

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "mesa_paga",
            "dados": {"numero_mesa": numero_mesa, "valor_total": round(valor_total_mesa, 2)}
        }, rest.id)
        await ws.broadcast({"tipo": "tempo_medio_atualizado", "dados": {}}, rest.id)

    return {
        "numero_mesa": numero_mesa,
        "pedidos_pagos": len(pedidos_ativos),
        "valor_total": round(valor_total_mesa, 2),
    }


class PedidoMesaRequest(BaseModel):
    itens: str
    valor_total: float
    observacoes: Optional[str] = None
    forma_pagamento: Optional[str] = None


@router.post("/mesas/{numero_mesa}/pedido")
async def adicionar_pedido_mesa(
    numero_mesa: str,
    dados: PedidoMesaRequest,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Cria um pedido para a mesa especificada."""
    mesa = numero_mesa.strip()
    agora = datetime.utcnow()
    proxima_comanda = _gerar_proxima_comanda(db, rest.id)

    pedido = models.Pedido(
        restaurante_id=rest.id,
        comanda=str(proxima_comanda),
        tipo='Mesa',
        origem='manual',
        tipo_entrega='mesa',
        cliente_nome=f"Mesa {mesa}",
        numero_mesa=mesa,
        itens=dados.itens,
        valor_total=dados.valor_total,
        forma_pagamento=dados.forma_pagamento,
        observacoes=dados.observacoes,
        status='pendente',
        historico_status=[{"status": "pendente", "timestamp": agora.isoformat()}],
        data_criacao=agora,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "novo_pedido",
            "dados": {
                "pedido_id": pedido.id,
                "comanda": pedido.comanda,
                "cliente_nome": pedido.cliente_nome,
                "valor_total": pedido.valor_total,
            }
        }, rest.id)

    await _broadcast_imprimir_pedido(request, db, pedido, rest.id)

    return {"id": pedido.id, "comanda": pedido.comanda, "status": pedido.status}


# ============================================================
# HELPER: Gerar próxima comanda de forma segura
# ============================================================

def _gerar_proxima_comanda(db: Session, restaurante_id: int) -> int:
    """Gera próxima comanda usando o último pedido por ID + lock para evitar duplicatas."""
    ultimo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == restaurante_id,
    ).order_by(desc(models.Pedido.id)).with_for_update().first()
    if ultimo and ultimo.comanda and str(ultimo.comanda).isdigit():
        return int(ultimo.comanda) + 1
    return 1


# ============================================================
# HELPER: Verificar e criar alerta de atraso
# ============================================================

def _verificar_e_criar_alerta_atraso(db: Session, rest: models.Restaurante, pedido: models.Pedido):
    """Cria AlertaAtraso + Notificacao se pedido finalizou com atraso."""
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()

    tipo = pedido.tipo_entrega or ''
    tempo_real = pedido.tempo_preparo_real_min
    tempo_configurado = None

    if tipo == 'entrega' and site_config:
        tempo_configurado = site_config.tempo_entrega_estimado
        entrega = pedido.entrega
        if entrega and entrega.delivery_started_at and entrega.delivery_finished_at:
            tempo_delivery = int((entrega.delivery_finished_at - entrega.delivery_started_at).total_seconds() / 60)
            tempo_real = (tempo_real or 0) + tempo_delivery
    elif tipo == 'retirada' and site_config:
        tempo_configurado = site_config.tempo_retirada_estimado
    elif tipo == 'mesa' and config:
        tempo_configurado = config.tempo_medio_preparo

    if tempo_real is None or tempo_configurado is None:
        return

    tolerancia = (config.tolerancia_atraso_min if config else 10) or 10
    atraso = tempo_real - tempo_configurado
    if atraso <= tolerancia:
        return

    alerta = models.AlertaAtraso(
        restaurante_id=rest.id,
        pedido_id=pedido.id,
        tipo_alerta=f'atraso_{tipo}',
        tipo_pedido=tipo,
        tempo_estimado_min=tempo_configurado,
        tempo_real_min=tempo_real,
        atraso_min=atraso,
    )
    db.add(alerta)

    notif = models.Notificacao(
        restaurante_id=rest.id,
        tipo='alerta_atraso',
        titulo=f'Atraso no pedido #{pedido.comanda}',
        mensagem=f'Pedido #{pedido.comanda} ({tipo}) levou {tempo_real}min (estimado: {tempo_configurado}min, atraso: {atraso}min)',
        dados_json={"pedido_id": pedido.id, "atraso_min": atraso, "tipo_pedido": tipo},
    )
    db.add(notif)


# ============================================================
# TEMPO MÉDIO — Configurado vs Real
# ============================================================

@router.get("/tempo-medio")
def get_tempo_medio(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Retorna comparação Configurado vs Real para entrega, retirada e mesa."""
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == rest.id
    ).first()
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()

    resultado = {}

    # ── Entrega ──
    conf_entrega = (site_config.tempo_entrega_estimado if site_config else 50) or 50
    pedidos_entrega = db.query(models.Pedido).options(
        joinedload(models.Pedido.entrega)
    ).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.tipo_entrega == 'entrega',
        models.Pedido.status == 'entregue',
        models.Pedido.tempo_preparo_real_min.isnot(None),
    ).order_by(desc(models.Pedido.atualizado_em)).limit(5).all()

    if pedidos_entrega:
        tempos = []
        for p in pedidos_entrega:
            t = p.tempo_preparo_real_min or 0
            if p.entrega and p.entrega.delivery_started_at and p.entrega.delivery_finished_at:
                t += int((p.entrega.delivery_finished_at - p.entrega.delivery_started_at).total_seconds() / 60)
            tempos.append(t)
        media = int(sum(tempos) / len(tempos))
        resultado["entrega"] = {
            "configurado_min": conf_entrega, "real_min": media,
            "base_pedidos": len(tempos),
            "status": _calcular_status_tempo(conf_entrega, media),
        }
    else:
        resultado["entrega"] = {
            "configurado_min": conf_entrega, "real_min": None,
            "base_pedidos": 0, "status": "sem_dados",
        }

    # ── Retirada ──
    conf_retirada = (site_config.tempo_retirada_estimado if site_config else 20) or 20
    pedidos_retirada = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.tipo_entrega == 'retirada',
        models.Pedido.status == 'entregue',
        models.Pedido.tempo_preparo_real_min.isnot(None),
    ).order_by(desc(models.Pedido.atualizado_em)).limit(5).all()

    if pedidos_retirada:
        media_ret = int(sum(p.tempo_preparo_real_min for p in pedidos_retirada) / len(pedidos_retirada))
        resultado["retirada"] = {
            "configurado_min": conf_retirada, "real_min": media_ret,
            "base_pedidos": len(pedidos_retirada),
            "status": _calcular_status_tempo(conf_retirada, media_ret),
        }
    else:
        resultado["retirada"] = {
            "configurado_min": conf_retirada, "real_min": None,
            "base_pedidos": 0, "status": "sem_dados",
        }

    # ── Mesa ──
    conf_mesa = (config.tempo_medio_preparo if config else 30) or 30
    pedidos_mesa = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id,
        models.Pedido.tipo_entrega == 'mesa',
        models.Pedido.status.in_(['pronto', 'entregue']),
        models.Pedido.tempo_preparo_real_min.isnot(None),
    ).order_by(desc(models.Pedido.atualizado_em)).limit(5).all()

    if pedidos_mesa:
        media_mesa = int(sum(p.tempo_preparo_real_min for p in pedidos_mesa) / len(pedidos_mesa))
        resultado["mesa"] = {
            "configurado_min": conf_mesa, "real_min": media_mesa,
            "base_pedidos": len(pedidos_mesa),
            "status": _calcular_status_tempo(conf_mesa, media_mesa),
        }
    else:
        resultado["mesa"] = {
            "configurado_min": conf_mesa, "real_min": None,
            "base_pedidos": 0, "status": "sem_dados",
        }

    return resultado


def _calcular_status_tempo(configurado: int, real: int) -> str:
    diff = real - configurado
    if diff <= 0:
        return "otimo"
    elif diff <= 5:
        return "ok"
    elif diff <= 15:
        return "atencao"
    else:
        return "critico"


# ============================================================
# ALERTAS DE ATRASO — Persistentes
# ============================================================

@router.get("/alertas-atraso")
def get_alertas_atraso(
    periodo: str = Query("hoje", pattern="^(hoje|7d|30d)$"),
    tipo: str = Query("todos", pattern="^(entrega|retirada|mesa|todos)$"),
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    agora = datetime.utcnow()
    if periodo == "hoje":
        inicio = agora.replace(hour=0, minute=0, second=0, microsecond=0)
    elif periodo == "7d":
        inicio = agora - timedelta(days=7)
    else:
        inicio = agora - timedelta(days=30)

    query = db.query(models.AlertaAtraso).filter(
        models.AlertaAtraso.restaurante_id == rest.id,
        models.AlertaAtraso.criado_em >= inicio,
    )
    if tipo != "todos":
        query = query.filter(models.AlertaAtraso.tipo_pedido == tipo)

    alertas = query.order_by(desc(models.AlertaAtraso.criado_em)).limit(100).all()

    items = [
        {
            "id": a.id, "pedido_id": a.pedido_id,
            "tipo_alerta": a.tipo_alerta, "tipo_pedido": a.tipo_pedido,
            "tempo_estimado_min": a.tempo_estimado_min,
            "tempo_real_min": a.tempo_real_min,
            "atraso_min": a.atraso_min, "resolvido": a.resolvido,
            "criado_em": a.criado_em.isoformat() if a.criado_em else None,
        }
        for a in alertas
    ]
    total_atraso = sum(a.atraso_min or 0 for a in alertas)
    media_atraso = int(total_atraso / len(alertas)) if alertas else 0
    maior_atraso = max((a.atraso_min or 0) for a in alertas) if alertas else 0

    return {
        "alertas": items,
        "resumo": {"total": len(alertas), "media_atraso_min": media_atraso, "maior_atraso_min": maior_atraso},
    }


# ============================================================
# SUGESTÕES DE TEMPO — Histórico + Rejeitar
# ============================================================

@router.get("/sugestoes-tempo/historico")
def get_sugestoes_tempo_historico(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    sugestoes = db.query(models.SugestaoTempo).filter(
        models.SugestaoTempo.restaurante_id == rest.id,
    ).order_by(desc(models.SugestaoTempo.criado_em)).limit(50).all()

    aceitas = sum(1 for s in sugestoes if s.aceita is True)
    rejeitadas = sum(1 for s in sugestoes if s.aceita is False)

    return {
        "sugestoes": [
            {
                "id": s.id, "tipo": s.tipo,
                "valor_antes": s.valor_antes, "valor_sugerido": s.valor_sugerido,
                "aceita": s.aceita, "motivo": s.motivo,
                "criado_em": s.criado_em.isoformat() if s.criado_em else None,
                "respondido_em": s.respondido_em.isoformat() if s.respondido_em else None,
            }
            for s in sugestoes
        ],
        "estatisticas": {"total": len(sugestoes), "aceitas": aceitas, "rejeitadas": rejeitadas},
    }


class RejeitarSugestaoRequest(BaseModel):
    tipo: str
    valor_antes: int
    valor_sugerido: int
    motivo: Optional[str] = None


@router.post("/sugestoes-tempo/rejeitar")
def rejeitar_sugestao_tempo(
    dados: RejeitarSugestaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    sugestao = models.SugestaoTempo(
        restaurante_id=rest.id, tipo=dados.tipo,
        valor_antes=dados.valor_antes, valor_sugerido=dados.valor_sugerido,
        aceita=False, motivo=dados.motivo or 'Rejeitado pelo operador',
        respondido_em=datetime.utcnow(),
    )
    db.add(sugestao)
    db.commit()
    return {"id": sugestao.id, "mensagem": "Sugestão rejeitada registrada"}


# ============================================================
# NOTIFICAÇÕES — CRUD
# ============================================================

@router.get("/notificacoes")
def listar_notificacoes(
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    notifs = db.query(models.Notificacao).filter(
        models.Notificacao.restaurante_id == rest.id,
    ).order_by(desc(models.Notificacao.data_criacao)).limit(50).all()

    nao_lidas = sum(1 for n in notifs if not n.lida)

    return {
        "notificacoes": [
            {
                "id": n.id, "tipo": n.tipo, "titulo": n.titulo,
                "mensagem": n.mensagem, "lida": n.lida,
                "dados_json": n.dados_json,
                "data_criacao": n.data_criacao.isoformat() if n.data_criacao else None,
            }
            for n in notifs
        ],
        "nao_lidas": nao_lidas,
    }


@router.put("/notificacoes/{notif_id}/lida")
def marcar_notificacao_lida(
    notif_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    notif = db.query(models.Notificacao).filter(
        models.Notificacao.id == notif_id,
        models.Notificacao.restaurante_id == rest.id,
    ).first()
    if not notif:
        raise HTTPException(404, "Notificação não encontrada")
    notif.lida = True
    db.commit()
    return {"id": notif.id, "lida": True}


# ============================================================
# PEDIDO RÁPIDO PARA MESA — Picker inline
# ============================================================

class PedidoRapidoMesaItem(BaseModel):
    produto_id: int
    quantidade: int = Field(default=1, ge=1, le=100)
    observacao: Optional[str] = None
    variacoes: Optional[List[dict]] = None


class PedidoRapidoMesaRequest(BaseModel):
    itens: List[PedidoRapidoMesaItem]


@router.post("/mesas/{numero_mesa}/pedido-rapido")
async def pedido_rapido_mesa(
    numero_mesa: str,
    dados: PedidoRapidoMesaRequest,
    request: Request,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    """Endpoint simplificado para adicionar itens a mesa."""
    mesa = numero_mesa.strip()
    if not dados.itens:
        raise HTTPException(400, "Nenhum item informado")

    agora = datetime.utcnow()
    linhas_itens = []
    valor_total = 0.0
    for item in dados.itens:
        prod = db.query(models.Produto).filter(
            models.Produto.id == item.produto_id,
            models.Produto.restaurante_id == rest.id,
        ).first()
        if not prod:
            raise HTTPException(404, f"Produto {item.produto_id} não encontrado")
        if prod.disponivel is False:
            raise HTTPException(400, f"Produto '{prod.nome}' está indisponível")
        preco = prod.preco * item.quantidade
        desc_variacoes = ""
        if item.variacoes:
            for v in item.variacoes:
                # Validar variação contra banco de dados
                var_id = v.get("variacao_id")
                if var_id:
                    var_db = db.query(models.VariacaoProduto).filter(
                        models.VariacaoProduto.id == var_id,
                        models.VariacaoProduto.produto_id == prod.id,
                    ).first()
                    if var_db:
                        preco += (var_db.preco_adicional or 0) * item.quantidade
                        desc_variacoes += f" ({var_db.nome})"
                    else:
                        raise HTTPException(404, f"Variação {var_id} não encontrada para '{prod.nome}'")
                else:
                    preco += (v.get("preco_adicional", 0) or 0) * item.quantidade
                    desc_variacoes += f" ({v.get('nome', '')})"
        valor_total += preco
        obs = f" - {item.observacao}" if item.observacao else ""
        linhas_itens.append(f"{item.quantidade}x {prod.nome}{desc_variacoes}{obs}")

    if valor_total <= 0:
        raise HTTPException(400, "Valor total deve ser maior que zero")

    proxima_comanda = _gerar_proxima_comanda(db, rest.id)

    pedido = models.Pedido(
        restaurante_id=rest.id,
        comanda=str(proxima_comanda),
        tipo='Mesa', origem='mesa', tipo_entrega='mesa',
        cliente_nome=f"Mesa {mesa}", numero_mesa=mesa,
        itens="\n".join(linhas_itens),
        valor_total=round(valor_total, 2),
        status='pendente',
        historico_status=[{"status": "pendente", "timestamp": agora.isoformat()}],
        data_criacao=agora,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "novo_pedido",
            "dados": {
                "pedido_id": pedido.id, "comanda": pedido.comanda,
                "cliente_nome": pedido.cliente_nome, "valor_total": pedido.valor_total,
            }
        }, rest.id)

    await _broadcast_imprimir_pedido(request, db, pedido, rest.id)

    return {"id": pedido.id, "comanda": pedido.comanda, "status": pedido.status, "valor_total": pedido.valor_total}
