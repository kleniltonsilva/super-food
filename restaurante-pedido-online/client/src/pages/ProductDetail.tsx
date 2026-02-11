import { useParams, useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Plus, Minus, ChevronRight, ChevronLeft, X } from "lucide-react";
import { useState, useEffect } from "react";
import { getProdutoDetalhe, adicionarAoCarrinho, getSaboresDisponiveis, getProdutos } from "@/lib/apiClient";
import { useRestaurante, type SiteInfo } from "@/contexts/RestauranteContext";
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

export default function ProductDetail() {
  const params = useParams();
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const productId = parseInt(params?.id || "0");

  const [produto, setProduto] = useState<ProdutoDetalhado | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);

  const [quantity, setQuantity] = useState(1);
  const [selectedTamanho, setSelectedTamanho] = useState<number | null>(null);
  const [selectedBorda, setSelectedBorda] = useState<number | null>(null);
  const [selectedAdicionais, setSelectedAdicionais] = useState<number[]>([]);
  const [selectedPontoCarne, setSelectedPontoCarne] = useState<number | null>(null);
  const [selectedSabores, setSelectedSabores] = useState<number[]>([]);
  const [observacoes, setObservacoes] = useState("");

  // Stepper
  const [currentStep, setCurrentStep] = useState(0);
  const [useStepper, setUseStepper] = useState(false);
  const [maxSabores, setMaxSabores] = useState(1);

  // Sabores e bebidas
  const [saboresDisp, setSaboresDisp] = useState<Sabor[]>([]);
  const [bebidas, setBebidas] = useState<Bebida[]>([]);
  const [showBebidaModal, setShowBebidaModal] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        const data = await getProdutoDetalhe(productId);
        setProduto(data);

        const tamanhos = data.variacoes_agrupadas?.tamanho || [];
        if (tamanhos.length > 0) {
          setSelectedTamanho(tamanhos[0].id);
          // Verifica se algum tamanho tem max_sabores > 1
          const hasMultiSabor = tamanhos.some((t: Variacao) => (t.max_sabores || 1) > 1);
          if (hasMultiSabor) {
            setUseStepper(true);
            setMaxSabores(tamanhos[0].max_sabores || 1);
            // Carrega sabores
            const sabData = await getSaboresDisponiveis(productId);
            setSaboresDisp(sabData.sabores || []);
            // Seleciona o produto atual como primeiro sabor
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

  // Carrega bebidas para sugestão
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

  // Atualiza max_sabores quando troca tamanho
  useEffect(() => {
    if (!produto || !useStepper) return;
    const tamanhos = produto.variacoes_agrupadas?.tamanho || [];
    const tam = tamanhos.find(t => t.id === selectedTamanho);
    if (tam) {
      const newMax = tam.max_sabores || 1;
      setMaxSabores(newMax);
      // Limita sabores selecionados se necessário
      if (selectedSabores.length > newMax) {
        setSelectedSabores(prev => prev.slice(0, newMax));
      }
    }
  }, [selectedTamanho, produto, useStepper]);

  const handleToggleAdicional = (id: number) => {
    setSelectedAdicionais(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleToggleSabor = (id: number) => {
    setSelectedSabores(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      if (prev.length >= maxSabores) return prev; // Limite atingido
      return [...prev, id];
    });
  };

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

    const adicionais = produto.variacoes_agrupadas?.adicional || [];
    for (const id of selectedAdicionais) {
      const ad = adicionais.find(a => a.id === id);
      if (ad) preco += ad.preco_adicional;
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
        variacoesIds.push({ variacao_id: id });
      }

      // Monta observação com sabores selecionados
      let obs = observacoes;
      if (useStepper && selectedSabores.length > 1) {
        const nomesSabores = selectedSabores.map(sid => {
          const s = saboresDisp.find(sb => sb.id === sid);
          return s ? s.nome : "";
        }).filter(Boolean);
        obs = `Sabores: ${nomesSabores.join(" / ")}${observacoes ? ` | ${observacoes}` : ""}`;
      }

      await adicionarAoCarrinho({
        produto_id: produto.id,
        quantidade: quantity,
        observacao: obs || undefined,
        variacoes: variacoesIds.length > 0 ? variacoesIds : undefined,
      });

      toast.success(`${produto.nome} adicionado ao carrinho!`);

      // Mostra sugestão de bebida se disponível
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
      await adicionarAoCarrinho({
        produto_id: bebida.id,
        quantidade: 1,
      });
      toast.success(`${bebida.nome} adicionado!`);
    } catch {
      toast.error("Erro ao adicionar bebida");
    }
    setShowBebidaModal(false);
    navigate("/cart");
  };

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

  const precoUnit = calcPreco();
  const tamanhos = produto.variacoes_agrupadas?.tamanho || [];
  const bordas = produto.variacoes_agrupadas?.borda || [];
  const adicionais = produto.variacoes_agrupadas?.adicional || [];
  const pontoCarne = produto.variacoes_agrupadas?.ponto_carne || [];

  // Steps para stepper: 1-Tamanho, 2-Sabores, 3-Borda, 4-Adicionais, 5-Confirmar
  const steps = useStepper
    ? [
        { label: "Tamanho", show: tamanhos.length > 0 },
        { label: "Sabores", show: maxSabores > 1 },
        { label: "Borda", show: bordas.length > 0 },
        { label: "Adicionais", show: adicionais.length > 0 },
        { label: "Confirmar", show: true },
      ].filter(s => s.show)
    : [];

  const canNextStep = () => {
    if (!useStepper) return true;
    const stepLabel = steps[currentStep]?.label;
    if (stepLabel === "Tamanho") return selectedTamanho !== null;
    if (stepLabel === "Sabores") return selectedSabores.length >= 1;
    return true;
  };

  // Render step content
  function renderStepContent() {
    const stepLabel = steps[currentStep]?.label;

    if (stepLabel === "Tamanho") {
      return (
        <div>
          <h3 className="text-lg font-bold mb-3">Escolha o Tamanho</h3>
          <div className="grid grid-cols-2 gap-3">
            {tamanhos.map(tam => {
              const precoTam = produto!.preco + tam.preco_adicional;
              return (
                <button
                  key={tam.id}
                  onClick={() => setSelectedTamanho(tam.id)}
                  className={`p-4 border rounded-lg transition-all text-left ${
                    selectedTamanho === tam.id
                      ? "border-2 bg-[var(--bg-card-hover)]"
                      : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                  }`}
                  style={selectedTamanho === tam.id ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
                >
                  <div className="font-bold">{tam.nome}</div>
                  <div className="text-sm text-muted-foreground">R$ {precoTam.toFixed(2)}</div>
                  {(tam.max_sabores || 1) > 1 && (
                    <div className="text-xs mt-1" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                      Até {tam.max_sabores} sabores
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    if (stepLabel === "Sabores") {
      return (
        <div>
          <h3 className="text-lg font-bold mb-1">Escolha os Sabores</h3>
          <p className="text-sm text-muted-foreground mb-3">
            Selecionados: {selectedSabores.length}/{maxSabores}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-80 overflow-y-auto">
            {saboresDisp.map(sabor => (
              <button
                key={sabor.id}
                onClick={() => handleToggleSabor(sabor.id)}
                disabled={!selectedSabores.includes(sabor.id) && selectedSabores.length >= maxSabores}
                className={`p-3 border rounded-lg transition-all text-left flex items-center gap-3 ${
                  selectedSabores.includes(sabor.id)
                    ? "border-2 bg-[var(--bg-card-hover)]"
                    : selectedSabores.length >= maxSabores
                    ? "border-[var(--border-subtle)] opacity-50"
                    : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                }`}
                style={selectedSabores.includes(sabor.id) ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
              >
                <div className="w-12 h-12 bg-[var(--bg-card-hover)] rounded-lg flex items-center justify-center text-2xl shrink-0">
                  {sabor.imagem_url ? (
                    <img src={sabor.imagem_url} alt={sabor.nome} className="w-full h-full object-cover rounded-lg" />
                  ) : (
                    getEmojiByTipo(siteInfo)
                  )}
                </div>
                <div>
                  <div className="font-bold text-sm">{sabor.nome}</div>
                  {sabor.descricao && (
                    <div className="text-xs text-muted-foreground line-clamp-1">{sabor.descricao}</div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (stepLabel === "Borda") {
      return (
        <div>
          <h3 className="text-lg font-bold mb-3">Escolha a Borda</h3>
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
      );
    }

    if (stepLabel === "Adicionais") {
      return (
        <div>
          <h3 className="text-lg font-bold mb-3">Adicionais (opcional)</h3>
          <div className="space-y-2">
            {adicionais.map(adic => (
              <button
                key={adic.id}
                onClick={() => handleToggleAdicional(adic.id)}
                className={`w-full p-3 border rounded-lg text-left transition-all flex justify-between items-center ${
                  selectedAdicionais.includes(adic.id)
                    ? "border-2 bg-green-900/15 border-green-600"
                    : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                }`}
              >
                <span className="font-semibold text-sm">{adic.nome}</span>
                <span className="text-sm">
                  {adic.preco_adicional > 0 ? `+R$ ${adic.preco_adicional.toFixed(2)}` : "Grátis"}
                </span>
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (stepLabel === "Confirmar") {
      const tamSel = tamanhos.find(t => t.id === selectedTamanho);
      const bordaSel = bordas.find(b => b.id === selectedBorda);
      const sabNomes = selectedSabores.map(sid => saboresDisp.find(s => s.id === sid)?.nome).filter(Boolean);
      const adicNomes = selectedAdicionais.map(aid => adicionais.find(a => a.id === aid)?.nome).filter(Boolean);

      return (
        <div>
          <h3 className="text-lg font-bold mb-3">Resumo do Pedido</h3>
          <div className="space-y-3 bg-[var(--bg-surface)] rounded-lg p-4">
            <div className="flex justify-between">
              <span className="font-bold">{produto!.nome}</span>
            </div>
            {tamSel && (
              <div className="flex justify-between text-sm">
                <span>Tamanho: {tamSel.nome}</span>
                <span>R$ {(produto!.preco + tamSel.preco_adicional).toFixed(2)}</span>
              </div>
            )}
            {sabNomes.length > 1 && (
              <div className="text-sm">
                <span>Sabores: {sabNomes.join(" / ")}</span>
              </div>
            )}
            {bordaSel && bordaSel.preco_adicional > 0 && (
              <div className="flex justify-between text-sm">
                <span>Borda: {bordaSel.nome}</span>
                <span>+R$ {bordaSel.preco_adicional.toFixed(2)}</span>
              </div>
            )}
            {adicNomes.length > 0 && (
              <div className="text-sm">
                <span>Adicionais: {adicNomes.join(", ")}</span>
              </div>
            )}
          </div>

          <div className="mt-4">
            <label className="text-sm font-bold mb-2 block">Observações (opcional)</label>
            <textarea
              value={observacoes}
              onChange={e => setObservacoes(e.target.value)}
              placeholder="Ex: Sem cebola, extra queijo..."
              className="w-full px-4 py-2 dark-input"
              rows={2}
            />
          </div>

          <div className="mt-4 flex items-center gap-4">
            <span className="text-sm font-bold">Quantidade:</span>
            <div className="flex items-center border rounded-lg overflow-hidden">
              <button className="px-3 py-2 hover:bg-[var(--bg-card-hover)]" onClick={() => setQuantity(Math.max(1, quantity - 1))}>
                <Minus className="w-4 h-4" />
              </button>
              <span className="px-4 py-2 font-bold">{quantity}</span>
              <button className="px-3 py-2 hover:bg-[var(--bg-card-hover)]" onClick={() => setQuantity(quantity + 1)}>
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      );
    }

    return null;
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 px-4">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar ao Cardápio
        </Button>

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

            {/* ===== MODO STEPPER (PIZZA) ===== */}
            {useStepper ? (
              <div>
                {/* Progress indicator */}
                <div className="flex items-center gap-2 mb-6">
                  {steps.map((step, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                          i === currentStep
                            ? "text-white"
                            : i < currentStep
                            ? "bg-green-500 text-white"
                            : "bg-[var(--bg-card-hover)] text-[var(--text-muted)]"
                        }`}
                        style={i === currentStep ? { background: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        {i < currentStep ? "✓" : i + 1}
                      </div>
                      <span className={`text-xs hidden sm:inline ${i === currentStep ? "font-bold" : "text-muted-foreground"}`}>
                        {step.label}
                      </span>
                      {i < steps.length - 1 && <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />}
                    </div>
                  ))}
                </div>

                {/* Step content */}
                {renderStepContent()}

                {/* Navigation buttons */}
                <div className="flex justify-between mt-6">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                    disabled={currentStep === 0}
                  >
                    <ChevronLeft className="w-4 h-4 mr-1" />
                    Voltar
                  </Button>

                  {currentStep < steps.length - 1 ? (
                    <Button
                      onClick={() => setCurrentStep(currentStep + 1)}
                      disabled={!canNextStep()}
                      style={{ background: `var(--cor-primaria, #E31A24)`, color: "white" }}
                    >
                      Próximo
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  ) : (
                    <div className="text-right">
                      <div className="text-2xl font-extrabold mb-2" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                        R$ {(precoUnit * quantity).toFixed(2)}
                      </div>
                      <Button
                        onClick={handleAddToCart}
                        disabled={adding}
                        className="py-4 px-8 text-lg font-bold text-white"
                        style={{ background: `var(--cor-primaria, #E31A24)` }}
                      >
                        {adding ? "Adicionando..." : "Adicionar ao Carrinho"}
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* ===== MODO CLÁSSICO (SEM STEPPER) ===== */
              <>
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
                    <h3 className="text-lg font-bold mb-3">Adicionais</h3>
                    <div className="space-y-2">
                      {adicionais.map(adic => (
                        <button
                          key={adic.id}
                          onClick={() => handleToggleAdicional(adic.id)}
                          className={`w-full p-3 border rounded-lg text-left transition-all flex justify-between items-center ${
                            selectedAdicionais.includes(adic.id)
                              ? "border-2 bg-green-900/15 border-green-600"
                              : "border-[var(--border-subtle)] hover:border-[rgba(255,255,255,0.15)]"
                          }`}
                        >
                          <span className="font-semibold text-sm">{adic.nome}</span>
                          <span className="text-sm">
                            {adic.preco_adicional > 0 ? `+R$ ${adic.preco_adicional.toFixed(2)}` : "Grátis"}
                          </span>
                        </button>
                      ))}
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
                    <span className="text-sm font-bold">Quantidade:</span>
                    <div className="flex items-center border rounded-lg overflow-hidden">
                      <button className="px-3 py-2 hover:bg-[var(--bg-card-hover)]" onClick={() => setQuantity(Math.max(1, quantity - 1))}>
                        <Minus className="w-4 h-4" />
                      </button>
                      <span className="px-4 py-2 font-bold">{quantity}</span>
                      <button className="px-3 py-2 hover:bg-[var(--bg-card-hover)]" onClick={() => setQuantity(quantity + 1)}>
                        <Plus className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="border-t pt-4">
                    <div className="flex items-center justify-between mb-4">
                      <span className="text-lg font-bold">Total:</span>
                      <span className="text-2xl font-extrabold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                        R$ {(precoUnit * quantity).toFixed(2)}
                      </span>
                    </div>

                    <Button
                      onClick={handleAddToCart}
                      disabled={adding}
                      className="w-full py-6 text-lg font-bold text-white"
                      style={{ background: `var(--cor-primaria, #E31A24)` }}
                    >
                      {adding ? "Adicionando..." : "Adicionar ao Carrinho"}
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
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
