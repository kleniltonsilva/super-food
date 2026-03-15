/**
 * ProductCard.tsx — Card de produto temático.
 *
 * Adapta-se ao tipo:
 * - Pizzaria: imagem circular (placa pizza redonda)
 * - Hamburgueria: card escuro #303030
 * - Açaí: border-radius 28px
 * - Bebidas: border-radius 28px
 * - Salgados: border-radius 18px
 * - Sushi: card escuro, fonte cursiva
 * - Outros: border-radius 16px
 *
 * Inclui: badges (Destaque, Promo), hover lift, zoom imagem, preço, botão comprar.
 */

import { useRestauranteTheme } from "@/contexts/RestauranteContext";
import { Link } from "wouter";

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
  eh_pizza?: boolean;
  variacoes: Variacao[];
}

interface ProductCardProps {
  produto: Produto;
  emoji?: string;
  onPizzaBuilderOpen?: (produtoId: number) => void;
}

function getPrecoDisplay(produto: Produto): string {
  const tamanhos = produto.variacoes.filter(v => v.tipo_variacao === "tamanho");
  if (tamanhos.length > 0) {
    const precos = tamanhos.map(t => produto.preco + t.preco_adicional);
    const min = Math.min(...precos);
    const max = Math.max(...precos);
    if (min === max) return `R$ ${min.toFixed(2)}`;
    return `R$ ${min.toFixed(2)} ~ R$ ${max.toFixed(2)}`;
  }
  if (produto.promocao && produto.preco_promocional) {
    return `R$ ${produto.preco_promocional.toFixed(2)}`;
  }
  return `R$ ${produto.preco.toFixed(2)}`;
}

export default function ProductCard({ produto, emoji, onPizzaBuilderOpen }: ProductCardProps) {
  const theme = useRestauranteTheme();

  // Abre PizzaBuilder apenas para produtos marcados como pizza (eh_pizza flag)
  const hasPizzaBuilder = !!onPizzaBuilderOpen && (
    produto.eh_pizza ||
    produto.variacoes.some(v => (v.max_sabores || 0) > 1)
  );

  const cardStyle: React.CSSProperties = {
    background: theme.colors.cardBg,
    border: `1px solid ${theme.colors.cardBorder}`,
    borderRadius: theme.cardRadius,
    boxShadow: theme.colors.shadowCard,
  };

  const isCircular = theme.circularImages;

  const content = (
      <div
        className="cursor-pointer overflow-hidden h-full flex flex-col card-hover group"
        style={cardStyle}
      >
        {/* Imagem */}
        <div
          className="relative overflow-hidden flex items-center justify-center"
          style={{
            aspectRatio: "1",
            padding: isCircular ? "6px" : undefined,
            background: theme.isDark ? "rgba(255,255,255,0.04)" : "#f8f8f8",
          }}
        >
          {produto.imagem_url ? (
            <img
              src={produto.imagem_url}
              alt={produto.nome}
              className={isCircular ? "img-circular-zoom" : "img-zoom"}
              style={{
                width: isCircular ? "92%" : "100%",
                height: isCircular ? "auto" : "100%",
                aspectRatio: isCircular ? "1" : undefined,
                objectFit: "cover",
                borderRadius: isCircular ? "50%" : undefined,
              }}
            />
          ) : (
            <span className="text-5xl">{emoji || "\u{1F37D}\uFE0F"}</span>
          )}

          {/* Overlay gradiente no hover */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />

          {/* Badges */}
          {produto.destaque && (
            <span
              className="absolute top-2 left-2 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-lg"
              style={{ background: theme.colors.badgeColors.novidade }}
            >
              Destaque
            </span>
          )}
          {produto.promocao && (
            <span
              className="absolute top-2 right-2 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-lg"
              style={{ background: theme.colors.badgeColors.doChef }}
            >
              Promo
            </span>
          )}
        </div>

        {/* Info */}
        <div className="p-3 flex flex-col flex-1">
          <h4
            className="font-bold text-sm mb-1 line-clamp-1 uppercase"
            style={{
              color: theme.colors.textPrimary,
              fontFamily: theme.fonts.special || theme.fonts.heading,
            }}
          >
            {produto.nome}
          </h4>
          {produto.descricao && (
            <p
              className="text-xs mb-2 line-clamp-2 flex-1"
              style={{ color: theme.colors.textMuted }}
            >
              {produto.descricao}
            </p>
          )}

          {/* Separador */}
          <div
            className="my-2"
            style={{ borderTop: `1px solid ${theme.colors.borderSubtle}` }}
          />

          <div className="flex items-center justify-between mt-auto">
            <div className="flex flex-col">
              {produto.promocao && produto.preco_promocional && (
                <span
                  className="text-[10px] line-through"
                  style={{ color: theme.colors.textMuted }}
                >
                  R$ {produto.preco.toFixed(2)}
                </span>
              )}
              <span
                className="font-extrabold text-sm"
                style={{
                  color: theme.colors.priceColor,
                  fontFamily: theme.fonts.special || theme.fonts.heading,
                }}
              >
                {getPrecoDisplay(produto)}
              </span>
            </div>
            <span
              className="text-xs px-2.5 py-1.5 rounded-lg font-semibold text-white btn-press"
              style={{
                background: theme.colors.btnComprar,
                borderBottom: `3px solid ${theme.colors.btnComprarBorder}`,
                fontFamily: theme.fonts.special || undefined,
              }}
            >
              Comprar
            </span>
          </div>
        </div>
      </div>
  );

  if (hasPizzaBuilder) {
    return <div onClick={() => onPizzaBuilderOpen!(produto.id)}>{content}</div>;
  }

  return <Link href={`/product/${produto.id}`}>{content}</Link>;
}
