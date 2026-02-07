import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Clock, MapPin, CreditCard } from "lucide-react";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";

const statusLabels: Record<string, string> = {
  pending: "Pendente",
  confirmed: "Confirmado",
  preparing: "Preparando",
  ready: "Pronto",
  delivering: "Entregando",
  delivered: "Entregue",
  cancelled: "Cancelado",
};

const statusColors: Record<string, string> = {
  pending: "status-pending",
  confirmed: "status-confirmed",
  preparing: "status-preparing",
  ready: "status-ready",
  delivered: "status-delivered",
  cancelled: "status-delivered",
};

export default function Orders() {
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();

  const ordersQuery = trpc.orders.getUserOrders.useQuery();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <p className="text-center text-muted-foreground">
            Faça login para ver seus pedidos
          </p>
        </div>
      </div>
    );
  }

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

        <h1 className="text-3xl font-bold mb-8">Meus Pedidos</h1>

        {ordersQuery.isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="p-6 animate-pulse">
                <div className="h-20 bg-muted rounded" />
              </Card>
            ))}
          </div>
        ) : ordersQuery.data && ordersQuery.data.length > 0 ? (
          <div className="space-y-4">
            {ordersQuery.data.map((order) => (
              <Card key={order.id} className="p-6 hover:shadow-lg transition-all">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">
                      Número do Pedido
                    </p>
                    <p className="font-bold text-lg">{order.orderNumber}</p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Status</p>
                    <span className={`status-badge ${statusColors[order.status]}`}>
                      {statusLabels[order.status]}
                    </span>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Total</p>
                    <p className="font-bold text-lg text-accent">
                      R$ {parseFloat(order.total).toFixed(2)}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Data</p>
                    <p className="font-bold">
                      {new Date(order.createdAt).toLocaleDateString("pt-BR")}
                    </p>
                  </div>
                </div>

                <div className="border-t border-border pt-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span>
                      {order.deliveryType === "delivery"
                        ? `Entrega em ${order.estimatedDeliveryTime || 50} min`
                        : "Retirada na loja"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-sm">
                    <CreditCard className="w-4 h-4 text-muted-foreground" />
                    <span>
                      {order.paymentMethod === "cash"
                        ? "Dinheiro"
                        : order.paymentMethod === "credit_card"
                        ? "Cartão de Crédito"
                        : order.paymentMethod === "debit_card"
                        ? "Cartão de Débito"
                        : order.paymentMethod === "pix"
                        ? "PIX"
                        : "Voucher"}
                    </span>
                  </div>

                  {order.deliveryType === "delivery" && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-muted-foreground" />
                      <span>Entrega agendada</span>
                    </div>
                  )}
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="mt-4"
                  onClick={() => navigate(`/order/${order.id}`)}
                >
                  Ver Detalhes
                </Button>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground mb-4">
              Você ainda não tem pedidos
            </p>
            <Button onClick={() => navigate("/")}>
              Fazer um Pedido
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}
