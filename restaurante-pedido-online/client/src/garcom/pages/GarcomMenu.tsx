import { useState, useMemo } from "react";
import { useLocation, useParams } from "wouter";
import { useCardapio, useCriarPedido, useItensEsgotados } from "@/garcom/hooks/useGarcomQueries";
import { sndClick } from "@/garcom/hooks/useGarcomWebSocket";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Input } from "@/components/ui/input";
import {
  ArrowLeft, Minus, Plus, Send, ShoppingBag, Search, X, AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

interface CartItem {
  item_cardapio_id: number;
  nome: string;
  preco: number;
  qty: number;
  obs: string;
  course: string;
}

const COURSES = [
  { value: "", label: "Sem etapa" },
  { value: "couvert", label: "Couvert", color: "bg-stone-500" },
  { value: "bebida", label: "Bebida", color: "bg-indigo-500" },
  { value: "entrada", label: "Entrada", color: "bg-sky-500" },
  { value: "principal", label: "Principal", color: "bg-amber-500" },
  { value: "sobremesa", label: "Sobremesa", color: "bg-pink-500" },
];

export default function GarcomMenu() {
  const params = useParams<{ sessaoId: string }>();
  const sessaoId = parseInt(params.sessaoId || "0");
  const [, navigate] = useLocation();
  const { data: categorias, isLoading } = useCardapio();
  const { data: esgotados } = useItensEsgotados();
  const criarPedido = useCriarPedido();

  const [cart, setCart] = useState<CartItem[]>([]);
  const [catIdx, setCatIdx] = useState(0);
  const [search, setSearch] = useState("");
  const [showCart, setShowCart] = useState(false);
  const [obsItem, setObsItem] = useState<number | null>(null);
  const [obsText, setObsText] = useState("");
  const [selectedCourse, setSelectedCourse] = useState("");

  const esgotadosIds = useMemo(() => new Set((esgotados || []).map((e: any) => e.item_cardapio_id)), [esgotados]);

  const cats = categorias || [];
  const currentCat = cats[catIdx];

  // Filtered products
  const filteredProducts = useMemo(() => {
    if (search.trim()) {
      const q = search.toLowerCase();
      return cats.flatMap((cat: any) =>
        (cat.produtos || []).filter((p: any) => p.nome.toLowerCase().includes(q))
      );
    }
    return currentCat?.produtos || [];
  }, [search, cats, currentCat]);

  function addToCart(product: any) {
    if (esgotadosIds.has(product.id)) return;
    sndClick();
    setCart((prev) => {
      const existing = prev.find((i) => i.item_cardapio_id === product.id && i.course === selectedCourse);
      if (existing) {
        return prev.map((i) =>
          i.item_cardapio_id === product.id && i.course === selectedCourse
            ? { ...i, qty: i.qty + 1 }
            : i
        );
      }
      return [...prev, {
        item_cardapio_id: product.id,
        nome: product.nome,
        preco: product.preco,
        qty: 1,
        obs: "",
        course: selectedCourse,
      }];
    });
  }

  function updateQty(id: number, course: string, delta: number) {
    setCart((prev) =>
      prev
        .map((i) => i.item_cardapio_id === id && i.course === course ? { ...i, qty: Math.max(0, i.qty + delta) } : i)
        .filter((i) => i.qty > 0)
    );
  }

  function setItemObs(id: number, course: string) {
    const item = cart.find((i) => i.item_cardapio_id === id && i.course === course);
    setObsItem(id);
    setObsText(item?.obs || "");
  }

  function saveObs() {
    if (obsItem === null) return;
    setCart((prev) =>
      prev.map((i) => i.item_cardapio_id === obsItem ? { ...i, obs: obsText } : i)
    );
    setObsItem(null);
    setObsText("");
  }

  const cartTotal = cart.reduce((sum, i) => sum + i.preco * i.qty, 0);
  const cartCount = cart.reduce((sum, i) => sum + i.qty, 0);

  async function handleEnviar() {
    if (cart.length === 0) return;
    sndClick();
    try {
      await criarPedido.mutateAsync({
        sessaoId,
        itens: cart.map((i) => ({
          item_cardapio_id: i.item_cardapio_id,
          qty: i.qty,
          obs: i.obs || undefined,
          course: i.course || undefined,
        })),
      });
      toast.success("Pedido enviado para a cozinha!");
      navigate(`/mesa/${sessaoId}`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao enviar pedido");
    }
  }

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0806]">
        <Spinner className="h-8 w-8 text-amber-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0a0806] text-white pb-24">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-white/5 bg-[#0a0806]/95 backdrop-blur">
        <div className="flex items-center gap-3 px-4 py-3">
          <Button variant="ghost" size="icon-sm" onClick={() => navigate(`/mesa/${sessaoId}`)} className="text-gray-400">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-lg font-semibold flex-1" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Cardapio
          </h1>
          <button
            onClick={() => setShowCart(true)}
            className="relative p-2 rounded-lg bg-amber-500/10 text-amber-500"
          >
            <ShoppingBag className="h-5 w-5" />
            {cartCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-amber-500 text-[10px] font-bold text-gray-950">
                {cartCount}
              </span>
            )}
          </button>
        </div>

        {/* Search */}
        <div className="px-4 pb-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar produto..."
              className="pl-9 bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500 h-9"
            />
            {search && (
              <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Course selector */}
        <div className="flex gap-1.5 px-4 pb-3 overflow-x-auto">
          {COURSES.map((c) => (
            <button
              key={c.value}
              onClick={() => setSelectedCourse(c.value)}
              className={`shrink-0 px-3 py-1 rounded-full text-xs font-medium transition-all ${
                selectedCourse === c.value
                  ? `${c.color || "bg-gray-500"} text-white`
                  : "bg-white/[0.03] text-gray-400 border border-white/10"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        {/* Categories tabs */}
        {!search && (
          <div className="flex gap-1 px-4 pb-2 overflow-x-auto">
            {cats.map((cat: any, idx: number) => (
              <button
                key={cat.id}
                onClick={() => setCatIdx(idx)}
                className={`shrink-0 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  catIdx === idx
                    ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    : "text-gray-500 hover:text-gray-300"
                }`}
              >
                {cat.icone && <span className="mr-1">{cat.icone}</span>}
                {cat.nome}
              </button>
            ))}
          </div>
        )}
      </header>

      {/* Products */}
      <div className="p-4 space-y-2">
        {filteredProducts.map((product: any) => {
          const inCart = cart.find((i) => i.item_cardapio_id === product.id && i.course === selectedCourse);
          const isEsgotado = esgotadosIds.has(product.id);

          return (
            <div
              key={`${product.id}-${selectedCourse}`}
              className={`flex items-center gap-3 rounded-xl border p-3 transition-all ${
                isEsgotado
                  ? "border-red-500/20 bg-red-500/5 opacity-50"
                  : "border-white/5 bg-white/[0.02] active:bg-white/[0.05]"
              }`}
              onClick={() => !isEsgotado && addToCart(product)}
            >
              {/* Image */}
              {product.imagem_url ? (
                <img src={product.imagem_url} alt="" className="h-14 w-14 rounded-lg object-cover shrink-0" />
              ) : (
                <div className="h-14 w-14 rounded-lg bg-white/[0.03] shrink-0" />
              )}

              {/* Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{product.nome}</p>
                {product.descricao && (
                  <p className="text-[10px] text-gray-500 truncate">{product.descricao}</p>
                )}
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-sm font-mono text-amber-400">
                    R$ {product.preco?.toFixed(2)}
                  </span>
                  {product.preco_original && (
                    <span className="text-[10px] text-gray-500 line-through">
                      R$ {product.preco_original.toFixed(2)}
                    </span>
                  )}
                </div>
              </div>

              {/* Qty controls or esgotado */}
              {isEsgotado ? (
                <span className="text-[10px] px-2 py-1 rounded bg-red-500/20 text-red-400 flex items-center gap-1">
                  <AlertCircle className="h-3 w-3" /> Esgotado
                </span>
              ) : inCart ? (
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <button
                    onClick={() => updateQty(product.id, selectedCourse, -1)}
                    className="h-7 w-7 rounded-full bg-white/5 flex items-center justify-center text-gray-400"
                  >
                    <Minus className="h-3.5 w-3.5" />
                  </button>
                  <span className="font-mono text-sm w-5 text-center">{inCart.qty}</span>
                  <button
                    onClick={() => updateQty(product.id, selectedCourse, 1)}
                    className="h-7 w-7 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-400"
                  >
                    <Plus className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <div className="h-7 w-7 rounded-full bg-amber-500/10 flex items-center justify-center">
                  <Plus className="h-4 w-4 text-amber-500" />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Cart footer */}
      {cartCount > 0 && !showCart && (
        <div className="fixed bottom-0 inset-x-0 p-4 bg-[#0a0806]/95 border-t border-white/5 backdrop-blur">
          <Button
            onClick={handleEnviar}
            disabled={criarPedido.isPending}
            className="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-semibold py-5"
          >
            <Send className="h-4 w-4 mr-2" />
            {criarPedido.isPending ? "Enviando..." : `Enviar ${cartCount} itens — R$ ${cartTotal.toFixed(2)}`}
          </Button>
        </div>
      )}

      {/* Cart drawer */}
      {showCart && (
        <div className="fixed inset-0 z-50 bg-black/60" onClick={() => setShowCart(false)}>
          <div
            className="absolute bottom-0 inset-x-0 max-h-[80vh] bg-[#0a0806] border-t border-white/10 rounded-t-2xl overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-4">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Carrinho ({cartCount})</h2>
                <button onClick={() => setShowCart(false)} className="text-gray-400">
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="space-y-3">
                {cart.map((item) => (
                  <div key={`${item.item_cardapio_id}-${item.course}`} className="flex items-center gap-3 rounded-lg bg-white/[0.02] p-3">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.nome}</p>
                      {item.course && (
                        <span className="text-[10px] text-gray-500 capitalize">{item.course}</span>
                      )}
                      {item.obs && (
                        <p className="text-[10px] text-amber-400 mt-0.5">Obs: {item.obs}</p>
                      )}
                      <button
                        onClick={() => setItemObs(item.item_cardapio_id, item.course)}
                        className="text-[10px] text-gray-500 hover:text-amber-400 mt-0.5"
                      >
                        {item.obs ? "Editar obs" : "+ Obs"}
                      </button>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateQty(item.item_cardapio_id, item.course, -1)}
                        className="h-7 w-7 rounded-full bg-white/5 flex items-center justify-center"
                      >
                        <Minus className="h-3.5 w-3.5 text-gray-400" />
                      </button>
                      <span className="font-mono text-sm w-5 text-center">{item.qty}</span>
                      <button
                        onClick={() => updateQty(item.item_cardapio_id, item.course, 1)}
                        className="h-7 w-7 rounded-full bg-amber-500/20 flex items-center justify-center"
                      >
                        <Plus className="h-3.5 w-3.5 text-amber-400" />
                      </button>
                    </div>
                    <span className="font-mono text-sm text-gray-400 w-20 text-right">
                      R$ {(item.preco * item.qty).toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>

              <div className="mt-4 pt-3 border-t border-white/5 flex justify-between items-center">
                <span className="text-sm text-gray-400">Total</span>
                <span className="text-lg font-bold font-mono text-amber-400">R$ {cartTotal.toFixed(2)}</span>
              </div>

              <Button
                onClick={handleEnviar}
                disabled={criarPedido.isPending}
                className="w-full mt-4 bg-amber-500 hover:bg-amber-600 text-gray-950 font-semibold py-5"
              >
                <Send className="h-4 w-4 mr-2" />
                {criarPedido.isPending ? "Enviando..." : "Enviar para Cozinha"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Obs modal */}
      {obsItem !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onClick={() => setObsItem(null)}>
          <div className="w-full max-w-sm rounded-xl bg-[#0a0806] border border-white/10 p-4" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-semibold mb-3">Observação do item</h3>
            <Input
              value={obsText}
              onChange={(e) => setObsText(e.target.value)}
              placeholder="Ex: sem cebola, bem passado"
              className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500"
              autoFocus
            />
            <div className="flex gap-2 mt-3">
              <Button variant="outline" size="sm" onClick={() => setObsItem(null)} className="flex-1 border-white/10 text-gray-300">
                Cancelar
              </Button>
              <Button size="sm" onClick={saveObs} className="flex-1 bg-amber-500 text-gray-950">
                Salvar
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
