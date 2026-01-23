# backend/app/routers/carrinho.py

"""
Router Carrinho - Gerenciamento do carrinho de compras
"""

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import uuid

from .. import models, database
from ..schemas import carrinho_schemas

router = APIRouter(prefix="/carrinho", tags=["Carrinho"])


def get_or_create_sessao_id(sessao_id: Optional[str] = Header(None, alias="X-Session-ID")) -> str:
    """Retorna sessao_id do header ou cria um novo"""
    if not sessao_id:
        sessao_id = str(uuid.uuid4())
    return sessao_id


@router.post("/adicionar", response_model=carrinho_schemas.CarrinhoResponse)
def adicionar_item(
    item: carrinho_schemas.AdicionarItemRequest,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """
    Adiciona item ao carrinho
    
    Args:
        item: Dados do produto, variações, quantidade
        sessao_id: ID da sessão (auto-gerado se não existir)
    
    Returns:
        Carrinho atualizado com todos os itens
    """
    # Valida produto
    produto = db.query(models.Produto).filter(
        models.Produto.id == item.produto_id,
        models.Produto.disponivel == True
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não disponível")
    
    # Busca carrinho existente
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.restaurante_id == produto.restaurante_id,
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()
    
    # Calcula preço do item
    preco_unitario = produto.preco_promocional if produto.promocao else produto.preco
    
    # Adiciona preço das variações
    for variacao_id in item.variacoes_ids:
        variacao = db.query(models.VariacaoProduto).filter(
            models.VariacaoProduto.id == variacao_id,
            models.VariacaoProduto.produto_id == item.produto_id
        ).first()
        if variacao:
            preco_unitario += variacao.preco_adicional
    
    subtotal_item = preco_unitario * item.quantidade
    
    # Monta item JSON
    novo_item = {
        "produto_id": item.produto_id,
        "nome": produto.nome,
        "imagem_url": produto.imagem_url,
        "variacoes": [
            {
                "id": v_id,
                "nome": db.query(models.VariacaoProduto).get(v_id).nome if db.query(models.VariacaoProduto).get(v_id) else ""
            }
            for v_id in item.variacoes_ids
        ],
        "observacoes": item.observacoes,
        "quantidade": item.quantidade,
        "preco_unitario": preco_unitario,
        "subtotal": subtotal_item
    }
    
    if not carrinho:
        # Cria novo carrinho
        carrinho = models.Carrinho(
            restaurante_id=produto.restaurante_id,
            sessao_id=sessao_id,
            itens_json=[novo_item],
            data_expiracao=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(carrinho)
    else:
        # Adiciona ao carrinho existente
        itens = carrinho.itens_json or []
        itens.append(novo_item)
        carrinho.itens_json = itens
        carrinho.data_atualizacao = datetime.utcnow()
    
    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    carrinho.valor_total = carrinho.valor_subtotal + carrinho.valor_taxa_entrega - carrinho.valor_desconto
    
    db.commit()
    db.refresh(carrinho)
    
    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega,
        "valor_desconto": carrinho.valor_desconto,
        "valor_total": carrinho.valor_total
    }


@router.get("/", response_model=carrinho_schemas.CarrinhoResponse)
def get_carrinho(
    codigo_acesso: str,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Retorna carrinho da sessão atual"""
    # Busca restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Busca carrinho
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.restaurante_id == restaurante.id,
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()
    
    if not carrinho:
        # Retorna carrinho vazio
        return {
            "id": None,
            "sessao_id": sessao_id,
            "itens": [],
            "quantidade_itens": 0,
            "valor_subtotal": 0.0,
            "valor_taxa_entrega": 0.0,
            "valor_desconto": 0.0,
            "valor_total": 0.0
        }
    
    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json or []),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega,
        "valor_desconto": carrinho.valor_desconto,
        "valor_total": carrinho.valor_total
    }


@router.put("/atualizar-quantidade/{item_index}", response_model=carrinho_schemas.CarrinhoResponse)
def atualizar_quantidade(
    item_index: int,
    nova_quantidade: int,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Atualiza quantidade de um item no carrinho"""
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()
    
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    
    if item_index < 0 or item_index >= len(carrinho.itens_json):
        raise HTTPException(status_code=400, detail="Item não encontrado no carrinho")
    
    # Atualiza quantidade
    carrinho.itens_json[item_index]['quantidade'] = nova_quantidade
    carrinho.itens_json[item_index]['subtotal'] = carrinho.itens_json[item_index]['preco_unitario'] * nova_quantidade
    
    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    carrinho.valor_total = carrinho.valor_subtotal + carrinho.valor_taxa_entrega - carrinho.valor_desconto
    carrinho.data_atualizacao = datetime.utcnow()
    
    db.commit()
    db.refresh(carrinho)
    
    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega,
        "valor_desconto": carrinho.valor_desconto,
        "valor_total": carrinho.valor_total
    }


@router.delete("/remover/{item_index}", response_model=carrinho_schemas.CarrinhoResponse)
def remover_item(
    item_index: int,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Remove item do carrinho"""
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()
    
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    
    if item_index < 0 or item_index >= len(carrinho.itens_json):
        raise HTTPException(status_code=400, detail="Item não encontrado")
    
    # Remove item
    carrinho.itens_json.pop(item_index)
    
    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    carrinho.valor_total = carrinho.valor_subtotal + carrinho.valor_taxa_entrega - carrinho.valor_desconto
    carrinho.data_atualizacao = datetime.utcnow()
    
    db.commit()
    db.refresh(carrinho)
    
    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega,
        "valor_desconto": carrinho.valor_desconto,
        "valor_total": carrinho.valor_total
    }


@router.delete("/limpar")
def limpar_carrinho(
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Limpa carrinho completamente"""
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.sessao_id == sessao_id
    ).first()
    
    if carrinho:
        db.delete(carrinho)
        db.commit()
    
    return {"mensagem": "Carrinho limpo com sucesso"}


@router.post("/finalizar", response_model=dict)
def finalizar_carrinho(
    finalizacao: carrinho_schemas.FinalizarCarrinhoRequest,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """
    Finaliza carrinho e cria pedido
    
    Args:
        finalizacao: Dados do cliente, endereço, forma pagamento
        sessao_id: ID da sessão
    
    Returns:
        ID do pedido criado
    """
    # Busca carrinho
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()
    
    if not carrinho or not carrinho.itens_json:
        raise HTTPException(status_code=400, detail="Carrinho vazio")
    
    # Busca site config para validar pedido mínimo
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == carrinho.restaurante_id
    ).first()
    
    if site_config and carrinho.valor_subtotal < site_config.pedido_minimo:
        raise HTTPException(
            status_code=400,
            detail=f"Pedido mínimo de R$ {site_config.pedido_minimo:.2f}"
        )
    
    # Gera número da comanda
    ultimo_pedido = db.query(models.Pedido).filter(
        models.Pedido.restaurante_id == carrinho.restaurante_id
    ).order_by(models.Pedido.id.desc()).first()
    
    proxima_comanda = str(int(ultimo_pedido.comanda) + 1) if ultimo_pedido and ultimo_pedido.comanda.isdigit() else "1"
    
    # Cria pedido
    pedido = models.Pedido(
        restaurante_id=carrinho.restaurante_id,
        comanda=proxima_comanda,
        tipo="Entrega" if finalizacao.tipo_entrega == "entrega" else "Retirada na loja",
        origem="site",
        tipo_entrega=finalizacao.tipo_entrega,
        cliente_nome=finalizacao.cliente_nome,
        cliente_telefone=finalizacao.cliente_telefone,
        endereco_entrega=finalizacao.endereco_entrega,
        latitude_entrega=finalizacao.latitude,
        longitude=finalizacao.longitude,
        itens="\n".join([f"{item['quantidade']}x {item['nome']}" for item in carrinho.itens_json]),
        carrinho_json=carrinho.itens_json,
        observacoes=finalizacao.observacoes,
        valor_total=carrinho.valor_total,
        forma_pagamento=finalizacao.forma_pagamento,
        troco_para=finalizacao.troco_para,
        status='pendente',
        data_criacao=datetime.utcnow()
    )
    
    db.add(pedido)
    
    # Limpa carrinho
    db.delete(carrinho)
    
    db.commit()
    db.refresh(pedido)
    
    return {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "mensagem": "Pedido realizado com sucesso!"
    }