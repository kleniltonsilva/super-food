# backend/app/routers/site_cliente.py

"""
Router Site do Cliente - APIs públicas para o site
Endpoints para buscar cardápio, validar endereços, etc
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import os

from .. import models, database
from ..schemas import site_schemas
from ..cache import cache_get, cache_set
from utils.mapbox_api import autocomplete_address, check_coverage_zone

router = APIRouter(prefix="/site", tags=["Site do Cliente"])


@router.get("/{codigo_acesso}", response_model=site_schemas.SiteInfoPublic)
def get_site_info(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna informacoes publicas do site do restaurante"""
    # Cache: site info (5 min)
    cache_key = f"site:{codigo_acesso}:info"
    cached = cache_get(cache_key)
    if cached:
        return cached

    # Busca restaurante
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper(),
        models.Restaurante.ativo == True
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Busca config do site
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()
    
    if not site_config or not site_config.site_ativo:
        raise HTTPException(status_code=503, detail="Site temporariamente indisponível")
    
    # Busca config operacional
    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()
    
    result = {
        "restaurante_id": restaurante.id,
        "codigo_acesso": restaurante.codigo_acesso,
        "nome_fantasia": restaurante.nome_fantasia,
        "telefone": restaurante.telefone,
        "endereco_completo": restaurante.endereco_completo,
        "tipo_restaurante": site_config.tipo_restaurante,
        "tema_cor_primaria": site_config.tema_cor_primaria,
        "tema_cor_secundaria": site_config.tema_cor_secundaria,
        "logo_url": site_config.logo_url,
        "banner_principal_url": site_config.banner_principal_url,
        "whatsapp_numero": site_config.whatsapp_numero,
        "whatsapp_ativo": site_config.whatsapp_ativo,
        "whatsapp_mensagem_padrao": site_config.whatsapp_mensagem_padrao,
        "pedido_minimo": site_config.pedido_minimo,
        "tempo_entrega_estimado": site_config.tempo_entrega_estimado,
        "tempo_retirada_estimado": site_config.tempo_retirada_estimado,
        "aceita_dinheiro": site_config.aceita_dinheiro,
        "aceita_cartao": site_config.aceita_cartao,
        "aceita_pix": site_config.aceita_pix,
        "aceita_vale_refeicao": site_config.aceita_vale_refeicao,
        "aceita_agendamento": site_config.aceita_agendamento,
        "status_aberto": config_rest.status_atual == 'aberto' if config_rest else False,
        "horario_abertura": config_rest.horario_abertura if config_rest else "18:00",
        "horario_fechamento": config_rest.horario_fechamento if config_rest else "23:00",
        "dias_semana_abertos": config_rest.dias_semana_abertos.split(',') if config_rest else []
    }
    cache_set(cache_key, result, ttl_seconds=300)  # 5 min
    return result


@router.get("/{codigo_acesso}/categorias", response_model=List[site_schemas.CategoriaPublic])
def get_categorias(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna categorias do menu"""
    # Cache: categorias (5 min)
    cache_key = f"cardapio:{codigo_acesso}:categorias"
    cached = cache_get(cache_key)
    if cached:
        return cached

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante nao encontrado")

    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante.id,
        models.CategoriaMenu.ativo == True
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    result = [
        {"id": c.id, "nome": c.nome, "descricao": getattr(c, 'descricao', None),
         "icone": getattr(c, 'icone', None), "ordem_exibicao": c.ordem_exibicao, "ativo": c.ativo}
        for c in categorias
    ]
    cache_set(cache_key, result, ttl_seconds=300)
    return result


@router.get("/{codigo_acesso}/produtos", response_model=List[site_schemas.ProdutoPublic])
def get_produtos(
    codigo_acesso: str,
    categoria_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    destaque: Optional[bool] = Query(None, description="Apenas destaques"),
    promocao: Optional[bool] = Query(None, description="Apenas promoções"),
    busca: Optional[str] = Query(None, description="Buscar por nome"),
    db: Session = Depends(database.get_db)
):
    """
    Retorna produtos do cardápio com filtros
    
    Args:
        codigo_acesso: Código do restaurante
        categoria_id: Filtrar por categoria (opcional)
        destaque: Se True, retorna apenas produtos em destaque
        promocao: Se True, retorna apenas produtos em promoção
        busca: Buscar por nome do produto
    """
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Query base
    query = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante.id,
        models.Produto.disponivel == True
    )
    
    # Aplicar filtros
    if categoria_id:
        query = query.filter(models.Produto.categoria_id == categoria_id)
    
    if destaque is not None:
        query = query.filter(models.Produto.destaque == destaque)
    
    if promocao is not None:
        query = query.filter(models.Produto.promocao == promocao)
    
    if busca:
        query = query.filter(
            models.Produto.nome.ilike(f"%{busca}%") |
            models.Produto.descricao.ilike(f"%{busca}%")
        )
    
    # Ordenar por destaque, depois por ordem
    query = query.order_by(
        models.Produto.destaque.desc(),
        models.Produto.ordem_exibicao,
        models.Produto.nome
    )
    
    produtos = query.all()
    
    # Adicionar variações
    resultado = []
    for produto in produtos:
        variacoes = db.query(models.VariacaoProduto).filter(
            models.VariacaoProduto.produto_id == produto.id,
            models.VariacaoProduto.ativo == True
        ).order_by(models.VariacaoProduto.ordem).all()
        
        produto_dict = {
            "id": produto.id,
            "nome": produto.nome,
            "descricao": produto.descricao,
            "preco": produto.preco,
            "preco_promocional": produto.preco_promocional if produto.promocao else None,
            "imagem_url": produto.imagem_url,
            "destaque": produto.destaque,
            "promocao": produto.promocao,
            "categoria_id": produto.categoria_id,
            "variacoes": [
                {
                    "id": v.id,
                    "tipo_variacao": v.tipo_variacao,
                    "nome": v.nome,
                    "descricao": v.descricao,
                    "preco_adicional": v.preco_adicional,
                    "estoque_disponivel": v.estoque_disponivel,
                    "max_sabores": v.max_sabores or 1
                }
                for v in variacoes
            ]
        }
        resultado.append(produto_dict)
    
    return resultado


@router.get("/{codigo_acesso}/produto/{produto_id}", response_model=site_schemas.ProdutoDetalhadoPublic)
def get_produto_detalhado(
    codigo_acesso: str,
    produto_id: int,
    db: Session = Depends(database.get_db)
):
    """Retorna detalhes completos de um produto"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    produto = db.query(models.Produto).filter(
        models.Produto.id == produto_id,
        models.Produto.restaurante_id == restaurante.id
    ).first()
    
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    
    # Busca variações
    variacoes = db.query(models.VariacaoProduto).filter(
        models.VariacaoProduto.produto_id == produto_id,
        models.VariacaoProduto.ativo == True
    ).order_by(models.VariacaoProduto.ordem).all()
    
    # Agrupa variações por tipo
    variacoes_agrupadas = {}
    for v in variacoes:
        if v.tipo_variacao not in variacoes_agrupadas:
            variacoes_agrupadas[v.tipo_variacao] = []
        variacoes_agrupadas[v.tipo_variacao].append({
            "id": v.id,
            "nome": v.nome,
            "descricao": v.descricao,
            "preco_adicional": v.preco_adicional,
            "estoque_disponivel": v.estoque_disponivel,
            "max_sabores": v.max_sabores or 1
        })
    
    return {
        "id": produto.id,
        "nome": produto.nome,
        "descricao": produto.descricao,
        "preco": produto.preco,
        "preco_promocional": produto.preco_promocional if produto.promocao else None,
        "imagem_url": produto.imagem_url,
        "imagens_adicionais": produto.imagens_adicionais_json or [],
        "destaque": produto.destaque,
        "promocao": produto.promocao,
        "categoria_id": produto.categoria_id,
        "variacoes_agrupadas": variacoes_agrupadas
    }


@router.post("/{codigo_acesso}/validar-entrega", response_model=site_schemas.ValidacaoEntregaResponse)
def validar_endereco_entrega(
    codigo_acesso: str,
    validacao: site_schemas.ValidacaoEntregaRequest,
    db: Session = Depends(database.get_db)
):
    """
    Valida se o endereço está na zona de cobertura
    
    Args:
        codigo_acesso: Código do restaurante
        validacao: Dados do endereço (lat, lon ou texto)
    
    Returns:
        dentro_zona, distancia_km, tempo_estimado, mensagem
    """
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Busca config
    config = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()
    
    site_config = db.query(models.SiteConfig).filter(
        models.SiteConfig.restaurante_id == restaurante.id
    ).first()
    
    if not restaurante.latitude or not restaurante.longitude:
        raise HTTPException(status_code=500, detail="Coordenadas do restaurante não configuradas")
    
    # Se enviou texto, geocodifica
    if validacao.endereco_texto and not (validacao.latitude and validacao.longitude):
        from utils.mapbox_api import geocode_address
        coords = geocode_address(validacao.endereco_texto)
        if not coords:
            raise HTTPException(status_code=400, detail="Endereço não encontrado")
        validacao.latitude, validacao.longitude = coords
    
    # Valida zona de cobertura
    raio_km = config.raio_entrega_km if config else 10.0
    
    resultado = check_coverage_zone(
        (restaurante.latitude, restaurante.longitude),
        (validacao.latitude, validacao.longitude),
        raio_km
    )
    
    # Calcula taxa de entrega
    taxa_entrega = 0.0
    if resultado['dentro_zona'] and config:
        distancia = resultado['distancia_km']
        if distancia <= config.distancia_base_km:
            taxa_entrega = config.taxa_entrega_base
        else:
            taxa_entrega = config.taxa_entrega_base + (distancia - config.distancia_base_km) * config.taxa_km_extra
    
    return {
        "dentro_zona": resultado['dentro_zona'],
        "distancia_km": resultado['distancia_km'],
        "tempo_estimado_min": site_config.tempo_entrega_estimado if site_config else 50,
        "taxa_entrega": round(taxa_entrega, 2),
        "mensagem": resultado['mensagem']
    }


@router.get("/{codigo_acesso}/autocomplete-endereco")
def autocomplete_endereco(
    codigo_acesso: str,
    query: str = Query(..., min_length=3, description="Texto do endereço"),
    db: Session = Depends(database.get_db)
):
    """
    Retorna sugestões de endereços conforme o usuário digita
    
    Args:
        codigo_acesso: Código do restaurante
        query: Texto parcial digitado pelo usuário
    
    Returns:
        Lista de sugestões com place_name e coordinates
    """
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Proximity: prioriza resultados próximos ao restaurante
    proximity = (restaurante.latitude, restaurante.longitude) if restaurante.latitude else None
    
    sugestoes = autocomplete_address(query, proximity)
    
    return {"sugestoes": sugestoes}


# ==================== BAIRROS DE ENTREGA ====================
@router.get("/{codigo_acesso}/bairros", response_model=List[site_schemas.BairroEntregaPublic])
def get_bairros(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna bairros atendidos pelo restaurante"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    bairros = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.restaurante_id == restaurante.id,
        models.BairroEntrega.ativo == True
    ).order_by(models.BairroEntrega.nome).all()

    return bairros


@router.get("/{codigo_acesso}/bairro/{nome_bairro}")
def get_bairro_por_nome(
    codigo_acesso: str,
    nome_bairro: str,
    db: Session = Depends(database.get_db)
):
    """Busca bairro por nome para calcular taxa"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    bairro = db.query(models.BairroEntrega).filter(
        models.BairroEntrega.restaurante_id == restaurante.id,
        models.BairroEntrega.nome.ilike(f"%{nome_bairro}%"),
        models.BairroEntrega.ativo == True
    ).first()

    if not bairro:
        return {"encontrado": False, "mensagem": "Bairro não atendido"}

    return {
        "encontrado": True,
        "bairro": bairro.nome,
        "taxa_entrega": bairro.taxa_entrega,
        "tempo_estimado_min": bairro.tempo_estimado_min
    }


# ==================== SABORES (PIZZA) ====================
@router.get("/{codigo_acesso}/produto/{produto_id}/sabores")
def get_sabores_disponiveis(
    codigo_acesso: str,
    produto_id: int,
    db: Session = Depends(database.get_db)
):
    """Retorna produtos da mesma categoria como opções de sabor"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    produto = db.query(models.Produto).filter(
        models.Produto.id == produto_id,
        models.Produto.restaurante_id == restaurante.id
    ).first()

    if not produto or not produto.categoria_id:
        return {"sabores": []}

    # Busca todos os produtos da mesma categoria (exceto o próprio)
    sabores = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante.id,
        models.Produto.categoria_id == produto.categoria_id,
        models.Produto.disponivel == True
    ).order_by(models.Produto.nome).all()

    return {
        "sabores": [
            {
                "id": s.id,
                "nome": s.nome,
                "descricao": s.descricao,
                "preco": s.preco,
                "imagem_url": s.imagem_url
            }
            for s in sabores
        ]
    }


# ==================== COMBOS ====================
@router.get("/{codigo_acesso}/combos", response_model=List[site_schemas.ComboPublic])
def get_combos(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna combos ativos do restaurante"""
    from datetime import datetime as dt

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper(),
        models.Restaurante.ativo == True
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    agora = dt.utcnow()

    combos = db.query(models.Combo).filter(
        models.Combo.restaurante_id == restaurante.id,
        models.Combo.ativo == True,
        (models.Combo.data_inicio == None) | (models.Combo.data_inicio <= agora),
        (models.Combo.data_fim == None) | (models.Combo.data_fim >= agora)
    ).order_by(models.Combo.ordem_exibicao).all()

    dia_atual = agora.weekday()  # 0=Monday...6=Sunday

    resultado = []
    for combo in combos:
        # Combos do dia só aparecem no dia correto
        if (combo.tipo_combo or "padrao") == "do_dia" and combo.dia_semana is not None:
            if combo.dia_semana != dia_atual:
                continue

        itens = db.query(models.ComboItem).filter(
            models.ComboItem.combo_id == combo.id
        ).all()

        itens_publicos = []
        for item in itens:
            produto = db.query(models.Produto).filter(
                models.Produto.id == item.produto_id
            ).first()
            if produto:
                itens_publicos.append({
                    "produto_id": produto.id,
                    "produto_nome": produto.nome,
                    "quantidade": item.quantidade,
                    "produto_imagem_url": produto.imagem_url
                })

        resultado.append({
            "id": combo.id,
            "nome": combo.nome,
            "descricao": combo.descricao,
            "preco_combo": combo.preco_combo,
            "preco_original": combo.preco_original,
            "imagem_url": combo.imagem_url,
            "ordem_exibicao": combo.ordem_exibicao or 0,
            "tipo_combo": combo.tipo_combo or "padrao",
            "dia_semana": combo.dia_semana,
            "quantidade_pessoas": combo.quantidade_pessoas,
            "itens": itens_publicos
        })

    return resultado


# ==================== TRACKING DE PEDIDO ====================
@router.get("/{codigo_acesso}/pedido/{pedido_id}/tracking")
def get_pedido_tracking(
    codigo_acesso: str,
    pedido_id: int,
    db: Session = Depends(database.get_db)
):
    """Retorna status do pedido para acompanhamento pelo cliente"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == restaurante.id
    ).first()

    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    # Busca motoboy se despachado
    motoboy_info = None
    if pedido.motoboy_id:
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == pedido.motoboy_id
        ).first()
        if motoboy:
            gps = db.query(models.GPSMotoboy).filter(
                models.GPSMotoboy.motoboy_id == motoboy.id
            ).order_by(models.GPSMotoboy.data_hora.desc()).first()
            motoboy_info = {
                "nome": motoboy.nome,
                "latitude": gps.latitude if gps else None,
                "longitude": gps.longitude if gps else None,
            }

    return {
        "id": pedido.id,
        "comanda": pedido.comanda,
        "status": pedido.status,
        "tipo_entrega": pedido.tipo_entrega,
        "endereco_entrega": pedido.endereco_entrega,
        "latitude_entrega": pedido.latitude_entrega,
        "longitude_entrega": pedido.longitude_entrega,
        "valor_total": pedido.valor_total,
        "data_criacao": pedido.data_criacao.isoformat() if pedido.data_criacao else None,
        "tempo_estimado": pedido.tempo_estimado,
        "motoboy": motoboy_info,
        "carrinho_json": pedido.carrinho_json,
    }


# ==================== FIDELIDADE ====================
@router.get("/{codigo_acesso}/fidelidade/pontos/{cliente_id}", response_model=site_schemas.PontosFidelidadePublic)
def get_pontos_fidelidade(
    codigo_acesso: str,
    cliente_id: int,
    db: Session = Depends(database.get_db)
):
    """Retorna saldo de pontos de fidelidade do cliente"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    pontos = db.query(models.PontosFidelidade).filter(
        models.PontosFidelidade.cliente_id == cliente_id,
        models.PontosFidelidade.restaurante_id == restaurante.id
    ).first()

    if not pontos:
        # Cria registro se não existe
        pontos = models.PontosFidelidade(
            cliente_id=cliente_id,
            restaurante_id=restaurante.id,
            pontos_total=0,
            pontos_disponiveis=0
        )
        db.add(pontos)
        db.commit()
        db.refresh(pontos)

    return pontos


@router.get("/{codigo_acesso}/fidelidade/premios", response_model=List[site_schemas.PremioFidelidadePublic])
def get_premios_fidelidade(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna prêmios disponíveis para resgate"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    premios = db.query(models.PremioFidelidade).filter(
        models.PremioFidelidade.restaurante_id == restaurante.id,
        models.PremioFidelidade.ativo == True
    ).order_by(models.PremioFidelidade.ordem_exibicao).all()

    return premios


@router.post("/{codigo_acesso}/fidelidade/resgatar/{cliente_id}", response_model=site_schemas.ResgatePremioResponse)
def resgatar_premio(
    codigo_acesso: str,
    cliente_id: int,
    resgate: site_schemas.ResgatePremioRequest,
    db: Session = Depends(database.get_db)
):
    """Resgata um prêmio usando pontos de fidelidade"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Busca prêmio
    premio = db.query(models.PremioFidelidade).filter(
        models.PremioFidelidade.id == resgate.premio_id,
        models.PremioFidelidade.restaurante_id == restaurante.id,
        models.PremioFidelidade.ativo == True
    ).first()

    if not premio:
        raise HTTPException(status_code=404, detail="Prêmio não encontrado")

    # Busca pontos do cliente
    pontos = db.query(models.PontosFidelidade).filter(
        models.PontosFidelidade.cliente_id == cliente_id,
        models.PontosFidelidade.restaurante_id == restaurante.id
    ).first()

    if not pontos or pontos.pontos_disponiveis < premio.custo_pontos:
        return {
            "sucesso": False,
            "mensagem": "Pontos insuficientes",
            "pontos_restantes": pontos.pontos_disponiveis if pontos else 0
        }

    # Deduz pontos
    pontos.pontos_disponiveis -= premio.custo_pontos

    # Registra transação
    transacao = models.TransacaoFidelidade(
        cliente_id=cliente_id,
        restaurante_id=restaurante.id,
        tipo="resgatado",
        pontos=premio.custo_pontos,
        descricao=f"Resgate do prêmio: {premio.nome}"
    )
    db.add(transacao)
    db.commit()

    return {
        "sucesso": True,
        "mensagem": f"Prêmio '{premio.nome}' resgatado com sucesso!",
        "pontos_restantes": pontos.pontos_disponiveis
    }


# ==================== PROMOÇÕES ====================
@router.get("/{codigo_acesso}/promocoes", response_model=List[site_schemas.PromocaoPublic])
def get_promocoes(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna promoções ativas do restaurante"""
    from datetime import datetime

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    agora = datetime.utcnow()

    promocoes = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante.id,
        models.Promocao.ativo == True,
        (models.Promocao.data_inicio == None) | (models.Promocao.data_inicio <= agora),
        (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora)
    ).all()

    return promocoes


@router.post("/{codigo_acesso}/validar-cupom", response_model=site_schemas.ValidarCupomResponse)
def validar_cupom(
    codigo_acesso: str,
    validacao: site_schemas.ValidarCupomRequest,
    db: Session = Depends(database.get_db)
):
    """Valida um código de cupom e calcula desconto"""
    from datetime import datetime

    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    agora = datetime.utcnow()

    promocao = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante.id,
        models.Promocao.codigo_cupom == validacao.codigo_cupom.upper(),
        models.Promocao.ativo == True,
        (models.Promocao.data_inicio == None) | (models.Promocao.data_inicio <= agora),
        (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora)
    ).first()

    if not promocao:
        return {
            "valido": False,
            "desconto_aplicado": 0,
            "mensagem": "Cupom inválido ou expirado"
        }

    # Verifica limite de usos
    if promocao.uso_limitado and promocao.usos_realizados >= promocao.limite_usos:
        return {
            "valido": False,
            "desconto_aplicado": 0,
            "mensagem": "Cupom esgotado"
        }

    # Verifica valor mínimo
    if validacao.valor_pedido < promocao.valor_pedido_minimo:
        return {
            "valido": False,
            "desconto_aplicado": 0,
            "mensagem": f"Valor mínimo do pedido: R$ {promocao.valor_pedido_minimo:.2f}"
        }

    # Calcula desconto
    if promocao.tipo_desconto == "percentual":
        desconto = validacao.valor_pedido * (promocao.valor_desconto / 100)
        if promocao.desconto_maximo:
            desconto = min(desconto, promocao.desconto_maximo)
    else:
        desconto = promocao.valor_desconto

    return {
        "valido": True,
        "desconto_aplicado": round(desconto, 2),
        "mensagem": f"Cupom '{promocao.nome}' aplicado! Desconto: R$ {desconto:.2f}"
    }