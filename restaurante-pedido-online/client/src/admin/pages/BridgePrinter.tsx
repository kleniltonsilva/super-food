import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useBridgePatterns,
  useDeletarBridgePattern,
  useBridgeOrders,
  useCriarPedidoFromBridge,
  useValidarEAprenderBridge,
  useReparseBridgeOrder,
  useBridgeStatus,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Printer,
  Trash2,
  Plus,
  RefreshCw,
  FileText,
  Brain,
  CheckCircle2,
  RotateCcw,
  Zap,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import { toast } from "sonner";

const PLATAFORMA_CORES: Record<string, string> = {
  ifood: "bg-red-500/20 text-red-400 border-red-500/30",
  rappi: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  "99food": "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  aiqfome: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  ubereats: "bg-green-500/20 text-green-400 border-green-500/30",
  keeta: "bg-teal-500/20 text-teal-400 border-teal-500/30",
  zdelivery: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  anota_ai: "bg-indigo-500/20 text-indigo-400 border-indigo-500/30",
  desconhecido: "bg-gray-500/20 text-gray-400 border-gray-500/30",
};

type TabType = "interceptados" | "padroes";

export default function BridgePrinter() {
  const [tab, setTab] = useState<TabType>("interceptados");
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  const { data: ordersData, isLoading: ordersLoading, refetch: refetchOrders } = useBridgeOrders(
    statusFilter ? { status: statusFilter } : undefined
  );
  const { data: patterns, isLoading: patternsLoading, refetch: refetchPatterns } = useBridgePatterns();
  const { data: bridgeStatus } = useBridgeStatus();
  const deletarPattern = useDeletarBridgePattern();
  const criarPedido = useCriarPedidoFromBridge();
  const validarEAprender = useValidarEAprenderBridge();
  const reparseOrder = useReparseBridgeOrder();

  function handleCriarPedido(orderId: number) {
    criarPedido.mutate(orderId, {
      onSuccess: (data) => {
        toast.success(`Pedido #${data.comanda} criado!`);
        refetchOrders();
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.detail || "Erro ao criar pedido");
      },
    });
  }

  function handleValidarEAprender(orderId: number) {
    validarEAprender.mutate(
      { orderId, gerarPattern: true },
      {
        onSuccess: (data) => {
          if (data.pattern_criado) {
            toast.success(`Padrão aprendido! ${data.campos_mapeados} campos mapeados`);
          } else if (data.pattern_atualizado) {
            toast.success("Padrão existente atualizado com novos campos");
          } else if (data.pattern_erro) {
            toast.info(`Validado, mas: ${data.pattern_erro}`);
          } else {
            toast.success("Parse validado!");
          }
          refetchOrders();
          refetchPatterns();
        },
        onError: (err: any) => {
          toast.error(err?.response?.data?.detail || "Erro ao validar");
        },
      }
    );
  }

  function handleReparse(orderId: number) {
    reparseOrder.mutate(orderId, {
      onSuccess: () => {
        toast.success("Re-parseado com sucesso pela IA!");
        refetchOrders();
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.detail || "IA não conseguiu parsear");
      },
    });
  }

  function handleDeletarPattern(patternId: number) {
    deletarPattern.mutate(patternId, {
      onSuccess: () => {
        toast.success("Padrão removido");
        refetchPatterns();
      },
      onError: () => toast.error("Erro ao remover padrão"),
    });
  }

  const orders = ordersData?.orders || [];
  const totalOrders = ordersData?.total || 0;

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Printer className="h-6 w-6 text-[var(--cor-primaria)]" />
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">Bridge Impressora</h2>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => { refetchOrders(); refetchPatterns(); }}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Atualizar
          </Button>
        </div>

        {/* Status cards */}
        {bridgeStatus && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-[var(--text-primary)]">{bridgeStatus.total_interceptados}</p>
                <p className="text-xs text-[var(--text-muted)]">Interceptados</p>
              </CardContent>
            </Card>
            <Card className="border-green-500/20 bg-green-500/5">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-green-400">{bridgeStatus.processados}</p>
                <p className="text-xs text-[var(--text-muted)]">Processados</p>
              </CardContent>
            </Card>
            <Card className="border-red-500/20 bg-red-500/5">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-red-400">{bridgeStatus.falhou}</p>
                <p className="text-xs text-[var(--text-muted)]">Falhou</p>
              </CardContent>
            </Card>
            <Card className="border-purple-500/20 bg-purple-500/5">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-purple-400">{bridgeStatus.patterns_total}</p>
                <p className="text-xs text-[var(--text-muted)]">Padrões</p>
              </CardContent>
            </Card>
            <Card className="border-blue-500/20 bg-blue-500/5">
              <CardContent className="p-3 text-center">
                <div className="flex items-center justify-center gap-1.5">
                  <Zap className="h-4 w-4 text-blue-400" />
                  <p className="text-sm font-bold text-blue-400">
                    {bridgeStatus.ia_disponivel === "groq" ? "Groq" :
                     bridgeStatus.ia_disponivel === "grok_fallback" ? "Grok" : "Sem IA"}
                  </p>
                </div>
                <p className="text-xs text-[var(--text-muted)]">Motor IA</p>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Aviso se IA não configurada */}
        {bridgeStatus?.ia_disponivel === "nenhuma" && (
          <Card className="border-amber-500/30 bg-amber-500/10">
            <CardContent className="p-4 flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0" />
              <div>
                <p className="text-sm font-medium text-amber-300">IA não configurada</p>
                <p className="text-xs text-amber-400/80">
                  Configure GROQ_API_KEY no servidor para ativar parsing inteligente.
                  Sem IA, apenas padrões regex salvos serão usados.
                  Cadastre-se grátis em console.groq.com
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Info card */}
        <Card className="border-blue-500/20 bg-blue-500/5">
          <CardContent className="p-4">
            <p className="text-sm text-blue-300">
              O Bridge Agent intercepta impressões de plataformas externas (iFood, Rappi, 99Food, etc.)
              e cria pedidos automaticamente no Derekh Food. O sistema aprende padrões: primeiro usa
              IA (Groq) para parsear, depois gera regex automáticos para processar sem IA.
            </p>
          </CardContent>
        </Card>

        {/* Tabs */}
        <div className="flex gap-2 border-b border-[var(--border-subtle)] pb-2">
          <button
            onClick={() => setTab("interceptados")}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              tab === "interceptados"
                ? "bg-[var(--cor-primaria)] text-white"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            Pedidos Interceptados ({totalOrders})
          </button>
          <button
            onClick={() => setTab("padroes")}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              tab === "padroes"
                ? "bg-[var(--cor-primaria)] text-white"
                : "text-[var(--text-muted)] hover:text-[var(--text-primary)]"
            }`}
          >
            Padrões Aprendidos ({(patterns || []).length})
          </button>
        </div>

        {/* Tab: Interceptados */}
        {tab === "interceptados" && (
          <div className="space-y-3">
            {/* Filtros */}
            <div className="flex gap-2 flex-wrap">
              {[
                { label: "Todos", value: undefined },
                { label: "Pendentes", value: "pendente" },
                { label: "Processados", value: "processado" },
                { label: "Validados", value: "validado" },
                { label: "Falhou", value: "falhou" },
              ].map((f) => (
                <Button
                  key={f.label}
                  variant={statusFilter === f.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(f.value)}
                  className={statusFilter === f.value ? "bg-[var(--cor-primaria)]" : ""}
                >
                  {f.label}
                </Button>
              ))}
            </div>

            {ordersLoading ? (
              <p className="text-sm text-[var(--text-muted)] py-8 text-center">Carregando...</p>
            ) : orders.length === 0 ? (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="flex flex-col items-center py-12">
                  <FileText className="h-12 w-12 text-[var(--text-muted)] mb-3" />
                  <p className="text-sm text-[var(--text-muted)]">Nenhum pedido interceptado</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Instale o Bridge Agent no Windows para começar
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {orders.map((order: any) => (
                  <Card key={order.id} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0 space-y-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge
                              className={`text-xs border ${
                                PLATAFORMA_CORES[order.plataforma_detectada] ||
                                PLATAFORMA_CORES.desconhecido
                              }`}
                            >
                              {order.plataforma_detectada || "?"}
                            </Badge>
                            <Badge
                              variant="outline"
                              className={`text-xs ${
                                order.status === "processado"
                                  ? "text-green-400 border-green-500/30"
                                  : order.status === "validado"
                                  ? "text-blue-400 border-blue-500/30"
                                  : order.status === "falhou"
                                  ? "text-red-400 border-red-500/30"
                                  : "text-yellow-400 border-yellow-500/30"
                              }`}
                            >
                              {order.status}
                            </Badge>
                            {order.pedido_id && (
                              <Badge variant="outline" className="text-xs text-green-400 border-green-500/30">
                                Pedido #{order.pedido_id}
                              </Badge>
                            )}
                            {order.pattern_id && (
                              <Badge variant="outline" className="text-xs text-purple-400 border-purple-500/30">
                                Pattern #{order.pattern_id}
                              </Badge>
                            )}
                            <span className="text-xs text-[var(--text-muted)]">
                              {order.impressora_origem}
                            </span>
                          </div>

                          {order.dados_parseados && (
                            <div className="text-sm text-[var(--text-primary)]">
                              <p className="font-medium">
                                {order.dados_parseados.cliente_nome || "Cliente"}
                                {order.dados_parseados.cliente_telefone && (
                                  <span className="text-[var(--text-muted)] ml-2">
                                    {order.dados_parseados.cliente_telefone}
                                  </span>
                                )}
                              </p>
                              {order.dados_parseados.itens && Array.isArray(order.dados_parseados.itens) && (
                                <p className="text-xs text-[var(--text-muted)] truncate">
                                  {order.dados_parseados.itens
                                    .map((i: any) => `${i.quantidade || 1}x ${i.nome || "?"}`)
                                    .join(", ")}
                                </p>
                              )}
                              {order.dados_parseados.valor_total && (
                                <p className="text-sm font-semibold text-[var(--cor-primaria)]">
                                  R$ {Number(order.dados_parseados.valor_total).toFixed(2)}
                                </p>
                              )}
                            </div>
                          )}

                          {order.erro_mensagem && (
                            <p className="text-xs text-red-400">{order.erro_mensagem}</p>
                          )}

                          <p className="text-xs text-[var(--text-muted)]">
                            {order.criado_em ? new Date(order.criado_em).toLocaleString("pt-BR") : ""}
                          </p>
                        </div>

                        <div className="shrink-0 flex flex-col gap-1.5">
                          {/* Botão Criar Pedido — para pendentes com dados */}
                          {(order.status === "pendente" || order.status === "validado") && order.dados_parseados && !order.pedido_id && (
                            <Button
                              size="sm"
                              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90 gap-1.5"
                              onClick={() => handleCriarPedido(order.id)}
                              disabled={criarPedido.isPending}
                            >
                              <Plus className="h-3.5 w-3.5" />
                              Criar Pedido
                            </Button>
                          )}

                          {/* Botão Validar e Aprender — para pendentes parseados por IA */}
                          {order.status === "pendente" && order.dados_parseados && !order.pattern_id && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1.5 text-purple-400 border-purple-500/30 hover:bg-purple-500/10"
                              onClick={() => handleValidarEAprender(order.id)}
                              disabled={validarEAprender.isPending}
                            >
                              <Brain className="h-3.5 w-3.5" />
                              Validar e Aprender
                            </Button>
                          )}

                          {/* Botão Re-parsear — para que falharam */}
                          {order.status === "falhou" && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="gap-1.5 text-blue-400 border-blue-500/30 hover:bg-blue-500/10"
                              onClick={() => handleReparse(order.id)}
                              disabled={reparseOrder.isPending}
                            >
                              <RotateCcw className="h-3.5 w-3.5" />
                              Re-parsear IA
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab: Padrões */}
        {tab === "padroes" && (
          <div className="space-y-3">
            {patternsLoading ? (
              <p className="text-sm text-[var(--text-muted)] py-8 text-center">Carregando...</p>
            ) : (patterns || []).length === 0 ? (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="flex flex-col items-center py-12">
                  <Brain className="h-12 w-12 text-[var(--text-muted)] mb-3" />
                  <p className="text-sm text-[var(--text-muted)]">Nenhum padrão aprendido</p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">
                    Quando a IA (Groq) parsear cupons e você validar, o sistema gera padrões automaticamente
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {(patterns || []).map((p: any) => (
                  <Card key={p.id} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between gap-4">
                        <div className="flex-1 min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <Badge
                              className={`text-xs border ${
                                PLATAFORMA_CORES[p.plataforma] || PLATAFORMA_CORES.desconhecido
                              }`}
                            >
                              {p.plataforma}
                            </Badge>
                            <span className="text-sm font-medium text-[var(--text-primary)]">
                              {p.nome_pattern || `Padrão #${p.id}`}
                            </span>
                            {p.validado && (
                              <Badge className="bg-green-500/20 text-green-400 border-green-500/30 text-xs gap-1">
                                <CheckCircle2 className="h-3 w-3" />
                                Validado
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-[var(--text-muted)]">
                            <span className="flex items-center gap-1">
                              <TrendingUp className="h-3 w-3" />
                              Confiança: {((p.confianca || 0) * 100).toFixed(0)}%
                            </span>
                            <span>Usos: {p.usos || 0}</span>
                            <span>
                              Campos: {p.mapeamento_json ? Object.keys(p.mapeamento_json).length : 0}
                            </span>
                            <span>
                              {p.criado_em ? new Date(p.criado_em).toLocaleDateString("pt-BR") : ""}
                            </span>
                          </div>
                          {p.mapeamento_json && (
                            <div className="flex gap-1.5 flex-wrap mt-1">
                              {Object.keys(p.mapeamento_json).map((campo) => (
                                <Badge key={campo} variant="outline" className="text-[10px] text-[var(--text-muted)]">
                                  {campo}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>

                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon-sm" className="text-red-400">
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Remover padrão?</AlertDialogTitle>
                              <AlertDialogDescription>
                                O padrão "{p.nome_pattern || `#${p.id}`}" será removido permanentemente.
                                Novos cupons desta plataforma voltarão a usar IA para parsing.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancelar</AlertDialogCancel>
                              <AlertDialogAction
                                className="bg-red-600 hover:bg-red-700"
                                onClick={() => handleDeletarPattern(p.id)}
                              >
                                Remover
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
