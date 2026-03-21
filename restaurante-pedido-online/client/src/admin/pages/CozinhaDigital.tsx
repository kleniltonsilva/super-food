import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
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
import { toast } from "sonner";
import { ChefHat, Plus, Pencil, Trash2, Activity, Settings, Users } from "lucide-react";
import {
  useCozinheiros,
  useCriarCozinheiro,
  useAtualizarCozinheiro,
  useDeletarCozinheiro,
  useConfigCozinha,
  useAtualizarConfigCozinha,
  useDashboardCozinha,
  useProdutos,
} from "@/admin/hooks/useAdminQueries";

const EMOJIS_COZINHEIRO = ["👨‍🍳", "👩‍🍳", "🧑‍🍳", "🔥", "🍳", "🥘", "🍕", "🍔"];

interface CozinheiroForm {
  nome: string;
  login: string;
  senha: string;
  modo: string;
  avatar_emoji: string;
  produto_ids: number[];
}

const formDefault: CozinheiroForm = {
  nome: "",
  login: "",
  senha: "",
  modo: "todos",
  avatar_emoji: "👨‍🍳",
  produto_ids: [],
};

export default function CozinhaDigital() {
  const [tab, setTab] = useState<"cozinheiros" | "config" | "monitor">("cozinheiros");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<CozinheiroForm>(formDefault);

  // Queries
  const { data: cozinheiros = [], isLoading: loadingCoz } = useCozinheiros();
  const { data: configCozinha } = useConfigCozinha();
  const { data: dashboard } = useDashboardCozinha();
  const { data: produtos = [] } = useProdutos();
  const criarMut = useCriarCozinheiro();
  const atualizarMut = useAtualizarCozinheiro();
  const deletarMut = useDeletarCozinheiro();
  const configMut = useAtualizarConfigCozinha();

  function openCreate() {
    setEditId(null);
    setForm(formDefault);
    setDialogOpen(true);
  }

  function openEdit(c: any) {
    setEditId(c.id);
    setForm({
      nome: c.nome,
      login: c.login,
      senha: "",
      modo: c.modo,
      avatar_emoji: c.avatar_emoji || "👨‍🍳",
      produto_ids: c.produto_ids || [],
    });
    setDialogOpen(true);
  }

  async function handleSave() {
    if (!form.nome.trim() || !form.login.trim()) {
      toast.error("Nome e login são obrigatórios");
      return;
    }
    if (!editId && !form.senha.trim()) {
      toast.error("Senha é obrigatória para novo cozinheiro");
      return;
    }

    try {
      if (editId) {
        await atualizarMut.mutateAsync({
          id: editId,
          nome: form.nome,
          login: form.login,
          senha: form.senha || undefined,
          modo: form.modo,
          avatar_emoji: form.avatar_emoji,
          produto_ids: form.modo === "individual" ? form.produto_ids : [],
        });
        toast.success("Cozinheiro atualizado");
      } else {
        await criarMut.mutateAsync({
          nome: form.nome,
          login: form.login,
          senha: form.senha,
          modo: form.modo,
          avatar_emoji: form.avatar_emoji,
          produto_ids: form.modo === "individual" ? form.produto_ids : [],
        });
        toast.success("Cozinheiro criado");
      }
      setDialogOpen(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao salvar");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Desativar este cozinheiro?")) return;
    try {
      await deletarMut.mutateAsync(id);
      toast.success("Cozinheiro desativado");
    } catch {
      toast.error("Erro ao desativar");
    }
  }

  function toggleProduto(pid: number) {
    setForm((prev) => ({
      ...prev,
      produto_ids: prev.produto_ids.includes(pid)
        ? prev.produto_ids.filter((id) => id !== pid)
        : [...prev.produto_ids, pid],
    }));
  }

  const tabs = [
    { key: "cozinheiros" as const, label: "Cozinheiros", icon: Users },
    { key: "config" as const, label: "Configuração", icon: Settings },
    { key: "monitor" as const, label: "Monitor", icon: Activity },
  ];

  return (
    <AdminLayout>
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <ChefHat className="h-6 w-6 text-[var(--cor-primaria)]" />
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Cozinha Digital</h1>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b border-[var(--border-subtle)]">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === t.key
                ? "border-[var(--cor-primaria)] text-[var(--cor-primaria)]"
                : "border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab: Cozinheiros */}
      {tab === "cozinheiros" && (
        <div>
          <div className="mb-4 flex items-center justify-between">
            <p className="text-sm text-[var(--text-muted)]">
              {cozinheiros.length} cozinheiro{cozinheiros.length !== 1 ? "s" : ""} ativo{cozinheiros.length !== 1 ? "s" : ""}
            </p>
            <Button onClick={openCreate} size="sm">
              <Plus className="h-4 w-4 mr-1" /> Novo Cozinheiro
            </Button>
          </div>

          {loadingCoz ? (
            <p className="text-[var(--text-muted)] text-center py-8">Carregando...</p>
          ) : cozinheiros.length === 0 ? (
            <div className="text-center py-12 text-[var(--text-muted)]">
              <ChefHat className="mx-auto h-12 w-12 mb-3 opacity-30" />
              <p>Nenhum cozinheiro cadastrado</p>
              <p className="text-xs mt-1">Crie cozinheiros para usar o KDS</p>
            </div>
          ) : (
            <div className="space-y-2">
              {cozinheiros.map((c: any) => (
                <div
                  key={c.id}
                  className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{c.avatar_emoji || "👨‍🍳"}</span>
                    <div>
                      <p className="font-medium text-[var(--text-primary)]">{c.nome}</p>
                      <p className="text-xs text-[var(--text-muted)]">
                        Login: {c.login} &middot;{" "}
                        <Badge variant={c.modo === "todos" ? "default" : "secondary"} className="text-xs">
                          {c.modo === "todos" ? "Todos os produtos" : `${c.produto_ids?.length || 0} produtos`}
                        </Badge>
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="ghost" size="icon-sm" onClick={() => openEdit(c)}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" onClick={() => handleDelete(c.id)}>
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Configuração */}
      {tab === "config" && (
        <div className="max-w-lg space-y-6">
          <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
            <div>
              <p className="font-medium text-[var(--text-primary)]">KDS Ativo</p>
              <p className="text-xs text-[var(--text-muted)]">
                Ativa o Kitchen Display System para cozinheiros
              </p>
            </div>
            <Switch
              checked={configCozinha?.kds_ativo ?? false}
              onCheckedChange={(checked) => {
                configMut.mutate(
                  { kds_ativo: checked },
                  { onSuccess: () => toast.success(checked ? "KDS ativado" : "KDS desativado") }
                );
              }}
            />
          </div>

          <div className="space-y-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
            <p className="font-medium text-[var(--text-primary)]">Tempos de Alerta</p>

            <div className="space-y-2">
              <Label>Tempo de alerta (minutos)</Label>
              <Input
                type="number"
                min={1}
                value={configCozinha?.tempo_alerta_min ?? 15}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (val > 0) configMut.mutate({ tempo_alerta_min: val });
                }}
              />
              <p className="text-xs text-[var(--text-muted)]">
                Pedido fica amarelo após este tempo
              </p>
            </div>

            <div className="space-y-2">
              <Label>Tempo crítico (minutos)</Label>
              <Input
                type="number"
                min={1}
                value={configCozinha?.tempo_critico_min ?? 25}
                onChange={(e) => {
                  const val = parseInt(e.target.value);
                  if (val > 0) configMut.mutate({ tempo_critico_min: val });
                }}
              />
              <p className="text-xs text-[var(--text-muted)]">
                Pedido fica vermelho após este tempo
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
            <div>
              <p className="font-medium text-[var(--text-primary)]">Som de novo pedido</p>
              <p className="text-xs text-[var(--text-muted)]">
                Toca alerta sonoro ao chegar pedido no KDS
              </p>
            </div>
            <Switch
              checked={configCozinha?.som_novo_pedido ?? true}
              onCheckedChange={(checked) => configMut.mutate({ som_novo_pedido: checked })}
            />
          </div>
        </div>
      )}

      {/* Tab: Monitor */}
      {tab === "monitor" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Novos", value: dashboard?.novo ?? 0, color: "text-red-500" },
              { label: "Fazendo", value: dashboard?.fazendo ?? 0, color: "text-amber-500" },
              { label: "Feitos", value: dashboard?.feito ?? 0, color: "text-green-500" },
              { label: "Prontos", value: dashboard?.pronto ?? 0, color: "text-cyan-500" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 text-center"
              >
                <p className={`text-3xl font-bold ${item.color}`}>{item.value}</p>
                <p className="text-xs text-[var(--text-muted)] mt-1">{item.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
              <p className="text-sm text-[var(--text-muted)]">Tempo Médio de Preparo</p>
              <p className="text-2xl font-bold text-[var(--text-primary)]">
                {dashboard?.tempo_medio_min ?? 0} min
              </p>
            </div>
            <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
              <p className="text-sm text-[var(--text-muted)]">Cozinheiros Ativos</p>
              <p className="text-2xl font-bold text-[var(--text-primary)]">
                {dashboard?.cozinheiros_ativos ?? 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Dialog Criar/Editar Cozinheiro */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Cozinheiro" : "Novo Cozinheiro"}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4">
            {/* Avatar emoji */}
            <div className="space-y-2">
              <Label>Avatar</Label>
              <div className="flex gap-2 flex-wrap">
                {EMOJIS_COZINHEIRO.map((e) => (
                  <button
                    key={e}
                    onClick={() => setForm((f) => ({ ...f, avatar_emoji: e }))}
                    className={`text-2xl p-1.5 rounded-lg border transition-colors ${
                      form.avatar_emoji === e
                        ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/10"
                        : "border-transparent hover:bg-[var(--bg-card-hover)]"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label>Nome</Label>
              <Input
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                placeholder="Ex: João da Grelha"
              />
            </div>

            <div className="space-y-2">
              <Label>Login</Label>
              <Input
                value={form.login}
                onChange={(e) => setForm((f) => ({ ...f, login: e.target.value }))}
                placeholder="Ex: joao"
              />
            </div>

            <div className="space-y-2">
              <Label>{editId ? "Nova Senha (deixe vazio para manter)" : "Senha"}</Label>
              <Input
                type="password"
                value={form.senha}
                onChange={(e) => setForm((f) => ({ ...f, senha: e.target.value }))}
                placeholder={editId ? "••••••" : "Mín. 4 caracteres"}
              />
            </div>

            <div className="space-y-2">
              <Label>Modo de Produtos</Label>
              <Select value={form.modo} onValueChange={(v) => setForm((f) => ({ ...f, modo: v }))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos os produtos</SelectItem>
                  <SelectItem value="individual">Produtos específicos</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {form.modo === "individual" && (
              <div className="space-y-2">
                <Label>Selecione os produtos</Label>
                <div className="max-h-48 overflow-y-auto space-y-1 rounded-lg border border-[var(--border-subtle)] p-2">
                  {produtos.length === 0 ? (
                    <p className="text-xs text-[var(--text-muted)] p-2">Nenhum produto cadastrado</p>
                  ) : (
                    produtos.map((p: any) => (
                      <label
                        key={p.id}
                        className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-[var(--bg-card-hover)] cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          checked={form.produto_ids.includes(p.id)}
                          onChange={() => toggleProduto(p.id)}
                          className="accent-[var(--cor-primaria)]"
                        />
                        <span className="text-sm text-[var(--text-primary)]">{p.nome}</span>
                      </label>
                    ))
                  )}
                </div>
                <p className="text-xs text-[var(--text-muted)]">
                  {form.produto_ids.length} selecionado{form.produto_ids.length !== 1 ? "s" : ""}
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={handleSave} disabled={criarMut.isPending || atualizarMut.isPending}>
              {editId ? "Salvar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
