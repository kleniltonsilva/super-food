import { useEffect, useRef } from "react";
import { useLocation } from "wouter";
import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { useEntregasPendentes, useEntregasEmRota, useIniciarEntrega } from "@/motoboy/hooks/useMotoboyQueries";
import { useNotificacaoSonora } from "@/motoboy/hooks/useNotificacaoSonora";
import MotoboyLayout from "@/motoboy/components/MotoboyLayout";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import {
  Package, MapPin, Phone, Navigation, Clock, AlertTriangle,
  ChevronRight, Loader2,
} from "lucide-react";

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
  pix_pago?: boolean;
  pago_online?: boolean;
  troco_para?: number;
  observacoes?: string;
  comanda?: string;
  valor_motoboy?: number;
  delivery_started_at?: string;
}

export default function MotoboyHome() {
  const { motoboy } = useMotoboyAuth();
  const [, navigate] = useLocation();
  const { data: pendentes = [], isLoading: loadingPendentes } = useEntregasPendentes();
  const { data: emRota = [] } = useEntregasEmRota();
  const iniciar = useIniciarEntrega();
  const { tocar, pedirPermissao } = useNotificacaoSonora();
  const prevCountRef = useRef(0);

  // Pedir permissão de notificação ao montar
  useEffect(() => {
    pedirPermissao();
  }, [pedirPermissao]);

  // Tocar som quando novas entregas chegam
  useEffect(() => {
    const totalPendentes = (pendentes as Entrega[]).filter((e: Entrega) => e.status === "pendente").length;
    if (totalPendentes > prevCountRef.current && prevCountRef.current > 0) {
      tocar();
    }
    prevCountRef.current = totalPendentes;
  }, [pendentes, tocar]);

  const entregaAtual = (emRota as Entrega[])[0] || null;
  const entregasPendentes = (pendentes as Entrega[]).filter((e: Entrega) => e.status === "pendente");
  const totalPendentes = entregasPendentes.length;

  async function handleIniciar() {
    if (entregasPendentes.length === 0) return;
    const primeira = entregasPendentes[0];
    try {
      await iniciar.mutateAsync(primeira.id);
      toast.success("Entrega iniciada!");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao iniciar";
      toast.error(msg);
    }
  }

  function abrirMaps(endereco: string) {
    window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(endereco)}`, "_blank");
  }

  function abrirWaze(endereco: string) {
    window.open(`https://waze.com/ul?q=${encodeURIComponent(endereco)}`, "_blank");
  }

  // Status display
  function renderStatusBanner() {
    if (entregaAtual) {
      const restantes = totalPendentes;
      return (
        <div className="bg-blue-600 px-4 py-3 text-center text-sm font-semibold text-white">
          EM ENTREGA {restantes > 0 && `— ${restantes} pendente${restantes > 1 ? "s" : ""}`}
        </div>
      );
    }
    if (totalPendentes > 0) {
      return (
        <div className="bg-yellow-600 px-4 py-3 text-center text-sm font-semibold text-white">
          {totalPendentes} ENTREGA{totalPendentes > 1 ? "S" : ""} ATRIBUÍDA{totalPendentes > 1 ? "S" : ""}
        </div>
      );
    }
    if (!motoboy?.disponivel) {
      return (
        <div className="bg-gray-700 px-4 py-3 text-center text-sm font-semibold text-gray-300">
          OFFLINE — Ative o status online no Perfil
        </div>
      );
    }
    return (
      <div className="bg-green-700 px-4 py-3 text-center text-sm font-semibold text-white">
        DISPONÍVEL — Aguardando entregas
      </div>
    );
  }

  return (
    <MotoboyLayout>
      {renderStatusBanner()}

      <div className="space-y-4 p-4">
        {/* Entrega em rota ativa */}
        {entregaAtual && (
          <div className="rounded-xl border border-blue-500/30 bg-blue-500/10 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-white">Entrega Atual</h2>
              {entregaAtual.comanda && (
                <span className="rounded-full bg-blue-600 px-3 py-0.5 text-xs font-bold text-white">
                  #{entregaAtual.comanda}
                </span>
              )}
            </div>

            <div className="space-y-2.5 text-sm">
              {entregaAtual.cliente_nome && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Package className="h-4 w-4 text-blue-400" />
                  <span className="font-medium">{entregaAtual.cliente_nome}</span>
                </div>
              )}
              {entregaAtual.endereco_entrega && (
                <div className="flex items-start gap-2 text-gray-300">
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
                  <span>{entregaAtual.endereco_entrega}</span>
                </div>
              )}
              {entregaAtual.cliente_telefone && (
                <a href={`tel:${entregaAtual.cliente_telefone}`} className="flex items-center gap-2 text-blue-400">
                  <Phone className="h-4 w-4" />
                  <span>{entregaAtual.cliente_telefone}</span>
                </a>
              )}
              {entregaAtual.distancia_km != null && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Navigation className="h-4 w-4 text-blue-400" />
                  <span>{entregaAtual.distancia_km.toFixed(1)} km</span>
                </div>
              )}

              <div className="flex items-center justify-between rounded-lg bg-gray-800/50 px-3 py-2">
                <span className="text-gray-400">Valor do pedido</span>
                <span className="font-bold text-green-400">
                  R$ {(entregaAtual.valor_total ?? 0).toFixed(2)}
                </span>
              </div>

              {entregaAtual.valor_motoboy != null && entregaAtual.valor_motoboy > 0 && (
                <div className="flex items-center justify-between rounded-lg bg-green-500/10 px-3 py-2">
                  <span className="text-green-400">Seu Ganho</span>
                  <span className="font-bold text-green-400">
                    R$ {entregaAtual.valor_motoboy.toFixed(2)}
                  </span>
                </div>
              )}

              {(entregaAtual.pago_online || entregaAtual.pix_pago) ? (
                <div className="rounded-lg bg-emerald-600 px-4 py-3 text-center">
                  <span className="text-lg font-bold text-white">PAGO ONLINE</span>
                  <p className="text-sm text-emerald-100 mt-0.5">Nada a receber do cliente</p>
                </div>
              ) : entregaAtual.forma_pagamento && (
                <div className="flex items-center justify-between rounded-lg bg-gray-800/50 px-3 py-2">
                  <span className="text-gray-400">Pagamento</span>
                  <span className="font-medium text-white">
                    {entregaAtual.forma_pagamento}
                  </span>
                </div>
              )}

              {entregaAtual.troco_para != null && entregaAtual.troco_para > 0 && (
                <div className="flex items-center justify-between rounded-lg bg-yellow-500/10 px-3 py-2">
                  <span className="text-yellow-400">Troco para</span>
                  <span className="font-bold text-yellow-400">
                    R$ {entregaAtual.troco_para.toFixed(2)}
                  </span>
                </div>
              )}

              {entregaAtual.observacoes && (
                <div className="rounded-lg bg-gray-800/50 px-3 py-2">
                  <div className="flex items-center gap-1.5 text-xs text-yellow-500">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Observações
                  </div>
                  <p className="mt-1 text-gray-300">{entregaAtual.observacoes}</p>
                </div>
              )}
            </div>

            {/* Botões de navegação */}
            <div className="mt-4 grid grid-cols-2 gap-2">
              {entregaAtual.endereco_entrega && (
                <>
                  <Button
                    variant="outline"
                    className="border-blue-600 text-blue-400 hover:bg-blue-600/20"
                    onClick={() => abrirMaps(entregaAtual.endereco_entrega!)}
                  >
                    <Navigation className="mr-1.5 h-4 w-4" />
                    Google Maps
                  </Button>
                  <Button
                    variant="outline"
                    className="border-blue-600 text-blue-400 hover:bg-blue-600/20"
                    onClick={() => abrirWaze(entregaAtual.endereco_entrega!)}
                  >
                    <MapPin className="mr-1.5 h-4 w-4" />
                    Waze
                  </Button>
                </>
              )}
            </div>

            {/* Botão de ação principal */}
            <Button
              className="mt-4 h-14 w-full bg-green-600 text-base font-bold hover:bg-green-700"
              onClick={() => navigate(`/entrega/${entregaAtual.id}`)}
            >
              VER DETALHES DA ENTREGA
              <ChevronRight className="ml-1 h-5 w-5" />
            </Button>
          </div>
        )}

        {/* Botão iniciar entregas */}
        {!entregaAtual && totalPendentes > 0 && (
          <Button
            className="h-16 w-full bg-green-600 text-lg font-bold hover:bg-green-700"
            onClick={handleIniciar}
            disabled={iniciar.isPending}
          >
            {iniciar.isPending ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                INICIANDO...
              </>
            ) : (
              <>
                <Package className="mr-2 h-5 w-5" />
                INICIAR ENTREGAS
              </>
            )}
          </Button>
        )}

        {/* Lista de entregas pendentes */}
        {entregasPendentes.length > 0 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-gray-400">
              {entregaAtual ? "Próximas Entregas" : "Entregas Pendentes"}
            </h3>
            <div className="space-y-2">
              {entregasPendentes.slice(0, 4).map((e: Entrega, idx: number) => (
                <div key={e.id} className="rounded-lg border border-gray-800 bg-gray-900 p-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-gray-700 text-xs font-bold text-white">
                        {idx + 1}
                      </span>
                      <span className="font-medium text-white">{e.cliente_nome || "Cliente"}</span>
                    </div>
                    {e.comanda && (
                      <span className="text-xs text-gray-500">#{e.comanda}</span>
                    )}
                  </div>
                  <div className="mt-1.5 flex items-center gap-2 text-xs text-gray-400">
                    <MapPin className="h-3 w-3" />
                    <span className="line-clamp-1">
                      {e.endereco_entrega || "Endereço não informado"}
                    </span>
                  </div>
                  {e.distancia_km != null && (
                    <div className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      <Navigation className="h-3 w-3" />
                      <span>{e.distancia_km.toFixed(1)} km</span>
                    </div>
                  )}
                </div>
              ))}
              {totalPendentes > 4 && (
                <p className="text-center text-xs text-gray-500">
                  + {totalPendentes - 4} entrega{totalPendentes - 4 > 1 ? "s" : ""}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Estado vazio */}
        {!loadingPendentes && totalPendentes === 0 && !entregaAtual && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <img
              src="/derekh-motoboy-icon.png"
              alt=""
              className="mb-6 h-24 w-24 opacity-30"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <h3 className="text-lg font-semibold text-gray-400">Sem entregas no momento</h3>
            <p className="mt-2 text-sm text-gray-600 max-w-[250px]">
              {motoboy?.disponivel
                ? "Aguardando novas entregas..."
                : "Ative o status online no Perfil para receber entregas"}
            </p>
          </div>
        )}

        {loadingPendentes && !entregaAtual && (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-green-500" />
          </div>
        )}
      </div>
    </MotoboyLayout>
  );
}
