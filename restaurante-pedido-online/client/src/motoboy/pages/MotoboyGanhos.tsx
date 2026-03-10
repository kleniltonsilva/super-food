import { useState } from "react";
import { useEstatisticas, useGanhosDetalhado, useHistoricoEntregas, useMotoboyConfig } from "@/motoboy/hooks/useMotoboyQueries";
import MotoboyLayout from "@/motoboy/components/MotoboyLayout";
import { Spinner } from "@/components/ui/spinner";
import {
  DollarSign, Package, MapPin, Clock, ChevronDown, ChevronUp,
  TrendingUp,
} from "lucide-react";

interface EntregaHistorico {
  id: number;
  comanda?: string;
  cliente_nome?: string;
  distancia_km?: number;
  valor_motoboy?: number;
  valor_base_motoboy?: number;
  valor_extra_motoboy?: number;
  entregue_em?: string;
  motivo_finalizacao?: string;
  status: string;
}

export default function MotoboyGanhos() {
  const { data: config } = useMotoboyConfig();
  const permitirSaldo = (config as Record<string, boolean> | undefined)?.permitir_ver_saldo ?? true;
  const { data: estatisticas, isLoading: loadingStats } = useEstatisticas();
  const { data: ganhosHoje, isLoading: loadingGanhos } = useGanhosDetalhado();
  const { data: historicoData } = useHistoricoEntregas({ limit: 20 });
  const [expandido, setExpandido] = useState<number | null>(null);

  const loading = loadingStats || loadingGanhos;

  if (!permitirSaldo) {
    return (
      <MotoboyLayout>
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <DollarSign className="mb-4 h-12 w-12 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-400">Visualização desabilitada</h3>
          <p className="mt-2 text-sm text-gray-500">
            O restaurante não habilitou a visualização de saldo para motoboys.
          </p>
          <p className="mt-1 text-sm text-gray-600">
            Entre em contato com o gerente para mais informações.
          </p>
        </div>
      </MotoboyLayout>
    );
  }

  // Métricas do dia
  const ganhoHoje = (ganhosHoje as Record<string, number | undefined>)?.total_ganhos ?? 0;
  const entregasHoje = (ganhosHoje as Record<string, number | undefined>)?.total_entregas ?? 0;
  const kmHoje = (ganhosHoje as Record<string, number | undefined>)?.total_km ?? 0;

  // Métricas gerais
  const totalEntregas = (estatisticas as Record<string, number | undefined>)?.total_entregas ?? 0;
  const totalGanho = (estatisticas as Record<string, number | undefined>)?.total_ganhos ?? 0;
  const totalKm = (estatisticas as Record<string, number | undefined>)?.total_km ?? 0;

  const historico = ((historicoData as { entregas?: EntregaHistorico[] })?.entregas ?? []) as EntregaHistorico[];

  function getStatusIcon(status: string) {
    switch (status) {
      case "entregue": return <Package className="h-4 w-4 text-green-500" />;
      case "cliente_ausente": return <span className="text-sm" title="Cliente ausente">🚪</span>;
      case "cancelado_cliente": return <span className="text-sm" title="Cancelado pelo cliente">❌</span>;
      default: return <Package className="h-4 w-4 text-gray-500" />;
    }
  }

  function formatarData(iso?: string) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) +
      " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  }

  if (loading) {
    return (
      <MotoboyLayout>
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-8 w-8 text-green-500" />
        </div>
      </MotoboyLayout>
    );
  }

  return (
    <MotoboyLayout>
      <div className="space-y-4 p-4">
        {/* Ganhos de Hoje */}
        <div>
          <h2 className="mb-2 text-sm font-semibold text-gray-400">Ganhos de Hoje</h2>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-xl bg-gradient-to-br from-green-600/20 to-green-600/5 p-3 text-center">
              <DollarSign className="mx-auto mb-1 h-5 w-5 text-green-400" />
              <p className="text-lg font-bold text-green-400">R$ {ganhoHoje.toFixed(2)}</p>
              <p className="text-[10px] text-gray-400">Total ganho</p>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-blue-600/20 to-blue-600/5 p-3 text-center">
              <Package className="mx-auto mb-1 h-5 w-5 text-blue-400" />
              <p className="text-lg font-bold text-blue-400">{entregasHoje}</p>
              <p className="text-[10px] text-gray-400">Entregas</p>
            </div>
            <div className="rounded-xl bg-gradient-to-br from-orange-600/20 to-orange-600/5 p-3 text-center">
              <MapPin className="mx-auto mb-1 h-5 w-5 text-orange-400" />
              <p className="text-lg font-bold text-orange-400">{kmHoje.toFixed(1)}</p>
              <p className="text-[10px] text-gray-400">Km</p>
            </div>
          </div>
        </div>

        {/* Estatísticas Gerais */}
        <div>
          <h2 className="mb-2 text-sm font-semibold text-gray-400">Estatísticas Gerais</h2>
          <div className="grid grid-cols-3 gap-2">
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-3 text-center">
              <TrendingUp className="mx-auto mb-1 h-5 w-5 text-gray-500" />
              <p className="text-lg font-bold text-white">{totalEntregas}</p>
              <p className="text-[10px] text-gray-500">Total entregas</p>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-3 text-center">
              <DollarSign className="mx-auto mb-1 h-5 w-5 text-gray-500" />
              <p className="text-lg font-bold text-white">R$ {totalGanho.toFixed(2)}</p>
              <p className="text-[10px] text-gray-500">Total ganho</p>
            </div>
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-3 text-center">
              <MapPin className="mx-auto mb-1 h-5 w-5 text-gray-500" />
              <p className="text-lg font-bold text-white">{totalKm.toFixed(1)}</p>
              <p className="text-[10px] text-gray-500">Total km</p>
            </div>
          </div>
        </div>

        {/* Histórico de Entregas */}
        <div>
          <h2 className="mb-2 text-sm font-semibold text-gray-400">Histórico de Entregas</h2>
          {historico.length === 0 ? (
            <div className="rounded-lg border border-gray-800 bg-gray-900 p-6 text-center">
              <Clock className="mx-auto mb-2 h-8 w-8 text-gray-600" />
              <p className="text-sm text-gray-500">Nenhuma entrega registrada</p>
            </div>
          ) : (
            <div className="space-y-1.5">
              {historico.map((e: EntregaHistorico) => (
                <div
                  key={e.id}
                  className="rounded-lg border border-gray-800 bg-gray-900"
                >
                  <button
                    onClick={() => setExpandido(expandido === e.id ? null : e.id)}
                    className="flex w-full items-center justify-between p-3 text-left"
                  >
                    <div className="flex items-center gap-2">
                      {getStatusIcon(e.status || e.motivo_finalizacao || "entregue")}
                      <div>
                        <p className="text-sm font-medium text-white">
                          {e.comanda ? `#${e.comanda}` : `#${e.id}`}
                        </p>
                        <p className="text-[10px] text-gray-500">{formatarData(e.entregue_em)}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-green-400">
                        R$ {(e.valor_motoboy ?? 0).toFixed(2)}
                      </span>
                      {expandido === e.id ? (
                        <ChevronUp className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      )}
                    </div>
                  </button>
                  {expandido === e.id && (
                    <div className="border-t border-gray-800 px-3 pb-3 pt-2 text-xs text-gray-400">
                      {e.cliente_nome && <p>Cliente: <span className="text-gray-300">{e.cliente_nome}</span></p>}
                      {e.distancia_km != null && <p>Distância: <span className="text-gray-300">{e.distancia_km.toFixed(1)} km</span></p>}
                      <p>Ganho: <span className="text-green-400">R$ {(e.valor_motoboy ?? 0).toFixed(2)}</span></p>
                      {e.valor_base_motoboy != null && e.valor_extra_motoboy != null && (
                        <p className="text-gray-500">
                          Base: R$ {e.valor_base_motoboy.toFixed(2)} + Extra: R$ {e.valor_extra_motoboy.toFixed(2)}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </MotoboyLayout>
  );
}
