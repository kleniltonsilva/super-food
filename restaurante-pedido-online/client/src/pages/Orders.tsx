/**
 * Orders.tsx — Página "Meus Pedidos".
 *
 * Usa React Query (useMeusPedidos) com staleTime 1min.
 * Dados em cache → navegação de volta para Orders é instantânea.
 * Revalida automaticamente ao focar na aba (refetchOnWindowFocus).
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Clock, MapPin, CreditCard } from "lucide-react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useMeusPedidos } from "@/hooks/useQueries";

const statusLabels: Record<string, string> = {
  pendente: "Pendente",
  confirmado: "Confirmado",
  preparando: "Preparando",
  pronto: "Pronto",
  em_rota: "Entregando",
  entregue: "Entregue",
  cancelado: "Cancelado",
};

const statusColors: Record<string, string> = {
  pendente: "bg-yellow-100 text-yellow-800",
  confirmado: "bg-blue-100 text-blue-800",
  preparando: "bg-orange-100 text-orange-800",
  pronto: "bg-green-100 text-green-800",
  em_rota: "bg-purple-100 text-purple-800",
  entregue: "bg-gray-100 text-gray-800",
  cancelado: "bg-red-100 text-red-800",
};

interface Pedido {
  id: number;
  comanda: string | null;
  status: string;
  tipo: string | null;
  tipo_entrega: string | null;
  endereco_entrega: string | null;
  valor_total: number;
  forma_pagamento: string | null;
  observacoes: string | null;
  data_criacao: string;
  itens_texto: string | null;
  carrinho_json: any[] | null;
}

export default function Orders() {
  const [, navigate] = useLocation();
  const { isLoggedIn } = useAuth();
  const { siteInfo } = useRestaurante();

  // React Query: cache 1min, enabled só quando logado
  const { data: pedidos = [], isLoading: loading } = useMeusPedidos(isLoggedIn);

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <Card className="p-8 text-center">
            <p className="text-muted-foreground mb-4">
              Faça login para ver seus pedidos
            </p>
            <Button
              onClick={() => navigate("/login")}
              style={{ background: `var(--cor-primaria, #E31A24)` }}
              className="text-white"
            >
              Fazer Login
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Meus Pedidos</h1>

        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map(i => (
              <Card key={i} className="p-6 animate-pulse">
                <div className="h-20 bg-muted rounded" />
              </Card>
            ))}
          </div>
        ) : pedidos.length > 0 ? (
          <div className="space-y-4">
            {pedidos.map((pedido: Pedido) => (
              <Card key={pedido.id} className="p-6 hover:shadow-lg transition-all">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Pedido</p>
                    <p className="font-bold text-lg">#{pedido.comanda || pedido.id}</p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Status</p>
                    <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold ${statusColors[pedido.status] || "bg-gray-100 text-gray-800"}`}>
                      {statusLabels[pedido.status] || pedido.status}
                    </span>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Total</p>
                    <p className="font-bold text-lg" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                      R$ {pedido.valor_total.toFixed(2)}
                    </p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-1">Data</p>
                    <p className="font-bold">
                      {new Date(pedido.data_criacao).toLocaleDateString("pt-BR")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(pedido.data_criacao).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
                    </p>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="w-4 h-4 text-muted-foreground" />
                    <span>
                      {pedido.tipo_entrega === "retirada"
                        ? `Retirada na loja (~${siteInfo?.tempo_retirada_estimado || 20} min)`
                        : `Entrega (~${siteInfo?.tempo_entrega_estimado || 50} min)`}
                    </span>
                  </div>

                  {pedido.forma_pagamento && (
                    <div className="flex items-center gap-2 text-sm">
                      <CreditCard className="w-4 h-4 text-muted-foreground" />
                      <span>{pedido.forma_pagamento}</span>
                    </div>
                  )}

                  {pedido.endereco_entrega && (
                    <div className="flex items-center gap-2 text-sm">
                      <MapPin className="w-4 h-4 text-muted-foreground" />
                      <span className="truncate">{pedido.endereco_entrega}</span>
                    </div>
                  )}

                  {/* Itens do pedido */}
                  {pedido.carrinho_json && pedido.carrinho_json.length > 0 && (
                    <div className="mt-3 pt-3 border-t">
                      <p className="text-xs font-bold text-muted-foreground mb-2">ITENS:</p>
                      <div className="space-y-1">
                        {pedido.carrinho_json.map((item: any, idx: number) => (
                          <div key={idx} className="flex justify-between text-sm">
                            <span>{item.quantidade}x {item.nome}</span>
                            <span className="font-bold">R$ {item.subtotal?.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Botão acompanhar */}
                  {!["entregue", "finalizado", "cancelado"].includes(pedido.status) && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="mt-3"
                      onClick={() => navigate(`/order/${pedido.id}`)}
                      style={{ borderColor: `var(--cor-primaria, #E31A24)`, color: `var(--cor-primaria, #E31A24)` }}
                    >
                      Acompanhar Pedido
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card className="p-8 text-center">
            <p className="text-muted-foreground mb-4">
              Você ainda não tem pedidos
            </p>
            <Button onClick={() => navigate("/")} style={{ background: `var(--cor-primaria, #E31A24)` }} className="text-white">
              Fazer um Pedido
            </Button>
          </Card>
        )}
      </div>
    </div>
  );
}
