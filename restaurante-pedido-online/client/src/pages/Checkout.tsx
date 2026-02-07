import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, MapPin, CreditCard } from "lucide-react";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState } from "react";

type PaymentMethod = "cash" | "credit_card" | "debit_card" | "pix" | "voucher";
type DeliveryType = "delivery" | "pickup";

export default function Checkout() {
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();

  const [deliveryType, setDeliveryType] = useState<DeliveryType>("delivery");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("pix");
  const [selectedAddressId, setSelectedAddressId] = useState<number | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const cartItemsQuery = trpc.cart.getItems.useQuery();
  const addressesQuery = trpc.delivery.getAddresses.useQuery();
  const neighborhoodsQuery = trpc.delivery.getNeighborhoods.useQuery();
  const createOrderMutation = trpc.orders.create.useMutation();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <p className="text-center text-muted-foreground">
            Faça login para fazer checkout
          </p>
        </div>
      </div>
    );
  }

  const cartItems = cartItemsQuery.data || [];
  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button
            variant="ghost"
            onClick={() => navigate("/cart")}
            className="mb-4"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <p className="text-center text-muted-foreground">
            Seu carrinho está vazio
          </p>
        </div>
      </div>
    );
  }

  const subtotal = cartItems.reduce(
    (sum, item) => sum + parseFloat(item.unitPrice) * item.quantity,
    0
  );

  const deliveryFee = deliveryType === "pickup" ? 0 : 5.0;
  const total = subtotal + deliveryFee;

  const handlePlaceOrder = async () => {
    if (deliveryType === "delivery" && !selectedAddressId) {
      toast.error("Selecione um endereço de entrega");
      return;
    }

    setIsProcessing(true);

    try {
      await createOrderMutation.mutateAsync({
        deliveryType,
        paymentMethod,
        subtotal: subtotal.toFixed(2),
        deliveryFee: deliveryFee.toFixed(2),
        discount: "0.00",
        total: total.toFixed(2),
        deliveryAddressId: deliveryType === "delivery" ? selectedAddressId || undefined : undefined,
        estimatedDeliveryTime: 50,
        items: cartItems.map((item) => ({
          productId: item.productId,
          quantity: item.quantity,
          unitPrice: item.unitPrice,
          subtotal: (parseFloat(item.unitPrice) * item.quantity).toFixed(2),
          sizeId: item.sizeId || undefined,
          selectedFlavors: item.selectedFlavors.length > 0 ? item.selectedFlavors : undefined,
          customizationNotes: item.customizationNotes || undefined,
        })),
      });

      toast.success("Pedido realizado com sucesso!");
      navigate("/orders");
    } catch (error) {
      toast.error("Erro ao realizar pedido");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/cart")}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Checkout</h1>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Checkout Form */}
          <div className="lg:col-span-2 space-y-6">
            {/* Delivery Type */}
            <Card className="checkout-section">
              <h2 className="text-xl font-bold mb-4">Tipo de Entrega</h2>
              <div className="space-y-3">
                <label className="payment-option cursor-pointer">
                  <input
                    type="radio"
                    name="delivery"
                    value="delivery"
                    checked={deliveryType === "delivery"}
                    onChange={(e) => setDeliveryType(e.target.value as DeliveryType)}
                  />
                  <div>
                    <div className="font-bold">Entrega em Casa</div>
                    <div className="text-sm text-muted-foreground">
                      Taxa: R$ {deliveryFee.toFixed(2)}
                    </div>
                  </div>
                </label>

                <label className="payment-option cursor-pointer">
                  <input
                    type="radio"
                    name="delivery"
                    value="pickup"
                    checked={deliveryType === "pickup"}
                    onChange={(e) => setDeliveryType(e.target.value as DeliveryType)}
                  />
                  <div>
                    <div className="font-bold">Retirada na Loja</div>
                    <div className="text-sm text-muted-foreground">
                      Sem taxa de entrega
                    </div>
                  </div>
                </label>
              </div>
            </Card>

            {/* Address Selection */}
            {deliveryType === "delivery" && (
              <Card className="checkout-section">
                <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Endereço de Entrega
                </h2>
                <div className="space-y-3">
                  {addressesQuery.data?.map((address) => (
                    <label
                      key={address.id}
                      className="payment-option cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="address"
                        value={address.id}
                        checked={selectedAddressId === address.id}
                        onChange={() => setSelectedAddressId(address.id)}
                      />
                      <div>
                        <div className="font-bold">
                          {address.street}, {address.number}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {address.neighborhood} - {address.city}, {address.state}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </Card>
            )}

            {/* Payment Method */}
            <Card className="checkout-section">
              <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Forma de Pagamento
              </h2>
              <div className="space-y-3">
                {[
                  { value: "pix", label: "PIX" },
                  { value: "cash", label: "Dinheiro" },
                  { value: "credit_card", label: "Cartão de Crédito" },
                  { value: "debit_card", label: "Cartão de Débito" },
                  { value: "voucher", label: "Voucher" },
                ].map((method) => (
                  <label
                    key={method.value}
                    className="payment-option cursor-pointer"
                  >
                    <input
                      type="radio"
                      name="payment"
                      value={method.value}
                      checked={paymentMethod === method.value}
                      onChange={() => setPaymentMethod(method.value as PaymentMethod)}
                    />
                    <span className="font-bold">{method.label}</span>
                  </label>
                ))}
              </div>
            </Card>
          </div>

          {/* Order Summary */}
          <div>
            <Card className="checkout-section sticky top-20">
              <h2 className="text-xl font-bold mb-4">Resumo do Pedido</h2>

              <div className="space-y-3 mb-4 pb-4 border-b border-border max-h-64 overflow-y-auto">
                {cartItems.map((item) => (
                  <div key={item.id} className="flex items-center justify-between text-sm">
                    <span>
                      Produto #{item.productId} x{item.quantity}
                    </span>
                    <span className="font-bold">
                      R$ {(parseFloat(item.unitPrice) * item.quantity).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 mb-4 pb-4 border-b border-border">
                <div className="flex items-center justify-between">
                  <span>Subtotal:</span>
                  <span className="font-bold">R$ {subtotal.toFixed(2)}</span>
                </div>
                {deliveryType === "delivery" && (
                  <div className="flex items-center justify-between">
                    <span>Entrega:</span>
                    <span className="font-bold">R$ {deliveryFee.toFixed(2)}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mb-6 text-lg">
                <span className="font-bold">Total:</span>
                <span className="text-accent font-bold">
                  R$ {total.toFixed(2)}
                </span>
              </div>

              <Button
                onClick={handlePlaceOrder}
                disabled={isProcessing || createOrderMutation.isPending}
                className="w-full bg-accent hover:bg-accent/90 text-white py-6 text-lg"
              >
                {isProcessing ? "Processando..." : "Confirmar Pedido"}
              </Button>

              <Button
                variant="outline"
                className="w-full mt-2"
                onClick={() => navigate("/cart")}
                disabled={isProcessing}
              >
                Voltar ao Carrinho
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
