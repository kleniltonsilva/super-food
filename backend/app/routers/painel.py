# backend/app/routers/painel.py

"""
Router Painel Restaurante - Todos os endpoints CRUD para o dashboard React
Sprint 1 da migração v4.0
Todos os endpoints requerem auth JWT do restaurante.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, desc
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta, date

from .. import models, database, auth
from ..cache import invalidate_cardapio

router = APIRouter(prefix="/painel", tags=["Painel Restaurante"])


def get_rest(current_restaurante=Depends(auth.get_current_restaurante)):
    return current_restaurante


def _commit_and_invalidate(db: Session, rest_id: int):
    """Commit + invalida cache do cardapio (para mutacoes em produtos/categorias/combos)"""
    db.commit()
    invalidate_cardapio(rest_id)


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
def criar_pedido_manual(
    dados: PedidoManualRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    ultimo = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == rest.id
    ).order_by(desc(models.Pedido.id)).first()
    proxima_comanda = (int(ultimo.comanda) + 1) if ultimo and ultimo.comanda and str(ultimo.comanda).isdigit() else 1

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
        data_criacao=datetime.utcnow()
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return {"id": pedido.id, "comanda": pedido.comanda, "status": pedido.status}


class StatusUpdate(BaseModel):
    status: str


@router.put("/pedidos/{pedido_id}/status")
def atualizar_status_pedido(
    pedido_id: int, dados: StatusUpdate,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    pedido.status = dados.status
    pedido.atualizado_em = datetime.utcnow()
    db.commit()
    return {"id": pedido.id, "status": pedido.status}


class DespachoRequest(BaseModel):
    motoboy_id: Optional[int] = None


@router.post("/pedidos/{pedido_id}/despachar")
def despachar_pedido(
    pedido_id: int, dados: DespachoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")

    if dados.motoboy_id:
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == dados.motoboy_id,
            models.Motoboy.restaurante_id == rest.id,
            models.Motoboy.status == 'ativo'
        ).first()
        if not motoboy:
            raise HTTPException(404, "Motoboy não encontrado")
    else:
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.restaurante_id == rest.id,
            models.Motoboy.status == 'ativo',
            models.Motoboy.disponivel == True
        ).order_by(models.Motoboy.ordem_hierarquia).first()
        if not motoboy:
            raise HTTPException(400, "Nenhum motoboy disponível")

    # Calcular distância restaurante → endereço de entrega
    distancia_km = None
    if rest.latitude and rest.longitude:
        lat_entrega = pedido.latitude_entrega
        lon_entrega = pedido.longitude_entrega
        # Se pedido não tem coords mas tem endereço, geocodificar
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

    entrega = models.Entrega(
        pedido_id=pedido.id,
        motoboy_id=motoboy.id,
        status='pendente',
        atribuido_em=datetime.utcnow(),
        distancia_km=distancia_km
    )
    db.add(entrega)
    pedido.despachado = True
    pedido.status = 'em_preparo'
    motoboy.entregas_pendentes = (motoboy.entregas_pendentes or 0) + 1
    motoboy.ultima_rota_em = datetime.utcnow()
    db.commit()
    return {"id": pedido.id, "motoboy_id": motoboy.id, "motoboy_nome": motoboy.nome}


@router.put("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(
    pedido_id: int,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id, models.Pedido.restaurante_id == rest.id
    ).first()
    if not pedido:
        raise HTTPException(404, "Pedido não encontrado")
    pedido.status = 'cancelado'
    pedido.atualizado_em = datetime.utcnow()
    db.commit()
    return {"id": pedido.id, "status": "cancelado"}


# ============================================================
# 1.4 CATEGORIAS
# ============================================================

class CategoriaRequest(BaseModel):
    nome: str
    descricao: Optional[str] = None
    icone: Optional[str] = None
    imagem_url: Optional[str] = None
    ordem_exibicao: Optional[int] = 0


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
        ordem_exibicao=dados.ordem_exibicao
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
    vars = db.query(models.VariacaoProduto).filter(
        models.VariacaoProduto.produto_id == prod_id,
        models.VariacaoProduto.ativo == True
    ).order_by(models.VariacaoProduto.ordem).all()
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
    var = models.VariacaoProduto(produto_id=prod_id, **dados.model_dump())
    db.add(var)
    db.commit()
    db.refresh(var)
    return {"id": var.id, "nome": var.nome}


@router.put("/variacoes/{var_id}")
def editar_variacao(
    var_id: int, dados: VariacaoRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    var = db.query(models.VariacaoProduto).join(models.Produto).filter(
        models.VariacaoProduto.id == var_id,
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
    var = db.query(models.VariacaoProduto).join(models.Produto).filter(
        models.VariacaoProduto.id == var_id,
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
    capacidade_entregas: Optional[int] = 3
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
    } for m in motoboys]


@router.post("/motoboys")
def cadastrar_motoboy(
    dados: MotoboyRequest,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
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
        cpf=dados.cpf, status='ativo', ordem_hierarquia=max_ordem + 1
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
    motoboy.nome = dados.nome
    motoboy.usuario = dados.usuario
    motoboy.telefone = dados.telefone
    motoboy.capacidade_entregas = dados.capacidade_entregas
    if dados.cpf:
        motoboy.cpf = dados.cpf
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
        "movimentacoes": [{
            "id": m.id, "tipo": m.tipo, "valor": m.valor,
            "descricao": m.descricao, "data_hora": m.data_hora.isoformat() if m.data_hora else None,
        } for m in movs],
    }


class AbrirCaixaRequest(BaseModel):
    operador: str
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
        operador_abertura=dados.operador,
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
    operador: str
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
    caixa.operador_fechamento = dados.operador
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
        "horario_abertura": config.horario_abertura,
        "horario_fechamento": config.horario_fechamento,
        "dias_semana_abertos": config.dias_semana_abertos,
        # Localização do restaurante (de Restaurante, não ConfigRestaurante)
        "endereco_completo": rest.endereco_completo,
        "latitude": rest.latitude,
        "longitude": rest.longitude,
    }


@router.put("/config")
def atualizar_config(
    dados: dict,
    rest: models.Restaurante = Depends(get_rest),
    db: Session = Depends(database.get_db)
):
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == rest.id
    ).first()
    if not config:
        config = models.ConfigRestaurante(restaurante_id=rest.id)
        db.add(config)

    campos_validos = {
        'status_atual', 'modo_despacho', 'raio_entrega_km', 'tempo_medio_preparo',
        'despacho_automatico', 'modo_prioridade_entrega', 'taxa_entrega_base',
        'distancia_base_km', 'taxa_km_extra', 'valor_base_motoboy', 'valor_km_extra_motoboy',
        'taxa_diaria', 'valor_lanche', 'max_pedidos_por_rota',
        'permitir_ver_saldo_motoboy', 'permitir_finalizar_fora_raio',
        'distancia_base_motoboy_km', 'horario_abertura', 'horario_fechamento',
        'dias_semana_abertos'
    }
    for campo, valor in dados.items():
        if campo in campos_validos:
            setattr(config, campo, valor)

    db.commit()
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
    }


@router.put("/config/site")
def atualizar_site_config(
    dados: dict,
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
        'meta_title', 'meta_description', 'meta_keywords'
    }
    for campo, valor in dados.items():
        if campo in campos_validos:
            setattr(sc, campo, valor)

    db.commit()
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
