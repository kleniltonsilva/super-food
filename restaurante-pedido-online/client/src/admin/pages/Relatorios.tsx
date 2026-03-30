import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useRelatorioVendas,
  useRelatorioMotoboys,
  useRelatorioProdutos,
  useAnalyticsAvancado,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart3,
  Download,
  Search,
  Lock,
  TrendingUp,
  TrendingDown,
  Clock,
  Users,
  ShoppingBag,
  CreditCard,
  CalendarDays,
  Eye,
} from "lucide-react";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

const CORES = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4", "#f97316", "#ec4899"];
const DIAS_SEMANA = ["Domingo", "Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"];

function fmt(value: number | undefined | null) {
  if (value == null || isNaN(value)) return "R$ 0,00";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

export default function Relatorios() {
  const [vendasInicio, setVendasInicio] = useState("");
  const [vendasFim, setVendasFim] = useState("");
  const [motoboyInicio, setMotoboyInicio] = useState("");
  const [motoboyFim, setMotoboyFim] = useState("");

  // Analytics state
  const [senhaAnalytics, setSenhaAnalytics] = useState("");
  const [senhaConfirmada, setSenhaConfirmada] = useState("");
  const [periodoAnalytics, setPeriodoAnalytics] = useState("30d");

  const vendasParams: Record<string, unknown> = {};
  if (vendasInicio) vendasParams.data_inicio = vendasInicio;
  if (vendasFim) vendasParams.data_fim = vendasFim;

  const motoboyParams: Record<string, unknown> = {};
  if (motoboyInicio) motoboyParams.data_inicio = motoboyInicio;
  if (motoboyFim) motoboyParams.data_fim = motoboyFim;

  const { data: vendas, refetch: fetchVendas, isFetching: loadingVendas } = useRelatorioVendas(vendasParams);
  const { data: motoboysData, refetch: fetchMotoboys, isFetching: loadingMotoboys } = useRelatorioMotoboys(motoboyParams);
  const { data: produtosData, refetch: fetchProdutos, isFetching: loadingProdutos } = useRelatorioProdutos();
  const { data: analytics, isLoading: loadingAnalytics, isError: errorAnalytics } = useAnalyticsAvancado(
    senhaConfirmada ? { periodo: periodoAnalytics, senha: senhaConfirmada } : undefined
  );

  function exportCSV(headers: string[], rows: string[][], filename: string) {
    const csv = [headers.join(";"), ...rows.map((r) => r.join(";"))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  function exportVendas() {
    if (!vendas?.pedidos) return;
    const headers = ["#", "Cliente", "Plataforma", "Valor", "Pagamento", "Status", "Data"];
    const rows = vendas.pedidos.map((p: Record<string, unknown>) => [
      String(p.comanda || p.id),
      (p.cliente_nome as string) || "",
      (p.plataforma_label as string) || "",
      Number(p.valor_total).toFixed(2).replace(".", ","),
      (p.forma_pagamento as string) || "",
      p.status as string,
      (p.data_criacao as string) || "",
    ]);
    exportCSV(headers, rows, "relatorio-vendas.csv");
  }

  function exportMotoboys() {
    if (!motoboysData) return;
    const headers = ["Motoboy", "Entregas", "Ganhos", "KM"];
    const rows = (motoboysData as Record<string, unknown>[]).map((m) => [
      m.nome as string,
      String(m.total_entregas),
      Number(m.total_ganhos).toFixed(2).replace(".", ","),
      Number(m.total_km).toFixed(1).replace(".", ","),
    ]);
    exportCSV(headers, rows, "relatorio-motoboys.csv");
  }

  function exportProdutos() {
    if (!produtosData) return;
    const headers = ["Produto", "Vendido", "Receita"];
    const rows = (produtosData as Record<string, unknown>[]).map((p) => [
      p.nome as string,
      String(p.total_vendido),
      Number(p.receita).toFixed(2).replace(".", ","),
    ]);
    exportCSV(headers, rows, "relatorio-produtos.csv");
  }

  function handleUnlockAnalytics(e: React.FormEvent) {
    e.preventDefault();
    if (!senhaAnalytics.trim()) {
      toast.error("Informe a senha do admin");
      return;
    }
    setSenhaConfirmada(senhaAnalytics.trim());
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const an: Record<string, any> = analytics ?? {};

  return (
    <AdminLayout>
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Relatórios</h2>

        <Tabs defaultValue="vendas">
          <TabsList>
            <TabsTrigger value="vendas">Vendas</TabsTrigger>
            <TabsTrigger value="motoboys">Motoboys</TabsTrigger>
            <TabsTrigger value="produtos">Produtos</TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-1">
              <Eye className="h-3.5 w-3.5" /> Analytics
            </TabsTrigger>
          </TabsList>

          {/* Vendas */}
          <TabsContent value="vendas">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Relatório de Vendas</CardTitle>
                  <div className="flex items-center gap-2">
                    <Input type="date" value={vendasInicio} onChange={(e) => setVendasInicio(e.target.value)} className="dark-input w-40" />
                    <span className="text-[var(--text-muted)]">até</span>
                    <Input type="date" value={vendasFim} onChange={(e) => setVendasFim(e.target.value)} className="dark-input w-40" />
                    <Button size="sm" className="bg-[var(--cor-primaria)]" onClick={() => fetchVendas()} disabled={loadingVendas}>
                      <Search className="mr-1 h-4 w-4" /> Buscar
                    </Button>
                    {vendas && (
                      <Button variant="outline" size="sm" onClick={exportVendas}>
                        <Download className="mr-1 h-4 w-4" /> CSV
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {!vendas ? (
                  <div className="flex flex-col items-center gap-2 py-12">
                    <BarChart3 className="h-10 w-10 text-[var(--text-muted)]" />
                    <p className="text-[var(--text-muted)]">Selecione o período e clique em Buscar</p>
                  </div>
                ) : (
                  <>
                    <div className="mb-4 grid gap-4 sm:grid-cols-2">
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                        <CardContent className="p-4">
                          <p className="text-sm text-[var(--text-muted)]">Total de Pedidos</p>
                          <p className="text-2xl font-bold text-[var(--text-primary)]">{vendas.total_pedidos}</p>
                        </CardContent>
                      </Card>
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                        <CardContent className="p-4">
                          <p className="text-sm text-[var(--text-muted)]">Faturamento Total</p>
                          <p className="text-2xl font-bold text-[var(--cor-primaria)]">R$ {Number(vendas.faturamento_total).toFixed(2)}</p>
                        </CardContent>
                      </Card>
                    </div>
                    {/* Resumo por plataforma */}
                    {vendas.resumo_por_plataforma && (vendas.resumo_por_plataforma as Record<string, unknown>[]).length > 1 && (
                      <div className="mb-4 grid gap-2 sm:grid-cols-3 lg:grid-cols-4">
                        {(vendas.resumo_por_plataforma as { label: string; pedidos: number; faturamento: number; percentual: number }[]).map((item) => (
                          <Card key={item.label} className="border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                            <CardContent className="p-3">
                              <p className="text-xs text-[var(--text-muted)]">{item.label}</p>
                              <p className="text-lg font-bold text-[var(--text-primary)]">{item.pedidos} <span className="text-xs font-normal text-[var(--text-muted)]">({item.percentual}%)</span></p>
                              <p className="text-xs text-[var(--cor-primaria)]">{fmt(item.faturamento)}</p>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    )}
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="border-[var(--border-subtle)]">
                            <TableHead className="text-[var(--text-muted)]">#</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Cliente</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Plataforma</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Valor</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Pagamento</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Data</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(vendas.pedidos as Record<string, unknown>[]).map((p) => (
                            <TableRow key={p.id as number} className="border-[var(--border-subtle)]">
                              <TableCell className="font-mono text-[var(--text-primary)]">#{String(p.comanda || p.id)}</TableCell>
                              <TableCell className="text-[var(--text-secondary)]">{(p.cliente_nome as string) || "—"}</TableCell>
                              <TableCell className="text-xs text-[var(--text-secondary)]">{(p.plataforma_label as string) || "—"}</TableCell>
                              <TableCell className="font-medium text-[var(--text-primary)]">R$ {Number(p.valor_total).toFixed(2)}</TableCell>
                              <TableCell className="text-[var(--text-secondary)]">{(p.forma_pagamento as string) || "—"}</TableCell>
                              <TableCell className="text-sm text-[var(--text-muted)]">
                                {p.data_criacao ? new Date(p.data_criacao as string).toLocaleDateString("pt-BR") : "—"}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Motoboys */}
          <TabsContent value="motoboys">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Relatório de Motoboys</CardTitle>
                  <div className="flex items-center gap-2">
                    <Input type="date" value={motoboyInicio} onChange={(e) => setMotoboyInicio(e.target.value)} className="dark-input w-40" />
                    <span className="text-[var(--text-muted)]">até</span>
                    <Input type="date" value={motoboyFim} onChange={(e) => setMotoboyFim(e.target.value)} className="dark-input w-40" />
                    <Button size="sm" className="bg-[var(--cor-primaria)]" onClick={() => fetchMotoboys()} disabled={loadingMotoboys}>
                      <Search className="mr-1 h-4 w-4" /> Buscar
                    </Button>
                    {motoboysData && (
                      <Button variant="outline" size="sm" onClick={exportMotoboys}>
                        <Download className="mr-1 h-4 w-4" /> CSV
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {!motoboysData ? (
                  <div className="flex flex-col items-center gap-2 py-12">
                    <BarChart3 className="h-10 w-10 text-[var(--text-muted)]" />
                    <p className="text-[var(--text-muted)]">Selecione o período e clique em Buscar</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[var(--border-subtle)]">
                          <TableHead className="text-[var(--text-muted)]">Motoboy</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Entregas</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Ganhos</TableHead>
                          <TableHead className="text-[var(--text-muted)]">KM</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(motoboysData as Record<string, unknown>[]).map((m) => (
                          <TableRow key={m.motoboy_id as number} className="border-[var(--border-subtle)]">
                            <TableCell className="font-medium text-[var(--text-primary)]">{m.nome as string}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">{m.total_entregas as number}</TableCell>
                            <TableCell className="font-medium text-[var(--text-primary)]">R$ {Number(m.total_ganhos).toFixed(2)}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">{Number(m.total_km).toFixed(1)} km</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Produtos */}
          <TabsContent value="produtos">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Produtos Mais Vendidos</CardTitle>
                  <div className="flex gap-2">
                    <Button size="sm" className="bg-[var(--cor-primaria)]" onClick={() => fetchProdutos()} disabled={loadingProdutos}>
                      <Search className="mr-1 h-4 w-4" /> Carregar
                    </Button>
                    {produtosData && (
                      <Button variant="outline" size="sm" onClick={exportProdutos}>
                        <Download className="mr-1 h-4 w-4" /> CSV
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {!produtosData ? (
                  <div className="flex flex-col items-center gap-2 py-12">
                    <BarChart3 className="h-10 w-10 text-[var(--text-muted)]" />
                    <p className="text-[var(--text-muted)]">Clique em Carregar para ver o ranking</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[var(--border-subtle)]">
                          <TableHead className="text-[var(--text-muted)]">#</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Produto</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Qtd Vendida</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Receita</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {(produtosData as Record<string, unknown>[]).map((p, idx) => (
                          <TableRow key={p.produto_id as number} className="border-[var(--border-subtle)]">
                            <TableCell className="text-[var(--text-muted)]">{idx + 1}</TableCell>
                            <TableCell className="font-medium text-[var(--text-primary)]">{p.nome as string}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">{p.total_vendido as number}</TableCell>
                            <TableCell className="font-medium text-[var(--cor-primaria)]">R$ {Number(p.receita).toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Analytics */}
          <TabsContent value="analytics">
            {!senhaConfirmada ? (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="py-16">
                  <form onSubmit={handleUnlockAnalytics} className="mx-auto max-w-sm space-y-4 text-center">
                    <Lock className="mx-auto h-12 w-12 text-[var(--text-muted)]" />
                    <h3 className="text-lg font-semibold text-[var(--text-primary)]">Relatórios Avançados</h3>
                    <p className="text-sm text-[var(--text-muted)]">Insira a senha do admin para acessar analytics detalhados com projeções e análises.</p>
                    <Input
                      type="password"
                      placeholder="Senha do admin"
                      value={senhaAnalytics}
                      onChange={(e) => setSenhaAnalytics(e.target.value)}
                      className="dark-input"
                    />
                    <Button type="submit" className="w-full bg-[var(--cor-primaria)]">
                      <Lock className="mr-2 h-4 w-4" /> Acessar Relatórios
                    </Button>
                  </form>
                </CardContent>
              </Card>
            ) : errorAnalytics ? (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="py-16 text-center">
                  <Lock className="mx-auto h-12 w-12 text-red-400" />
                  <h3 className="mt-3 text-lg font-semibold text-red-400">Senha incorreta</h3>
                  <p className="text-sm text-[var(--text-muted)]">Verifique a senha e tente novamente.</p>
                  <Button variant="outline" className="mt-4" onClick={() => { setSenhaConfirmada(""); setSenhaAnalytics(""); }}>
                    Tentar novamente
                  </Button>
                </CardContent>
              </Card>
            ) : loadingAnalytics ? (
              <div className="flex h-64 items-center justify-center">
                <BarChart3 className="h-8 w-8 text-[var(--cor-primaria)] animate-pulse" />
              </div>
            ) : (
              <div className="space-y-6">
                {/* Seletor período */}
                <div className="flex gap-2">
                  {["30d", "90d", "12m", "anual"].map((p) => (
                    <Button
                      key={p}
                      size="sm"
                      variant={periodoAnalytics === p ? "default" : "outline"}
                      className={periodoAnalytics === p ? "bg-[var(--cor-primaria)]" : ""}
                      onClick={() => setPeriodoAnalytics(p)}
                    >
                      {p === "30d" ? "30 dias" : p === "90d" ? "90 dias" : p === "12m" ? "12 meses" : "Anual"}
                    </Button>
                  ))}
                </div>

                {/* Faturamento */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                    <TrendingUp className="h-4 w-4" /> Faturamento
                  </h3>
                  <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Mês Atual</p>
                        <p className="text-xl font-bold text-[var(--cor-primaria)]">{fmt(an.faturamento_mes)}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Projeção Anual</p>
                        <p className="text-xl font-bold text-[var(--text-primary)]">{fmt(an.projecao_anual)}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">vs Mês Anterior</p>
                        <p className={cn("text-xl font-bold", (an.comparacao_mes_anterior ?? 0) >= 0 ? "text-green-400" : "text-red-400")}>
                          {(an.comparacao_mes_anterior ?? 0) >= 0 ? <TrendingUp className="inline h-4 w-4 mr-1" /> : <TrendingDown className="inline h-4 w-4 mr-1" />}
                          {(an.comparacao_mes_anterior ?? 0).toFixed(1)}%
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Ticket Médio</p>
                        <p className="text-xl font-bold text-[var(--text-primary)]">{fmt(an.ticket_medio)}</p>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {/* Tendência */}
                {(an.tendencia?.length ?? 0) > 0 && (
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardHeader><CardTitle className="text-[var(--text-primary)] text-base">Tendência de Faturamento</CardTitle></CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={an.tendencia}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                          <XAxis dataKey="data" stroke="var(--text-muted)" fontSize={11} tickFormatter={(v: string) => v.slice(5)} />
                          <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(v: number) => `R$${v}`} />
                          <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                          <Line type="monotone" dataKey="faturamento" stroke="var(--cor-primaria)" strokeWidth={2} dot={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                )}

                {/* Quando mais vende */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                    <Clock className="h-4 w-4" /> Quando Mais Vende
                  </h3>
                  <div className="grid grid-cols-2 gap-3 mb-4">
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Melhor Dia</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          {an.melhor_dia_semana?.dia || "—"}
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">
                          {an.melhor_dia_semana?.total_pedidos ?? 0} pedidos — {fmt(an.melhor_dia_semana?.faturamento)}
                        </p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Horário Pico</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          {an.horario_pico?.hora ?? "--"}h
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">{an.horario_pico?.total_pedidos ?? 0} pedidos</p>
                      </CardContent>
                    </Card>
                  </div>
                  <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                    {/* Distribuição por dia */}
                    {(an.distribuicao_dia_semana?.length ?? 0) > 0 && (
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardHeader><CardTitle className="text-sm text-[var(--text-primary)] flex items-center gap-1.5"><CalendarDays className="h-4 w-4" /> Por Dia da Semana</CardTitle></CardHeader>
                        <CardContent>
                          <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={an.distribuicao_dia_semana}>
                              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                              <XAxis dataKey="nome" stroke="var(--text-muted)" fontSize={10} tickFormatter={(v: string) => v.slice(0, 3)} />
                              <YAxis stroke="var(--text-muted)" fontSize={10} />
                              <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                              <Bar dataKey="pedidos" fill="var(--cor-primaria)" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    )}
                    {/* Distribuição por hora */}
                    {(an.distribuicao_hora?.length ?? 0) > 0 && (
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardHeader><CardTitle className="text-sm text-[var(--text-primary)] flex items-center gap-1.5"><Clock className="h-4 w-4" /> Por Hora do Dia</CardTitle></CardHeader>
                        <CardContent>
                          <ResponsiveContainer width="100%" height={200}>
                            <BarChart data={an.distribuicao_hora}>
                              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                              <XAxis dataKey="hora" stroke="var(--text-muted)" fontSize={10} tickFormatter={(v: number) => `${v}h`} />
                              <YAxis stroke="var(--text-muted)" fontSize={10} />
                              <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                              <Bar dataKey="pedidos" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>

                {/* O que mais vende */}
                {(an.produtos_mais_vendidos?.length ?? 0) > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <ShoppingBag className="h-4 w-4" /> O Que Mais Vende
                    </h3>
                    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardHeader><CardTitle className="text-sm text-[var(--text-primary)]">Top 20 Produtos</CardTitle></CardHeader>
                        <CardContent>
                          <div className="overflow-x-auto max-h-80 overflow-y-auto">
                            <Table>
                              <TableHeader>
                                <TableRow className="border-[var(--border-subtle)]">
                                  <TableHead className="text-[var(--text-muted)]">#</TableHead>
                                  <TableHead className="text-[var(--text-muted)]">Produto</TableHead>
                                  <TableHead className="text-[var(--text-muted)] text-right">Qtd</TableHead>
                                  <TableHead className="text-[var(--text-muted)] text-right">Receita</TableHead>
                                  <TableHead className="text-[var(--text-muted)] text-right">%</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                                {an.produtos_mais_vendidos.map((p: any, idx: number) => (
                                  <TableRow key={idx} className="border-[var(--border-subtle)]">
                                    <TableCell className="text-[var(--text-muted)]">{idx + 1}</TableCell>
                                    <TableCell className="text-[var(--text-primary)] text-sm">{p.nome}</TableCell>
                                    <TableCell className="text-right text-[var(--text-secondary)]">{p.quantidade}</TableCell>
                                    <TableCell className="text-right font-medium text-[var(--cor-primaria)]">{fmt(p.receita)}</TableCell>
                                    <TableCell className="text-right text-[var(--text-muted)]">{(p.percentual_vendas ?? 0).toFixed(1)}%</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </div>
                        </CardContent>
                      </Card>
                      {/* Categorias PieChart */}
                      {(an.categorias_mais_vendidas?.length ?? 0) > 0 && (
                        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                          <CardHeader><CardTitle className="text-sm text-[var(--text-primary)]">Categorias</CardTitle></CardHeader>
                          <CardContent>
                            <ResponsiveContainer width="100%" height={220}>
                              <PieChart>
                                <Pie data={an.categorias_mais_vendidas} cx="50%" cy="50%" outerRadius={80} dataKey="quantidade" nameKey="nome" label={(entry: { nome: string; percentual: number }) => `${entry.nome}: ${entry.percentual?.toFixed(0)}%`}>
                                  {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                                  {(an.categorias_mais_vendidas as any[]).map((_: unknown, idx: number) => (
                                    <Cell key={idx} fill={CORES[idx % CORES.length]} />
                                  ))}
                                </Pie>
                                <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                              </PieChart>
                            </ResponsiveContainer>
                          </CardContent>
                        </Card>
                      )}
                    </div>
                  </div>
                )}

                {/* Como pagam */}
                {(an.formas_pagamento?.length ?? 0) > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <CreditCard className="h-4 w-4" /> Como Pagam
                    </h3>
                    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                      {(an.formas_pagamento as any[]).map((f: any, idx: number) => (
                        <Card key={f.forma} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                          <CardContent className="p-4">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="h-3 w-3 rounded-full" style={{ backgroundColor: CORES[idx % CORES.length] }} />
                              <p className="text-xs text-[var(--text-muted)] capitalize">{f.forma}</p>
                            </div>
                            <p className="text-lg font-bold text-[var(--text-primary)]">{f.total}</p>
                            <p className="text-xs text-[var(--text-muted)]">{fmt(f.valor)} ({(f.percentual ?? 0).toFixed(0)}%)</p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {/* Clientes */}
                <div>
                  <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                    <Users className="h-4 w-4" /> Clientes
                  </h3>
                  <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Únicos no Mês</p>
                        <p className="text-xl font-bold text-[var(--text-primary)]">{an.clientes_unicos_mes ?? 0}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Novos</p>
                        <p className="text-xl font-bold text-green-400">{an.clientes_novos_mes ?? 0}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Recorrentes</p>
                        <p className="text-xl font-bold text-[var(--text-primary)]">{an.clientes_recorrentes ?? 0}</p>
                      </CardContent>
                    </Card>
                    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                      <CardContent className="p-4">
                        <p className="text-xs text-[var(--text-muted)]">Taxa Recorrência</p>
                        <p className="text-xl font-bold text-[var(--cor-primaria)]">{(an.taxa_recorrencia ?? 0).toFixed(1)}%</p>
                        <p className="text-[10px] text-[var(--text-muted)]">dos clientes voltam a pedir</p>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                {/* Cancelamentos */}
                <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <p className="text-xs text-[var(--text-muted)]">Cancelamentos no Mês</p>
                      <p className="text-xl font-bold text-red-400">{an.cancelamentos_mes ?? 0}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <p className="text-xs text-[var(--text-muted)]">Taxa Cancelamento</p>
                      <p className="text-xl font-bold text-red-400">{(an.taxa_cancelamento ?? 0).toFixed(1)}%</p>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <p className="text-xs text-[var(--text-muted)]">Entregas</p>
                      <p className="text-xl font-bold text-[var(--text-primary)]">{an.entregas_vs_retiradas?.entregas ?? 0}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="p-4">
                      <p className="text-xs text-[var(--text-muted)]">Retiradas</p>
                      <p className="text-xl font-bold text-[var(--text-primary)]">{an.entregas_vs_retiradas?.retiradas ?? 0}</p>
                    </CardContent>
                  </Card>
                </div>

                {/* De Onde Vem os Pedidos */}
                {(an.distribuicao_plataforma?.length ?? 0) > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <ShoppingBag className="h-4 w-4" /> De Onde Vem os Pedidos
                    </h3>
                    <div className="grid gap-4 lg:grid-cols-2">
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardContent className="p-4">
                          <ResponsiveContainer width="100%" height={220}>
                            <PieChart>
                              <Pie
                                data={an.distribuicao_plataforma}
                                dataKey="pedidos"
                                nameKey="label"
                                cx="50%"
                                cy="50%"
                                outerRadius={80}
                                label={({ label, percentual }: { label: string; percentual: number }) => `${label} ${percentual}%`}
                              >
                                {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                                {(an.distribuicao_plataforma as any[]).map((_: unknown, i: number) => (
                                  <Cell key={i} fill={CORES[i % CORES.length]} />
                                ))}
                              </Pie>
                              <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                            </PieChart>
                          </ResponsiveContainer>
                        </CardContent>
                      </Card>
                      <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardContent className="p-4">
                          <Table>
                            <TableHeader>
                              <TableRow className="border-[var(--border-subtle)]">
                                <TableHead className="text-[var(--text-muted)]">Plataforma</TableHead>
                                <TableHead className="text-[var(--text-muted)] text-right">Pedidos</TableHead>
                                <TableHead className="text-[var(--text-muted)] text-right">Faturamento</TableHead>
                                <TableHead className="text-[var(--text-muted)] text-right">%</TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                              {(an.distribuicao_plataforma as any[]).map((item: any, i: number) => (
                                <TableRow key={item.plataforma} className="border-[var(--border-subtle)]">
                                  <TableCell className="text-[var(--text-primary)]">
                                    <div className="flex items-center gap-2">
                                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: CORES[i % CORES.length] }} />
                                      {item.label}
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-right text-[var(--text-primary)]">{item.pedidos}</TableCell>
                                  <TableCell className="text-right text-[var(--cor-primaria)]">{fmt(item.faturamento)}</TableCell>
                                  <TableCell className="text-right text-[var(--text-muted)]">{item.percentual}%</TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </CardContent>
                      </Card>
                    </div>
                  </div>
                )}

                {/* Previsão */}
                {(an.previsao_proximos_3_meses?.length ?? 0) > 0 && (
                  <div>
                    <h3 className="mb-3 text-sm font-semibold text-[var(--text-muted)] uppercase tracking-wider flex items-center gap-1.5">
                      <TrendingUp className="h-4 w-4" /> Previsão
                    </h3>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                      {(an.previsao_proximos_3_meses as any[]).map((p: any) => (
                        <Card key={p.mes} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                          <CardContent className="p-4">
                            <p className="text-xs text-[var(--text-muted)]">{p.mes}</p>
                            <p className="text-lg font-bold text-[var(--cor-primaria)]">{fmt(p.faturamento_estimado)}</p>
                            <p className="text-xs text-[var(--text-muted)]">~{p.pedidos_estimados} pedidos</p>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {/* Comparação anual */}
                {an.comparacao_anual && (
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardHeader><CardTitle className="text-base text-[var(--text-primary)]">Comparação Ano Atual vs Anterior</CardTitle></CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={an.comparacao_anual}>
                          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                          <XAxis dataKey="mes" stroke="var(--text-muted)" fontSize={11} />
                          <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={(v: number) => `R$${v}`} />
                          <Tooltip contentStyle={{ backgroundColor: "var(--bg-card)", border: "1px solid var(--border-subtle)", borderRadius: "8px" }} />
                          <Bar dataKey="faturamento_atual" fill="var(--cor-primaria)" radius={[4, 4, 0, 0]} name="Atual" />
                          <Bar dataKey="faturamento_anterior" fill="#6b7280" radius={[4, 4, 0, 0]} name="Anterior" />
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}
