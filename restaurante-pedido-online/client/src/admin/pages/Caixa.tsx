import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useCaixaAtual,
  useAbrirCaixa,
  useRegistrarMovimentacao,
  useFecharCaixa,
  useHistoricoCaixa,
  useOperadoresCaixa,
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
  User,
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

const CRIAR_NOVO_VALUE = "__criar_novo__";

export default function Caixa() {
  const { data: caixa, isLoading } = useCaixaAtual();
  const { data: historico } = useHistoricoCaixa();
  const { data: operadores } = useOperadoresCaixa();
  const abrirCaixa = useAbrirCaixa();
  const registrarMov = useRegistrarMovimentacao();
  const fecharCaixa = useFecharCaixa();

  // Abrir caixa
  const [showAbrir, setShowAbrir] = useState(false);
  const [valorAbertura, setValorAbertura] = useState("");
  const [abrirOperador, setAbrirOperador] = useState("Gerente");
  const [abrirSenha, setAbrirSenha] = useState("");
  const [abrirNovoNome, setAbrirNovoNome] = useState("");
  const [abrirNovoSenha, setAbrirNovoSenha] = useState("");

  // Movimentação
  const [showMov, setShowMov] = useState(false);
  const [movTipo, setMovTipo] = useState("entrada");
  const [movValor, setMovValor] = useState("");
  const [movDesc, setMovDesc] = useState("");

  // Fechar caixa
  const [showFechar, setShowFechar] = useState(false);
  const [contadoDinheiro, setContadoDinheiro] = useState("");
  const [contadoCartao, setContadoCartao] = useState("");
  const [contadoPix, setContadoPix] = useState("");
  const [fecharOperador, setFecharOperador] = useState("Gerente");
  const [fecharSenha, setFecharSenha] = useState("");

  const caixaAberto = caixa && caixa.id;
  const isCriarNovo = abrirOperador === CRIAR_NOVO_VALUE;

  const operadoresLista = (operadores as Array<{ id: number; nome: string }>) || [];

  function resetAbrirDialog() {
    setValorAbertura("");
    setAbrirOperador("Gerente");
    setAbrirSenha("");
    setAbrirNovoNome("");
    setAbrirNovoSenha("");
  }

  function resetFecharDialog() {
    setContadoDinheiro("");
    setContadoCartao("");
    setContadoPix("");
    setFecharOperador("Gerente");
    setFecharSenha("");
  }

  function handleAbrir() {
    if (isCriarNovo) {
      const nome = abrirNovoNome.trim();
      if (!nome) { toast.error("Informe o nome do operador"); return; }
      if (nome.toLowerCase() === "gerente") { toast.error("'Gerente' é um nome reservado"); return; }
      if (abrirNovoSenha.trim().length < 4) { toast.error("Senha deve ter no mínimo 4 caracteres"); return; }
      abrirCaixa.mutate(
        { valor_abertura: Number(valorAbertura) || 0, operador_nome: nome, senha: abrirNovoSenha, criar_operador: true },
        {
          onSuccess: () => { toast.success("Caixa aberto!"); resetAbrirDialog(); setShowAbrir(false); },
          onError: (err: unknown) => toast.error(extractErrorMessage(err)),
        }
      );
    } else {
      if (!abrirSenha.trim()) { toast.error("Informe a senha"); return; }
      abrirCaixa.mutate(
        { valor_abertura: Number(valorAbertura) || 0, operador_nome: abrirOperador, senha: abrirSenha },
        {
          onSuccess: () => { toast.success("Caixa aberto!"); resetAbrirDialog(); setShowAbrir(false); },
          onError: (err: unknown) => toast.error(extractErrorMessage(err)),
        }
      );
    }
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
    fecharCaixa.mutate(
      { valor_contado: totalContado, operador_nome: fecharOperador, senha: fecharSenha },
      {
        onSuccess: (data) => {
          toast.success(`Caixa fechado. Diferença: R$ ${data.diferenca?.toFixed(2)}`);
          setShowFechar(false);
          resetFecharDialog();
        },
        onError: (err: unknown) => toast.error(extractErrorMessage(err)),
      }
    );
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
                {/* Info operador */}
                <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
                  <User className="h-4 w-4" />
                  <span>Aberto por: <strong className="text-[var(--text-primary)]">{caixa.operador_abertura}</strong></span>
                </div>

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
                      <TableHead className="text-[var(--text-muted)]">Operador</TableHead>
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
                        <TableCell colSpan={10} className="py-8 text-center text-[var(--text-muted)]">
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
                          <TableCell className="text-sm text-[var(--text-primary)]">
                            <div className="flex flex-col">
                              <span>{(h.operador_abertura as string) || "—"}</span>
                              {(h.operador_fechamento as string) && (h.operador_fechamento as string) !== (h.operador_abertura as string) && (
                                <span className="text-xs text-[var(--text-muted)]">Fechou: {h.operador_fechamento as string}</span>
                              )}
                            </div>
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
      <Dialog open={showAbrir} onOpenChange={(open) => { setShowAbrir(open); if (!open) resetAbrirDialog(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Abrir Caixa</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Operador */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Operador</label>
              <Select value={abrirOperador} onValueChange={(v) => { setAbrirOperador(v); setAbrirSenha(""); }}>
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Gerente">Gerente</SelectItem>
                  {operadoresLista.map((op) => (
                    <SelectItem key={op.id} value={op.nome}>{op.nome}</SelectItem>
                  ))}
                  <SelectItem value={CRIAR_NOVO_VALUE}>
                    <span className="flex items-center gap-1.5">
                      <Plus className="h-3.5 w-3.5" /> Criar novo operador
                    </span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Se criar novo operador */}
            {isCriarNovo ? (
              <>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Nome do operador</label>
                  <Input
                    value={abrirNovoNome}
                    onChange={(e) => setAbrirNovoNome(e.target.value)}
                    className="dark-input"
                    placeholder="Ex: Maria"
                    autoFocus
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Senha do operador</label>
                  <Input
                    type="password"
                    value={abrirNovoSenha}
                    onChange={(e) => setAbrirNovoSenha(e.target.value)}
                    className="dark-input"
                    placeholder="Mínimo 4 caracteres"
                  />
                </div>
              </>
            ) : (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Senha</label>
                <Input
                  type="password"
                  value={abrirSenha}
                  onChange={(e) => setAbrirSenha(e.target.value)}
                  className="dark-input"
                  placeholder={abrirOperador === "Gerente" ? "Senha do restaurante" : "Senha do operador"}
                  autoFocus
                />
              </div>
            )}

            {/* Valor abertura */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Troco / Fundo de Caixa (R$)</label>
              <Input
                type="number"
                step="0.01"
                value={valorAbertura}
                onChange={(e) => setValorAbertura(e.target.value)}
                className="dark-input"
                placeholder="0.00"
              />
              <p className="text-xs text-[var(--text-muted)]">Quanto de dinheiro tem no caixa para troco?</p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowAbrir(false); resetAbrirDialog(); }}>Cancelar</Button>
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
      <Dialog open={showFechar} onOpenChange={(open) => { setShowFechar(open); if (!open) resetFecharDialog(); }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Fechar Caixa</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {/* Operador + Senha */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Operador</label>
              <Select value={fecharOperador} onValueChange={(v) => { setFecharOperador(v); setFecharSenha(""); }}>
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Gerente">Gerente</SelectItem>
                  {operadoresLista.map((op) => (
                    <SelectItem key={op.id} value={op.nome}>{op.nome}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Senha</label>
              <Input
                type="password"
                value={fecharSenha}
                onChange={(e) => setFecharSenha(e.target.value)}
                className="dark-input"
                placeholder={fecharOperador === "Gerente" ? "Senha do restaurante" : "Senha do operador"}
              />
            </div>

            {/* Valor esperado */}
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
            <Button variant="outline" onClick={() => { setShowFechar(false); resetFecharDialog(); }}>Cancelar</Button>
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
