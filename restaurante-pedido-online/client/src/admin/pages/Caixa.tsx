import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useCaixaAtual,
  useAbrirCaixa,
  useRegistrarMovimentacao,
  useFecharCaixa,
  useHistoricoCaixa,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
  DollarSign,
  ArrowUpCircle,
  ArrowDownCircle,
  Lock,
  Unlock,
  Plus,
  Banknote,
  CreditCard,
  Smartphone,
  Ticket,
} from "lucide-react";
import { toast } from "sonner";

function extractErrorMessage(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (!detail) return "Erro desconhecido";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((e: { msg?: string }) => e.msg || String(e)).join(", ");
  return String(detail);
}

const PAGAMENTO_LABELS: Record<string, { label: string; icon: React.ReactNode; color: string }> = {
  dinheiro: { label: "Dinheiro", icon: <Banknote className="h-5 w-5 text-green-400" />, color: "bg-green-500/10" },
  cartao: { label: "Cartão", icon: <CreditCard className="h-5 w-5 text-blue-400" />, color: "bg-blue-500/10" },
  pix: { label: "Pix", icon: <Smartphone className="h-5 w-5 text-purple-400" />, color: "bg-purple-500/10" },
  vale: { label: "Vale", icon: <Ticket className="h-5 w-5 text-orange-400" />, color: "bg-orange-500/10" },
};

export default function Caixa() {
  const { data: caixa, isLoading } = useCaixaAtual();
  const { data: historico } = useHistoricoCaixa();
  const abrirCaixa = useAbrirCaixa();
  const registrarMov = useRegistrarMovimentacao();
  const fecharCaixa = useFecharCaixa();

  const [showAbrir, setShowAbrir] = useState(false);
  const [valorAbertura, setValorAbertura] = useState("");
  const [showMov, setShowMov] = useState(false);
  const [movTipo, setMovTipo] = useState("entrada");
  const [movValor, setMovValor] = useState("");
  const [movDesc, setMovDesc] = useState("");
  const [showFechar, setShowFechar] = useState(false);
  const [contadoDinheiro, setContadoDinheiro] = useState("");
  const [contadoCartao, setContadoCartao] = useState("");
  const [contadoPix, setContadoPix] = useState("");

  const caixaAberto = caixa && caixa.id;

  function handleAbrir() {
    abrirCaixa.mutate(Number(valorAbertura) || 0, {
      onSuccess: () => { toast.success("Caixa aberto!"); setValorAbertura(""); setShowAbrir(false); },
      onError: (err: unknown) => toast.error(extractErrorMessage(err)),
    });
  }

  function handleMov() {
    if (!movValor || Number(movValor) <= 0) { toast.error("Informe o valor"); return; }
    registrarMov.mutate(
      { tipo: movTipo, valor: Number(movValor), descricao: movDesc.trim() || undefined },
      {
        onSuccess: () => {
          toast.success("Movimentação registrada");
          setShowMov(false);
          setMovValor("");
          setMovDesc("");
        },
        onError: (err: unknown) => toast.error(extractErrorMessage(err)),
      }
    );
  }

  const totalContado = (Number(contadoDinheiro) || 0) + (Number(contadoCartao) || 0) + (Number(contadoPix) || 0);

  function handleFechar() {
    if (totalContado <= 0) { toast.error("Informe os valores contados"); return; }
    fecharCaixa.mutate(totalContado, {
      onSuccess: (data) => {
        toast.success(`Caixa fechado. Diferença: R$ ${data.diferenca?.toFixed(2)}`);
        setShowFechar(false);
        setContadoDinheiro("");
        setContadoCartao("");
        setContadoPix("");
      },
      onError: (err: unknown) => toast.error(extractErrorMessage(err)),
    });
  }

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("pt-BR");
  }

  const valorEsperado = caixa
    ? (Number(caixa.valor_abertura || 0) + Number(caixa.total_vendas || 0) - Number(caixa.valor_retiradas || 0))
    : 0;

  return (
    <AdminLayout>
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Caixa</h2>

        <Tabs defaultValue="atual">
          <TabsList>
            <TabsTrigger value="atual">Caixa Atual</TabsTrigger>
            <TabsTrigger value="historico">Histórico</TabsTrigger>
          </TabsList>

          <TabsContent value="atual">
            {isLoading ? (
              <Skeleton className="h-64 w-full" />
            ) : !caixaAberto ? (
              /* Caixa fechado */
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="flex flex-col items-center gap-4 py-12">
                  <Lock className="h-12 w-12 text-[var(--text-muted)]" />
                  <p className="text-lg font-medium text-[var(--text-primary)]">Caixa Fechado</p>
                  <Button
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => setShowAbrir(true)}
                  >
                    <Unlock className="mr-2 h-4 w-4" /> Abrir Caixa
                  </Button>
                </CardContent>
              </Card>
            ) : (
              /* Caixa aberto */
              <div className="space-y-4">
                {/* Métricas principais */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="flex items-center gap-3 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                        <DollarSign className="h-5 w-5 text-blue-400" />
                      </div>
                      <div>
                        <p className="text-xs text-[var(--text-muted)]">Abertura</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          R$ {Number(caixa.valor_abertura || 0).toFixed(2)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="flex items-center gap-3 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                        <ArrowUpCircle className="h-5 w-5 text-green-400" />
                      </div>
                      <div>
                        <p className="text-xs text-[var(--text-muted)]">Vendas</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          R$ {Number(caixa.total_vendas || 0).toFixed(2)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="flex items-center gap-3 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                        <ArrowDownCircle className="h-5 w-5 text-red-400" />
                      </div>
                      <div>
                        <p className="text-xs text-[var(--text-muted)]">Retiradas</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          R$ {Number(caixa.valor_retiradas || 0).toFixed(2)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                    <CardContent className="flex items-center gap-3 p-4">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--cor-primaria)]/10">
                        <DollarSign className="h-5 w-5 text-[var(--cor-primaria)]" />
                      </div>
                      <div>
                        <p className="text-xs text-[var(--text-muted)]">Saldo Esperado</p>
                        <p className="text-lg font-bold text-[var(--text-primary)]">
                          R$ {valorEsperado.toFixed(2)}
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Breakdown por forma de pagamento */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  {(["dinheiro", "cartao", "pix", "vale"] as const).map((key) => {
                    const info = PAGAMENTO_LABELS[key];
                    const valor = Number(caixa[`total_${key}`] || 0);
                    return (
                      <Card key={key} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                        <CardContent className="flex items-center gap-3 p-4">
                          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${info.color}`}>
                            {info.icon}
                          </div>
                          <div>
                            <p className="text-xs text-[var(--text-muted)]">{info.label}</p>
                            <p className="text-lg font-bold text-[var(--text-primary)]">
                              R$ {valor.toFixed(2)}
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    );
                  })}
                </div>

                {/* Ações */}
                <div className="flex gap-2">
                  <Button
                    className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                    onClick={() => setShowMov(true)}
                  >
                    <Plus className="mr-1 h-4 w-4" /> Nova Movimentação
                  </Button>
                  <Button
                    variant="outline"
                    className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                    onClick={() => setShowFechar(true)}
                  >
                    <Lock className="mr-1 h-4 w-4" /> Fechar Caixa
                  </Button>
                </div>

                {/* Movimentações */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Movimentações</CardTitle>
                  </CardHeader>
                  <CardContent>
                    {(caixa.movimentacoes || []).length === 0 ? (
                      <p className="py-4 text-center text-sm text-[var(--text-muted)]">
                        Nenhuma movimentação registrada
                      </p>
                    ) : (
                      <div className="space-y-2">
                        {(caixa.movimentacoes as Record<string, unknown>[]).map((m) => (
                          <div
                            key={m.id as number}
                            className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-3"
                          >
                            <div className="flex items-center gap-3">
                              {(m.tipo === "entrada" || m.tipo === "venda") ? (
                                <ArrowUpCircle className="h-5 w-5 text-green-400" />
                              ) : (
                                <ArrowDownCircle className="h-5 w-5 text-red-400" />
                              )}
                              <div>
                                <div className="flex items-center gap-2">
                                  <p className="text-sm font-medium text-[var(--text-primary)]">
                                    {(m.descricao as string) || (m.tipo as string)}
                                  </p>
                                  {(m.forma_pagamento as string) && (
                                    <Badge variant="outline" className="text-xs capitalize border-[var(--border-subtle)]">
                                      {PAGAMENTO_LABELS[m.forma_pagamento as string]?.label || (m.forma_pagamento as string)}
                                    </Badge>
                                  )}
                                  {m.tipo === "venda" && (
                                    <Badge className="bg-green-500/20 text-green-400 border border-green-500/30 text-xs">
                                      Auto
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-xs text-[var(--text-muted)]">
                                  {formatDate(m.data_hora as string)}
                                </p>
                              </div>
                            </div>
                            <p className={`font-medium ${(m.tipo === "entrada" || m.tipo === "venda") ? "text-green-400" : "text-red-400"}`}>
                              {(m.tipo === "entrada" || m.tipo === "venda") ? "+" : "-"} R$ {Number(m.valor).toFixed(2)}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </TabsContent>

          {/* Histórico */}
          <TabsContent value="historico">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[var(--border-subtle)]">
                      <TableHead className="text-[var(--text-muted)]">Abertura</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Fechamento</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Vendas</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Dinheiro</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Cartão</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Pix</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Vale</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Contado</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Diferença</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(historico || []).length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="py-8 text-center text-[var(--text-muted)]">
                          Sem histórico
                        </TableCell>
                      </TableRow>
                    ) : (
                      (historico as Record<string, unknown>[]).map((h) => (
                        <TableRow key={h.id as number} className="border-[var(--border-subtle)]">
                          <TableCell className="text-sm text-[var(--text-secondary)]">
                            {formatDate(h.data_abertura as string)}
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-secondary)]">
                            {formatDate(h.data_fechamento as string)}
                          </TableCell>
                          <TableCell className="text-sm font-medium text-[var(--text-primary)]">
                            R$ {Number(h.total_vendas || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-sm text-green-400">
                            R$ {Number(h.total_dinheiro || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-sm text-blue-400">
                            R$ {Number(h.total_cartao || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-sm text-purple-400">
                            R$ {Number(h.total_pix || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-sm text-orange-400">
                            R$ {Number(h.total_vale || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-primary)]">
                            R$ {Number(h.valor_contado || 0).toFixed(2)}
                          </TableCell>
                          <TableCell>
                            <Badge className={Number(h.diferenca || 0) >= 0
                              ? "bg-green-500/20 text-green-400 border border-green-500/30"
                              : "bg-red-500/20 text-red-400 border border-red-500/30"
                            }>
                              R$ {Number(h.diferenca || 0).toFixed(2)}
                            </Badge>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Dialog movimentação */}
      <Dialog open={showMov} onOpenChange={setShowMov}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nova Movimentação</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Tipo</label>
              <Select value={movTipo} onValueChange={setMovTipo}>
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="entrada">Entrada</SelectItem>
                  <SelectItem value="saida">Saída</SelectItem>
                  <SelectItem value="retirada">Retirada</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Valor</label>
              <Input
                type="number"
                step="0.01"
                value={movValor}
                onChange={(e) => setMovValor(e.target.value)}
                className="dark-input"
                placeholder="0.00"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Descrição</label>
              <Input
                value={movDesc}
                onChange={(e) => setMovDesc(e.target.value)}
                className="dark-input"
                placeholder="Descrição da movimentação"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowMov(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleMov}
              disabled={registrarMov.isPending}
            >
              Registrar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog abrir caixa */}
      <Dialog open={showAbrir} onOpenChange={setShowAbrir}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Abrir Caixa</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Troco / Fundo de Caixa (R$)</label>
              <Input
                type="number"
                step="0.01"
                value={valorAbertura}
                onChange={(e) => setValorAbertura(e.target.value)}
                className="dark-input"
                placeholder="0.00"
                autoFocus
              />
              <p className="text-xs text-[var(--text-muted)]">Quanto de dinheiro tem no caixa para troco?</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAbrir(false)}>Cancelar</Button>
            <Button
              className="bg-green-600 hover:bg-green-700"
              onClick={handleAbrir}
              disabled={abrirCaixa.isPending}
            >
              <Unlock className="mr-1 h-4 w-4" /> Abrir Caixa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog fechar caixa */}
      <Dialog open={showFechar} onOpenChange={setShowFechar}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Fechar Caixa</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
              <p className="text-sm text-[var(--text-muted)]">Valor esperado pelo sistema</p>
              <p className="text-xl font-bold text-[var(--text-primary)]">R$ {valorEsperado.toFixed(2)}</p>
              <div className="mt-2 flex gap-4 text-xs text-[var(--text-muted)]">
                <span>Dinheiro: <strong className="text-green-400">R$ {Number(caixa?.total_dinheiro || 0).toFixed(2)}</strong></span>
                <span>Cartão: <strong className="text-blue-400">R$ {Number(caixa?.total_cartao || 0).toFixed(2)}</strong></span>
                <span>Pix: <strong className="text-purple-400">R$ {Number(caixa?.total_pix || 0).toFixed(2)}</strong></span>
              </div>
            </div>

            <p className="text-sm font-medium text-[var(--text-secondary)]">Quanto foi recebido hoje?</p>

            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-500/10">
                  <Banknote className="h-5 w-5 text-green-400" />
                </div>
                <div className="flex-1">
                  <label className="text-xs font-medium text-green-400">Dinheiro</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={contadoDinheiro}
                    onChange={(e) => setContadoDinheiro(e.target.value)}
                    className="dark-input mt-0.5"
                    placeholder="0.00"
                    autoFocus
                  />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10">
                  <CreditCard className="h-5 w-5 text-blue-400" />
                </div>
                <div className="flex-1">
                  <label className="text-xs font-medium text-blue-400">Cartão</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={contadoCartao}
                    onChange={(e) => setContadoCartao(e.target.value)}
                    className="dark-input mt-0.5"
                    placeholder="0.00"
                  />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/10">
                  <Smartphone className="h-5 w-5 text-purple-400" />
                </div>
                <div className="flex-1">
                  <label className="text-xs font-medium text-purple-400">Pix</label>
                  <Input
                    type="number"
                    step="0.01"
                    value={contadoPix}
                    onChange={(e) => setContadoPix(e.target.value)}
                    className="dark-input mt-0.5"
                    placeholder="0.00"
                  />
                </div>
              </div>
            </div>

            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3 flex justify-between items-center">
              <span className="text-sm font-medium text-[var(--text-secondary)]">Total Contado</span>
              <span className={`text-lg font-bold ${Math.abs(totalContado - valorEsperado) > 0.01 ? "text-amber-400" : "text-green-400"}`}>
                R$ {totalContado.toFixed(2)}
              </span>
            </div>

            {totalContado > 0 && Math.abs(totalContado - valorEsperado) > 0.01 && (
              <p className={`text-sm font-medium ${totalContado > valorEsperado ? "text-green-400" : "text-red-400"}`}>
                Diferença: R$ {(totalContado - valorEsperado).toFixed(2)}
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFechar(false)}>Cancelar</Button>
            <Button
              className="bg-red-600 hover:bg-red-700"
              onClick={handleFechar}
              disabled={fecharCaixa.isPending}
            >
              <Lock className="mr-1 h-4 w-4" /> Fechar Caixa
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
