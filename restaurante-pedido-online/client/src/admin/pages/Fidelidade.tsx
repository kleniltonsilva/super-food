import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  usePremios,
  useCriarPremio,
  useAtualizarPremio,
  useDeletarPremio,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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
import { Plus, Pencil, Trash2, Star, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

interface PremioForm {
  nome: string;
  descricao: string;
  custo_pontos: string;
  tipo_premio: string;
  valor_premio: string;
  ordem_exibicao: string;
}

const emptyForm: PremioForm = { nome: "", descricao: "", custo_pontos: "", tipo_premio: "desconto", valor_premio: "", ordem_exibicao: "0" };

export default function Fidelidade() {
  const { data: premios, isLoading } = usePremios();
  const criarPremio = useCriarPremio();
  const atualizarPremio = useAtualizarPremio();
  const deletarPremio = useDeletarPremio();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<PremioForm>(emptyForm);
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
      custo_pontos: String(p.custo_pontos),
      tipo_premio: p.tipo_premio as string,
      valor_premio: (p.valor_premio as string) || "",
      ordem_exibicao: String(p.ordem_exibicao ?? 0),
    });
    setShowForm(true);
  }

  function handleSave() {
    if (!form.nome.trim() || !form.custo_pontos) { toast.error("Nome e pontos obrigatórios"); return; }

    const payload: Record<string, unknown> = {
      nome: form.nome.trim(),
      descricao: form.descricao.trim() || null,
      custo_pontos: Number(form.custo_pontos),
      tipo_premio: form.tipo_premio,
      valor_premio: form.valor_premio.trim() || null,
      ordem_exibicao: Number(form.ordem_exibicao) || 0,
    };

    if (editId) {
      atualizarPremio.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Prêmio atualizado"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      criarPremio.mutate(payload, {
        onSuccess: () => { toast.success("Prêmio criado"); setShowForm(false); },
        onError: () => toast.error("Erro ao criar"),
      });
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarPremio.mutate(deleteId, {
      onSuccess: () => { toast.success("Prêmio removido"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  const TIPO_MAP: Record<string, string> = { desconto: "Desconto", item_gratis: "Item Grátis", brinde: "Brinde" };
  const list: Record<string, unknown>[] = premios || [];

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Programa de Fidelidade</h2>
          <Button size="sm" className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={openNew}>
            <Plus className="mr-1 h-4 w-4" /> Novo Prêmio
          </Button>
        </div>

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-36" />)}
          </div>
        ) : list.length === 0 ? (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardContent className="flex flex-col items-center gap-2 py-12">
              <Star className="h-10 w-10 text-[var(--text-muted)]" />
              <p className="text-[var(--text-muted)]">Nenhum prêmio cadastrado</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {list.map((p) => (
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
                          atualizarPremio.mutate(
                            { id: p.id as number, ativo: p.ativo === false },
                            {
                              onSuccess: () => toast.success(p.ativo === false ? "Prêmio ativado" : "Prêmio desativado"),
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
                  <div className="flex items-center gap-2">
                    <Badge className="bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">
                      <Star className="mr-1 h-3 w-3" /> {String(p.custo_pontos)} pontos
                    </Badge>
                    <Badge variant="outline" className="border-[var(--border-subtle)]">
                      {TIPO_MAP[p.tipo_premio as string] || String(p.tipo_premio)}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Prêmio" : "Novo Prêmio"}</DialogTitle>
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
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Custo (pontos)</label>
                <Input type="number" value={form.custo_pontos} onChange={(e) => setForm({ ...form, custo_pontos: e.target.value })} className="dark-input" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Tipo</label>
                <Select value={form.tipo_premio} onValueChange={(v) => setForm({ ...form, tipo_premio: v })}>
                  <SelectTrigger className="dark-input"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="desconto">Desconto</SelectItem>
                    <SelectItem value="item_gratis">Item Grátis</SelectItem>
                    <SelectItem value="brinde">Brinde</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Ordem</label>
                <Input type="number" value={form.ordem_exibicao} onChange={(e) => setForm({ ...form, ordem_exibicao: e.target.value })} className="dark-input" />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Valor do Prêmio</label>
              <Input value={form.valor_premio} onChange={(e) => setForm({ ...form, valor_premio: e.target.value })} className="dark-input" placeholder="Ex: R$ 10.00 ou Nome do item" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={handleSave} disabled={criarPremio.isPending || atualizarPremio.isPending}>
              {editId ? "Salvar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover Prêmio</AlertDialogTitle>
            <AlertDialogDescription>O prêmio será desativado.</AlertDialogDescription>
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
