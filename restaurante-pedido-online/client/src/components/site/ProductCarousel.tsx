/**
 * ProductCarousel.tsx — Carousel horizontal de ProductCards usando embla-carousel.
 *
 * Mostra produtos em carousel com setas prev/next nos lados.
 * Usado quando a categoria tem muitos produtos para melhor UX.
 * Adapta a largura dos slides por breakpoint.
 */

import { useCallback } from "react";
import useEmblaCarousel from "embla-carousel-react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useRestauranteTheme } from "@/contexts/RestauranteContext";
import ProductCard from "./ProductCard";

interface Variacao {
  id: number;
  tipo_variacao: string;
  nome: string;
  preco_adicional: number;
  max_sabores?: number;
}

interface Produto {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  preco_promocional: number | null;
  imagem_url: string | null;
  destaque: boolean;
  promocao: boolean;
  categoria_id: number;
  variacoes: Variacao[];
}

interface ProductCarouselProps {
  produtos: Produto[];
  getEmoji: (produto: Produto) => string;
  onPizzaBuilderOpen?: (produtoId: number) => void;
}

export default function ProductCarousel({ produtos, getEmoji, onPizzaBuilderOpen }: ProductCarouselProps) {
  const theme = useRestauranteTheme();

  const [emblaRef, emblaApi] = useEmblaCarousel({
    align: "start",
    containScroll: "trimSnaps",
    slidesToScroll: 1,
    dragFree: true,
  });

  const scrollPrev = useCallback(() => emblaApi?.scrollPrev(), [emblaApi]);
  const scrollNext = useCallback(() => emblaApi?.scrollNext(), [emblaApi]);

  return (
    <div className="relative group">
      {/* Seta prev */}
      <button
        className="absolute -left-3 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full flex items-center justify-center shadow-md opacity-0 group-hover:opacity-100 transition-opacity hidden md:flex"
        style={{
          background: theme.colors.cardBg,
          border: `1px solid ${theme.colors.borderSubtle}`,
          color: theme.colors.textPrimary,
        }}
        onClick={scrollPrev}
      >
        <ChevronLeft className="w-4 h-4" />
      </button>

      {/* Carousel */}
      <div className="overflow-hidden" ref={emblaRef}>
        <div className="flex gap-4">
          {produtos.map((produto) => (
            <div
              key={produto.id}
              className="flex-shrink-0 w-[48%] sm:w-[31%] lg:w-[31%]"
            >
              <ProductCard produto={produto} emoji={getEmoji(produto)} onPizzaBuilderOpen={onPizzaBuilderOpen} />
            </div>
          ))}
        </div>
      </div>

      {/* Seta next */}
      <button
        className="absolute -right-3 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full flex items-center justify-center shadow-md opacity-0 group-hover:opacity-100 transition-opacity hidden md:flex"
        style={{
          background: theme.colors.cardBg,
          border: `1px solid ${theme.colors.borderSubtle}`,
          color: theme.colors.textPrimary,
        }}
        onClick={scrollNext}
      >
        <ChevronRight className="w-4 h-4" />
      </button>
    </div>
  );
}
