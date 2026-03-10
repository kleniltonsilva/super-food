import { useState, useEffect, useRef } from "react";
import { useLocation, useParams } from "wouter";
import { useEntregasEmRota, useEntregasPendentes, useFinalizarEntrega } from "@/motoboy/hooks/useMotoboyQueries";
import MotoboyLayout from "@/motoboy/components/MotoboyLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
  Package, MapPin, Phone, Navigation, ArrowLeft, AlertTriangle,
  CheckCircle, Loader2, XCircle, DoorOpen, CreditCard, Banknote, Blend,
} from "lucide-react";

type EstadoEntrega = "em_rota" | "no_destino" | "pagamento" | "confirmado";
type TipoPagamento = "Dinheiro" | "Cartão/Pix" | "Misto" | null;

interface Entrega {
  id: number;
  pedido_id: number;
  status: string;
  distancia_km?: number;
  cliente_nome?: string;
  cliente_telefone?: string;
  endereco_entrega?: string;
  latitude_entrega?: number;
  longitude_entrega?: number;
  valor_total?: number;
  forma_pagamento?: string;
  troco_para?: number;
  observacoes?: string;
  comanda?: string;
  valor_motoboy?: number;
  itens?: string;
}

export default function MotoboyEntrega() {
  const params = useParams<{ id: string }>();
  const entregaId = Number(params.id);
  const [, navigate] = useLocation();
  const { data: emRota = [] } = useEntregasEmRota();
  const { data: pendentes = [] } = useEntregasPendentes();
  const finalizar = useFinalizarEntrega();

  const [estado, setEstado] = useState<EstadoEntrega>("em_rota");
  const [tipoPagamento, setTipoPagamento] = useState<TipoPagamento>(null);
  const [valorRecebido, setValorRecebido] = useState("");
  const [valorDinheiro, setValorDinheiro] = useState("");
  const [valorCartao, setValorCartao] = useState("");
  const [showProblema, setShowProblema] = useState<"ausente" | "cancelou" | null>(null);
  const [motivoAusente, setMotivoAusente] = useState("Tentei ligar e não atendeu");
  const [motivoCancelou, setMotivoCancelou] = useState("Cliente cancelou o pedido");
  const [observacao, setObservacao] = useState("");

  // Encontrar entrega pelo ID (em rota ou pendentes)
  const todasEntregas = [...(emRota as Entrega[]), ...(pendentes as Entrega[])];
  const entrega = todasEntregas.find((e: Entrega) => e.id === entregaId) || null;

  if (!entrega) {
    return (
      <MotoboyLayout>
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <Package className="mb-4 h-12 w-12 text-gray-600" />
          <p className="text-gray-400">Entrega não encontrada</p>
          <Button variant="ghost" className="mt-4 text-green-500" onClick={() => navigate("/")}>
            <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
          </Button>
        </div>
      </MotoboyLayout>
    );
  }

  const valorTotal = entrega.valor_total ?? 0;

  // GPS: capturar posição atual para enviar na finalização + calcular distância percorrida
  const gpsRef = useRef<{ lat: number; lon: number } | null>(null);
  const [distanciaPercorrida, setDistanciaPercorrida] = useState<number>(entrega.distancia_km ?? 0);
  const posInicialRef = useRef<{ lat: number; lon: number } | null>(null);

  useEffect(() => {
    if (!navigator.geolocation) return;
    const watchId = navigator.geolocation.watchPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        gpsRef.current = { lat: latitude, lon: longitude };
        // Salvar posição inicial (do restaurante) para calcular distância
        if (!posInicialRef.current) {
          posInicialRef.current = { lat: latitude, lon: longitude };
        }
        // Calcular distância em tempo real (haversine)
        if (posInicialRef.current) {
          const R = 6371;
          const dLat = ((latitude - posInicialRef.current.lat) * Math.PI) / 180;
          const dLon = ((longitude - posInicialRef.current.lon) * Math.PI) / 180;
          const a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos((posInicialRef.current.lat * Math.PI) / 180) *
              Math.cos((latitude * Math.PI) / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
          const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
          const dist = R * c;
          // Usar a maior entre: distância do banco ou distância GPS
          setDistanciaPercorrida(Math.max(entrega.distancia_km ?? 0, parseFloat(dist.toFixed(2))));
        }
      },
      () => {}, // erro silencioso — GPS já é monitorado pelo useGPS global
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 10000 }
    );
    return () => navigator.geolocation.clearWatch(watchId);
  }, [entrega.distancia_km]);

  function abrirMaps(endereco: string) {
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`, "_blank");
  }

  function abrirWaze(endereco: string) {
    window.open(`https://waze.com/ul?q=${encodeURIComponent(endereco)}`, "_blank");
  }

  async function handleFinalizar(motivo: string) {
    try {
      // Combinar motivo predefinido com observação
      let obsCompleta = "";
      if (motivo === "cliente_ausente") obsCompleta = motivoAusente;
      else if (motivo === "cancelado_cliente") obsCompleta = motivoCancelou;
      if (observacao) obsCompleta = obsCompleta ? `${obsCompleta}. ${observacao}` : observacao;

      const payload: Parameters<typeof finalizar.mutateAsync>[0]["payload"] = {
        motivo,
        observacao: obsCompleta || undefined,
        distancia_km: distanciaPercorrida > 0 ? distanciaPercorrida : undefined,
        lat_atual: gpsRef.current?.lat,
        lon_atual: gpsRef.current?.lon,
      };

      if (tipoPagamento) {
        payload.forma_pagamento_real = tipoPagamento;
        if (tipoPagamento === "Dinheiro") {
          payload.valor_pago_dinheiro = parseFloat(valorRecebido) || valorTotal;
        } else if (tipoPagamento === "Cartão/Pix") {
          payload.valor_pago_cartao = valorTotal;
        } else if (tipoPagamento === "Misto") {
          payload.valor_pago_dinheiro = parseFloat(valorDinheiro) || 0;
          payload.valor_pago_cartao = parseFloat(valorCartao) || 0;
        }
      }

      await finalizar.mutateAsync({ entregaId, payload });
      toast.success(motivo === "entregue" ? "Entrega finalizada!" : "Entrega registrada!");
      navigate("/");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao finalizar";
      toast.error(msg);
    }
  }

  // Calcular troco
  const trocoDinheiro = tipoPagamento === "Dinheiro"
    ? Math.max(0, (parseFloat(valorRecebido) || 0) - valorTotal)
    : 0;

  return (
    <MotoboyLayout>
      <div className="p-4">
        {/* Header */}
        <div className="mb-4 flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/")} className="text-gray-400">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-lg font-bold text-white">
            Entrega {entrega.comanda ? `#${entrega.comanda}` : `#${entrega.id}`}
          </h1>
        </div>

        {/* Card da entrega */}
        <div className="space-y-3 rounded-xl border border-gray-800 bg-gray-900 p-4">
          {entrega.cliente_nome && (
            <div className="flex items-center gap-2 text-white">
              <Package className="h-4 w-4 text-green-500" />
              <span className="font-semibold">{entrega.cliente_nome}</span>
            </div>
          )}
          {entrega.endereco_entrega && (
            <div className="flex items-start gap-2 text-gray-300">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
              <span className="text-sm">{entrega.endereco_entrega}</span>
            </div>
          )}
          {entrega.cliente_telefone && (
            <a href={`tel:${entrega.cliente_telefone}`} className="flex items-center gap-2 text-green-400">
              <Phone className="h-4 w-4" />
              <span className="text-sm">{entrega.cliente_telefone}</span>
            </a>
          )}
          {(distanciaPercorrida > 0 || (entrega.distancia_km != null && entrega.distancia_km > 0)) && (
            <div className="flex items-center gap-2 text-sm text-gray-400">
              <Navigation className="h-4 w-4 text-green-500" />
              {distanciaPercorrida.toFixed(1)} km
            </div>
          )}

          <div className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2">
            <span className="text-sm text-gray-400">Valor a cobrar</span>
            <span className="text-lg font-bold text-green-400">R$ {valorTotal.toFixed(2)}</span>
          </div>

          {entrega.valor_motoboy != null && entrega.valor_motoboy > 0 && (
            <div className="flex items-center justify-between rounded-lg bg-green-500/10 px-3 py-2">
              <span className="text-sm text-green-400">Seu Ganho</span>
              <span className="text-lg font-bold text-green-400">R$ {entrega.valor_motoboy.toFixed(2)}</span>
            </div>
          )}

          {entrega.forma_pagamento && (
            <div className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2">
              <span className="text-sm text-gray-400">Forma pagamento</span>
              <span className="text-sm font-medium text-white">{entrega.forma_pagamento}</span>
            </div>
          )}

          {entrega.troco_para != null && entrega.troco_para > 0 && (
            <div className="flex items-center justify-between rounded-lg bg-yellow-500/10 px-3 py-2">
              <span className="text-sm text-yellow-400">Troco para</span>
              <span className="font-bold text-yellow-400">R$ {entrega.troco_para.toFixed(2)}</span>
            </div>
          )}

          {entrega.observacoes && (
            <div className="rounded-lg bg-yellow-500/10 px-3 py-2">
              <div className="flex items-center gap-1.5 text-xs font-medium text-yellow-500">
                <AlertTriangle className="h-3.5 w-3.5" /> Observações
              </div>
              <p className="mt-1 text-sm text-gray-300">{entrega.observacoes}</p>
            </div>
          )}

          {/* Botões de navegação */}
          {entrega.endereco_entrega && (
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                className="border-gray-700 text-green-400 hover:bg-green-500/10"
                onClick={() => abrirMaps(entrega.endereco_entrega!)}
              >
                <Navigation className="mr-1.5 h-4 w-4" /> Google Maps
              </Button>
              <Button
                variant="outline"
                className="border-gray-700 text-green-400 hover:bg-green-500/10"
                onClick={() => abrirWaze(entrega.endereco_entrega!)}
              >
                <MapPin className="mr-1.5 h-4 w-4" /> Waze
              </Button>
            </div>
          )}
        </div>

        {/* State Machine: em_rota → no_destino → pagamento → confirmado → finalizar */}
        <div className="mt-4 space-y-3">
          {/* Estado: em_rota */}
          {estado === "em_rota" && (
            <Button
              className="h-14 w-full bg-blue-600 text-base font-bold hover:bg-blue-700"
              onClick={() => setEstado("no_destino")}
            >
              <MapPin className="mr-2 h-5 w-5" />
              CHEGUEI AO DESTINO
            </Button>
          )}

          {/* Estado: no_destino — selecionar forma de pagamento */}
          {estado === "no_destino" && (
            <div className="space-y-3">
              <p className="text-center text-sm font-semibold text-gray-300">Selecione a forma de pagamento</p>
              <div className="grid grid-cols-3 gap-2">
                <Button
                  variant={tipoPagamento === "Dinheiro" ? "default" : "outline"}
                  className={tipoPagamento === "Dinheiro" ? "bg-green-600" : "border-gray-700 text-gray-300"}
                  onClick={() => { setTipoPagamento("Dinheiro"); setEstado("pagamento"); }}
                >
                  <Banknote className="mr-1 h-4 w-4" /> Dinheiro
                </Button>
                <Button
                  variant={tipoPagamento === "Cartão/Pix" ? "default" : "outline"}
                  className={tipoPagamento === "Cartão/Pix" ? "bg-blue-600" : "border-gray-700 text-gray-300"}
                  onClick={() => { setTipoPagamento("Cartão/Pix"); setEstado("pagamento"); }}
                >
                  <CreditCard className="mr-1 h-4 w-4" /> Cartão/Pix
                </Button>
                <Button
                  variant={tipoPagamento === "Misto" ? "default" : "outline"}
                  className={tipoPagamento === "Misto" ? "bg-purple-600" : "border-gray-700 text-gray-300"}
                  onClick={() => { setTipoPagamento("Misto"); setEstado("pagamento"); }}
                >
                  <Blend className="mr-1 h-4 w-4" /> Misto
                </Button>
              </div>
            </div>
          )}

          {/* Estado: pagamento — detalhes do pagamento */}
          {estado === "pagamento" && tipoPagamento === "Dinheiro" && (
            <div className="space-y-3 rounded-xl border border-gray-700 bg-gray-900 p-4">
              <p className="text-sm font-semibold text-gray-300">Pagamento em Dinheiro</p>
              <div>
                <label className="text-xs text-gray-400">Valor recebido (R$)</label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder={valorTotal.toFixed(2)}
                  value={valorRecebido}
                  onChange={(e) => setValorRecebido(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                />
              </div>
              {trocoDinheiro > 0 && (
                <div className="flex items-center justify-between rounded-lg bg-yellow-500/10 px-3 py-2">
                  <span className="text-sm text-yellow-400">Troco</span>
                  <span className="font-bold text-yellow-400">R$ {trocoDinheiro.toFixed(2)}</span>
                </div>
              )}
              <Button
                className="h-12 w-full bg-green-600 font-bold hover:bg-green-700"
                onClick={() => setEstado("confirmado")}
              >
                <CheckCircle className="mr-2 h-4 w-4" /> Confirmar Pagamento
              </Button>
              <Button
                variant="ghost"
                className="w-full text-gray-500"
                onClick={() => { setEstado("no_destino"); setTipoPagamento(null); }}
              >
                Voltar
              </Button>
            </div>
          )}

          {estado === "pagamento" && tipoPagamento === "Cartão/Pix" && (
            <div className="space-y-3 rounded-xl border border-gray-700 bg-gray-900 p-4">
              <p className="text-sm font-semibold text-gray-300">Pagamento Cartão/Pix</p>
              <div className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2">
                <span className="text-sm text-gray-400">Total</span>
                <span className="font-bold text-green-400">R$ {valorTotal.toFixed(2)}</span>
              </div>
              <Button
                className="h-12 w-full bg-green-600 font-bold hover:bg-green-700"
                onClick={() => setEstado("confirmado")}
              >
                <CheckCircle className="mr-2 h-4 w-4" /> Pagamento Recebido
              </Button>
              <Button
                variant="ghost"
                className="w-full text-gray-500"
                onClick={() => { setEstado("no_destino"); setTipoPagamento(null); }}
              >
                Voltar
              </Button>
            </div>
          )}

          {estado === "pagamento" && tipoPagamento === "Misto" && (
            <div className="space-y-3 rounded-xl border border-gray-700 bg-gray-900 p-4">
              <p className="text-sm font-semibold text-gray-300">Pagamento Misto</p>
              <div>
                <label className="text-xs text-gray-400">Dinheiro (R$)</label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={valorDinheiro}
                  onChange={(e) => setValorDinheiro(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">Cartão/Pix (R$)</label>
                <Input
                  type="number"
                  step="0.01"
                  placeholder="0.00"
                  value={valorCartao}
                  onChange={(e) => setValorCartao(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                />
              </div>
              <div className="flex items-center justify-between rounded-lg bg-gray-800 px-3 py-2">
                <span className="text-sm text-gray-400">Total informado</span>
                <span className={`font-bold ${
                  (parseFloat(valorDinheiro || "0") + parseFloat(valorCartao || "0")).toFixed(2) === valorTotal.toFixed(2)
                    ? "text-green-400"
                    : "text-yellow-400"
                }`}>
                  R$ {(parseFloat(valorDinheiro || "0") + parseFloat(valorCartao || "0")).toFixed(2)}
                </span>
              </div>
              <Button
                className="h-12 w-full bg-green-600 font-bold hover:bg-green-700"
                onClick={() => setEstado("confirmado")}
              >
                <CheckCircle className="mr-2 h-4 w-4" /> Confirmar
              </Button>
              <Button
                variant="ghost"
                className="w-full text-gray-500"
                onClick={() => { setEstado("no_destino"); setTipoPagamento(null); }}
              >
                Voltar
              </Button>
            </div>
          )}

          {/* Estado: confirmado — finalizar */}
          {estado === "confirmado" && (
            <Button
              className="h-16 w-full bg-green-600 text-lg font-bold hover:bg-green-700"
              onClick={() => handleFinalizar("entregue")}
              disabled={finalizar.isPending}
            >
              {finalizar.isPending ? (
                <><Loader2 className="mr-2 h-5 w-5 animate-spin" /> FINALIZANDO...</>
              ) : (
                <><CheckCircle className="mr-2 h-5 w-5" /> FINALIZAR ENTREGA</>
              )}
            </Button>
          )}

          {/* Botões de problema (no_destino em diante) */}
          {(estado === "no_destino" || estado === "pagamento" || estado === "confirmado") && !showProblema && (
            <div className="grid grid-cols-2 gap-2">
              <Button
                variant="outline"
                className="border-yellow-600/50 text-yellow-500 hover:bg-yellow-600/10"
                onClick={() => setShowProblema("ausente")}
              >
                <DoorOpen className="mr-1.5 h-4 w-4" /> Cliente Ausente
              </Button>
              <Button
                variant="outline"
                className="border-red-600/50 text-red-500 hover:bg-red-600/10"
                onClick={() => setShowProblema("cancelou")}
              >
                <XCircle className="mr-1.5 h-4 w-4" /> Cliente Cancelou
              </Button>
            </div>
          )}

          {/* Modal problema: cliente ausente */}
          {showProblema === "ausente" && (
            <div className="space-y-3 rounded-xl border border-yellow-600/30 bg-yellow-500/5 p-4">
              <p className="text-sm font-semibold text-yellow-400">Cliente Ausente</p>
              <p className="text-xs text-gray-400">Você receberá o valor da entrega normalmente.</p>
              <div>
                <label className="text-xs text-gray-400">O que aconteceu?</label>
                <div className="mt-1.5 space-y-1.5">
                  {[
                    "Tentei ligar e não atendeu",
                    "Toquei campainha/bati na porta",
                    "Aguardei no local por mais de 5 minutos",
                    "Vizinho informou que não está em casa",
                  ].map((opcao) => (
                    <label key={opcao} className="flex items-center gap-2 rounded-lg bg-gray-800/50 px-3 py-2 text-sm text-gray-300">
                      <input
                        type="radio"
                        name="motivo_ausente"
                        checked={motivoAusente === opcao}
                        onChange={() => setMotivoAusente(opcao)}
                        className="accent-yellow-500"
                      />
                      {opcao}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400">Observações adicionais (opcional)</label>
                <Input
                  placeholder="Detalhes adicionais..."
                  value={observacao}
                  onChange={(e) => setObservacao(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                />
              </div>
              <Button
                className="h-12 w-full bg-yellow-600 font-bold text-white hover:bg-yellow-700"
                onClick={() => handleFinalizar("cliente_ausente")}
                disabled={finalizar.isPending}
              >
                {finalizar.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <DoorOpen className="mr-2 h-4 w-4" />
                )}
                Registrar Ausência
              </Button>
              <Button variant="ghost" className="w-full text-gray-500" onClick={() => setShowProblema(null)}>
                Cancelar
              </Button>
            </div>
          )}

          {/* Modal problema: cliente cancelou */}
          {showProblema === "cancelou" && (
            <div className="space-y-3 rounded-xl border border-red-600/30 bg-red-500/5 p-4">
              <p className="text-sm font-semibold text-red-400">Cliente Cancelou</p>
              <p className="text-xs text-gray-400">Você receberá o valor da entrega normalmente.</p>
              <div>
                <label className="text-xs text-gray-400">Motivo</label>
                <div className="mt-1.5 space-y-1.5">
                  {[
                    "Cliente cancelou o pedido",
                    "Cliente recusou receber",
                    "Pedido errado",
                    "Problema com pagamento",
                    "Outro motivo",
                  ].map((opcao) => (
                    <label key={opcao} className="flex items-center gap-2 rounded-lg bg-gray-800/50 px-3 py-2 text-sm text-gray-300">
                      <input
                        type="radio"
                        name="motivo_cancelou"
                        checked={motivoCancelou === opcao}
                        onChange={() => setMotivoCancelou(opcao)}
                        className="accent-red-500"
                      />
                      {opcao}
                    </label>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-400">Observações adicionais (opcional)</label>
                <Input
                  placeholder="Detalhes adicionais..."
                  value={observacao}
                  onChange={(e) => setObservacao(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                />
              </div>
              <Button
                className="h-12 w-full bg-red-600 font-bold text-white hover:bg-red-700"
                onClick={() => handleFinalizar("cancelado_cliente")}
                disabled={finalizar.isPending}
              >
                {finalizar.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <XCircle className="mr-2 h-4 w-4" />
                )}
                Confirmar Cancelamento
              </Button>
              <Button variant="ghost" className="w-full text-gray-500" onClick={() => setShowProblema(null)}>
                Cancelar
              </Button>
            </div>
          )}
        </div>
      </div>
    </MotoboyLayout>
  );
}
