import { useState, useEffect, useRef } from "react";
import { useLocation } from "wouter";
import {
  useMesas,
  usePagarMesa,
  useAtualizarStatusPedido,
  useCancelarPedido,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Plus,
  Clock,
  CreditCard,
  XCircle,
  ChefHat,
  CheckCircle,
  Truck,
} from "lucide-react";
import { toast } from "sonner";
import MesaProductPicker from "@/admin/components/MesaProductPicker";

interface PedidoMesa {
  id: number;
  comanda: string;
  itens: string;
  valor_total: number;
  status: string;
  forma_pagamento: string | null;
  observacoes: string | null;
  data_criacao: string | null;
}

interface Mesa {
  numero_mesa: string;
  status: "aberta" | "paga";
  valor_total: number;
  aberta_desde: string | null;
  pedidos: PedidoMesa[];
}

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pendente: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  confirmado: { label: "Confirmado", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  em_preparo: { label: "Em Preparo", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  pronto: { label: "Pronto", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  em_entrega: { label: "Em Entrega", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  entregue: { label: "Entregue", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  cancelado: { label: "Cancelado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

const STATUS_FLOW: Record<string, string[]> = {
  pendente: ["em_preparo"],
  confirmado: ["em_preparo"],
  em_preparo: ["pronto"],
  pronto: ["entregue"],
};

function getMinutosAberta(iso: string | null): number {
  if (!iso) return 0;
  return Math.round((Date.now() - new Date(iso).getTime()) / 60000);
}

function tempoAbertaColor(min: number): string {
  if (min < 30) return "text-green-400";
  if (min < 60) return "text-yellow-400";
  return "text-red-400";
}

function tocarSomAlerta() {
  try {
    const ctx = new AudioContext();
    const tempos = [0, 0.25, 0.5, 0.75];
    tempos.forEach((t) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 440;
      osc.type = "square";
      gain.gain.setValueAtTime(0.3, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.2);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.2);
    });
  } catch {
    // AudioContext não disponível
  }
}

export default function MesasGrid() {
  const [, navigate] = useLocation();
  const { data } = useMesas();
  const pagarMesa = usePagarMesa();
  const atualizarStatus = useAtualizarStatusPedido();
  const cancelarPedido = useCancelarPedido();

  const [mesaSelecionada, setMesaSelecionada] = useState<Mesa | null>(null);
  const [pagarDialogOpen, setPagarDialogOpen] = useState(false);
  const [formaPagamento, setFormaPagamento] = useState("dinheiro");
  const [abrirMesaDialogOpen, setAbrirMesaDialogOpen] = useState(false);
  const [novaMesaNumero, setNovaMesaNumero] = useState("");
  const [cancelarId, setCancelarId] = useState<number | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pickerMesa, setPickerMesa] = useState("");

  const mesas: Mesa[] = data?.mesas || [];
  const totalAbertas: number = data?.total_abertas || 0;
  const totalPagas: number = data?.total_pagas || 0;

  // Alerta sonoro para mesas abertas > 60min (não repete por 5min)
  const ultimoAlertaRef = useRef(0);
  useEffect(() => {
    const agora = Date.now();
    if (agora - ultimoAlertaRef.current < 300000) return; // 5 min cooldown
    const temMesaAtrasada = mesas.some(
      (m) => m.status === "aberta" && getMinutosAberta(m.aberta_desde) > 60
    );
    if (temMesaAtrasada) {
      tocarSomAlerta();
      ultimoAlertaRef.current = agora;
    }
  }, [mesas]);

  // Atualizar mesa selecionada quando os dados mudam
  useEffect(() => {
    if (mesaSelecionada) {
      const atualizada = mesas.find((m) => m.numero_mesa === mesaSelecionada.numero_mesa);
      if (atualizada) {
        setMesaSelecionada(atualizada);
      } else {
        setMesaSelecionada(null);
      }
    }
  }, [data]); // eslint-disable-line react-hooks/exhaustive-deps

  function handlePagarMesa() {
    if (!mesaSelecionada) return;
    pagarMesa.mutate(
      { numero_mesa: mesaSelecionada.numero_mesa, forma_pagamento: formaPagamento },
      {
        onSuccess: (res) => {
          toast.success(`Mesa ${res.numero_mesa} paga! R$ ${res.valor_total.toFixed(2)}`);
          setPagarDialogOpen(false);
          setMesaSelecionada(null);
        },
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          toast.error(detail || "Erro ao pagar mesa");
        },
      }
    );
  }

  function handleAvancarStatus(pedidoId: number, novoStatus: string) {
    atualizarStatus.mutate(
      { id: pedidoId, status: novoStatus },
      {
        onSuccess: () => toast.success(`Pedido atualizado para ${STATUS_MAP[novoStatus]?.label || novoStatus}`),
        onError: () => toast.error("Erro ao atualizar status"),
      }
    );
  }

  function handleCancelar() {
    if (!cancelarId) return;
    cancelarPedido.mutate(
      { id: cancelarId },
      {
        onSuccess: () => {
          toast.success("Pedido cancelado");
          setCancelarId(null);
        },
        onError: () => toast.error("Erro ao cancelar"),
      }
    );
  }

  function handleAbrirMesa() {
    const num = novaMesaNumero.trim();
    if (!num) {
      toast.error("Informe o número da mesa");
      return;
    }
    setAbrirMesaDialogOpen(false);
    setNovaMesaNumero("");
    navigate(`/pedidos/novo?mesa=${encodeURIComponent(num)}`);
  }

  // Calcula tamanho da bola baseado no valor (min 64px, max 96px)
  function getBolaTamanho(valor: number): number {
    return Math.min(96, Math.max(64, 64 + (valor / 500) * 32));
  }

  return (
    <div className="space-y-4">
      {/* Topo */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="border-red-500/30 text-red-400">
            {totalAbertas} aberta{totalAbertas !== 1 ? "s" : ""}
          </Badge>
          <Badge variant="outline" className="border-green-500/30 text-green-400">
            {totalPagas} paga{totalPagas !== 1 ? "s" : ""}
          </Badge>
        </div>
        <Button
          size="sm"
          className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
          onClick={() => setAbrirMesaDialogOpen(true)}
        >
          <Plus className="mr-1 h-4 w-4" /> Abrir Mesa
        </Button>
      </div>

      {/* Grid de Mesas (bolas) */}
      {mesas.length === 0 ? (
        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
          <CardContent className="py-12 text-center text-[var(--text-muted)]">
            Nenhuma mesa aberta no momento
          </CardContent>
        </Card>
      ) : (
        <div className="flex flex-wrap gap-4">
          {mesas.map((mesa) => {
            const min = getMinutosAberta(mesa.aberta_desde);
            const tamanho = getBolaTamanho(mesa.valor_total);
            const isAberta = mesa.status === "aberta";
            return (
              <button
                key={mesa.numero_mesa}
                onClick={() => setMesaSelecionada(mesa)}
                className="flex flex-col items-center gap-1.5 transition-transform hover:scale-105"
              >
                <div
                  className={`flex items-center justify-center rounded-full text-white font-bold text-lg shadow-lg transition-all ${
                    isAberta
                      ? "bg-gradient-to-br from-red-500 to-red-700"
                      : "bg-gradient-to-br from-green-500 to-green-700"
                  }`}
                  style={{ width: tamanho, height: tamanho }}
                >
                  {mesa.numero_mesa}
                </div>
                <span className="text-xs font-medium text-[var(--text-primary)]">
                  R$ {mesa.valor_total.toFixed(2)}
                </span>
                {isAberta && (
                  <span className={`text-[10px] font-mono ${tempoAbertaColor(min)}`}>
                    <Clock className="inline h-3 w-3 mr-0.5" />
                    {min}min
                  </span>
                )}
                {!isAberta && (
                  <span className="text-[10px] text-green-400 font-medium">Paga</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Dialog Detalhe da Mesa */}
      <Dialog open={mesaSelecionada !== null} onOpenChange={() => setMesaSelecionada(null)}>
        <DialogContent className="max-w-lg">
          {mesaSelecionada && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  Mesa {mesaSelecionada.numero_mesa}
                  <Badge
                    className={
                      mesaSelecionada.status === "aberta"
                        ? "bg-red-500/20 text-red-400 border-red-500/30 border"
                        : "bg-green-500/20 text-green-400 border-green-500/30 border"
                    }
                  >
                    {mesaSelecionada.status === "aberta" ? "Aberta" : "Paga"}
                  </Badge>
                  <span className="text-sm font-normal text-[var(--text-muted)] ml-auto">
                    Total: R$ {mesaSelecionada.valor_total.toFixed(2)}
                  </span>
                </DialogTitle>
              </DialogHeader>

              <div className="space-y-3 max-h-[400px] overflow-y-auto">
                {mesaSelecionada.pedidos.map((p) => {
                  const st = STATUS_MAP[p.status] || { label: p.status, color: "bg-gray-500/20 text-gray-400" };
                  const nextStatuses = STATUS_FLOW[p.status] || [];
                  return (
                    <div
                      key={p.id}
                      className="rounded-lg border border-[var(--border-subtle)] p-3 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-sm text-[var(--text-primary)]">
                          #{p.comanda}
                        </span>
                        <div className="flex items-center gap-2">
                          <Badge className={`${st.color} border text-xs`}>{st.label}</Badge>
                          <span className="text-sm font-medium text-[var(--text-primary)]">
                            R$ {(p.valor_total || 0).toFixed(2)}
                          </span>
                        </div>
                      </div>
                      <p className="text-sm text-[var(--text-secondary)]">{p.itens}</p>
                      {p.observacoes && (
                        <p className="text-xs text-[var(--text-muted)] italic">{p.observacoes}</p>
                      )}
                      {p.status !== "entregue" && (
                        <div className="flex items-center gap-1.5 pt-1">
                          {nextStatuses.map((ns) => {
                            const icon =
                              ns === "em_preparo" ? <ChefHat className="h-3.5 w-3.5 mr-1" /> :
                              ns === "pronto" ? <CheckCircle className="h-3.5 w-3.5 mr-1" /> :
                              ns === "entregue" ? <Truck className="h-3.5 w-3.5 mr-1" /> :
                              null;
                            return (
                              <Button
                                key={ns}
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs border-[var(--border-subtle)]"
                                onClick={() => handleAvancarStatus(p.id, ns)}
                                disabled={atualizarStatus.isPending}
                              >
                                {icon}
                                {STATUS_MAP[ns]?.label || ns}
                              </Button>
                            );
                          })}
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs text-red-400 border-red-500/30 hover:bg-red-500/10"
                            onClick={() => setCancelarId(p.id)}
                          >
                            <XCircle className="h-3.5 w-3.5 mr-1" /> Cancelar
                          </Button>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <DialogFooter className="flex-col gap-2 sm:flex-row">
                <Button
                  variant="outline"
                  className="border-[var(--border-subtle)]"
                  onClick={() => {
                    setPickerMesa(mesaSelecionada.numero_mesa);
                    setPickerOpen(true);
                  }}
                >
                  <Plus className="mr-1 h-4 w-4" /> Adicionar Itens
                </Button>
                <Button
                  variant="outline"
                  className="border-[var(--border-subtle)]"
                  onClick={() => {
                    setMesaSelecionada(null);
                    navigate(`/pedidos/novo?mesa=${encodeURIComponent(mesaSelecionada.numero_mesa)}`);
                  }}
                >
                  Pedido Completo
                </Button>
                {mesaSelecionada.status === "aberta" && (
                  <Button
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => {
                      setFormaPagamento("dinheiro");
                      setPagarDialogOpen(true);
                    }}
                  >
                    <CreditCard className="mr-1 h-4 w-4" /> Pagar Mesa
                  </Button>
                )}
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Sub-dialog: forma pagamento */}
      <Dialog open={pagarDialogOpen} onOpenChange={setPagarDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Pagar Mesa {mesaSelecionada?.numero_mesa}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <p className="text-sm text-[var(--text-secondary)]">
              Total: <span className="font-bold text-[var(--text-primary)]">R$ {mesaSelecionada?.valor_total.toFixed(2)}</span>
            </p>
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-[var(--text-muted)]">Forma de Pagamento</label>
              <Select value={formaPagamento} onValueChange={setFormaPagamento}>
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="dinheiro">Dinheiro</SelectItem>
                  <SelectItem value="pix">PIX</SelectItem>
                  <SelectItem value="credito">Cartão Crédito</SelectItem>
                  <SelectItem value="debito">Cartão Débito</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPagarDialogOpen(false)}>Cancelar</Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={handlePagarMesa}
              disabled={pagarMesa.isPending}
            >
              Confirmar Pagamento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog Abrir Mesa */}
      <Dialog open={abrirMesaDialogOpen} onOpenChange={setAbrirMesaDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Abrir Mesa</DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-[var(--text-muted)]">Número da Mesa</label>
            <Input
              value={novaMesaNumero}
              onChange={(e) => setNovaMesaNumero(e.target.value)}
              className="dark-input"
              placeholder="Ex: 5"
              autoFocus
              onKeyDown={(e) => { if (e.key === "Enter") handleAbrirMesa(); }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAbrirMesaDialogOpen(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleAbrirMesa}
            >
              Abrir e Adicionar Pedido
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog cancelar pedido */}
      <AlertDialog open={cancelarId !== null} onOpenChange={() => setCancelarId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar Pedido</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja cancelar este pedido? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancelar}
              className="bg-red-600 hover:bg-red-700"
            >
              Cancelar Pedido
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Product Picker para mesa */}
      <MesaProductPicker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        numeroMesa={pickerMesa}
      />
    </div>
  );
}
