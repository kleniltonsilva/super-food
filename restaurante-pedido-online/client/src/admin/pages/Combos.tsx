import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useCombos,
  useCriarCombo,
  useAtualizarCombo,
  useDeletarCombo,
  useProdutos,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Pencil, Trash2, Layers, Eye, EyeOff, Calendar, Users } from "lucide-react";
import { toast } from "sonner";

interface ComboItem {
  produto_id: number;
  quantidade: number;
}

interface ComboForm {
  nome: string;
  descricao: string;
  preco_combo: string;
  preco_original: string;
  ordem_exibicao: string;
  data_inicio: string;
  data_fim: string;
  tipo_combo: string;
  dia_semana: string;
  quantidade_pessoas: string;
  itens: ComboItem[];
}

const DIAS_SEMANA = [
  { value: "0", label: "Segunda-feira" },
  { value: "1", label: "Terça-feira" },
  { value: "2", label: "Quarta-feira" },
  { value: "3", label: "Quinta-feira" },
  { value: "4", label: "Sexta-feira" },
  { value: "5", label: "Sábado" },
  { value: "6", label: "Domingo" },
];

const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

const emptyForm: ComboForm = {
  nome: "", descricao: "", preco_combo: "", preco_original: "",
  ordem_exibicao: "0", data_inicio: "", data_fim: "",
  tipo_combo: "padrao", dia_semana: "", quantidade_pessoas: "",
  itens: [],
};

export default function Combos() {
  const { data: combos, isLoading } = useCombos();
  const { data: produtos } = useProdutos();
  const criarCombo = useCriarCombo();
  const atualizarCombo = useAtualizarCombo();
  const deletarCombo = useDeletarCombo();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<ComboForm>(emptyForm);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  function openNew() {
    setEditId(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(combo: Record<string, unknown>) {
    setEditId(combo.id as number);
    setForm({
      nome: combo.nome as string,
      descricao: (combo.descricao as string) || "",
      preco_combo: String(combo.preco_combo),
      preco_original: String(combo.preco_original),
      ordem_exibicao: String(combo.ordem_exibicao ?? 0),
      data_inicio: (combo.data_inicio as string)?.slice(0, 10) || "",
      data_fim: (combo.data_fim as string)?.slice(0, 10) || "",
      tipo_combo: (combo.tipo_combo as string) || "padrao",
      dia_semana: combo.dia_semana != null ? String(combo.dia_semana) : "",
      quantidade_pessoas: combo.quantidade_pessoas ? String(combo.quantidade_pessoas) : "",
      itens: (combo.itens as ComboItem[]) || [],
    });
    setShowForm(true);
  }

  function addItem() {
    setForm({ ...form, itens: [...form.itens, { produto_id: 0, quantidade: 1 }] });
  }

  function removeItem(idx: number) {
    setForm({ ...form, itens: form.itens.filter((_, i) => i !== idx) });
  }

  function updateItem(idx: number, field: string, value: number) {
    setForm({
      ...form,
      itens: form.itens.map((item, i) => (i === idx ? { ...item, [field]: value } : item)),
    });
  }

  function handleSave() {
    if (!form.nome.trim()) { toast.error("Informe o nome"); return; }
    if (!form.preco_combo) { toast.error("Informe o preço do combo"); return; }
    if (form.tipo_combo === "do_dia" && form.dia_semana === "") {
      toast.error("Selecione o dia da semana"); return;
    }
    if (form.tipo_combo === "kit_festa" && !form.quantidade_pessoas) {
      toast.error("Informe a quantidade de pessoas"); return;
    }

    const payload: Record<string, unknown> = {
      nome: form.nome.trim(),
      descricao: form.descricao.trim() || null,
      preco_combo: Number(form.preco_combo),
      preco_original: Number(form.preco_original || form.preco_combo),
      ordem_exibicao: Number(form.ordem_exibicao) || 0,
      data_inicio: form.data_inicio || null,
      data_fim: form.data_fim || null,
      tipo_combo: form.tipo_combo,
      dia_semana: form.tipo_combo === "do_dia" && form.dia_semana !== "" ? Number(form.dia_semana) : null,
      quantidade_pessoas: form.tipo_combo === "kit_festa" && form.quantidade_pessoas ? Number(form.quantidade_pessoas) : null,
      itens: form.itens.filter((i) => i.produto_id > 0),
    };

    if (editId) {
      atualizarCombo.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Combo atualizado"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      criarCombo.mutate(payload, {
        onSuccess: () => { toast.success("Combo criado"); setShowForm(false); },
        onError: () => toast.error("Erro ao criar"),
      });
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarCombo.mutate(deleteId, {
      onSuccess: () => { toast.success("Combo removido"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  const comboList: Record<string, unknown>[] = combos || [];
  const prodMap = new Map((produtos || []).map((p: Record<string, unknown>) => [p.id, p.nome]));

  function renderTipoBadge(combo: Record<string, unknown>) {
    const tipo = (combo.tipo_combo as string) || "padrao";
    if (tipo === "do_dia") {
      const dia = combo.dia_semana as number;
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-500/20 px-2 py-0.5 text-xs font-medium text-blue-400">
          <Calendar className="h-3 w-3" />
          {dia != null ? DIAS_CURTOS[dia] : "Dia"}
        </span>
      );
    }
    if (tipo === "kit_festa") {
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-purple-500/20 px-2 py-0.5 text-xs font-medium text-purple-400">
          <Users className="h-3 w-3" />
          {combo.quantidade_pessoas ? `${combo.quantidade_pessoas} pessoas` : "Kit Festa"}
        </span>
      );
    }
    return null;
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Combos</h2>
          <Button
            size="sm"
            className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
            onClick={openNew}
          >
            <Plus className="mr-1 h-4 w-4" /> Novo Combo
          </Button>
        </div>

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        ) : comboList.length === 0 ? (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardContent className="flex flex-col items-center justify-center gap-2 py-12">
              <Layers className="h-10 w-10 text-[var(--text-muted)]" />
              <p className="text-[var(--text-muted)]">Nenhum combo cadastrado</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {comboList.map((combo) => (
              <Card key={combo.id as number} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg text-[var(--text-primary)]">
                        {combo.nome as string}
                      </CardTitle>
                      {renderTipoBadge(combo)}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className={combo.ativo === false ? "text-red-400" : "text-green-400"}
                        onClick={() => {
                          atualizarCombo.mutate(
                            { id: combo.id as number, ativo: combo.ativo === false },
                            {
                              onSuccess: () => toast.success(combo.ativo === false ? "Combo ativado" : "Combo desativado"),
                              onError: () => toast.error("Erro ao atualizar"),
                            }
                          );
                        }}
                      >
                        {combo.ativo === false ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(combo)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-red-400"
                        onClick={() => setDeleteId(combo.id as number)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {combo.descricao ? (
                    <p className="mb-2 text-sm text-[var(--text-muted)]">{combo.descricao as string}</p>
                  ) : null}
                  <div className="flex items-baseline gap-2">
                    <span className="text-xl font-bold text-[var(--cor-primaria)]">
                      R$ {Number(combo.preco_combo).toFixed(2)}
                    </span>
                    {Number(combo.preco_original) > Number(combo.preco_combo) && (
                      <span className="text-sm text-[var(--text-muted)] line-through">
                        R$ {Number(combo.preco_original).toFixed(2)}
                      </span>
                    )}
                  </div>
                  {(combo.itens as ComboItem[])?.length > 0 && (
                    <div className="mt-2 space-y-1">
                      {(combo.itens as ComboItem[]).map((item, i) => (
                        <p key={i} className="text-xs text-[var(--text-secondary)]">
                          {item.quantidade}x {(prodMap.get(item.produto_id) as string) || `Produto #${item.produto_id}`}
                        </p>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Form Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Combo" : "Novo Combo"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Nome</label>
              <Input
                value={form.nome}
                onChange={(e) => setForm({ ...form, nome: e.target.value })}
                className="dark-input"
                placeholder="Nome do combo"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Descrição</label>
              <Textarea
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                className="dark-input"
                rows={2}
              />
            </div>

            {/* Tipo do Combo */}
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Tipo do Combo</label>
              <Select
                value={form.tipo_combo}
                onValueChange={(v) => setForm({ ...form, tipo_combo: v, dia_semana: "", quantidade_pessoas: "" })}
              >
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="padrao">Combo Padrão</SelectItem>
                  <SelectItem value="do_dia">Combo do Dia</SelectItem>
                  <SelectItem value="kit_festa">Kit Festa</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Dia da Semana (condicional) */}
            {form.tipo_combo === "do_dia" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Dia da Semana</label>
                <Select
                  value={form.dia_semana}
                  onValueChange={(v) => setForm({ ...form, dia_semana: v })}
                >
                  <SelectTrigger className="dark-input">
                    <SelectValue placeholder="Selecione o dia" />
                  </SelectTrigger>
                  <SelectContent>
                    {DIAS_SEMANA.map((d) => (
                      <SelectItem key={d.value} value={d.value}>{d.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Quantidade de Pessoas (condicional) */}
            {form.tipo_combo === "kit_festa" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Quantidade de Pessoas</label>
                <Input
                  type="number"
                  min="1"
                  value={form.quantidade_pessoas}
                  onChange={(e) => setForm({ ...form, quantidade_pessoas: e.target.value })}
                  className="dark-input"
                  placeholder="Ex: 10, 20, 50"
                />
              </div>
            )}

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Preço Combo</label>
                <Input
                  type="number"
                  step="0.01"
                  value={form.preco_combo}
                  onChange={(e) => setForm({ ...form, preco_combo: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Preço Original</label>
                <Input
                  type="number"
                  step="0.01"
                  value={form.preco_original}
                  onChange={(e) => setForm({ ...form, preco_original: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Ordem</label>
                <Input
                  type="number"
                  value={form.ordem_exibicao}
                  onChange={(e) => setForm({ ...form, ordem_exibicao: e.target.value })}
                  className="dark-input"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Data Início</label>
                <Input
                  type="date"
                  value={form.data_inicio}
                  onChange={(e) => setForm({ ...form, data_inicio: e.target.value })}
                  className="dark-input"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Data Fim</label>
                <Input
                  type="date"
                  value={form.data_fim}
                  onChange={(e) => setForm({ ...form, data_fim: e.target.value })}
                  className="dark-input"
                />
              </div>
            </div>

            {/* Itens */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Itens do Combo</label>
                <Button variant="outline" size="sm" onClick={addItem}>
                  <Plus className="mr-1 h-3 w-3" /> Item
                </Button>
              </div>
              {form.itens.map((item, idx) => (
                <div key={idx} className="flex items-end gap-2">
                  <div className="flex-1">
                    <Select
                      value={item.produto_id ? String(item.produto_id) : ""}
                      onValueChange={(v) => updateItem(idx, "produto_id", Number(v))}
                    >
                      <SelectTrigger className="dark-input h-9 text-xs">
                        <SelectValue placeholder="Produto" />
                      </SelectTrigger>
                      <SelectContent>
                        {(produtos || []).map((p: Record<string, unknown>) => (
                          <SelectItem key={p.id as number} value={String(p.id)}>
                            {p.nome as string}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <Input
                    type="number"
                    min="1"
                    value={item.quantidade}
                    onChange={(e) => updateItem(idx, "quantidade", Number(e.target.value))}
                    className="dark-input h-9 w-16 text-xs"
                  />
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="shrink-0 text-red-400"
                    onClick={() => removeItem(idx)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleSave}
              disabled={criarCombo.isPending || atualizarCombo.isPending}
            >
              {editId ? "Salvar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover Combo</AlertDialogTitle>
            <AlertDialogDescription>
              O combo será desativado. Tem certeza?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
