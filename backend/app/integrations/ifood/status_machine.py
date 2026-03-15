"""
Máquina de estados: iFood ↔ Derekh Food.

Mapeamento bidirecional de status entre os dois sistemas.

iFood Status Flow:
  PLACED → CONFIRMED → READY_TO_PICKUP → DISPATCHED → CONCLUDED
                                                    → CANCELLED

Derekh Status Flow:
  pendente → em_preparo → pronto → em_entrega → entregue
                                              → cancelado
"""

# Status Derekh → Ação iFood
DEREKH_TO_IFOOD = {
    "em_preparo": "CONFIRM",          # Admin aceita pedido
    "pronto": "READY_TO_PICKUP",      # Pedido pronto para retirar
    "em_entrega": "DISPATCH",         # Saiu para entrega
    "cancelado": "CANCEL",            # Admin cancela
    # "entregue" não tem ação — iFood conclui automaticamente
}

# Evento iFood → Status Derekh
IFOOD_TO_DEREKH = {
    "PLACED": "pendente",             # Novo pedido
    "PLC": "pendente",                # Alias
    "CONFIRMED": "em_preparo",        # Confirmado no iFood
    "CFM": "em_preparo",              # Alias
    "READY_TO_PICKUP": "pronto",      # Pronto no iFood
    "RTP": "pronto",                  # Alias
    "DISPATCHED": "em_entrega",       # Despachado no iFood
    "DSP": "em_entrega",              # Alias
    "CONCLUDED": "entregue",          # Concluído no iFood
    "CON": "entregue",                # Alias
    "CANCELLED": "cancelado",         # Cancelado no iFood
    "CAN": "cancelado",              # Alias
    "CANCELLATION_REQUESTED": "cancelado",
}

# Eventos iFood que representam novo pedido
IFOOD_NEW_ORDER_EVENTS = {"PLACED", "PLC"}

# Eventos iFood que representam cancelamento
IFOOD_CANCEL_EVENTS = {"CANCELLED", "CAN", "CANCELLATION_REQUESTED"}
