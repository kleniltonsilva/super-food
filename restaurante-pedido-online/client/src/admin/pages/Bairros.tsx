import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useBairros,
  useCriarBairro,
  useAtualizarBairro,
  useDeletarBairro,
} from "@/admin/hooks/useAdminQueries";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Plus, Pencil, Trash2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

interface BairroForm {
  nome: string;
  taxa_entrega: string;
  tempo_estimado_min: string;
}

export default function Bairros() {
  const { data: bairros, isLoading } = useBairros();
  const criarBairro = useCriarBairro();
  const atualizarBairro = useAtualizarBairro();
  const deletarBairro = useDeletarBairro();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<BairroForm>({ nome: "", taxa_entrega: "0", tempo_estimado_min: "30" });
  const [deleteId, setDeleteId] = useState<number | null>(null);

  function openNew() {
    setEditId(null);
    setForm({ nome: "", taxa_entrega: "0", tempo_estimado_min: "30" });
    setShowForm(true);
  }

  function openEdit(b: Record<string, unknown>) {
    setEditId(b.id as number);
    setForm({
      nome: b.nome as string,
      taxa_entrega: String(b.taxa_entrega),
      tempo_estimado_min: String(b.tempo_estimado_min ?? 30),
    });
    setShowForm(true);
  }

  function handleSave() {
    if (!form.nome.trim()) { toast.error("Informe o nome"); return; }
    const payload = {
      nome: form.nome.trim(),
      taxa_entrega: Number(form.taxa_entrega) || 0,
      tempo_estimado_min: Number(form.tempo_estimado_min) || 30,
    };

    if (editId) {
      atualizarBairro.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Bairro atualizado"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      criarBairro.mutate(payload, {
        onSuccess: () => { toast.success("Bairro criado"); setShowForm(false); },
        onError: () => toast.error("Erro ao criar"),
      });
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarBairro.mutate(deleteId, {
      onSuccess: () => { toast.success("Bairro removido"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  const list: Record<string, unknown>[] = bairros || [];

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Bairros de Entrega</h2>
          <Button size="sm" className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={openNew}>
            <Plus className="mr-1 h-4 w-4" /> Novo Bairro
          </Button>
        </div>

        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[var(--border-subtle)]">
                  <TableHead className="text-[var(--text-muted)]">Bairro</TableHead>
                  <TableHead className="text-[var(--text-muted)]">Taxa Entrega</TableHead>
                  <TableHead className="text-[var(--text-muted)]">Tempo</TableHead>
                  <TableHead className="text-[var(--text-muted)] text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 3 }).map((_, i) => (
                    <TableRow key={i} className="border-[var(--border-subtle)]">
                      <TableCell><Skeleton className="h-5 w-32" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-20" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                      <TableCell><Skeleton className="h-5 w-16" /></TableCell>
                    </TableRow>
                  ))
                ) : list.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="py-12 text-center text-[var(--text-muted)]">
                      Nenhum bairro cadastrado
                    </TableCell>
                  </TableRow>
                ) : (
                  list.map((b) => (
                    <TableRow key={b.id as number} className="border-[var(--border-subtle)]">
                      <TableCell className="font-medium text-[var(--text-primary)]">{b.nome as string}</TableCell>
                      <TableCell className="text-[var(--text-secondary)]">
                        R$ {Number(b.taxa_entrega || 0).toFixed(2)}
                      </TableCell>
                      <TableCell className="text-[var(--text-secondary)]">
                        {Number(b.tempo_estimado_min ?? 30)} min
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className={b.ativo === false ? "text-red-400" : "text-green-400"}
                            onClick={() => {
                              atualizarBairro.mutate(
                                { id: b.id as number, ativo: b.ativo === false },
                                {
                                  onSuccess: () => toast.success(b.ativo === false ? "Bairro ativado" : "Bairro desativado"),
                                  onError: () => toast.error("Erro ao atualizar"),
                                }
                              );
                            }}
                          >
                            {b.ativo === false ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                          </Button>
                          <Button variant="ghost" size="icon-sm" onClick={() => openEdit(b)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon-sm" className="text-red-400" onClick={() => setDeleteId(b.id as number)}>
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
      </div>

      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Bairro" : "Novo Bairro"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Nome</label>
              <Input value={form.nome} onChange={(e) => setForm({ ...form, nome: e.target.value })} className="dark-input" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Taxa de Entrega (R$)</label>
                <Input type="number" step="0.01" value={form.taxa_entrega} onChange={(e) => setForm({ ...form, taxa_entrega: e.target.value })} className="dark-input" />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Tempo estimado (min)</label>
                <Input type="number" min="1" value={form.tempo_estimado_min} onChange={(e) => setForm({ ...form, tempo_estimado_min: e.target.value })} className="dark-input" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90" onClick={handleSave} disabled={criarBairro.isPending || atualizarBairro.isPending}>
              {editId ? "Salvar" : "Criar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover Bairro</AlertDialogTitle>
            <AlertDialogDescription>O bairro será desativado.</AlertDialogDescription>
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
