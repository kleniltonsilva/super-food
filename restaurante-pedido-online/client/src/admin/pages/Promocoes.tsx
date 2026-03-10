import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  usePromocoes,
  useCriarPromocao,
  useAtualizarPromocao,
  useDeletarPromocao,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plus, Pencil, Trash2, Percent, Tag, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

interface PromoForm {
  nome: string;
  descricao: string;
  tipo_desconto: string;
  valor_desconto: string;
  desconto_maximo: string;
  valor_pedido_minimo: string;
  codigo_cupom: string;
  data_inicio: string;
  data_fim: string;
  uso_limitado: boolean;
  limite_usos: string;
}

const emptyForm: PromoForm = {
  nome: "", descricao: "", tipo_desconto: "percentual", valor_desconto: "",
  desconto_maximo: "", valor_pedido_minimo: "0", codigo_cupom: "",
  data_inicio: "", data_fim: "", uso_limitado: false, limite_usos: "",
};

export default function Promocoes() {
  const { data: promocoes, isLoading } = usePromocoes();
  const criarPromocao = useCriarPromocao();
  const atualizarPromocao = useAtualizarPromocao();
  const deletarPromocao = useDeletarPromocao();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<PromoForm>(emptyForm);
  const [deleteId, setDeleteId] = useState<number | null>(null);

  function openNew() {
    setEditId(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(p: Record<string, unknown>) {
    setEditId(p.id as number);
    setForm({
      nome: p.nome as string,
      descricao: (p.descricao as string) || "",
      tipo_desconto: p.tipo_desconto as string,
      valor_desconto: String(p.valor_desconto),
      desconto_maximo: p.desconto_maximo ? String(p.desconto_maximo) : "",
      valor_pedido_minimo: String(p.valor_pedido_minimo || 0),
      codigo_cupom: (p.codigo_cupom as string) || "",
      data_inicio: (p.data_inicio as string)?.slice(0, 10) || "",
      data_fim: (p.data_fim as string)?.slice(0, 10) || "",
      uso_limitado: !!p.uso_limitado,
      limite_usos: p.limite_usos ? String(p.limite_usos) : "",
    });
    setShowForm(true);
  }

  function handleSave() {
    if (!form.nome.trim() || !form.valor_desconto) { toast.error("Nome e valor obrigatórios"); return; }

    const payload: Record<string, unknown> = {
      nome: form.nome.trim(),
      descricao: form.descricao.trim() || null,
      tipo_desconto: form.tipo_desconto,
      valor_desconto: Number(form.valor_desconto),
      valor_pedido_minimo: Number(form.valor_pedido_minimo) || 0,
      codigo_cupom: form.codigo_cupom.trim() || null,
      data_inicio: form.data_inicio || null,
      data_fim: form.data_fim || null,
      uso_limitado: form.uso_limitado,
      limite_usos: form.uso_limitado && form.limite_usos ? Number(form.limite_usos) : null,
    };

    if (form.tipo_desconto === "percentual" && form.desconto_maximo) {
      payload.desconto_maximo = Number(form.desconto_maximo);
    } else {
      payload.desconto_maximo = null;
    }

    if (editId) {
      atualizarPromocao.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Promoção atualizada"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      criarPromocao.mutate(payload, {
        onSuccess: () => { toast.success("Promoção criada"); setShowForm(false); },
        onError: () => toast.error("Erro ao criar"),
      });
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarPromocao.mutate(deleteId, {
      onSuccess: () => { toast.success("Promoção removida"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  function formatUsos(p: Record<string, unknown>): string | null {
    const realizados = Number(p.usos_realizados || 0);
    if (p.uso_limitado && p.limite_usos) {
      return `${realizados}/${p.limite_usos} usos`;
    }
    if (realizados > 0) {
      return `${realizados} usos`;
    }
    return null;
  }

  const list: Record<string, unknown>[] = promocoes || [];

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Promoções</h2>
          <Button size="sm" className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={openNew}>
            <Plus className="mr-1 h-4 w-4" /> Nova Promoção
          </Button>
        </div>

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-40" />)}
          </div>
        ) : list.length === 0 ? (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardContent className="flex flex-col items-center gap-2 py-12">
              <Percent className="h-10 w-10 text-[var(--text-muted)]" />
              <p className="text-[var(--text-muted)]">Nenhuma promoção ativa</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {list.map((p) => {
              const usosText = formatUsos(p);
              return (
                <Card key={p.id as number} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg text-[var(--text-primary)]">{p.nome as string}</CardTitle>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className={p.ativo === false ? "text-red-400" : "text-green-400"}
                          onClick={() => {
                            atualizarPromocao.mutate(
                              { id: p.id as number, ativo: p.ativo === false },
                              {
                                onSuccess: () => toast.success(p.ativo === false ? "Promoção ativada" : "Promoção desativada"),
                                onError: () => toast.error("Erro ao atualizar"),
                              }
                            );
                          }}
                        >
                          {p.ativo === false ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                        <Button variant="ghost" size="icon-sm" onClick={() => openEdit(p)}>
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon-sm" className="text-red-400" onClick={() => setDeleteId(p.id as number)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {p.descricao ? <p className="text-sm text-[var(--text-muted)]">{p.descricao as string}</p> : null}
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge className="bg-green-500/20 text-green-400 border border-green-500/30">
                        {p.tipo_desconto === "percentual"
                          ? `${p.valor_desconto}% OFF`
                          : `R$ ${Number(p.valor_desconto).toFixed(2)} OFF`}
                      </Badge>
                      {p.codigo_cupom ? (
                        <Badge variant="outline" className="border-[var(--border-subtle)]">
                          <Tag className="mr-1 h-3 w-3" /> {p.codigo_cupom as string}
                        </Badge>
                      ) : null}
                      {usosText && (
                        <Badge variant="outline" className="border-[var(--border-subtle)] text-[var(--text-muted)]">
                          {usosText}
                        </Badge>
                      )}
                    </div>
                    {Number(p.valor_pedido_minimo) > 0 && (
                      <p className="text-xs text-[var(--text-muted)]">
                        Pedido mínimo: R$ {Number(p.valor_pedido_minimo).toFixed(2)}
                      </p>
                    )}
                    {p.tipo_desconto === "percentual" && Number(p.desconto_maximo) > 0 && (
                      <p className="text-xs text-[var(--text-muted)]">
                        Desconto máx: R$ {Number(p.desconto_maximo).toFixed(2)}
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Promoção" : "Nova Promoção"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Nome</label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="dark-input" />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Descrição</label>
              <Input value={form.descricao} onChange={(e) => setForm({ ...form, descricao: e.target.value })} className="dark-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Tipo</label>
                <Select value={form.tipo_desconto} onValueChange={(v) => setForm({ ...form, tipo_desconto: v })}>
                  <SelectTrigger className="dark-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="percentual">Percentual (%)</SelectItem>
                    <SelectItem value="fixo">Fixo (R$)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Valor Desconto</label>
                <Input type="number" step="0.01" value={form.valor_desconto} onChange={(e) => setForm({ ...form, valor_desconto: e.target.value })} className="dark-input" />
              </div>
            </div>

            {form.tipo_desconto === "percentual" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Desconto Máximo (R$)</label>
                <Input type="number" step="0.01" value={form.desconto_maximo} onChange={(e) => setForm({ ...form, desconto_maximo: e.target.value })} className="dark-input" placeholder="Sem limite" />
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Pedido Mínimo</label>
                <Input type="number" step="0.01" value={form.valor_pedido_minimo} onChange={(e) => setForm({ ...form, valor_pedido_minimo: e.target.value })} className="dark-input" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Código Cupom</label>
                <Input value={form.codigo_cupom} onChange={(e) => setForm({ ...form, codigo_cupom: e.target.value.toUpperCase() })} className="dark-input" placeholder="Ex: PROMO10" />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Início</label>
                <Input type="date" value={form.data_inicio} onChange={(e) => setForm({ ...form, data_inicio: e.target.value })} className="dark-input" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Fim</label>
                <Input type="date" value={form.data_fim} onChange={(e) => setForm({ ...form, data_fim: e.target.value })} className="dark-input" />
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-sm text-[var(--text-secondary)]">Uso Limitado</label>
                <Switch checked={form.uso_limitado} onCheckedChange={(v) => setForm({ ...form, uso_limitado: v })} />
              </div>
              {form.uso_limitado && (
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Limite de Usos</label>
                  <Input type="number" min="1" value={form.limite_usos} onChange={(e) => setForm({ ...form, limite_usos: e.target.value })} className="dark-input" placeholder="Ex: 100" />
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={handleSave} disabled={criarPromocao.isPending || atualizarPromocao.isPending}>
              {editId ? "Salvar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover Promoção</AlertDialogTitle>
            <AlertDialogDescription>A promoção será desativada.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">Remover</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
