import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useRelatorioVendas,
  useRelatorioMotoboys,
  useRelatorioProdutos,
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
import { BarChart3, Download, Search } from "lucide-react";

export default function Relatorios() {
  const [vendasInicio, setVendasInicio] = useState("");
  const [vendasFim, setVendasFim] = useState("");
  const [motoboyInicio, setMotoboyInicio] = useState("");
  const [motoboyFim, setMotoboyFim] = useState("");

  const vendasParams: Record<string, unknown> = {};
  if (vendasInicio) vendasParams.data_inicio = vendasInicio;
  if (vendasFim) vendasParams.data_fim = vendasFim;

  const motoboyParams: Record<string, unknown> = {};
  if (motoboyInicio) motoboyParams.data_inicio = motoboyInicio;
  if (motoboyFim) motoboyParams.data_fim = motoboyFim;

  const { data: vendas, refetch: fetchVendas, isFetching: loadingVendas } = useRelatorioVendas(vendasParams);
  const { data: motoboysData, refetch: fetchMotoboys, isFetching: loadingMotoboys } = useRelatorioMotoboys(motoboyParams);
  const { data: produtosData, refetch: fetchProdutos, isFetching: loadingProdutos } = useRelatorioProdutos();

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
    const headers = ["#", "Cliente", "Valor", "Pagamento", "Status", "Data"];
    const rows = vendas.pedidos.map((p: Record<string, unknown>) => [
      String(p.comanda || p.id),
      (p.cliente_nome as string) || "",
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

  return (
    <AdminLayout>
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Relatórios</h2>

        <Tabs defaultValue="vendas">
          <TabsList>
            <TabsTrigger value="vendas">Vendas</TabsTrigger>
            <TabsTrigger value="motoboys">Motoboys</TabsTrigger>
            <TabsTrigger value="produtos">Produtos</TabsTrigger>
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
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="border-[var(--border-subtle)]">
                            <TableHead className="text-[var(--text-muted)]">#</TableHead>
                            <TableHead className="text-[var(--text-muted)]">Cliente</TableHead>
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
        </Tabs>
      </div>
    </AdminLayout>
  );
}
