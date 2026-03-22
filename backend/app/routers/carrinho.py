# backend/app/routers/carrinho.py

"""
Router Carrinho - Gerenciamento do carrinho de compras
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional
from datetime import datetime, timedelta
import uuid
import random

from .. import models, database
from ..schemas import carrinho_schemas
from .auth_cliente import get_cliente_opcional

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
        flag_modified(carrinho, "itens_json")

    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    taxa = carrinho.valor_taxa_entrega or 0.0
    desconto = carrinho.valor_desconto or 0.0
    carrinho.valor_total = carrinho.valor_subtotal + taxa - desconto

    db.commit()
    db.refresh(carrinho)

    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega or 0.0,
        "valor_desconto": carrinho.valor_desconto or 0.0,
        "valor_total": carrinho.valor_total
    }


@router.post("/adicionar-combo", response_model=carrinho_schemas.CarrinhoResponse)
def adicionar_combo(
    payload: dict,
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Adiciona todos os itens de um combo ao carrinho"""
    combo_id = payload.get("combo_id")
    if not combo_id:
        raise HTTPException(status_code=400, detail="combo_id é obrigatório")

    combo = db.query(models.Combo).filter(
        models.Combo.id == combo_id,
        models.Combo.ativo == True
    ).first()

    if not combo:
        raise HTTPException(status_code=404, detail="Combo não encontrado")

    combo_itens = db.query(models.ComboItem).filter(
        models.ComboItem.combo_id == combo.id
    ).all()

    if not combo_itens:
        raise HTTPException(status_code=400, detail="Combo sem itens")

    # Busca carrinho existente
    carrinho = db.query(models.Carrinho).filter(
        models.Carrinho.restaurante_id == combo.restaurante_id,
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ).first()

    # Monta itens do combo como um único item no carrinho
    nomes_itens = []
    for ci in combo_itens:
        produto = db.query(models.Produto).filter(models.Produto.id == ci.produto_id).first()
        if produto:
            nomes_itens.append(f"{ci.quantidade}x {produto.nome}")

    novo_item = {
        "produto_id": None,
        "combo_id": combo.id,
        "nome": f"COMBO: {combo.nome}",
        "imagem_url": combo.imagem_url,
        "variacoes": [],
        "observacoes": " | ".join(nomes_itens),
        "quantidade": 1,
        "preco_unitario": combo.preco_combo,
        "subtotal": combo.preco_combo
    }

    if not carrinho:
        carrinho = models.Carrinho(
            restaurante_id=combo.restaurante_id,
            sessao_id=sessao_id,
            itens_json=[novo_item],
            data_expiracao=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(carrinho)
    else:
        itens = carrinho.itens_json or []
        itens.append(novo_item)
        carrinho.itens_json = itens
        carrinho.data_atualizacao = datetime.utcnow()
        flag_modified(carrinho, "itens_json")

    carrinho.valor_subtotal = sum(i['subtotal'] for i in carrinho.itens_json)
    taxa = carrinho.valor_taxa_entrega or 0.0
    desconto = carrinho.valor_desconto or 0.0
    carrinho.valor_total = carrinho.valor_subtotal + taxa - desconto

    db.commit()
    db.refresh(carrinho)

    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega or 0.0,
        "valor_desconto": carrinho.valor_desconto or 0.0,
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
    codigo_acesso: str = "",
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Atualiza quantidade de um item no carrinho"""
    filtros = [
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ]
    if codigo_acesso:
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.codigo_acesso == codigo_acesso.upper()
        ).first()
        if restaurante:
            filtros.append(models.Carrinho.restaurante_id == restaurante.id)
    carrinho = db.query(models.Carrinho).filter(*filtros).first()
    
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    
    if item_index < 0 or item_index >= len(carrinho.itens_json):
        raise HTTPException(status_code=400, detail="Item não encontrado no carrinho")
    
    # Atualiza quantidade
    carrinho.itens_json[item_index]['quantidade'] = nova_quantidade
    carrinho.itens_json[item_index]['subtotal'] = carrinho.itens_json[item_index]['preco_unitario'] * nova_quantidade
    flag_modified(carrinho, "itens_json")

    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    carrinho.valor_total = carrinho.valor_subtotal + (carrinho.valor_taxa_entrega or 0.0) - (carrinho.valor_desconto or 0.0)
    carrinho.data_atualizacao = datetime.utcnow()

    db.commit()
    db.refresh(carrinho)

    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega or 0.0,
        "valor_desconto": carrinho.valor_desconto or 0.0,
        "valor_total": carrinho.valor_total
    }


@router.delete("/remover/{item_index}", response_model=carrinho_schemas.CarrinhoResponse)
def remover_item(
    item_index: int,
    codigo_acesso: str = "",
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Remove item do carrinho"""
    filtros = [
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ]
    if codigo_acesso:
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.codigo_acesso == codigo_acesso.upper()
        ).first()
        if restaurante:
            filtros.append(models.Carrinho.restaurante_id == restaurante.id)
    carrinho = db.query(models.Carrinho).filter(*filtros).first()
    
    if not carrinho:
        raise HTTPException(status_code=404, detail="Carrinho não encontrado")
    
    if item_index < 0 or item_index >= len(carrinho.itens_json):
        raise HTTPException(status_code=400, detail="Item não encontrado")
    
    # Remove item
    carrinho.itens_json.pop(item_index)
    flag_modified(carrinho, "itens_json")

    # Recalcula totais
    carrinho.valor_subtotal = sum(item['subtotal'] for item in carrinho.itens_json)
    carrinho.valor_total = carrinho.valor_subtotal + (carrinho.valor_taxa_entrega or 0.0) - (carrinho.valor_desconto or 0.0)
    carrinho.data_atualizacao = datetime.utcnow()

    db.commit()
    db.refresh(carrinho)

    return {
        "id": carrinho.id,
        "sessao_id": carrinho.sessao_id,
        "itens": carrinho.itens_json,
        "quantidade_itens": len(carrinho.itens_json),
        "valor_subtotal": carrinho.valor_subtotal,
        "valor_taxa_entrega": carrinho.valor_taxa_entrega or 0.0,
        "valor_desconto": carrinho.valor_desconto or 0.0,
        "valor_total": carrinho.valor_total
    }


@router.delete("/limpar")
def limpar_carrinho(
    codigo_acesso: str = "",
    sessao_id: str = Depends(get_or_create_sessao_id),
    db: Session = Depends(database.get_db)
):
    """Limpa carrinho completamente"""
    filtros = [models.Carrinho.sessao_id == sessao_id]
    if codigo_acesso:
        restaurante = db.query(models.Restaurante).filter(
            models.Restaurante.codigo_acesso == codigo_acesso.upper()
        ).first()
        if restaurante:
            filtros.append(models.Carrinho.restaurante_id == restaurante.id)
    carrinho = db.query(models.Carrinho).filter(*filtros).first()
    
    if carrinho:
        db.delete(carrinho)
        db.commit()
    
    return {"mensagem": "Carrinho limpo com sucesso"}


@router.post("/finalizar", response_model=dict)
async def finalizar_carrinho(
    finalizacao: carrinho_schemas.FinalizarCarrinhoRequest,
    request: Request,
    sessao_id: str = Depends(get_or_create_sessao_id),
    cliente: Optional[models.Cliente] = Depends(get_cliente_opcional),
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
    # Busca restaurante pelo codigo_acesso se informado
    restaurante_id_filtro = None
    if finalizacao.codigo_acesso:
        rest = db.query(models.Restaurante).filter(
            models.Restaurante.codigo_acesso == finalizacao.codigo_acesso.upper()
        ).first()
        if rest:
            restaurante_id_filtro = rest.id

    # Busca carrinho
    filtros_carrinho = [
        models.Carrinho.sessao_id == sessao_id,
        models.Carrinho.data_expiracao > datetime.utcnow()
    ]
    if restaurante_id_filtro:
        filtros_carrinho.append(models.Carrinho.restaurante_id == restaurante_id_filtro)
    carrinho = db.query(models.Carrinho).filter(*filtros_carrinho).first()

    if not carrinho or not carrinho.itens_json:
        raise HTTPException(status_code=400, detail="Carrinho vazio")

    # Verifica se é restaurante demo
    _rest_for_demo = db.query(models.Restaurante).filter(
        models.Restaurante.id == carrinho.restaurante_id
    ).first()
    _is_demo = bool(_rest_for_demo and _rest_for_demo.email and _rest_for_demo.email.endswith("@superfood.test"))

    # Verificar se restaurante está aberto (skip para demos)
    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == carrinho.restaurante_id
    ).first()
    if not _is_demo and config_rest and config_rest.status_atual != "aberto":
        horario_msg = ""
        if config_rest.horario_abertura and config_rest.horario_fechamento:
            horario_msg = f" Horário de funcionamento: {config_rest.horario_abertura} às {config_rest.horario_fechamento}."
        raise HTTPException(
            status_code=403,
            detail=f"Restaurante fechado no momento. Não é possível realizar pedidos.{horario_msg}"
        )

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
    
    # Geocodifica endereço se não veio com coordenadas
    lat_entrega = finalizacao.latitude
    lng_entrega = finalizacao.longitude

    # Demo: auto-gerar coordenadas e taxa fixa
    if _is_demo and finalizacao.tipo_entrega == "entrega":
        if not (lat_entrega and lng_entrega) and _rest_for_demo.latitude:
            lat_entrega = _rest_for_demo.latitude + random.uniform(-0.015, 0.015)
            lng_entrega = _rest_for_demo.longitude + random.uniform(-0.015, 0.015)
        taxa_entrega = 5.0
    else:
        if finalizacao.endereco_entrega and not (lat_entrega and lng_entrega):
            try:
                from utils.mapbox_api import geocode_address
                coords = geocode_address(finalizacao.endereco_entrega)
                if coords:
                    lat_entrega, lng_entrega = coords
            except Exception:
                pass  # Segue sem coordenadas se geocoding falhar

        # Calcula taxa de entrega real se tem coordenadas
        taxa_entrega = 0.0
        if lat_entrega and lng_entrega and finalizacao.tipo_entrega == "entrega":
            restaurante = db.query(models.Restaurante).filter(
                models.Restaurante.id == carrinho.restaurante_id
            ).first()
            config = db.query(models.ConfigRestaurante).filter(
                models.ConfigRestaurante.restaurante_id == carrinho.restaurante_id
            ).first()
            if restaurante and restaurante.latitude and restaurante.longitude and config:
                from utils.mapbox_api import check_coverage_zone
                resultado = check_coverage_zone(
                    (restaurante.latitude, restaurante.longitude),
                    (lat_entrega, lng_entrega),
                    config.raio_entrega_km or 10.0
                )
                if resultado['dentro_zona']:
                    distancia = resultado['distancia_km']
                    if distancia <= config.distancia_base_km:
                        taxa_entrega = config.taxa_entrega_base
                    else:
                        taxa_entrega = config.taxa_entrega_base + (distancia - config.distancia_base_km) * config.taxa_km_extra

    valor_total_final = carrinho.valor_subtotal + taxa_entrega - carrinho.valor_desconto

    # Cria pedido
    pedido = models.Pedido(
        restaurante_id=carrinho.restaurante_id,
        cliente_id=cliente.id if cliente else None,
        comanda=proxima_comanda,
        tipo="Entrega" if finalizacao.tipo_entrega == "entrega" else "Retirada na loja",
        origem="site",
        tipo_entrega=finalizacao.tipo_entrega,
        cliente_nome=finalizacao.cliente_nome if finalizacao.cliente_nome else (cliente.nome if cliente else ""),
        cliente_telefone=finalizacao.cliente_telefone if finalizacao.cliente_telefone else (cliente.telefone if cliente else ""),
        endereco_entrega=finalizacao.endereco_entrega,
        latitude_entrega=lat_entrega,
        longitude_entrega=lng_entrega,
        itens="\n".join([f"{item['quantidade']}x {item['nome']}" for item in carrinho.itens_json]),
        carrinho_json=carrinho.itens_json,
        observacoes=finalizacao.observacoes,
        valor_subtotal=round(carrinho.valor_subtotal, 2),
        valor_taxa_entrega=round(taxa_entrega, 2),
        valor_total=round(valor_total_final, 2),
        forma_pagamento=finalizacao.forma_pagamento,
        troco_para=finalizacao.troco_para,
        status='pendente',
        historico_status=[{"status": "pendente", "timestamp": datetime.utcnow().isoformat()}],
        data_criacao=datetime.utcnow()
    )

    db.add(pedido)

    # Auto-aceitar pedido do site: se restaurante configurado e cliente tem histórico positivo
    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == carrinho.restaurante_id
    ).first()

    if config_rest and config_rest.aceitar_pedido_site_auto and cliente:
        # Verifica se cliente tem ao menos 1 pedido concluído (entregue ou finalizado)
        pedido_anterior = db.query(models.Pedido).filter(
            models.Pedido.cliente_id == cliente.id,
            models.Pedido.restaurante_id == carrinho.restaurante_id,
            models.Pedido.status.in_(['entregue', 'finalizado'])
        ).first()

        if pedido_anterior:
            pedido.status = 'confirmado'

    # Auto-enviar para KDS se cozinha digital está ativa
    try:
        config_kds = db.query(models.ConfigCozinha).filter(
            models.ConfigCozinha.restaurante_id == carrinho.restaurante_id,
            models.ConfigCozinha.kds_ativo == True
        ).first()
        if config_kds:
            # Mudar status para em_preparo e criar PedidoCozinha
            pedido.status = 'em_preparo'
            historico = list(pedido.historico_status or [])
            historico.append({"status": "em_preparo", "timestamp": datetime.utcnow().isoformat()})
            pedido.historico_status = historico

            pc_novo = models.PedidoCozinha(
                restaurante_id=carrinho.restaurante_id,
                pedido_id=pedido.id,
                status='NOVO',
                criado_em=datetime.utcnow(),
            )
            db.add(pc_novo)
    except Exception:
        pass  # Tabelas KDS podem não existir ainda

    # Limpa carrinho
    db.delete(carrinho)

    db.commit()
    db.refresh(pedido)

    # Broadcast WebSocket para painel admin — alerta sonoro novo pedido
    ws = getattr(request.app.state, 'ws_manager', None)
    if ws:
        await ws.broadcast({
            "tipo": "novo_pedido",
            "dados": {
                "pedido_id": pedido.id,
                "comanda": pedido.comanda,
                "cliente_nome": pedido.cliente_nome,
                "valor_total": pedido.valor_total,
                "origem": "site",
            }
        }, pedido.restaurante_id)

    # Broadcast KDS se auto-enviou para cozinha
    try:
        config_kds_check = db.query(models.ConfigCozinha).filter(
            models.ConfigCozinha.restaurante_id == pedido.restaurante_id,
            models.ConfigCozinha.kds_ativo == True
        ).first()
        if config_kds_check and pedido.status == 'em_preparo':
            kds_ws = getattr(request.app.state, 'kds_manager', None)
            if kds_ws:
                await kds_ws.broadcast({
                    "tipo": "kds:novo_pedido",
                    "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
                }, pedido.restaurante_id)
    except Exception:
        pass

    # Broadcast para printer agent (impressão automática)
    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == pedido.restaurante_id
    ).first()
    if config_rest and config_rest.impressao_automatica:
        pm = getattr(request.app.state, 'printer_manager', None)
        if pm:
            await pm.broadcast({
                "tipo": "imprimir_pedido",
                "dados": {"pedido_id": pedido.id, "comanda": pedido.comanda}
            }, pedido.restaurante_id)

    # ── Pix Online: se restaurante aderiu e forma_pagamento é PIX, criar cobrança ──
    pix_config = None
    try:
        pix_config = db.query(models.PixConfig).filter(
            models.PixConfig.restaurante_id == pedido.restaurante_id,
            models.PixConfig.ativo == True,
        ).first()
    except Exception:
        pass  # PixConfig table may not exist yet (migration 028 pending)

    if pix_config and finalizacao.forma_pagamento and finalizacao.forma_pagamento.upper() == "PIX":
        try:
            from ..pix.pix_service import criar_cobranca_pedido
            pix_data = await criar_cobranca_pedido(pedido.id, db)
            return {
                "pedido_id": pedido.id,
                "comanda": pedido.comanda,
                "status": pedido.status,
                "mensagem": "Pedido realizado com sucesso!",
                "pix_online": True,
                "pix_qr_code": pix_data.get("qr_code_image", ""),
                "pix_br_code": pix_data.get("br_code", ""),
                "pix_expira_em": pix_data.get("expira_em", ""),
            }
        except Exception as e:
            import logging
            logging.getLogger("superfood.pix").warning(f"Erro ao criar cobrança Pix para pedido {pedido.id}: {e}")

    return {
        "pedido_id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "mensagem": "Pedido realizado com sucesso!"
    }