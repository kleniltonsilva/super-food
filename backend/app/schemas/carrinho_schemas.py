"""
Schemas Pydantic para Carrinho de Compras
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# ==================== ADICIONAR ITEM ====================

class AdicionarItemRequest(BaseModel):
    """Request para adicionar item ao carrinho"""
    produto_id: int = Field(..., description="ID do produto")
    variacoes_ids: List[int] = Field(
        default=[],
        description="IDs das variações selecionadas"
    )
    quantidade: int = Field(
        1,
        ge=1,
        description="Quantidade do produto"
    )
    observacoes: Optional[str] = Field(
        None,
        max_length=500,
        description="Observações do cliente"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "produto_id": 5,
                "variacoes_ids": [12, 25, 34],
                "quantidade": 2,
                "observacoes": "Sem cebola, por favor"
            }
        }


# ==================== CARRINHO RESPONSE ====================

class CarrinhoResponse(BaseModel):
    """Response do carrinho completo"""
    id: Optional[int] = None
    sessao_id: str
    itens: List[dict] = []
    quantidade_itens: int
    valor_subtotal: float
    valor_taxa_entrega: float
    valor_desconto: float
    valor_total: float

    class Config:
        json_schema_extra = {
            "example": {
                "id": 123,
                "sessao_id": "abc-123-def-456",
                "itens": [
                    {
                        "produto_id": 5,
                        "nome": "Pizza Grande Calabresa",
                        "imagem_url": "/static/uploads/pizza.jpg",
                        "variacoes": [
                            {"id": 12, "nome": "Grande"},
                            {"id": 25, "nome": "Borda Catupiry"}
                        ],
                        "observacoes": "Sem cebola",
                        "quantidade": 2,
                        "preco_unitario": 50.0,
                        "subtotal": 100.0
                    }
                ],
                "quantidade_itens": 1,
                "valor_subtotal": 100.0,
                "valor_taxa_entrega": 5.0,
                "valor_desconto": 0.0,
                "valor_total": 105.0
            }
        }


# ==================== FINALIZAR CARRINHO ====================

class FinalizarCarrinhoRequest(BaseModel):
    """Request para finalizar carrinho e criar pedido"""

    codigo_acesso: Optional[str] = Field(None, description="Código do restaurante para validação multi-tenant")
    cliente_nome: Optional[str] = Field(None, min_length=3, max_length=200)
    cliente_telefone: Optional[str] = Field(None, min_length=10, max_length=20)

    tipo_entrega: str = Field(
        ...,
        description="'entrega' ou 'retirada'"
    )

    # Campos para entrega
    endereco_entrega: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Pagamento
    forma_pagamento: str = Field(
        ...,
        description="dinheiro, cartao, pix, vale"
    )
    troco_para: Optional[float] = Field(
        None,
        description="Se dinheiro, troco para quanto"
    )

    observacoes: Optional[str] = Field(
        None,
        max_length=1000
    )

    class Config:
        json_schema_extra = {
            "example": {
                "cliente_nome": "João Silva",
                "cliente_telefone": "11999999999",
                "tipo_entrega": "entrega",
                "endereco_entrega": "Rua Augusta, 123, Apt 45, São Paulo, SP",
                "latitude": -23.550520,
                "longitude": -46.633308,
                "forma_pagamento": "dinheiro",
                "troco_para": 150.0,
                "observacoes": "Interfone 45. Deixar com porteiro se não atender."
            }
        }
