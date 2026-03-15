"""
Models - Super Food API
Importa os models do projeto principal para manter compatibilidade.

IMPORTANTE: Todos os models estão definidos em database/models.py
Este arquivo apenas re-exporta para uso no backend FastAPI.
"""
import sys
from pathlib import Path

# Adiciona raiz do projeto ao path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Re-exporta todos os models do projeto principal
from database.models import (
    # Tenants
    SuperAdmin,
    Restaurante,
    ConfigRestaurante,
    SiteConfig,

    # Motoboys
    Motoboy,
    MotoboySolicitacao,
    GPSMotoboy,

    # Produtos
    CategoriaMenu,
    Produto,
    TipoProduto,
    VariacaoProduto,

    # Pedidos
    Pedido,
    ItemPedido,
    Entrega,
    RotaOtimizada,

    # Clientes
    Cliente,
    EnderecoCliente,
    Carrinho,

    # Financeiro
    Caixa,
    MovimentacaoCaixa,

    # Sistema
    Notificacao,

    # Site Cliente (Fidelidade, Bairros, Promoções)
    BairroEntrega,
    PontosFidelidade,
    TransacaoFidelidade,
    PremioFidelidade,
    Promocao,

    # Combos
    Combo,
    ComboItem,

    # Domínios
    DominioPersonalizado,

    # Tempo Real / Alertas
    AlertaAtraso,
    SugestaoTempo,
)

# Para compatibilidade com imports existentes
__all__ = [
    'SuperAdmin',
    'Restaurante',
    'ConfigRestaurante',
    'SiteConfig',
    'Motoboy',
    'MotoboySolicitacao',
    'GPSMotoboy',
    'CategoriaMenu',
    'Produto',
    'TipoProduto',
    'VariacaoProduto',
    'Pedido',
    'ItemPedido',
    'Entrega',
    'RotaOtimizada',
    'Cliente',
    'EnderecoCliente',
    'Carrinho',
    'Caixa',
    'MovimentacaoCaixa',
    'Notificacao',
    'BairroEntrega',
    'PontosFidelidade',
    'TransacaoFidelidade',
    'PremioFidelidade',
    'Promocao',
    'Combo',
    'ComboItem',
    'DominioPersonalizado',
    'AlertaAtraso',
    'SugestaoTempo',
]
