# backend/app/feature_flags.py
"""
Feature Flags por Plano — Registry central de features.
Comparação por tier inteiro (1-4). Hierarquia cumulativa.
"""

from enum import IntEnum
from typing import Optional
import json


class PlanTier(IntEnum):
    BASICO = 1
    ESSENCIAL = 2
    AVANCADO = 3
    PREMIUM = 4


# Mapeamento nome do plano → tier (com aliases)
PLANO_TO_TIER: dict[str, int] = {
    "Básico": 1, "basico": 1, "Basico": 1, "básico": 1,
    "Essencial": 2, "essencial": 2,
    "Avançado": 3, "avancado": 3, "Avancado": 3, "avançado": 3,
    "Premium": 4, "premium": 4,
}

# Feature key → tier mínimo necessário
FEATURE_TIERS: dict[str, int] = {
    # Tier 1 — Básico (incluído em todos)
    "site_cardapio": 1,
    "pedidos": 1,
    "dashboard": 1,
    "caixa": 1,
    "bairros_taxas": 1,
    "motoboys": 1,
    "configuracoes": 1,
    "relatorios_basicos": 1,

    # Tier 2 — Essencial
    "cupons_promocoes": 2,
    "fidelidade": 2,
    "combos": 2,
    "relatorios_avancados": 2,
    "operadores_caixa": 2,
    "kds_cozinha": 2,

    # Tier 3 — Avançado
    "app_garcom": 3,
    "integracoes_marketplace": 3,
    "pix_online": 3,
    "dominio_personalizado": 3,
    "analytics_avancado": 3,

    # Tier 1 — Básico (operacional — incluso em todos os planos conforme termos de uso)
    "bridge_printer": 1,

    # Tier 4 — Premium
    "bot_whatsapp": 4,
    "suporte_dedicado": 4,
}

# Labels legíveis em pt-BR (para mensagens de upgrade)
FEATURE_LABELS: dict[str, str] = {
    "site_cardapio": "Site e Cardápio",
    "pedidos": "Pedidos",
    "dashboard": "Dashboard",
    "caixa": "Caixa",
    "bairros_taxas": "Bairros e Taxas",
    "motoboys": "Motoboys",
    "configuracoes": "Configurações",
    "relatorios_basicos": "Relatórios Básicos",
    "cupons_promocoes": "Cupons e Promoções",
    "fidelidade": "Programa de Fidelidade",
    "combos": "Combos Promocionais",
    "relatorios_avancados": "Relatórios Avançados",
    "operadores_caixa": "Operadores de Caixa",
    "kds_cozinha": "KDS Cozinha Digital",
    "app_garcom": "App Garçom",
    "integracoes_marketplace": "Integrações Marketplace",
    "pix_online": "Pix Online",
    "dominio_personalizado": "Domínio Personalizado",
    "analytics_avancado": "Analytics Avançado",
    "bridge_printer": "Bridge Printer IA",
    "bot_whatsapp": "WhatsApp Humanoide",
    "suporte_dedicado": "Suporte Dedicado",
}

# Tier → nome do plano (para mensagens de upgrade)
TIER_TO_PLANO: dict[int, str] = {
    1: "Básico",
    2: "Essencial",
    3: "Avançado",
    4: "Premium",
}

# Limite de motoboys por tier
MOTOBOYS_POR_TIER: dict[int, int] = {
    1: 2,
    2: 5,
    3: 10,
    4: 999,
}

# Features novas em cada tier (só as que são novas naquele nível)
FEATURES_POR_PLANO: dict[str, list[str]] = {
    "Básico": [k for k, v in FEATURE_TIERS.items() if v == 1],
    "Essencial": [k for k, v in FEATURE_TIERS.items() if v == 2],
    "Avançado": [k for k, v in FEATURE_TIERS.items() if v == 3],
    "Premium": [k for k, v in FEATURE_TIERS.items() if v == 4],
}


def get_tier(plano_nome: Optional[str]) -> int:
    """Retorna tier numérico a partir do nome do plano. Default: 1 (Básico)."""
    if not plano_nome:
        return 1
    return PLANO_TO_TIER.get(plano_nome, PLANO_TO_TIER.get(plano_nome.strip(), 1))


def has_feature(plano: Optional[str], feature_key: str, overrides: Optional[str] = None, plano_tier: Optional[int] = None) -> bool:
    """Verifica se um plano tem acesso a uma feature.

    Args:
        plano: Nome do plano (ex: "Essencial")
        feature_key: Chave da feature (ex: "kds_cozinha")
        overrides: JSON string de overrides do Super Admin (ex: '{"kds_cozinha": true}')
        plano_tier: Tier pré-computado (evita recalcular)
    """
    # Override do Super Admin tem prioridade absoluta
    if overrides:
        try:
            override_dict = json.loads(overrides) if isinstance(overrides, str) else overrides
            if feature_key in override_dict:
                return bool(override_dict[feature_key])
        except (json.JSONDecodeError, TypeError):
            pass

    tier = plano_tier if plano_tier is not None else get_tier(plano)
    min_tier = FEATURE_TIERS.get(feature_key, 1)
    return tier >= min_tier


def get_all_features(plano: Optional[str], overrides: Optional[str] = None, plano_tier: Optional[int] = None) -> dict[str, bool]:
    """Retorna dict com todas features e se o plano tem acesso.

    Args:
        plano: Nome do plano
        overrides: JSON string de overrides
        plano_tier: Tier pré-computado
    """
    tier = plano_tier if plano_tier is not None else get_tier(plano)

    override_dict = {}
    if overrides:
        try:
            override_dict = json.loads(overrides) if isinstance(overrides, str) else overrides
        except (json.JSONDecodeError, TypeError):
            pass

    result = {}
    for feature_key, min_tier in FEATURE_TIERS.items():
        if feature_key in override_dict:
            result[feature_key] = bool(override_dict[feature_key])
        else:
            result[feature_key] = tier >= min_tier
    return result


def get_features_list_for_plano(plano_nome: str) -> list[str]:
    """Retorna lista cumulativa de features para um plano (todas do tier e abaixo)."""
    tier = get_tier(plano_nome)
    return [k for k, v in FEATURE_TIERS.items() if v <= tier]


def get_new_features_for_plano(plano_nome: str) -> list[str]:
    """Retorna apenas features novas neste tier (não herdadas)."""
    tier = get_tier(plano_nome)
    return [k for k, v in FEATURE_TIERS.items() if v == tier]
