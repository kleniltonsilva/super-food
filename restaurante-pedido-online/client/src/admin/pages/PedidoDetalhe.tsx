import { useState } from "react";
import { useLocation, useRoute } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  usePedido,
  useAtualizarStatusPedido,
  useDespacharPedido,
  useCancelarPedido,
  useMotoboys,
  useConfig,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  ArrowLeft,
  User,
  Phone,
  MapPin,
  Clock,
  CreditCard,
  ChefHat,
  CheckCircle,
  Truck,
  XCircle,
  Bike,
  AlertTriangle,
  Package,
  Printer,
} from "lucide-react";
import { toast } from "sonner";
import { useWebSocket } from "@/admin/hooks/useWebSocket";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pendente: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  em_preparo: { label: "Em Preparo", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  pronto: { label: "Pronto", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  em_entrega: { label: "Em Entrega", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  entregue: { label: "Entregue", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  cancelado: { label: "Cancelado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

// Calcula minutos entre duas datas ISO
function diffMinutos(a: string | null, b: string | null): number | null {
  if (!a || !b) return null;
  return Math.round((new Date(b).getTime() - new Date(a).getTime()) / 60000);
}

export default function PedidoDetalhe() {
  const [, navigate] = useLocation();
  const [, params] = useRoute("/pedidos/:id");
  const pedidoId = Number(params?.id);

  const { data: pedido, isLoading } = usePedido(pedidoId);
  const atualizarStatus = useAtualizarStatusPedido();
  const despachar = useDespacharPedido();
  const cancelar = useCancelarPedido();
  const { data: motoboys } = useMotoboys();
  const { data: configData } = useConfig();
  const { restaurante } = useAdminAuth();
  const { enviarMensagem } = useWebSocket({ restauranteId: restaurante?.id ?? null });

  const modoDespacho = configData?.modo_prioridade_entrega || "rapido_economico";

  const [showCancelar, setShowCancelar] = useState(false);
  const [cancelarSenha, setCancelarSenha] = useState("");
  const [showDespachar, setShowDespachar] = useState(false);
  const [motoboyId, setMotoboyId] = useState<string>("");

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AdminLayout>
    );
  }

  if (!pedido) {
    return (
      <AdminLayout>
        <div className="flex h-64 flex-col items-center justify-center gap-2">
          <p className="text-[var(--text-muted)]">Pedido não encontrado</p>
          <Button variant="outline" onClick={() => navigate("/pedidos")}>
            Voltar
          </Button>
        </div>
      </AdminLayout>
    );
  }

  const st = STATUS_MAP[pedido.status] || { label: pedido.status, color: "" };

  function handleStatus(status: string) {
    atualizarStatus.mutate(
      { id: pedidoId, status },
      {
        onSuccess: () => toast.success(`Status atualizado para ${STATUS_MAP[status]?.label}`),
        onError: () => toast.error("Erro ao atualizar status"),
      }
    );
  }

  function handleDespachar(manualMotoboyId?: number) {
    despachar.mutate(
      { id: pedidoId, motoboy_id: manualMotoboyId },
      {
        onSuccess: (data) => {
          toast.success(`Despachado para ${data.motoboy_nome}`);
          setShowDespachar(false);
          setMotoboyId("");
        },
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          toast.error(detail || "Erro ao despachar");
        },
      }
    );
  }

  function handleDespacharClick() {
    if (modoDespacho === "manual") {
      // Modo manual: mostrar seleção de motoboy
      setShowDespachar(true);
    } else {
      // Modo automático: despachar direto sem selecionar motoboy
      handleDespachar();
    }
  }

  const requerSenha = ['entregue', 'pago', 'finalizado'].includes(pedido?.status);

  function handleCancelar() {
    if (requerSenha && !cancelarSenha.trim()) {
      toast.error("Informe a senha do administrador");
      return;
    }
    cancelar.mutate(
      { id: pedidoId, senha: requerSenha ? cancelarSenha.trim() : undefined },
      {
        onSuccess: () => {
          toast.success("Pedido cancelado");
          setShowCancelar(false);
          setCancelarSenha("");
        },
        onError: (err: unknown) => {
          const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
          const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? detail.map((e: { msg?: string }) => e.msg || String(e)).join(", ") : "Erro ao cancelar";
          toast.error(msg);
        },
      }
    );
  }

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("pt-BR");
  }

  // Parse itens (pode ser JSON string ou texto)
  let itensDisplay: { nome: string; qtd: number; preco: number; obs?: string }[] = [];
  try {
    if (pedido.carrinho_json) {
      const parsed = typeof pedido.carrinho_json === "string"
        ? JSON.parse(pedido.carrinho_json)
        : pedido.carrinho_json;
      if (Array.isArray(parsed)) {
        itensDisplay = parsed.map((item: Record<string, unknown>) => ({
          nome: (item.nome || item.produto_nome || "Item") as string,
          qtd: (item.quantidade || item.qtd || 1) as number,
          preco: (item.preco || item.preco_unitario || 0) as number,
          obs: item.observacoes as string | undefined,
        }));
      }
    }
  } catch {
    // fallback to itens text
  }

  // Timeline data
  const entrega = pedido.entrega;
  const timelineSteps = [
    { label: "Recebido", time: pedido.data_criacao, icon: Package, done: true },
    {
      label: "Em Preparo",
      time: pedido.status !== "pendente" ? pedido.data_criacao : null,
      icon: ChefHat,
      done: ["em_preparo", "pronto", "em_entrega", "entregue"].includes(pedido.status),
    },
    {
      label: "Pronto",
      time: ["pronto", "em_entrega", "entregue"].includes(pedido.status)
        ? (entrega?.atribuido_em || pedido.atualizado_em)
        : null,
      icon: CheckCircle,
      done: ["pronto", "em_entrega", "entregue"].includes(pedido.status),
    },
    {
      label: "Saiu p/ Entrega",
      time: entrega?.saiu_em || (entrega?.atribuido_em && ["em_entrega", "entregue"].includes(pedido.status) ? entrega.atribuido_em : null),
      icon: Truck,
      done: ["em_entrega", "entregue"].includes(pedido.status),
    },
    {
      label: "Entregue",
      time: entrega?.entregue_em,
      icon: CheckCircle,
      done: pedido.status === "entregue",
    },
  ];

  // Identificar gargalo
  const tempoPreparo = diffMinutos(pedido.data_criacao, entrega?.atribuido_em || pedido.atualizado_em);
  const tempoEntrega = entrega ? diffMinutos(entrega.atribuido_em, entrega.entregue_em) : null;
  const gargalo = tempoPreparo !== null && tempoEntrega !== null
    ? (tempoPreparo > tempoEntrega ? "cozinha" : "entrega")
    : null;

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={() => navigate("/pedidos")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-[var(--text-primary)]">
                Pedido #{pedido.comanda || pedido.id}
              </h2>
              <Badge className={`${st.color} border`}>{st.label}</Badge>
              {pedido.marketplace_source && (
                <Badge variant="outline" className={
                  pedido.marketplace_source === "ifood" ? "bg-red-100 text-red-700 border-red-200" :
                  pedido.marketplace_source === "99food" ? "bg-yellow-100 text-yellow-700 border-yellow-200" :
                  pedido.marketplace_source === "rappi" ? "bg-orange-100 text-orange-700 border-orange-200" :
                  "bg-blue-100 text-blue-700 border-blue-200"
                }>
                  {pedido.marketplace_source === "ifood" ? "iFood" :
                   pedido.marketplace_source === "99food" ? "99Food" :
                   pedido.marketplace_source === "rappi" ? "Rappi" :
                   pedido.marketplace_source === "keeta" ? "Keeta" :
                   pedido.marketplace_source}
                </Badge>
              )}
            </div>
            <p className="text-sm text-[var(--text-muted)]">
              {formatDate(pedido.data_criacao)}
              {pedido.marketplace_display_id && (
                <span className="ml-2 text-xs">({pedido.marketplace_display_id})</span>
              )}
            </p>
          </div>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* Coluna principal */}
          <div className="space-y-4 lg:col-span-2">
            {/* Timeline */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Timeline</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="relative space-y-0">
                  {timelineSteps.map((step, i) => {
                    const Icon = step.icon;
                    const nextStep = timelineSteps[i + 1];
                    const duracao = step.time && nextStep?.time ? diffMinutos(step.time, nextStep.time) : null;
                    const isLast = i === timelineSteps.length - 1;
                    const isCancelled = pedido.status === "cancelado";

                    return (
                      <div key={step.label} className="relative flex items-start gap-3 pb-6 last:pb-0">
                        {/* Linha vertical */}
                        {!isLast && (
                          <div className={`absolute left-[15px] top-[30px] h-[calc(100%-18px)] w-0.5 ${
                            step.done && nextStep?.done ? "bg-green-500" : "bg-[var(--border-subtle)]"
                          }`} />
                        )}
                        {/* Ícone */}
                        <div className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                          step.done
                            ? isCancelled ? "bg-red-500/20 text-red-400" : "bg-green-500/20 text-green-400"
                            : "bg-[var(--bg-surface)] text-[var(--text-muted)]"
                        }`}>
                          {isCancelled && step.label === "Entregue" ? (
                            <XCircle className="h-4 w-4" />
                          ) : (
                            <Icon className="h-4 w-4" />
                          )}
                        </div>
                        {/* Conteúdo */}
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm font-medium ${
                            step.done ? "text-[var(--text-primary)]" : "text-[var(--text-muted)]"
                          }`}>
                            {isCancelled && step.label === "Entregue" ? "Cancelado" : step.label}
                          </p>
                          {step.time && (
                            <p className="text-xs text-[var(--text-muted)]">
                              {formatDate(step.time)}
                            </p>
                          )}
                          {duracao !== null && duracao > 0 && (
                            <div className="mt-1 flex items-center gap-1">
                              <Clock className="h-3 w-3 text-[var(--text-muted)]" />
                              <span className={`text-xs ${
                                duracao > 30 ? "text-red-400" : duracao > 15 ? "text-yellow-400" : "text-[var(--text-muted)]"
                              }`}>
                                {duracao} min
                                {duracao > 30 && (
                                  <span className="ml-1">
                                    ({i <= 1 ? "cozinha demorou" : "entrega demorou"})
                                  </span>
                                )}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
                {/* Gargalo */}
                {gargalo && pedido.status === "entregue" && (
                  <div className={`mt-4 flex items-center gap-2 rounded-md p-2 text-xs ${
                    gargalo === "cozinha"
                      ? "bg-yellow-500/10 text-yellow-400"
                      : "bg-blue-500/10 text-blue-400"
                  }`}>
                    <AlertTriangle className="h-3.5 w-3.5" />
                    Gargalo identificado: <strong>{gargalo === "cozinha" ? "tempo de preparo" : "tempo de entrega"}</strong>
                    {tempoPreparo !== null && tempoEntrega !== null && (
                      <span> (preparo: {tempoPreparo}min, entrega: {tempoEntrega}min)</span>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Itens */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Itens do Pedido</CardTitle>
              </CardHeader>
              <CardContent>
                {itensDisplay.length > 0 ? (
                  <div className="space-y-3">
                    {itensDisplay.map((item, i) => (
                      <div key={i} className="flex items-start justify-between">
                        <div>
                          <p className="text-sm font-medium text-[var(--text-primary)]">
                            {item.qtd}x {item.nome}
                          </p>
                          {item.obs && (
                            <p className="text-xs text-[var(--text-muted)]">{item.obs}</p>
                          )}
                        </div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          R$ {(item.qtd * item.preco).toFixed(2)}
                        </p>
                      </div>
                    ))}
                    <Separator className="bg-[var(--border-subtle)]" />
                    <div className="flex justify-between text-base font-bold text-[var(--text-primary)]">
                      <span>Total</span>
                      <span>R$ {Number(pedido.valor_total).toFixed(2)}</span>
                    </div>
                  </div>
                ) : pedido.itens ? (
                  <div>
                    <p className="whitespace-pre-wrap text-sm text-[var(--text-secondary)]">{pedido.itens}</p>
                    <Separator className="my-3 bg-[var(--border-subtle)]" />
                    <div className="flex justify-between text-base font-bold text-[var(--text-primary)]">
                      <span>Total</span>
                      <span>R$ {Number(pedido.valor_total).toFixed(2)}</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-[var(--text-muted)]">Sem itens detalhados</p>
                )}
              </CardContent>
            </Card>

            {/* Observações */}
            {pedido.observacoes && (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)]">Observações</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[var(--text-secondary)]">{pedido.observacoes}</p>
                </CardContent>
              </Card>
            )}

            {/* Entrega */}
            {pedido.entrega && (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-[var(--text-primary)]">
                    <Bike className="h-5 w-5" /> Entrega
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[var(--text-muted)]">Motoboy</span>
                    <span className="text-[var(--text-primary)]">{pedido.entrega.motoboy_nome || "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--text-muted)]">Status</span>
                    <span className="text-[var(--text-primary)]">{pedido.entrega.status}</span>
                  </div>
                  {pedido.entrega.distancia_km && (
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Distância</span>
                      <span className="text-[var(--text-primary)]">{pedido.entrega.distancia_km} km</span>
                    </div>
                  )}
                  {pedido.entrega.entregue_em && (
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Entregue em</span>
                      <span className="text-[var(--text-primary)]">{formatDate(pedido.entrega.entregue_em)}</span>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar direita */}
          <div className="space-y-4">
            {/* Dados do cliente */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Cliente</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                  <User className="h-4 w-4 text-[var(--text-muted)]" />
                  {pedido.cliente_nome || "Não informado"}
                </div>
                {pedido.cliente_telefone && (
                  <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                    <Phone className="h-4 w-4 text-[var(--text-muted)]" />
                    {pedido.cliente_telefone}
                  </div>
                )}
                {pedido.endereco_entrega && (
                  <div className="flex items-start gap-2 text-[var(--text-secondary)]">
                    <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[var(--text-muted)]" />
                    {pedido.endereco_entrega}
                  </div>
                )}
                <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                  <Clock className="h-4 w-4 text-[var(--text-muted)]" />
                  {formatDate(pedido.data_criacao)}
                </div>
                {pedido.forma_pagamento && (
                  <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                    <CreditCard className="h-4 w-4 text-[var(--text-muted)]" />
                    {pedido.forma_pagamento}
                    {pedido.troco_para ? ` (troco p/ R$ ${Number(pedido.troco_para).toFixed(2)})` : ""}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Ações */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Ações</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {pedido.status === "pendente" && (
                  <Button
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    onClick={() => handleStatus("em_preparo")}
                    disabled={atualizarStatus.isPending}
                  >
                    <ChefHat className="mr-2 h-4 w-4" /> Iniciar Preparo
                  </Button>
                )}
                {pedido.status === "em_preparo" && (
                  <Button
                    className="w-full bg-green-600 hover:bg-green-700"
                    onClick={() => handleStatus("pronto")}
                    disabled={atualizarStatus.isPending}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" /> Marcar Pronto
                  </Button>
                )}
                {pedido.status === "pronto" && pedido.tipo_entrega === "entrega" && !pedido.despachado && (
                  <Button
                    className="w-full bg-purple-600 hover:bg-purple-700"
                    onClick={handleDespacharClick}
                    disabled={despachar.isPending}
                  >
                    <Truck className="mr-2 h-4 w-4" />
                    {despachar.isPending ? "Despachando..." : modoDespacho === "manual" ? "Despachar (Manual)" : "Despachar Automático"}
                  </Button>
                )}
                {pedido.status === "pronto" && pedido.tipo_entrega !== "entrega" && (
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleStatus("entregue")}
                    disabled={atualizarStatus.isPending}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" /> Marcar Entregue
                  </Button>
                )}
                {pedido.status === "em_entrega" && (
                  <Button
                    className="w-full bg-emerald-600 hover:bg-emerald-700"
                    onClick={() => handleStatus("entregue")}
                    disabled={atualizarStatus.isPending}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" /> Confirmar Entrega
                  </Button>
                )}
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    const ok = enviarMensagem({ tipo: "reimprimir_pedido", dados: { pedido_id: pedidoId } });
                    if (ok) toast.success("Comando de impressão enviado");
                    else toast.error("Sem conexão WebSocket");
                  }}
                >
                  <Printer className="mr-2 h-4 w-4" /> Imprimir
                </Button>
                {!["cancelado", "recusado", "entregue"].includes(pedido.status) && (
                  <Button
                    variant="outline"
                    className="w-full border-red-500/30 text-red-400 hover:bg-red-500/10"
                    onClick={() => setShowCancelar(true)}
                  >
                    <XCircle className="mr-2 h-4 w-4" /> Cancelar
                  </Button>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Dialog cancelar */}
      <AlertDialog open={showCancelar} onOpenChange={(open) => { setShowCancelar(open); if (!open) setCancelarSenha(""); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar Pedido</AlertDialogTitle>
            <AlertDialogDescription>
              {requerSenha
                ? "Este pedido já foi entregue/pago. Para cancelar, informe a senha do administrador."
                : `Tem certeza que deseja cancelar o pedido #${pedido.comanda || pedido.id}?`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {requerSenha && (
            <div className="px-6 pb-2">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Senha do Administrador</label>
              <Input
                type="password"
                value={cancelarSenha}
                onChange={(e) => setCancelarSenha(e.target.value)}
                className="dark-input mt-1"
                placeholder="Digite a senha"
              />
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>Voltar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleCancelar}
              className="bg-red-600 hover:bg-red-700"
              disabled={requerSenha && !cancelarSenha.trim()}
            >
              Cancelar Pedido
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Dialog despachar */}
      <Dialog open={showDespachar} onOpenChange={setShowDespachar}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Despachar Pedido</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <label className="text-sm font-medium text-[var(--text-secondary)]">
              Selecione o Motoboy
            </label>
            <Select value={motoboyId} onValueChange={setMotoboyId}>
              <SelectTrigger className="dark-input">
                <SelectValue placeholder="Escolher motoboy..." />
              </SelectTrigger>
              <SelectContent>
                {(motoboys || []).map((m: Record<string, unknown>) => (
                  <SelectItem key={m.id as number} value={String(m.id)}>
                    {m.nome as string} {m.disponivel ? "" : "(indisponível)"}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDespachar(false)}>
              Cancelar
            </Button>
            <Button
              className="bg-purple-600 hover:bg-purple-700"
              onClick={() => handleDespachar(Number(motoboyId))}
              disabled={!motoboyId || despachar.isPending}
            >
              <Truck className="mr-2 h-4 w-4" /> Despachar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
