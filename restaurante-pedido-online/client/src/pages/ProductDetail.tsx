import { useParams, useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Plus, Minus, X, Trash2, Search, ShoppingCart, Star, MessageSquare, RotateCcw } from "lucide-react";
import { useState, useEffect, useMemo, useRef } from "react";
import { getProdutoDetalhe, adicionarAoCarrinho, getSaboresDisponiveis, getProdutos } from "@/lib/apiClient";
import { useRestaurante, useRestauranteTheme, type SiteInfo } from "@/contexts/RestauranteContext";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/hooks/useQueries";
import { toast } from "sonner";

function getEmojiByTipo(siteInfo: SiteInfo | null): string {
  const tipo = (siteInfo?.tipo_restaurante || "").toLowerCase();
  if (tipo.includes("pizza")) return "🍕";
  if (tipo.includes("hambur") || tipo.includes("lanch")) return "🍔";
  if (tipo.includes("sushi") || tipo.includes("japon")) return "🍣";
  if (tipo.includes("acai") || tipo.includes("sorvet")) return "🍨";
  if (tipo.includes("churrasco")) return "🥩";
  if (tipo.includes("doce") || tipo.includes("bolo")) return "🎂";
  if (tipo.includes("esfih")) return "🥙";
  return "🍽️";
}

interface Variacao {
  id: number;
  nome: string;
  descricao: string | null;
  preco_adicional: number;
  estoque_disponivel: boolean;
  max_sabores?: number;
}

interface ProdutoDetalhado {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  preco_promocional: number | null;
  imagem_url: string | null;
  imagens_adicionais: string[];
  destaque: boolean;
  promocao: boolean;
  categoria_id: number;
  eh_pizza?: boolean;
  variacoes_agrupadas: Record<string, Variacao[]>;
}

interface Sabor {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  imagem_url: string | null;
}

interface Bebida {
  id: number;
  nome: string;
  preco: number;
  imagem_url: string | null;
}

// ============================================================
// PIZZA VISUAL — helpers
// ============================================================

function getPizzaScaleDynamic(selectedIdx: number, totalTamanhos: number): number {
  if (totalTamanhos <= 1) return 0.80;
  const minScale = 0.55;
  const maxScale = 0.95;
  return minScale + (selectedIdx / (totalTamanhos - 1)) * (maxScale - minScale);
}

// Posição de cada fatia — estilo Expresso Delivery (position:absolute + overflow:hidden)
function getSliceStyle(idx: number, total: number): React.CSSProperties {
  if (total === 1) return { top: 0, left: 0, width: "100%", height: "100%" };
  if (total === 2) {
    return idx === 0
      ? { top: 0, left: 0, width: "50%", height: "100%" }
      : { top: 0, right: 0, width: "50%", height: "100%" };
  }
  if (total === 3) {
    if (idx === 0) return { bottom: 0, left: 0, width: "50%", height: "100%" };
    if (idx === 1) return { bottom: 0, right: 0, width: "50%", height: "100%" };
    return {
      top: "-10.8%", right: "24.5%", width: "51%", height: "51%",
      transform: "rotate(45deg)", borderTopLeftRadius: "100%", zIndex: 2,
      overflow: "hidden",
    };
  }
  if (idx === 0) return { top: 0, left: 0, width: "50%", height: "50%" };
  if (idx === 1) return { top: 0, right: 0, width: "50%", height: "50%" };
  if (idx === 2) return { bottom: 0, left: 0, width: "50%", height: "50%" };
  return { bottom: 0, right: 0, width: "50%", height: "50%" };
}

function getSliceBgPos(idx: number, total: number): string {
  if (total === 1) return "center center";
  if (total === 2) return idx === 0 ? "left center" : "right center";
  if (total === 3) {
    if (idx === 0) return "left center";
    if (idx === 1) return "right center";
    return "center center";
  }
  if (idx === 0) return "left top";
  if (idx === 1) return "right top";
  if (idx === 2) return "left bottom";
  return "right bottom";
}

function getSliceImgStyle(idx: number, total: number): React.CSSProperties {
  if (total === 3 && idx === 2) {
    return {
      position: "absolute", inset: 0, width: "140%", height: "140%",
      objectFit: "cover", transform: "rotate(-45deg)",
      transformOrigin: "bottom right",
    };
  }
  return {
    position: "absolute", inset: 0, width: "100%", height: "100%",
    objectFit: "cover", objectPosition: getSliceBgPos(idx, total),
  };
}

// ============================================================
// Componente Principal
// ============================================================

export default function ProductDetail() {
  const params = useParams();
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const theme = useRestauranteTheme();
  const qc = useQueryClient();
  const productId = parseInt(params?.id || "0");

  const [produto, setProduto] = useState<ProdutoDetalhado | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const [quantity, setQuantity] = useState(1);
  const [selectedTamanho, setSelectedTamanho] = useState<number | null>(null);
  const [selectedBorda, setSelectedBorda] = useState<number | null>(null);
  const [selectedAdicionais, setSelectedAdicionais] = useState<number[]>([]);
  const [adicionaisQtd, setAdicionaisQtd] = useState<Map<number, number>>(new Map());
  const [selectedPontoCarne, setSelectedPontoCarne] = useState<number | null>(null);
  const [selectedSabores, setSelectedSabores] = useState<(number | null)[]>([]);
  const [observacoes, setObservacoes] = useState("");

  // Pizza montador
  const [useStepper, setUseStepper] = useState(false);
  const [maxSabores, setMaxSabores] = useState(1);
  const [numFlavors, setNumFlavors] = useState(1);
  const [activeSlice, setActiveSlice] = useState(0);
  const [searchSabor, setSearchSabor] = useState("");

  // Modais do montador (estilo Expresso Delivery)
  const [showFlavorModal, setShowFlavorModal] = useState(false);
  const [showBordaModal, setShowBordaModal] = useState(false);
  const [showObsModal, setShowObsModal] = useState(false);
  const [showTamanhoDropdown, setShowTamanhoDropdown] = useState(false);

  // Sabores e bebidas
  const [saboresDisp, setSaboresDisp] = useState<Sabor[]>([]);
  const [bebidas, setBebidas] = useState<Bebida[]>([]);
  const [showBebidaModal, setShowBebidaModal] = useState(false);

  const saborListRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getProdutoDetalhe(productId);
        setProduto(data);

        const tamanhos = data.variacoes_agrupadas?.tamanho || [];
        if (tamanhos.length > 0) {
          setSelectedTamanho(tamanhos[0].id);
          const hasMultiSabor = data.eh_pizza && tamanhos.some((t: Variacao) => (t.max_sabores || 1) > 1);
          if (hasMultiSabor) {
            setUseStepper(true);
            const initialMax = tamanhos[0].max_sabores || 1;
            setMaxSabores(initialMax);
            setNumFlavors(1);
            const sabData = await getSaboresDisponiveis(productId);
            setSaboresDisp(sabData.sabores || []);
            setSelectedSabores([productId]);
          }
        }

        const bordas = data.variacoes_agrupadas?.borda || [];
        if (bordas.length > 0) {
          setSelectedBorda(bordas[0].id);
        }
      } catch {
        setProduto(null);
      } finally {
        setLoading(false);
      }
    }
    if (productId) load();
  }, [productId]);

  useEffect(() => {
    async function loadBebidas() {
      try {
        const allProds = await getProdutos();
        const bebidasList = allProds.filter((p: any) => {
          const nome = p.nome?.toLowerCase() || "";
          return nome.includes("refriger") || nome.includes("suco") || nome.includes("água") || nome.includes("agua") || nome.includes("coca") || nome.includes("guaraná") || nome.includes("cerveja");
        });
        setBebidas(bebidasList.slice(0, 6));
      } catch {
        setBebidas([]);
      }
    }
    loadBebidas();
  }, []);

  // Sync max_sabores quando troca tamanho
  useEffect(() => {
    if (!produto || !useStepper) return;
    const tamanhos = produto.variacoes_agrupadas?.tamanho || [];
    const tam = tamanhos.find(t => t.id === selectedTamanho);
    if (tam) {
      const newMax = tam.max_sabores || 1;
      setMaxSabores(newMax);
      if (numFlavors > newMax) {
        setNumFlavors(newMax);
        setSelectedSabores(prev => prev.slice(0, newMax));
      }
    }
  }, [selectedTamanho, produto, useStepper]);

  // Sync sabores array quando numFlavors muda
  useEffect(() => {
    setSelectedSabores(prev => {
      if (prev.length > numFlavors) return prev.slice(0, numFlavors);
      const arr = [...prev];
      while (arr.length < numFlavors) arr.push(null);
      return arr;
    });
    if (activeSlice >= numFlavors) setActiveSlice(Math.max(0, numFlavors - 1));
  }, [numFlavors]);

  // Trava scroll do body quando montador mobile está ativo
  useEffect(() => {
    if (!useStepper) return;
    const isMobile = window.innerWidth < 768;
    if (isMobile) {
      document.body.style.overflow = "hidden";
      document.body.style.position = "fixed";
      document.body.style.width = "100%";
      document.body.style.top = `-${window.scrollY}px`;
      return () => {
        const scrollY = document.body.style.top;
        document.body.style.overflow = "";
        document.body.style.position = "";
        document.body.style.width = "";
        document.body.style.top = "";
        window.scrollTo(0, parseInt(scrollY || "0") * -1);
      };
    }
  }, [useStepper]);

  const isAcai = (siteInfo?.tipo_restaurante || "").toLowerCase().includes("acai") ||
    (siteInfo?.tipo_restaurante || "").toLowerCase().includes("açaí") ||
    (siteInfo?.tipo_restaurante || "").toLowerCase().includes("sorvet");

  const handleToggleAdicional = (id: number) => {
    setSelectedAdicionais(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleAdicionalQtd = (id: number, delta: number) => {
    setAdicionaisQtd(prev => {
      const next = new Map(prev);
      const current = next.get(id) || 0;
      const newQty = Math.max(0, current + delta);
      if (newQty === 0) {
        next.delete(id);
        setSelectedAdicionais(sa => sa.filter(x => x !== id));
      } else {
        next.set(id, newQty);
        if (!selectedAdicionais.includes(id)) {
          setSelectedAdicionais(sa => [...sa, id]);
        }
      }
      return next;
    });
  };

  // Pizza: seleciona sabor na fatia ativa
  const handleSelectSabor = (id: number) => {
    setSelectedSabores(prev => {
      const arr = [...prev];
      const existIdx = arr.indexOf(id);
      if (existIdx !== -1 && existIdx !== activeSlice) {
        arr[existIdx] = null;
      }
      arr[activeSlice] = id;
      return arr;
    });
    setTimeout(() => {
      setSelectedSabores(curr => {
        const nextEmpty = curr.findIndex((s, i) => i !== activeSlice && !s);
        if (nextEmpty !== -1) setActiveSlice(nextEmpty);
        return curr;
      });
    }, 50);
    setShowFlavorModal(false);
  };

  const handleRemoveSabor = (idx: number) => {
    setSelectedSabores(prev => {
      const arr = [...prev];
      arr[idx] = null;
      return arr;
    });
    setActiveSlice(idx);
  };

  const handleClickSlice = (idx: number) => {
    setActiveSlice(idx);
    setShowFlavorModal(true);
    setSearchSabor("");
  };

  const handleRecomecar = () => {
    setSelectedSabores(Array(numFlavors).fill(null));
    setActiveSlice(0);
    setSelectedBorda(null);
    setObservacoes("");
  };

  const getSaborNome = (id: number | null): string => {
    if (!id) return "";
    if (id === productId) return produto?.nome || "";
    const s = saboresDisp.find(sb => sb.id === id);
    return s?.nome || "";
  };
  const getSaborImg = (id: number | null): string | null => {
    if (!id) return null;
    if (id === productId) return produto?.imagem_url || null;
    const s = saboresDisp.find(sb => sb.id === id);
    return s?.imagem_url || null;
  };

  const filteredSabores = useMemo(() => {
    if (!searchSabor.trim()) return saboresDisp;
    const term = searchSabor.toLowerCase();
    return saboresDisp.filter(s =>
      s.nome.toLowerCase().includes(term) ||
      (s.descricao || "").toLowerCase().includes(term)
    );
  }, [saboresDisp, searchSabor]);

  function calcPreco(): number {
    if (!produto) return 0;
    let preco = produto.promocao && produto.preco_promocional
      ? produto.preco_promocional
      : produto.preco;

    const tamanhos = produto.variacoes_agrupadas?.tamanho || [];
    const tamSel = tamanhos.find(t => t.id === selectedTamanho);
    if (tamSel) preco += tamSel.preco_adicional;

    const bordas = produto.variacoes_agrupadas?.borda || [];
    const bordaSel = bordas.find(b => b.id === selectedBorda);
    if (bordaSel) preco += bordaSel.preco_adicional;

    const adicionaisArr = produto.variacoes_agrupadas?.adicional || [];
    for (const id of selectedAdicionais) {
      const ad = adicionaisArr.find(a => a.id === id);
      if (ad) {
        const qty = adicionaisQtd.get(id) || 1;
        preco += ad.preco_adicional * qty;
      }
    }
    return preco;
  }

  const handleAddToCart = async () => {
    if (!produto) return;
    setAdding(true);
    try {
      const variacoesIds: { variacao_id: number }[] = [];
      if (selectedTamanho) variacoesIds.push({ variacao_id: selectedTamanho });
      if (selectedBorda) variacoesIds.push({ variacao_id: selectedBorda });
      if (selectedPontoCarne) variacoesIds.push({ variacao_id: selectedPontoCarne });
      for (const id of selectedAdicionais) {
        const qty = adicionaisQtd.get(id) || 1;
        for (let i = 0; i < qty; i++) {
          variacoesIds.push({ variacao_id: id });
        }
      }

      let obs = observacoes;
      const saboresValidos = selectedSabores.filter((s): s is number => s !== null && s > 0);
      if (useStepper && saboresValidos.length > 1) {
        const nomesSabores = saboresValidos.map(sid => getSaborNome(sid)).filter(Boolean);
        obs = `Sabores: ${nomesSabores.join(" / ")}${observacoes ? ` | ${observacoes}` : ""}`;
      }

      await adicionarAoCarrinho({
        produto_id: produto.id,
        quantidade: quantity,
        observacao: obs || undefined,
        variacoes: variacoesIds.length > 0 ? variacoesIds : undefined,
      });

      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
      toast.success(`${produto.nome} adicionado ao carrinho!`);
      if (bebidas.length > 0) {
        setShowBebidaModal(true);
      } else {
        navigate("/cart");
      }
    } catch {
      toast.error("Erro ao adicionar ao carrinho");
    } finally {
      setAdding(false);
    }
  };

  const handleAddBebida = async (bebida: Bebida) => {
    try {
      await adicionarAoCarrinho({ produto_id: bebida.id, quantidade: 1 });
      toast.success(`${bebida.nome} adicionado!`);
    } catch {
      toast.error("Erro ao adicionar bebida");
    }
    setShowBebidaModal(false);
    navigate("/cart");
  };

  // ===== LOADING / NOT FOUND =====
  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-96 bg-muted rounded-lg" />
            <div className="h-8 bg-muted rounded w-1/3" />
            <div className="h-4 bg-muted rounded w-2/3" />
          </div>
        </div>
      </div>
    );
  }

  if (!produto) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <p className="text-center text-muted-foreground">Produto não encontrado</p>
        </div>
      </div>
    );
  }

  // ===== VARIÁVEIS DERIVADAS =====
  const precoUnit = calcPreco();
  const tamanhos = produto.variacoes_agrupadas?.tamanho || [];
  const bordas = produto.variacoes_agrupadas?.borda || [];
  const adicionais = produto.variacoes_agrupadas?.adicional || [];
  const pontoCarne = produto.variacoes_agrupadas?.ponto_carne || [];

  const tamSel = tamanhos.find(t => t.id === selectedTamanho);
  const bordaSel = bordas.find(b => b.id === selectedBorda);
  const saboresValidos = selectedSabores.filter((s): s is number => s !== null && s > 0);
  const canBuy = saboresValidos.length >= 1;

  const tamSelectedIdx = tamSel ? tamanhos.findIndex(t => t.id === selectedTamanho) : 0;
  const pizzaScale = getPizzaScaleDynamic(tamSelectedIdx >= 0 ? tamSelectedIdx : 0, tamanhos.length);

  // Cores Expresso Delivery
  const ED = {
    redDark: "#a40000",
    red: "#e40000",
    redGradient: "linear-gradient(90deg, #b30000 0%, #e40000 100%)",
    green: "#087607",
    greenDark: "#014f00",
    blue: "#0062ab",
    orange: "#ff4800",
    orangeDark: "#b13504",
    chipSabor: "#b20000",
    chipBorda: "#ff4800",
    chipObs: "#008a2a",
    chipMassa: "#0062ab",
    textDark: "#333",
    textMid: "#454545",
    textLight: "#515151",
    border: "#d4d4d4",
    bgLight: "#f5f5f5",
    white: "#fff",
  };

  // ===== RENDER =====
  return (
    <div className="min-h-screen" style={{ background: theme.colors.bodyBg }}>
      <div className="container py-4 md:py-6 px-4 max-w-5xl">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-3"
          style={{ color: theme.colors.textSecondary }}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar ao Cardápio
        </Button>

        {/* ===== MODO MONTADOR PIZZA ===== */}
        {useStepper ? (
          <div style={{ fontFamily: "'Roboto', 'Open Sans', sans-serif" }}>

            {/* ====== MOBILE: Layout fullscreen tipo app — SEM SCROLL ====== */}
            <div className="md:hidden" style={{
              position: "fixed", inset: 0, zIndex: 50,
              background: "#1a1a1a",
              display: "flex", flexDirection: "column",
              overflow: "hidden",
              touchAction: "none",
              overscrollBehavior: "none",
            }}>
              {/* TOPO: Voltar + Nome */}
              <div style={{
                padding: "10px 16px", display: "flex", alignItems: "center", gap: "10px",
                background: "rgba(0,0,0,0.3)", flexShrink: 0,
              }}>
                <button onClick={() => navigate("/")} style={{
                  background: "none", border: "none", cursor: "pointer", color: ED.white,
                  padding: "4px",
                }}>
                  <ArrowLeft className="w-5 h-5" />
                </button>
                <h2 style={{
                  color: ED.white, fontSize: "16px", fontWeight: 700, margin: 0,
                  flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {produto.nome}
                </h2>
                <button onClick={handleRecomecar} style={{
                  background: "rgba(255,255,255,0.15)", border: "none", borderRadius: "50%",
                  width: "32px", height: "32px", cursor: "pointer",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <RotateCcw className="w-4 h-4" style={{ color: ED.white }} />
                </button>
              </div>

              {/* TAMANHO: pill dropdown */}
              <div style={{ padding: "6px 16px", flexShrink: 0, position: "relative" }}>
                <label style={{
                  fontSize: "13px", textTransform: "uppercase", fontWeight: "bold",
                  display: "block", paddingBottom: "3px", color: ED.white,
                }}>Tamanho:</label>
                <button
                  onClick={() => setShowTamanhoDropdown(!showTamanhoDropdown)}
                  style={{
                    width: "100%", padding: "10px 40px 10px 16px",
                    borderRadius: "25px", border: "none",
                    background: ED.redGradient, color: ED.white,
                    fontSize: "15px", fontWeight: 700,
                    textAlign: "center", cursor: "pointer", position: "relative",
                    textTransform: "uppercase",
                  }}
                >
                  {tamSel ? `${tamSel.nome} - R$ ${(produto.preco + tamSel.preco_adicional).toFixed(2)}` : "Selecione"}
                  <span style={{
                    position: "absolute", right: "16px", top: "50%",
                    transform: "translateY(-50%)", fontSize: "12px",
                  }}>▼</span>
                </button>
                {showTamanhoDropdown && (
                  <div style={{
                    position: "absolute", top: "100%", left: 16, right: 16,
                    background: ED.white,
                    borderRadius: "0 0 12px 12px", zIndex: 100,
                    boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
                  }}>
                    {tamanhos.map(tam => (
                      <button
                        key={tam.id}
                        onClick={() => { setSelectedTamanho(tam.id); setShowTamanhoDropdown(false); }}
                        style={{
                          width: "100%", padding: "12px 16px", textAlign: "left",
                          border: "none", borderBottom: `1px solid #eee`,
                          background: selectedTamanho === tam.id ? "#fff5f5" : ED.white,
                          color: selectedTamanho === tam.id ? ED.redDark : "#444",
                          fontWeight: selectedTamanho === tam.id ? 700 : 400,
                          fontSize: "15px", cursor: "pointer",
                        }}
                      >
                        {tam.nome}
                        {(tam.max_sabores || 1) > 1 && <span style={{ color: "#999", fontSize: "12px" }}> (até {tam.max_sabores} sab.)</span>}
                        <span style={{ float: "right", color: ED.redDark, fontWeight: 700 }}>
                          R$ {(produto.preco + tam.preco_adicional).toFixed(2)}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* SABORES: pill com -/+ */}
              {maxSabores > 1 && (
                <div style={{ padding: "4px 16px", flexShrink: 0 }}>
                  <div style={{
                    display: "flex", alignItems: "center",
                    borderRadius: "25px", overflow: "hidden",
                    background: ED.redGradient, height: "42px",
                  }}>
                    <button
                      onClick={() => setNumFlavors(Math.max(1, numFlavors - 1))}
                      style={{
                        width: "50px", height: "42px", border: "none",
                        background: "rgba(0,0,0,0.15)", cursor: "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: ED.white,
                      }}
                    >
                      <Minus className="w-5 h-5" />
                    </button>
                    <span style={{
                      flex: 1, textAlign: "center",
                      fontSize: "15px", fontWeight: 700,
                      color: ED.white, textTransform: "uppercase",
                    }}>
                      {numFlavors} {numFlavors === 1 ? "sabor" : "sabores"}
                    </span>
                    <button
                      onClick={() => setNumFlavors(Math.min(maxSabores, numFlavors + 1))}
                      disabled={numFlavors >= maxSabores}
                      style={{
                        width: "50px", height: "42px", border: "none",
                        background: "rgba(0,0,0,0.15)", cursor: numFlavors >= maxSabores ? "not-allowed" : "pointer",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        color: ED.white,
                        opacity: numFlavors >= maxSabores ? 0.3 : 1,
                      }}
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}

              {/* CENTRO: Pizza na tábua — flex:1 ocupa todo espaço disponível */}
              <div style={{
                flex: 1, display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                minHeight: 0, padding: "8px 0",
              }}>
                <div style={{
                  position: "relative",
                  width: "min(280px, 70vw)", height: "min(280px, 70vw)",
                }}>
                  <img
                    src="/themes/pizzaria/wood-board.png" alt=""
                    style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }}
                    draggable={false}
                  />
                  <div style={{
                    position: "absolute",
                    top: "6%", left: "6%",
                    width: `${88 * pizzaScale}%`, height: `${88 * pizzaScale}%`,
                    marginTop: `${(88 - 88 * pizzaScale) / 2}%`,
                    marginLeft: `${(88 - 88 * pizzaScale) / 2}%`,
                    borderRadius: "100%", overflow: "hidden", cursor: "pointer",
                    transition: "all 0.3s ease",
                  }}>
                    {Array.from({ length: numFlavors }, (_, i) => {
                      const sid = selectedSabores[i];
                      const img = getSaborImg(sid);
                      const isEmpty = !sid;
                      const isActive = activeSlice === i;
                      const sliceStyle = getSliceStyle(i, numFlavors);
                      return (
                        <div key={i} onClick={() => handleClickSlice(i)}
                          style={{
                            position: "absolute", ...sliceStyle,
                            background: "transparent",
                            overflow: "hidden",
                            outline: isActive ? "2px solid #e40000" : "none",
                            outlineOffset: "-2px",
                            zIndex: sliceStyle.zIndex as number || (isActive ? 3 : 1),
                            cursor: "pointer",
                          }}
                        >
                          {!isEmpty && img && (
                            <img src={img} alt="" draggable={false} style={getSliceImgStyle(i, numFlavors)} />
                          )}
                          {isEmpty && (
                            <div style={{
                              position: "absolute", inset: 0,
                              display: "flex", alignItems: "center", justifyContent: "center",
                            }}>
                              <span style={{ color: "rgba(255,255,255,0.6)", fontSize: "11px", fontWeight: 500, textAlign: "center" }}>
                                {isActive ? "Toque" : `${i + 1}`}
                              </span>
                            </div>
                          )}
                          {!isEmpty && (
                            <button onClick={e => { e.stopPropagation(); handleRemoveSabor(i); }}
                              style={{
                                position: "absolute", top: "2px", right: "2px",
                                width: "22px", height: "22px", borderRadius: "50%",
                                background: "rgba(0,0,0,0.6)", border: "none", cursor: "pointer",
                                display: "flex", alignItems: "center", justifyContent: "center", zIndex: 10,
                              }}
                            >
                              <X className="w-3 h-3" style={{ color: ED.white }} />
                            </button>
                          )}
                        </div>
                      );
                    })}
                    {numFlavors === 2 && (
                      <div style={{ position: "absolute", top: 0, left: "50%", width: "2px", height: "100%", background: "rgba(255,255,255,0.8)", transform: "translateX(-50%)", pointerEvents: "none", zIndex: 4 }} />
                    )}
                    {numFlavors === 4 && (
                      <>
                        <div style={{ position: "absolute", top: 0, left: "50%", width: "2px", height: "100%", background: "rgba(255,255,255,0.8)", transform: "translateX(-50%)", pointerEvents: "none", zIndex: 4 }} />
                        <div style={{ position: "absolute", top: "50%", left: 0, width: "100%", height: "2px", background: "rgba(255,255,255,0.8)", transform: "translateY(-50%)", pointerEvents: "none", zIndex: 4 }} />
                      </>
                    )}
                  </div>
                </div>

                {/* Preço abaixo da pizza */}
                <p style={{
                  margin: "6px 0 0", fontSize: "15px", fontWeight: 700,
                  color: "rgba(255,255,255,0.85)", textAlign: "center",
                  textTransform: "uppercase",
                }}>
                  Preço da pizza: <span style={{ color: ED.white }}>R$ {(precoUnit * quantity).toFixed(2)}</span>
                </p>
              </div>

              {/* BAIXO: Botões de ação — fixo no fundo */}
              <div style={{
                padding: "8px 16px", flexShrink: 0,
                display: "flex", flexDirection: "column", gap: "6px",
                paddingBottom: "max(12px, env(safe-area-inset-bottom))",
              }}>
                {/* Escolher Sabor */}
                <button
                  onClick={() => { setShowFlavorModal(true); setSearchSabor(""); }}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
                    gap: "8px", padding: "11px 20px", borderRadius: "25px",
                    background: ED.redGradient, color: ED.white,
                    border: "none", cursor: "pointer",
                    fontSize: "15px", fontWeight: 700, textTransform: "uppercase",
                  }}
                >
                  <Search className="w-4 h-4" />
                  Escolher Sabor {numFlavors > 1 ? `(fatia ${activeSlice + 1})` : ""}
                </button>

                {/* Linha com Borda + Observações lado a lado */}
                <div style={{ display: "flex", gap: "6px" }}>
                  {bordas.length > 0 && (
                    <button
                      onClick={() => setShowBordaModal(true)}
                      style={{
                        flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                        gap: "6px", padding: "9px 12px", borderRadius: "25px",
                        background: ED.redGradient, color: ED.white,
                        border: "none", cursor: "pointer",
                        fontSize: "13px", fontWeight: 700, textTransform: "uppercase",
                      }}
                    >
                      <Star className="w-4 h-4" />
                      Borda
                      {bordaSel && bordaSel.preco_adicional > 0 && (
                        <span style={{ fontSize: "10px", opacity: 0.8 }}>({bordaSel.nome})</span>
                      )}
                    </button>
                  )}
                  <button
                    onClick={() => setShowObsModal(true)}
                    style={{
                      flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
                      gap: "6px", padding: "9px 12px", borderRadius: "25px",
                      background: ED.blue, color: ED.white,
                      border: "none", cursor: "pointer",
                      fontSize: "13px", fontWeight: 600, textTransform: "uppercase",
                    }}
                  >
                    <MessageSquare className="w-4 h-4" />
                    Obs.
                    {observacoes && <span style={{ fontSize: "10px", opacity: 0.8 }}>...</span>}
                  </button>
                </div>

                {/* Botão Adicionar ao Pedido */}
                <button
                  onClick={handleAddToCart}
                  disabled={adding || !canBuy}
                  style={{
                    width: "100%", display: "flex", alignItems: "center", justifyContent: "center",
                    gap: "10px", padding: "13px 20px",
                    background: canBuy ? `linear-gradient(to bottom, ${ED.green}, ${ED.greenDark})` : "#555",
                    borderBottom: canBuy ? `3px solid ${ED.greenDark}` : "3px solid #333",
                    color: canBuy ? ED.white : "#999",
                    borderTop: "none", borderLeft: "none", borderRight: "none",
                    borderRadius: "25px",
                    cursor: canBuy ? "pointer" : "not-allowed",
                    fontSize: "17px", fontWeight: 700, textTransform: "uppercase",
                    fontFamily: "'Oswald', 'Open Sans', sans-serif",
                  }}
                >
                  <ShoppingCart className="w-5 h-5" />
                  {adding ? "Adicionando..." : "Adicionar ao Pedido"}
                </button>
              </div>
            </div>

            {/* ====== DESKTOP: Layout original ====== */}

            {/* ====== HEADER VERMELHO — gradiente Expresso (desktop only) ====== */}
            <div
              className="hidden md:block"
              style={{
                background: ED.redGradient,
                borderRadius: "10px 10px 0 0",
                padding: "10px 16px",
              }}
            >
              <h2 style={{
                color: ED.white, fontSize: "20px", fontWeight: 700, margin: 0,
                textShadow: "0.5px 0.866px 1px rgb(47, 44, 36)",
              }}>
                {produto.nome} {tamSel ? `- ${tamSel.nome}` : ""}
                {numFlavors > 1 ? ` - ${numFlavors} sabore${numFlavors > 1 ? "s" : ""}` : ""}
              </h2>
            </div>

            {/* ====== CORPO DO MONTADOR (desktop) ====== */}
            <div
              className="hidden md:block"
              style={{
                background: ED.white,
                border: `1px solid ${ED.border}`, borderTop: "none",
                borderRadius: "0 0 10px 10px",
              }}
            >

              <div style={{ display: "flex", flexWrap: "wrap" }}>

                {/* ====== COLUNA ESQUERDA — Imagem produto + Quantidade (desktop) ====== */}
                <div style={{
                  minWidth: "212px", padding: "20px", textAlign: "center",
                  borderRight: `1px solid ${ED.border}`,
                }}>
                  {/* Imagem do produto */}
                  <div style={{
                    width: "200px", padding: "5px", border: `1px solid ${ED.border}`,
                    marginBottom: "15px", display: "inline-block",
                  }}>
                    {produto.imagem_url ? (
                      <img src={produto.imagem_url} alt={produto.nome}
                        style={{ width: "100%", display: "block" }} />
                    ) : (
                      <div style={{
                        width: "100%", height: "190px", display: "flex",
                        alignItems: "center", justifyContent: "center", fontSize: "72px",
                        background: "#f9f9f9",
                      }}>🍕</div>
                    )}
                  </div>

                  {/* Quantidade */}
                  <p style={{ color: ED.textDark, fontSize: "16px", margin: "0 0 5px" }}>Quantidade</p>
                  <div style={{
                    width: "134px", height: "40px", border: `1px solid ${ED.border}`,
                    margin: "0 auto", display: "flex", alignItems: "center",
                  }}>
                    <button
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                      style={{
                        width: "37px", height: "38px", background: ED.blue,
                        color: ED.white, fontSize: "24px", fontWeight: "bold",
                        border: "none", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center",
                      }}
                    >−</button>
                    <span style={{
                      width: "58px", height: "38px", display: "flex",
                      alignItems: "center", justifyContent: "center",
                      fontSize: "24px", fontWeight: "bold", color: ED.textDark,
                    }}>{String(quantity).padStart(2, "0")}</span>
                    <button
                      onClick={() => setQuantity(quantity + 1)}
                      style={{
                        width: "37px", height: "38px", background: ED.blue,
                        color: ED.white, fontSize: "24px", fontWeight: "bold",
                        border: "none", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center",
                      }}
                    >+</button>
                  </div>
                </div>

                {/* ====== COLUNA DIREITA — Controles + Pizza + Sabores ====== */}
                <div style={{ flex: 1, minWidth: 0 }}>

                  {/* --- CONTROLES: Tamanho + Qtd sabores --- */}
                  <div style={{
                    padding: "12px 16px", borderBottom: `1px solid ${ED.border}`,
                    display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "center",
                  }}>
                    {/* Tamanho dropdown (Select2 style) */}
                    <div style={{ position: "relative", flex: "1 1 auto", minWidth: "180px" }}>
                      <label style={{
                        fontSize: "14px", textTransform: "uppercase", fontWeight: "bold",
                        display: "block", paddingBottom: "2px", paddingLeft: "4px",
                        color: ED.textDark,
                      }}>Tamanho:</label>
                      <button
                        onClick={() => setShowTamanhoDropdown(!showTamanhoDropdown)}
                        style={{
                          width: "100%", maxWidth: "300px", padding: "10px 36px 10px 10px",
                          border: `1px solid ${ED.border}`, borderRadius: "3px",
                          fontSize: "16px", color: "#444", background: ED.white,
                          textAlign: "left", cursor: "pointer", position: "relative",
                        }}
                      >
                        {tamSel ? `${tamSel.nome} - R$ ${(produto.preco + tamSel.preco_adicional).toFixed(2)}` : "Selecione"}
                        <span style={{
                          position: "absolute", right: "10px", top: "50%",
                          transform: "translateY(-50%)", fontSize: "10px", color: "#888",
                        }}>▼</span>
                      </button>
                      {showTamanhoDropdown && (
                        <div style={{
                          position: "absolute", top: "100%", left: 0, right: 0,
                          maxWidth: "300px", background: ED.white,
                          border: `1px solid ${ED.border}`, borderTop: "none",
                          borderRadius: "0 0 3px 3px", zIndex: 100,
                          boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
                        }}>
                          {tamanhos.map(tam => (
                            <button
                              key={tam.id}
                              onClick={() => { setSelectedTamanho(tam.id); setShowTamanhoDropdown(false); }}
                              style={{
                                width: "100%", padding: "10px", textAlign: "left",
                                border: "none", borderBottom: `1px solid #eee`,
                                background: selectedTamanho === tam.id ? "#fff5f5" : ED.white,
                                color: selectedTamanho === tam.id ? ED.redDark : "#444",
                                fontWeight: selectedTamanho === tam.id ? 700 : 400,
                                fontSize: "14px", cursor: "pointer",
                              }}
                            >
                              {tam.nome}
                              {(tam.max_sabores || 1) > 1 && <span style={{ color: "#999", fontSize: "12px" }}> (até {tam.max_sabores} sab.)</span>}
                              <span style={{ float: "right", color: ED.redDark }}>
                                R$ {(produto.preco + tam.preco_adicional).toFixed(2)}
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Qtd sabores */}
                    {maxSabores > 1 && (
                      <div style={{
                        display: "flex", alignItems: "center", gap: "0",
                        border: `1px solid ${ED.border}`, borderRadius: "25px",
                        overflow: "hidden", height: "38px",
                      }}>
                        <button
                          onClick={() => setNumFlavors(Math.max(1, numFlavors - 1))}
                          style={{
                            width: "38px", height: "38px", border: "none",
                            background: "transparent", cursor: "pointer",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "20px", color: ED.textDark,
                          }}
                        >
                          <Minus className="w-4 h-4" />
                        </button>
                        <span style={{
                          padding: "0 12px", fontSize: "14px", fontWeight: 600,
                          color: ED.textDark, whiteSpace: "nowrap",
                        }}>
                          {numFlavors} {numFlavors === 1 ? "sabor" : "sabores"}
                        </span>
                        <button
                          onClick={() => setNumFlavors(Math.min(maxSabores, numFlavors + 1))}
                          disabled={numFlavors >= maxSabores}
                          style={{
                            width: "38px", height: "38px", border: "none",
                            background: "transparent", cursor: numFlavors >= maxSabores ? "not-allowed" : "pointer",
                            display: "flex", alignItems: "center", justifyContent: "center",
                            fontSize: "20px", color: ED.textDark,
                            opacity: numFlavors >= maxSabores ? 0.3 : 1,
                          }}
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    )}

                    {/* Botão Recomeçar */}
                    <button
                      onClick={handleRecomecar}
                      style={{
                        display: "flex", alignItems: "center", gap: "4px",
                        padding: "8px 14px", borderRadius: "25px",
                        background: ED.red, color: ED.white,
                        border: "none", cursor: "pointer",
                        fontSize: "13px", fontWeight: 600,
                      }}
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Recomeçar
                    </button>
                  </div>

                  {/* --- PIZZA VISUAL + PAINEL SABORES (desktop) --- */}
                  <div style={{ display: "flex", flexWrap: "wrap" }}>

                    {/* PIZZA NA TÁBUA */}
                    <div style={{
                      flex: "0 0 auto",
                      display: "flex", flexDirection: "column", alignItems: "center",
                      padding: "16px",
                    }}>
                      {/* Container da tábua — 270x270 como Expresso */}
                      <div style={{ position: "relative", width: "270px", height: "270px" }}>
                        <img
                          src="/themes/pizzaria/wood-board.png"
                          alt=""
                          style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }}
                          draggable={false}
                        />
                        {/* Pizza (240x240, margin 15px 9px como Expresso) */}
                        <div style={{
                          position: "absolute",
                          top: `${15 + (270 - 15 * 2) * (1 - pizzaScale) / 2}px`,
                          left: `${9 + (270 - 9 * 2) * (1 - pizzaScale) / 2}px`,
                          width: `${240 * pizzaScale}px`,
                          height: `${240 * pizzaScale}px`,
                          borderRadius: "100%",
                          overflow: "hidden",
                          cursor: "pointer",
                          transition: "all 0.3s ease",
                        }}>
                          {/* Fatias */}
                          {Array.from({ length: numFlavors }, (_, i) => {
                            const sid = selectedSabores[i];
                            const img = getSaborImg(sid);
                            const isEmpty = !sid;
                            const isActive = activeSlice === i;
                            const sliceStyle = getSliceStyle(i, numFlavors);

                            return (
                              <div
                                key={i}
                                onClick={() => handleClickSlice(i)}
                                style={{
                                  position: "absolute",
                                  ...sliceStyle,
                                  background: "transparent",
                                  overflow: "hidden",
                                  outline: isActive ? "2px solid #e40000" : "none",
                                  outlineOffset: "-2px",
                                  zIndex: sliceStyle.zIndex as number || (isActive ? 3 : 1),
                                  cursor: "pointer",
                                  transition: "all 0.2s",
                                }}
                              >
                                {!isEmpty && img && (
                                  <img src={img} alt="" draggable={false}
                                    style={getSliceImgStyle(i, numFlavors)} />
                                )}
                                {isEmpty && (
                                  <div style={{
                                    position: "absolute", inset: 0,
                                    display: "flex", alignItems: "center", justifyContent: "center",
                                  }}>
                                    <span style={{
                                      color: "#888", fontSize: "11px", fontWeight: 500,
                                      textAlign: "center", lineHeight: 1.2,
                                    }}>
                                      {isActive ? "Clique\npara\nescolher" : `${i + 1}`}
                                    </span>
                                  </div>
                                )}
                                {/* Remove flavor icon — estilo Expresso */}
                                {!isEmpty && (
                                  <button
                                    onClick={e => { e.stopPropagation(); handleRemoveSabor(i); }}
                                    style={{
                                      position: "absolute", top: "2px", right: "2px",
                                      width: "24px", height: "24px", borderRadius: "50%",
                                      background: "rgba(0,0,0,0.6)", border: "none",
                                      cursor: "pointer", display: "flex",
                                      alignItems: "center", justifyContent: "center",
                                      zIndex: 10,
                                    }}
                                  >
                                    <X className="w-3 h-3" style={{ color: ED.white }} />
                                  </button>
                                )}
                              </div>
                            );
                          })}

                          {/* Separadores brancos */}
                          {numFlavors === 2 && (
                            <div style={{
                              position: "absolute", top: 0, left: "50%", width: "2px", height: "100%",
                              background: "rgba(255,255,255,0.8)", transform: "translateX(-50%)",
                              pointerEvents: "none", zIndex: 4,
                            }} />
                          )}
                          {numFlavors === 4 && (
                            <>
                              <div style={{
                                position: "absolute", top: 0, left: "50%", width: "2px", height: "100%",
                                background: "rgba(255,255,255,0.8)", transform: "translateX(-50%)",
                                pointerEvents: "none", zIndex: 4,
                              }} />
                              <div style={{
                                position: "absolute", top: "50%", left: 0, width: "100%", height: "2px",
                                background: "rgba(255,255,255,0.8)", transform: "translateY(-50%)",
                                pointerEvents: "none", zIndex: 4,
                              }} />
                            </>
                          )}
                        </div>
                      </div>

                      {/* Preço abaixo da pizza */}
                      <p style={{
                        margin: "12px 0 0", fontSize: "16px", fontWeight: 600,
                        color: ED.textDark, textAlign: "center",
                      }}>
                        Preço da pizza: <span style={{ color: ED.redDark }}>R$ {(precoUnit * quantity).toFixed(2)}</span>
                      </p>
                    </div>

                    {/* PAINEL DE SABORES (lado direito desktop / embaixo mobile) */}
                    <div className="hidden md:flex" style={{
                      flex: 1, minWidth: "260px", flexDirection: "column",
                      borderLeft: `1px solid ${ED.border}`,
                    }}>
                      {/* Header painel */}
                      <div style={{
                        background: ED.redGradient, padding: "8px 12px",
                        color: ED.white, fontSize: "16px", fontWeight: 600,
                        textShadow: "0.5px 0.866px 1px rgb(47, 44, 36)",
                      }}>
                        Escolha o sabor {numFlavors > 1 ? `(fatia ${activeSlice + 1})` : ""}
                      </div>

                      {/* Busca */}
                      <div style={{ padding: "8px", borderBottom: `1px solid #eee` }}>
                        <div style={{ position: "relative" }}>
                          <Search style={{
                            position: "absolute", left: "10px", top: "50%",
                            transform: "translateY(-50%)", width: "16px", height: "16px",
                            color: "#999",
                          }} />
                          <input
                            type="text" value={searchSabor}
                            onChange={e => setSearchSabor(e.target.value)}
                            placeholder="Buscar sabor..."
                            style={{
                              width: "100%", padding: "8px 10px 8px 34px",
                              border: `1px solid ${ED.border}`, borderRadius: "3px",
                              fontSize: "14px", color: ED.textDark, outline: "none",
                            }}
                          />
                        </div>
                      </div>

                      {/* Lista de sabores scrollável */}
                      <div ref={saborListRef} style={{
                        flex: 1, overflowY: "auto", maxHeight: "350px",
                      }}>
                        {filteredSabores.map(sabor => {
                          const selIdx = selectedSabores.indexOf(sabor.id);
                          const isSelected = selIdx !== -1;
                          return (
                            <div
                              key={sabor.id}
                              onClick={() => handleSelectSabor(sabor.id)}
                              style={{
                                display: "flex", alignItems: "center", gap: "8px",
                                padding: "6px 8px", cursor: "pointer",
                                borderBottom: `1px dotted ${ED.border}`,
                                background: isSelected ? "#fff5f5" : ED.white,
                                transition: "background 0.15s",
                              }}
                              onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = "#efefef"; }}
                              onMouseLeave={e => { e.currentTarget.style.background = isSelected ? "#fff5f5" : ED.white; }}
                            >
                              {/* Thumb 56px */}
                              <div style={{
                                width: "56px", height: "56px", flexShrink: 0,
                                borderRadius: "4px", overflow: "hidden", background: "#f5f5f5",
                              }}>
                                {sabor.imagem_url ? (
                                  <img src={sabor.imagem_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                                ) : (
                                  <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px" }}>🍕</div>
                                )}
                              </div>
                              {/* Nome + desc */}
                              <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{
                                  fontSize: "14px", fontWeight: 600, color: ED.textMid,
                                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                }}>
                                  {sabor.nome}
                                </div>
                                {sabor.descricao && (
                                  <div style={{
                                    fontSize: "11px", color: ED.textLight,
                                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                                  }}>
                                    {sabor.descricao}
                                  </div>
                                )}
                              </div>
                              {/* Preço / badge */}
                              <div style={{ flexShrink: 0, textAlign: "right" }}>
                                {isSelected ? (
                                  <span style={{
                                    fontSize: "11px", fontWeight: 700, padding: "2px 8px",
                                    borderRadius: "10px", background: ED.chipSabor, color: ED.white,
                                  }}>Fatia {selIdx + 1}</span>
                                ) : (
                                  <span style={{ fontSize: "13px", fontWeight: 600, color: ED.redDark }}>
                                    R$ {sabor.preco.toFixed(2)}
                                  </span>
                                )}
                              </div>
                            </div>
                          );
                        })}
                        {filteredSabores.length === 0 && (
                          <div style={{ padding: "24px", textAlign: "center", color: "#999", fontSize: "14px" }}>
                            Nenhum sabor encontrado
                          </div>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* --- CHIPS DOS SELECIONADOS + BOTÕES OPCIONAIS (desktop) --- */}
                  <div style={{ padding: "12px 16px", borderTop: `1px solid ${ED.border}` }}>

                    {/* Chips: Sabores selecionados */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "8px" }}>
                      {selectedSabores.map((sid, i) => sid && (
                        <span key={`chip-sab-${i}`} style={{
                          display: "inline-flex", alignItems: "center",
                          borderRadius: "20px", overflow: "hidden",
                          background: ED.white, border: `1px solid ${ED.border}`,
                          fontSize: "13px",
                        }}>
                          <button
                            onClick={() => handleRemoveSabor(i)}
                            style={{
                              padding: "4px 8px", background: ED.chipSabor,
                              color: ED.white, border: "none", cursor: "pointer",
                              display: "flex", alignItems: "center",
                            }}
                          >
                            <X className="w-3 h-3" />
                          </button>
                          <span style={{ padding: "4px 10px", color: ED.textDark, fontWeight: 500 }}>
                            {getSaborNome(sid)}
                          </span>
                        </span>
                      ))}

                      {/* Chip borda */}
                      {bordaSel && bordaSel.preco_adicional > 0 && (
                        <span style={{
                          display: "inline-flex", alignItems: "center",
                          borderRadius: "20px", overflow: "hidden",
                          background: ED.white, border: `1px solid ${ED.border}`,
                          fontSize: "13px",
                        }}>
                          <button
                            onClick={() => setSelectedBorda(bordas[0]?.id || null)}
                            style={{
                              padding: "4px 8px", background: ED.chipBorda,
                              color: ED.white, border: "none", cursor: "pointer",
                              display: "flex", alignItems: "center",
                            }}
                          >
                            <X className="w-3 h-3" />
                          </button>
                          <span style={{ padding: "4px 10px", color: ED.textDark, fontWeight: 500 }}>
                            Borda: {bordaSel.nome}
                          </span>
                        </span>
                      )}

                      {/* Chip observações */}
                      {observacoes && (
                        <span style={{
                          display: "inline-flex", alignItems: "center",
                          borderRadius: "20px", overflow: "hidden",
                          background: ED.white, border: `1px solid ${ED.border}`,
                          fontSize: "13px",
                        }}>
                          <button
                            onClick={() => setObservacoes("")}
                            style={{
                              padding: "4px 8px", background: ED.chipObs,
                              color: ED.white, border: "none", cursor: "pointer",
                              display: "flex", alignItems: "center",
                            }}
                          >
                            <X className="w-3 h-3" />
                          </button>
                          <span style={{
                            padding: "4px 10px", color: ED.textDark, fontWeight: 500,
                            maxWidth: "150px", overflow: "hidden", textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}>
                            Obs: {observacoes}
                          </span>
                        </span>
                      )}
                    </div>

                    {/* Botões: Borda + Observações (pills estilo Expresso) */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                      {bordas.length > 0 && (
                        <button
                          onClick={() => setShowBordaModal(true)}
                          style={{
                            display: "flex", alignItems: "center", gap: "6px",
                            padding: "8px 16px", borderRadius: "25px",
                            background: ED.orange, color: ED.white,
                            border: "none", borderBottom: `2px solid ${ED.orangeDark}`,
                            cursor: "pointer", fontSize: "14px", fontWeight: 500,
                          }}
                        >
                          <Star className="w-4 h-4" />
                          Escolher Borda
                        </button>
                      )}

                      <button
                        onClick={() => setShowObsModal(true)}
                        style={{
                          display: "flex", alignItems: "center", gap: "6px",
                          padding: "8px 16px", borderRadius: "25px",
                          background: ED.blue, color: ED.white,
                          border: "none", borderBottom: `2px solid #004276`,
                          cursor: "pointer", fontSize: "14px", fontWeight: 500,
                        }}
                      >
                        <MessageSquare className="w-4 h-4" />
                        Observações
                      </button>
                    </div>
                  </div>

                  {/* --- BOTÃO COMPRAR (fixo embaixo) --- */}
                  <div style={{ padding: "0 16px 16px" }}>
                    <button
                      onClick={handleAddToCart}
                      disabled={adding || !canBuy}
                      style={{
                        width: "100%", maxWidth: "295px",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        gap: "10px", margin: "0 auto",
                        padding: "14px 20px",
                        background: canBuy ? `linear-gradient(to bottom, ${ED.green}, ${ED.greenDark})` : "#d4d4d4",
                        borderBottom: canBuy ? `3px solid ${ED.greenDark}` : "3px solid #a5a5a5",
                        color: canBuy ? ED.white : "#6f6f6f",
                        borderTop: "none", borderLeft: "none", borderRight: "none",
                        borderRadius: "4px",
                        cursor: canBuy ? "pointer" : "not-allowed",
                        fontSize: "20px", fontWeight: 400,
                        fontFamily: "'Oswald', 'Open Sans', sans-serif",
                        transition: "all 0.2s",
                      }}
                    >
                      <ShoppingCart className="w-5 h-5" />
                      {adding ? "Adicionando..." : "Adicionar ao Pedido"}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* ====== MODAL SABORES — Bottom-sheet mobile / Dialog desktop ====== */}
            {showFlavorModal && (
              <>
                {/* Backdrop */}
                <div
                  onClick={() => setShowFlavorModal(false)}
                  style={{
                    position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)",
                    zIndex: 9998,
                  }}
                />
                {/* Modal — bottom-sheet no mobile, centralizado no desktop */}
                <div
                  className="fixed inset-x-0 bottom-0 md:inset-auto md:top-1/2 md:left-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2"
                  style={{
                    zIndex: 9999, background: ED.white,
                    borderRadius: "24px 24px 0 0",
                    maxHeight: "80vh", display: "flex", flexDirection: "column",
                    boxShadow: "0 -4px 30px rgba(0,0,0,0.3)",
                  }}
                >
                  {/* Drag handle mobile */}
                  <div className="md:hidden" style={{
                    display: "flex", justifyContent: "center", padding: "8px 0 4px",
                  }}>
                    <div style={{ width: "40px", height: "4px", borderRadius: "2px", background: "#ccc" }} />
                  </div>

                  {/* Header */}
                  <div style={{
                    background: ED.redGradient, padding: "10px 16px",
                    borderRadius: "0",
                    color: ED.white, fontSize: "18px", fontWeight: 600,
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    textShadow: "0.5px 0.866px 1px rgb(47, 44, 36)",
                  }}>
                    <span>Escolha o sabor {numFlavors > 1 ? `(fatia ${activeSlice + 1})` : ""}</span>
                    <button
                      onClick={() => setShowFlavorModal(false)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: ED.white }}
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Busca */}
                  <div style={{ padding: "10px 12px", borderBottom: `1px solid #eee` }}>
                    <div style={{ position: "relative" }}>
                      <Search style={{
                        position: "absolute", left: "10px", top: "50%",
                        transform: "translateY(-50%)", width: "16px", height: "16px", color: "#999",
                      }} />
                      <input
                        type="text" value={searchSabor}
                        onChange={e => setSearchSabor(e.target.value)}
                        placeholder="Buscar sabor..."
                        autoFocus
                        style={{
                          width: "100%", padding: "10px 10px 10px 34px",
                          border: `1px solid ${ED.border}`, borderRadius: "3px",
                          fontSize: "15px", color: ED.textDark, outline: "none",
                        }}
                      />
                    </div>
                  </div>

                  {/* Lista scrollável */}
                  <div style={{ flex: 1, overflowY: "auto", maxHeight: "60vh" }}>
                    {filteredSabores.map(sabor => {
                      const selIdx = selectedSabores.indexOf(sabor.id);
                      const isSelected = selIdx !== -1;
                      return (
                        <div
                          key={sabor.id}
                          onClick={() => handleSelectSabor(sabor.id)}
                          style={{
                            display: "flex", alignItems: "center", gap: "10px",
                            padding: "8px 12px", cursor: "pointer",
                            borderBottom: `1px dotted ${ED.border}`,
                            background: isSelected ? "#fff5f5" : ED.white,
                          }}
                        >
                          <div style={{
                            width: "56px", height: "56px", flexShrink: 0,
                            borderRadius: "4px", overflow: "hidden", background: "#f5f5f5",
                          }}>
                            {sabor.imagem_url ? (
                              <img src={sabor.imagem_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                            ) : (
                              <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "28px" }}>🍕</div>
                            )}
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: "14px", fontWeight: 600, color: ED.textMid }}>
                              {sabor.nome}
                            </div>
                            {sabor.descricao && (
                              <div style={{
                                fontSize: "12px", color: ED.textLight,
                                overflow: "hidden", textOverflow: "ellipsis",
                                display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                              }}>
                                {sabor.descricao}
                              </div>
                            )}
                          </div>
                          <div style={{ flexShrink: 0, textAlign: "right" }}>
                            {isSelected ? (
                              <span style={{
                                fontSize: "11px", fontWeight: 700, padding: "3px 10px",
                                borderRadius: "10px", background: ED.chipSabor, color: ED.white,
                              }}>Fatia {selIdx + 1}</span>
                            ) : (
                              <span style={{ fontSize: "13px", fontWeight: 600, color: ED.redDark }}>
                                R$ {sabor.preco.toFixed(2)}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                    {filteredSabores.length === 0 && (
                      <div style={{ padding: "32px", textAlign: "center", color: "#999" }}>
                        Nenhum sabor encontrado
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}

            {/* ====== MODAL BORDA ====== */}
            {showBordaModal && (
              <>
                <div onClick={() => setShowBordaModal(false)}
                  style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 9998 }} />
                <div
                  className="fixed inset-x-0 bottom-0 md:inset-auto md:top-1/2 md:left-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2"
                  style={{
                    zIndex: 9999, background: ED.white,
                    borderRadius: "24px 24px 0 0",
                    maxHeight: "60vh", display: "flex", flexDirection: "column",
                    boxShadow: "0 -4px 30px rgba(0,0,0,0.3)",
                    width: "100%", maxWidth: "400px",
                  }}
                >
                  <div className="md:hidden" style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px" }}>
                    <div style={{ width: "40px", height: "4px", borderRadius: "2px", background: "#ccc" }} />
                  </div>
                  <div style={{
                    background: `linear-gradient(to bottom, ${ED.red} 30%, ${ED.redDark})`,
                    padding: "10px 16px", color: ED.white, fontSize: "18px", fontWeight: 600,
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    textShadow: "0.5px 0.866px 1px rgb(47, 44, 36)",
                  }}>
                    <span>Escolha a Borda</span>
                    <button onClick={() => setShowBordaModal(false)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: ED.white }}>
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <div style={{ flex: 1, overflowY: "auto" }}>
                    {bordas.map(borda => (
                      <button
                        key={borda.id}
                        onClick={() => { setSelectedBorda(borda.id); setShowBordaModal(false); }}
                        style={{
                          width: "100%", padding: "12px 16px", textAlign: "left",
                          border: "none", borderBottom: `1px solid ${ED.border}`,
                          background: selectedBorda === borda.id ? "#fff5f5" : ED.white,
                          color: selectedBorda === borda.id ? ED.redDark : "#444",
                          fontWeight: selectedBorda === borda.id ? 700 : 400,
                          fontSize: "15px", cursor: "pointer",
                          display: "flex", justifyContent: "space-between", alignItems: "center",
                        }}
                      >
                        <span>{borda.nome}</span>
                        <span style={{ color: ED.redDark, fontSize: "13px" }}>
                          {borda.preco_adicional > 0 ? `+R$ ${borda.preco_adicional.toFixed(2)}` : "Grátis"}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {/* ====== MODAL OBSERVAÇÕES ====== */}
            {showObsModal && (
              <>
                <div onClick={() => setShowObsModal(false)}
                  style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.5)", zIndex: 9998 }} />
                <div
                  className="fixed inset-x-0 bottom-0 md:inset-auto md:top-1/2 md:left-1/2 md:transform md:-translate-x-1/2 md:-translate-y-1/2"
                  style={{
                    zIndex: 9999, background: ED.white,
                    borderRadius: "24px 24px 0 0",
                    display: "flex", flexDirection: "column",
                    boxShadow: "0 -4px 30px rgba(0,0,0,0.3)",
                    width: "100%", maxWidth: "400px",
                  }}
                >
                  <div className="md:hidden" style={{ display: "flex", justifyContent: "center", padding: "8px 0 4px" }}>
                    <div style={{ width: "40px", height: "4px", borderRadius: "2px", background: "#ccc" }} />
                  </div>
                  <div style={{
                    background: `linear-gradient(to bottom, ${ED.red} 30%, ${ED.redDark})`,
                    padding: "10px 16px", color: ED.white, fontSize: "18px", fontWeight: 600,
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    textShadow: "0.5px 0.866px 1px rgb(47, 44, 36)",
                  }}>
                    <span>Observações</span>
                    <button onClick={() => setShowObsModal(false)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: ED.white }}>
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                  <div style={{ padding: "16px" }}>
                    <textarea
                      value={observacoes}
                      onChange={e => setObservacoes(e.target.value)}
                      placeholder="Ex: Sem cebola, extra queijo..."
                      autoFocus
                      style={{
                        width: "100%", padding: "10px", minHeight: "100px",
                        border: `1px solid ${ED.border}`, borderRadius: "4px",
                        fontSize: "15px", color: ED.textDark, outline: "none",
                        resize: "vertical",
                      }}
                    />
                    <button
                      onClick={() => setShowObsModal(false)}
                      style={{
                        width: "100%", marginTop: "10px", padding: "10px",
                        background: ED.green, color: ED.white,
                        border: "none", borderBottom: `2px solid ${ED.greenDark}`,
                        borderRadius: "4px", cursor: "pointer",
                        fontSize: "16px", fontWeight: 600,
                      }}
                    >
                      Confirmar
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        ) : (
          /* ===== MODO CLÁSSICO (SEM MONTADOR) ===== */
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Imagem */}
            <div>
              <Card className="overflow-hidden rounded-xl">
                <div className="w-full aspect-square bg-[var(--bg-card-hover)] flex items-center justify-center text-8xl">
                  {produto.imagem_url ? (
                    <img src={produto.imagem_url} alt={produto.nome} className="w-full h-full object-cover" />
                  ) : (
                    getEmojiByTipo(siteInfo)
                  )}
                </div>
              </Card>
            </div>

            {/* Info + Variações */}
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-extrabold mb-2 uppercase">{produto.nome}</h1>
                {produto.descricao && (
                  <p className="text-muted-foreground mb-2">{produto.descricao}</p>
                )}
                {produto.promocao && produto.preco_promocional && (
                  <div className="flex items-center gap-3">
                    <span className="text-lg text-muted-foreground line-through">
                      R$ {produto.preco.toFixed(2)}
                    </span>
                    <span className="text-2xl font-bold text-[var(--cor-primaria)]">
                      R$ {produto.preco_promocional.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Tamanhos */}
              {tamanhos.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-3">Tamanho</h3>
                  <div className="grid grid-cols-2 gap-3">
                    {tamanhos.map(tam => {
                      const precoTam = produto.preco + tam.preco_adicional;
                      return (
                        <button
                          key={tam.id}
                          onClick={() => setSelectedTamanho(tam.id)}
                          className={`p-3 border rounded-lg transition-all text-left ${
                            selectedTamanho === tam.id
                              ? "border-2 bg-[var(--bg-card-hover)]"
                              : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                          }`}
                          style={selectedTamanho === tam.id ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
                        >
                          <div className="font-bold text-sm">{tam.nome}</div>
                          <div className="text-xs text-muted-foreground">R$ {precoTam.toFixed(2)}</div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Bordas */}
              {bordas.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-3">Borda</h3>
                  <div className="space-y-2">
                    {bordas.map(borda => (
                      <button
                        key={borda.id}
                        onClick={() => setSelectedBorda(borda.id)}
                        className={`w-full p-3 border rounded-lg text-left transition-all flex justify-between items-center ${
                          selectedBorda === borda.id
                            ? "border-2 bg-[var(--bg-card-hover)]"
                            : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                        }`}
                        style={selectedBorda === borda.id ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        <span className="font-semibold text-sm">{borda.nome}</span>
                        {borda.preco_adicional > 0 && (
                          <span className="text-sm font-bold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                            +R$ {borda.preco_adicional.toFixed(2)}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Ponto da carne */}
              {pontoCarne.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-3">Ponto da Carne</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {pontoCarne.map(pc => (
                      <button
                        key={pc.id}
                        onClick={() => setSelectedPontoCarne(pc.id)}
                        className={`p-2 border rounded-lg text-center text-sm font-semibold ${
                          selectedPontoCarne === pc.id
                            ? "border-2 bg-[var(--bg-card-hover)]"
                            : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                        }`}
                        style={selectedPontoCarne === pc.id ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        {pc.nome}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Adicionais */}
              {adicionais.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold mb-3"
                    style={{ color: theme.colors.textPrimary, fontFamily: theme.fonts.special || theme.fonts.heading }}
                  >
                    {isAcai ? "Monte seu Açaí" : "Adicionais"}
                  </h3>
                  <div className="space-y-2">
                    {adicionais.map(adic => {
                      const qty = adicionaisQtd.get(adic.id) || 0;
                      const isSelected = selectedAdicionais.includes(adic.id);

                      return isAcai ? (
                        <div
                          key={adic.id}
                          className="w-full p-3 rounded-lg flex items-center justify-between"
                          style={{
                            background: qty > 0
                              ? (theme.isDark ? "rgba(0,180,0,0.08)" : "rgba(0,180,0,0.05)")
                              : (theme.isDark ? "rgba(255,255,255,0.03)" : "rgba(0,0,0,0.02)"),
                            border: `1px solid ${qty > 0 ? theme.colors.quantityIncrease : theme.colors.borderSubtle}`,
                            borderRadius: theme.cardRadius,
                          }}
                        >
                          <div>
                            <span className="font-semibold text-sm" style={{ color: theme.colors.textPrimary }}>
                              {adic.nome}
                            </span>
                            <span className="text-xs ml-2" style={{ color: theme.colors.priceColor }}>
                              {adic.preco_adicional > 0 ? `+R$ ${adic.preco_adicional.toFixed(2)}` : "Grátis"}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            {qty > 0 && (
                              <button
                                className="w-7 h-7 rounded flex items-center justify-center text-white"
                                style={{ background: theme.colors.quantityDecrease }}
                                onClick={() => handleAdicionalQtd(adic.id, -1)}
                              >
                                {qty === 1 ? <Trash2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                              </button>
                            )}
                            {qty > 0 && (
                              <span className="w-6 text-center text-sm font-bold" style={{ color: theme.colors.textPrimary }}>
                                {qty}
                              </span>
                            )}
                            <button
                              className="w-7 h-7 rounded flex items-center justify-center text-white"
                              style={{ background: theme.colors.quantityIncrease }}
                              onClick={() => handleAdicionalQtd(adic.id, 1)}
                            >
                              <Plus className="w-3 h-3" />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          key={adic.id}
                          onClick={() => handleToggleAdicional(adic.id)}
                          className={`w-full p-3 border rounded-lg text-left transition-all flex justify-between items-center ${
                            isSelected
                              ? "border-2 bg-green-900/15 border-green-600"
                              : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                          }`}
                        >
                          <span className="font-semibold text-sm">{adic.nome}</span>
                          <span className="text-sm">
                            {adic.preco_adicional > 0 ? `+R$ ${adic.preco_adicional.toFixed(2)}` : "Grátis"}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Observações */}
              <div>
                <label className="text-sm font-bold mb-2 block">Observações (opcional)</label>
                <textarea
                  value={observacoes}
                  onChange={e => setObservacoes(e.target.value)}
                  placeholder="Ex: Sem cebola, extra queijo..."
                  className="w-full px-4 py-2 dark-input"
                  rows={3}
                />
              </div>

              {/* Quantidade + Preço + Botão */}
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <span className="text-sm font-bold" style={{ color: theme.colors.textPrimary }}>Quantidade:</span>
                  <div className="flex items-center rounded-lg overflow-hidden" style={{ border: `1px solid ${theme.colors.borderSubtle}` }}>
                    <button
                      className="w-9 h-9 flex items-center justify-center text-white"
                      style={{ background: theme.colors.quantityDecrease }}
                      onClick={() => setQuantity(Math.max(1, quantity - 1))}
                    >
                      <Minus className="w-4 h-4" />
                    </button>
                    <span className="px-4 py-2 font-bold" style={{ color: theme.colors.textPrimary }}>{quantity}</span>
                    <button
                      className="w-9 h-9 flex items-center justify-center text-white"
                      style={{ background: theme.colors.quantityIncrease }}
                      onClick={() => setQuantity(quantity + 1)}
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="pt-4" style={{ borderTop: `1px solid ${theme.colors.borderSubtle}` }}>
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-lg font-bold" style={{ color: theme.colors.textPrimary }}>Total:</span>
                    <span
                      className="text-2xl font-extrabold"
                      style={{ color: theme.colors.priceColor, fontFamily: theme.fonts.special || theme.fonts.heading }}
                    >
                      R$ {(precoUnit * quantity).toFixed(2)}
                    </span>
                  </div>

                  <button
                    onClick={handleAddToCart}
                    disabled={adding}
                    className="w-full font-bold text-white text-lg rounded-lg transition-opacity disabled:opacity-50"
                    style={{
                      background: "#00b400",
                      borderBottom: "3px solid #009a00",
                      height: "52px",
                    }}
                  >
                    {adding ? "Adicionando..." : "Adicionar ao Carrinho"}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal sugestão de bebidas */}
      {showBebidaModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-xl max-w-md w-full p-6 relative">
            <button onClick={() => { setShowBebidaModal(false); navigate("/cart"); }} className="absolute top-3 right-3">
              <X className="w-5 h-5 text-[var(--text-muted)]" />
            </button>
            <h3 className="text-xl font-bold mb-1">Que tal uma bebida?</h3>
            <p className="text-sm text-muted-foreground mb-4">Aproveite para adicionar ao seu pedido</p>
            <div className="grid grid-cols-2 gap-3 max-h-60 overflow-y-auto">
              {bebidas.map(beb => (
                <button
                  key={beb.id}
                  onClick={() => handleAddBebida(beb)}
                  className="p-3 border rounded-lg text-left hover:border-[rgba(255,255,255,0.15)] transition-all"
                >
                  <div className="text-2xl mb-1">🥤</div>
                  <div className="font-bold text-sm">{beb.nome}</div>
                  <div className="text-sm" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                    R$ {beb.preco.toFixed(2)}
                  </div>
                </button>
              ))}
            </div>
            <Button
              variant="outline"
              className="w-full mt-4"
              onClick={() => { setShowBebidaModal(false); navigate("/cart"); }}
            >
              Não, obrigado
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
