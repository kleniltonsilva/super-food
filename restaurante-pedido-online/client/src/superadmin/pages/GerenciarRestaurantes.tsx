import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useRestaurantes,
  useAtualizarStatusRestaurante,
  useAtualizarRestaurante,
  useDominiosRestaurante,
  useCriarDominio,
  useVerificarDominioDNS,
  useDeletarDominio,
} from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import {
  Search,
  Store,
  Play,
  Pause,
  XCircle,
  RefreshCw,
  Edit,
  Loader2,
  Globe,
  Trash2,
  CheckCircle2,
  Clock,
  Shield,
  Plus,
} from "lucide-react";
import { useLocation } from "wouter";
import { cn } from "@/lib/utils";

interface Restaurante {
  id: number;
  nome_fantasia: string;
  email: string;
  telefone: string;
  plano: string;
  valor_plano: number;
  status: string | null;
  ativo: boolean;
  codigo_acesso: string;
  criado_em: string | null;
  data_vencimento: string | null;
  total_pedidos: number;
  total_motoboys: number;
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("pt-BR");
}

function diasRestantes(dataVenc: string | null) {
  if (!dataVenc) return null;
  const diff = Math.ceil((new Date(dataVenc).getTime() - Date.now()) / 86400000);
  return diff;
}

function statusBadge(status: string | null) {
  const s = status || "ativo";
  const map: Record<string, { color: string; label: string }> = {
    ativo: { color: "bg-green-500/20 text-green-400", label: "Ativo" },
    suspenso: { color: "bg-yellow-500/20 text-yellow-400", label: "Suspenso" },
    cancelado: { color: "bg-red-500/20 text-red-400", label: "Cancelado" },
  };
  const info = map[s] || map.ativo;
  return (
    <span className={cn("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", info.color)}>
      {info.label}
    </span>
  );
}

export default function GerenciarRestaurantes() {
  const [busca, setBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState<string>("todos");
  const [filtroPlano, setFiltroPlano] = useState<string>("todos");
  const [editModal, setEditModal] = useState<Restaurante | null>(null);
  const [editForm, setEditForm] = useState<Record<string, string>>({});
  const [dominioModal, setDominioModal] = useState<Restaurante | null>(null);
  const [novoDominio, setNovoDominio] = useState("");
  const [, navigate] = useLocation();

  const params: Record<string, string> = {};
  if (filtroStatus !== "todos") params.status = filtroStatus;
  if (filtroPlano !== "todos") params.plano = filtroPlano;
  if (busca.trim()) params.busca = busca.trim();

  const { data: restaurantes, isLoading } = useRestaurantes(
    Object.keys(params).length > 0 ? params : undefined
  );
  const atualizarStatus = useAtualizarStatusRestaurante();
  const atualizarRest = useAtualizarRestaurante();
  const { data: dominios, isLoading: dominiosLoading } = useDominiosRestaurante(dominioModal?.id ?? null);
  const criarDom = useCriarDominio();
  const verificarDNS = useVerificarDominioDNS();
  const deletarDom = useDeletarDominio();

  function handleStatusChange(id: number, novoStatus: string) {
    atualizarStatus.mutate(
      { id, status: novoStatus },
      {
        onSuccess: (data) => {
          toast.success(data.mensagem || `Status atualizado para '${novoStatus}'`);
        },
        onError: () => toast.error("Erro ao atualizar status"),
      }
    );
  }

  function handleRenovar(id: number) {
    atualizarStatus.mutate(
      { id, status: "ativo" },
      {
        onSuccess: () => toast.success("Assinatura renovada por +30 dias!"),
        onError: () => toast.error("Erro ao renovar"),
      }
    );
  }

  function openEdit(r: Restaurante) {
    setEditForm({
      nome_fantasia: r.nome_fantasia,
      email: r.email,
      telefone: r.telefone,
      plano: r.plano,
    });
    setEditModal(r);
  }

  function handleSaveEdit() {
    if (!editModal) return;
    const payload: Record<string, unknown> = {};
    if (editForm.nome_fantasia !== editModal.nome_fantasia) payload.nome_fantasia = editForm.nome_fantasia;
    if (editForm.email !== editModal.email) payload.email = editForm.email;
    if (editForm.telefone !== editModal.telefone) payload.telefone = editForm.telefone;
    if (editForm.plano !== editModal.plano) payload.plano = editForm.plano;

    if (Object.keys(payload).length === 0) {
      toast.info("Nenhuma alteração detectada");
      setEditModal(null);
      return;
    }

    atualizarRest.mutate(
      { id: editModal.id, payload },
      {
        onSuccess: () => {
          toast.success("Restaurante atualizado!");
          setEditModal(null);
        },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao atualizar";
          toast.error(msg);
        },
      }
    );
  }

  const lista: Restaurante[] = restaurantes || [];

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold text-white">Gerenciar Restaurantes</h2>
          <Button
            className="bg-amber-600 hover:bg-amber-700 text-white"
            onClick={() => navigate("/restaurantes/novo")}
          >
            <Store className="mr-2 h-4 w-4" />
            Novo Restaurante
          </Button>
        </div>

        {/* Filtros */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-500" />
            <Input
              placeholder="Buscar por nome, email ou telefone..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-9 border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
            />
          </div>
          <Select value={filtroStatus} onValueChange={setFiltroStatus}>
            <SelectTrigger className="w-40 border-gray-700 bg-gray-800 text-white">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos</SelectItem>
              <SelectItem value="ativo">Ativo</SelectItem>
              <SelectItem value="suspenso">Suspenso</SelectItem>
              <SelectItem value="cancelado">Cancelado</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filtroPlano} onValueChange={setFiltroPlano}>
            <SelectTrigger className="w-40 border-gray-700 bg-gray-800 text-white">
              <SelectValue placeholder="Plano" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="todos">Todos</SelectItem>
              <SelectItem value="Básico">Básico</SelectItem>
              <SelectItem value="Essencial">Essencial</SelectItem>
              <SelectItem value="Avançado">Avançado</SelectItem>
              <SelectItem value="Premium">Premium</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Contador */}
        <p className="text-sm text-gray-400">
          {lista.length} restaurante(s) encontrado(s)
        </p>

        {/* Tabela */}
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Spinner className="h-6 w-6 text-amber-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-10 text-center">
            <Store className="mx-auto h-12 w-12 text-gray-600" />
            <p className="mt-3 text-gray-400">Nenhum restaurante encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-800">
            <Table>
              <TableHeader>
                <TableRow className="border-gray-800 hover:bg-transparent">
                  <TableHead className="text-gray-400">Restaurante</TableHead>
                  <TableHead className="text-gray-400">Plano</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-gray-400">Vencimento</TableHead>
                  <TableHead className="text-gray-400">Pedidos</TableHead>
                  <TableHead className="text-gray-400">Motoboys</TableHead>
                  <TableHead className="text-gray-400 text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lista.map((r) => {
                  const dias = diasRestantes(r.data_vencimento);
                  return (
                    <TableRow key={r.id} className="border-gray-800 hover:bg-gray-800/50">
                      <TableCell>
                        <div>
                          <p className="font-medium text-white">{r.nome_fantasia}</p>
                          <p className="text-xs text-gray-500">{r.email}</p>
                          <p className="text-xs text-gray-500">{r.telefone}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="border-gray-600 text-gray-300">
                          {r.plano}
                        </Badge>
                        <p className="mt-0.5 text-xs text-gray-500">
                          R$ {r.valor_plano.toFixed(2)}/mês
                        </p>
                      </TableCell>
                      <TableCell>{statusBadge(r.status)}</TableCell>
                      <TableCell>
                        <p className="text-sm text-gray-300">{formatDate(r.data_vencimento)}</p>
                        {dias !== null && (
                          <p className={cn(
                            "text-xs",
                            dias < 0 ? "text-red-400 font-medium" : dias <= 7 ? "text-yellow-400" : "text-gray-500"
                          )}>
                            {dias < 0
                              ? `Vencido há ${Math.abs(dias)} dias`
                              : dias === 0
                                ? "Vence hoje"
                                : `${dias} dias restantes`}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-gray-300">{r.total_pedidos}</TableCell>
                      <TableCell className="text-gray-300">{r.total_motoboys}</TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-purple-400 hover:text-purple-300"
                            onClick={() => { setDominioModal(r); setNovoDominio(""); }}
                          >
                            <Globe className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-gray-400 hover:text-white"
                            onClick={() => openEdit(r)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          {r.status !== "ativo" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-green-400 hover:text-green-300"
                              onClick={() => handleStatusChange(r.id, "ativo")}
                              disabled={atualizarStatus.isPending}
                            >
                              <Play className="h-4 w-4" />
                            </Button>
                          )}
                          {r.status === "ativo" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-yellow-400 hover:text-yellow-300"
                              onClick={() => handleStatusChange(r.id, "suspenso")}
                              disabled={atualizarStatus.isPending}
                            >
                              <Pause className="h-4 w-4" />
                            </Button>
                          )}
                          {r.status !== "cancelado" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-400 hover:text-red-300"
                              onClick={() => handleStatusChange(r.id, "cancelado")}
                              disabled={atualizarStatus.isPending}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-blue-400 hover:text-blue-300"
                            onClick={() => handleRenovar(r.id)}
                            disabled={atualizarStatus.isPending}
                          >
                            <RefreshCw className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </div>

      {/* Modal Editar */}
      <Dialog open={!!editModal} onOpenChange={(open) => !open && setEditModal(null)}>
        <DialogContent className="border-gray-800 bg-gray-900 text-white sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Restaurante</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Nome Fantasia</label>
              <Input
                value={editForm.nome_fantasia || ""}
                onChange={(e) => setEditForm({ ...editForm, nome_fantasia: e.target.value })}
                className="border-gray-700 bg-gray-800 text-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Email</label>
              <Input
                type="email"
                value={editForm.email || ""}
                onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                className="border-gray-700 bg-gray-800 text-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Telefone</label>
              <Input
                value={editForm.telefone || ""}
                onChange={(e) => setEditForm({ ...editForm, telefone: e.target.value })}
                className="border-gray-700 bg-gray-800 text-white"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Plano</label>
              <Select value={editForm.plano} onValueChange={(v) => setEditForm({ ...editForm, plano: v })}>
                <SelectTrigger className="border-gray-700 bg-gray-800 text-white">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Básico">Básico</SelectItem>
                  <SelectItem value="Essencial">Essencial</SelectItem>
                  <SelectItem value="Avançado">Avançado</SelectItem>
                  <SelectItem value="Premium">Premium</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditModal(null)} className="text-gray-400">
              Cancelar
            </Button>
            <Button
              className="bg-amber-600 hover:bg-amber-700 text-white"
              onClick={handleSaveEdit}
              disabled={atualizarRest.isPending}
            >
              {atualizarRest.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Salvando...</>
              ) : (
                "Salvar"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      {/* Modal Domínios */}
      <Dialog open={!!dominioModal} onOpenChange={(open) => !open && setDominioModal(null)}>
        <DialogContent className="border-gray-800 bg-gray-900 text-white sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-purple-400" />
              Domínios — {dominioModal?.nome_fantasia}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            {/* Adicionar novo domínio */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Adicionar novo domínio</label>
              <div className="flex gap-2">
                <Input
                  placeholder="www.meurestaurante.com.br"
                  value={novoDominio}
                  onChange={(e) => setNovoDominio(e.target.value)}
                  className="flex-1 border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && novoDominio.trim()) {
                      criarDom.mutate(
                        { restauranteId: dominioModal!.id, dominio: novoDominio.trim() },
                        {
                          onSuccess: (res) => {
                            toast.success(`Domínio adicionado! SSL: ${res.fly_certificado || "pendente"}`);
                            if (res.fly_aviso) toast.warning(res.fly_aviso);
                            setNovoDominio("");
                          },
                          onError: (err: unknown) => {
                            const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao adicionar";
                            toast.error(msg);
                          },
                        }
                      );
                    }
                  }}
                />
                <Button
                  className="bg-purple-600 hover:bg-purple-700 text-white"
                  disabled={!novoDominio.trim() || criarDom.isPending}
                  onClick={() => {
                    criarDom.mutate(
                      { restauranteId: dominioModal!.id, dominio: novoDominio.trim() },
                      {
                        onSuccess: (res) => {
                          toast.success(`Domínio adicionado! SSL: ${res.fly_certificado || "pendente"}`);
                          if (res.fly_aviso) toast.warning(res.fly_aviso);
                          setNovoDominio("");
                        },
                        onError: (err: unknown) => {
                          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao adicionar";
                          toast.error(msg);
                        },
                      }
                    );
                  }}
                >
                  {criarDom.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                </Button>
              </div>
            </div>

            {/* Lista de domínios */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-400">Domínios cadastrados</h4>
              {dominiosLoading ? (
                <div className="flex h-16 items-center justify-center">
                  <Spinner className="h-5 w-5 text-purple-400" />
                </div>
              ) : !dominios || dominios.length === 0 ? (
                <p className="rounded-lg border border-gray-800 bg-gray-800/50 p-4 text-center text-sm text-gray-500">
                  Nenhum domínio cadastrado
                </p>
              ) : (
                <div className="space-y-3">
                  {dominios.map((d: { id: number; dominio: string; verificado: boolean; ssl_ativo: boolean; criado_em: string | null }) => (
                    <div key={d.id} className="rounded-lg border border-gray-800 bg-gray-800/50 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-white">{d.dominio}</span>
                        <div className="flex items-center gap-1">
                          {d.verificado ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-green-500/20 px-2 py-0.5 text-xs text-green-400">
                              <CheckCircle2 className="h-3 w-3" /> Verificado
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-yellow-500/20 px-2 py-0.5 text-xs text-yellow-400">
                              <Clock className="h-3 w-3" /> Pendente
                            </span>
                          )}
                          {d.ssl_ativo && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/20 px-2 py-0.5 text-xs text-blue-400">
                              <Shield className="h-3 w-3" /> SSL
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          className="border-gray-700 text-gray-300 hover:text-white hover:bg-gray-700"
                          disabled={verificarDNS.isPending}
                          onClick={() => {
                            verificarDNS.mutate(d.id, {
                              onSuccess: (res) => {
                                if (res.verificado) toast.success(res.mensagem);
                                else toast.warning(res.mensagem);
                              },
                              onError: () => toast.error("Erro ao verificar DNS"),
                            });
                          }}
                        >
                          {verificarDNS.isPending ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : <RefreshCw className="mr-1 h-3 w-3" />}
                          Verificar DNS
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                          disabled={deletarDom.isPending}
                          onClick={() => {
                            deletarDom.mutate(d.id, {
                              onSuccess: (res) => toast.success(res.mensagem),
                              onError: () => toast.error("Erro ao remover domínio"),
                            });
                          }}
                        >
                          <Trash2 className="mr-1 h-3 w-3" /> Remover
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Instruções DNS */}
            <div className="rounded-lg border border-gray-700 bg-gray-800/70 p-4 space-y-2">
              <h4 className="text-sm font-medium text-gray-300">Instruções para o cliente</h4>
              <p className="text-xs text-gray-400">No painel DNS do domínio, criar o seguinte registro:</p>
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                <span className="text-gray-500">Tipo:</span>
                <span className="font-mono text-amber-400">CNAME</span>
                <span className="text-gray-500">Nome:</span>
                <span className="font-mono text-amber-400">www</span>
                <span className="text-gray-500">Valor:</span>
                <span className="font-mono text-amber-400">superfood-api.fly.dev</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">Aguardar até 48h para propagação do DNS.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </SuperAdminLayout>
  );
}
