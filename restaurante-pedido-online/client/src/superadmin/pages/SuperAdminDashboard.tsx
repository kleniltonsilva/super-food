import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useMetricas, useAnalytics } from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Store,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Bike,
  ShoppingBag,
  AlertTriangle,
  Clock,
  Users,
  Search,
  ArrowUpDown,
  Medal,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { cn } from "@/lib/utils";

const CORES_PIE = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4", "#f97316", "#ec4899"];

function fmt(value: number | undefined | null) {
  if (value == null || isNaN(value)) return "R$ 0,00";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function fmtPct(value: number | undefined | null) {
  if (value == null || isNaN(value)) return "0%";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}%`;
}

interface MiniCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  subtitle?: string;
}

function MiniCard({ label, value, icon: Icon, color, subtitle }: MiniCardProps) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
      <div className="flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-xs text-gray-400 truncate">{label}</p>
          <p className="mt-0.5 text-xl font-bold text-white truncate">{value}</p>
          {subtitle && <p className="mt-0.5 text-[11px] text-gray-500 truncate">{subtitle}</p>}
        </div>
        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-5 w-5 text-white" />
        </div>
      </div>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function renderPieLabel(entry: any) {
  return `${entry?.forma || entry?.tipo || entry?.name || ""}: ${entry?.percentual?.toFixed(0) || 0}%`;
}

export default function SuperAdminDashboard() {
  const [periodo, setPeriodo] = useState("30d");
  const [buscaSaude, setBuscaSaude] = useState("");
  const [sortKey, setSortKey] = useState("faturamento_mes");
  const [sortAsc, setSortAsc] = useState(false);

  const { data: metricas, isLoading: loadingMetricas } = useMetricas();
  const { data: analytics, isLoading: loadingAnalytics } = useAnalytics(periodo);

  if (loadingMetricas && loadingAnalytics) {
    return (
      <SuperAdminLayout>
        <div className="flex h-64 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-500" />
        </div>
      </SuperAdminLayout>
    );
  }

  const m = metricas ?? {};
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const a: Record<string, any> = analytics ?? {};

  const totalRest = m.total_restaurantes ?? 0;
  const ativos = m.restaurantes_ativos ?? 0;
  const totalMotoboys = m.total_motoboys ?? 0;
  const motoboysOnline = m.motoboys_online ?? 0;

  // Analytics data
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const topRest: any[] = a.top_restaurantes || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tendencia: any[] = a.tendencia_faturamento || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const formasPgto: any[] = a.formas_pagamento || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const tiposEntrega: any[] = a.tipos_entrega || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const saudeRaw: any[] = a.saude_restaurantes || [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const inativos: any[] = a.restaurantes_inativos || [];

  // Filtrar e ordenar saúde
  const saudeFiltrada = saudeRaw
    .filter((r) => !buscaSaude || r.nome?.toLowerCase().includes(buscaSaude.toLowerCase()))
    .sort((x, y) => {
      const a = x[sortKey] ?? 0;
      const b = y[sortKey] ?? 0;
      return sortAsc ? (a > b ? 1 : -1) : (a < b ? 1 : -1);
    });

  function toggleSort(key: string) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(false); }
  }

  const medalhas = ["text-yellow-400", "text-gray-300", "text-amber-600"];

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold text-white">Dashboard Analytics</h2>
          <div className="flex gap-2">
            {["7d", "30d", "90d"].map((p) => (
              <Button
                key={p}
                size="sm"
                variant={periodo === p ? "default" : "outline"}
                className={periodo === p ? "bg-amber-600 hover:bg-amber-700 text-white" : "border-gray-700 text-gray-300 hover:bg-gray-800"}
                onClick={() => setPeriodo(p)}
              >
                {p === "7d" ? "7 dias" : p === "30d" ? "30 dias" : "90 dias"}
              </Button>
            ))}
          </div>
        </div>

        {/* Cards Faturamento */}
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-400 uppercase tracking-wider">Faturamento Real</h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MiniCard label="Hoje" value={fmt(a.faturamento_hoje)} icon={DollarSign} color="bg-green-600" />
            <MiniCard label="Semana" value={fmt(a.faturamento_semana)} icon={DollarSign} color="bg-green-600" />
            <MiniCard label="Mês" value={fmt(a.faturamento_mes)} icon={DollarSign} color="bg-green-600" subtitle={`Anterior: ${fmt(a.faturamento_mes_anterior)}`} />
            <MiniCard label="Mês Anterior (bruto)" value={fmt(a.faturamento_mes_anterior_bruto)} icon={DollarSign} color="bg-gray-600" subtitle={`Líquido: ${fmt(a.faturamento_mes_anterior)}`} />
          </div>
        </div>

        {/* Cards Pedidos */}
        <div>
          <h3 className="mb-3 text-sm font-medium text-gray-400 uppercase tracking-wider">Pedidos</h3>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <MiniCard label="Pedidos Hoje" value={a.pedidos_hoje ?? 0} icon={ShoppingBag} color="bg-purple-600" subtitle={`${a.cancelamentos_hoje ?? 0} cancelados`} />
            <MiniCard label="Pedidos Mês" value={a.pedidos_mes ?? 0} icon={ShoppingBag} color="bg-purple-600" subtitle={`${a.cancelamentos_mes ?? 0} cancelados`} />
            <MiniCard label="Taxa Cancelamento" value={`${(a.taxa_cancelamento_mes ?? 0).toFixed(1)}%`} icon={AlertTriangle} color={a.taxa_cancelamento_mes > 10 ? "bg-red-600" : "bg-orange-600"} />
            <MiniCard label="Ticket Médio" value={fmt(a.ticket_medio_real)} icon={TrendingUp} color="bg-amber-600" />
          </div>
        </div>

        {/* Cards Infra (existente) */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <MiniCard label="Restaurantes" value={totalRest} icon={Store} color="bg-blue-600" subtitle={`${ativos} ativos`} />
          <MiniCard label="Motoboys" value={totalMotoboys} icon={Bike} color="bg-cyan-600" subtitle={`${motoboysOnline} online`} />
          <MiniCard label="Motoboys Ociosos" value={a.motoboys_ociosos ?? 0} icon={Bike} color="bg-orange-600" subtitle="Sem entrega 7 dias" />
          <MiniCard
            label="Crescimento MoM"
            value={fmtPct(a.crescimento_mom)}
            icon={a.crescimento_mom >= 0 ? TrendingUp : TrendingDown}
            color={a.crescimento_mom >= 0 ? "bg-green-600" : "bg-red-600"}
          />
        </div>

        {/* TOP 5 Restaurantes */}
        {topRest.length > 0 && (
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Medal className="h-5 w-5 text-amber-400" />
                Top 5 Restaurantes — Faturamento no Mês
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-gray-800 hover:bg-transparent">
                      <TableHead className="text-gray-400 w-10">#</TableHead>
                      <TableHead className="text-gray-400">Restaurante</TableHead>
                      <TableHead className="text-gray-400 text-right">Faturamento</TableHead>
                      <TableHead className="text-gray-400 text-right">Pedidos</TableHead>
                      <TableHead className="text-gray-400 text-right">Ticket Médio</TableHead>
                      <TableHead className="text-gray-400 text-right">Cancelamentos</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {topRest.map((r: any, idx: number) => (
                      <TableRow key={r.id} className="border-gray-800 hover:bg-gray-800/50">
                        <TableCell>
                          <Medal className={cn("h-5 w-5", idx < 3 ? medalhas[idx] : "text-gray-600")} />
                        </TableCell>
                        <TableCell className="font-medium text-white">{r.nome}</TableCell>
                        <TableCell className="text-right font-semibold text-green-400">{fmt(r.faturamento)}</TableCell>
                        <TableCell className="text-right text-gray-300">{r.total_pedidos}</TableCell>
                        <TableCell className="text-right text-gray-300">{fmt(r.ticket_medio)}</TableCell>
                        <TableCell className="text-right">
                          <span className={r.cancelamentos > 0 ? "text-red-400" : "text-gray-500"}>
                            {r.cancelamentos}
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Gráficos */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Tendência Faturamento */}
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <CardTitle className="text-white text-base">Tendência de Faturamento</CardTitle>
            </CardHeader>
            <CardContent>
              {tendencia.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <LineChart data={tendencia}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="data" stroke="#9ca3af" fontSize={11} tickFormatter={(v: string) => v.slice(5)} />
                    <YAxis stroke="#9ca3af" fontSize={11} tickFormatter={(v: number) => `R$${v}`} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                      labelStyle={{ color: "#fff" }}
                      formatter={(value: number, name: string) => [name === "faturamento" ? fmt(value) : value, name === "faturamento" ? "Faturamento" : "Pedidos"]}
                    />
                    <Line type="monotone" dataKey="faturamento" stroke="#10b981" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="pedidos" stroke="#f59e0b" strokeWidth={1.5} dot={false} yAxisId={0} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <p className="py-10 text-center text-gray-500">Sem dados no período</p>
              )}
            </CardContent>
          </Card>

          {/* Formas de Pagamento */}
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <CardTitle className="text-white text-base">Formas de Pagamento</CardTitle>
            </CardHeader>
            <CardContent>
              {formasPgto.length > 0 ? (
                <div className="flex flex-col items-center">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={formasPgto} cx="50%" cy="50%" outerRadius={80} dataKey="total" nameKey="forma" label={renderPieLabel}>
                        {formasPgto.map((_: unknown, idx: number) => (
                          <Cell key={idx} fill={CORES_PIE[idx % CORES_PIE.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                        formatter={(value: number, name: string) => [value, name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="mt-2 flex flex-wrap justify-center gap-3">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {formasPgto.map((f: any, idx: number) => (
                      <div key={f.forma} className="flex items-center gap-1.5">
                        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: CORES_PIE[idx % CORES_PIE.length] }} />
                        <span className="text-xs text-gray-400">{f.forma} ({f.total})</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="py-10 text-center text-gray-500">Sem dados</p>
              )}
            </CardContent>
          </Card>

          {/* Tipo Entrega */}
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <CardTitle className="text-white text-base">Tipo de Entrega</CardTitle>
            </CardHeader>
            <CardContent>
              {tiposEntrega.length > 0 ? (
                <div className="flex flex-col items-center">
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie data={tiposEntrega} cx="50%" cy="50%" outerRadius={80} dataKey="total" nameKey="tipo" label={renderPieLabel}>
                        {tiposEntrega.map((_: unknown, idx: number) => (
                          <Cell key={idx} fill={CORES_PIE[idx % CORES_PIE.length]} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                        formatter={(value: number, name: string) => [value, name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="py-10 text-center text-gray-500">Sem dados</p>
              )}
            </CardContent>
          </Card>

          {/* Insights */}
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <CardTitle className="text-white text-base">Insights</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center gap-3 rounded-lg border border-gray-800 p-3">
                <Clock className="h-5 w-5 text-amber-400 shrink-0" />
                <div>
                  <p className="text-sm text-gray-300">Horário Pico</p>
                  <p className="text-lg font-bold text-white">{a.horario_pico?.hora ?? "--"}h <span className="text-sm font-normal text-gray-400">({a.horario_pico?.total_pedidos ?? 0} pedidos)</span></p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-gray-800 p-3">
                <Users className="h-5 w-5 text-blue-400 shrink-0" />
                <div>
                  <p className="text-sm text-gray-300">Clientes Novos (semana)</p>
                  <p className="text-lg font-bold text-white">{a.clientes_novos_semana ?? 0}</p>
                </div>
              </div>
              <div className="flex items-center gap-3 rounded-lg border border-gray-800 p-3">
                <TrendingUp className="h-5 w-5 text-green-400 shrink-0" />
                <div>
                  <p className="text-sm text-gray-300">Crescimento Mês vs Anterior</p>
                  <p className={cn("text-lg font-bold", (a.crescimento_mom ?? 0) >= 0 ? "text-green-400" : "text-red-400")}>{fmtPct(a.crescimento_mom)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Restaurantes Inativos */}
        {inativos.length > 0 && (
          <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/5 p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-5 w-5 text-yellow-400" />
              <h3 className="text-sm font-semibold text-yellow-400">Restaurantes Inativos (sem pedidos em 7 dias)</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
              {inativos.map((r: any) => (
                <Badge key={r.id} variant="outline" className="border-yellow-500/30 text-yellow-300">
                  {r.nome}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Tabela Saúde Restaurantes */}
        {saudeRaw.length > 0 && (
          <Card className="border-gray-800 bg-gray-900">
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <CardTitle className="text-white">Saúde dos Restaurantes</CardTitle>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                  <Input
                    placeholder="Buscar restaurante..."
                    value={buscaSaude}
                    onChange={(e) => setBuscaSaude(e.target.value)}
                    className="pl-9 w-64 border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-gray-800 hover:bg-transparent">
                      <TableHead className="text-gray-400">Nome</TableHead>
                      <TableHead className="text-gray-400">Plano</TableHead>
                      {[
                        { key: "pedidos_dia", label: "Dia" },
                        { key: "pedidos_semana", label: "Sem" },
                        { key: "pedidos_mes", label: "Mês" },
                        { key: "faturamento_mes", label: "Fat. Mês" },
                        { key: "cancelamentos_mes", label: "Cancel" },
                        { key: "ticket_medio", label: "TM" },
                      ].map((col) => (
                        <TableHead
                          key={col.key}
                          className="text-gray-400 cursor-pointer hover:text-white text-right"
                          onClick={() => toggleSort(col.key)}
                        >
                          <span className="inline-flex items-center gap-1">
                            {col.label}
                            {sortKey === col.key && <ArrowUpDown className="h-3 w-3" />}
                          </span>
                        </TableHead>
                      ))}
                      <TableHead className="text-gray-400 text-right">Último</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {saudeFiltrada.slice(0, 50).map((r: any) => {
                      const ativo = r.pedidos_mes > 0;
                      const baixo = r.pedidos_mes > 0 && r.pedidos_mes < 10;
                      return (
                        <TableRow key={r.id} className="border-gray-800 hover:bg-gray-800/50">
                          <TableCell className="font-medium text-white">{r.nome}</TableCell>
                          <TableCell>
                            <Badge variant="outline" className="border-gray-600 text-gray-300 text-xs">
                              {r.plano}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right text-gray-300">{r.pedidos_dia}</TableCell>
                          <TableCell className="text-right text-gray-300">{r.pedidos_semana}</TableCell>
                          <TableCell className="text-right text-gray-300">{r.pedidos_mes}</TableCell>
                          <TableCell className="text-right font-medium text-green-400">{fmt(r.faturamento_mes)}</TableCell>
                          <TableCell className="text-right">
                            <span className={r.cancelamentos_mes > 0 ? "text-red-400" : "text-gray-500"}>
                              {r.cancelamentos_mes}
                            </span>
                          </TableCell>
                          <TableCell className="text-right text-gray-300">{fmt(r.ticket_medio)}</TableCell>
                          <TableCell className="text-right">
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                !ativo ? "border-red-500/30 text-red-400" : baixo ? "border-yellow-500/30 text-yellow-400" : "border-green-500/30 text-green-400"
                              )}
                            >
                              {r.ultimo_pedido ? new Date(r.ultimo_pedido).toLocaleDateString("pt-BR") : "Nunca"}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
              {saudeFiltrada.length > 50 && (
                <p className="mt-2 text-xs text-gray-500 text-center">Mostrando 50 de {saudeFiltrada.length} restaurantes</p>
              )}
            </CardContent>
          </Card>
        )}

        {loadingAnalytics && (
          <div className="flex items-center justify-center py-4">
            <Spinner className="h-5 w-5 text-amber-500" />
            <span className="ml-2 text-sm text-gray-400">Carregando analytics...</span>
          </div>
        )}
      </div>
    </SuperAdminLayout>
  );
}
