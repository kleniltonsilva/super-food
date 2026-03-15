"""
Sincronização de catálogo Derekh Food → iFood Catalog API v2.
Envia categorias e produtos para o iFood.
"""

import logging
from typing import List, Dict, Any

import httpx

from database import models

logger = logging.getLogger(__name__)

IFOOD_CATALOG_BASE = "https://merchant-api.ifood.com.br/catalog/v2.0"


async def sync_catalog_to_ifood(
    db,
    restaurante_id: int,
    merchant_id: str,
    access_token: str,
) -> Dict[str, Any]:
    """Sincroniza o cardápio do restaurante para o iFood.

    Returns:
        dict com resultado: {"success": bool, "categories_synced": int, "products_synced": int, "errors": []}
    """
    result = {"success": True, "categories_synced": 0, "products_synced": 0, "errors": []}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Buscar categorias ativas do restaurante
    categorias = db.query(models.CategoriaMenu).filter(
        models.CategoriaMenu.restaurante_id == restaurante_id,
        models.CategoriaMenu.ativo == True,
    ).order_by(models.CategoriaMenu.ordem_exibicao).all()

    # Buscar produtos disponíveis
    produtos = db.query(models.Produto).filter(
        models.Produto.restaurante_id == restaurante_id,
        models.Produto.disponivel == True,
    ).all()

    async with httpx.AsyncClient(timeout=30) as http:
        # Sincronizar categorias
        for cat in categorias:
            ifood_cat = {
                "externalCode": str(cat.id),
                "name": cat.nome,
                "description": cat.descricao or "",
                "order": cat.ordem_exibicao or 0,
                "status": "AVAILABLE",
            }

            try:
                resp = await http.put(
                    f"{IFOOD_CATALOG_BASE}/merchants/{merchant_id}/categories/{cat.id}",
                    headers=headers,
                    json=ifood_cat,
                )
                if resp.status_code in (200, 201, 204):
                    result["categories_synced"] += 1
                else:
                    result["errors"].append(f"Categoria {cat.nome}: {resp.status_code} - {resp.text}")
            except Exception as e:
                result["errors"].append(f"Categoria {cat.nome}: {e}")

        # Sincronizar produtos
        for prod in produtos:
            # Buscar variações
            variacoes = db.query(models.VariacaoProduto).filter(
                models.VariacaoProduto.produto_id == prod.id,
                models.VariacaoProduto.ativo == True,
            ).all()

            # Mapear variações para option groups do iFood
            option_groups = []
            grupos_variacao = {}
            for var in variacoes:
                tipo = var.tipo_variacao
                grupos_variacao.setdefault(tipo, []).append(var)

            for tipo, vars_list in grupos_variacao.items():
                options = []
                for v in vars_list:
                    options.append({
                        "externalCode": str(v.id),
                        "name": v.nome,
                        "description": v.descricao or "",
                        "price": {"value": int((v.preco_adicional or 0) * 100), "currency": "BRL"},
                        "status": "AVAILABLE" if v.estoque_disponivel else "UNAVAILABLE",
                        "order": v.ordem or 0,
                    })
                option_groups.append({
                    "externalCode": f"og_{prod.id}_{tipo}",
                    "name": tipo.replace("_", " ").title(),
                    "minQuantity": 1 if tipo == "tamanho" else 0,
                    "maxQuantity": 1 if tipo == "tamanho" else len(vars_list),
                    "options": options,
                })

            ifood_product = {
                "externalCode": str(prod.id),
                "name": prod.nome,
                "description": prod.descricao or "",
                "categoryExternalCode": str(prod.categoria_id) if prod.categoria_id else None,
                "price": {
                    "value": int(prod.preco * 100),
                    "originalValue": int((prod.preco_promocional or prod.preco) * 100) if prod.promocao else None,
                    "currency": "BRL",
                },
                "status": "AVAILABLE" if prod.disponivel else "UNAVAILABLE",
                "order": prod.ordem_exibicao or 0,
                "imagePath": prod.imagem_url,
                "optionGroups": option_groups if option_groups else None,
            }

            # Remover campos None
            ifood_product = {k: v for k, v in ifood_product.items() if v is not None}

            try:
                resp = await http.put(
                    f"{IFOOD_CATALOG_BASE}/merchants/{merchant_id}/products/{prod.id}",
                    headers=headers,
                    json=ifood_product,
                )
                if resp.status_code in (200, 201, 204):
                    result["products_synced"] += 1
                else:
                    result["errors"].append(f"Produto {prod.nome}: {resp.status_code} - {resp.text}")
            except Exception as e:
                result["errors"].append(f"Produto {prod.nome}: {e}")

    if result["errors"]:
        result["success"] = False

    logger.info(
        f"Catalog sync rest:{restaurante_id}: "
        f"{result['categories_synced']} cats, "
        f"{result['products_synced']} prods, "
        f"{len(result['errors'])} erros"
    )

    return result
