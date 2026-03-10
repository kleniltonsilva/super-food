import { useState } from "react";
import { useLocation } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useProdutos,
  useCategorias,
  useToggleDisponibilidade,
  useDeletarProduto,
  useCarregarProdutosModelo,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent } from "@/components/ui/card";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { Plus, Search, MoreHorizontal, Pencil, Trash2, Upload } from "lucide-react";
import { toast } from "sonner";

export default function Produtos() {
  const [, navigate] = useLocation();
  const { data: categorias } = useCategorias();
  const [catFilter, setCatFilter] = useState<string>("todas");
  const [busca, setBusca] = useState("");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const params: Record<string, unknown> = {};
  if (catFilter !== "todas") params.categoria_id = Number(catFilter);
  if (busca.trim()) params.busca = busca.trim();

  const { data: produtos, isLoading } = useProdutos(params);
  const toggleDisp = useToggleDisponibilidade();
  const deletar = useDeletarProduto();
  const carregarModelo = useCarregarProdutosModelo();

  function handleToggle(id: number, atual: boolean) {
    toggleDisp.mutate(
      { id, disponivel: !atual },
      { onError: () => toast.error("Erro ao alterar disponibilidade") }
    );
  }

  function handleDelete() {
    if (!deleteId) return;
    deletar.mutate(deleteId, {
      onSuccess: () => { toast.success("Produto removido"); setDeleteId(null); },
      onError: () => toast.error("Erro ao remover"),
    });
  }

  function handleCarregarModelo() {
    carregarModelo.mutate(undefined, {
      onSuccess: () => toast.success("Produtos modelo carregados!"),
      onError: () => toast.error("Erro ao carregar produtos modelo"),
    });
  }

  const prods: Record<string, unknown>[] = produtos || [];
  const catMap = new Map((categorias || []).map((c: Record<string, unknown>) => [c.id, c.nome]));

  return (
    <AdminLayout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Produtos</h2>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="border-[var(--border-subtle)]"
              onClick={handleCarregarModelo}
              disabled={carregarModelo.isPending}
            >
              <Upload className="mr-1 h-4 w-4" /> Carregar Modelo
            </Button>
            <Button
              size="sm"
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={() => navigate("/produtos/novo")}
            >
              <Plus className="mr-1 h-4 w-4" /> Novo Produto
            </Button>
          </div>
        </div>

        {/* Filtros */}
        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
          <CardContent className="flex flex-col gap-3 p-4 sm:flex-row">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
              <Input
                placeholder="Buscar produto..."
                value={busca}
                onChange={(e) => setBusca(e.target.value)}
                className="dark-input pl-9"
              />
            </div>
            <Select value={catFilter} onValueChange={setCatFilter}>
              <SelectTrigger className="w-full sm:w-48 dark-input">
                <SelectValue placeholder="Categoria" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todas">Todas</SelectItem>
                {(categorias || []).map((c: Record<string, unknown>) => (
                  <SelectItem key={c.id as number} value={String(c.id)}>
                    {c.nome as string}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* Tabela */}
        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] overflow-hidden">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-[var(--border-subtle)]">
                  <TableHead className="text-[var(--text-muted)]">Produto</TableHead>
                  <TableHead className="text-[var(--text-muted)]">Categoria</TableHead>
                  <TableHead className="text-[var(--text-muted)]">Preço</TableHead>
                  <TableHead className="text-[var(--text-muted)]">Disponível</TableHead>
                  <TableHead className="text-[var(--text-muted)] text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <TableRow key={i} className="border-[var(--border-subtle)]">
                      {Array.from({ length: 5 }).map((_, j) => (
                        <TableCell key={j}><Skeleton className="h-5 w-20" /></TableCell>
                      ))}
                    </TableRow>
                  ))
                ) : prods.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="py-12 text-center text-[var(--text-muted)]">
                      Nenhum produto encontrado
                    </TableCell>
                  </TableRow>
                ) : (
                  prods.map((p) => (
                    <TableRow key={p.id as number} className="border-[var(--border-subtle)]">
                      <TableCell>
                        <div className="flex items-center gap-3">
                          {p.imagem_url ? (
                            <img
                              src={p.imagem_url as string}
                              alt=""
                              className="h-10 w-10 rounded-lg object-cover"
                            />
                          ) : (
                            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--bg-base)] text-lg">
                              🍽️
                            </div>
                          )}
                          <div>
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              {p.nome as string}
                            </p>
                            {p.destaque ? (
                              <Badge variant="outline" className="text-xs border-yellow-500/30 text-yellow-400">
                                Destaque
                              </Badge>
                            ) : null}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-sm text-[var(--text-secondary)]">
                        {(catMap.get(p.categoria_id) as string) || "—"}
                      </TableCell>
                      <TableCell>
                        <div>
                          {p.promocao && p.preco_promocional ? (
                            <>
                              <p className="text-sm font-medium text-[var(--cor-primaria)]">
                                R$ {Number(p.preco_promocional).toFixed(2)}
                              </p>
                              <p className="text-xs text-[var(--text-muted)] line-through">
                                R$ {Number(p.preco).toFixed(2)}
                              </p>
                            </>
                          ) : (
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              R$ {Number(p.preco).toFixed(2)}
                            </p>
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={!!p.disponivel}
                          onCheckedChange={() => handleToggle(p.id as number, !!p.disponivel)}
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm">
                              <MoreHorizontal className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => navigate(`/produtos/${p.id}`)}>
                              <Pencil className="mr-2 h-4 w-4" /> Editar
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => setDeleteId(p.id as number)}
                              className="text-red-400"
                            >
                              <Trash2 className="mr-2 h-4 w-4" /> Excluir
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </Card>
      </div>

      {/* Delete Dialog */}
      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir Produto</AlertDialogTitle>
            <AlertDialogDescription>
              Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Excluir
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
