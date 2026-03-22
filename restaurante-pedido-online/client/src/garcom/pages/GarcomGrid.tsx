import { useState } from "react";
import { useLocation } from "wouter";
import { useGarcomAuth } from "@/garcom/contexts/GarcomAuthContext";
import { useMesas } from "@/garcom/hooks/useGarcomQueries";
import { sndClick } from "@/garcom/hooks/useGarcomWebSocket";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Users, LogOut, Clock, ArrowRightLeft } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  LIVRE: "border-green-500/30 bg-green-500/5 hover:bg-green-500/10",
  ABERTA: "border-amber-500/30 bg-amber-500/5 hover:bg-amber-500/10",
  FECHANDO: "border-red-500/30 bg-red-500/5 hover:bg-red-500/10",
};

const STATUS_DOT: Record<string, string> = {
  LIVRE: "bg-green-500",
  ABERTA: "bg-amber-500",
  FECHANDO: "bg-red-500",
};

function getMinutos(criadoEm?: string) {
  if (!criadoEm) return 0;
  const diff = Date.now() - new Date(criadoEm).getTime();
  return Math.floor(diff / 60_000);
}

function TempoDecorrido({ criadoEm }: { criadoEm?: string }) {
  const [, setTick] = useState(0);

  // Update every 30s
  useState(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(interval);
  });

  const min = getMinutos(criadoEm);
  if (min < 1) return null;

  const h = Math.floor(min / 60);
  const m = min % 60;
  const text = h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;

  return (
    <span className={`text-xs font-mono ${min > 60 ? "text-red-400" : min > 30 ? "text-amber-400" : "text-gray-400"}`}>
      <Clock className="inline h-3 w-3 mr-0.5" />
      {text}
    </span>
  );
}

export default function GarcomGrid() {
  const [, navigate] = useLocation();
  const { garcom, logout } = useGarcomAuth();
  const { data, isLoading } = useMesas();
  const [transferMode, setTransferMode] = useState<number | null>(null);

  const mesas = data?.mesas || [];

  function handleMesaClick(mesa: any) {
    sndClick();
    if (transferMode !== null) {
      // Transferência: navegar para confirmar
      if (mesa.status === "LIVRE") {
        navigate(`/transferir/${transferMode}/${mesa.mesa_id}`);
      }
      setTransferMode(null);
      return;
    }

    if (mesa.status === "LIVRE") {
      navigate(`/abrir/${mesa.mesa_id}`);
    } else if (mesa.sessao) {
      navigate(`/mesa/${mesa.sessao.sessao_id}`);
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0806]">
        <Spinner className="h-8 w-8 text-amber-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0806] text-white">
      {/* Header */}
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-white/5 bg-[#0a0806]/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber-500/10">
            <Users className="h-4 w-4 text-amber-500" />
          </div>
          <div>
            <h1 className="text-sm font-semibold" style={{ fontFamily: "'Outfit', sans-serif" }}>
              {garcom?.restaurante?.nome_fantasia || garcom?.restaurante?.nome}
            </h1>
            <p className="text-xs text-gray-500">{garcom?.avatar_emoji} {garcom?.nome}</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={logout} className="text-gray-400 hover:text-white">
          <LogOut className="h-4 w-4" />
        </Button>
      </header>

      {/* Transfer mode banner */}
      {transferMode !== null && (
        <div className="mx-4 mt-3 rounded-lg bg-indigo-500/10 border border-indigo-500/20 px-4 py-2 flex items-center justify-between">
          <p className="text-sm text-indigo-300">
            <ArrowRightLeft className="inline h-4 w-4 mr-1" />
            Selecione a mesa de destino
          </p>
          <Button variant="ghost" size="sm" onClick={() => setTransferMode(null)} className="text-indigo-300 text-xs">
            Cancelar
          </Button>
        </div>
      )}

      {/* Grid de mesas */}
      <div className="grid grid-cols-4 gap-3 p-4">
        {mesas.map((mesa: any) => (
          <button
            key={mesa.mesa_id}
            onClick={() => handleMesaClick(mesa)}
            className={`relative flex flex-col items-center justify-center rounded-xl border p-3 transition-all ${
              transferMode !== null && mesa.status !== "LIVRE"
                ? "opacity-30 cursor-not-allowed"
                : STATUS_COLORS[mesa.status] || STATUS_COLORS.LIVRE
            }`}
            disabled={transferMode !== null && mesa.status !== "LIVRE"}
          >
            {/* Status dot */}
            <span className={`absolute top-2 right-2 h-2 w-2 rounded-full ${STATUS_DOT[mesa.status] || STATUS_DOT.LIVRE}`} />

            {/* Mesa number */}
            <span className="text-lg font-bold font-mono text-white">{mesa.mesa_id}</span>

            {/* Info */}
            {mesa.sessao ? (
              <div className="mt-1 flex flex-col items-center gap-0.5">
                <TempoDecorrido criadoEm={mesa.sessao.criado_em} />
                {mesa.sessao.qtd_pessoas > 0 && (
                  <span className="text-[10px] text-gray-500">{mesa.sessao.qtd_pessoas}p</span>
                )}
              </div>
            ) : (
              <span className="mt-1 text-[10px] text-green-400/60">Livre</span>
            )}

            {/* Tags */}
            {mesa.sessao?.tags && (mesa.sessao.tags as string[]).length > 0 && (
              <div className="mt-1 flex flex-wrap gap-0.5 justify-center">
                {(mesa.sessao.tags as string[]).slice(0, 2).map((tag: string, i: number) => (
                  <span key={i} className="text-[9px] px-1 rounded bg-amber-500/10 text-amber-400">{tag}</span>
                ))}
              </div>
            )}
          </button>
        ))}
      </div>

      {/* Footer stats */}
      <div className="fixed bottom-0 inset-x-0 border-t border-white/5 bg-[#0a0806]/95 px-4 py-2 backdrop-blur">
        <div className="flex justify-between text-xs text-gray-500">
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-green-500 mr-1" />
            {mesas.filter((m: any) => m.status === "LIVRE").length} livres
          </span>
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-amber-500 mr-1" />
            {mesas.filter((m: any) => m.status === "ABERTA").length} ocupadas
          </span>
          <span>
            <span className="inline-block h-2 w-2 rounded-full bg-red-500 mr-1" />
            {mesas.filter((m: any) => m.status === "FECHANDO").length} fechando
          </span>
        </div>
      </div>
    </div>
  );
}
