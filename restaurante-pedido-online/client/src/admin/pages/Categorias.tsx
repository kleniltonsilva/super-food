import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useCategorias,
  useCriarCategoria,
  useAtualizarCategoria,
  useDeletarCategoria,
  useReordenarCategorias,
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
import { Plus, GripVertical, Pencil, Trash2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Categoria {
  id: number;
  nome: string;
  descricao?: string;
  icone?: string;
  ordem_exibicao: number;
  ativo?: boolean;
  setor_impressao?: string;
}

export default function Categorias() {
  const { data: categorias, isLoading } = useCategorias();
  const criarCategoria = useCriarCategoria();
  const atualizarCategoria = useAtualizarCategoria();
  const deletarCategoria = useDeletarCategoria();
  const reordenar = useReordenarCategorias();

  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [nome, setNome] = useState("");
  const [icone, setIcone] = useState("");
  const [descricao, setDescricao] = useState("");
  const [setorImpressao, setSetorImpressao] = useState("geral");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // Drag state
  const [dragIdx, setDragIdx] = useState<number | null>(null);

  const cats: Categoria[] = categorias || [];

  function openNew() {
    setEditId(null);
    setNome("");
    setIcone("");
    setDescricao("");
    setSetorImpressao("geral");
    setShowForm(true);
  }

  function openEdit(cat: Categoria) {
    setEditId(cat.id);
    setNome(cat.nome);
    setIcone(cat.icone || "");
    setDescricao(cat.descricao || "");
    setSetorImpressao(cat.setor_impressao || "geral");
    setShowForm(true);
  }

  function handleSave() {
    if (!nome.trim()) { toast.error("Informe o nome"); return; }

    const payload: Record<string, unknown> = {
      nome: nome.trim(),
      icone: icone.trim() || null,
      descricao: descricao.trim() || null,
      setor_impressao: setorImpressao,
    };

    if (editId) {
      atualizarCategoria.mutate(
        { id: editId, ...payload },
        {
          onSuccess: () => { toast.success("Categoria atualizada"); setShowForm(false); },
          onError: () => toast.error("Erro ao atualizar"),
        }
      );
    } else {
      criarCategoria.mutate(
        { ...payload, ordem: cats.length } as { nome: string; ordem?: number },
        {
          onSuccess: () => { toast.success("Categoria criada"); setShowForm(false); },
          onError: () => toast.error("Erro ao criar"),
        }
      );
    }
  }

  function handleDelete() {
    if (!deleteId) return;
    deletarCategoria.mutate(deleteId, {
      onSuccess: () => { toast.success("Categoria removida"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  function handleDragStart(idx: number) {
    setDragIdx(idx);
  }

  function handleDragOver(e: React.DragEvent, idx: number) {
    e.preventDefault();
    if (dragIdx === null || dragIdx === idx) return;
    const newCats = [...cats];
    const [moved] = newCats.splice(dragIdx, 1);
    newCats.splice(idx, 0, moved);
    // Reorder via API
    reordenar.mutate(newCats.map((c) => c.id));
    setDragIdx(idx);
  }

  function handleDragEnd() {
    setDragIdx(null);
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Categorias</h2>
          <Button
            size="sm"
            className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
            onClick={openNew}
          >
            <Plus className="mr-1 h-4 w-4" /> Nova Categoria
          </Button>
        </div>

        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
          <CardHeader>
            <CardTitle className="text-sm text-[var(--text-muted)]">
              Arraste para reordenar
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full" />
                ))}
              </div>
            ) : cats.length === 0 ? (
              <p className="py-8 text-center text-sm text-[var(--text-muted)]">
                Nenhuma categoria cadastrada
              </p>
            ) : (
              <div className="space-y-2">
                {cats.map((cat, idx) => (
                  <div
                    key={cat.id}
                    draggable
                    onDragStart={() => handleDragStart(idx)}
                    onDragOver={(e) => handleDragOver(e, idx)}
                    onDragEnd={handleDragEnd}
                    className={`flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3 transition-colors ${
                      dragIdx === idx ? "opacity-50" : ""
                    }`}
                  >
                    <GripVertical className="h-5 w-5 shrink-0 cursor-grab text-[var(--text-muted)]" />
                    {cat.icone && (
                      <span className="text-xl shrink-0">{cat.icone}</span>
                    )}
                    <div className="flex-1">
                      <p className="font-medium text-[var(--text-primary)]">{cat.nome}</p>
                      {cat.descricao && (
                        <p className="text-xs text-[var(--text-muted)]">{cat.descricao}</p>
                      )}
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className={cat.ativo === false ? "text-red-400" : "text-green-400"}
                        onClick={() => {
                          atualizarCategoria.mutate(
                            { id: cat.id, ativo: cat.ativo === false },
                            {
                              onSuccess: () => toast.success(cat.ativo === false ? "Categoria ativada" : "Categoria desativada"),
                              onError: () => toast.error("Erro ao atualizar"),
                            }
                          );
                        }}
                      >
                        {cat.ativo === false ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => openEdit(cat)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        className="text-red-400"
                        onClick={() => setDeleteId(cat.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Form Dialog */}
      <Dialog open={showForm} onOpenChange={setShowForm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editId ? "Editar Categoria" : "Nova Categoria"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-[1fr_80px] gap-3">
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Nome</label>
                <Input
                  value={nome}
                  onChange={(e) => setNome(e.target.value)}
                  className="dark-input"
                  placeholder="Ex: Pizzas, Bebidas..."
                  onKeyDown={(e) => e.key === "Enter" && handleSave()}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-[var(--text-secondary)]">Ícone</label>
                <Input
                  value={icone}
                  onChange={(e) => setIcone(e.target.value)}
                  className="dark-input text-center text-lg"
                  placeholder="🍕"
                  maxLength={4}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Descrição</label>
              <Textarea
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                className="dark-input"
                placeholder="Descrição da categoria (opcional)"
                rows={2}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-[var(--text-secondary)]">Setor de Impressão</label>
              <Select value={setorImpressao} onValueChange={setSetorImpressao}>
                <SelectTrigger className="dark-input">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="geral">Geral (padrão)</SelectItem>
                  <SelectItem value="cozinha">Cozinha</SelectItem>
                  <SelectItem value="bar">Bar / Bebidas</SelectItem>
                  <SelectItem value="caixa">Caixa</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowForm(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleSave}
              disabled={criarCategoria.isPending || atualizarCategoria.isPending}
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
            <AlertDialogTitle>Remover Categoria</AlertDialogTitle>
            <AlertDialogDescription>
              A categoria será desativada. Os produtos vinculados não serão excluídos.
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
