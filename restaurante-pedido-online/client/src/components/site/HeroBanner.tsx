/**
 * HeroBanner.tsx — Banner hero temático com suporte a slideshow.
 *
 * Adapta-se ao tipo:
 * - Se tem banner_principal_url: exibe imagem com overlay gradiente
 * - Se não: exibe gradiente do tema com nome/info
 * - Restaurante: sem banner hero grande (seção compacta)
 */

import { Clock, MapPin } from "lucide-react";
import { useRestaurante, useRestauranteTheme } from "@/contexts/RestauranteContext";

const STRONG_SHADOW = "0 1px 4px rgba(0,0,0,0.95), 0 2px 8px rgba(0,0,0,0.85), 0 4px 16px rgba(0,0,0,0.6)";

const INFO_STYLE: React.CSSProperties = {
  color: "#ffffff",
  textShadow: STRONG_SHADOW,
};

export default function HeroBanner() {
  const { siteInfo } = useRestaurante();
  const theme = useRestauranteTheme();

  const nomeRestaurante = siteInfo?.nome_fantasia || "Restaurante";
  const bannerUrl = siteInfo?.banner_principal_url || theme.defaultBanner;
  const hasBanner = !!bannerUrl;

  // Restaurante tipo "restaurante" sem banner customizado: seção compacta
  if (theme.id === "restaurante" && !siteInfo?.banner_principal_url && !theme.defaultBanner) {
    return (
      <div
        className="w-full py-6 md:py-8"
        style={{ background: theme.colors.headerBg }}
      >
        <div className="container text-center">
          <h2
            className="text-2xl md:text-3xl font-bold mb-2"
            style={{ color: "#ffffff", fontFamily: theme.fonts.heading, textShadow: STRONG_SHADOW }}
          >
            {nomeRestaurante}
          </h2>
          <div className="flex items-center justify-center gap-4 text-sm" style={INFO_STYLE}>
            <span className="flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              ~{siteInfo?.tempo_entrega_estimado || 50} min
            </span>
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" />
              Entrega e Retirada
            </span>
          </div>
        </div>
      </div>
    );
  }

  // Com banner
  if (hasBanner) {
    const overlayGradient = theme.isDark
      ? "linear-gradient(to top, rgba(0,0,0,0.85), transparent, transparent)"
      : `linear-gradient(to top, ${theme.colors.bodyBg}, transparent, transparent)`;

    return (
      <div className="w-full h-40 md:h-56 overflow-hidden relative">
        <img
          src={bannerUrl!}
          alt={nomeRestaurante}
          className="w-full h-full object-cover"
          loading="lazy"
          style={{
            borderRadius: theme.id === "acai" || theme.id === "bebidas" ? "0 0 28px 28px" : undefined,
          }}
        />
        <div className="absolute inset-0" style={{ background: overlayGradient }} />
        <div className="absolute bottom-4 left-0 right-0">
          <div className="container">
            <div className="flex items-center gap-3">
              <h2
                className="text-xl md:text-2xl font-bold"
                style={{ color: "#ffffff", fontFamily: theme.fonts.heading, textShadow: STRONG_SHADOW }}
              >
                {nomeRestaurante}
              </h2>
              <span className="text-xs px-2 py-0.5 rounded-full text-white/90 border border-white/30 bg-white/10 backdrop-blur-sm">
                {siteInfo?.tipo_restaurante || "Restaurante"}
              </span>
            </div>
            <div className="flex items-center gap-4 mt-1 text-sm" style={INFO_STYLE}>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                ~{siteInfo?.tempo_entrega_estimado || 50} min
              </span>
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" />
                Entrega e Retirada
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Sem banner — gradiente do tema
  return (
    <div
      className="w-full h-36 md:h-48 flex items-center justify-center relative overflow-hidden"
      style={{ background: theme.colors.heroGradient }}
    >
      <div className="absolute inset-0 bg-black/20" />
      <div className="text-center text-white relative z-10">
        <h2
          className="text-2xl md:text-3xl font-bold mb-2"
          style={{ fontFamily: theme.fonts.heading, textShadow: STRONG_SHADOW }}
        >
          {nomeRestaurante}
        </h2>
        <p className="text-sm opacity-80">{theme.label}</p>
        <div className="flex items-center justify-center gap-4 mt-2 text-sm" style={INFO_STYLE}>
          <span className="flex items-center gap-1">
            <Clock className="w-3.5 h-3.5" />
            ~{siteInfo?.tempo_entrega_estimado || 50} min
          </span>
        </div>
      </div>
    </div>
  );
}
