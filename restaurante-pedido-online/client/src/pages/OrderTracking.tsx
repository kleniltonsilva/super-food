import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Check, Clock, Truck, ChefHat, Package } from "lucide-react";
import { useParams, useLocation } from "wouter";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { getTrackingPedido } from "@/lib/apiClient";
import { useState, useEffect, useRef } from "react";
import MapTracking from "@/components/MapTracking";

interface TrackingData {
  id: number;
  comanda: string | null;
  status: string;
  tipo_entrega: string | null;
  endereco_entrega: string | null;
  latitude_entrega: number | null;
  longitude_entrega: number | null;
  valor_total: number;
  data_criacao: string | null;
  tempo_estimado: number | null;
  motoboy: { nome: string; latitude: number | null; longitude: number | null } | null;
  carrinho_json: any[] | null;
}

const STATUS_STEPS = [
  { key: "pendente", label: "Pedido Recebido", icon: Package },
  { key: "confirmado", label: "Confirmado", icon: Check },
  { key: "em_preparo", label: "Preparando", icon: ChefHat },
  { key: "pronto", label: "Pronto", icon: Check },
  { key: "saiu_entrega", label: "Saiu para Entrega", icon: Truck },
  { key: "entregue", label: "Entregue", icon: Check },
];

const STATUS_RETIRADA_STEPS = [
  { key: "pendente", label: "Pedido Recebido", icon: Package },
  { key: "confirmado", label: "Confirmado", icon: Check },
  { key: "em_preparo", label: "Preparando", icon: ChefHat },
  { key: "pronto", label: "Pronto para Retirada", icon: Check },
  { key: "finalizado", label: "Retirado", icon: Check },
];

function getStepIndex(status: string, steps: typeof STATUS_STEPS): number {
  const idx = steps.findIndex(s => s.key === status);
  return idx >= 0 ? idx : 0;
}

export default function OrderTracking() {
  const params = useParams();
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const pedidoId = parseInt(params?.id || "0");

  const [tracking, setTracking] = useState<TrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling mais rápido quando motoboy está em rota (10s) vs normal (30s)
  const isEmRota = tracking?.status === "saiu_entrega" && tracking?.motoboy?.latitude != null;

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getTrackingPedido(pedidoId);
        setTracking(data);
        setError(null);
      } catch {
        setError("Pedido não encontrado");
      } finally {
        setLoading(false);
      }
    }

    if (pedidoId) load();
  }, [pedidoId]);

  // Polling dinâmico: 10s quando mapa visível, 30s normal
  useEffect(() => {
    if (!pedidoId) return;
    const intervalo = isEmRota ? 10000 : 30000;

    intervalRef.current = setInterval(() => {
      getTrackingPedido(pedidoId)
        .then(data => { setTracking(data); setError(null); })
        .catch(() => {});
    }, intervalo);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [pedidoId, isEmRota]);

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Carregando pedido...</p>
      </div>
    );
  }

  if (error || !tracking) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <p className="text-center text-muted-foreground">{error || "Pedido não encontrado"}</p>
        </div>
      </div>
    );
  }

  const isRetirada = tracking.tipo_entrega === "retirada";
  const steps = isRetirada ? STATUS_RETIRADA_STEPS : STATUS_STEPS;
  const currentStep = getStepIndex(tracking.status, steps);
  const isCancelled = tracking.status === "cancelado";
  const isFinished = tracking.status === "entregue" || tracking.status === "finalizado";

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 max-w-2xl mx-auto">
        <Button variant="ghost" onClick={() => navigate("/orders")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Meus Pedidos
        </Button>

        <h1 className="text-2xl font-bold mb-2">
          Pedido #{tracking.comanda || tracking.id}
        </h1>
        {tracking.data_criacao && (
          <p className="text-sm text-muted-foreground mb-6">
            {new Date(tracking.data_criacao).toLocaleDateString("pt-BR")} às{" "}
            {new Date(tracking.data_criacao).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}

        {/* Status cancelado */}
        {isCancelled && (
          <Card className="p-6 mb-6 bg-red-50 border-red-200">
            <p className="text-red-700 font-bold text-lg">Pedido Cancelado</p>
            <p className="text-red-600 text-sm">Este pedido foi cancelado.</p>
          </Card>
        )}

        {/* Timeline */}
        {!isCancelled && (
          <Card className="p-6 mb-6">
            <h2 className="font-bold text-lg mb-6 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Acompanhamento
            </h2>
            <div className="space-y-0">
              {steps.map((step, idx) => {
                const isCompleted = idx <= currentStep;
                const isCurrent = idx === currentStep;
                const IconComponent = step.icon;
                return (
                  <div key={step.key} className="flex items-start gap-4">
                    {/* Icone + linha */}
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                          isCompleted
                            ? "text-white"
                            : "bg-gray-200 text-gray-400"
                        } ${isCurrent ? "ring-4 ring-offset-2" : ""}`}
                        style={isCompleted ? { background: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        <IconComponent className="w-5 h-5" />
                      </div>
                      {idx < steps.length - 1 && (
                        <div
                          className={`w-0.5 h-8 ${
                            idx < currentStep ? "" : "bg-gray-200"
                          }`}
                          style={idx < currentStep ? { background: `var(--cor-primaria, #E31A24)` } : {}}
                        />
                      )}
                    </div>
                    {/* Texto */}
                    <div className={`pb-6 ${isCurrent ? "font-bold" : ""}`}>
                      <p className={`text-sm ${isCompleted ? "" : "text-muted-foreground"}`}>
                        {step.label}
                      </p>
                      {isCurrent && !isFinished && tracking.tempo_estimado && (
                        <p className="text-xs text-muted-foreground mt-1">
                          Tempo estimado: ~{tracking.tempo_estimado} min
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}

        {/* Motoboy info + Mapa em tempo real */}
        {tracking.motoboy && tracking.status === "saiu_entrega" && (
          <Card className="p-4 md:p-6 mb-6">
            <h2 className="font-bold text-lg mb-3 flex items-center gap-2">
              <Truck className="w-5 h-5" />
              Entregador a caminho
            </h2>
            <p className="text-sm mb-4">
              <span className="font-semibold">{tracking.motoboy.nome}</span> está levando seu pedido
            </p>

            {/* Mapa com GPS em tempo real */}
            {tracking.motoboy.latitude && tracking.motoboy.longitude && (
              <MapTracking
                motoboyLat={tracking.motoboy.latitude}
                motoboyLng={tracking.motoboy.longitude}
                motoboyNome={tracking.motoboy.nome}
                destinoLat={tracking.latitude_entrega ?? undefined}
                destinoLng={tracking.longitude_entrega ?? undefined}
                destinoLabel={tracking.endereco_entrega ?? "Seu endereço"}
              />
            )}

            <p className="text-xs text-muted-foreground mt-3 text-center">
              Posição atualizada a cada 10 segundos
            </p>
          </Card>
        )}

        {/* Motoboy info (sem mapa — antes de sair para entrega) */}
        {tracking.motoboy && tracking.status !== "saiu_entrega" && (
          <Card className="p-6 mb-6">
            <h2 className="font-bold text-lg mb-3 flex items-center gap-2">
              <Truck className="w-5 h-5" />
              Entregador
            </h2>
            <p className="text-sm">
              <span className="font-semibold">{tracking.motoboy.nome}</span> foi designado para seu pedido
            </p>
          </Card>
        )}

        {/* Itens do pedido */}
        {tracking.carrinho_json && tracking.carrinho_json.length > 0 && (
          <Card className="p-6 mb-6">
            <h2 className="font-bold text-lg mb-3">Itens do Pedido</h2>
            <div className="space-y-2">
              {tracking.carrinho_json.map((item: any, idx: number) => (
                <div key={idx} className="flex justify-between text-sm">
                  <span>{item.quantidade}x {item.nome}</span>
                  <span className="font-bold">R$ {item.subtotal?.toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div className="border-t mt-3 pt-3 flex justify-between font-bold">
              <span>Total</span>
              <span style={{ color: `var(--cor-primaria, #E31A24)` }}>
                R$ {tracking.valor_total.toFixed(2)}
              </span>
            </div>
          </Card>
        )}

        {/* Endereço */}
        {tracking.endereco_entrega && (
          <Card className="p-6 mb-6">
            <h2 className="font-bold text-lg mb-2">Endereço de Entrega</h2>
            <p className="text-sm text-muted-foreground">{tracking.endereco_entrega}</p>
          </Card>
        )}

        <p className="text-xs text-center text-muted-foreground mt-4">
          Atualizando automaticamente a cada {isEmRota ? "10" : "30"} segundos
        </p>
      </div>
    </div>
  );
}
