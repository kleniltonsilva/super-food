import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";

// Tier mínimo para cada feature (espelha backend feature_flags.py)
export const FEATURE_MIN_TIER: Record<string, number> = {
  site_cardapio: 1,
  pedidos: 1,
  dashboard: 1,
  caixa: 1,
  bairros_taxas: 1,
  motoboys: 1,
  configuracoes: 1,
  relatorios_basicos: 1,
  cupons_promocoes: 2,
  fidelidade: 2,
  combos: 2,
  relatorios_avancados: 2,
  operadores_caixa: 2,
  kds_cozinha: 2,
  app_garcom: 3,
  integracoes_marketplace: 3,
  pix_online: 3,
  dominio_personalizado: 3,
  analytics_avancado: 3,
  bridge_printer: 4,
  bot_whatsapp: 4,
  suporte_dedicado: 4,
};

export const FEATURE_LABELS: Record<string, string> = {
  site_cardapio: "Site e Cardápio",
  pedidos: "Pedidos",
  dashboard: "Dashboard",
  caixa: "Caixa",
  bairros_taxas: "Bairros e Taxas",
  motoboys: "Motoboys",
  configuracoes: "Configurações",
  relatorios_basicos: "Relatórios Básicos",
  cupons_promocoes: "Cupons e Promoções",
  fidelidade: "Programa de Fidelidade",
  combos: "Combos Promocionais",
  relatorios_avancados: "Relatórios Avançados",
  operadores_caixa: "Operadores de Caixa",
  kds_cozinha: "KDS Cozinha Digital",
  app_garcom: "App Garçom",
  integracoes_marketplace: "Integrações Marketplace",
  pix_online: "Pix Online",
  dominio_personalizado: "Domínio Personalizado",
  analytics_avancado: "Analytics Avançado",
  bridge_printer: "Bridge Printer IA",
  bot_whatsapp: "WhatsApp Humanoide",
  suporte_dedicado: "Suporte Dedicado",
};

export const TIER_TO_PLANO: Record<number, string> = {
  1: "Básico",
  2: "Essencial",
  3: "Avançado",
  4: "Premium",
};

// Mapa rota sidebar → feature key
export const ROUTE_FEATURE_MAP: Record<string, string> = {
  "/cozinha": "kds_cozinha",
  "/garcons": "app_garcom",
  "/bridge": "bridge_printer",
  "/combos": "combos",
  "/promocoes": "cupons_promocoes",
  "/fidelidade": "fidelidade",
  "/integracoes": "integracoes_marketplace",
  "/pix": "pix_online",
};

export function useFeatureFlag(feature: string) {
  const { restaurante } = useAdminAuth();

  const features = restaurante?.features as Record<string, boolean> | undefined;
  const planoTier = restaurante?.plano_tier ?? 1;
  const plano = restaurante?.plano ?? "Básico";

  // Se tem features do backend, usar diretamente
  if (features && feature in features) {
    return {
      hasFeature: features[feature],
      plano,
      planoTier,
      requiredPlano: TIER_TO_PLANO[FEATURE_MIN_TIER[feature] ?? 1] ?? "Essencial",
      featureLabel: FEATURE_LABELS[feature] ?? feature,
    };
  }

  // Fallback: calcular localmente pelo tier
  const minTier = FEATURE_MIN_TIER[feature] ?? 1;
  return {
    hasFeature: planoTier >= minTier,
    plano,
    planoTier,
    requiredPlano: TIER_TO_PLANO[minTier] ?? "Essencial",
    featureLabel: FEATURE_LABELS[feature] ?? feature,
  };
}
