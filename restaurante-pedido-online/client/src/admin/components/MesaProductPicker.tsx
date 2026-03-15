import { useState, useMemo } from "react";
import { Plus, Minus, Search, ShoppingCart } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useCategorias, useProdutos, useAdicionarPedidoMesaRapido } from "@/admin/hooks/useAdminQueries";
import { toast } from "sonner";

interface PickerItem {
  produto_id: number;
  nome: string;
  preco: number;
  quantidade: number;
  observacao?: string;
}

interface Produto {
  id: number;
  nome: string;
  preco: number;
  categoria_id: number;
  imagem_url?: string;
  disponivel: boolean;
}

interface Categoria {
  id: number;
  nome: string;
  icone?: string;
}

interface MesaProductPickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  numeroMesa: string;
}

export default function MesaProductPicker({ open, onOpenChange, numeroMesa }: MesaProductPickerProps) {
  const [busca, setBusca] = useState("");
  const [categoriaAtiva, setCategoriaAtiva] = useState<number | null>(null);
  const [itens, setItens] = useState<PickerItem[]>([]);

  const { data: categoriasData } = useCategorias();
  const { data: produtosData } = useProdutos();
  const addPedido = useAdicionarPedidoMesaRapido();

  const categorias = (categoriasData as Categoria[]) || [];
  const todosProdutos = (
    Array.isArray(produtosData) ? produtosData : (produtosData as Record<string, unknown>)?.produtos || []
  ) as Produto[];

  const produtosFiltrados = useMemo(() => {
    let lista = todosProdutos.filter((p) => p.disponivel !== false);
    if (categoriaAtiva) {
      lista = lista.filter((p) => p.categoria_id === categoriaAtiva);
    }
    if (busca.trim()) {
      const term = busca.toLowerCase();
      lista = lista.filter((p) => p.nome.toLowerCase().includes(term));
    }
    return lista;
  }, [todosProdutos, categoriaAtiva, busca]);

  const addItem = (prod: Produto) => {
    setItens((prev) => {
      const idx = prev.findIndex((i) => i.produto_id === prod.id);
      if (idx >= 0) {
        const copy = [...prev];
        copy[idx] = { ...copy[idx], quantidade: copy[idx].quantidade + 1 };
        return copy;
      }
      return [...prev, { produto_id: prod.id, nome: prod.nome, preco: prod.preco, quantidade: 1 }];
    });
  };

  const removeItem = (produtoId: number) => {
    setItens((prev) => {
      const idx = prev.findIndex((i) => i.produto_id === produtoId);
      if (idx < 0) return prev;
      if (prev[idx].quantidade <= 1) return prev.filter((_, i) => i !== idx);
      const copy = [...prev];
      copy[idx] = { ...copy[idx], quantidade: copy[idx].quantidade - 1 };
      return copy;
    });
  };

  const getQtd = (produtoId: number) => {
    return itens.find((i) => i.produto_id === produtoId)?.quantidade || 0;
  };

  const totalItens = itens.reduce((acc, i) => acc + i.quantidade, 0);
  const totalValor = itens.reduce((acc, i) => acc + i.preco * i.quantidade, 0);

  const enviar = () => {
    if (itens.length === 0) return;
    addPedido.mutate(
      {
        numero_mesa: numeroMesa,
        itens: itens.map((i) => ({ produto_id: i.produto_id, quantidade: i.quantidade })),
      },
      {
        onSuccess: () => {
          toast.success(`${totalItens} item(ns) adicionado(s) à Mesa ${numeroMesa}`);
          setItens([]);
          setBusca("");
          onOpenChange(false);
        },
        onError: () => {
          toast.error("Não foi possível adicionar o pedido");
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Adicionar itens — Mesa {numeroMesa}</DialogTitle>
        </DialogHeader>

        {/* Busca */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Buscar produto..."
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Categorias */}
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          <Button
            size="sm"
            variant={categoriaAtiva === null ? "default" : "outline"}
            onClick={() => setCategoriaAtiva(null)}
            className="shrink-0 text-xs"
          >
            Todos
          </Button>
          {categorias.map((cat) => (
            <Button
              key={cat.id}
              size="sm"
              variant={categoriaAtiva === cat.id ? "default" : "outline"}
              onClick={() => setCategoriaAtiva(cat.id)}
              className="shrink-0 text-xs"
            >
              {cat.icone && <span className="mr-1">{cat.icone}</span>}
              {cat.nome}
            </Button>
          ))}
        </div>

        {/* Lista de produtos */}
        <ScrollArea className="flex-1 min-h-0 max-h-[40vh]">
          <div className="space-y-1">
            {produtosFiltrados.map((prod) => {
              const qtd = getQtd(prod.id);
              return (
                <div
                  key={prod.id}
                  className="flex items-center justify-between rounded-lg border p-2.5 hover:bg-accent/50"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{prod.nome}</p>
                    <p className="text-xs text-muted-foreground">
                      R$ {prod.preco.toFixed(2)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1.5 ml-2">
                    {qtd > 0 && (
                      <>
                        <Button
                          size="icon"
                          variant="outline"
                          className="h-7 w-7"
                          onClick={() => removeItem(prod.id)}
                        >
                          <Minus className="h-3 w-3" />
                        </Button>
                        <span className="text-sm font-bold w-6 text-center">{qtd}</span>
                      </>
                    )}
                    <Button
                      size="icon"
                      variant="outline"
                      className="h-7 w-7"
                      onClick={() => addItem(prod)}
                    >
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                </div>
              );
            })}
            {produtosFiltrados.length === 0 && (
              <div className="text-center py-8 text-sm text-muted-foreground">
                Nenhum produto encontrado
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Footer com total */}
        <DialogFooter className="flex-row items-center justify-between gap-2 border-t pt-3">
          <div className="flex items-center gap-2 text-sm">
            <ShoppingCart className="h-4 w-4" />
            <span>{totalItens} item(ns)</span>
            <Badge variant="secondary" className="font-mono">
              R$ {totalValor.toFixed(2)}
            </Badge>
          </div>
          <Button
            onClick={enviar}
            disabled={itens.length === 0 || addPedido.isPending}
            className="bg-green-600 hover:bg-green-700"
          >
            {addPedido.isPending ? "Enviando..." : "Adicionar à Mesa"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
