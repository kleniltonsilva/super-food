import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  useGarcons, useCriarGarcom, useAtualizarGarcom, useDeletarGarcom,
  useConfigGarcom, useAtualizarConfigGarcom,
  useSessoesGarcom, useFecharSessaoGarcom,
} from "@/admin/hooks/useAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import {
  Users, Plus, Pencil, Trash2, Clock, DollarSign,
  UserCheck, Settings, Monitor,
} from "lucide-react";
import { toast } from "sonner";

// ─── Aba Garçons (CRUD) ────────────────────────────────

function GarconsTab() {
  const { data: garcons, isLoading } = useGarcons();
  const criarGarcom = useCriarGarcom();
  const atualizarGarcom = useAtualizarGarcom();
  const deletarGarcom = useDeletarGarcom();
  const [editId, setEditId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ nome: "", login: "", senha: "", avatar_emoji: "", modo_secao: "TODOS", secao_inicio: "", secao_fim: "" });

  function resetForm() {
    setForm({ nome: "", login: "", senha: "", avatar_emoji: "", modo_secao: "TODOS", secao_inicio: "", secao_fim: "" });
    setEditId(null);
    setShowForm(false);
  }

  function editGarcom(g: any) {
    setForm({
      nome: g.nome,
      login: g.login,
      senha: "",
      avatar_emoji: g.avatar_emoji || "",
      modo_secao: g.modo_secao || "TODOS",
      secao_inicio: g.secao_inicio?.toString() || "",
      secao_fim: g.secao_fim?.toString() || "",
    });
    setEditId(g.id);
    setShowForm(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    try {
      const payload: any = {
        nome: form.nome,
        login: form.login,
        modo_secao: form.modo_secao,
        avatar_emoji: form.avatar_emoji || undefined,
        secao_inicio: form.secao_inicio ? parseInt(form.secao_inicio) : undefined,
        secao_fim: form.secao_fim ? parseInt(form.secao_fim) : undefined,
      };
      if (editId) {
        if (form.senha) payload.senha = form.senha;
        await atualizarGarcom.mutateAsync({ id: editId, ...payload });
        toast.success("Garçom atualizado");
      } else {
        payload.senha = form.senha;
        await criarGarcom.mutateAsync(payload);
        toast.success("Garçom criado");
      }
      resetForm();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro");
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Deletar este garçom?")) return;
    try {
      await deletarGarcom.mutateAsync(id);
      toast.success("Garçom deletado");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro");
    }
  }

  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-semibold text-[var(--text-primary)]">Garçons ({(garcons || []).length})</h3>
        <Button size="sm" onClick={() => { resetForm(); setShowForm(true); }}>
          <Plus className="h-4 w-4 mr-1" /> Novo
        </Button>
      </div>

      {/* Form */}
      {showForm && (
        <form onSubmit={handleSubmit} className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>Nome</Label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} required />
            </div>
            <div>
              <Label>Login</Label>
              <Input value={form.login} onChange={(e) => setForm({ ...form, login: e.target.value })} required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label>{editId ? "Nova senha (deixe vazio para manter)" : "Senha"}</Label>
              <Input type="password" value={form.senha} onChange={(e) => setForm({ ...form, senha: e.target.value })} required={!editId} />
            </div>
            <div>
              <Label>Emoji (opcional)</Label>
              <Input value={form.avatar_emoji} onChange={(e) => setForm({ ...form, avatar_emoji: e.target.value })} placeholder="Ex: 👨‍🍳" maxLength={4} />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label>Modo</Label>
              <select
                value={form.modo_secao}
                onChange={(e) => setForm({ ...form, modo_secao: e.target.value })}
                className="w-full rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface)] px-3 py-2 text-sm text-[var(--text-primary)]"
              >
                <option value="TODOS">Todas as mesas</option>
                <option value="FAIXA">Faixa de mesas</option>
                <option value="CUSTOM">Mesas específicas</option>
              </select>
            </div>
            {form.modo_secao === "FAIXA" && (
              <>
                <div>
                  <Label>Mesa início</Label>
                  <Input type="number" value={form.secao_inicio} onChange={(e) => setForm({ ...form, secao_inicio: e.target.value })} />
                </div>
                <div>
                  <Label>Mesa fim</Label>
                  <Input type="number" value={form.secao_fim} onChange={(e) => setForm({ ...form, secao_fim: e.target.value })} />
                </div>
              </>
            )}
          </div>
          <div className="flex gap-2">
            <Button type="submit" size="sm" disabled={criarGarcom.isPending || atualizarGarcom.isPending}>
              {editId ? "Salvar" : "Criar"}
            </Button>
            <Button type="button" variant="outline" size="sm" onClick={resetForm}>Cancelar</Button>
          </div>
        </form>
      )}

      {/* Lista */}
      <div className="space-y-2">
        {(garcons || []).map((g: any) => (
          <div key={g.id} className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
            <div className="flex items-center gap-3">
              <span className="text-xl">{g.avatar_emoji || "👤"}</span>
              <div>
                <p className="font-medium text-sm text-[var(--text-primary)]">{g.nome}</p>
                <p className="text-xs text-[var(--text-muted)]">
                  @{g.login} • {g.modo_secao === "TODOS" ? "Todas mesas" : g.modo_secao === "FAIXA" ? `Mesas ${g.secao_inicio}-${g.secao_fim}` : "Custom"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <span className={`px-2 py-0.5 rounded text-[10px] ${g.ativo ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}`}>
                {g.ativo ? "Ativo" : "Inativo"}
              </span>
              <Button variant="ghost" size="icon-sm" onClick={() => editGarcom(g)}>
                <Pencil className="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="icon-sm" onClick={() => handleDelete(g.id)} className="text-red-400 hover:text-red-300">
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        ))}
        {(garcons || []).length === 0 && (
          <p className="text-center py-8 text-[var(--text-muted)]">Nenhum garçom cadastrado</p>
        )}
      </div>
    </div>
  );
}

// ─── Aba Config ────────────────────────────────────────

function ConfigTab() {
  const { data: config, isLoading } = useConfigGarcom();
  const atualizarConfig = useAtualizarConfigGarcom();

  async function handleToggle(field: string, value: any) {
    try {
      await atualizarConfig.mutateAsync({ [field]: value });
      toast.success("Configuração salva");
    } catch {
      toast.error("Erro ao salvar");
    }
  }

  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>;

  return (
    <div className="space-y-4">
      {/* Ativar/Desativar */}
      <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
        <div>
          <p className="font-medium text-[var(--text-primary)]">App Garçom</p>
          <p className="text-xs text-[var(--text-muted)]">Habilita login de garçons pelo app</p>
        </div>
        <Switch
          checked={config?.garcom_ativo || false}
          onCheckedChange={(v) => handleToggle("garcom_ativo", v)}
        />
      </div>

      {/* Taxa de serviço */}
      <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4 space-y-3">
        <p className="font-medium text-[var(--text-primary)]">Taxa de Serviço</p>
        <div className="flex items-center gap-3">
          <Input
            type="number"
            step="0.01"
            value={config?.taxa_servico || 0.10}
            onChange={(e) => handleToggle("taxa_servico", parseFloat(e.target.value) || 0)}
            className="w-24"
          />
          <span className="text-sm text-[var(--text-muted)]">
            {config?.pct_taxa ? "% do subtotal" : "valor fixo"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Switch
            checked={config?.pct_taxa !== false}
            onCheckedChange={(v) => handleToggle("pct_taxa", v)}
          />
          <span className="text-xs text-[var(--text-muted)]">Percentual</span>
        </div>
      </div>

      {/* Permitir cancelamento */}
      <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-4">
        <div>
          <p className="font-medium text-[var(--text-primary)]">Cancelamento de itens</p>
          <p className="text-xs text-[var(--text-muted)]">Garçom pode cancelar itens de pedidos em preparo</p>
        </div>
        <Switch
          checked={config?.permitir_cancelamento !== false}
          onCheckedChange={(v) => handleToggle("permitir_cancelamento", v)}
        />
      </div>
    </div>
  );
}

// ─── Aba Mesas Ativas (Monitor) ───────────────────────

function MonitorTab() {
  const { data: sessoes, isLoading } = useSessoesGarcom();
  const fecharSessao = useFecharSessaoGarcom();

  async function handleFechar(sessaoId: number) {
    if (!confirm("Fechar esta sessão?")) return;
    try {
      await fecharSessao.mutateAsync(sessaoId);
      toast.success("Sessão fechada");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro");
    }
  }

  if (isLoading) return <div className="flex justify-center py-8"><Spinner className="h-6 w-6" /></div>;

  const list = sessoes || [];

  return (
    <div className="space-y-2">
      <h3 className="font-semibold text-[var(--text-primary)]">Mesas Ativas ({list.length})</h3>
      {list.length === 0 ? (
        <p className="text-center py-8 text-[var(--text-muted)]">Nenhuma mesa ativa</p>
      ) : (
        list.map((s: any) => (
          <div key={s.sessao_id} className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-card)] p-3">
            <div className="flex items-center gap-3">
              <div className={`h-10 w-10 rounded-lg flex items-center justify-center font-bold font-mono ${
                s.status === "FECHANDO" ? "bg-red-500/20 text-red-400" : "bg-amber-500/20 text-amber-400"
              }`}>
                {s.mesa_id}
              </div>
              <div>
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  Mesa {s.mesa_id}
                  {s.status === "FECHANDO" && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-400">FECHANDO</span>}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {s.garcom_nome || "—"} • {s.qtd_pessoas}p • {s.qtd_pedidos} pedidos
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="font-mono text-sm font-semibold text-[var(--text-primary)]">R$ {(s.total || 0).toFixed(2)}</p>
                <p className="text-[10px] text-[var(--text-muted)]">
                  <Clock className="inline h-3 w-3 mr-0.5" />
                  {s.criado_em ? new Date(s.criado_em).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" }) : "—"}
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleFechar(s.sessao_id)}
                disabled={fecharSessao.isPending}
                className="text-xs"
              >
                Fechar
              </Button>
            </div>
          </div>
        ))
      )}
    </div>
  );
}

// ─── Página Principal ──────────────────────────────────

export default function Garcons() {
  const [tab, setTab] = useState<"garcons" | "config" | "monitor">("garcons");

  const tabs = [
    { key: "garcons" as const, label: "Garçons", icon: UserCheck },
    { key: "config" as const, label: "Config", icon: Settings },
    { key: "monitor" as const, label: "Mesas Ativas", icon: Monitor },
  ];

  return (
    <AdminLayout>
      {/* Tabs */}
      <div className="flex gap-1 mb-4">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key
                ? "bg-[var(--cor-primaria)] text-white"
                : "text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {tab === "garcons" && <GarconsTab />}
      {tab === "config" && <ConfigTab />}
      {tab === "monitor" && <MonitorTab />}
    </AdminLayout>
  );
}
