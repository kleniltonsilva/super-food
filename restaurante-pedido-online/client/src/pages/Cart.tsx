import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Trash2, Plus, Minus } from "lucide-react";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState } from "react";

export default function Cart() {
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();
  const [isCheckingOut, setIsCheckingOut] = useState(false);

  const cartItemsQuery = trpc.cart.getItems.useQuery();
  const updateItemMutation = trpc.cart.updateItem.useMutation();
  const removeItemMutation = trpc.cart.removeItem.useMutation();
  const clearCartMutation = trpc.cart.clear.useMutation();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <p className="text-center text-muted-foreground">
            Faça login para ver seu carrinho
          </p>
        </div>
      </div>
    );
  }

  const cartItems = cartItemsQuery.data || [];
  const subtotal = cartItems.reduce(
    (sum, item) => sum + parseFloat(item.unitPrice) * item.quantity,
    0
  );

  const handleUpdateQuantity = async (cartItemId: number, newQuantity: number) => {
    if (newQuantity < 1) return;

    try {
      await updateItemMutation.mutateAsync({
        cartItemId,
        quantity: newQuantity,
      });
      cartItemsQuery.refetch();
    } catch (error) {
      toast.error("Erro ao atualizar quantidade");
    }
  };

  const handleRemoveItem = async (cartItemId: number) => {
    try {
      await removeItemMutation.mutateAsync({ cartItemId });
      cartItemsQuery.refetch();
      toast.success("Item removido do carrinho");
    } catch (error) {
      toast.error("Erro ao remover item");
    }
  };

  const handleClearCart = async () => {
    if (!confirm("Tem certeza que deseja limpar o carrinho?")) return;

    try {
      await clearCartMutation.mutateAsync();
      cartItemsQuery.refetch();
      toast.success("Carrinho limpo");
    } catch (error) {
      toast.error("Erro ao limpar carrinho");
    }
  };

  const handleCheckout = () => {
    if (cartItems.length === 0) {
      toast.error("Carrinho vazio");
      return;
    }
    setIsCheckingOut(true);
    navigate("/checkout");
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Meu Carrinho</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Cart Items */}
          <div className="lg:col-span-2">
            {cartItemsQuery.isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <Card key={i} className="p-4 animate-pulse">
                    <div className="h-20 bg-muted rounded" />
                  </Card>
                ))}
              </div>
            ) : cartItems.length === 0 ? (
              <Card className="p-8 text-center">
                <p className="text-muted-foreground mb-4">
                  Seu carrinho está vazio
                </p>
                <Button onClick={() => navigate("/")}>
                  Voltar ao Cardápio
                </Button>
              </Card>
            ) : (
              <div className="space-y-4">
                {cartItems.map((item) => (
                  <Card key={item.id} className="cart-item">
                    <div className="cart-item-image">
                      <div className="w-full h-full flex items-center justify-center text-3xl bg-muted">
                        🍕
                      </div>
                    </div>
                    <div className="cart-item-info">
                      <h3 className="cart-item-name">Produto #{item.productId}</h3>
                      {item.customizationNotes && (
                        <p className="text-xs text-muted-foreground mb-1">
                          {item.customizationNotes}
                        </p>
                      )}
                      <p className="cart-item-price">
                        R$ {parseFloat(item.unitPrice).toFixed(2)}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="quantity-selector">
                        <button
                          className="quantity-btn"
                          onClick={() =>
                            handleUpdateQuantity(item.id, item.quantity - 1)
                          }
                          disabled={updateItemMutation.isPending}
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span className="px-4 py-1 font-bold">
                          {item.quantity}
                        </span>
                        <button
                          className="quantity-btn"
                          onClick={() =>
                            handleUpdateQuantity(item.id, item.quantity + 1)
                          }
                          disabled={updateItemMutation.isPending}
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveItem(item.id)}
                        disabled={removeItemMutation.isPending}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </Card>
                ))}

                {cartItems.length > 0 && (
                  <Button
                    variant="outline"
                    className="w-full text-red-600 hover:text-red-700"
                    onClick={handleClearCart}
                    disabled={clearCartMutation.isPending}
                  >
                    Limpar Carrinho
                  </Button>
                )}
              </div>
            )}
          </div>

          {/* Summary */}
          <div>
            <Card className="checkout-section sticky top-20">
              <h2 className="text-xl font-bold mb-4">Resumo</h2>

              <div className="space-y-3 mb-4 pb-4 border-b border-border">
                <div className="flex items-center justify-between">
                  <span>Subtotal:</span>
                  <span className="font-bold">
                    R$ {subtotal.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Entrega:</span>
                  <span className="font-bold">A calcular</span>
                </div>
              </div>

              <div className="flex items-center justify-between mb-6 text-lg">
                <span className="font-bold">Total:</span>
                <span className="text-accent font-bold">
                  R$ {subtotal.toFixed(2)}
                </span>
              </div>

              <Button
                onClick={handleCheckout}
                disabled={cartItems.length === 0 || isCheckingOut}
                className="w-full bg-accent hover:bg-accent/90 text-white"
              >
                {isCheckingOut ? "Processando..." : "Ir para Checkout"}
              </Button>

              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => navigate("/")}
              >
                Continuar Comprando
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
