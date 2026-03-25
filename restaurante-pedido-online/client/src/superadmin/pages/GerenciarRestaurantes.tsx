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
  useBotInstancias,
  useCriarBotInstancia,
  useDeletarBotInstancia,
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
  Bot,
} from "lucide-react";
import { useLocation } from "wouter";
import { cn } from "@/lib/utils";

interface Restaurante {
  id: number;
  nome_fantasia: string;
  razao_social?: string;
  cnpj?: string;
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
  endereco_completo?: string;
  cidade?: string;
  estado?: string;
}

function validarCpfCnpj(valor: string): boolean {
  const digits = valor.replace(/\D/g, "");
  if (digits.length === 11) {
    // Validar CPF
    if (/^(\d)\1{10}$/.test(digits)) return false;
    let soma = 0;
    for (let i = 0; i < 9; i++) soma += parseInt(digits[i]) * (10 - i);
    let resto = soma % 11;
    const d1 = resto < 2 ? 0 : 11 - resto;
    if (parseInt(digits[9]) !== d1) return false;
    soma = 0;
    for (let i = 0; i < 10; i++) soma += parseInt(digits[i]) * (11 - i);
    resto = soma % 11;
    const d2 = resto < 2 ? 0 : 11 - resto;
    return parseInt(digits[10]) === d2;
  }
  if (digits.length === 14) {
    // Validar CNPJ
    if (/^(\d)\1{13}$/.test(digits)) return false;
    const pesos1 = [5,4,3,2,9,8,7,6,5,4,3,2];
    let soma = 0;
    for (let i = 0; i < 12; i++) soma += parseInt(digits[i]) * pesos1[i];
    let resto = soma % 11;
    const d1 = resto < 2 ? 0 : 11 - resto;
    if (parseInt(digits[12]) !== d1) return false;
    const pesos2 = [6,5,4,3,2,9,8,7,6,5,4,3,2];
    soma = 0;
    for (let i = 0; i < 13; i++) soma += parseInt(digits[i]) * pesos2[i];
    resto = soma % 11;
    const d2 = resto < 2 ? 0 : 11 - resto;
    return parseInt(digits[13]) === d2;
  }
  return false;
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
  const [botModal, setBotModal] = useState<Restaurante | null>(null);
  const [botForm, setBotForm] = useState({
    evolution_instance: "",
    evolution_api_url: "https://derekh-evolution.fly.dev",
    evolution_api_key: "",
    whatsapp_numero: "",
    nome_atendente: "Bia",
    voz_tts: "ara",
    bot_ativo: false,
  });
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
  const { data: botInstancias } = useBotInstancias();
  const criarBot = useCriarBotInstancia();
  const deletarBot = useDeletarBotInstancia();

  function getBotForRestaurante(restId: number) {
    if (!botInstancias || !Array.isArray(botInstancias)) return null;
    return botInstancias.find((b: any) => b.restaurante_id === restId) || null;
  }

  function openBotModal(r: Restaurante) {
    const existing = getBotForRestaurante(r.id);
    if (existing) {
      setBotForm({
        evolution_instance: existing.evolution_instance || "",
        evolution_api_url: existing.evolution_api_url || "https://derekh-evolution.fly.dev",
        evolution_api_key: existing.evolution_api_key || "",
        whatsapp_numero: existing.whatsapp_numero || "",
        nome_atendente: existing.nome_atendente || "Bia",
        voz_tts: existing.voz_tts || "ara",
        bot_ativo: existing.bot_ativo || false,
      });
    } else {
      setBotForm({
        evolution_instance: "",
        evolution_api_url: "https://derekh-evolution.fly.dev",
        evolution_api_key: "",
        whatsapp_numero: "",
        nome_atendente: "Bia",
        voz_tts: "ara",
        bot_ativo: false,
      });
    }
    setBotModal(r);
  }

  function handleSaveBot() {
    if (!botModal) return;
    criarBot.mutate(
      { restauranteId: botModal.id, payload: botForm },
      {
        onSuccess: (data) => {
          toast.success(data.mensagem || "Bot configurado!");
          setBotModal(null);
        },
        onError: (err: any) => {
          toast.error(err?.response?.data?.detail || "Erro ao configurar bot");
        },
      }
    );
  }

  function handleDeleteBot(configId: number) {
    deletarBot.mutate(configId, {
      onSuccess: () => toast.success("Bot removido"),
      onError: () => toast.error("Erro ao remover bot"),
    });
  }

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
      razao_social: r.razao_social || "",
      cnpj: r.cnpj || "",
      email: r.email,
      telefone: r.telefone,
      endereco_completo: r.endereco_completo || "",
      cidade: r.cidade || "",
      estado: r.estado || "",
      plano: r.plano,
    });
    setEditModal(r);
  }

  function handleSaveEdit() {
    if (!editModal) return;

    // Validar CPF/CNPJ se preenchido
    const cnpjDigits = editForm.cnpj?.replace(/\D/g, "") || "";
    if (cnpjDigits && !validarCpfCnpj(cnpjDigits)) {
      toast.error("CPF/CNPJ inválido. Verifique os dígitos.");
      return;
    }

    const payload: Record<string, unknown> = {};
    if (editForm.nome_fantasia !== editModal.nome_fantasia) payload.nome_fantasia = editForm.nome_fantasia;
    if (editForm.razao_social !== (editModal.razao_social || "")) payload.razao_social = editForm.razao_social || null;
    if (cnpjDigits !== (editModal.cnpj || "")) payload.cnpj = cnpjDigits || null;
    if (editForm.email !== editModal.email) payload.email = editForm.email;
    if (editForm.telefone !== editModal.telefone) payload.telefone = editForm.telefone;
    if (editForm.endereco_completo !== (editModal.endereco_completo || "")) payload.endereco_completo = editForm.endereco_completo || null;
    if (editForm.cidade !== (editModal.cidade || "")) payload.cidade = editForm.cidade || null;
    if (editForm.estado !== (editModal.estado || "")) payload.estado = editForm.estado || null;
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
          <h2 className="text-2xl font-bold text-[var(--sa-text-primary)]">Gerenciar Restaurantes</h2>
          <Button
            className="bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)] text-white"
            onClick={() => navigate("/restaurantes/novo")}
          >
            <Store className="mr-2 h-4 w-4" />
            Novo Restaurante
          </Button>
        </div>

        {/* Filtros */}
        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--sa-text-dimmed)]" />
            <Input
              placeholder="Buscar por nome, email ou telefone..."
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              className="pl-9 border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)] placeholder:text-[var(--sa-text-dimmed)]"
            />
          </div>
          <Select value={filtroStatus} onValueChange={setFiltroStatus}>
            <SelectTrigger className="w-40 border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]">
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
            <SelectTrigger className="w-40 border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]">
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
        <p className="text-sm text-[var(--sa-text-muted)]">
          {lista.length} restaurante(s) encontrado(s)
        </p>

        {/* Tabela */}
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Spinner className="h-6 w-6 text-amber-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-10 text-center">
            <Store className="mx-auto h-12 w-12 text-[var(--sa-text-dimmed)]" />
            <p className="mt-3 text-[var(--sa-text-muted)]">Nenhum restaurante encontrado</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-[var(--sa-border)]">
            <Table>
              <TableHeader>
                <TableRow className="border-[var(--sa-border)] hover:bg-transparent">
                  <TableHead className="text-[var(--sa-text-muted)]">Restaurante</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Plano</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Status</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Vencimento</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Pedidos</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Motoboys</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)] text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lista.map((r) => {
                  const dias = diasRestantes(r.data_vencimento);
                  return (
                    <TableRow key={r.id} className="border-[var(--sa-border)] hover:bg-[var(--sa-bg-hover)]/50">
                      <TableCell>
                        <div>
                          <p className="font-medium text-[var(--sa-text-primary)]">{r.nome_fantasia}</p>
                          <p className="text-xs text-[var(--sa-text-dimmed)]">{r.email}</p>
                          <p className="text-xs text-[var(--sa-text-dimmed)]">{r.telefone}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline" className="border-[var(--sa-border-input)] text-[var(--sa-text-secondary)]">
                          {r.plano}
                        </Badge>
                        <p className="mt-0.5 text-xs text-[var(--sa-text-dimmed)]">
                          R$ {r.valor_plano.toFixed(2)}/mês
                        </p>
                      </TableCell>
                      <TableCell>{statusBadge(r.status)}</TableCell>
                      <TableCell>
                        <p className="text-sm text-[var(--sa-text-secondary)]">{formatDate(r.data_vencimento)}</p>
                        {dias !== null && (
                          <p className={cn(
                            "text-xs",
                            dias < 0 ? "text-red-400 font-medium" : dias <= 7 ? "text-yellow-400" : "text-[var(--sa-text-dimmed)]"
                          )}>
                            {dias < 0
                              ? `Vencido há ${Math.abs(dias)} dias`
                              : dias === 0
                                ? "Vence hoje"
                                : `${dias} dias restantes`}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-[var(--sa-text-secondary)]">{r.total_pedidos}</TableCell>
                      <TableCell className="text-[var(--sa-text-secondary)]">{r.total_motoboys}</TableCell>
                      <TableCell>
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className={cn(
                              "hover:text-green-300",
                              getBotForRestaurante(r.id) ? "text-green-400" : "text-[var(--sa-text-muted)]"
                            )}
                            onClick={() => openBotModal(r)}
                            title={getBotForRestaurante(r.id) ? "Bot ativo — editar" : "Criar Humanoide"}
                          >
                            <Bot className="h-4 w-4" />
                          </Button>
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
                            className="text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
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
        <DialogContent className="border-[var(--sa-border)] bg-[var(--sa-bg-surface)] text-white sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Editar Restaurante</DialogTitle>
            {editModal && (
              <p className="text-xs text-[var(--sa-text-dimmed)]">Código: {editModal.codigo_acesso}</p>
            )}
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Nome Fantasia</label>
                <Input
                  value={editForm.nome_fantasia || ""}
                  onChange={(e) => setEditForm({ ...editForm, nome_fantasia: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Razão Social</label>
                <Input
                  value={editForm.razao_social || ""}
                  onChange={(e) => setEditForm({ ...editForm, razao_social: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                  placeholder="Opcional"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">CPF/CNPJ</label>
              <Input
                value={editForm.cnpj || ""}
                onChange={(e) => setEditForm({ ...editForm, cnpj: e.target.value })}
                className={cn(
                  "border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]",
                  editForm.cnpj && editForm.cnpj.replace(/\D/g, "").length >= 11 && !validarCpfCnpj(editForm.cnpj)
                    ? "border-red-500 focus-visible:ring-red-500"
                    : editForm.cnpj && validarCpfCnpj(editForm.cnpj)
                      ? "border-green-500 focus-visible:ring-green-500"
                      : ""
                )}
                placeholder="CPF (11 dígitos) ou CNPJ (14 dígitos)"
              />
              {editForm.cnpj && editForm.cnpj.replace(/\D/g, "").length >= 11 && (
                <p className={cn("text-xs", validarCpfCnpj(editForm.cnpj) ? "text-green-400" : "text-red-400")}>
                  {validarCpfCnpj(editForm.cnpj) ? "CPF/CNPJ válido" : "CPF/CNPJ inválido"}
                </p>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Email</label>
                <Input
                  type="email"
                  value={editForm.email || ""}
                  onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Telefone</label>
                <Input
                  value={editForm.telefone || ""}
                  onChange={(e) => setEditForm({ ...editForm, telefone: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Endereço</label>
              <Input
                value={editForm.endereco_completo || ""}
                onChange={(e) => setEditForm({ ...editForm, endereco_completo: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                placeholder="Rua, número, bairro"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Cidade</label>
                <Input
                  value={editForm.cidade || ""}
                  onChange={(e) => setEditForm({ ...editForm, cidade: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Estado</label>
                <Input
                  value={editForm.estado || ""}
                  onChange={(e) => setEditForm({ ...editForm, estado: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                  placeholder="UF"
                  maxLength={2}
                />
              </div>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Plano</label>
              <Select value={editForm.plano} onValueChange={(v) => setEditForm({ ...editForm, plano: v })}>
                <SelectTrigger className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]">
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
            <Button variant="ghost" onClick={() => setEditModal(null)} className="text-[var(--sa-text-muted)]">
              Cancelar
            </Button>
            <Button
              className="bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)] text-white"
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
        <DialogContent className="border-[var(--sa-border)] bg-[var(--sa-bg-surface)] text-white sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5 text-purple-400" />
              Domínios — {dominioModal?.nome_fantasia}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-5">
            {/* Adicionar novo domínio */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Adicionar novo domínio</label>
              <div className="flex gap-2">
                <Input
                  placeholder="www.meurestaurante.com.br"
                  value={novoDominio}
                  onChange={(e) => setNovoDominio(e.target.value)}
                  className="flex-1 border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)] placeholder:text-[var(--sa-text-dimmed)]"
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
              <h4 className="text-sm font-medium text-[var(--sa-text-muted)]">Domínios cadastrados</h4>
              {dominiosLoading ? (
                <div className="flex h-16 items-center justify-center">
                  <Spinner className="h-5 w-5 text-purple-400" />
                </div>
              ) : !dominios || dominios.length === 0 ? (
                <p className="rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg-hover)]/50 p-4 text-center text-sm text-[var(--sa-text-dimmed)]">
                  Nenhum domínio cadastrado
                </p>
              ) : (
                <div className="space-y-3">
                  {dominios.map((d: { id: number; dominio: string; verificado: boolean; ssl_ativo: boolean; criado_em: string | null }) => (
                    <div key={d.id} className="rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg-hover)]/50 p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-medium text-[var(--sa-text-primary)]">{d.dominio}</span>
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
                          className="border-[var(--sa-border-input)] text-[var(--sa-text-secondary)] hover:text-[var(--sa-text-primary)] hover:bg-[var(--sa-bg-hover)]"
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
            <div className="rounded-lg border border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)]/70 p-4 space-y-2">
              <h4 className="text-sm font-medium text-[var(--sa-text-secondary)]">Instruções para o cliente</h4>
              <p className="text-xs text-[var(--sa-text-muted)]">No painel DNS do domínio, criar o seguinte registro:</p>
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                <span className="text-[var(--sa-text-dimmed)]">Tipo:</span>
                <span className="font-mono text-amber-400">CNAME</span>
                <span className="text-[var(--sa-text-dimmed)]">Nome:</span>
                <span className="font-mono text-amber-400">www</span>
                <span className="text-[var(--sa-text-dimmed)]">Valor:</span>
                <span className="font-mono text-amber-400">superfood-api.fly.dev</span>
              </div>
              <p className="text-xs text-[var(--sa-text-dimmed)] mt-1">Aguardar até 48h para propagação do DNS.</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Modal Bot WhatsApp */}
      <Dialog open={!!botModal} onOpenChange={(open) => !open && setBotModal(null)}>
        <DialogContent className="border-[var(--sa-border)] bg-[var(--sa-bg-surface)] text-white sm:max-w-lg max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bot className="h-5 w-5 text-green-400" />
              WhatsApp Humanoide — {botModal?.nome_fantasia}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {getBotForRestaurante(botModal?.id ?? 0) && (
              <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 p-3">
                <Bot className="h-5 w-5 text-green-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-green-400">Bot já configurado</p>
                  <p className="text-xs text-[var(--sa-text-muted)]">
                    Editando configuração existente
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  onClick={() => {
                    const bot = getBotForRestaurante(botModal?.id ?? 0);
                    if (bot) {
                      handleDeleteBot(bot.id);
                      setBotModal(null);
                    }
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-1" /> Remover
                </Button>
              </div>
            )}
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Instância Evolution</label>
              <Input
                value={botForm.evolution_instance}
                onChange={(e) => setBotForm({ ...botForm, evolution_instance: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                placeholder="nome-da-instancia"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">URL Evolution API</label>
              <Input
                value={botForm.evolution_api_url}
                onChange={(e) => setBotForm({ ...botForm, evolution_api_url: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                placeholder="https://derekh-evolution.fly.dev"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">API Key Evolution</label>
              <Input
                type="password"
                value={botForm.evolution_api_key}
                onChange={(e) => setBotForm({ ...botForm, evolution_api_key: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                placeholder="API key"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Número WhatsApp</label>
              <Input
                value={botForm.whatsapp_numero}
                onChange={(e) => setBotForm({ ...botForm, whatsapp_numero: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                placeholder="5511999999999"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Nome do atendente</label>
                <Input
                  value={botForm.nome_atendente}
                  onChange={(e) => setBotForm({ ...botForm, nome_atendente: e.target.value })}
                  className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Voz TTS</label>
                <Select value={botForm.voz_tts} onValueChange={(v) => setBotForm({ ...botForm, voz_tts: v })}>
                  <SelectTrigger className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="rex">Rex (masculino)</SelectItem>
                    <SelectItem value="leo">Leo (masculino)</SelectItem>
                    <SelectItem value="sal">Sal (masculino)</SelectItem>
                    <SelectItem value="eve">Eve (feminino)</SelectItem>
                    <SelectItem value="ara">Ara (feminino)</SelectItem>
                    <SelectItem value="una">Una (feminino)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setBotModal(null)} className="text-[var(--sa-text-muted)]">
              Cancelar
            </Button>
            <Button
              className="bg-green-600 hover:bg-green-700 text-white"
              onClick={handleSaveBot}
              disabled={criarBot.isPending || !botForm.evolution_instance}
            >
              {criarBot.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Salvando...</>
              ) : getBotForRestaurante(botModal?.id ?? 0) ? (
                "Atualizar Bot"
              ) : (
                "Criar Humanoide"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SuperAdminLayout>
  );
}
