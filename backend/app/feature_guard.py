# backend/app/feature_guard.py
"""
Feature Guard — FastAPI Depends factory para verificar acesso a features por plano.
"""

from fastapi import Depends, HTTPException
from . import auth, models
from .feature_flags import (
    has_feature, FEATURE_LABELS, FEATURE_TIERS, TIER_TO_PLANO, get_tier
)


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

        # 3. Comparar tier
        tier = getattr(rest, "plano_tier", None) or get_tier(rest.plano)
        overrides = getattr(rest, "features_override", None)

        if has_feature(rest.plano, feature_key, overrides=overrides, plano_tier=tier):
            return rest

        # 4. Feature bloqueada → 403 estruturado
        min_tier = FEATURE_TIERS.get(feature_key, 1)
        required_plano = TIER_TO_PLANO.get(min_tier, "Essencial")
        feature_label = FEATURE_LABELS.get(feature_key, feature_key)

        raise HTTPException(
            status_code=403,
            detail={
                "type": "feature_blocked",
                "feature": feature_key,
                "feature_label": feature_label,
                "current_plano": rest.plano,
                "current_tier": tier,
                "required_plano": required_plano,
                "required_tier": min_tier,
                "message": f"A funcionalidade \"{feature_label}\" requer o plano {required_plano} ou superior. Seu plano atual é {rest.plano}.",
            },
        )

    return _guard
