import { useState, useEffect, useMemo } from "react";
import { useKdsAuth } from "@/kds/contexts/KdsAuthContext";
import { usePedidosKds, useAtualizarStatusKds, useRefazerPedidoKds, useConfigKds } from "@/kds/hooks/useKdsQueries";
import { Button } from "@/components/ui/button";
import { ChefHat, LogOut, Flame, Check, RotateCcw, Bell, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface PedidoKds {
  id: number;
  pedido_id: number;
  status: string;
  cozinheiro_id: number | null;
  urgente: boolean;
  criado_em: string | null;
  iniciado_em: string | null;
  feito_em: string | null;
  pronto_em: string | null;
  comanda: string;
  tipo: string;
  tipo_entrega: string | null;
  numero_mesa: string | null;
  cliente_nome: string;
  observacoes: string | null;
  itens: Array<{
    nome: string;
    quantidade: number;
    observacoes: string;
    variacoes: Array<{ nome: string; preco_adicional?: number }>;
    produto_id: number | null;
  }>;
}

function getMinutosDesde(isoStr: string | null): number {
  if (!isoStr) return 0;
  const diff = Date.now() - new Date(isoStr).getTime();
  return Math.max(0, Math.floor(diff / 60000));
}

function formatTempo(min: number): string {
  if (min < 60) return `${min}m`;
  return `${Math.floor(min / 60)}h ${min % 60}m`;
}

function TempoDecorrido({ isoStr, alertaMin, criticoMin }: { isoStr: string | null; alertaMin: number; criticoMin: number }) {
  const [min, setMin] = useState(() => getMinutosDesde(isoStr));

  useEffect(() => {
    const interval = setInterval(() => setMin(getMinutosDesde(isoStr)), 5000);
    return () => clearInterval(interval);
  }, [isoStr]);

  const color = min >= criticoMin ? "text-red-500" : min >= alertaMin ? "text-amber-400" : "text-green-400";
  const animate = min >= criticoMin ? "animate-pulse" : "";

  return <span className={cn("font-mono font-bold", color, animate)}>{formatTempo(min)}</span>;
}

function QueueChip({ pedido, selected, onClick, alertaMin, criticoMin }: {
  pedido: PedidoKds;
  selected: boolean;
  onClick: () => void;
  alertaMin: number;
  criticoMin: number;
}) {
  const min = getMinutosDesde(pedido.criado_em);
  const color = min >= criticoMin ? "border-red-500 bg-red-500/10" : min >= alertaMin ? "border-amber-500 bg-amber-500/10" : "border-green-500 bg-green-500/10";

  return (
    <button
      onClick={onClick}
      className={cn(
        "flex-shrink-0 rounded-lg border-2 px-3 py-2 text-sm font-medium transition-all",
        color,
        selected ? "ring-2 ring-amber-400 ring-offset-2 ring-offset-gray-950" : "opacity-70 hover:opacity-100"
      )}
    >
      <span className="text-white">#{pedido.comanda}</span>
      <span className="ml-2 text-xs">
        <TempoDecorrido isoStr={pedido.criado_em} alertaMin={alertaMin} criticoMin={criticoMin} />
      </span>
    </button>
  );
}

function OrigemBadge({ pedido }: { pedido: PedidoKds }) {
  if (pedido.numero_mesa) return <span className="text-xs bg-blue-500/20 text-blue-400 rounded-full px-2 py-0.5">Mesa {pedido.numero_mesa}</span>;
  if (pedido.tipo_entrega === "retirada") return <span className="text-xs bg-purple-500/20 text-purple-400 rounded-full px-2 py-0.5">Retirada</span>;
  return <span className="text-xs bg-orange-500/20 text-orange-400 rounded-full px-2 py-0.5">Delivery</span>;
}

export default function KdsMain() {
  const { cozinheiro, logout } = useKdsAuth();
  const { data: pedidos = [], isLoading } = usePedidosKds();
  const { data: config } = useConfigKds();
  const statusMut = useAtualizarStatusKds();
  const refazerMut = useRefazerPedidoKds();

  const [tab, setTab] = useState<"preparo" | "despacho">("preparo");
  const [selectedIdx, setSelectedIdx] = useState(0);

  const alertaMin = config?.tempo_alerta_min ?? 15;
  const criticoMin = config?.tempo_critico_min ?? 25;

  // Separar pedidos por aba
  const preparoPedidos = useMemo(() =>
    (pedidos as PedidoKds[]).filter((p) => p.status === "NOVO" || p.status === "FAZENDO"),
    [pedidos]
  );

  const feitoPedidos = useMemo(() =>
    (pedidos as PedidoKds[]).filter((p) => p.status === "FEITO"),
    [pedidos]
  );

  const prontoPedidos = useMemo(() =>
    (pedidos as PedidoKds[]).filter((p) => p.status === "PRONTO"),
    [pedidos]
  );

  // Reset selectedIdx when pedidos change
  useEffect(() => {
    if (selectedIdx >= preparoPedidos.length) setSelectedIdx(Math.max(0, preparoPedidos.length - 1));
  }, [preparoPedidos.length, selectedIdx]);

  const currentPedido = preparoPedidos[selectedIdx];

  async function handleAction(pedido: PedidoKds, novoStatus: string) {
    try {
      await statusMut.mutateAsync({ id: pedido.id, status: novoStatus });
      if (novoStatus === "FAZENDO") toast.success(`Preparando #${pedido.comanda}`);
      else if (novoStatus === "FEITO") toast.success(`#${pedido.comanda} feito!`);
      else if (novoStatus === "PRONTO") toast.success(`#${pedido.comanda} pronto para despacho!`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao atualizar");
    }
  }

  async function handleRefazer(pedido: PedidoKds) {
    try {
      await refazerMut.mutateAsync(pedido.id);
      toast.info(`#${pedido.comanda} voltou para preparo`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao refazer");
    }
  }

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-white">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-500/20">
            <ChefHat className="h-5 w-5 text-amber-500" />
          </div>
          <div>
            <h1 className="text-base font-bold">Cozinha Digital</h1>
            <p className="text-xs text-gray-400">
              {cozinheiro?.restaurante.nome_fantasia || cozinheiro?.restaurante.nome}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-400">
            {cozinheiro?.avatar_emoji || "👨‍🍳"} {cozinheiro?.nome}
          </span>
          <Button variant="ghost" size="icon-sm" onClick={logout} className="text-gray-400 hover:text-white">
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-gray-800">
        <button
          onClick={() => setTab("preparo")}
          className={cn(
            "flex-1 py-3 text-center text-sm font-semibold transition-colors border-b-2",
            tab === "preparo"
              ? "border-amber-500 text-amber-500"
              : "border-transparent text-gray-500 hover:text-gray-300"
          )}
        >
          PREPARO ({preparoPedidos.length})
        </button>
        <button
          onClick={() => setTab("despacho")}
          className={cn(
            "flex-1 py-3 text-center text-sm font-semibold transition-colors border-b-2",
            tab === "despacho"
              ? "border-green-500 text-green-500"
              : "border-transparent text-gray-500 hover:text-gray-300"
          )}
        >
          DESPACHO ({feitoPedidos.length})
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500">Carregando pedidos...</p>
          </div>
        )}

        {/* ═══ TAB PREPARO ═══ */}
        {tab === "preparo" && !isLoading && (
          <div className="flex flex-col h-full">
            {preparoPedidos.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-gray-500">
                <ChefHat className="h-16 w-16 mb-4 opacity-20" />
                <p className="text-lg">Nenhum pedido em preparo</p>
                <p className="text-sm mt-1">Aguardando novos pedidos...</p>
              </div>
            ) : (
              <>
                {/* Queue Strip */}
                <div className="flex gap-2 overflow-x-auto px-4 py-3 border-b border-gray-800 scrollbar-hide">
                  {preparoPedidos.map((p, i) => (
                    <QueueChip
                      key={p.id}
                      pedido={p}
                      selected={i === selectedIdx}
                      onClick={() => setSelectedIdx(i)}
                      alertaMin={alertaMin}
                      criticoMin={criticoMin}
                    />
                  ))}
                </div>

                {/* Current card */}
                {currentPedido && (
                  <div className="flex-1 p-4">
                    <div className={cn(
                      "rounded-xl border-2 p-5 transition-colors",
                      currentPedido.status === "FAZENDO"
                        ? "border-amber-500 bg-amber-500/5"
                        : "border-gray-700 bg-gray-900"
                    )}>
                      {/* Card header */}
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <span className="text-xl font-bold">#{currentPedido.comanda}</span>
                          <OrigemBadge pedido={currentPedido} />
                          {currentPedido.status === "FAZENDO" && (
                            <span className="text-xs bg-amber-500/20 text-amber-400 rounded-full px-2 py-0.5 animate-pulse">
                              Preparando...
                            </span>
                          )}
                        </div>
                        <TempoDecorrido isoStr={currentPedido.criado_em} alertaMin={alertaMin} criticoMin={criticoMin} />
                      </div>

                      {/* Itens */}
                      <div className="space-y-3 mb-6">
                        {currentPedido.itens.map((item, i) => (
                          <div key={i} className="border-l-2 border-gray-700 pl-3">
                            <p className="text-base font-medium">
                              <span className="text-amber-400">{item.quantidade}x</span>{" "}
                              {item.nome}
                            </p>
                            {item.variacoes?.length > 0 && (
                              <div className="mt-0.5 space-y-0.5">
                                {item.variacoes.map((v, vi) => (
                                  <p key={vi} className="text-xs text-gray-400">&bull; {v.nome}</p>
                                ))}
                              </div>
                            )}
                            {item.observacoes && (
                              <p className="text-xs text-yellow-400 mt-0.5">
                                &#9888; {item.observacoes}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Observações do pedido */}
                      {currentPedido.observacoes && (
                        <div className="mb-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 p-3">
                          <p className="text-xs text-yellow-400 font-medium">Observação:</p>
                          <p className="text-sm text-yellow-300">{currentPedido.observacoes}</p>
                        </div>
                      )}

                      {/* Actions */}
                      {currentPedido.status === "NOVO" && (
                        <Button
                          onClick={() => handleAction(currentPedido, "FAZENDO")}
                          disabled={statusMut.isPending}
                          className="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-bold py-6 text-lg"
                        >
                          <Flame className="h-5 w-5 mr-2" />
                          COMECEI A FAZER
                        </Button>
                      )}

                      {currentPedido.status === "FAZENDO" && (
                        <Button
                          onClick={() => handleAction(currentPedido, "FEITO")}
                          disabled={statusMut.isPending}
                          className="w-full bg-green-500 hover:bg-green-600 text-white font-bold py-6 text-lg"
                        >
                          <Check className="h-5 w-5 mr-2" />
                          FEITO - PROXIMO
                        </Button>
                      )}
                    </div>

                    {/* Navigation */}
                    {preparoPedidos.length > 1 && (
                      <div className="flex items-center justify-between mt-4">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedIdx(Math.max(0, selectedIdx - 1))}
                          disabled={selectedIdx === 0}
                          className="text-gray-400"
                        >
                          <ChevronLeft className="h-4 w-4 mr-1" /> Anterior
                        </Button>
                        <span className="text-sm text-gray-500">
                          {selectedIdx + 1}/{preparoPedidos.length}
                        </span>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setSelectedIdx(Math.min(preparoPedidos.length - 1, selectedIdx + 1))}
                          disabled={selectedIdx === preparoPedidos.length - 1}
                          className="text-gray-400"
                        >
                          Próximo <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ═══ TAB DESPACHO ═══ */}
        {tab === "despacho" && !isLoading && (
          <div className="p-4 space-y-6">
            {/* FEITOS */}
            <div>
              <h3 className="text-sm font-semibold text-green-400 mb-3 flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                FEITOS — AGUARDANDO DESPACHO ({feitoPedidos.length})
              </h3>
              {feitoPedidos.length === 0 ? (
                <p className="text-sm text-gray-500 py-4 text-center">Nenhum pedido feito aguardando</p>
              ) : (
                <div className="space-y-3">
                  {feitoPedidos.map((p) => (
                    <div key={p.id} className="rounded-lg border border-green-500/30 bg-green-500/5 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold">#{p.comanda}</span>
                          <OrigemBadge pedido={p} />
                        </div>
                        <span className="text-xs text-gray-400">
                          preparo: <TempoDecorrido isoStr={p.iniciado_em} alertaMin={999} criticoMin={999} />
                        </span>
                      </div>
                      <p className="text-sm text-gray-300 mb-3">
                        {p.itens.map((item) => `${item.quantidade}x ${item.nome}`).join(", ")}
                      </p>
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleAction(p, "PRONTO")}
                          disabled={statusMut.isPending}
                          size="sm"
                          className="bg-cyan-500 hover:bg-cyan-600 text-white font-semibold"
                        >
                          <Bell className="h-4 w-4 mr-1" /> PRONTO
                        </Button>
                        <Button
                          onClick={() => handleRefazer(p)}
                          disabled={refazerMut.isPending}
                          variant="ghost"
                          size="sm"
                          className="text-gray-400 hover:text-white"
                        >
                          <RotateCcw className="h-4 w-4 mr-1" /> Refazer
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* PRONTOS (despachados) */}
            {prontoPedidos.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-cyan-400 mb-3 flex items-center gap-2">
                  <Check className="h-4 w-4" />
                  DESPACHADOS ({prontoPedidos.length})
                </h3>
                <div className="space-y-2">
                  {prontoPedidos.slice(0, 10).map((p) => (
                    <div key={p.id} className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">#{p.comanda}</span>
                        <OrigemBadge pedido={p} />
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-400">
                        <span>{p.itens.map((item) => `${item.quantidade}x ${item.nome}`).join(", ").slice(0, 40)}</span>
                        <Check className="h-4 w-4 text-cyan-500" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {feitoPedidos.length === 0 && prontoPedidos.length === 0 && (
              <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                <Bell className="h-16 w-16 mb-4 opacity-20" />
                <p className="text-lg">Nenhum pedido para despachar</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
