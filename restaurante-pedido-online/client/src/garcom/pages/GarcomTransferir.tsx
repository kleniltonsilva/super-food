import { useLocation, useParams } from "wouter";
import { useMesas, useTransferirMesa } from "@/garcom/hooks/useGarcomQueries";
import { sndClick } from "@/garcom/hooks/useGarcomWebSocket";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { ArrowLeft, ArrowRightLeft } from "lucide-react";
import { toast } from "sonner";

export default function GarcomTransferir() {
  const params = useParams<{ mesaId: string; sessaoId: string }>();
  const mesaId = parseInt(params.mesaId || "0");
  const [, navigate] = useLocation();
  const { data, isLoading } = useMesas();
  const transferir = useTransferirMesa();

  const mesas = data?.mesas || [];
  const mesasLivres = mesas.filter((m: any) => m.status === "LIVRE" && m.mesa_id !== mesaId);

  async function handleTransferir(mesaDestinoId: number) {
    sndClick();
    try {
      await transferir.mutateAsync({ mesaId, mesaDestinoId });
      toast.success(`Mesa transferida para mesa ${mesaDestinoId}`);
      navigate("/");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao transferir");
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
      <header className="flex items-center gap-3 border-b border-white/5 px-4 py-3">
        <Button variant="ghost" size="icon-sm" onClick={() => navigate(-1 as any)} className="text-gray-400">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-lg font-semibold" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Transferir Mesa {mesaId}
          </h1>
          <p className="text-xs text-gray-500">Selecione a mesa de destino</p>
        </div>
      </header>

      {mesasLivres.length === 0 ? (
        <div className="p-8 text-center text-gray-500">
          <ArrowRightLeft className="mx-auto h-12 w-12 mb-3 opacity-30" />
          <p>Nenhuma mesa livre disponivel</p>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-3 p-4">
          {mesasLivres.map((mesa: any) => (
            <button
              key={mesa.mesa_id}
              onClick={() => handleTransferir(mesa.mesa_id)}
              disabled={transferir.isPending}
              className="flex flex-col items-center justify-center rounded-xl border border-green-500/30 bg-green-500/5 hover:bg-green-500/10 p-4 transition-all"
            >
              <span className="text-lg font-bold font-mono">{mesa.mesa_id}</span>
              <span className="mt-1 text-[10px] text-green-400">Livre</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
