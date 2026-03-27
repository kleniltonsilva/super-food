import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ADMIN_QUERY_KEYS } from "@/admin/hooks/useAdminQueries";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useMotoboys,
  useCriarMotoboy,
  useAtualizarMotoboy,
  useDeletarMotoboy,
  useSolicitacoesMotoboys,
  useResponderSolicitacao,
  useRankingMotoboys,
  useRelatorioMotoboys,
  useConfig,
  useAtualizarConfig,
} from "@/admin/hooks/useAdminQueries";
import { getRelatorioMotoboys, atualizarHierarquia } from "@/admin/lib/adminApiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Pencil, Trash2, Check, X, Trophy, Key, Download, Loader2, AlertTriangle, ShieldCheck, Search, ArrowUp, ArrowDown, GripVertical, Info, Save } from "lucide-react";
import { toast } from "sonner";
import { validarCPF, formatarCPF, limparCPF } from "@/utils/cpf";
import InfoTooltip from "@/components/InfoTooltip";

interface MotoboyForm {
  nome: string;
  usuario: string;
  telefone: string;
  senha: string;
  capacidade_entregas: string;
  cpf: string;
}

const emptyForm: MotoboyForm = { nome: "", usuario: "", telefone: "", senha: "", capacidade_entregas: "5", cpf: "" };

export default function Motoboys() {
  const { data: motoboys, isLoading } = useMotoboys();
  const { data: solicitacoes } = useSolicitacoesMotoboys();
  const { data: ranking } = useRankingMotoboys();
  const { data: config } = useConfig();
  const atualizarConfig = useAtualizarConfig();
  const criarMotoboy = useCriarMotoboy();
  const atualizarMotoboy = useAtualizarMotoboy();
  const deletarMotoboy = useDeletarMotoboy();
  const responderSolic = useResponderSolicitacao();

  const qc = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<MotoboyForm>(emptyForm);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // Ranking state
  const [rankDataInicio, setRankDataInicio] = useState("");
  const [rankDataFim, setRankDataFim] = useState("");
  const [rankDados, setRankDados] = useState<Record<string, unknown>[] | null>(null);
  const [rankLoading, setRankLoading] = useState(false);

  // Hierarquia state
  const [hierarquiaSaving, setHierarquiaSaving] = useState<number | null>(null);

  // Pagamentos state
  const [pagDataInicio, setPagDataInicio] = useState("");
  const [pagDataFim, setPagDataFim] = useState("");
  const [pagDados, setPagDados] = useState<Record<string, unknown>[] | null>(null);
  const [pagLoading, setPagLoading] = useState(false);

  // Config pagamento motoboy
  const [configPag, setConfigPag] = useState<Record<string, unknown>>({});
  useEffect(() => {
    if (config) setConfigPag({
      valor_base_motoboy: config.valor_base_motoboy,
      valor_km_extra_motoboy: config.valor_km_extra_motoboy,
      taxa_diaria: config.taxa_diaria,
      valor_lanche: config.valor_lanche,
      permitir_ver_saldo_motoboy: config.permitir_ver_saldo_motoboy,
      permitir_finalizar_fora_raio: config.permitir_finalizar_fora_raio,
    });
  }, [config]);

  function handleSaveConfigPag() {
    atualizarConfig.mutate(configPag, {
      onSuccess: () => toast.success("Configurações de pagamento salvas!"),
      onError: () => toast.error("Erro ao salvar configurações"),
    });
  }

  async function moverHierarquia(motoboyId: number, direcao: "subir" | "descer") {
    const ativos = motoboyList
      .filter((m) => m.status === "ativo")
      .sort((a, b) => Number(a.ordem_hierarquia || 0) - Number(b.ordem_hierarquia || 0));
    const idx = ativos.findIndex((m) => (m.id as number) === motoboyId);
    if (idx < 0) return;
    const outroIdx = direcao === "subir" ? idx - 1 : idx + 1;
    if (outroIdx < 0 || outroIdx >= ativos.length) return;

    const meuMotoboy = ativos[idx];
    const outroMotoboy = ativos[outroIdx];
    const minhaOrdem = Number(meuMotoboy.ordem_hierarquia || 0);
    const outraOrdem = Number(outroMotoboy.ordem_hierarquia || 0);

    setHierarquiaSaving(motoboyId);
    try {
      await atualizarHierarquia(motoboyId, outraOrdem);
      await atualizarHierarquia(outroMotoboy.id as number, minhaOrdem);
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
      toast.success(`${meuMotoboy.nome} movido para posição ${outraOrdem + 1}`);
    } catch {
      toast.error("Erro ao reordenar");
    } finally {
      setHierarquiaSaving(null);
    }
  }

  function openNew() {
    setEditId(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(m: Record<string, unknown>) {
    setEditId(m.id as number);
    setForm({
      nome: m.nome as string,
      usuario: m.usuario as string,
      telefone: (m.telefone as string) || "",
      senha: "",
      capacidade_entregas: String(m.capacidade_entregas ?? 5),
      cpf: m.cpf ? formatarCPF(m.cpf as string) : "",
    });
    setShowForm(true);
  }

  function handleSave() {
    if (!form.nome.trim() || !form.usuario.trim()) { toast.error("Nome e usuário obrigatórios"); return; }

    const cpfLimpo = limparCPF(form.cpf);
    if (cpfLimpo && !validarCPF(cpfLimpo)) { toast.error("CPF inválido"); return; }

    const payload: Record<string, unknown> = {
      nome: form.nome.trim(),
      usuario: form.usuario.trim(),
      telefone: form.telefone.trim(),
      capacidade_entregas: Number(form.capacidade_entregas),
      cpf: cpfLimpo || null,
    };
    if (form.senha.trim()) payload.senha = form.senha.trim();

    if (editId) {
      atualizarMotoboy.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Motoboy atualizado"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      if (!form.senha.trim()) { toast.error("Informe a senha"); return; }
      criarMotoboy.mutate(payload, {
        onSuccess: () => { toast.success("Motoboy cadastrado"); setShowForm(false); },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao cadastrar";
          toast.error(msg);
        },
      });
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarMotoboy.mutate(deleteId, {
      onSuccess: () => { toast.success("Motoboy desativado"); setDeleteId(null); },
      onError: () => toast.error("Erro ao desativar"),
    });
  }

  function handleSolicitacao(id: number, aprovado: boolean) {
    responderSolic.mutate(
      { id, aprovado },
      {
        onSuccess: () => toast.success(aprovado ? "Solicitação aprovada" : "Solicitação rejeitada"),
        onError: () => toast.error("Erro ao processar"),
      }
    );
  }

  function handleToggleOnline(m: Record<string, unknown>) {
    atualizarMotoboy.mutate(
      { id: m.id as number, disponivel: !m.disponivel },
      {
        onSuccess: () => toast.success(`${m.nome} agora está ${m.disponivel ? "offline" : "online"}`),
        onError: () => toast.error("Erro ao alterar status"),
      }
    );
  }

  function handleDesativar(m: Record<string, unknown>) {
    atualizarMotoboy.mutate(
      { id: m.id as number, status: "inativo" },
      {
        onSuccess: () => toast.success(`${m.nome} desativado`),
        onError: () => toast.error("Erro ao desativar"),
      }
    );
  }

  function handleResetSenha(m: Record<string, unknown>) {
    atualizarMotoboy.mutate(
      { id: m.id as number, senha: "123456" },
      {
        onSuccess: () => toast.success(`Senha de ${m.nome} resetada para 123456`),
        onError: () => toast.error("Erro ao resetar senha"),
      }
    );
  }

  async function buscarRanking() {
    if (!rankDataInicio || !rankDataFim) { toast.error("Selecione o período"); return; }
    setRankLoading(true);
    try {
      const data = await getRelatorioMotoboys({ data_inicio: rankDataInicio, data_fim: rankDataFim });
      const arr = Array.isArray(data) ? data : data?.motoboys || [];
      arr.sort((a: Record<string, unknown>, b: Record<string, unknown>) =>
        Number(b.total_entregas || 0) - Number(a.total_entregas || 0)
      );
      setRankDados(arr);
    } catch {
      toast.error("Erro ao buscar ranking");
    } finally {
      setRankLoading(false);
    }
  }

  function limparFiltroRanking() {
    setRankDataInicio("");
    setRankDataFim("");
    setRankDados(null);
  }

  async function buscarPagamentos() {
    if (!pagDataInicio || !pagDataFim) { toast.error("Selecione o período"); return; }
    setPagLoading(true);
    try {
      const data = await getRelatorioMotoboys({ data_inicio: pagDataInicio, data_fim: pagDataFim });
      setPagDados(Array.isArray(data) ? data : data?.motoboys || []);
    } catch {
      toast.error("Erro ao buscar pagamentos");
    } finally {
      setPagLoading(false);
    }
  }

  function exportarCSV() {
    if (!pagDados || pagDados.length === 0) return;
    const headers = ["Motoboy", "Entregas", "Taxa Base (R$)", "Extra KM (R$)", "Alimentação (R$)", "Diárias (R$)", "Total (R$)"];
    const rows = pagDados.map((m) => [
      m.nome,
      m.total_entregas || 0,
      Number(m.valor_base || 0).toFixed(2).replace(".", ","),
      Number(m.valor_km_extra || 0).toFixed(2).replace(".", ","),
      Number(m.valor_alimentacao || 0).toFixed(2).replace(".", ","),
      Number(m.valor_diarias || 0).toFixed(2).replace(".", ","),
      Number(m.total_ganhos || 0).toFixed(2).replace(".", ","),
    ]);
    const csv = [headers.join(";"), ...rows.map((r) => r.join(";"))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `pagamentos_motoboys_${pagDataInicio}_${pagDataFim}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const motoboyList: Record<string, unknown>[] = motoboys || [];
  const solicList: Record<string, unknown>[] = solicitacoes || [];
  const rankList: Record<string, unknown>[] = ranking || [];

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Motoboys</h2>
          <Button
            size="sm"
            className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
            onClick={openNew}
          >
            <Plus className="mr-1 h-4 w-4" /> Novo Motoboy
          </Button>
        </div>

        <Tabs defaultValue="lista">
          <TabsList>
            <TabsTrigger value="lista">
              Lista ({motoboyList.length})
            </TabsTrigger>
            <TabsTrigger value="solicitacoes">
              Solicitações ({solicList.length})
            </TabsTrigger>
            <TabsTrigger value="ranking">
              Ranking
            </TabsTrigger>
            <TabsTrigger value="pagamentos">
              Pagamentos
            </TabsTrigger>
            <TabsTrigger value="hierarquia">
              Hierarquia
            </TabsTrigger>
          </TabsList>

          {/* Lista */}
          <TabsContent value="lista">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-[var(--border-subtle)]">
                      <TableHead className="text-[var(--text-muted)]">Nome</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Telefone</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Online</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Status</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Cap.</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Entregas</TableHead>
                      <TableHead className="text-[var(--text-muted)]">Ganhos</TableHead>
                      <TableHead className="text-[var(--text-muted)] text-right">Ações</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {isLoading ? (
                      Array.from({ length: 3 }).map((_, i) => (
                        <TableRow key={i} className="border-[var(--border-subtle)]">
                          {Array.from({ length: 8 }).map((_, j) => (
                            <TableCell key={j}><Skeleton className="h-5 w-20" /></TableCell>
                          ))}
                        </TableRow>
                      ))
                    ) : motoboyList.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={8} className="py-12 text-center text-[var(--text-muted)]">
                          Nenhum motoboy cadastrado
                        </TableCell>
                      </TableRow>
                    ) : (
                      motoboyList.map((m) => (
                        <TableRow key={m.id as number} className="border-[var(--border-subtle)]">
                          <TableCell>
                            <div>
                              <p className="font-medium text-[var(--text-primary)]">{m.nome as string}</p>
                              <p className="text-xs text-[var(--text-muted)]">@{m.usuario as string}</p>
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-secondary)]">
                            {(m.telefone as string) || "—"}
                          </TableCell>
                          <TableCell>
                            <Switch
                              checked={!!m.disponivel}
                              onCheckedChange={() => handleToggleOnline(m)}
                              disabled={atualizarMotoboy.isPending}
                            />
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center gap-1">
                              {m.disponivel ? (
                                <Badge className="bg-green-500/20 text-green-400 border border-green-500/30 text-xs">
                                  Online
                                </Badge>
                              ) : (
                                <Badge className="bg-gray-500/20 text-gray-400 border border-gray-500/30 text-xs">
                                  Offline
                                </Badge>
                              )}
                              {m.em_rota ? (
                                <Badge className="bg-purple-500/20 text-purple-400 border border-purple-500/30 text-xs">
                                  Em rota
                                </Badge>
                              ) : null}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-primary)]">
                            {(m.capacidade_entregas as number) ?? 5}
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-primary)]">
                            {(m.total_entregas as number) || 0}
                          </TableCell>
                          <TableCell className="text-sm text-[var(--text-primary)]">
                            R$ {Number(m.total_ganhos || 0).toFixed(2)}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-1">
                              <Button variant="ghost" size="icon-sm" onClick={() => openEdit(m)} title="Editar">
                                <Pencil className="h-4 w-4" />
                              </Button>
                              <Button variant="ghost" size="icon-sm" onClick={() => handleResetSenha(m)} title="Reset Senha (123456)">
                                <Key className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-red-400"
                                onClick={() => setDeleteId(m.id as number)}
                                title="Desativar"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>
            </Card>
          </TabsContent>

          {/* Solicitações */}
          <TabsContent value="solicitacoes">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardContent className="p-4">
                {solicList.length === 0 ? (
                  <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                    Nenhuma solicitação pendente
                  </p>
                ) : (
                  <div className="space-y-3">
                    {solicList.map((s) => (
                      <div
                        key={s.id as number}
                        className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-3"
                      >
                        <div>
                          <p className="font-medium text-[var(--text-primary)]">{s.nome as string}</p>
                          <p className="text-xs text-[var(--text-muted)]">
                            @{s.usuario as string} | {s.telefone as string}
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700"
                            onClick={() => handleSolicitacao(s.id as number, true)}
                            disabled={responderSolic.isPending}
                          >
                            <Check className="mr-1 h-4 w-4" /> Aprovar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-500/30 text-red-400"
                            onClick={() => handleSolicitacao(s.id as number, false)}
                            disabled={responderSolic.isPending}
                          >
                            <X className="mr-1 h-4 w-4" /> Rejeitar
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Ranking */}
          <TabsContent value="ranking">
            <div className="space-y-3">
              {/* Aviso antifraude */}
              {config?.permitir_finalizar_fora_raio ? (
                <div className="flex items-center gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-yellow-400" />
                  <p className="text-sm text-yellow-400">Ranking sem validação antifraude — motoboys podem finalizar fora do raio</p>
                </div>
              ) : (
                <div className="flex items-center gap-2 rounded-md border border-green-500/30 bg-green-500/10 px-3 py-2">
                  <ShieldCheck className="h-4 w-4 shrink-0 text-green-400" />
                  <p className="text-sm text-green-400">Ranking com validação antifraude ativa</p>
                </div>
              )}

              {/* Filtro de data */}
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="flex flex-col gap-3 p-3 sm:flex-row sm:items-end">
                  <div className="space-y-1">
                    <label className="text-xs text-[var(--text-muted)]">De</label>
                    <Input type="date" value={rankDataInicio} onChange={(e) => setRankDataInicio(e.target.value)} className="dark-input h-9 w-36" />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs text-[var(--text-muted)]">Até</label>
                    <Input type="date" value={rankDataFim} onChange={(e) => setRankDataFim(e.target.value)} className="dark-input h-9 w-36" />
                  </div>
                  <Button size="sm" onClick={buscarRanking} disabled={rankLoading}>
                    {rankLoading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Search className="mr-1 h-4 w-4" />}
                    Buscar
                  </Button>
                  {rankDados && (
                    <Button size="sm" variant="ghost" onClick={limparFiltroRanking}>
                      Limpar filtro
                    </Button>
                  )}
                </CardContent>
              </Card>

              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow className="border-[var(--border-subtle)]">
                        <TableHead className="text-[var(--text-muted)]">#</TableHead>
                        <TableHead className="text-[var(--text-muted)]">Motoboy</TableHead>
                        <TableHead className="text-[var(--text-muted)]">Entregas</TableHead>
                        <TableHead className="text-[var(--text-muted)]">Ganhos</TableHead>
                        <TableHead className="text-[var(--text-muted)]">KM</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(rankDados || rankList).length === 0 ? (
                        <TableRow>
                          <TableCell colSpan={5} className="py-8 text-center text-[var(--text-muted)]">
                            Sem dados {rankDados ? "para o período" : ""}
                          </TableCell>
                        </TableRow>
                      ) : (
                        (rankDados || rankList).map((r, idx) => (
                          <TableRow key={(r.id ?? r.motoboy_id) as number} className="border-[var(--border-subtle)]">
                            <TableCell>
                              {idx < 3 ? (
                                <Trophy className={`h-5 w-5 ${idx === 0 ? "text-yellow-400" : idx === 1 ? "text-gray-400" : "text-amber-700"}`} />
                              ) : (
                                <span className="text-[var(--text-muted)]">{idx + 1}</span>
                              )}
                            </TableCell>
                            <TableCell className="font-medium text-[var(--text-primary)]">
                              {r.nome as string}
                            </TableCell>
                            <TableCell className="text-[var(--text-secondary)]">
                              {(r.total_entregas as number) || 0}
                            </TableCell>
                            <TableCell className="text-[var(--text-secondary)]">
                              R$ {Number(r.total_ganhos || 0).toFixed(2)}
                            </TableCell>
                            <TableCell className="text-[var(--text-secondary)]">
                              {Number(r.total_km || 0).toFixed(1)} km
                            </TableCell>
                          </TableRow>
                        ))
                      )}
                    </TableBody>
                  </Table>
                </div>
              </Card>
            </div>
          </TabsContent>

          {/* Pagamentos */}
          <TabsContent value="pagamentos">
            {/* Config Pagamento Motoboy */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] mb-4">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)] text-base">Configuração de Pagamento</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                      Valor Base (R$)
                      <InfoTooltip text="Valor pago ao motoboy por entrega, independente da distância percorrida." />
                    </label>
                    <Input type="number" step="0.01" value={(configPag.valor_base_motoboy as number) || ""} onChange={(e) => setConfigPag({ ...configPag, valor_base_motoboy: Number(e.target.value) })} className="dark-input" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                      KM Extra (R$)
                      <InfoTooltip text="Adicional pago ao motoboy por cada km além da distância base. Somado ao valor base." />
                    </label>
                    <Input type="number" step="0.01" value={(configPag.valor_km_extra_motoboy as number) || ""} onChange={(e) => setConfigPag({ ...configPag, valor_km_extra_motoboy: Number(e.target.value) })} className="dark-input" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                      Taxa Diária (R$)
                      <InfoTooltip text="Valor fixo pago ao motoboy por dia trabalhado. 0 = não pagar taxa diária." />
                    </label>
                    <Input type="number" step="0.01" value={(configPag.taxa_diaria as number) || ""} onChange={(e) => setConfigPag({ ...configPag, taxa_diaria: Number(e.target.value) })} className="dark-input" />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                      Valor Lanche (R$)
                      <InfoTooltip text="Auxílio alimentação diário pago ao motoboy. 0 = não aplicar." />
                    </label>
                    <Input type="number" step="0.01" value={(configPag.valor_lanche as number) || ""} onChange={(e) => setConfigPag({ ...configPag, valor_lanche: Number(e.target.value) })} className="dark-input" />
                  </div>
                </div>

                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-6">
                  <div className="flex items-center justify-between gap-2 sm:justify-start">
                    <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                      Ver Saldo
                      <InfoTooltip text="Quando ativado, o motoboy pode ver seus ganhos acumulados no app." />
                    </label>
                    <Switch checked={!!configPag.permitir_ver_saldo_motoboy} onCheckedChange={(v) => setConfigPag({ ...configPag, permitir_ver_saldo_motoboy: v })} />
                  </div>
                  <div className="flex items-center justify-between gap-2 sm:justify-start">
                    <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                      Finalizar Fora do Raio
                      <InfoTooltip text="Antifraude GPS. Quando desativado, motoboy só finaliza a menos de 50m do destino." />
                    </label>
                    <Switch checked={!!configPag.permitir_finalizar_fora_raio} onCheckedChange={(v) => setConfigPag({ ...configPag, permitir_finalizar_fora_raio: v })} />
                  </div>
                </div>

                {!!configPag.permitir_finalizar_fora_raio && (
                  <div className="flex items-center gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-3 py-2">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-yellow-400" />
                    <p className="text-xs text-yellow-400">
                      Motoboys poderão finalizar entregas fora do raio de entrega.
                    </p>
                  </div>
                )}

                <Button
                  size="sm"
                  className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                  onClick={handleSaveConfigPag}
                  disabled={atualizarConfig.isPending}
                >
                  <Save className="mr-1 h-4 w-4" /> Salvar Configurações
                </Button>
              </CardContent>
            </Card>

            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Pagamentos Motoboys</CardTitle>
                  <div className="flex items-end gap-2">
                    <div className="space-y-1">
                      <label className="text-xs text-[var(--text-muted)]">De</label>
                      <Input type="date" value={pagDataInicio} onChange={(e) => setPagDataInicio(e.target.value)} className="dark-input h-9 w-36" />
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-[var(--text-muted)]">Até</label>
                      <Input type="date" value={pagDataFim} onChange={(e) => setPagDataFim(e.target.value)} className="dark-input h-9 w-36" />
                    </div>
                    <Button size="sm" onClick={buscarPagamentos} disabled={pagLoading}>
                      {pagLoading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : null}
                      Buscar
                    </Button>
                    {pagDados && pagDados.length > 0 && (
                      <Button size="sm" variant="outline" onClick={exportarCSV}>
                        <Download className="mr-1 h-4 w-4" /> CSV
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {pagDados === null ? (
                  <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                    Selecione o período e clique em "Buscar"
                  </p>
                ) : pagDados.length === 0 ? (
                  <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                    Nenhum dado encontrado para o período
                  </p>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-[var(--border-subtle)]">
                          <TableHead className="text-[var(--text-muted)]">Motoboy</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Entregas</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Taxa Base</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Extra KM</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Alimentação</TableHead>
                          <TableHead className="text-[var(--text-muted)]">Diárias</TableHead>
                          <TableHead className="text-[var(--text-muted)] font-bold">Total</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {pagDados.map((m) => (
                          <TableRow key={m.id as number} className="border-[var(--border-subtle)]">
                            <TableCell className="font-medium text-[var(--text-primary)]">{m.nome as string}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">{(m.total_entregas as number) || 0}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">R$ {Number(m.valor_base || 0).toFixed(2)}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">R$ {Number(m.valor_km_extra || 0).toFixed(2)}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">R$ {Number(m.valor_alimentacao || 0).toFixed(2)}</TableCell>
                            <TableCell className="text-[var(--text-secondary)]">R$ {Number(m.valor_diarias || 0).toFixed(2)}</TableCell>
                            <TableCell className="font-bold text-[var(--text-primary)]">R$ {Number(m.total_ganhos || 0).toFixed(2)}</TableCell>
                          </TableRow>
                        ))}
                        <TableRow className="border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                          <TableCell className="font-bold text-[var(--text-primary)]">TOTAL GERAL</TableCell>
                          <TableCell className="font-bold text-[var(--text-primary)]">{pagDados.reduce((a, m) => a + Number(m.total_entregas || 0), 0)}</TableCell>
                          <TableCell className="font-bold text-[var(--text-primary)]">R$ {pagDados.reduce((a, m) => a + Number(m.valor_base || 0), 0).toFixed(2)}</TableCell>
                          <TableCell className="font-bold text-[var(--text-primary)]">R$ {pagDados.reduce((a, m) => a + Number(m.valor_km_extra || 0), 0).toFixed(2)}</TableCell>
                          <TableCell className="font-bold text-[var(--text-primary)]">R$ {pagDados.reduce((a, m) => a + Number(m.valor_alimentacao || 0), 0).toFixed(2)}</TableCell>
                          <TableCell className="font-bold text-[var(--text-primary)]">R$ {pagDados.reduce((a, m) => a + Number(m.valor_diarias || 0), 0).toFixed(2)}</TableCell>
                          <TableCell className="font-bold text-[var(--cor-primaria)]">R$ {pagDados.reduce((a, m) => a + Number(m.total_ganhos || 0), 0).toFixed(2)}</TableCell>
                        </TableRow>
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
          {/* Hierarquia */}
          <TabsContent value="hierarquia">
            <div className="space-y-3">
              {/* Explicação */}
              <div className="flex items-start gap-3 rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
                <Info className="mt-0.5 h-5 w-5 shrink-0 text-blue-400" />
                <div className="space-y-1.5">
                  <p className="text-sm font-medium text-blue-300">Como funciona a hierarquia?</p>
                  <p className="text-sm text-blue-300/80">
                    Quando o sistema precisa escolher um motoboy automaticamente, ele prioriza quem fez
                    <strong> menos entregas no dia</strong> (distribuição justa). Se dois ou mais motoboys
                    empatarem em número de entregas, a <strong>hierarquia abaixo</strong> define quem será
                    escolhido primeiro.
                  </p>
                  <p className="text-sm text-blue-300/80">
                    O motoboy na <strong>posição 1</strong> tem preferência sobre o da posição 2 no desempate.
                    Use as setas para ajustar a ordem conforme sua preferência.
                  </p>
                </div>
              </div>

              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] text-base">Ordem de Preferência</CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {(() => {
                    const ativos = motoboyList
                      .filter((m) => m.status === "ativo")
                      .sort((a, b) => Number(a.ordem_hierarquia || 0) - Number(b.ordem_hierarquia || 0));
                    if (ativos.length === 0) {
                      return (
                        <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                          Nenhum motoboy ativo para ordenar
                        </p>
                      );
                    }
                    return ativos.map((m, idx) => (
                      <div
                        key={m.id as number}
                        className="flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4 py-3 transition-colors hover:bg-[var(--bg-card-hover)]"
                      >
                        <GripVertical className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
                        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--cor-primaria)]/20 text-sm font-bold text-[var(--cor-primaria)]">
                          {idx + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-[var(--text-primary)] truncate">{m.nome as string}</p>
                          <p className="text-xs text-[var(--text-muted)]">
                            {m.disponivel ? "Online" : "Offline"}
                            {m.em_rota ? " · Em rota" : ""}
                            {" · "}{(m.total_entregas as number) || 0} entregas total
                          </p>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            disabled={idx === 0 || hierarquiaSaving !== null}
                            onClick={() => moverHierarquia(m.id as number, "subir")}
                            className="h-8 w-8"
                          >
                            {hierarquiaSaving === (m.id as number) ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <ArrowUp className="h-4 w-4" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            disabled={idx === ativos.length - 1 || hierarquiaSaving !== null}
                            onClick={() => moverHierarquia(m.id as number, "descer")}
                            className="h-8 w-8"
                          >
                            {hierarquiaSaving === (m.id as number) ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <ArrowDown className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    ));
                  })()}
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* Form Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Motoboy" : "Novo Motoboy"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Nome *</label>
                <Input
                  value={form.nome}
                  onChange={(e) => setForm({ ...form, nome: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Usuário *</label>
                <Input
                  value={form.usuario}
                  onChange={(e) => setForm({ ...form, usuario: e.target.value })}
                  className="dark-input"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Telefone</label>
                <Input
                  value={form.telefone}
                  onChange={(e) => setForm({ ...form, telefone: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">CPF</label>
                <Input
                  value={form.cpf}
                  onChange={(e) => setForm({ ...form, cpf: formatarCPF(e.target.value) })}
                  className="dark-input"
                  placeholder="000.000.000-00"
                  maxLength={14}
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">
                  Senha {editId ? "(deixe vazio para manter)" : "*"}
                </label>
                <Input
                  type="password"
                  value={form.senha}
                  onChange={(e) => setForm({ ...form, senha: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Capacidade</label>
                <Input
                  type="number"
                  min="1"
                  value={form.capacidade_entregas}
                  onChange={(e) => setForm({ ...form, capacidade_entregas: e.target.value })}
                  className="dark-input"
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleSave}
              disabled={criarMotoboy.isPending || atualizarMotoboy.isPending}
            >
              {editId ? "Salvar" : "Cadastrar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desativar Motoboy</AlertDialogTitle>
            <AlertDialogDescription>
              O motoboy será desativado e não receberá mais entregas.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Desativar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
