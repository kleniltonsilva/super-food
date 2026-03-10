import { useState } from "react";
import { useLocation } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  usePedidos,
  useAtualizarStatusPedido,
  useCancelarPedido,
  useDespacharPedido,
  useDashboard,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
  Search,
  Plus,
  MoreHorizontal,
  Eye,
  CheckCircle,
  XCircle,
  ChefHat,
  Truck,
  Clock,
  RefreshCw,
  Send,
  Bike,
  Globe,
  Smartphone,
} from "lucide-react";
import { toast } from "sonner";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pendente: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  em_preparo: { label: "Em Preparo", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  pronto: { label: "Pronto", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  em_entrega: { label: "Em Entrega", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  entregue: { label: "Entregue", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  cancelado: { label: "Cancelado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
  recusado: { label: "Recusado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

const STATUS_FLOW: Record<string, string[]> = {
  pendente: ["em_preparo", "cancelado"],
  em_preparo: ["pronto", "cancelado"],
  pronto: ["em_entrega", "entregue", "cancelado"],
  em_entrega: ["entregue"],
};

export default function Pedidos() {
  const [, navigate] = useLocation();
  const [statusFilter, setStatusFilter] = useState<string>("todos");
  const [busca, setBusca] = useState("");
  const [cancelarId, setCancelarId] = useState<number | null>(null);
  const [tab, setTab] = useState("ativos");
  const [histDataInicio, setHistDataInicio] = useState("");
  const [histDataFim, setHistDataFim] = useState("");

  // Params para pedidos ativos
  const ativosParams: Record<string, unknown> = {};
  if (statusFilter !== "todos") ativosParams.status = statusFilter;
  if (busca.trim()) ativosParams.busca = busca.trim();

  // Params para histórico
  const histParams: Record<string, unknown> = { status: "entregue,cancelado" };
  if (histDataInicio) histParams.data_inicio = histDataInicio;
  if (histDataFim) histParams.data_fim = histDataFim;

  const { data, isLoading, refetch } = usePedidos(tab === "ativos" ? ativosParams : histParams);
  const { data: dashData } = useDashboard();
  const atualizarStatus = useAtualizarStatusPedido();
  const cancelar = useCancelarPedido();
  const despachar = useDespacharPedido();

  const pedidos = data?.pedidos || [];

  // Pedidos prontos para despacho
  const pedidosProntos = (tab === "ativos" ? pedidos : []).filter(
    (p: Record<string, unknown>) => p.status === "pronto"
  );

  function handleStatusChange(id: number, status: string) {
    atualizarStatus.mutate(
      { id, status },
      {
        onSuccess: () => toast.success(`Pedido #${id} atualizado para ${STATUS_MAP[status]?.label || status}`),
        onError: () => toast.error("Erro ao atualizar status"),
      }
    );
  }

  function handleCancelar() {
    if (!cancelarId) return;
    cancelar.mutate(
      { id: cancelarId },
      {
        onSuccess: () => {
          toast.success("Pedido cancelado");
          setCancelarId(null);
        },
        onError: () => toast.error("Erro ao cancelar pedido"),
      }
    );
  }

  function handleDespacharProntos() {
    if (pedidosProntos.length === 0) return;
    let count = 0;
    for (const p of pedidosProntos) {
      atualizarStatus.mutate(
        { id: p.id as number, status: "em_entrega" },
        {
          onSuccess: () => {
            count++;
            if (count === pedidosProntos.length) {
              toast.success(`${count} pedido(s) despachado(s)`);
            }
          },
        }
      );
    }
  }

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  function getOrigemBadge(p: Record<string, unknown>) {
    const origem = p.origem as string;
    if (origem === "site" || origem === "web") {
      return <span title="Site"><Globe className="h-4 w-4 text-blue-400" /></span>;
    }
    return <span title="Manual"><Smartphone className="h-4 w-4 text-orange-400" /></span>;
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Pedidos</h2>
          <div className="flex gap-2">
            {pedidosProntos.length > 0 && tab === "ativos" && (
              <Button
                size="sm"
                className="bg-green-600 hover:bg-green-700"
                onClick={handleDespacharProntos}
                disabled={atualizarStatus.isPending}
              >
                <Send className="mr-1 h-4 w-4" /> Despachar Prontos ({pedidosProntos.length})
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => refetch()}
              className="border-[var(--border-subtle)]"
            >
              <RefreshCw className="mr-1 h-4 w-4" /> Atualizar
            </Button>
            <Button
              size="sm"
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={() => navigate("/pedidos/novo")}
            >
              <Plus className="mr-1 h-4 w-4" /> Novo Pedido
            </Button>
          </div>
        </div>

        {/* Barra de capacidade motoboys */}
        {dashData && (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardContent className="flex items-center gap-4 p-3">
              <Bike className="h-5 w-5 text-[var(--cor-primaria)]" />
              <div className="flex gap-4 text-sm">
                <span className="text-[var(--text-secondary)]">
                  Online: <span className="font-medium text-green-400">{dashData.motoboys_online ?? 0}</span>
                </span>
                <span className="text-[var(--text-secondary)]">
                  Em rota: <span className="font-medium text-purple-400">{dashData.motoboys_em_rota ?? 0}</span>
                </span>
                <span className="text-[var(--text-secondary)]">
                  Disponíveis: <span className="font-medium text-[var(--text-primary)]">{Math.max(0, (dashData.motoboys_online ?? 0) - (dashData.motoboys_em_rota ?? 0))}</span>
                </span>
              </div>
            </CardContent>
          </Card>
        )}

        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="ativos">Ativos</TabsTrigger>
            <TabsTrigger value="historico">Histórico</TabsTrigger>
          </TabsList>

          <TabsContent value="ativos">
            {/* Filtros */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] mb-4">
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
                  <Input
                    placeholder="Buscar por nome, telefone ou comanda..."
                    value={busca}
                    onChange={(e) => setBusca(e.target.value)}
                    className="dark-input pl-9"
                  />
                </div>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-full sm:w-48 dark-input">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="todos">Todos</SelectItem>
                    <SelectItem value="pendente">Pendente</SelectItem>
                    <SelectItem value="em_preparo">Em Preparo</SelectItem>
                    <SelectItem value="pronto">Pronto</SelectItem>
                    <SelectItem value="em_entrega">Em Entrega</SelectItem>
                    <SelectItem value="entregue">Entregue</SelectItem>
                    <SelectItem value="cancelado">Cancelado</SelectItem>
                  </SelectContent>
                </Select>
              </CardContent>
            </Card>

            <p className="text-sm text-[var(--text-muted)] mb-2">
              {data?.total ?? "—"} pedido(s) encontrado(s)
            </p>

            <PedidosTabela
              pedidos={pedidos}
              isLoading={isLoading}
              navigate={navigate}
              handleStatusChange={handleStatusChange}
              setCancelarId={setCancelarId}
              formatDate={formatDate}
              getOrigemBadge={getOrigemBadge}
            />
          </TabsContent>

          <TabsContent value="historico">
            {/* Filtros histórico */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] mb-4">
              <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-end">
                <div className="space-y-1">
                  <label className="text-xs text-[var(--text-muted)]">De</label>
                  <Input type="date" value={histDataInicio} onChange={(e) => setHistDataInicio(e.target.value)} className="dark-input h-9" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-[var(--text-muted)]">Até</label>
                  <Input type="date" value={histDataFim} onChange={(e) => setHistDataFim(e.target.value)} className="dark-input h-9" />
                </div>
                <Button size="sm" onClick={() => refetch()}>Buscar</Button>
              </CardContent>
            </Card>

            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-[var(--text-muted)]">
                {data?.total ?? "—"} pedido(s) encontrado(s)
              </p>
              {pedidos.length > 0 && (
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  Total: R$ {pedidos.reduce((acc: number, p: Record<string, unknown>) => acc + Number(p.valor_total || 0), 0).toFixed(2)}
                </p>
              )}
            </div>

            <PedidosTabela
              pedidos={pedidos}
              isLoading={isLoading}
              navigate={navigate}
              handleStatusChange={handleStatusChange}
              setCancelarId={setCancelarId}
              formatDate={formatDate}
              getOrigemBadge={getOrigemBadge}
            />
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialog cancelar */}
      <AlertDialog open={cancelarId !== null} onOpenChange={() => setCancelarId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Cancelar Pedido</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja cancelar o pedido #{cancelarId}? Esta ação não pode ser desfeita.
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
    </AdminLayout>
  );
}

function PedidosTabela({
  pedidos,
  isLoading,
  navigate,
  handleStatusChange,
  setCancelarId,
  formatDate,
  getOrigemBadge,
}: {
  pedidos: Record<string, unknown>[];
  isLoading: boolean;
  navigate: (path: string) => void;
  handleStatusChange: (id: number, status: string) => void;
  setCancelarId: (id: number | null) => void;
  formatDate: (iso: string | null) => string;
  getOrigemBadge: (p: Record<string, unknown>) => React.ReactNode;
}) {
  return (
    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-[var(--border-subtle)]">
              <TableHead className="text-[var(--text-muted)]">#</TableHead>
              <TableHead className="text-[var(--text-muted)]">Cliente</TableHead>
              <TableHead className="text-[var(--text-muted)]">Tipo</TableHead>
              <TableHead className="text-[var(--text-muted)]">Valor</TableHead>
              <TableHead className="text-[var(--text-muted)]">Status</TableHead>
              <TableHead className="text-[var(--text-muted)]">Data</TableHead>
              <TableHead className="text-[var(--text-muted)] text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i} className="border-[var(--border-subtle)]">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-5 w-20" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : pedidos.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-12 text-center text-[var(--text-muted)]">
                  Nenhum pedido encontrado
                </TableCell>
              </TableRow>
            ) : (
              pedidos.map((p: Record<string, unknown>) => {
                const st = STATUS_MAP[p.status as string] || { label: p.status, color: "bg-gray-500/20 text-gray-400" };
                return (
                  <TableRow
                    key={p.id as number}
                    className="border-[var(--border-subtle)] cursor-pointer hover:bg-[var(--bg-card-hover)]"
                    onClick={() => navigate(`/pedidos/${p.id}`)}
                  >
                    <TableCell className="font-mono text-[var(--text-primary)]">
                      <div className="flex items-center gap-1.5">
                        {getOrigemBadge(p)}
                        #{String(p.comanda || p.id)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {(p.cliente_nome as string) || "Sem nome"}
                        </p>
                        {p.cliente_telefone ? (
                          <p className="text-xs text-[var(--text-muted)]">{p.cliente_telefone as string}</p>
                        ) : null}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-[var(--border-subtle)] text-[var(--text-secondary)]">
                        {(p.tipo_entrega as string) || (p.tipo as string) || "—"}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium text-[var(--text-primary)]">
                      R$ {Number(p.valor_total).toFixed(2)}
                    </TableCell>
                    <TableCell>
                      <Badge className={`${st.color} border`}>{st.label}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-[var(--text-muted)]">
                      {formatDate(p.data_criacao as string)}
                    </TableCell>
                    <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon-sm">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => navigate(`/pedidos/${p.id}`)}>
                            <Eye className="mr-2 h-4 w-4" /> Ver Detalhes
                          </DropdownMenuItem>
                          {(STATUS_FLOW[p.status as string] || []).map((nextStatus) => {
                            if (nextStatus === "cancelado") {
                              return (
                                <DropdownMenuItem
                                  key={nextStatus}
                                  onClick={() => setCancelarId(p.id as number)}
                                  className="text-red-400"
                                >
                                  <XCircle className="mr-2 h-4 w-4" /> Cancelar
                                </DropdownMenuItem>
                              );
                            }
                            const icon =
                              nextStatus === "em_preparo" ? <ChefHat className="mr-2 h-4 w-4" /> :
                              nextStatus === "pronto" ? <CheckCircle className="mr-2 h-4 w-4" /> :
                              nextStatus === "em_entrega" ? <Truck className="mr-2 h-4 w-4" /> :
                              nextStatus === "entregue" ? <CheckCircle className="mr-2 h-4 w-4" /> :
                              <Clock className="mr-2 h-4 w-4" />;
                            return (
                              <DropdownMenuItem
                                key={nextStatus}
                                onClick={() => handleStatusChange(p.id as number, nextStatus)}
                              >
                                {icon} {STATUS_MAP[nextStatus]?.label || nextStatus}
                              </DropdownMenuItem>
                            );
                          })}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </Card>
  );
}
