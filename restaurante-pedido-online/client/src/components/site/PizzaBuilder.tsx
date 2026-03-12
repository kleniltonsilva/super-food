/**
 * PizzaBuilder.tsx — Montador visual de pizza inline na página.
 *
 * Aparece como uma CAIXA na mesma página (não modal fullscreen).
 * Layout 3 colunas: esquerda (opções) | centro (pizza visual) | direita (recheio + adicionais).
 *
 * TODOS os controles são botões accordion (clica abre/fecha):
 * - Tamanho: accordion seleção única
 * - Sabores Qtd: accordion seleção única
 * - Sabores: lista com checkbox visual + busca
 * - Borda: accordion seleção única, "Sem Borda" pré-selecionado
 * - Recheio: accordion por sabor (desmarcar = remover ingrediente)
 * - Adicionais: accordion com busca + extras selecionados como tags com X
 * - Observações: accordion com textarea
 * - Preço: modo mais_caro ou proporcional
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { X, Plus, Minus, Trash2, ChevronDown, Check, Search } from "lucide-react";
import { useProdutoDetalhe, useSaboresDisponiveis, useAdicionarCarrinho } from "@/hooks/useQueries";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { toast } from "sonner";
import PizzaPaddle from "./PizzaPaddle";

interface PizzaBuilderProps {
  produtoId: number;
  onClose: () => void;
}

interface Variacao {
  id: number;
  nome: string;
  descricao: string | null;
  preco_adicional: number;
  estoque_disponivel: boolean;
  max_sabores?: number;
}

interface Sabor {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  imagem_url: string | null;
  ingredientes: string[];
}

interface IngredienteAdicional {
  nome: string;
  preco: number;
}

function getSizeBadge(nome: string): string {
  const lower = nome.toLowerCase();
  if (lower.includes("gigante") || lower.includes("familia")) return "GG";
  if (lower.includes("grande")) return "G";
  if (lower.includes("media") || lower.includes("média")) return "M";
  if (lower.includes("pequena") || lower.includes("broto") || lower.includes("individual")) return "P";
  const words = nome.split(" ").filter(w => w.length > 0);
  if (words.length === 1) return words[0].charAt(0).toUpperCase();
  return words.map(w => w.charAt(0).toUpperCase()).join("").slice(0, 2);
}

function MiniPizzaIcon({ slices, className }: { slices: number; className?: string }) {
  return (
    <svg viewBox="0 0 32 32" className={className} width="32" height="32">
      <circle cx="16" cy="16" r="14" fill="#8B1A1A" />
      <circle cx="16" cy="16" r="12" fill="#D4880F" />
      <circle cx="16" cy="16" r="11" fill="#E8A030" />
      {slices >= 2 && <line x1="16" y1="4" x2="16" y2="28" stroke="#8B1A1A" strokeWidth="1" />}
      {slices >= 3 && <line x1="5" y1="22" x2="27" y2="10" stroke="#8B1A1A" strokeWidth="1" />}
      {slices >= 4 && <line x1="5" y1="10" x2="27" y2="22" stroke="#8B1A1A" strokeWidth="1" />}
      <circle cx="11" cy="12" r="1.5" fill="#C0392B" />
      <circle cx="20" cy="14" r="1.5" fill="#C0392B" />
      <circle cx="15" cy="20" r="1.5" fill="#C0392B" />
    </svg>
  );
}

export default function PizzaBuilder({ produtoId, onClose }: PizzaBuilderProps) {
  const { siteInfo } = useRestaurante();
  const { data: produto, isLoading: loadingProduto } = useProdutoDetalhe(produtoId);
  const { data: saboresData, isLoading: loadingSabores } = useSaboresDisponiveis(produtoId);
  const adicionarMutation = useAdicionarCarrinho();

  const modoPreco = siteInfo?.modo_preco_pizza || "mais_caro";
  const ingredientesAdicionaisGlobal: IngredienteAdicional[] = siteInfo?.ingredientes_adicionais_pizza || [];

  // State
  const [selectedTamanho, setSelectedTamanho] = useState<number | null>(null);
  const [selectedSabores, setSelectedSabores] = useState<number[]>([]);
  const [numSabores, setNumSabores] = useState(1);
  const [selectedBorda, setSelectedBorda] = useState<number | null>(null); // null = "Sem Borda"
  const [adicionaisQtd, setAdicionaisQtd] = useState<Map<string, number>>(new Map());
  const [removedIngredientes, setRemovedIngredientes] = useState<Map<number, string[]>>(new Map());
  const [observacoes, setObservacoes] = useState("");
  const [quantity, setQuantity] = useState(1);

  // Accordion open states
  const [tamanhoOpen, setTamanhoOpen] = useState(false);
  const [saboresCountOpen, setSaboresCountOpen] = useState(false);
  const [bordaOpen, setBordaOpen] = useState(false);
  const [recheioOpenIds, setRecheioOpenIds] = useState<number[]>([]);
  const [adicionaisOpen, setAdicionaisOpen] = useState(false);
  const [observacoesOpen, setObservacoesOpen] = useState(false);

  // Busca
  const [buscaSabor, setBuscaSabor] = useState("");
  const [buscaAdicional, setBuscaAdicional] = useState("");

  // Variações agrupadas
  const tamanhos = useMemo(() => (produto?.variacoes_agrupadas?.tamanho || []) as Variacao[], [produto]);
  const bordas = useMemo(() => (produto?.variacoes_agrupadas?.borda || []) as Variacao[], [produto]);
  const sabores = useMemo(() => (saboresData?.sabores || []) as Sabor[], [saboresData]);

  // Sabores filtrados por busca
  const saboresFiltrados = useMemo(() => {
    if (!buscaSabor.trim()) return sabores;
    const termo = buscaSabor.toLowerCase();
    return sabores.filter(s => s.nome.toLowerCase().includes(termo));
  }, [sabores, buscaSabor]);

  // Adicionais filtrados por busca
  const adicionaisFiltrados = useMemo(() => {
    if (!buscaAdicional.trim()) return ingredientesAdicionaisGlobal;
    const termo = buscaAdicional.toLowerCase();
    return ingredientesAdicionaisGlobal.filter(a => a.nome.toLowerCase().includes(termo));
  }, [ingredientesAdicionaisGlobal, buscaAdicional]);

  // Extras selecionados (para exibir tags)
  const extrasSelecionados = useMemo(() => {
    const list: { nome: string; preco: number; qty: number }[] = [];
    Array.from(adicionaisQtd.entries()).forEach(([nome, qty]) => {
      if (qty > 0) {
        const ing = ingredientesAdicionaisGlobal.find(a => a.nome === nome);
        list.push({ nome, preco: ing?.preco || 0, qty });
      }
    });
    return list;
  }, [adicionaisQtd, ingredientesAdicionaisGlobal]);

  // Auto-select
  useEffect(() => {
    if (tamanhos.length > 0 && selectedTamanho === null) setSelectedTamanho(tamanhos[0].id);
  }, [tamanhos, selectedTamanho]);

  useEffect(() => {
    if (selectedSabores.length === 0 && sabores.length > 0) {
      const match = sabores.find(s => s.id === produtoId);
      setSelectedSabores(match ? [match.id] : [sabores[0].id]);
    }
  }, [sabores, produtoId, selectedSabores.length]);

  const maxSabores = useMemo(() => {
    const tam = tamanhos.find(t => t.id === selectedTamanho);
    return tam?.max_sabores || 1;
  }, [tamanhos, selectedTamanho]);

  useEffect(() => { if (numSabores > maxSabores) setNumSabores(maxSabores); }, [maxSabores, numSabores]);
  useEffect(() => {
    if (selectedSabores.length > numSabores) setSelectedSabores(prev => prev.slice(0, numSabores));
  }, [numSabores, selectedSabores.length]);

  const tamSel = useMemo(() => tamanhos.find(t => t.id === selectedTamanho), [tamanhos, selectedTamanho]);
  const bordaSel = useMemo(() => selectedBorda !== null ? bordas.find(b => b.id === selectedBorda) : null, [bordas, selectedBorda]);

  const saboresSelecionadosData = useMemo(() => {
    return selectedSabores.map(id => sabores.find(s => s.id === id)).filter(Boolean) as Sabor[];
  }, [selectedSabores, sabores]);

  const saboresOptions = useMemo(() => {
    const opts = [];
    for (let i = 1; i <= maxSabores; i++) opts.push(i);
    return opts;
  }, [maxSabores]);

  // Toggle recheio accordion por sabor
  const toggleRecheio = (saborId: number) => {
    setRecheioOpenIds(prev =>
      prev.includes(saborId) ? prev.filter(id => id !== saborId) : [...prev, saborId]
    );
  };

  // Preço
  const calcPreco = useCallback((): number => {
    if (!produto) return 0;
    let preco = produto.promocao && produto.preco_promocional ? produto.preco_promocional : produto.preco;

    if (tamSel) preco += tamSel.preco_adicional;

    // Borda selecionada (única)
    if (bordaSel) preco += bordaSel.preco_adicional;

    // Adicionais (ingredientes globais)
    Array.from(adicionaisQtd.entries()).forEach(([nome, qty]) => {
      if (qty > 0) {
        const ing = ingredientesAdicionaisGlobal.find(a => a.nome === nome);
        if (ing) preco += ing.preco * qty;
      }
    });

    return preco;
  }, [produto, tamSel, bordaSel, adicionaisQtd, ingredientesAdicionaisGlobal]);

  const precoTotal = calcPreco() * quantity;

  // Handlers
  const handleToggleSabor = (id: number) => {
    setSelectedSabores(prev => {
      if (prev.includes(id)) {
        if (prev.length <= 1) return prev;
        return prev.filter(x => x !== id);
      }
      if (prev.length >= numSabores) return prev;
      return [...prev, id];
    });
  };

  const handleToggleIngrediente = (saborId: number, ingrediente: string) => {
    setRemovedIngredientes(prev => {
      const next = new Map(prev);
      const removed = next.get(saborId) || [];
      if (removed.includes(ingrediente)) {
        next.set(saborId, removed.filter(i => i !== ingrediente));
      } else {
        next.set(saborId, [...removed, ingrediente]);
      }
      return next;
    });
  };

  const handleAdicionalQtd = (nome: string, delta: number) => {
    setAdicionaisQtd(prev => {
      const next = new Map(prev);
      const current = next.get(nome) || 0;
      const newQty = Math.max(0, current + delta);
      if (newQty === 0) next.delete(nome);
      else next.set(nome, newQty);
      return next;
    });
  };

  const handleRemoveExtra = (nome: string) => {
    setAdicionaisQtd(prev => {
      const next = new Map(prev);
      next.delete(nome);
      return next;
    });
  };

  const handleAddToCart = async () => {
    if (!produto) return;

    const variacoesIds: { variacao_id: number }[] = [];
    if (selectedTamanho) variacoesIds.push({ variacao_id: selectedTamanho });
    if (selectedBorda !== null) variacoesIds.push({ variacao_id: selectedBorda });

    const parts: string[] = [];

    if (selectedSabores.length > 1) {
      parts.push(`Sabores: ${saboresSelecionadosData.map(s => s.nome).join(" / ")}`);
    }

    // Borda
    if (bordaSel) parts.push(`Borda: ${bordaSel.nome}`);

    // Ingredientes removidos
    for (const sabor of saboresSelecionadosData) {
      const removed = removedIngredientes.get(sabor.id) || [];
      if (removed.length > 0) parts.push(`${sabor.nome}: Sem ${removed.join(", ")}`);
    }

    // Adicionais (ingredientes globais)
    const extras: string[] = [];
    Array.from(adicionaisQtd.entries()).forEach(([nome, qty]) => {
      if (qty > 0) extras.push(`${nome}${qty > 1 ? ` ${qty}x` : ""}`);
    });
    if (extras.length > 0) parts.push(`Extras: ${extras.join(", ")}`);

    if (observacoes.trim()) parts.push(observacoes.trim());

    try {
      await adicionarMutation.mutateAsync({
        produto_id: produto.id,
        quantidade: quantity,
        observacao: parts.join(" | ") || undefined,
        variacoes: variacoesIds.length > 0 ? variacoesIds : undefined,
      });
      toast.success(`${produto.nome} adicionado ao carrinho!`);
      onClose();
    } catch {
      toast.error("Erro ao adicionar ao carrinho");
    }
  };

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  // Prevent body scroll
  useEffect(() => {
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, []);

  const isLoading = loadingProduto || loadingSabores;

  return (
    <div className="pizza-builder-overlay" onClick={onClose}>
      <div className="pizza-builder-modal" onClick={e => e.stopPropagation()}>

        {/* ═══ HEADER ═══ */}
        <div className="pb-header">
          <div className="pb-header-content">
            <div className="pb-header-left">
              <h2 className="pb-header-title">
                {tamSel ? `Pizza ${tamSel.nome}` : (produto?.nome || "Monte Sua Pizza")}
                {numSabores > 1 && ` - ${numSabores} Sabores`}
              </h2>
              <div className="pb-header-badges">
                {tamSel && (
                  <span className="pb-header-badge pb-header-badge--size">
                    {getSizeBadge(tamSel.nome)}
                  </span>
                )}
                {numSabores > 1 && (
                  <span className="pb-header-badge pb-header-badge--sabores">
                    <MiniPizzaIcon slices={numSabores} className="pb-header-badge-icon" />
                  </span>
                )}
              </div>
            </div>
            <button className="pb-header-close" onClick={onClose}>
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <div className="text-5xl mb-4 animate-pulse">{"\u{1F355}"}</div>
              <p className="text-gray-500">Carregando montador...</p>
            </div>
          </div>
        ) : (
          <div className="pb-body">

            {/* ═══ COLUNA ESQUERDA ═══ */}
            <div className="pb-col-left">

              {/* Tamanho — botão accordion */}
              {tamanhos.length > 0 && (
                <div className="pb-section">
                  <h3 className="pb-section-label">Escolha um</h3>
                  <div className="pb-accordion">
                    <button
                      className="pb-accordion-trigger"
                      onClick={() => setTamanhoOpen(!tamanhoOpen)}
                    >
                      {tamSel ? (
                        <div className="pb-accordion-selected">
                          <span className="pb-size-badge">{getSizeBadge(tamSel.nome)}</span>
                          <div className="pb-accordion-info">
                            <span className="pb-accordion-name">{tamSel.nome}</span>
                            {tamSel.descricao && <span className="pb-accordion-desc">{tamSel.descricao}</span>}
                          </div>
                        </div>
                      ) : (
                        <span className="pb-accordion-placeholder">Selecione o tamanho</span>
                      )}
                      <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${tamanhoOpen ? "pb-accordion-arrow--open" : ""}`} />
                    </button>
                    <div className={`pb-accordion-list ${tamanhoOpen ? "pb-accordion-list--open" : ""}`}>
                      {tamanhos.map(tam => (
                        <button
                          key={tam.id}
                          onClick={() => { setSelectedTamanho(tam.id); setTamanhoOpen(false); }}
                          className={`pb-accordion-option ${selectedTamanho === tam.id ? "pb-accordion-option--active" : ""}`}
                        >
                          <span className="pb-size-badge">{getSizeBadge(tam.nome)}</span>
                          <div className="pb-accordion-option-info">
                            <span className="pb-accordion-option-name">{tam.nome}</span>
                            <span className="pb-accordion-option-desc">
                              {tam.descricao || `${(tam.max_sabores || 1) > 1 ? `Até ${tam.max_sabores} sabores` : "1 sabor"}`}
                            </span>
                          </div>
                          {selectedTamanho === tam.id && <Check className="w-4 h-4 text-[#8B1A1A] shrink-0" />}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Quantos Sabores — botão accordion */}
              {maxSabores > 1 && (
                <div className="pb-section">
                  <h3 className="pb-section-label">Quantos Sabores</h3>
                  <div className="pb-accordion">
                    <button
                      className="pb-accordion-trigger"
                      onClick={() => setSaboresCountOpen(!saboresCountOpen)}
                    >
                      <div className="pb-accordion-selected">
                        <MiniPizzaIcon slices={numSabores} className="pb-mini-pizza" />
                        <div className="pb-accordion-info">
                          <span className="pb-accordion-name">{numSabores} {numSabores === 1 ? "Sabor" : "Sabores"}</span>
                          <span className="pb-accordion-desc">Pizzas Tradicionais Com {numSabores} {numSabores === 1 ? "Sabor" : "Sabores"}</span>
                        </div>
                      </div>
                      <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${saboresCountOpen ? "pb-accordion-arrow--open" : ""}`} />
                    </button>
                    <div className={`pb-accordion-list ${saboresCountOpen ? "pb-accordion-list--open" : ""}`}>
                      {saboresOptions.map(n => (
                        <button
                          key={n}
                          onClick={() => { setNumSabores(n); setSaboresCountOpen(false); }}
                          className={`pb-accordion-option ${numSabores === n ? "pb-accordion-option--active" : ""}`}
                        >
                          <MiniPizzaIcon slices={n} className="pb-mini-pizza" />
                          <div className="pb-accordion-option-info">
                            <span className="pb-accordion-option-name">{n} {n === 1 ? "Sabor" : "Sabores"}</span>
                            <span className="pb-accordion-option-desc">Pizzas Tradicionais Com {n} {n === 1 ? "Sabor" : "Sabores"}</span>
                          </div>
                          {numSabores === n && <Check className="w-4 h-4 text-[#8B1A1A] shrink-0" />}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Sabores — lista com checkbox visual + busca */}
              <div className="pb-section">
                <h3 className="pb-section-label">
                  Sabores <span className="pb-section-counter">({selectedSabores.length}/{numSabores})</span>
                </h3>
                {/* Busca sabores */}
                {sabores.length > 5 && (
                  <div className="pb-search">
                    <Search className="w-3.5 h-3.5 text-gray-400" />
                    <input
                      type="text"
                      value={buscaSabor}
                      onChange={e => setBuscaSabor(e.target.value)}
                      placeholder="Buscar sabor..."
                      className="pb-search-input"
                    />
                    {buscaSabor && (
                      <button onClick={() => setBuscaSabor("")} className="text-gray-400 hover:text-gray-600">
                        <X className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                )}
                <div className="pb-sabores-grid">
                  {saboresFiltrados.map(sabor => {
                    const isSelected = selectedSabores.includes(sabor.id);
                    const isFull = selectedSabores.length >= numSabores && !isSelected;
                    return (
                      <button
                        key={sabor.id}
                        onClick={() => handleToggleSabor(sabor.id)}
                        disabled={isFull}
                        className={`pb-sabor-item ${isSelected ? "pb-sabor-item--selected" : ""} ${isFull ? "pb-sabor-item--disabled" : ""}`}
                      >
                        <div className="pb-sabor-img-wrap">
                          {sabor.imagem_url ? (
                            <img src={sabor.imagem_url} alt={sabor.nome} className="pb-sabor-img" />
                          ) : (
                            <span className="pb-sabor-emoji">{"\u{1F355}"}</span>
                          )}
                          {isSelected && (
                            <div className="pb-sabor-check">
                              <Check className="w-3.5 h-3.5 text-white" />
                            </div>
                          )}
                        </div>
                        <div className="pb-sabor-info">
                          <span className="pb-sabor-name">{sabor.nome}</span>
                          {sabor.descricao && <span className="pb-sabor-desc">{sabor.descricao}</span>}
                        </div>
                      </button>
                    );
                  })}
                  {saboresFiltrados.length === 0 && (
                    <p className="text-xs text-gray-400 p-2">Nenhum sabor encontrado</p>
                  )}
                </div>
              </div>

              {/* Borda — botão accordion, "Sem Borda" padrão */}
              {bordas.length > 0 && (
                <div className="pb-section">
                  <h3 className="pb-section-label">Borda</h3>
                  <div className="pb-accordion">
                    <button
                      className="pb-accordion-trigger"
                      onClick={() => setBordaOpen(!bordaOpen)}
                    >
                      <div className="pb-accordion-selected">
                        <span className="pb-borda-icon">{"\u{1F9C0}"}</span>
                        <div className="pb-accordion-info">
                          <span className="pb-accordion-name">
                            {bordaSel ? bordaSel.nome : "Sem Borda"}
                          </span>
                          <span className="pb-accordion-desc">
                            {bordaSel && bordaSel.preco_adicional > 0
                              ? `+R$ ${bordaSel.preco_adicional.toFixed(2)}`
                              : "Sem adicional"
                            }
                          </span>
                        </div>
                      </div>
                      <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${bordaOpen ? "pb-accordion-arrow--open" : ""}`} />
                    </button>
                    <div className={`pb-accordion-list ${bordaOpen ? "pb-accordion-list--open" : ""}`}>
                      {/* Opção "Sem Borda" */}
                      <button
                        onClick={() => { setSelectedBorda(null); setBordaOpen(false); }}
                        className={`pb-accordion-option ${selectedBorda === null ? "pb-accordion-option--active" : ""}`}
                      >
                        <span className="pb-borda-icon">{"\u{274C}"}</span>
                        <div className="pb-accordion-option-info">
                          <span className="pb-accordion-option-name">Sem Borda</span>
                          <span className="pb-accordion-option-desc">Borda tradicional</span>
                        </div>
                        {selectedBorda === null && <Check className="w-4 h-4 text-[#8B1A1A] shrink-0" />}
                      </button>
                      {/* Bordas disponíveis */}
                      {bordas.map(borda => (
                        <button
                          key={borda.id}
                          onClick={() => { setSelectedBorda(borda.id); setBordaOpen(false); }}
                          className={`pb-accordion-option ${selectedBorda === borda.id ? "pb-accordion-option--active" : ""}`}
                        >
                          <span className="pb-borda-icon">{"\u{1F9C0}"}</span>
                          <div className="pb-accordion-option-info">
                            <span className="pb-accordion-option-name">{borda.nome}</span>
                            <span className="pb-accordion-option-desc">
                              {borda.preco_adicional > 0 ? `+R$ ${borda.preco_adicional.toFixed(2)}` : "Grátis"}
                            </span>
                          </div>
                          {selectedBorda === borda.id && <Check className="w-4 h-4 text-[#8B1A1A] shrink-0" />}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Preço + Quantidade + Comprar (desktop) */}
              <div className="pb-footer-desktop">
                <div className="pb-price">R$ {precoTotal.toFixed(2)}</div>
                <div className="pb-qty-row">
                  <button className="pb-qty-btn pb-qty-btn--minus" onClick={() => setQuantity(Math.max(1, quantity - 1))}>
                    <Minus className="w-4 h-4" />
                  </button>
                  <span className="pb-qty-value">{quantity}</span>
                  <button className="pb-qty-btn pb-qty-btn--plus" onClick={() => setQuantity(quantity + 1)}>
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                <button
                  onClick={handleAddToCart}
                  disabled={adicionarMutation.isPending || selectedSabores.length === 0}
                  className="pb-buy-btn"
                >
                  {adicionarMutation.isPending ? "Adicionando..." : "Comprar!"}
                </button>
              </div>
            </div>

            {/* ═══ CENTRO: Pizza Visual ═══ */}
            <div className="pb-col-center">
              <PizzaPaddle
                maxSabores={numSabores}
                saboresSelecionados={saboresSelecionadosData.map(s => ({
                  id: s.id,
                  nome: s.nome,
                  imagem_url: s.imagem_url,
                }))}
                tamanhoLabel={tamSel?.nome}
                bordaLabel={bordaSel?.nome || undefined}
              />
            </div>

            {/* ═══ COLUNA DIREITA ═══ */}
            <div className="pb-col-right">

              {/* Recheio — accordion por sabor */}
              {saboresSelecionadosData.length > 0 && saboresSelecionadosData.some(s => (s.ingredientes || []).length > 0) && (
                <div className="pb-section">
                  <h3 className="pb-section-label">Recheio</h3>
                  <div className="pb-ingredientes-wrap">
                    {saboresSelecionadosData.map(sabor => {
                      const ingredientes = sabor.ingredientes || [];
                      if (ingredientes.length === 0) return null;
                      const removedForSabor = removedIngredientes.get(sabor.id) || [];
                      const isOpen = recheioOpenIds.includes(sabor.id);
                      const removedCount = removedForSabor.length;
                      return (
                        <div key={sabor.id} className="pb-accordion" style={{ marginBottom: 6 }}>
                          <button
                            className="pb-accordion-trigger"
                            onClick={() => toggleRecheio(sabor.id)}
                          >
                            <div className="pb-accordion-selected">
                              <span className="pb-borda-icon">{"\u{1F355}"}</span>
                              <div className="pb-accordion-info">
                                <span className="pb-accordion-name">{sabor.nome}</span>
                                <span className="pb-accordion-desc">
                                  {ingredientes.length} ingredientes
                                  {removedCount > 0 && ` (${removedCount} removido${removedCount > 1 ? "s" : ""})`}
                                </span>
                              </div>
                            </div>
                            <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${isOpen ? "pb-accordion-arrow--open" : ""}`} />
                          </button>
                          <div className={`pb-accordion-list ${isOpen ? "pb-accordion-list--open" : ""}`}>
                            <div className="pb-ingredientes-list" style={{ padding: "8px 14px" }}>
                              {ingredientes.map((ing: string) => {
                                const isRemoved = removedForSabor.includes(ing);
                                return (
                                  <label key={ing} className={`pb-ingrediente ${isRemoved ? "pb-ingrediente--removed" : ""}`}>
                                    <input
                                      type="checkbox"
                                      checked={!isRemoved}
                                      onChange={() => handleToggleIngrediente(sabor.id, ing)}
                                      className="pb-checkbox"
                                    />
                                    <span>{ing}</span>
                                  </label>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Ingredientes Extras — accordion com busca + tags dos selecionados */}
              <div className="pb-section">
                <h3 className="pb-section-label">Ingredientes Extras</h3>

                {/* Tags dos extras já selecionados */}
                {extrasSelecionados.length > 0 && (
                  <div className="pb-extras-tags">
                    {extrasSelecionados.map(extra => (
                      <span key={extra.nome} className="pb-extra-tag">
                        <span className="pb-extra-tag-name">
                          {extra.nome}
                          {extra.qty > 1 && ` ${extra.qty}x`}
                        </span>
                        {extra.preco > 0 && (
                          <span className="pb-extra-tag-price">+R$ {(extra.preco * extra.qty).toFixed(2)}</span>
                        )}
                        <button
                          className="pb-extra-tag-remove"
                          onClick={() => handleRemoveExtra(extra.nome)}
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}

                <div className="pb-accordion">
                  <button
                    className="pb-accordion-trigger"
                    onClick={() => setAdicionaisOpen(!adicionaisOpen)}
                  >
                    <div className="pb-accordion-selected">
                      <span className="pb-borda-icon">{"\u{2795}"}</span>
                      <div className="pb-accordion-info">
                        <span className="pb-accordion-name">Adicionar Extras</span>
                        <span className="pb-accordion-desc">
                          {ingredientesAdicionaisGlobal.length > 0
                            ? `${ingredientesAdicionaisGlobal.length} opções disponíveis`
                            : "Nenhum extra cadastrado"
                          }
                        </span>
                      </div>
                    </div>
                    <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${adicionaisOpen ? "pb-accordion-arrow--open" : ""}`} />
                  </button>
                  <div className={`pb-accordion-list ${adicionaisOpen ? "pb-accordion-list--open" : ""}`}>
                    <div style={{ padding: "8px 14px" }}>
                      {/* Busca adicionais */}
                      {ingredientesAdicionaisGlobal.length > 5 && (
                        <div className="pb-search" style={{ marginBottom: 8 }}>
                          <Search className="w-3.5 h-3.5 text-gray-400" />
                          <input
                            type="text"
                            value={buscaAdicional}
                            onChange={e => setBuscaAdicional(e.target.value)}
                            placeholder="Buscar extra..."
                            className="pb-search-input"
                          />
                          {buscaAdicional && (
                            <button onClick={() => setBuscaAdicional("")} className="text-gray-400 hover:text-gray-600">
                              <X className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      )}
                      <div className="pb-adicionais-wrap">
                        {adicionaisFiltrados.map(adic => {
                          const qty = adicionaisQtd.get(adic.nome) || 0;
                          return (
                            <div key={adic.nome} className="pb-adicional">
                              <div className="pb-adicional-info">
                                <span className="pb-adicional-name">{adic.nome}</span>
                                {adic.preco > 0 && (
                                  <span className="pb-adicional-price">+R$ {adic.preco.toFixed(2)}</span>
                                )}
                              </div>
                              <div className="pb-adicional-controls">
                                {qty > 0 && (
                                  <button className="pb-qty-btn pb-qty-btn--minus pb-qty-btn--sm" onClick={() => handleAdicionalQtd(adic.nome, -1)}>
                                    {qty === 1 ? <Trash2 className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                                  </button>
                                )}
                                {qty > 0 && <span className="pb-adicional-qty">{qty}</span>}
                                <button className="pb-qty-btn pb-qty-btn--plus pb-qty-btn--sm" onClick={() => handleAdicionalQtd(adic.nome, 1)}>
                                  <Plus className="w-3 h-3" />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                        {adicionaisFiltrados.length === 0 && ingredientesAdicionaisGlobal.length > 0 && (
                          <p className="text-xs text-gray-400 p-2">Nenhum extra encontrado</p>
                        )}
                        {ingredientesAdicionaisGlobal.length === 0 && (
                          <p className="text-xs text-gray-400 p-2">Nenhum extra cadastrado pelo restaurante</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Observações — accordion */}
              <div className="pb-section">
                <h3 className="pb-section-label">Observações</h3>
                <div className="pb-accordion">
                  <button
                    className="pb-accordion-trigger"
                    onClick={() => setObservacoesOpen(!observacoesOpen)}
                  >
                    <div className="pb-accordion-selected">
                      <span className="pb-borda-icon">{"\u{1F4DD}"}</span>
                      <div className="pb-accordion-info">
                        <span className="pb-accordion-name">
                          {observacoes.trim() ? "Observação adicionada" : "Adicionar observação"}
                        </span>
                        <span className="pb-accordion-desc">
                          {observacoes.trim()
                            ? observacoes.trim().substring(0, 40) + (observacoes.trim().length > 40 ? "..." : "")
                            : "Ex: Bem assada, extra queijo..."
                          }
                        </span>
                      </div>
                    </div>
                    <ChevronDown className={`w-5 h-5 pb-accordion-arrow ${observacoesOpen ? "pb-accordion-arrow--open" : ""}`} />
                  </button>
                  <div className={`pb-accordion-list ${observacoesOpen ? "pb-accordion-list--open" : ""}`}>
                    <div style={{ padding: "8px 14px" }}>
                      <textarea
                        value={observacoes}
                        onChange={e => setObservacoes(e.target.value)}
                        placeholder="Ex: Bem assada, extra queijo..."
                        className="pb-textarea"
                        rows={3}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer mobile */}
        {!isLoading && (
          <div className="pb-footer-mobile">
            <div className="pb-footer-mobile-inner">
              <span className="pb-price pb-price--mobile">R$ {precoTotal.toFixed(2)}</span>
              <div className="pb-qty-row pb-qty-row--mobile">
                <button className="pb-qty-btn pb-qty-btn--minus" onClick={() => setQuantity(Math.max(1, quantity - 1))}>
                  <Minus className="w-4 h-4" />
                </button>
                <span className="pb-qty-value">{quantity}</span>
                <button className="pb-qty-btn pb-qty-btn--plus" onClick={() => setQuantity(quantity + 1)}>
                  <Plus className="w-4 h-4" />
                </button>
              </div>
              <button
                onClick={handleAddToCart}
                disabled={adicionarMutation.isPending || selectedSabores.length === 0}
                className="pb-buy-btn pb-buy-btn--mobile"
              >
                {adicionarMutation.isPending ? "..." : "Comprar!"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
