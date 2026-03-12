import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Check, Clock, Truck, ChefHat, Package, Star } from "lucide-react";
import { useParams, useLocation } from "wouter";
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
  aceitar_pedido_site_auto: boolean;
  aviso_proximo_pedido_auto: boolean;
}

const STATUS_STEPS = [
  { key: "pendente", label: "Pedido Recebido", icon: Package },
  { key: "confirmado", label: "Confirmado", icon: Check },
  { key: "em_preparo", label: "Preparando", icon: ChefHat },
  { key: "pronto", label: "Pronto", icon: Check },
  { key: "em_entrega", label: "Saiu para Entrega", icon: Truck },
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
  const pedidoId = parseInt(params?.id || "0");

  const [tracking, setTracking] = useState<TrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Polling mais rápido quando motoboy está em rota (10s) vs normal (30s)
  const isEmRota = tracking?.status === "em_entrega" && tracking?.motoboy?.latitude != null;

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getTrackingPedido(pedidoId);
        setTracking(data);
        setError(null);
        setErrorStatus(null);
      } catch (err: any) {
        const status = err?.response?.status ?? null;
        setErrorStatus(status);
        if (status === 404) {
          setError("Pedido não encontrado. Verifique o número do pedido.");
        } else {
          setError("Não foi possível carregar o pedido. Tente novamente em instantes.");
        }
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
          <Card className="p-8 text-center space-y-3">
            <Package className="w-12 h-12 mx-auto text-muted-foreground" />
            <p className="font-semibold">{error || "Pedido não encontrado"}</p>
            {errorStatus !== 404 && (
              <p className="text-xs text-muted-foreground">
                A página atualiza automaticamente. Se o problema persistir, volte ao cardápio.
              </p>
            )}
            <Button variant="outline" size="sm" onClick={() => navigate("/")}>
              Voltar ao cardápio
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  const isRetirada = tracking.tipo_entrega === "retirada";
  const steps = isRetirada ? STATUS_RETIRADA_STEPS : STATUS_STEPS;
  const currentStep = getStepIndex(tracking.status, steps);
  const isCancelled = tracking.status === "cancelado";
  const isFinished = tracking.status === "entregue" || tracking.status === "finalizado";
  const isPendente = tracking.status === "pendente";

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
          <p className="text-sm text-muted-foreground mb-4">
            {new Date(tracking.data_criacao).toLocaleDateString("pt-BR")} às{" "}
            {new Date(tracking.data_criacao).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}
          </p>
        )}

        {/* Aviso: aguardando aceitação do restaurante */}
        {isPendente && !isCancelled && (
          <Card className="p-4 mb-4 border-yellow-700/40 bg-yellow-900/10">
            <div className="flex items-start gap-3">
              <Clock className="w-5 h-5 text-yellow-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-yellow-300 font-semibold text-sm">Aguardando confirmação do restaurante</p>
                <p className="text-yellow-400/70 text-xs mt-1">
                  Seu pedido foi recebido e está na fila. O restaurante irá confirmar em breve.
                </p>
                {tracking.aceitar_pedido_site_auto && (
                  <p className="text-yellow-400/70 text-xs mt-2">
                    Se este pedido for concluído com sucesso, seus próximos pedidos serão aceitos automaticamente.
                  </p>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Status cancelado */}
        {isCancelled && (
          <Card className="p-6 mb-6 bg-red-900/20 border-red-800/30">
            <p className="text-red-400 font-bold text-lg">Pedido Cancelado</p>
            <p className="text-red-400/70 text-sm">Este pedido foi cancelado pelo restaurante.</p>
          </Card>
        )}

        {/* Aviso: próximo pedido aceito automaticamente (aparece quando o pedido foi concluído) */}
        {isFinished && tracking.aviso_proximo_pedido_auto && (
          <Card className="p-4 mb-4 border-green-700/40 bg-green-900/10">
            <div className="flex items-start gap-3">
              <Star className="w-5 h-5 text-green-400 mt-0.5 shrink-0" />
              <div>
                <p className="text-green-300 font-semibold text-sm">Parabéns! Pedido concluído com sucesso</p>
                <p className="text-green-400/70 text-xs mt-1">
                  A partir de agora, seus próximos pedidos neste restaurante serão aceitos automaticamente, sem precisar aguardar confirmação.
                </p>
              </div>
            </div>
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
                            : "bg-[var(--bg-card-hover)] text-[var(--text-muted)]"
                        } ${isCurrent ? "ring-4 ring-offset-2 ring-offset-background" : ""}`}
                        style={isCompleted ? { background: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        <IconComponent className="w-5 h-5" />
                      </div>
                      {idx < steps.length - 1 && (
                        <div
                          className={`w-0.5 h-8 ${
                            idx < currentStep ? "" : "bg-[var(--bg-card-hover)]"
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
                      {/* Sub-texto do step atual */}
                      {isCurrent && step.key === "pendente" && (
                        <p className="text-xs text-yellow-400/80 mt-1">
                          Aguardando confirmação do restaurante
                        </p>
                      )}
                      {isCurrent && step.key === "confirmado" && (
                        <p className="text-xs text-green-400/80 mt-1">
                          Pedido aceito pelo restaurante!
                        </p>
                      )}
                      {isCurrent && !isFinished && tracking.tempo_estimado && step.key !== "pendente" && step.key !== "confirmado" && (
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
        {tracking.motoboy && tracking.status === "em_entrega" && (
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
        {tracking.motoboy && tracking.status !== "em_entrega" && (
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
