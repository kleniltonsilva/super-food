/**
 * themeConfig.ts — Configuração completa de tema por tipo de restaurante.
 *
 * Cada tipo possui: cores (primária, secundária, body, header, footer, preço, badge),
 * fontes (heading, body), borderRadius dos cards, estilo do header (dark/light/pattern),
 * e mood descritivo.
 *
 * Paleta extraída dos modelos HTML em `MODELOS DE RESTAURANTES/`.
 */

export type HeaderStyle = "dark" | "light" | "pattern";

export interface ThemeColors {
  primary: string;
  secondary: string;
  bodyBg: string;
  headerBg: string;
  footerBg: string;
  priceColor: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  cardBg: string;
  cardBorder: string;
  borderSubtle: string;
  shadowCard: string;
  shadowCardHover: string;
  /** Cor do badge "Do Chef", "Promo", etc. */
  badgeColors: {
    doChef: string;
    novidade: string;
    promo: string;
    maisPedido: string;
    lancamento: string;
    maisVendido: string;
  };
  /** Gradiente do hero/banner */
  heroGradient: string;
  /** Botão comprar */
  btnComprar: string;
  btnComprarBorder: string;
  /** Controles de quantidade */
  quantityDecrease: string;
  quantityIncrease: string;
  /** Top bar login */
  topBarBg: string;
  topBarText: string;
}

export interface ThemeFonts {
  heading: string;
  body: string;
  /** Fonte especial (ex: Kaushan Script para Sushi) — aplicada em TODOS os textos */
  special?: string;
}

export interface ThemeConfig {
  id: string;
  label: string;
  mood: string;
  colors: ThemeColors;
  fonts: ThemeFonts;
  cardRadius: string;
  headerStyle: HeaderStyle;
  /** Temas escuros (Hamburgueria, Sushi) invertem ícones e usam texto claro */
  isDark: boolean;
  /** Imagem de pattern para o body (se aplicável) */
  bodyPattern?: string;
  /** Imagem de pattern para o header (se aplicável) */
  headerPattern?: string;
  /** Imagem de pattern para o footer (se aplicável) */
  footerPattern?: string;
  /** Tamanho máximo do logo */
  logoMaxWidth: string;
  /** Imagens de produto com formato circular (Pizzaria) */
  circularImages: boolean;
  /** Footer border top (ex: Bebidas tem 8px solid red) */
  footerBorderTop?: string;
  /** Banner padrão do tema (fallback quando restaurante não tem banner) */
  defaultBanner?: string;
}

// Badges padrão — iguais para todos os tipos
const defaultBadges: ThemeColors["badgeColors"] = {
  doChef: "#e4002e",
  novidade: "#169e0a",
  promo: "#2ecc71",
  maisPedido: "#ff0000",
  lancamento: "#a40000",
  maisVendido: "#2ecc71",
};

// Botão verde padrão (todos os tipos)
const defaultBtnComprar = "#087607";
const defaultBtnComprarBorder = "#014f00";

// Quantidade +/- padrão
const defaultQuantityDecrease = "#ff0d0d";
const defaultQuantityIncrease = "#00b400";

// Top bar padrão
const defaultTopBar = { bg: "#333", text: "#fff" };

export const themeConfigs: Record<string, ThemeConfig> = {
  // ─── PIZZARIA ─────────────────────────────────────────
  pizzaria: {
    id: "pizzaria",
    label: "Pizzaria",
    mood: "Italiano clássico",
    colors: {
      primary: "#e4002e",
      secondary: "#ffefef",
      bodyBg: "#ffefef",
      headerBg: "#ffffff",
      footerBg: "#333333",
      priceColor: "#a40000",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.08)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.12)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #e4002e, #a40000)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: defaultTopBar.bg,
      topBarText: defaultTopBar.text,
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "12px",
    headerStyle: "pattern",
    isDark: false,
    logoMaxWidth: "380px",
    circularImages: true,
    bodyPattern: undefined,
    headerPattern: "/themes/pizzaria/bg-header.png",
    footerPattern: "/themes/pizzaria/bg-header.png",
    defaultBanner: "/themes/pizzaria/banner.png",
  },

  // ─── HAMBURGUERIA ────────────────────────────────────
  hamburgueria: {
    id: "hamburgueria",
    label: "Hamburgueria",
    mood: "Dark urbano",
    colors: {
      primary: "#ffcd00",
      secondary: "#161616",
      bodyBg: "#161616",
      headerBg: "#161616",
      footerBg: "#ffcd00",
      priceColor: "#ffcd00",
      textPrimary: "#ffffff",
      textSecondary: "#b3b3b3",
      textMuted: "#6b6b6b",
      cardBg: "#303030",
      cardBorder: "rgba(255,255,255,0.08)",
      borderSubtle: "rgba(255,255,255,0.06)",
      shadowCard: "0 2px 8px rgba(0,0,0,0.3)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.5)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #ffcd00, #ff8c00)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: "#111111",
      topBarText: "#ffffff",
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "16px",
    headerStyle: "dark",
    isDark: true,
    logoMaxWidth: "320px",
    circularImages: false,
    defaultBanner: "/themes/hamburgueria/banner.png",
  },

  // ─── SUSHI ───────────────────────────────────────────
  sushi: {
    id: "sushi",
    label: "Sushi / Japonesa",
    mood: "Oriental minimalista",
    colors: {
      primary: "#a40000",
      secondary: "#1d1c1c",
      bodyBg: "#1a1a1a",
      headerBg: "#1d1c1c",
      footerBg: "#1d1c1c",
      priceColor: "#a40000",
      textPrimary: "#ffffff",
      textSecondary: "#cccccc",
      textMuted: "#888888",
      cardBg: "#252525",
      cardBorder: "rgba(255,255,255,0.06)",
      borderSubtle: "rgba(255,255,255,0.04)",
      shadowCard: "0 2px 8px rgba(0,0,0,0.4)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.6)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #a40000, #1d1c1c)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: "#111111",
      topBarText: "#ffffff",
    },
    fonts: {
      heading: "'Kaushan Script', cursive",
      body: "'Lato', sans-serif",
      special: "'Kaushan Script', cursive",
    },
    cardRadius: "16px",
    headerStyle: "dark",
    isDark: true,
    logoMaxWidth: "460px",
    circularImages: false,
    bodyPattern: "/themes/sushi/bg-body.png",
    defaultBanner: "/themes/sushi/banner.png",
  },

  // ─── AÇAÍ / SORVETES ────────────────────────────────
  acai: {
    id: "acai",
    label: "Açaí / Sorvetes",
    mood: "Tropical dessert",
    colors: {
      primary: "#61269c",
      secondary: "#2a7e3f",
      bodyBg: "#ffffff",
      headerBg: "#ffffff",
      footerBg: "#562a98",
      priceColor: "#61269c",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.08)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.12)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #61269c, #2a7e3f)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: defaultTopBar.bg,
      topBarText: defaultTopBar.text,
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "28px",
    headerStyle: "pattern",
    isDark: false,
    logoMaxWidth: "380px",
    circularImages: false,
    headerPattern: "/themes/acai/bg-header.png",
    defaultBanner: "/themes/acai/banner.png",
  },

  // ─── BEBIDAS ─────────────────────────────────────────
  bebidas: {
    id: "bebidas",
    label: "Bebidas / Distribuidora",
    mood: "Clean fresh",
    colors: {
      primary: "#e50e16",
      secondary: "#f6f5f5",
      bodyBg: "#f6f5f5",
      headerBg: "#f6f5f5",
      footerBg: "#f6f5f5",
      priceColor: "#e50e16",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.06)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.10)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #e50e16, #ff4444)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: defaultTopBar.bg,
      topBarText: defaultTopBar.text,
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "28px",
    headerStyle: "light",
    isDark: false,
    logoMaxWidth: "380px",
    circularImages: false,
    footerBorderTop: "8px solid #e50e16",
    defaultBanner: "/themes/bebidas/banner.png",
  },

  // ─── ESFIHARIA ───────────────────────────────────────
  esfiharia: {
    id: "esfiharia",
    label: "Esfiharia",
    mood: "Árabe quente",
    colors: {
      primary: "#d4880f",
      secondary: "#5c3310",
      bodyBg: "#fff8f0",
      headerBg: "#5c3310",
      footerBg: "#5c3310",
      priceColor: "#d4880f",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.08)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.12)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #d4880f, #5c3310)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: defaultTopBar.bg,
      topBarText: defaultTopBar.text,
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "16px",
    headerStyle: "pattern",
    isDark: false,
    logoMaxWidth: "380px",
    circularImages: false,
    headerPattern: "/themes/esfiharia/bg-header.png",
    defaultBanner: "/themes/esfiharia/banner.png",
  },

  // ─── RESTAURANTE ─────────────────────────────────────
  restaurante: {
    id: "restaurante",
    label: "Restaurante",
    mood: "Casual quente",
    colors: {
      primary: "#ff990a",
      secondary: "#2b2723",
      bodyBg: "#faf6f1",
      headerBg: "#2b2723",
      footerBg: "#2b2723",
      priceColor: "#ff990a",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.08)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.12)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #ff990a, #2b2723)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: "#2b2723",
      topBarText: "#ffffff",
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "16px",
    headerStyle: "dark",
    isDark: false,
    logoMaxWidth: "460px",
    circularImages: false,
    bodyPattern: "/themes/restaurante/bg-body.png",
    defaultBanner: "/themes/restaurante/banner.png",
  },

  // ─── SALGADOS / DOCES ────────────────────────────────
  salgados: {
    id: "salgados",
    label: "Salgados / Doces",
    mood: "Artesanal festa",
    colors: {
      primary: "#ff883a",
      secondary: "#fff5eb",
      bodyBg: "#fff5eb",
      headerBg: "#ffffff",
      footerBg: "#fff5eb",
      priceColor: "#ff883a",
      textPrimary: "#333333",
      textSecondary: "#666666",
      textMuted: "#999999",
      cardBg: "#ffffff",
      cardBorder: "#d4d4d4",
      borderSubtle: "#e8e8e8",
      shadowCard: "0 2px 8px rgba(0,0,0,0.06)",
      shadowCardHover: "0 8px 24px rgba(0,0,0,0.10)",
      badgeColors: defaultBadges,
      heroGradient: "linear-gradient(135deg, #ff883a, #ff6b00)",
      btnComprar: defaultBtnComprar,
      btnComprarBorder: defaultBtnComprarBorder,
      quantityDecrease: defaultQuantityDecrease,
      quantityIncrease: defaultQuantityIncrease,
      topBarBg: defaultTopBar.bg,
      topBarText: defaultTopBar.text,
    },
    fonts: {
      heading: "'Oswald', sans-serif",
      body: "'Lato', sans-serif",
    },
    cardRadius: "18px",
    headerStyle: "pattern",
    isDark: false,
    logoMaxWidth: "380px",
    circularImages: false,
    headerPattern: "/themes/salgados/bg-header.png",
    footerBorderTop: "8px solid #ff883a",
    defaultBanner: "/themes/salgados/banner.jpg",
  },
};

/**
 * Resolve o ID do tema a partir do tipo_restaurante do banco.
 * Faz matching parcial case-insensitive.
 */
export function resolveThemeId(tipo: string): string {
  const t = (tipo || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  if (t.includes("pizza")) return "pizzaria";
  if (t.includes("hambur") || t.includes("lanch") || t.includes("burger")) return "hamburgueria";
  if (t.includes("sushi") || t.includes("japon") || t.includes("oriental")) return "sushi";
  if (t.includes("acai") || t.includes("sorvet") || t.includes("gelat")) return "acai";
  if (t.includes("bebid") || t.includes("distribui")) return "bebidas";
  if (t.includes("esfih")) return "esfiharia";
  if (t.includes("salgad") || t.includes("doce") || t.includes("confeit") || t.includes("bolo") || t.includes("festa")) return "salgados";
  if (t.includes("restaurante") || t.includes("geral")) return "restaurante";
  // Tipos extras sem modelo — usam restaurante como base
  if (t.includes("churrasco") || t.includes("grill")) return "restaurante";
  if (t.includes("padaria") || t.includes("cafe")) return "restaurante";
  if (t.includes("fitness") || t.includes("sauda")) return "restaurante";
  if (t.includes("marmitex") || t.includes("marmita")) return "restaurante";
  return "restaurante"; // fallback
}

/**
 * Retorna a config de tema completa para um tipo de restaurante.
 */
export function getThemeConfig(tipo: string): ThemeConfig {
  const id = resolveThemeId(tipo);
  return themeConfigs[id] || themeConfigs.restaurante;
}

/**
 * Gera as CSS variables a partir de um ThemeConfig.
 * Retorna um Record de variáveis prontas para aplicar ao :root.
 */
export function themeToCSSVars(
  theme: ThemeConfig,
  overridePrimary?: string,
  overrideSecondary?: string,
): Record<string, string> {
  const c = theme.colors;
  const primary = overridePrimary || c.primary;
  const secondary = overrideSecondary || c.secondary;

  return {
    // Cores do tema
    "--theme-primary": primary,
    "--theme-secondary": secondary,
    "--theme-body-bg": c.bodyBg,
    "--theme-header-bg": c.headerBg,
    "--theme-footer-bg": c.footerBg,
    "--theme-price-color": c.priceColor,
    "--theme-text-primary": c.textPrimary,
    "--theme-text-secondary": c.textSecondary,
    "--theme-text-muted": c.textMuted,
    "--theme-card-bg": c.cardBg,
    "--theme-card-border": c.cardBorder,
    "--theme-border-subtle": c.borderSubtle,
    "--theme-shadow-card": c.shadowCard,
    "--theme-shadow-card-hover": c.shadowCardHover,
    "--theme-hero-gradient": c.heroGradient,
    "--theme-card-radius": theme.cardRadius,
    "--theme-heading-font": theme.fonts.heading,
    "--theme-body-font": theme.fonts.body,
    "--theme-btn-comprar": c.btnComprar,
    "--theme-btn-comprar-border": c.btnComprarBorder,
    "--theme-qty-decrease": c.quantityDecrease,
    "--theme-qty-increase": c.quantityIncrease,
    "--theme-topbar-bg": c.topBarBg,
    "--theme-topbar-text": c.topBarText,
    "--theme-logo-max-width": theme.logoMaxWidth,
    // Compatibilidade com CSS existente
    "--cor-primaria": primary,
    "--cor-secundaria": secondary,
    // Shadcn tokens
    "--primary": primary,
    "--accent": primary,
    "--ring": primary,
    // Design tokens que se adaptam ao tema
    "--bg-base": c.bodyBg,
    "--bg-surface": theme.isDark ? c.cardBg : "#f8f8f8",
    "--bg-card": c.cardBg,
    "--bg-card-hover": theme.isDark
      ? "color-mix(in srgb, " + primary + " 15%, #1a1a1a)"
      : "color-mix(in srgb, " + primary + " 10%, white)",
    "--text-primary": c.textPrimary,
    "--text-secondary": c.textSecondary,
    "--text-muted": c.textMuted,
    "--border-subtle": c.borderSubtle,
    "--shadow-card": c.shadowCard,
    "--shadow-card-hover": c.shadowCardHover,
    "--radius-card": theme.cardRadius,
  };
}

/**
 * Lista de todos os tipos disponíveis para o select de cadastro.
 */
export const tiposRestaurante = Object.values(themeConfigs).map((t) => ({
  id: t.id,
  label: t.label,
  mood: t.mood,
}));
