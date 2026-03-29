# backend/app/feature_guard.py
"""
Feature Guard — FastAPI Depends factory para verificar acesso a features por plano.
"""

from fastapi import Depends, HTTPException
from . import auth, models
from .feature_flags import (
    has_feature, FEATURE_LABELS, FEATURE_TIERS, TIER_TO_PLANO, get_tier,
    ADDON_FEATURES, ADDON_PRICES, ADDON_MIN_TIER, ADDON_LABELS,
)


def _get_addons(rest: models.Restaurante) -> dict[str, bool]:
    """Monta dict de add-ons ativos do restaurante."""
    return {
        "addon_bot_whatsapp": bool(getattr(rest, "addon_bot_whatsapp", False)),
    }


def verificar_feature(feature_key: str):
    """Factory: retorna um FastAPI Depends que verifica se o restaurante tem acesso à feature.

    Uso:
        @router.get("/painel/combos")
        def listar_combos(rest = Depends(verificar_feature("combos"))):
            ...
    """
    async def _guard(
        current_restaurante: models.Restaurante = Depends(auth.get_current_restaurante),
    ) -> models.Restaurante:
        rest = current_restaurante

        # 1. Billing suspenso/cancelado → 403 genérico (igual ao existente)
        if rest.billing_status in ("suspended_billing", "canceled_billing"):
            raise HTTPException(
                status_code=403,
                detail="Assinatura suspensa ou cancelada. Regularize seu pagamento para continuar.",
            )

        # 2. Trial → acesso total (Premium)
        if rest.billing_status == "trial":
            return rest

        # 3. Comparar tier + add-ons
        tier = getattr(rest, "plano_tier", None) or get_tier(rest.plano)
        overrides = getattr(rest, "features_override", None)
        addons = _get_addons(rest)

        if has_feature(rest.plano, feature_key, overrides=overrides, plano_tier=tier, addons=addons):
            return rest

        # 4. Feature bloqueada → 403 estruturado com info de add-on
        min_tier = FEATURE_TIERS.get(feature_key, 1)
        required_plano = TIER_TO_PLANO.get(min_tier, "Essencial")
        feature_label = FEATURE_LABELS.get(feature_key, feature_key)

        detail = {
            "type": "feature_blocked",
            "feature": feature_key,
            "feature_label": feature_label,
            "current_plano": rest.plano,
            "current_tier": tier,
            "required_plano": required_plano,
            "required_tier": min_tier,
            "message": f"A funcionalidade \"{feature_label}\" requer o plano {required_plano} ou superior. Seu plano atual é {rest.plano}.",
        }

        # Informar sobre add-on disponível
        if feature_key in ADDON_FEATURES:
            addon_min = ADDON_MIN_TIER.get(feature_key, 2)
            can_subscribe = tier >= addon_min and tier < min_tier
            detail["addon_info"] = {
                "available": True,
                "price": ADDON_PRICES.get(feature_key, 0),
                "label": ADDON_LABELS.get(feature_key, feature_key),
                "min_tier": addon_min,
                "min_plano": TIER_TO_PLANO.get(addon_min, "Essencial"),
                "can_subscribe": can_subscribe,
            }
            if can_subscribe:
                detail["message"] = (
                    f"A funcionalidade \"{feature_label}\" está disponível como add-on "
                    f"por R${ADDON_PRICES.get(feature_key, 0):.2f}/mês, ou inclusa no plano {required_plano}."
                )

        raise HTTPException(status_code=403, detail=detail)

    return _guard
