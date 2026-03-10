/**
 * CategoryNav.tsx — Navegação de categorias temática.
 *
 * Carousel horizontal com scroll suave usando embla-carousel.
 * Estilos por tipo:
 * - Pizzaria/Açaí/Restaurante: pill com gradiente colorido
 * - Bebidas/Sushi: pill rounded
 * - Salgados: pill com background
 * - Hamburgueria: pill dark
 *
 * Sticky abaixo do header. Auto-highlight por IntersectionObserver.
 */

import { useRef, useCallback } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRestauranteTheme } from "@/contexts/RestauranteContext";

interface Categoria {
  id: number;
  nome: string;
  icone: string | null;
  ordem_exibicao: number;
}

interface CategoryNavProps {
  categorias: Categoria[];
  loading: boolean;
  activeSection: number | null;
  produtoCounts: Map<number, number>;
  onCategoryClick: (catId: number) => void;
}

export default function CategoryNav({
  categorias,
  loading,
  activeSection,
  produtoCounts,
  onCategoryClick,
}: CategoryNavProps) {
  const theme = useRestauranteTheme();
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollLeft = useCallback(() => {
    scrollRef.current?.scrollBy({ left: -200, behavior: "smooth" });
  }, []);

  const scrollRight = useCallback(() => {
    scrollRef.current?.scrollBy({ left: 200, behavior: "smooth" });
  }, []);

  const isDark = theme.isDark;
  const navBg = isDark ? theme.colors.headerBg : theme.colors.bodyBg;
  const navBorder = isDark ? "rgba(255,255,255,0.06)" : "#e8e8e8";
  const navShadow = isDark ? "0 1px 6px rgba(0,0,0,0.3)" : "0 1px 6px rgba(0,0,0,0.06)";

  // Estilos do botão de categoria baseados no tema
  function getCatStyle(isActive: boolean): React.CSSProperties {
    if (isActive) {
      return {
        background: theme.colors.primary,
        color: "#ffffff",
        borderColor: theme.colors.primary,
        fontFamily: theme.fonts.heading,
      };
    }

    return {
      background: isDark ? "rgba(255,255,255,0.06)" : "#ffffff",
      color: isDark ? theme.colors.textSecondary : theme.colors.textSecondary,
      borderColor: isDark ? "rgba(255,255,255,0.08)" : "#d4d4d4",
      fontFamily: theme.fonts.heading,
    };
  }

  const arrowStyle: React.CSSProperties = {
    background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.04)",
    color: isDark ? "#ffffff" : theme.colors.textPrimary,
  };

  return (
    <nav
      className="sticky top-[60px] z-40"
      style={{ background: navBg, borderBottom: `1px solid ${navBorder}`, boxShadow: navShadow }}
    >
      <div className="container relative">
        {/* Seta esquerda */}
        <button
          onClick={scrollLeft}
          className="hidden md:flex absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full items-center justify-center hover:opacity-80 transition-opacity"
          style={arrowStyle}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        {/* Scroll container */}
        <div
          ref={scrollRef}
          className="flex gap-2 overflow-x-auto scrollbar-hide py-2.5 category-fade mx-0 md:mx-10"
        >
          {loading ? (
            [1, 2, 3, 4].map(i => (
              <div
                key={i}
                className="h-9 w-28 rounded-full flex-shrink-0 animate-pulse"
                style={{ background: isDark ? "rgba(255,255,255,0.06)" : "#e8e8e8" }}
              />
            ))
          ) : (
            categorias.map((cat) => {
              const count = produtoCounts.get(cat.id) || 0;
              if (count === 0) return null;
              const isActive = activeSection === cat.id;

              return (
                <button
                  key={cat.id}
                  data-cat-id={cat.id}
                  onClick={() => onCategoryClick(cat.id)}
                  className="flex items-center gap-1.5 whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-all flex-shrink-0 border"
                  style={getCatStyle(isActive)}
                >
                  {cat.icone && <span>{cat.icone}</span>}
                  {cat.nome.replace(/^[^\w\s]+\s*/, "")}
                  <span
                    className="text-xs"
                    style={{ opacity: isActive ? 0.7 : 0.5 }}
                  >
                    ({count})
                  </span>
                </button>
              );
            })
          )}
        </div>

        {/* Seta direita */}
        <button
          onClick={scrollRight}
          className="hidden md:flex absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full items-center justify-center hover:opacity-80 transition-opacity"
          style={arrowStyle}
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
}
