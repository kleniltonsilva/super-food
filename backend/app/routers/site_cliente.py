# backend/app/routers/site_cliente.py

"""
Router Site do Cliente - APIs públicas para o site
Endpoints para buscar cardápio, validar endereços, etc
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import json
import os

from .. import models, database
from ..schemas import site_schemas
from ..cache import cache_get, cache_set
from utils.mapbox_api import autocomplete_address, check_coverage_zone, _cache_key_dist
from .auth_cliente import get_cliente_atual, get_cliente_opcional


def _detectar_pais_restaurante(restaurante, db) -> str:
    """Detecta o país do restaurante via reverse geocoding direto. Auto-corrige se pais='BR' mas coordenadas fora do Brasil."""
    pais = getattr(restaurante, 'pais', None) or "BR"
    if pais == "BR" and restaurante.latitude and restaurante.longitude:
        lat, lng = restaurante.latitude, restaurante.longitude
        if not (-35 <= lat <= 6 and -75 <= lng <= -34):
            try:
                import requests as req
                token = os.getenv("MAPBOX_TOKEN")
                if token:
                    url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
                    params = {"access_token": token, "types": "country", "language": "pt"}
                    resp = req.get(url, params=params, timeout=10)
                    if resp.status_code == 200:
                        for feat in resp.json().get("features", []):
                            if "country" in feat.get("place_type", []):
                                code = (feat.get("properties", {}).get("short_code") or "").upper()
                                if code:
                                    pais = code
                                    try:
                                        restaurante.pais = pais
                                        db.commit()
                                    except Exception:
                                        pass
                                    break
            except Exception:
                pais = None  # Não filtrar se falhar
    return pais


def _check_pix_online(db, restaurante_id: int) -> bool:
    """Verifica se Pix online está ativo. Retorna False se tabela não existir."""
    try:
        return bool(db.query(models.PixConfig).filter(
            models.PixConfig.restaurante_id == restaurante_id,
            models.PixConfig.ativo == True,
        ).first())
    except Exception:
        return False


def _calcular_status_aberto(config_rest):
    """Calcula se o restaurante está aberto considerando horários por dia."""
    if not config_rest or config_rest.status_atual != 'aberto':
        return False

    agora = datetime.now()
    dia_semana_map = {0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sabado', 6: 'domingo'}
    dia_atual = dia_semana_map[agora.weekday()]

    if config_rest.horarios_por_dia:
        try:
            horarios = json.loads(config_rest.horarios_por_dia)
        except (json.JSONDecodeError, TypeError):
            horarios = {}
        dia_config = horarios.get(dia_atual, {})
        if not dia_config.get('ativo', False):
            return False
        abertura = dia_config.get('abertura', '')
        fechamento = dia_config.get('fechamento', '')
    else:
        # Fallback: horário único
        if config_rest.dias_semana_abertos:
            dias = config_rest.dias_semana_abertos.split(',')
            if dia_atual not in dias:
                return False
        abertura = config_rest.horario_abertura or '00:00'
        fechamento = config_rest.horario_fechamento or '23:59'

    if abertura and fechamento:
        hora_atual = agora.strftime('%H:%M')
        return abertura <= hora_atual <= fechamento
    return True


def _get_horario_hoje(config_rest):
    """Retorna abertura/fechamento do dia atual."""
    if not config_rest:
        return "18:00", "23:00"

    agora = datetime.now()
    dia_semana_map = {0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sabado', 6: 'domingo'}
    dia_atual = dia_semana_map[agora.weekday()]

    if config_rest.horarios_por_dia:
        try:
            horarios = json.loads(config_rest.horarios_por_dia)
        except (json.JSONDecodeError, TypeError):
            horarios = {}
        dia_config = horarios.get(dia_atual, {})
        return dia_config.get('abertura', ''), dia_config.get('fechamento', '')

    return config_rest.horario_abertura or '18:00', config_rest.horario_fechamento or '23:00'


def _verificar_controle_pedidos(config_rest, db):
    """Verifica e auto-reativa controle de pedidos se expirou."""
    if not config_rest:
        return True, True, None

    pedidos_ativos = config_rest.pedidos_online_ativos if config_rest.pedidos_online_ativos is not None else True
    entregas_ativas = config_rest.entregas_ativas if config_rest.entregas_ativas is not None else True
    motivo = config_rest.controle_pedidos_motivo

    # Auto-reativar se controle_pedidos_ate expirou
    if config_rest.controle_pedidos_ate and config_rest.controle_pedidos_ate <= datetime.now():
        config_rest.pedidos_online_ativos = True
        config_rest.entregas_ativas = True
        config_rest.controle_pedidos_motivo = None
        config_rest.controle_pedidos_ate = None
        db.commit()
        pedidos_ativos = True
        entregas_ativas = True
        motivo = None

    return pedidos_ativos, entregas_ativas, motivo

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
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    # Restaurante suspenso por billing: retorna info mínima com flag
    if not restaurante.ativo and restaurante.billing_status in ("suspended_billing", "canceled_billing"):
        return {
            "restaurante_id": restaurante.id,
            "codigo_acesso": restaurante.codigo_acesso,
            "nome_fantasia": restaurante.nome_fantasia,
            "billing_suspenso": True,
            "status_aberto": False,
            "pedidos_online_ativos": False,
        }

    if not restaurante.ativo:
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
    
    # Calcular status e horários usando funções helper
    horario_abertura, horario_fechamento = _get_horario_hoje(config_rest)
    is_demo = bool(restaurante.email and restaurante.email.endswith("@superfood.test"))
    status_aberto = True if is_demo else _calcular_status_aberto(config_rest)
    pedidos_online_ativos, entregas_ativas, controle_motivo = _verificar_controle_pedidos(config_rest, db)

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
        "status_aberto": status_aberto,
        "horario_abertura": horario_abertura,
        "horario_fechamento": horario_fechamento,
        "dias_semana_abertos": config_rest.dias_semana_abertos.split(',') if config_rest and config_rest.dias_semana_abertos else [],
        "modo_preco_pizza": config_rest.modo_preco_pizza if config_rest else "mais_caro",
        "ingredientes_adicionais_pizza": site_config.ingredientes_adicionais_pizza or [],
        "pedidos_online_ativos": pedidos_online_ativos,
        "entregas_ativas": entregas_ativas,
        "controle_pedidos_motivo": controle_motivo,
        "pix_online": _check_pix_online(db, restaurante.id),
        "is_demo": is_demo,
    }
    cache_set(cache_key, result, ttl_seconds=300)  # 5 min
    return result


@router.get("/{codigo_acesso}/pedido/{pedido_id}/pix-status")
def get_pix_status_pedido(
    codigo_acesso: str,
    pedido_id: int,
    db: Session = Depends(database.get_db)
):
    """Polling do status de pagamento Pix de um pedido"""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()
    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    pedido = db.query(models.Pedido).filter(
        models.Pedido.id == pedido_id,
        models.Pedido.restaurante_id == restaurante.id,
    ).first()
    if not pedido:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")

    cobranca = db.query(models.PixCobranca).filter(
        models.PixCobranca.pedido_id == pedido_id,
        models.PixCobranca.restaurante_id == restaurante.id,
    ).order_by(models.PixCobranca.criado_em.desc()).first()

    return {
        "pedido_id": pedido.id,
        "pedido_status": pedido.status,
        "pix_status": cobranca.status if cobranca else None,
        "pix_pago": cobranca.status == "COMPLETED" if cobranca else False,
        "pix_qr_code": cobranca.qr_code_imagem if cobranca else None,
        "pix_br_code": cobranca.br_code if cobranca else None,
        "pix_payment_link": cobranca.payment_link_url if cobranca else None,
        "pix_expira_em": cobranca.expira_em.isoformat() if cobranca and cobranca.expira_em else None,
    }


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
        "ingredientes": produto.ingredientes_json or [],
        "eh_pizza": produto.eh_pizza or False,
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
    
    # Demo bypass: sempre retornar dentro_zona para restaurantes demo
    is_demo = bool(restaurante.email and restaurante.email.endswith("@superfood.test"))
    if is_demo:
        return {
            "dentro_zona": True,
            "distancia_km": 2.5,
            "tempo_estimado_min": 35,
            "taxa_entrega": 5.00,
            "mensagem": "Entrega disponível",
        }

    if not restaurante.latitude or not restaurante.longitude:
        raise HTTPException(status_code=500, detail="Coordenadas do restaurante não configuradas")

    # Se enviou texto, geocodifica
    if validacao.endereco_texto and not (validacao.latitude and validacao.longitude):
        from utils.mapbox_api import geocode_address
        coords = geocode_address(validacao.endereco_texto)
        if not coords:
            raise HTTPException(status_code=400, detail="Endereço não encontrado")
        validacao.latitude, validacao.longitude = coords

    # Cache: verificar distância/taxa cacheada (30 dias TTL)
    dist_cache_key = _cache_key_dist(restaurante.id, validacao.latitude, validacao.longitude)
    cached_dist = cache_get(dist_cache_key)
    if cached_dist:
        return {
            "dentro_zona": cached_dist["dentro_zona"],
            "distancia_km": cached_dist["distancia_km"],
            "tempo_estimado_min": site_config.tempo_entrega_estimado if site_config else 50,
            "taxa_entrega": cached_dist["taxa_entrega"],
            "mensagem": cached_dist.get("mensagem", ""),
        }

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

    taxa_entrega = round(taxa_entrega, 2)

    # Cache: salvar resultado (30 dias)
    cache_set(dist_cache_key, {
        "dentro_zona": resultado['dentro_zona'],
        "distancia_km": resultado['distancia_km'],
        "taxa_entrega": taxa_entrega,
        "mensagem": resultado['mensagem'],
    }, ttl_seconds=2592000)

    return {
        "dentro_zona": resultado['dentro_zona'],
        "distancia_km": resultado['distancia_km'],
        "tempo_estimado_min": site_config.tempo_entrega_estimado if site_config else 50,
        "taxa_entrega": taxa_entrega,
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
    
    pais = _detectar_pais_restaurante(restaurante, db)
    sugestoes = autocomplete_address(query, proximity, country=pais)

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
                "imagem_url": s.imagem_url,
                "ingredientes": s.ingredientes_json or []
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

    # Busca motoboy via relacionamento Entrega (Pedido não tem motoboy_id direto)
    motoboy_info = None
    if pedido.entrega and pedido.entrega.motoboy_id:
        motoboy = db.query(models.Motoboy).filter(
            models.Motoboy.id == pedido.entrega.motoboy_id
        ).first()
        if motoboy:
            # Usa lat/lng do próprio model Motoboy (atualizado pelo GPS hook)
            # fallback: última entrada na tabela GPS
            lat = motoboy.latitude_atual
            lng = motoboy.longitude_atual
            if lat is None or lng is None:
                gps = db.query(models.GPSMotoboy).filter(
                    models.GPSMotoboy.motoboy_id == motoboy.id
                ).order_by(models.GPSMotoboy.timestamp.desc()).first()
                if gps:
                    lat = gps.latitude
                    lng = gps.longitude
            motoboy_info = {
                "nome": motoboy.nome,
                "latitude": lat,
                "longitude": lng,
            }

    # Verifica config auto-aceitar para informar cliente sobre próximos pedidos
    config_rest = db.query(models.ConfigRestaurante).filter(
        models.ConfigRestaurante.restaurante_id == restaurante.id
    ).first()
    aceitar_auto = config_rest.aceitar_pedido_site_auto if config_rest else False

    # Verifica se este é o primeiro pedido concluído do cliente (para exibir aviso)
    primeiro_pedido_concluido = False
    status_concluido = pedido.status in ('entregue', 'finalizado')
    if aceitar_auto and status_concluido and pedido.cliente_id:
        qtd_anteriores = db.query(models.Pedido).filter(
            models.Pedido.cliente_id == pedido.cliente_id,
            models.Pedido.restaurante_id == restaurante.id,
            models.Pedido.status.in_(['entregue', 'finalizado']),
            models.Pedido.id != pedido.id
        ).count()
        # Se não há outros pedidos concluídos, este é o primeiro
        primeiro_pedido_concluido = (qtd_anteriores == 0)

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
        "aceitar_pedido_site_auto": aceitar_auto,
        "aviso_proximo_pedido_auto": primeiro_pedido_concluido,
        "historico_status": pedido.historico_status or [],
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
    cliente: Optional[models.Cliente] = Depends(get_cliente_opcional),
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

    # Verifica se é cupom exclusivo de outro cliente
    if promocao.cliente_id and (not cliente or promocao.cliente_id != cliente.id):
        return {
            "valido": False,
            "desconto_aplicado": 0,
            "mensagem": "Este cupom é exclusivo para outro cliente"
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


@router.get("/{codigo_acesso}/meus-cupons")
def listar_meus_cupons(
    codigo_acesso: str,
    cliente: models.Cliente = Depends(get_cliente_atual),
    db: Session = Depends(database.get_db)
):
    """Lista cupons exclusivos do cliente logado (ativos e não expirados)."""
    restaurante = db.query(models.Restaurante).filter(
        models.Restaurante.codigo_acesso == codigo_acesso.upper()
    ).first()

    if not restaurante:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")

    agora = datetime.utcnow()

    cupons = db.query(models.Promocao).filter(
        models.Promocao.restaurante_id == restaurante.id,
        models.Promocao.cliente_id == cliente.id,
        models.Promocao.ativo == True,
        (models.Promocao.data_fim == None) | (models.Promocao.data_fim >= agora),
    ).all()

    resultado = []
    for c in cupons:
        # Verificar se ainda tem usos disponíveis
        if c.uso_limitado and c.usos_realizados >= (c.limite_usos or 0):
            continue
        resultado.append({
            "id": c.id,
            "codigo_cupom": c.codigo_cupom,
            "tipo_desconto": c.tipo_desconto,
            "valor_desconto": c.valor_desconto,
            "tipo_cupom": c.tipo_cupom or "exclusivo",
            "data_fim": c.data_fim.isoformat() if c.data_fim else None,
            "nome": c.nome,
        })

    return resultado