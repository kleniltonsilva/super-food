/**
 * Cart.tsx — Página do carrinho.
 *
 * Usa React Query (useCarrinho) com staleTime 30s para dados quase em tempo real.
 * Mutations (useAtualizarQuantidade, useRemoverCarrinho, useLimparCarrinho)
 * invalidam cache automaticamente após cada ação.
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Trash2, Plus, Minus } from "lucide-react";
import { useLocation } from "wouter";
import { useCarrinho, useAtualizarQuantidade, useRemoverCarrinho, useLimparCarrinho } from "@/hooks/useQueries";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { toast } from "sonner";
import { useState } from "react";

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

interface CarrinhoData {
  id: number;
  itens_json: CartItem[];
  valor_subtotal: number;
  valor_taxa_entrega: number;
  valor_desconto: number;
  valor_total: number;
}

export default function Cart() {
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const [updating, setUpdating] = useState(false);

  // React Query: cache automático com staleTime 30s, refetch ao montar
  const { data: carrinho, isLoading: loading } = useCarrinho();
  const updateQtyMutation = useAtualizarQuantidade();
  const removeMutation = useRemoverCarrinho();
  const clearMutation = useLimparCarrinho();

  const cartItems = carrinho?.itens_json || carrinho?.itens || [];
  const subtotal = carrinho?.valor_subtotal || cartItems.reduce((s: number, i: CartItem) => s + i.subtotal, 0);

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

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Meu Carrinho</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Itens */}
          <div className="lg:col-span-2">
            {loading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <Card key={i} className="p-4 animate-pulse">
                    <div className="h-20 bg-muted rounded" />
                  </Card>
                ))}
              </div>
            ) : cartItems.length === 0 ? (
              <Card className="p-8 text-center">
                <p className="text-muted-foreground mb-4">Seu carrinho está vazio</p>
                <Button onClick={() => navigate("/")}>Voltar ao Cardápio</Button>
              </Card>
            ) : (
              <div className="space-y-4">
                {cartItems.map((item: CartItem, index: number) => (
                  <Card key={index} className="p-4">
                    <div className="flex items-start gap-4">
                      <div className="w-16 h-16 bg-gray-100 rounded-lg flex items-center justify-center text-2xl flex-shrink-0">
                        {item.imagem_url ? (
                          <img src={item.imagem_url} alt={item.nome} className="w-full h-full object-cover rounded-lg" />
                        ) : (
                          "🍕"
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-bold text-sm">{item.nome}</h3>
                        {item.variacoes && item.variacoes.length > 0 && (
                          <p className="text-xs text-muted-foreground">
                            {item.variacoes.map((v: { id: number; nome: string }) => v.nome).join(", ")}
                          </p>
                        )}
                        {item.observacoes && (
                          <p className="text-xs text-muted-foreground italic">
                            Obs: {item.observacoes}
                          </p>
                        )}
                        <p className="font-bold mt-1" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                          R$ {item.preco_unitario.toFixed(2)}
                        </p>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center border rounded-lg overflow-hidden">
                          <button
                            className="px-2 py-1 hover:bg-gray-100"
                            onClick={() => handleUpdateQty(index, item.quantidade - 1)}
                            disabled={updating}
                          >
                            <Minus className="w-3 h-3" />
                          </button>
                          <span className="px-3 py-1 font-bold text-sm">{item.quantidade}</span>
                          <button
                            className="px-2 py-1 hover:bg-gray-100"
                            onClick={() => handleUpdateQty(index, item.quantidade + 1)}
                            disabled={updating}
                          >
                            <Plus className="w-3 h-3" />
                          </button>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemove(index)}
                          disabled={updating}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </Card>
                ))}

                <Button
                  variant="outline"
                  className="w-full text-red-600 hover:text-red-700"
                  onClick={handleClear}
                  disabled={updating}
                >
                  Limpar Carrinho
                </Button>
              </div>
            )}
          </div>

          {/* Resumo */}
          <div>
            <Card className="p-6 sticky top-20">
              <h2 className="text-xl font-bold mb-4">Resumo</h2>

              <div className="space-y-3 mb-4 pb-4 border-b">
                <div className="flex items-center justify-between">
                  <span>Subtotal:</span>
                  <span className="font-bold">R$ {subtotal.toFixed(2)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Entrega:</span>
                  <span className="font-bold">A calcular</span>
                </div>
              </div>

              <div className="flex items-center justify-between mb-6 text-lg">
                <span className="font-bold">Total:</span>
                <span className="font-bold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                  R$ {subtotal.toFixed(2)}
                </span>
              </div>

              {siteInfo && siteInfo.pedido_minimo > 0 && subtotal < siteInfo.pedido_minimo && (
                <p className="text-sm text-yellow-600 mb-4">
                  Pedido mínimo: R$ {siteInfo.pedido_minimo.toFixed(2)}
                </p>
              )}

              <Button
                onClick={() => navigate("/checkout")}
                disabled={cartItems.length === 0}
                className="w-full py-6 text-lg font-bold text-white"
                style={{ background: `var(--cor-primaria, #E31A24)` }}
              >
                Ir para Checkout
              </Button>

              <Button variant="outline" className="w-full mt-2" onClick={() => navigate("/")}>
                Continuar Comprando
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
