/**
 * FooterSection.tsx — Footer temático 3 colunas.
 *
 * Adapta-se ao tipo:
 * - Hamburgueria: footer amarelo #ffcd00, texto escuro
 * - Açaí: footer roxo #562a98, texto branco
 * - Sushi: footer dark gradient igual header
 * - Pizzaria/Salgados: footer com pattern image repeat-x
 * - Bebidas/Restaurante: footer com borda superior colorida
 */

import { Clock, MapPin, Phone } from "lucide-react";
import { useRestaurante, useRestauranteTheme } from "@/contexts/RestauranteContext";

export default function FooterSection() {
  const { siteInfo } = useRestaurante();
  const theme = useRestauranteTheme();

  const nomeRestaurante = siteInfo?.nome_fantasia || "Restaurante";

  // Footer cor de texto — depende do background
  const footerBg = theme.colors.footerBg;
  const isFooterDark = isColorDark(footerBg);
  const footerTextColor = isFooterDark ? "#ffffff" : theme.colors.textPrimary;
  const footerMutedColor = isFooterDark ? "rgba(255,255,255,0.7)" : theme.colors.textMuted;
  const footerBorderColor = isFooterDark ? "rgba(255,255,255,0.1)" : "#e8e8e8";

  const footerStyle: React.CSSProperties = {
    background: footerBg,
    ...(theme.footerPattern ? {
      backgroundImage: `url(${theme.footerPattern})`,
      backgroundRepeat: "repeat-x",
      backgroundSize: "auto 100%",
    } : {}),
  };

  return (
    <footer className="mt-12" style={footerStyle}>
      {/* Accent line ou border top */}
      {theme.footerBorderTop ? (
        <div style={{ borderTop: theme.footerBorderTop }} />
      ) : (
        <div
          className="h-1"
          style={{ background: `linear-gradient(90deg, ${theme.colors.primary}, ${theme.colors.secondary})` }}
        />
      )}

      <div className="container px-4 py-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Coluna 1 — Endereço + Horários */}
          <div>
            <h3
              className="font-bold text-base mb-3"
              style={{
                color: theme.colors.primary,
                fontFamily: theme.fonts.special || theme.fonts.heading,
              }}
            >
              {nomeRestaurante}
            </h3>
            <p className="text-sm flex items-start gap-1.5 mb-2" style={{ color: footerMutedColor }}>
              <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              {siteInfo?.endereco_completo}
            </p>
            <p className="text-sm flex items-center gap-1.5" style={{ color: footerMutedColor }}>
              <Clock className="w-3.5 h-3.5" />
              {siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}
            </p>
          </div>

          {/* Coluna 2 — Contato */}
          <div>
            <h3
              className="font-bold text-base mb-3"
              style={{
                color: theme.colors.primary,
                fontFamily: theme.fonts.special || theme.fonts.heading,
              }}
            >
              Contato
            </h3>
            <p className="text-sm flex items-center gap-1.5 mb-2" style={{ color: footerMutedColor }}>
              <Phone className="w-3.5 h-3.5" />
              {siteInfo?.telefone}
            </p>
            {siteInfo?.whatsapp_ativo && siteInfo.whatsapp_numero && (
              <a
                href={`https://wa.me/${siteInfo.whatsapp_numero.replace(/\D/g, "")}?text=${encodeURIComponent(siteInfo.whatsapp_mensagem_padrao || "Olá!")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm mt-1 hover:opacity-80 transition-opacity"
                style={{ color: "#25D366" }}
              >
                WhatsApp: {siteInfo.whatsapp_numero}
              </a>
            )}
          </div>

          {/* Coluna 3 — Formas de pagamento */}
          <div>
            <h3
              className="font-bold text-base mb-3"
              style={{
                color: theme.colors.primary,
                fontFamily: theme.fonts.special || theme.fonts.heading,
              }}
            >
              Pagamento
            </h3>
            <div className="flex flex-wrap gap-2">
              {siteInfo?.aceita_dinheiro && (
                <span className="text-xs px-2 py-1 rounded-full" style={{ background: isFooterDark ? "rgba(255,255,255,0.1)" : "#f0f0f0", color: footerMutedColor }}>
                  Dinheiro
                </span>
              )}
              {siteInfo?.aceita_cartao && (
                <span className="text-xs px-2 py-1 rounded-full" style={{ background: isFooterDark ? "rgba(255,255,255,0.1)" : "#f0f0f0", color: footerMutedColor }}>
                  Cartão
                </span>
              )}
              {siteInfo?.aceita_pix && (
                <span className="text-xs px-2 py-1 rounded-full" style={{ background: isFooterDark ? "rgba(255,255,255,0.1)" : "#f0f0f0", color: footerMutedColor }}>
                  PIX
                </span>
              )}
              {siteInfo?.aceita_vale_refeicao && (
                <span className="text-xs px-2 py-1 rounded-full" style={{ background: isFooterDark ? "rgba(255,255,255,0.1)" : "#f0f0f0", color: footerMutedColor }}>
                  Vale Refeição
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="mt-8 pt-6 text-center text-xs" style={{ borderTop: `1px solid ${footerBorderColor}`, color: footerMutedColor }}>
          &copy; {new Date().getFullYear()} {nomeRestaurante} - Powered by Super Food
        </div>
      </div>
    </footer>
  );
}

/** Helper: determina se uma cor hex é escura */
function isColorDark(hex: string): boolean {
  // Remove # e tenta parsear
  const clean = hex.replace("#", "");
  if (clean.length < 6) return true;
  const r = parseInt(clean.substring(0, 2), 16);
  const g = parseInt(clean.substring(2, 4), 16);
  const b = parseInt(clean.substring(4, 6), 16);
  // Luminância relativa
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum < 0.5;
}
