"""
Mapper: pedido iFood → formato interno Derekh Food.
Converte a estrutura do iFood Merchant API para os campos do model Pedido.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def ifood_order_to_pedido(ifood_order: dict, restaurante_id: int) -> Optional[Dict[str, Any]]:
    """Converte um pedido do iFood para o formato interno do Derekh Food.

    Estrutura iFood típica:
    {
        "id": "uuid",
        "displayId": "A1B2",
        "orderType": "DELIVERY" | "TAKEOUT",
        "customer": {"name": "...", "phone": {"number": "..."}},
        "deliveryAddress": {"formattedAddress": "...", "coordinates": {"latitude": ..., "longitude": ...}},
        "items": [{"name": "...", "quantity": 1, "unitPrice": 10.0, "totalPrice": 10.0, "subItems": [...]}],
        "totalPrice": 50.0,
        "subTotal": 45.0,
        "deliveryFee": {"value": 5.0},
        "payments": {"methods": [{"method": "CREDIT", "value": 50.0}]},
        "createdAt": "2026-03-15T21:30:00Z",
    }
    """
    if not ifood_order:
        return None

    try:
        # Cliente
        customer = ifood_order.get("customer", {})
        cliente_nome = customer.get("name", "Cliente iFood")
        phone = customer.get("phone", {})
        cliente_telefone = phone.get("number") if isinstance(phone, dict) else str(phone) if phone else None

        # Tipo de entrega
        order_type = ifood_order.get("orderType", "DELIVERY")
        tipo_entrega = "retirada" if order_type == "TAKEOUT" else "entrega"

        # Endereço
        address = ifood_order.get("deliveryAddress", {})
        endereco_entrega = address.get("formattedAddress") or address.get("streetName", "")
        if address.get("streetNumber"):
            endereco_entrega += f", {address['streetNumber']}"
        if address.get("complement"):
            endereco_entrega += f" - {address['complement']}"
        if address.get("neighborhood"):
            endereco_entrega += f", {address['neighborhood']}"
        if address.get("city"):
            endereco_entrega += f" - {address['city']}"

        coords = address.get("coordinates", {})
        latitude = coords.get("latitude")
        longitude = coords.get("longitude")

        # Itens do pedido
        items = ifood_order.get("items", [])
        carrinho_json = []
        itens_texto_parts = []

        for item in items:
            nome = item.get("name", "Item")
            qtd = item.get("quantity", 1)
            preco_unitario = item.get("unitPrice", 0)
            preco_total = item.get("totalPrice", preco_unitario * qtd)

            # Sub-items (adicionais, variações)
            sub_items = item.get("subItems", [])
            observacoes_parts = []
            variacoes = []

            for sub in sub_items:
                sub_nome = sub.get("name", "")
                sub_preco = sub.get("price", 0) or sub.get("unitPrice", 0)
                sub_qtd = sub.get("quantity", 1)
                if sub_nome:
                    variacoes.append({
                        "nome": sub_nome,
                        "preco": sub_preco,
                        "quantidade": sub_qtd,
                    })

            # Observações do item
            if item.get("observations"):
                observacoes_parts.append(item["observations"])

            cart_item = {
                "nome": nome,
                "quantidade": qtd,
                "preco": preco_unitario,
                "preco_total": preco_total,
                "observacoes": " | ".join(observacoes_parts) if observacoes_parts else None,
                "variacoes": variacoes if variacoes else None,
            }
            carrinho_json.append(cart_item)
            itens_texto_parts.append(f"{qtd}x {nome}")

        # Valores — suportar ambos formatos (totalPrice no root OU total.orderAmount)
        total_obj = ifood_order.get("total", {}) or {}
        valor_total = ifood_order.get("totalPrice") or total_obj.get("orderAmount") or 0
        valor_subtotal = ifood_order.get("subTotal") or total_obj.get("subTotal") or valor_total
        delivery_fee = ifood_order.get("deliveryFee", {})
        if isinstance(delivery_fee, dict):
            valor_taxa = delivery_fee.get("value", 0) or 0
        else:
            valor_taxa = float(delivery_fee or 0)
        if not valor_taxa:
            valor_taxa = total_obj.get("deliveryFee", 0) or 0
        benefits = ifood_order.get("benefits", {})
        valor_desconto = benefits.get("value", 0) if isinstance(benefits, dict) else (total_obj.get("benefits", 0) or 0)

        # Pagamento
        payments = ifood_order.get("payments", {})
        methods = payments.get("methods", []) if isinstance(payments, dict) else []
        forma_pagamento = "Online"
        if methods:
            method = methods[0].get("method", "ONLINE")
            method_map = {
                "CREDIT": "Cartão Crédito",
                "DEBIT": "Cartão Débito",
                "MEAL_VOUCHER": "Vale Refeição",
                "CASH": "Dinheiro",
                "PIX": "PIX",
                "ONLINE": "Online",
            }
            forma_pagamento = method_map.get(method, method)

        # Display ID
        display_id = ifood_order.get("displayId", "")
        marketplace_display_id = f"iFood #{display_id}" if display_id else None

        # Observações gerais
        observacoes = ifood_order.get("extraInfo") or ifood_order.get("observations")

        return {
            "cliente_nome": cliente_nome,
            "cliente_telefone": cliente_telefone,
            "tipo": "delivery",
            "tipo_entrega": tipo_entrega,
            "endereco_entrega": endereco_entrega if tipo_entrega == "entrega" else None,
            "latitude_entrega": latitude,
            "longitude_entrega": longitude,
            "carrinho_json": carrinho_json,
            "itens_texto": ", ".join(itens_texto_parts),
            "observacoes": observacoes,
            "valor_total": valor_total,
            "valor_subtotal": valor_subtotal,
            "valor_taxa_entrega": valor_taxa,
            "valor_desconto": valor_desconto,
            "forma_pagamento": forma_pagamento,
            "marketplace_display_id": marketplace_display_id,
            "pagamento_online": forma_pagamento != "Dinheiro",
        }

    except Exception as e:
        logger.error(f"Erro ao mapear pedido iFood: {e}", exc_info=True)
        return None
