import { useLocation } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useDashboard,
  useDashboardGrafico,
  usePedidos,
  useCaixaAtual,
  useAbrirCaixa,
  useAtualizarConfig,
  useConfig,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ShoppingBag,
  DollarSign,
  TrendingUp,
  Users,
  Bike,
  Vault,
  Store,
  Eye,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pendente: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  em_preparo: { label: "Em Preparo", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  pronto: { label: "Pronto", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  em_entrega: { label: "Em Entrega", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  entregue: { label: "Entregue", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  cancelado: { label: "Cancelado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

export default function Dashboard() {
  const [, navigate] = useLocation();
  const { data, isLoading } = useDashboard();
  const { data: graficoData } = useDashboardGrafico("7d");
  const { data: config } = useConfig();
  const { data: pedidosData } = usePedidos({ limite: 5 });
  const { data: caixaData } = useCaixaAtual();
  const atualizarConfig = useAtualizarConfig();
  const abrirCaixa = useAbrirCaixa();

  const pedidosRecentes = pedidosData?.pedidos || [];
  const caixaAberto = caixaData?.status === "aberto";
  const restauranteAberto = config?.status_atual === "aberto";

  function toggleRestaurante() {
    const novoStatus = restauranteAberto ? "fechado" : "aberto";
    atualizarConfig.mutate(
      { status_atual: novoStatus },
      {
        onSuccess: () => toast.success(`Restaurante ${novoStatus === "aberto" ? "aberto" : "fechado"}!`),
        onError: () => toast.error("Erro ao alterar status"),
      }
    );
  }

  function handleAbrirCaixa() {
    abrirCaixa.mutate(0, {
      onSuccess: () => toast.success("Caixa aberto!"),
      onError: () => toast.error("Erro ao abrir caixa"),
    });
  }

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Dashboard</h2>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={restauranteAberto ? "outline" : "default"}
              className={restauranteAberto
                ? "border-red-500/30 text-red-400 hover:bg-red-500/10"
                : "bg-green-600 hover:bg-green-700"
              }
              onClick={toggleRestaurante}
              disabled={atualizarConfig.isPending}
            >
              <Store className="mr-1 h-4 w-4" />
              {restauranteAberto ? "Fechar Restaurante" : "Abrir Restaurante"}
            </Button>
            {!caixaAberto && (
              <Button
                size="sm"
                className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                onClick={handleAbrirCaixa}
                disabled={abrirCaixa.isPending}
              >
                <Vault className="mr-1 h-4 w-4" /> Abrir Caixa
              </Button>
            )}
          </div>
        </div>

        {/* Cards de métricas */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          <MetricCard
            title="Pedidos Hoje"
            value={data?.pedidos_hoje}
            icon={ShoppingBag}
            loading={isLoading}
          />
          <MetricCard
            title="Pendentes"
            value={data?.pedidos_pendentes ?? 0}
            icon={Clock}
            loading={isLoading}
            valueColor={(data?.pedidos_pendentes ?? 0) > 0 ? "text-yellow-400" : undefined}
          />
          <MetricCard
            title="Faturamento Hoje"
            value={data?.faturamento_hoje != null ? `R$ ${Number(data.faturamento_hoje).toFixed(2)}` : undefined}
            icon={DollarSign}
            loading={isLoading}
          />
          <MetricCard
            title="Ticket Médio"
            value={data?.ticket_medio != null ? `R$ ${Number(data.ticket_medio).toFixed(2)}` : undefined}
            icon={TrendingUp}
            loading={isLoading}
          />
          <MetricCard
            title="Clientes Ativos"
            value={data?.clientes_ativos}
            icon={Users}
            loading={isLoading}
          />
          <MetricCard
            title="Motoboys Online"
            value={data?.motoboys_online ?? 0}
            icon={Bike}
            loading={isLoading}
          />
          <MetricCard
            title="Caixa"
            value={caixaAberto ? "Aberto" : "Fechado"}
            icon={Vault}
            loading={isLoading}
            valueColor={caixaAberto ? "text-green-400" : "text-red-400"}
          />
        </div>

        {/* Gráfico e Pedidos Recentes */}
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader>
              <CardTitle className="text-[var(--text-primary)]">
                Vendas dos Últimos 7 Dias
              </CardTitle>
            </CardHeader>
            <CardContent>
              {graficoData && Array.isArray(graficoData) && graficoData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={graficoData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis
                      dataKey="data"
                      tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                      tickFormatter={(v: string) => {
                        const d = new Date(v + "T00:00:00");
                        return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
                      }}
                    />
                    <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 8,
                        color: "var(--text-primary)",
                      }}
                      formatter={(value: number) => [`R$ ${value.toFixed(2)}`, "Faturamento"]}
                      labelFormatter={(label: string) => {
                        const d = new Date(label + "T00:00:00");
                        return d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });
                      }}
                    />
                    <Bar dataKey="faturamento" fill="var(--cor-primaria)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-48 items-center justify-center text-[var(--text-muted)]">
                  Sem dados de vendas no período
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-[var(--text-primary)]">Pedidos Recentes</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-[var(--cor-primaria)]"
                  onClick={() => navigate("/pedidos")}
                >
                  Ver todos
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {pedidosRecentes.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-[var(--text-muted)]">
                  Nenhum pedido recente
                </div>
              ) : (
                <div className="space-y-3">
                  {pedidosRecentes.map((p: Record<string, unknown>) => {
                    const st = STATUS_MAP[p.status as string] || { label: p.status, color: "bg-gray-500/20 text-gray-400" };
                    return (
                      <div
                        key={p.id as number}
                        className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-3 cursor-pointer hover:bg-[var(--bg-card-hover)] transition-colors"
                        onClick={() => navigate(`/pedidos/${p.id}`)}
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-[var(--text-muted)]">
                            #{String(p.comanda || p.id)}
                          </span>
                          <div>
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              {(p.cliente_nome as string) || "Sem nome"}
                            </p>
                            <p className="text-xs text-[var(--text-muted)]">{formatDate(p.data_criacao as string)}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-[var(--text-primary)]">
                            R$ {Number(p.valor_total).toFixed(2)}
                          </span>
                          <Badge className={`${st.color} border text-xs`}>{st.label}</Badge>
                          <Eye className="h-4 w-4 text-[var(--text-muted)]" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}

function MetricCard({
  title,
  value,
  icon: Icon,
  loading,
  valueColor,
}: {
  title: string;
  value?: string | number;
  icon: React.ComponentType<{ className?: string }>;
  loading: boolean;
  valueColor?: string;
}) {
  return (
    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--cor-primaria)]/10">
          <Icon className="h-6 w-6 text-[var(--cor-primaria)]" />
        </div>
        <div>
          <p className="text-sm text-[var(--text-muted)]">{title}</p>
          {loading ? (
            <Skeleton className="mt-1 h-7 w-20" />
          ) : (
            <p className={`text-2xl font-bold ${valueColor || "text-[var(--text-primary)]"}`}>
              {value ?? "—"}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
