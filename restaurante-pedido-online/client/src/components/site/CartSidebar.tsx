/**
 * CartSidebar.tsx — Carrinho lateral temático.
 *
 * Desktop: sidebar direita fixa (~33% width), visível quando há itens.
 * Mobile: Sheet/drawer deslizante pela direita.
 *
 * Usa React Query (useCarrinho) e mutations para atualizar/remover itens.
 * Cores de quantidade: #ff0d0d (decrease) e #00b400 (increase) via themeConfig.
 */

import { useState } from "react";
import { ShoppingCart, Minus, Plus, Trash2, X, ShoppingBag } from "lucide-react";
import { useLocation } from "wouter";
import { useCarrinho, useAtualizarQuantidade, useRemoverCarrinho, useLimparCarrinho } from "@/hooks/useQueries";
import { useRestaurante, useRestauranteTheme } from "@/contexts/RestauranteContext";
import { toast } from "sonner";

interface CartItem {
  produto_id: number;
  nome: string;
  imagem_url: string | null;
  variacoes: { id: number; nome: string }[];
  observacoes: string | null;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

interface CartSidebarProps {
  /** Controle externo do Sheet mobile */
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export default function CartSidebar({ open, onOpenChange }: CartSidebarProps) {
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const theme = useRestauranteTheme();
  const [updating, setUpdating] = useState(false);

  const { data: carrinho, isLoading } = useCarrinho();
  const updateQtyMutation = useAtualizarQuantidade();
  const removeMutation = useRemoverCarrinho();
  const clearMutation = useLimparCarrinho();

  const cartItems: CartItem[] = carrinho?.itens_json || carrinho?.itens || [];
  const subtotal = carrinho?.valor_subtotal || cartItems.reduce((s, i) => s + i.subtotal, 0);
  const itemCount = cartItems.reduce((sum, i) => sum + (i.quantidade || 1), 0);

  const handleUpdateQty = async (index: number, newQty: number) => {
    if (newQty < 1) return;
    setUpdating(true);
    try {
      await updateQtyMutation.mutateAsync({ itemIndex: index, quantidade: newQty });
    } catch {
      toast.error("Erro ao atualizar quantidade");
    } finally {
      setUpdating(false);
    }
  };

  const handleRemove = async (index: number) => {
    setUpdating(true);
    try {
      await removeMutation.mutateAsync(index);
      toast.success("Item removido");
    } catch {
      toast.error("Erro ao remover item");
    } finally {
      setUpdating(false);
    }
  };

  const handleClear = async () => {
    if (!confirm("Tem certeza que deseja limpar o carrinho?")) return;
    setUpdating(true);
    try {
      await clearMutation.mutateAsync();
      toast.success("Carrinho limpo");
    } catch {
      toast.error("Erro ao limpar carrinho");
    } finally {
      setUpdating(false);
    }
  };

  const handleCheckout = () => {
    onOpenChange(false);
    navigate("/checkout");
  };

  const pedidoMinimo = siteInfo?.pedido_minimo || 0;
  const abaixoMinimo = pedidoMinimo > 0 && subtotal < pedidoMinimo;

  // ─── Conteúdo interno do carrinho (compartilhado desktop/mobile) ───
  const cartContent = (
    <div className="flex flex-col h-full">
      {/* Header com gradiente do tema */}
      <div
        className="flex items-center justify-between px-4 py-3 flex-shrink-0"
        style={{
          background: `linear-gradient(135deg, ${theme.colors.primary}, ${theme.colors.secondary})`,
          color: "#fff",
        }}
      >
        <div className="flex items-center gap-2">
          <ShoppingBag className="w-5 h-5" />
          <span className="font-bold text-base" style={{ fontFamily: theme.fonts.heading }}>
            Meu Pedido
          </span>
          {itemCount > 0 && (
            <span className="bg-white/20 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              {itemCount} {itemCount === 1 ? "item" : "itens"}
            </span>
          )}
        </div>
        {/* Botão fechar só mobile */}
        <button
          className="lg:hidden p-1 rounded-full hover:bg-white/20 transition-colors"
          onClick={() => onOpenChange(false)}
        >
          <X className="w-5 h-5" />
        </button>
        {/* Limpar carrinho desktop */}
        {cartItems.length > 0 && (
          <button
            className="hidden lg:flex items-center gap-1 text-xs text-white/80 hover:text-white transition-colors"
            onClick={handleClear}
            disabled={updating}
          >
            <Trash2 className="w-3 h-3" />
            Limpar
          </button>
        )}
      </div>

      {/* Lista de itens */}
      <div className="flex-1 overflow-y-auto px-3 py-2" style={{ background: theme.colors.cardBg }}>
        {isLoading ? (
          <div className="space-y-3 py-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="animate-pulse rounded-lg p-3" style={{ background: theme.colors.borderSubtle }}>
                <div className="h-12" />
              </div>
            ))}
          </div>
        ) : cartItems.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <ShoppingCart className="w-12 h-12 mb-3" style={{ color: theme.colors.textMuted }} />
            <p className="text-sm font-medium" style={{ color: theme.colors.textSecondary }}>
              Seu carrinho está vazio
            </p>
            <p className="text-xs mt-1" style={{ color: theme.colors.textMuted }}>
              Adicione itens do cardápio
            </p>
          </div>
        ) : (
          <div className="space-y-2 py-1">
            {cartItems.map((item, index) => (
              <div
                key={index}
                className="flex items-start gap-2 p-2 rounded-lg transition-colors"
                style={{
                  background: theme.isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.02)",
                  border: `1px solid ${theme.colors.borderSubtle}`,
                }}
              >
                {/* Imagem */}
                <div
                  className="w-12 h-12 rounded-lg flex-shrink-0 flex items-center justify-center text-lg overflow-hidden"
                  style={{ background: theme.isDark ? "rgba(255,255,255,0.06)" : "#f0f0f0" }}
                >
                  {item.imagem_url ? (
                    <img src={item.imagem_url} alt={item.nome} className="w-full h-full object-cover" />
                  ) : (
                    "\u{1F37D}\uFE0F"
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-bold truncate" style={{ color: theme.colors.textPrimary }}>
                    {item.nome}
                  </p>
                  {/* Sabores de pizza */}
                  {item.observacoes && item.observacoes.startsWith("Sabores:") ? (() => {
                    const saboresStr = (item.observacoes as string).replace("Sabores:", "").split("|")[0].trim();
                    const sabores = saboresStr.split("/").map((s: string) => s.trim()).filter(Boolean);
                    return sabores.length > 1 ? (
                      <div className="space-y-0">
                        {sabores.map((s: string, si: number) => (
                          <p key={si} className="text-[10px]" style={{ color: theme.colors.textMuted }}>
                            1/{sabores.length} {s}
                          </p>
                        ))}
                      </div>
                    ) : null;
                  })() : null}
                  {item.variacoes && item.variacoes.length > 0 && (
                    <p className="text-[10px] truncate" style={{ color: theme.colors.textMuted }}>
                      {item.variacoes.map((v: { id: number; nome: string }) => v.nome).join(", ")}
                    </p>
                  )}
                  {item.observacoes && !item.observacoes.startsWith("Sabores:") && (
                    <p className="text-[10px] italic truncate" style={{ color: theme.colors.textMuted }}>
                      {item.observacoes}
                    </p>
                  )}
                  {/* Obs adicional após sabores (ex: "Sabores: X / Y | Sem cebola") */}
                  {item.observacoes && item.observacoes.startsWith("Sabores:") && item.observacoes.includes("|") && (
                    <p className="text-[10px] italic truncate" style={{ color: theme.colors.textMuted }}>
                      {(item.observacoes as string).split("|").slice(1).join("|").trim()}
                    </p>
                  )}

                  {/* Preço + controles quantidade */}
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs font-bold" style={{ color: theme.colors.priceColor }}>
                      R$ {item.subtotal.toFixed(2)}
                    </span>

                    <div className="flex items-center gap-0.5">
                      {/* Botão - (decrease) */}
                      <button
                        className="w-6 h-6 rounded flex items-center justify-center text-white transition-opacity disabled:opacity-40"
                        style={{ background: theme.colors.quantityDecrease }}
                        onClick={() => item.quantidade <= 1 ? handleRemove(index) : handleUpdateQty(index, item.quantidade - 1)}
                        disabled={updating}
                      >
                        {item.quantidade <= 1 ? <Trash2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                      </button>

                      <span
                        className="w-7 text-center text-xs font-bold"
                        style={{ color: theme.colors.textPrimary }}
                      >
                        {item.quantidade}
                      </span>

                      {/* Botão + (increase) */}
                      <button
                        className="w-6 h-6 rounded flex items-center justify-center text-white transition-opacity disabled:opacity-40"
                        style={{ background: theme.colors.quantityIncrease }}
                        onClick={() => handleUpdateQty(index, item.quantidade + 1)}
                        disabled={updating}
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Limpar carrinho - mobile */}
            <button
              className="lg:hidden w-full text-xs py-2 rounded-lg transition-colors"
              style={{
                color: theme.colors.quantityDecrease,
                border: `1px solid ${theme.colors.borderSubtle}`,
                background: "transparent",
              }}
              onClick={handleClear}
              disabled={updating}
            >
              Limpar Carrinho
            </button>
          </div>
        )}
      </div>

      {/* Footer: resumo + botão finalizar */}
      {cartItems.length > 0 && (
        <div
          className="flex-shrink-0 px-4 py-3 space-y-2"
          style={{
            background: theme.colors.cardBg,
            borderTop: `1px solid ${theme.colors.borderSubtle}`,
          }}
        >
          {/* Subtotal */}
          <div className="flex items-center justify-between text-sm">
            <span style={{ color: theme.colors.textSecondary }}>Subtotal</span>
            <span className="font-bold" style={{ color: theme.colors.textPrimary }}>
              R$ {subtotal.toFixed(2)}
            </span>
          </div>

          {/* Entrega */}
          <div className="flex items-center justify-between text-sm">
            <span style={{ color: theme.colors.textSecondary }}>Entrega</span>
            <span className="text-xs" style={{ color: theme.colors.textMuted }}>A calcular</span>
          </div>

          {/* Separador */}
          <div className="border-t pt-2" style={{ borderColor: theme.colors.borderSubtle }}>
            <div className="flex items-center justify-between">
              <span className="font-bold text-sm" style={{ color: theme.colors.textPrimary }}>Total</span>
              <span className="font-bold text-lg" style={{ color: theme.colors.priceColor }}>
                R$ {subtotal.toFixed(2)}
              </span>
            </div>
          </div>

          {/* Aviso pedido mínimo */}
          {abaixoMinimo && (
            <p className="text-xs text-center py-1 px-2 rounded" style={{
              background: "rgba(234, 179, 8, 0.1)",
              color: theme.isDark ? "#FACC15" : "#B45309",
            }}>
              Pedido mínimo: R$ {pedidoMinimo.toFixed(2)}
            </p>
          )}

          {/* Botão finalizar */}
          <button
            className="w-full font-bold text-white text-sm rounded-lg transition-opacity disabled:opacity-50"
            style={{
              background: "#00b400",
              borderBottom: "3px solid #009a00",
              height: "48px",
            }}
            onClick={handleCheckout}
            disabled={cartItems.length === 0 || updating}
          >
            Finalizar Pedido
          </button>

          {/* Continuar comprando */}
          <button
            className="w-full text-xs py-2 rounded-lg transition-colors"
            style={{
              color: theme.colors.textSecondary,
              border: `1px solid ${theme.colors.borderSubtle}`,
            }}
            onClick={() => onOpenChange(false)}
          >
            Continuar Comprando
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* ═══════ Desktop: sidebar fixa ═══════ */}
      <aside className="hidden lg:flex flex-col sticky top-[60px] h-[calc(100vh-60px)] w-full border-l"
        style={{
          background: theme.colors.cardBg,
          borderColor: theme.colors.borderSubtle,
        }}
      >
        {cartContent}
      </aside>

      {/* ═══════ Mobile: Sheet/drawer pela direita ═══════ */}
      {open && (
        <div className="lg:hidden fixed inset-0 z-50">
          {/* Overlay */}
          <div
            className="absolute inset-0 bg-black/50 animate-in fade-in-0 duration-300"
            onClick={() => onOpenChange(false)}
          />
          {/* Drawer */}
          <div
            className="absolute inset-y-0 right-0 w-[85%] max-w-sm flex flex-col shadow-xl animate-in slide-in-from-right duration-300"
            style={{ background: theme.colors.cardBg }}
          >
            {cartContent}
          </div>
        </div>
      )}
    </>
  );
}
