"""
Router App Garçom — Endpoints para o PWA de atendimento em mesa
Sprint 19 — App Garçom
Todos os endpoints requerem auth JWT do garçom (role=garcom).
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from .. import models, database, auth

router = APIRouter(prefix="/garcom", tags=["App Garçom"])


def get_garcom(current_garcom=Depends(auth.get_current_garcom)):
    return current_garcom


# ========== Schemas ==========

class AbrirMesaRequest(BaseModel):
    qtd_pessoas: int = Field(ge=1, le=50, default=1)
    alergia: Optional[str] = None
    tags: Optional[List[str]] = None
    notas: Optional[str] = None


class TransferirMesaRequest(BaseModel):
    mesa_destino_id: int


class ItemPedidoGarcom(BaseModel):
    item_cardapio_id: int
    qty: int = Field(ge=1, default=1)
    obs: Optional[str] = None
    course: Optional[str] = None  # couvert, bebida, entrada, principal, sobremesa


class CriarPedidoGarcomRequest(BaseModel):
    itens: List[ItemPedidoGarcom]
    observacoes: Optional[str] = None


class ItemEsgotadoRequest(BaseModel):
    item_cardapio_id: int


# ========== Endpoints Mesas ==========

@router.get("/mesas")
def listar_mesas(
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Lista mesas do restaurante com status (LIVRE/OCUPADA/FECHANDO) e sessão ativa."""
    rest_id = garcom.restaurante_id

    # Buscar config do restaurante para saber qtd de mesas
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest_id
    ).first()

    # Buscar sessões ativas (ABERTA ou FECHANDO)
    sessoes_ativas = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.status.in_(["ABERTA", "FECHANDO"])
    ).all()

    sessao_por_mesa = {}
    for s in sessoes_ativas:
        sessao_por_mesa[s.mesa_id] = {
            "sessao_id": s.id,
            "status": s.status,
            "garcom_id": s.garcom_id,
            "garcom_nome": s.garcom.nome if s.garcom else None,
            "qtd_pessoas": s.qtd_pessoas,
            "alergia": s.alergia,
            "tags": s.tags,
            "notas": s.notas,
            "subtotal": s.subtotal,
            "taxa": s.taxa,
            "total": s.total,
            "criado_em": s.criado_em.isoformat() if s.criado_em else None,
        }

    # Mesas — usar campo existente do restaurante ou default 20
    # Pedidos de mesa usam numero_mesa como string "1", "2", etc.
    total_mesas = 20  # Default
    if config and hasattr(config, 'tempo_alerta_mesa_min'):
        # Contar mesas a partir de pedidos existentes ou usar um número razoável
        max_mesa_pedido = db.query(func.max(models.SessaoMesa.mesa_id)).filter(
            models.SessaoMesa.restaurante_id == rest_id
        ).scalar()
        if max_mesa_pedido and max_mesa_pedido > total_mesas:
            total_mesas = max_mesa_pedido

    mesas = []
    for i in range(1, total_mesas + 1):
        sessao = sessao_por_mesa.get(i)
        if sessao:
            mesa_status = sessao["status"]  # ABERTA ou FECHANDO
        else:
            mesa_status = "LIVRE"

        mesas.append({
            "mesa_id": i,
            "status": mesa_status,
            "sessao": sessao,
        })

    return {"mesas": mesas, "total": total_mesas}


@router.post("/mesas/{mesa_id}/abrir")
def abrir_mesa(
    mesa_id: int,
    dados: AbrirMesaRequest,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Abre uma sessão em uma mesa."""
    rest_id = garcom.restaurante_id

    # Verificar se mesa já tem sessão ativa
    sessao_existente = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.mesa_id == mesa_id,
        models.SessaoMesa.status.in_(["ABERTA", "FECHANDO"])
    ).first()

    if sessao_existente:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mesa já está ocupada"
        )

    sessao = models.SessaoMesa(
        restaurante_id=rest_id,
        mesa_id=mesa_id,
        garcom_id=garcom.id,
        status="ABERTA",
        qtd_pessoas=dados.qtd_pessoas,
        alergia=dados.alergia,
        tags=dados.tags,
        notas=dados.notas,
    )
    db.add(sessao)
    db.commit()
    db.refresh(sessao)

    return {
        "sessao_id": sessao.id,
        "mesa_id": mesa_id,
        "status": "ABERTA",
        "garcom": garcom.nome,
    }


@router.post("/mesas/{mesa_id}/transferir")
def transferir_mesa(
    mesa_id: int,
    dados: TransferirMesaRequest,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Transfere uma sessão ativa de uma mesa para outra mesa livre."""
    rest_id = garcom.restaurante_id

    # Buscar sessão ativa da mesa origem
    sessao = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.mesa_id == mesa_id,
        models.SessaoMesa.status.in_(["ABERTA", "FECHANDO"])
    ).first()

    if not sessao:
        raise HTTPException(status_code=404, detail="Mesa não tem sessão ativa")

    # Verificar se mesa destino está livre
    destino_ocupada = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.mesa_id == dados.mesa_destino_id,
        models.SessaoMesa.status.in_(["ABERTA", "FECHANDO"])
    ).first()

    if destino_ocupada:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Mesa de destino já está ocupada"
        )

    # Transferir
    sessao.mesa_id = dados.mesa_destino_id
    db.commit()

    return {
        "sessao_id": sessao.id,
        "mesa_origem": mesa_id,
        "mesa_destino": dados.mesa_destino_id,
        "status": sessao.status,
    }


# ========== Endpoints Sessões ==========

@router.get("/sessoes/{sessao_id}")
def detalhe_sessao(
    sessao_id: int,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Detalhe de uma sessão com pedidos e itens por course."""
    rest_id = garcom.restaurante_id

    sessao = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.id == sessao_id,
        models.SessaoMesa.restaurante_id == rest_id,
    ).first()

    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")

    # Buscar pedidos vinculados
    sessao_pedidos = db.query(models.SessaoPedido).filter(
        models.SessaoPedido.sessao_id == sessao_id
    ).all()

    pedidos_list = []
    for sp in sessao_pedidos:
        pedido = db.query(models.Pedido).options(
            joinedload(models.Pedido.itens_detalhados)
        ).filter(models.Pedido.id == sp.pedido_id).first()
        if not pedido:
            continue

        itens = []
        for item in pedido.itens_detalhados:
            produto = db.query(models.Produto).filter(models.Produto.id == item.produto_id).first()
            itens.append({
                "item_id": item.id,
                "produto_id": item.produto_id,
                "nome": produto.nome if produto else "Item removido",
                "quantidade": item.quantidade,
                "preco_unitario": item.preco_unitario,
                "observacoes": item.observacoes,
                "subtotal": item.quantidade * item.preco_unitario,
            })

        pedidos_list.append({
            "pedido_id": pedido.id,
            "comanda": pedido.comanda,
            "course": pedido.course,
            "status": pedido.status,
            "observacoes": pedido.observacoes,
            "valor_total": pedido.valor_total,
            "criado_em": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
            "itens": itens,
        })

    # Config garçom para taxa de serviço
    config = db.query(models.ConfigGarcom).filter(
        models.ConfigGarcom.restaurante_id == rest_id
    ).first()
    taxa_servico = config.taxa_servico if config else 0.10
    pct_taxa = config.pct_taxa if config else True

    return {
        "sessao_id": sessao.id,
        "mesa_id": sessao.mesa_id,
        "status": sessao.status,
        "garcom_id": sessao.garcom_id,
        "qtd_pessoas": sessao.qtd_pessoas,
        "alergia": sessao.alergia,
        "tags": sessao.tags,
        "notas": sessao.notas,
        "subtotal": sessao.subtotal,
        "taxa": sessao.taxa,
        "total": sessao.total,
        "criado_em": sessao.criado_em.isoformat() if sessao.criado_em else None,
        "pedidos": pedidos_list,
        "config": {
            "taxa_servico": taxa_servico,
            "pct_taxa": pct_taxa,
        }
    }


@router.post("/sessoes/{sessao_id}/pedidos")
async def criar_pedido_sessao(
    sessao_id: int,
    dados: CriarPedidoGarcomRequest,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Cria um pedido dentro de uma sessão de mesa e envia para a cozinha (KDS)."""
    rest_id = garcom.restaurante_id

    sessao = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.id == sessao_id,
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.status == "ABERTA",
    ).first()

    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou fechada")

    if not dados.itens:
        raise HTTPException(status_code=400, detail="Nenhum item no pedido")

    # Verificar itens esgotados
    itens_esgotados_ids = [ie.item_cardapio_id for ie in db.query(models.ItemEsgotado).filter(
        models.ItemEsgotado.restaurante_id == rest_id,
        models.ItemEsgotado.ativo == True
    ).all()]

    for item in dados.itens:
        if item.item_cardapio_id in itens_esgotados_ids:
            produto = db.query(models.Produto).filter(models.Produto.id == item.item_cardapio_id).first()
            nome = produto.nome if produto else f"#{item.item_cardapio_id}"
            raise HTTPException(status_code=400, detail=f"Item esgotado: {nome}")

    # Calcular valor total
    valor_total = 0.0
    itens_detalhados = []
    carrinho_json_items = []

    for item in dados.itens:
        produto = db.query(models.Produto).filter(
            models.Produto.id == item.item_cardapio_id,
            models.Produto.restaurante_id == rest_id,
        ).first()
        if not produto:
            raise HTTPException(status_code=404, detail=f"Produto #{item.item_cardapio_id} não encontrado")

        preco = produto.preco_promocional if produto.promocao and produto.preco_promocional else produto.preco
        subtotal = preco * item.qty
        valor_total += subtotal

        itens_detalhados.append({
            "produto_id": produto.id,
            "nome": produto.nome,
            "quantidade": item.qty,
            "preco_unitario": preco,
            "observacoes": item.obs,
        })

        carrinho_json_items.append({
            "id": produto.id,
            "nome": produto.nome,
            "quantidade": item.qty,
            "preco": preco,
            "observacoes": item.obs,
            "course": item.course,
        })

    # Gerar comanda
    import secrets
    comanda = f"M{sessao.mesa_id}-{secrets.token_hex(2).upper()}"

    # Criar pedido
    course_principal = dados.itens[0].course if dados.itens[0].course else None
    pedido = models.Pedido(
        restaurante_id=rest_id,
        comanda=comanda,
        tipo="mesa",
        origem="garcom",
        marketplace_source="derekh_garcom",
        tipo_origem="garcom",
        label_origem=f"Mesa {sessao.mesa_id} - {garcom.nome}",
        course=course_principal,
        cliente_nome=f"Mesa {sessao.mesa_id}",
        numero_mesa=str(sessao.mesa_id),
        itens=", ".join([f"{i['quantidade']}x {i['nome']}" for i in itens_detalhados]),
        carrinho_json=carrinho_json_items,
        valor_total=valor_total,
        valor_subtotal=valor_total,
        observacoes=dados.observacoes,
        status="em_preparo",
        historico_status=[{"status": "em_preparo", "timestamp": datetime.utcnow().isoformat()}],
    )
    db.add(pedido)
    db.flush()

    # Criar ItemPedido detalhados
    for item_data in itens_detalhados:
        item_pedido = models.ItemPedido(
            pedido_id=pedido.id,
            produto_id=item_data["produto_id"],
            quantidade=item_data["quantidade"],
            preco_unitario=item_data["preco_unitario"],
            observacoes=item_data["observacoes"],
        )
        db.add(item_pedido)

    # Vincular à sessão
    sessao_pedido = models.SessaoPedido(
        sessao_id=sessao.id,
        pedido_id=pedido.id,
    )
    db.add(sessao_pedido)

    # Atualizar subtotal da sessão
    sessao.subtotal = (sessao.subtotal or 0) + valor_total
    # Calcular taxa de serviço
    config_garcom = db.query(models.ConfigGarcom).filter(
        models.ConfigGarcom.restaurante_id == rest_id
    ).first()
    if config_garcom and config_garcom.pct_taxa:
        sessao.taxa = sessao.subtotal * (config_garcom.taxa_servico or 0.10)
    elif config_garcom:
        sessao.taxa = config_garcom.taxa_servico or 0
    sessao.total = sessao.subtotal + (sessao.taxa or 0)

    # Enviar para KDS se ativo
    config_kds = db.query(models.ConfigCozinha).filter(
        models.ConfigCozinha.restaurante_id == rest_id
    ).first()

    if config_kds and config_kds.kds_ativo:
        pedido_cozinha = models.PedidoCozinha(
            restaurante_id=rest_id,
            pedido_id=pedido.id,
            status="NOVO",
        )
        db.add(pedido_cozinha)

    db.commit()
    db.refresh(pedido)

    # Broadcast WebSocket
    ws_manager = getattr(request.app.state, 'ws_manager', None)
    kds_mgr = getattr(request.app.state, 'kds_manager', None)

    if ws_manager:
        await ws_manager.broadcast({
            "tipo": "novo_pedido",
            "dados": {
                "pedido_id": pedido.id,
                "comanda": pedido.comanda,
                "mesa": sessao.mesa_id,
                "origem": "garcom",
                "garcom": garcom.nome,
            }
        }, rest_id)

    if kds_mgr and config_kds and config_kds.kds_ativo:
        await kds_mgr.broadcast({
            "tipo": "kds:novo_pedido",
            "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
        }, rest_id)

    return {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "valor_total": valor_total,
        "itens": len(dados.itens),
        "sessao_subtotal": sessao.subtotal,
        "sessao_total": sessao.total,
    }


@router.post("/sessoes/{sessao_id}/solicitar-fechamento")
async def solicitar_fechamento(
    sessao_id: int,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Solicita fechamento da sessão (status → FECHANDO)."""
    rest_id = garcom.restaurante_id

    sessao = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.id == sessao_id,
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.status == "ABERTA",
    ).first()

    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou já em fechamento")

    sessao.status = "FECHANDO"
    db.commit()

    # Broadcast para admin
    ws_manager = getattr(request.app.state, 'ws_manager', None)
    if ws_manager:
        await ws_manager.broadcast({
            "tipo": "garcom:mesa_fechando",
            "dados": {
                "sessao_id": sessao.id,
                "mesa_id": sessao.mesa_id,
                "total": sessao.total,
                "garcom": garcom.nome,
            }
        }, rest_id)

    return {
        "sessao_id": sessao.id,
        "status": "FECHANDO",
        "total": sessao.total,
    }


@router.post("/sessoes/{sessao_id}/repetir-rodada")
async def repetir_rodada(
    sessao_id: int,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Repete o último pedido da sessão."""
    rest_id = garcom.restaurante_id

    sessao = db.query(models.SessaoMesa).filter(
        models.SessaoMesa.id == sessao_id,
        models.SessaoMesa.restaurante_id == rest_id,
        models.SessaoMesa.status == "ABERTA",
    ).first()

    if not sessao:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou fechada")

    # Buscar último pedido da sessão
    ultimo_sp = db.query(models.SessaoPedido).filter(
        models.SessaoPedido.sessao_id == sessao_id
    ).order_by(models.SessaoPedido.id.desc()).first()

    if not ultimo_sp:
        raise HTTPException(status_code=404, detail="Nenhum pedido anterior para repetir")

    ultimo_pedido = db.query(models.Pedido).options(
        joinedload(models.Pedido.itens_detalhados)
    ).filter(models.Pedido.id == ultimo_sp.pedido_id).first()

    if not ultimo_pedido:
        raise HTTPException(status_code=404, detail="Pedido anterior não encontrado")

    # Criar novo pedido com os mesmos itens
    itens = [
        ItemPedidoGarcom(
            item_cardapio_id=item.produto_id,
            qty=item.quantidade,
            obs=item.observacoes,
            course=ultimo_pedido.course,
        )
        for item in ultimo_pedido.itens_detalhados
        if item.produto_id
    ]

    if not itens:
        raise HTTPException(status_code=400, detail="Pedido anterior sem itens válidos para repetir")

    # Reutilizar o endpoint de criação
    req = CriarPedidoGarcomRequest(itens=itens, observacoes="(Repetição)")
    return await criar_pedido_sessao(sessao_id, req, request, garcom, db)


# ========== Endpoints Itens de Pedido ==========

@router.delete("/pedidos/{pedido_id}/itens/{item_id}")
async def cancelar_item(
    pedido_id: int,
    item_id: int,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Cancela um item de um pedido (só se pedido ainda em preparo)."""
    rest_id = garcom.restaurante_id

    # Verificar permissão de cancelamento
    config = db.query(models.ConfigGarcom).filter(
        models.ConfigGarcom.restaurante_id == rest_id
    ).first()
    if config and not config.permitir_cancelamento:
        raise HTTPException(status_code=403, detail="Cancelamento de itens não permitido")

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == rest_id,
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    if pedido.status not in ("pendente", "em_preparo"):
        raise HTTPException(status_code=400, detail="Pedido já passou da fase de preparo")

    item = db.query(models.ItemPedido).filter(
        models.ItemPedido.id == item_id,
        models.ItemPedido.pedido_id == pedido_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    # Recalcular valor
    valor_removido = item.quantidade * item.preco_unitario
    pedido.valor_total = max(0, (pedido.valor_total or 0) - valor_removido)
    pedido.valor_subtotal = max(0, (pedido.valor_subtotal or 0) - valor_removido)

    db.delete(item)

    # Atualizar subtotal da sessão
    sp = db.query(models.SessaoPedido).filter(
        models.SessaoPedido.pedido_id == pedido_id
    ).first()
    if sp:
        sessao = db.query(models.SessaoMesa).filter(
            models.SessaoMesa.id == sp.sessao_id
        ).first()
        if sessao:
            sessao.subtotal = max(0, (sessao.subtotal or 0) - valor_removido)
            config_garcom = db.query(models.ConfigGarcom).filter(
                models.ConfigGarcom.restaurante_id == rest_id
            ).first()
            if config_garcom and config_garcom.pct_taxa:
                sessao.taxa = sessao.subtotal * (config_garcom.taxa_servico or 0.10)
            sessao.total = sessao.subtotal + (sessao.taxa or 0)

    db.commit()

    return {"removido": True, "item_id": item_id, "valor_removido": valor_removido}


# ========== Endpoints Itens Esgotados ==========

@router.get("/itens-esgotados")
def listar_itens_esgotados(
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Lista itens esgotados do restaurante."""
    itens = db.query(models.ItemEsgotado).filter(
        models.ItemEsgotado.restaurante_id == garcom.restaurante_id,
        models.ItemEsgotado.ativo == True,
    ).all()

    result = []
    for ie in itens:
        produto = db.query(models.Produto).filter(models.Produto.id == ie.item_cardapio_id).first()
        result.append({
            "id": ie.id,
            "item_cardapio_id": ie.item_cardapio_id,
            "nome": produto.nome if produto else f"#{ie.item_cardapio_id}",
            "reportado_por": ie.reportado_por,
            "criado_em": ie.criado_em.isoformat() if ie.criado_em else None,
        })

    return result


@router.post("/itens-esgotados")
async def marcar_esgotado(
    dados: ItemEsgotadoRequest,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Marca um item do cardápio como esgotado."""
    rest_id = garcom.restaurante_id

    # Verificar se já está esgotado
    existente = db.query(models.ItemEsgotado).filter(
        models.ItemEsgotado.restaurante_id == rest_id,
        models.ItemEsgotado.item_cardapio_id == dados.item_cardapio_id,
        models.ItemEsgotado.ativo == True,
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Item já está esgotado")

    ie = models.ItemEsgotado(
        restaurante_id=rest_id,
        item_cardapio_id=dados.item_cardapio_id,
        reportado_por=garcom.id,
    )
    db.add(ie)
    db.commit()
    db.refresh(ie)

    # Broadcast para todos os garçons
    garcom_mgr = getattr(request.app.state, 'garcom_manager', None)
    if garcom_mgr:
        produto = db.query(models.Produto).filter(models.Produto.id == dados.item_cardapio_id).first()
        await garcom_mgr.broadcast({
            "tipo": "garcom:item_esgotado",
            "dados": {
                "item_cardapio_id": dados.item_cardapio_id,
                "nome": produto.nome if produto else f"#{dados.item_cardapio_id}",
                "reportado_por": garcom.nome,
            }
        }, rest_id)

    return {"id": ie.id, "item_cardapio_id": ie.item_cardapio_id}


@router.delete("/itens-esgotados/{id}")
async def desmarcar_esgotado(
    id: int,
    request: Request,
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Desmarca um item como esgotado (volta a estar disponível)."""
    rest_id = garcom.restaurante_id

    ie = db.query(models.ItemEsgotado).filter(
        models.ItemEsgotado.id == id,
        models.ItemEsgotado.restaurante_id == rest_id,
    ).first()
    if not ie:
        raise HTTPException(status_code=404, detail="Item esgotado não encontrado")

    ie.ativo = False
    db.commit()

    # Broadcast
    garcom_mgr = getattr(request.app.state, 'garcom_manager', None)
    if garcom_mgr:
        await garcom_mgr.broadcast({
            "tipo": "garcom:item_disponivel",
            "dados": {"item_cardapio_id": ie.item_cardapio_id}
        }, rest_id)

    return {"removido": True}


# ========== Endpoint Cardápio (para o app garçom) ==========

@router.get("/cardapio")
def cardapio_garcom(
    garcom: models.Garcom = Depends(get_garcom),
    db: Session = Depends(database.get_db),
):
    """Retorna o cardápio do restaurante para o app garçom (categorias + produtos)."""
    rest_id = garcom.restaurante_id

    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == rest_id,
        models.CategoriaMenu.ativo == True,
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    # Itens esgotados
    esgotados_ids = set(
        ie.item_cardapio_id for ie in db.query(models.ItemEsgotado).filter(
            models.ItemEsgotado.restaurante_id == rest_id,
            models.ItemEsgotado.ativo == True,
        ).all()
    )

    result = []
    for cat in categorias:
        produtos = db.query(models.Produto).filter(
            models.Produto.restaurante_id == rest_id,
            models.Produto.categoria_id == cat.id,
            models.Produto.disponivel == True,
        ).order_by(models.Produto.ordem_exibicao).all()

        items = []
        for p in produtos:
            preco = p.preco_promocional if p.promocao and p.preco_promocional else p.preco
            items.append({
                "id": p.id,
                "nome": p.nome,
                "descricao": p.descricao,
                "preco": preco,
                "preco_original": p.preco if p.promocao else None,
                "imagem_url": p.imagem_url,
                "esgotado": p.id in esgotados_ids,
                "eh_pizza": p.eh_pizza,
            })

        result.append({
            "id": cat.id,
            "nome": cat.nome,
            "icone": cat.icone,
            "produtos": items,
        })

    return result
