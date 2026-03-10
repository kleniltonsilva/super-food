/**
 * ComboDetailModal.tsx — Modal de detalhe do combo temático.
 *
 * Mostra imagem, itens inclusos, preço original vs combo, economia.
 * Botão de adicionar ao carrinho com cores do tema.
 */

import { useState } from "react";
import { X, ShoppingBag, Tag, Package } from "lucide-react";
import { adicionarComboAoCarrinho } from "@/lib/apiClient";
import { useRestauranteTheme } from "@/contexts/RestauranteContext";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/hooks/useQueries";
import { toast } from "sonner";

interface ComboItem {
  produto_id: number;
  produto_nome: string;
  quantidade: number;
  produto_imagem_url: string | null;
}

interface Combo {
  id: number;
  nome: string;
  descricao: string | null;
  preco_combo: number;
  preco_original: number;
  imagem_url: string | null;
  tipo_combo?: string;
  dia_semana?: number | null;
  quantidade_pessoas?: number | null;
  itens: ComboItem[];
}

interface ComboDetailModalProps {
  combo: Combo;
  onClose: () => void;
}

export default function ComboDetailModal({ combo, onClose }: ComboDetailModalProps) {
  const theme = useRestauranteTheme();
  const qc = useQueryClient();
  const [adding, setAdding] = useState(false);
  const [quantity, setQuantity] = useState(1);

  const economia = combo.preco_original - combo.preco_combo;
  const pct = combo.preco_original > 0 ? Math.round((economia / combo.preco_original) * 100) : 0;

  const handleAdd = async () => {
    setAdding(true);
    try {
      for (let i = 0; i < quantity; i++) {
        await adicionarComboAoCarrinho(combo.id);
      }
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
      toast.success(`${combo.nome} adicionado ao carrinho!`);
      onClose();
    } catch {
      toast.error("Erro ao adicionar combo");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
      {/* Overlay */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in-0 duration-200"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className="relative w-full max-w-lg max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 fade-in-0 duration-200"
        style={{
          background: theme.colors.cardBg,
          border: `2px solid ${theme.colors.primary}`,
          borderRadius: theme.cardRadius,
          boxShadow: "0 20px 60px rgba(0,0,0,0.4)",
        }}
      >
        {/* Header com imagem */}
        <div className="relative flex-shrink-0">
          <div
            className="w-full h-48 flex items-center justify-center overflow-hidden"
            style={{ background: theme.isDark ? "rgba(255,255,255,0.04)" : "#f0f0f0" }}
          >
            {combo.imagem_url ? (
              <img src={combo.imagem_url} alt={combo.nome} className="w-full h-full object-cover" />
            ) : (
              <span className="text-7xl">{"\u{1F381}"}</span>
            )}
          </div>

          {/* Badge economia */}
          {pct > 0 && (
            <span
              className="absolute top-3 left-3 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1"
              style={{ background: theme.colors.primary }}
            >
              <Tag className="w-3 h-3" />
              -{pct}% OFF
            </span>
          )}

          {/* Badge Kit Festa */}
          {combo.tipo_combo === "kit_festa" && combo.quantidade_pessoas && (
            <span
              className="absolute top-3 left-3 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1"
              style={{ background: "#7c3aed", top: pct > 0 ? "40px" : "12px" }}
            >
              Para {combo.quantidade_pessoas} pessoas
            </span>
          )}

          {/* Botão fechar */}
          <button
            className="absolute top-3 right-3 w-8 h-8 rounded-full flex items-center justify-center transition-colors"
            style={{
              background: "rgba(0,0,0,0.5)",
              color: "#fff",
            }}
            onClick={onClose}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Conteúdo */}
        <div className="flex-1 overflow-y-auto px-5 py-4">
          <h2
            className="text-xl font-bold mb-1"
            style={{
              color: theme.colors.textPrimary,
              fontFamily: theme.fonts.special || theme.fonts.heading,
            }}
          >
            {combo.nome}
          </h2>

          {combo.descricao && (
            <p className="text-sm mb-4" style={{ color: theme.colors.textMuted }}>
              {combo.descricao}
            </p>
          )}

          {/* Itens do combo */}
          <div className="mb-4">
            <h3
              className="text-sm font-bold mb-2 flex items-center gap-2"
              style={{ color: theme.colors.textSecondary }}
            >
              <Package className="w-4 h-4" />
              O que vem no combo:
            </h3>
            <div className="space-y-2">
              {combo.itens.map((item, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 p-2.5 rounded-lg"
                  style={{
                    background: theme.isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.02)",
                    border: `1px solid ${theme.colors.borderSubtle}`,
                  }}
                >
                  <div
                    className="w-10 h-10 rounded-lg flex-shrink-0 flex items-center justify-center overflow-hidden"
                    style={{ background: theme.isDark ? "rgba(255,255,255,0.06)" : "#f0f0f0" }}
                  >
                    {item.produto_imagem_url ? (
                      <img src={item.produto_imagem_url} alt={item.produto_nome} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-lg">{"\u{1F37D}\uFE0F"}</span>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <span className="text-sm font-medium" style={{ color: theme.colors.textPrimary }}>
                      {item.quantidade}x {item.produto_nome}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Preços */}
          <div
            className="rounded-lg p-3"
            style={{
              background: theme.isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)",
              border: `1px solid ${theme.colors.borderSubtle}`,
            }}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm" style={{ color: theme.colors.textMuted }}>Preço original:</span>
              <span className="text-sm line-through" style={{ color: theme.colors.textMuted }}>
                R$ {combo.preco_original.toFixed(2)}
              </span>
            </div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-bold" style={{ color: theme.colors.textPrimary }}>Preço combo:</span>
              <span
                className="text-lg font-extrabold"
                style={{ color: theme.colors.priceColor, fontFamily: theme.fonts.special || theme.fonts.heading }}
              >
                R$ {combo.preco_combo.toFixed(2)}
              </span>
            </div>
            {economia > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: theme.colors.quantityIncrease }}>Economia:</span>
                <span className="text-sm font-bold" style={{ color: theme.colors.quantityIncrease }}>
                  R$ {economia.toFixed(2)}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Footer: quantidade + botão */}
        <div
          className="flex-shrink-0 px-5 py-4 flex items-center gap-3"
          style={{ borderTop: `1px solid ${theme.colors.borderSubtle}` }}
        >
          {/* Controle quantidade */}
          <div className="flex items-center rounded-lg overflow-hidden" style={{ border: `1px solid ${theme.colors.borderSubtle}` }}>
            <button
              className="w-9 h-9 flex items-center justify-center text-white"
              style={{ background: theme.colors.quantityDecrease }}
              onClick={() => setQuantity(Math.max(1, quantity - 1))}
            >
              <span className="text-lg font-bold">-</span>
            </button>
            <span
              className="w-10 text-center font-bold text-sm"
              style={{ color: theme.colors.textPrimary }}
            >
              {quantity}
            </span>
            <button
              className="w-9 h-9 flex items-center justify-center text-white"
              style={{ background: theme.colors.quantityIncrease }}
              onClick={() => setQuantity(quantity + 1)}
            >
              <span className="text-lg font-bold">+</span>
            </button>
          </div>

          {/* Botão adicionar */}
          <button
            className="flex-1 flex items-center justify-center gap-2 font-bold text-white text-sm rounded-lg transition-opacity disabled:opacity-50"
            style={{
              background: "#00b400",
              borderBottom: "3px solid #009a00",
              height: "48px",
            }}
            onClick={handleAdd}
            disabled={adding}
          >
            <ShoppingBag className="w-4 h-4" />
            {adding ? "Adicionando..." : `Adicionar - R$ ${(combo.preco_combo * quantity).toFixed(2)}`}
          </button>
        </div>
      </div>
    </div>
  );
}
