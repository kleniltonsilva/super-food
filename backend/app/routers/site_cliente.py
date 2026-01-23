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
from utils.mapbox_api import autocomplete_address, check_coverage_zone

router = APIRouter(prefix="/site", tags=["Site do Cliente"])


@router.get("/{codigo_acesso}", response_model=site_schemas.SiteInfoPublic)
def get_site_info(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """
    Retorna informações públicas do site do restaurante
    
    Args:
        codigo_acesso: Código único do restaurante (8 caracteres)
    
    Returns:
        Dados do restaurante, site config, horários, etc
    """
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
    
    return {
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


@router.get("/{codigo_acesso}/categorias", response_model=List[site_schemas.CategoriaPublic])
def get_categorias(
    codigo_acesso: str,
    db: Session = Depends(database.get_db)
):
    """Retorna categorias do menu"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante.id,
        models.CategoriaMenu.ativo == True
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()
    
    return categorias


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
                    "estoque_disponivel": v.estoque_disponivel
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
            "estoque_disponivel": v.estoque_disponivel
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