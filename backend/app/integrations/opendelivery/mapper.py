"""
Mapper: pedido Open Delivery (ABRASEL) → formato interno Derekh Food.
Suporta 99Food, Keeta, Rappi e outros que seguem o padrão.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Nomes amigáveis dos marketplaces
MARKETPLACE_DISPLAY_NAMES = {
    "99food": "99Food",
    "rappi": "Rappi",
    "keeta": "Keeta",
    "opendelivery": "Marketplace",
}


def opendelivery_order_to_pedido(
    od_order: dict,
    restaurante_id: int,
    marketplace_name: str = "opendelivery",
) -> Optional[Dict[str, Any]]:
    """Converte pedido Open Delivery para formato interno Derekh.

    Estrutura Open Delivery típica:
    {
        "id": "uuid",
        "displayId": "ABC123",
        "type": "DELIVERY" | "TAKEOUT",
        "customer": {"name": "...", "phone": "..."},
        "delivery": {"address": {"formattedAddress": "...", "lat": ..., "lng": ...}},
        "items": [{"name": "...", "quantity": 1, "unitPrice": 10.0, "totalPrice": 10.0, "options": [...]}],
        "total": {"orderAmount": 50.0, "subTotal": 45.0, "deliveryFee": 5.0, "discount": 0},
        "payments": [{"type": "CREDIT_CARD", "value": 50.0, "prepaid": true}],
    }
    """
    if not od_order:
        return None

    try:
        # Cliente (spec usa "consumer", fallback "customer")
        customer = od_order.get("consumer") or od_order.get("customer", {})
        cliente_nome = customer.get("name", f"Cliente {marketplace_name}")
        cliente_telefone = customer.get("phone") or customer.get("phoneNumber")

        # Tipo de entrega
        order_type = od_order.get("type", "DELIVERY")
        tipo_entrega = "retirada" if order_type in ("TAKEOUT", "PICKUP") else "entrega"

        # Endereço
        delivery = od_order.get("delivery", {})
        address = delivery.get("address", {})
        endereco_entrega = address.get("formattedAddress") or address.get("streetName", "")
        if address.get("streetNumber"):
            endereco_entrega += f", {address['streetNumber']}"
        if address.get("complement"):
            endereco_entrega += f" - {address['complement']}"
        if address.get("neighborhood"):
            endereco_entrega += f", {address['neighborhood']}"
        if address.get("city"):
            endereco_entrega += f" - {address['city']}"

        latitude = address.get("lat") or address.get("latitude")
        longitude = address.get("lng") or address.get("longitude")

        # Itens
        items = od_order.get("items", [])
        carrinho_json = []
        itens_texto_parts = []

        for item in items:
            nome = item.get("name", "Item")
            qtd = item.get("quantity", 1)
            preco_unitario = item.get("unitPrice", 0)
            preco_total = item.get("totalPrice", preco_unitario * qtd)

            # Opções/adicionais
            options = item.get("options", []) or item.get("subItems", [])
            variacoes = []
            for opt in options:
                opt_nome = opt.get("name", "")
                opt_preco = opt.get("price", 0) or opt.get("unitPrice", 0)
                opt_qtd = opt.get("quantity", 1)
                if opt_nome:
                    variacoes.append({
                        "nome": opt_nome,
                        "preco": opt_preco,
                        "quantidade": opt_qtd,
                    })

            observacoes = item.get("observations") or item.get("notes")

            cart_item = {
                "nome": nome,
                "quantidade": qtd,
                "preco": preco_unitario,
                "preco_total": preco_total,
                "observacoes": observacoes,
                "variacoes": variacoes if variacoes else None,
            }
            carrinho_json.append(cart_item)
            itens_texto_parts.append(f"{qtd}x {nome}")

        # Valores
        total = od_order.get("total", {})
        valor_total = total.get("orderAmount", 0) or od_order.get("totalPrice", 0)
        valor_subtotal = total.get("subTotal", valor_total) or valor_total
        valor_taxa = total.get("deliveryFee", 0) or 0
        valor_desconto = total.get("discount", 0) or 0

        # Pagamento (spec usa "payment" singular, fallback "payments" plural)
        payments = od_order.get("payments") or ([od_order["payment"]] if od_order.get("payment") else [])
        forma_pagamento = "Online"
        pagamento_online = True
        if payments:
            pay = payments[0] if isinstance(payments, list) else payments
            pay_type = pay.get("type", "ONLINE") if isinstance(pay, dict) else "ONLINE"
            type_map = {
                "CREDIT_CARD": "Cartão Crédito",
                "DEBIT_CARD": "Cartão Débito",
                "MEAL_VOUCHER": "Vale Refeição",
                "CASH": "Dinheiro",
                "PIX": "PIX",
                "ONLINE": "Online",
            }
            forma_pagamento = type_map.get(pay_type, pay_type)
            pagamento_online = pay.get("prepaid", True) if isinstance(pay, dict) else True

        # Display ID (spec usa "orderDisplayId", fallback "displayId"/"shortId")
        display_id = od_order.get("orderDisplayId") or od_order.get("displayId") or od_order.get("shortId", "")
        display_name = MARKETPLACE_DISPLAY_NAMES.get(marketplace_name, marketplace_name.title())
        marketplace_display_id = f"{display_name} #{display_id}" if display_id else None

        # Observações
        observacoes = od_order.get("observations") or od_order.get("notes")

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
            "pagamento_online": pagamento_online,
        }

    except Exception as e:
        logger.error(f"Erro ao mapear pedido Open Delivery ({marketplace_name}): {e}", exc_info=True)
        return None
