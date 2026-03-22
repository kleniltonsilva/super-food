import { useState } from "react";
import { useLocation, useParams } from "wouter";
import {
  useSessao, useSolicitarFechamento, useRepetirRodada, useCancelarItem,
} from "@/garcom/hooks/useGarcomQueries";
import { sndClick } from "@/garcom/hooks/useGarcomWebSocket";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  ArrowLeft, Plus, Clock, Users, DollarSign, Repeat, Receipt,
  Trash2, ArrowRightLeft, AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const COURSE_COLORS: Record<string, string> = {
  couvert: "bg-stone-500/20 text-stone-300",
  bebida: "bg-indigo-500/20 text-indigo-300",
  entrada: "bg-sky-500/20 text-sky-300",
  principal: "bg-amber-500/20 text-amber-300",
  sobremesa: "bg-pink-500/20 text-pink-300",
};

function getMinutos(criadoEm?: string) {
  if (!criadoEm) return 0;
  return Math.floor((Date.now() - new Date(criadoEm).getTime()) / 60_000);
}

function formatTempo(min: number) {
  if (min < 1) return "agora";
  const h = Math.floor(min / 60);
  const m = min % 60;
  return h > 0 ? `${h}h${m.toString().padStart(2, "0")}` : `${m}min`;
}

export default function GarcomMesa() {
  const params = useParams<{ sessaoId: string }>();
  const sessaoId = parseInt(params.sessaoId || "0");
  const [, navigate] = useLocation();
  const { data: sessao, isLoading } = useSessao(sessaoId || null);
  const solicitarFechamento = useSolicitarFechamento();
  const repetirRodada = useRepetirRodada();
  const cancelarItem = useCancelarItem();
  const [, setTick] = useState(0);

  // Timer update
  useState(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 30_000);
    return () => clearInterval(interval);
  });

  if (isLoading || !sessao) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0806]">
        <Spinner className="h-8 w-8 text-amber-500" />
      </div>
    );
  }

  const min = getMinutos(sessao.criado_em);
  const pedidos = sessao.pedidos || [];

  async function handleFechamento() {
    sndClick();
    try {
      await solicitarFechamento.mutateAsync(sessaoId);
      toast.success("Fechamento solicitado");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro");
    }
  }

  async function handleRepetir() {
    sndClick();
    try {
      await repetirRodada.mutateAsync(sessaoId);
      toast.success("Rodada repetida!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro");
    }
  }

  async function handleCancelarItem(pedidoId: number, itemId: number) {
    try {
      await cancelarItem.mutateAsync({ pedidoId, itemId });
      toast.success("Item cancelado");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao cancelar");
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0806] text-white pb-28">
      {/* Header */}
      <header className="sticky top-0 z-10 border-b border-white/5 bg-[#0a0806]/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon-sm" onClick={() => navigate("/")} className="text-gray-400">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="text-lg font-semibold" style={{ fontFamily: "'Outfit', sans-serif" }}>
                Mesa {sessao.mesa_id}
              </h1>
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <Users className="h-3 w-3" /> {sessao.qtd_pessoas}p
                <Clock className="h-3 w-3 ml-1" /> {formatTempo(min)}
                {sessao.status === "FECHANDO" && (
                  <span className="ml-1 px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-[10px]">FECHANDO</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={() => navigate(`/transferir/${sessao.mesa_id}/${sessaoId}`)}
              className="text-gray-400"
              title="Transferir mesa"
            >
              <ArrowRightLeft className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Alergia warning */}
        {sessao.alergia && (
          <div className="mt-2 rounded-lg bg-red-500/10 border border-red-500/20 px-3 py-1.5 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />
            <span className="text-xs text-red-300">Alergia: {sessao.alergia}</span>
          </div>
        )}
      </header>

      {/* Pedidos por course */}
      <div className="p-4 space-y-4">
        {pedidos.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Plus className="mx-auto h-12 w-12 mb-3 opacity-30" />
            <p>Nenhum pedido ainda</p>
            <Button
              onClick={() => { sndClick(); navigate(`/menu/${sessaoId}`); }}
              className="mt-4 bg-amber-500 hover:bg-amber-600 text-gray-950"
            >
              <Plus className="h-4 w-4 mr-1" /> Fazer pedido
            </Button>
          </div>
        ) : (
          pedidos.map((pedido: any) => (
            <div key={pedido.pedido_id} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-gray-500">#{pedido.comanda}</span>
                  {pedido.course && (
                    <span className={`text-[10px] px-2 py-0.5 rounded-full capitalize ${COURSE_COLORS[pedido.course] || "bg-gray-500/20 text-gray-300"}`}>
                      {pedido.course}
                    </span>
                  )}
                </div>
                <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                  pedido.status === "pronto" ? "bg-green-500/20 text-green-400" :
                  pedido.status === "em_preparo" ? "bg-amber-500/20 text-amber-400" :
                  "bg-gray-500/20 text-gray-400"
                }`}>
                  {pedido.status === "em_preparo" ? "Preparando" :
                   pedido.status === "pronto" ? "Pronto" : pedido.status}
                </span>
              </div>

              {/* Itens */}
              <div className="space-y-2">
                {(pedido.itens || []).map((item: any) => (
                  <div key={item.item_id} className="flex items-center justify-between">
                    <div className="flex-1">
                      <span className="text-sm">
                        <span className="font-mono text-amber-400 mr-1">{item.quantidade}x</span>
                        {item.nome}
                      </span>
                      {item.observacoes && (
                        <p className="text-[10px] text-gray-500 ml-6">{item.observacoes}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-gray-400">
                        R$ {item.subtotal?.toFixed(2)}
                      </span>
                      {pedido.status === "em_preparo" && (
                        <button
                          onClick={() => handleCancelarItem(pedido.pedido_id, item.item_id)}
                          className="text-red-400/50 hover:text-red-400 transition-colors"
                          title="Cancelar item"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer com resumo e ações */}
      <div className="fixed bottom-0 inset-x-0 border-t border-white/5 bg-[#0a0806]/95 backdrop-blur p-4 space-y-3">
        {/* Resumo financeiro */}
        <div className="space-y-1 text-sm">
          <div className="flex justify-between text-gray-400">
            <span>Subtotal</span>
            <span className="font-mono">R$ {(sessao.subtotal || 0).toFixed(2)}</span>
          </div>
          {(sessao.taxa || 0) > 0 && (
            <div className="flex justify-between text-gray-400">
              <span>Taxa serviço ({((sessao.config?.taxa_servico || 0.10) * 100).toFixed(0)}%)</span>
              <span className="font-mono">R$ {(sessao.taxa || 0).toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between text-white font-semibold">
            <span>Total</span>
            <span className="font-mono text-amber-400">R$ {(sessao.total || 0).toFixed(2)}</span>
          </div>
          {sessao.qtd_pessoas > 1 && (
            <div className="flex justify-between text-gray-500 text-xs">
              <span>Por pessoa ({sessao.qtd_pessoas})</span>
              <span className="font-mono">R$ {((sessao.total || 0) / sessao.qtd_pessoas).toFixed(2)}</span>
            </div>
          )}
        </div>

        {/* Ações */}
        <div className="flex gap-2">
          {pedidos.length > 0 && sessao.status === "ABERTA" && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleRepetir}
              disabled={repetirRodada.isPending}
              className="flex-1 border-white/10 text-gray-300 hover:bg-white/5"
            >
              <Repeat className="h-4 w-4 mr-1" /> Repetir
            </Button>
          )}
          <Button
            size="sm"
            onClick={() => { sndClick(); navigate(`/menu/${sessaoId}`); }}
            className="flex-1 bg-amber-500 hover:bg-amber-600 text-gray-950"
            disabled={sessao.status !== "ABERTA"}
          >
            <Plus className="h-4 w-4 mr-1" /> Pedido
          </Button>
          {sessao.status === "ABERTA" && pedidos.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleFechamento}
              disabled={solicitarFechamento.isPending}
              className="border-red-500/20 text-red-400 hover:bg-red-500/10"
            >
              <Receipt className="h-4 w-4 mr-1" /> Conta
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
