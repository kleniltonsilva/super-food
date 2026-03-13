/**
 * Checkout.tsx — Página de finalização do pedido.
 *
 * Usa React Query (useCarrinho, useEnderecos, useFinalizarPedido, useCriarEndereco)
 * para cache e mutations com invalidação automática.
 * Endereços cacheados por 5min → se voltar ao checkout, não re-busca.
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, MapPin, CreditCard, User, Plus, Search } from "lucide-react";
import { useLocation } from "wouter";
import { autocompleteEndereco, validarEntrega, validarCupom } from "@/lib/apiClient";
import { useCarrinho, useEnderecos, useFinalizarPedido, useCriarEndereco } from "@/hooks/useQueries";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useAuth } from "@/contexts/AuthContext";
import { toast } from "sonner";
import { useState, useEffect, useRef } from "react";

type PaymentMethod = "Dinheiro" | "Cartão de Crédito" | "Cartão de Débito" | "PIX" | "Vale Refeição";
type DeliveryType = "entrega" | "retirada";

interface CartItem {
  produto_id: number;
  nome: string;
  variacoes: { id: number; nome: string }[];
  observacoes: string | null;
  quantidade: number;
  preco_unitario: number;
  subtotal: number;
}

interface Endereco {
  id: number;
  apelido: string | null;
  endereco_completo: string;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  latitude: number | null;
  longitude: number | null;
  padrao: boolean;
}

interface Sugestao {
  place_name: string;
  coordinates: [number, number];
}

export default function Checkout() {
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const { cliente, isLoggedIn } = useAuth();

  const [deliveryType, setDeliveryType] = useState<DeliveryType>("entrega");
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("PIX");

  // React Query: carrinho (staleTime 30s) e endereços (staleTime 5min)
  const { data: carrinhoData, isLoading: loading } = useCarrinho();
  const { data: enderecosData = [] } = useEnderecos(isLoggedIn);
  const finalizarMutation = useFinalizarPedido();
  const criarEnderecoMutation = useCriarEndereco();
  const isProcessing = finalizarMutation.isPending;

  const cartItems: CartItem[] = carrinhoData?.itens || carrinhoData?.itens_json || [];
  const enderecos: Endereco[] = enderecosData;
  const [selectedEnderecoId, setSelectedEnderecoId] = useState<number | null>(null);
  const [showNewAddress, setShowNewAddress] = useState(false);
  const [newEndereco, setNewEndereco] = useState("");
  const [newNumero, setNewNumero] = useState("");
  const [newComplemento, setNewComplemento] = useState("");
  const [newBairro, setNewBairro] = useState("");
  const [newApelido, setNewApelido] = useState("");

  // Dados para não logados
  const [nomeCliente, setNomeCliente] = useState("");
  const [telefoneCliente, setTelefoneCliente] = useState("");
  const [enderecoTexto, setEnderecoTexto] = useState("");

  // Autocomplete
  const [sugestoes, setSugestoes] = useState<Sugestao[]>([]);
  const [showSugestoes, setShowSugestoes] = useState(false);
  const autocompleteTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Coordenadas selecionadas
  const [selectedLat, setSelectedLat] = useState<number | null>(null);
  const [selectedLng, setSelectedLng] = useState<number | null>(null);

  // Taxa de entrega calculada
  const [deliveryFee, setDeliveryFee] = useState<number>(0);
  const [deliveryMsg, setDeliveryMsg] = useState("");
  const [calculandoTaxa, setCalculandoTaxa] = useState(false);

  // Campos do formulário
  const [observacao, setObservacao] = useState("");
  const [cupom, setCupom] = useState("");
  const [cupomValidado, setCupomValidado] = useState<{ valido: boolean; desconto: number; mensagem: string } | null>(null);
  const [validandoCupom, setValidandoCupom] = useState(false);
  const [troco, setTroco] = useState("");

  // Seleciona endereço padrão quando endereços carregam do cache/API
  useEffect(() => {
    if (enderecos.length > 0 && !selectedEnderecoId) {
      const padrao = enderecos.find((e: Endereco) => e.padrao);
      if (padrao) setSelectedEnderecoId(padrao.id);
      else setSelectedEnderecoId(enderecos[0].id);
    }
  }, [enderecos, selectedEnderecoId]);

  // Calcular taxa quando endereço selecionado muda
  useEffect(() => {
    if (deliveryType === "retirada") {
      setDeliveryFee(0);
      setDeliveryMsg("");
      return;
    }

    if (isLoggedIn && selectedEnderecoId) {
      const end = enderecos.find(e => e.id === selectedEnderecoId);
      if (end && end.latitude && end.longitude) {
        calcularTaxaEntrega(end.endereco_completo, end.latitude, end.longitude);
      } else if (end) {
        calcularTaxaEntrega(end.endereco_completo);
      }
    }
  }, [selectedEnderecoId, deliveryType]);

  async function calcularTaxaEntrega(endereco: string, lat?: number, lng?: number) {
    setCalculandoTaxa(true);
    try {
      const result = await validarEntrega({
        endereco: endereco,
        latitude: lat,
        longitude: lng,
      });
      if (result.dentro_zona) {
        setDeliveryFee(result.taxa_entrega);
        setDeliveryMsg(`~${result.tempo_estimado_min} min | ${result.distancia_km.toFixed(1)} km`);
      } else {
        setDeliveryFee(0);
        setDeliveryMsg(result.mensagem || "Fora da zona de entrega");
      }
    } catch {
      setDeliveryFee(0);
      setDeliveryMsg("");
    } finally {
      setCalculandoTaxa(false);
    }
  }

  // Autocomplete de endereço
  function handleEnderecoChange(value: string) {
    setEnderecoTexto(value);
    setSelectedLat(null);
    setSelectedLng(null);
    setDeliveryFee(0);
    setDeliveryMsg("");

    if (autocompleteTimeout.current) clearTimeout(autocompleteTimeout.current);

    if (value.length >= 3) {
      autocompleteTimeout.current = setTimeout(async () => {
        try {
          const result = await autocompleteEndereco(value);
          setSugestoes(result.sugestoes || []);
          setShowSugestoes(true);
        } catch {
          setSugestoes([]);
        }
      }, 400);
    } else {
      setSugestoes([]);
      setShowSugestoes(false);
    }
  }

  function selecionarSugestao(sugestao: Sugestao) {
    setEnderecoTexto(sugestao.place_name);
    setSelectedLat(sugestao.coordinates[1]);
    setSelectedLng(sugestao.coordinates[0]);
    setSugestoes([]);
    setShowSugestoes(false);
    calcularTaxaEntrega(sugestao.place_name, sugestao.coordinates[1], sugestao.coordinates[0]);
  }

  // Autocomplete para novo endereço (logado)
  const [newSugestoes, setNewSugestoes] = useState<Sugestao[]>([]);
  const [showNewSugestoes, setShowNewSugestoes] = useState(false);
  const [newLat, setNewLat] = useState<number | null>(null);
  const [newLng, setNewLng] = useState<number | null>(null);
  const newAutocompleteTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  function handleNewEnderecoChange(value: string) {
    setNewEndereco(value);
    setNewLat(null);
    setNewLng(null);

    if (newAutocompleteTimeout.current) clearTimeout(newAutocompleteTimeout.current);

    if (value.length >= 3) {
      newAutocompleteTimeout.current = setTimeout(async () => {
        try {
          const result = await autocompleteEndereco(value);
          setNewSugestoes(result.sugestoes || []);
          setShowNewSugestoes(true);
        } catch {
          setNewSugestoes([]);
        }
      }, 400);
    } else {
      setNewSugestoes([]);
      setShowNewSugestoes(false);
    }
  }

  function selecionarNewSugestao(sugestao: Sugestao) {
    setNewEndereco(sugestao.place_name);
    setNewLat(sugestao.coordinates[1]);
    setNewLng(sugestao.coordinates[0]);
    setNewSugestoes([]);
    setShowNewSugestoes(false);
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Carregando...</p>
      </div>
    );
  }

  // Bloquear checkout se restaurante fechado
  const isRestauranteClosed = siteInfo && !siteInfo.status_aberto;

  if (cartItems.length === 0) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button variant="ghost" onClick={() => navigate("/cart")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <p className="text-center text-muted-foreground">Seu carrinho está vazio</p>
        </div>
      </div>
    );
  }

  const subtotal = cartItems.reduce((sum, item) => sum + item.subtotal, 0);
  const descontoCupom = cupomValidado?.valido ? cupomValidado.desconto : 0;
  const total = subtotal + (deliveryType === "retirada" ? 0 : deliveryFee) - descontoCupom;

  async function handleValidarCupom() {
    if (!cupom.trim()) { toast.error("Digite o código do cupom"); return; }
    setValidandoCupom(true);
    try {
      const result = await validarCupom(cupom.trim(), subtotal);
      if (result.valido) {
        setCupomValidado({ valido: true, desconto: result.desconto, mensagem: result.mensagem || "Cupom aplicado!" });
        toast.success(result.mensagem || "Cupom aplicado!");
      } else {
        setCupomValidado({ valido: false, desconto: 0, mensagem: result.mensagem || "Cupom inválido" });
        toast.error(result.mensagem || "Cupom inválido");
      }
    } catch {
      setCupomValidado({ valido: false, desconto: 0, mensagem: "Erro ao validar cupom" });
      toast.error("Erro ao validar cupom");
    } finally {
      setValidandoCupom(false);
    }
  }

  // Métodos de pagamento disponíveis
  const paymentMethods: { value: PaymentMethod; label: string }[] = [];
  if (siteInfo?.aceita_pix) paymentMethods.push({ value: "PIX", label: "PIX" });
  if (siteInfo?.aceita_dinheiro) paymentMethods.push({ value: "Dinheiro", label: "Dinheiro" });
  if (siteInfo?.aceita_cartao) {
    paymentMethods.push({ value: "Cartão de Crédito", label: "Cartão de Crédito" });
    paymentMethods.push({ value: "Cartão de Débito", label: "Cartão de Débito" });
  }
  if (siteInfo?.aceita_vale_refeicao) paymentMethods.push({ value: "Vale Refeição", label: "Vale Refeição" });
  if (paymentMethods.length === 0) {
    paymentMethods.push(
      { value: "PIX", label: "PIX" },
      { value: "Dinheiro", label: "Dinheiro" },
      { value: "Cartão de Crédito", label: "Cartão de Crédito" },
    );
  }

  const handleSaveNewAddress = async () => {
    if (!newEndereco.trim()) {
      toast.error("Digite o endereço");
      return;
    }
    try {
      // Mutation invalida cache de endereços automaticamente (useQueries.ts)
      const end = await criarEnderecoMutation.mutateAsync({
        apelido: newApelido || undefined,
        endereco_completo: newEndereco,
        numero: newNumero || undefined,
        complemento: newComplemento || undefined,
        bairro: newBairro || undefined,
        latitude: newLat || undefined,
        longitude: newLng || undefined,
        padrao: enderecos.length === 0,
      });
      setSelectedEnderecoId(end.id);
      setShowNewAddress(false);
      setNewEndereco("");
      setNewNumero("");
      setNewComplemento("");
      setNewBairro("");
      setNewApelido("");
      setNewLat(null);
      setNewLng(null);
      toast.success("Endereço salvo!");
    } catch {
      toast.error("Erro ao salvar endereço");
    }
  };

  const handlePlaceOrder = async () => {
    if (isRestauranteClosed) {
      toast.error("Restaurante fechado. Não é possível realizar pedidos no momento.");
      return;
    }

    if (siteInfo && siteInfo.pedido_minimo > 0 && subtotal < siteInfo.pedido_minimo) {
      toast.error(`Pedido mínimo: R$ ${siteInfo.pedido_minimo.toFixed(2)}`);
      return;
    }

    if (!isLoggedIn) {
      if (!nomeCliente.trim()) { toast.error("Digite seu nome"); return; }
      if (!telefoneCliente.trim()) { toast.error("Digite seu telefone"); return; }
      if (deliveryType === "entrega" && !enderecoTexto.trim()) { toast.error("Digite o endereço de entrega"); return; }
    } else if (deliveryType === "entrega" && !selectedEnderecoId && !enderecoTexto.trim()) {
      toast.error("Selecione ou adicione um endereço de entrega");
      return;
    }

    // Monta endereço e coordenadas
    let enderecoFinal = "";
    let latFinal: number | undefined;
    let lngFinal: number | undefined;

    if (deliveryType === "entrega") {
      if (isLoggedIn && selectedEnderecoId) {
        const end = enderecos.find(e => e.id === selectedEnderecoId);
        if (end) {
          enderecoFinal = end.endereco_completo;
          if (end.numero) enderecoFinal += `, ${end.numero}`;
          if (end.complemento) enderecoFinal += ` - ${end.complemento}`;
          latFinal = end.latitude || undefined;
          lngFinal = end.longitude || undefined;
        }
      } else {
        enderecoFinal = enderecoTexto;
        latFinal = selectedLat || undefined;
        lngFinal = selectedLng || undefined;
      }
    }

    try {
      // Mutation invalida cache do carrinho e pedidos automaticamente
      const result = await finalizarMutation.mutateAsync({
        tipo_entrega: deliveryType === "entrega" ? "entrega" : "retirada",
        forma_pagamento: paymentMethod,
        troco_para: paymentMethod === "Dinheiro" && troco ? parseFloat(troco) : undefined,
        observacoes: observacao || undefined,
        cupom_desconto: cupomValidado?.valido ? cupom : undefined,
        valor_desconto: cupomValidado?.valido ? descontoCupom : undefined,
        cliente_nome: isLoggedIn ? cliente?.nome : nomeCliente,
        cliente_telefone: isLoggedIn ? cliente?.telefone : telefoneCliente,
        endereco_entrega: enderecoFinal || undefined,
        latitude: latFinal,
        longitude: lngFinal,
      });

      toast.success("Pedido realizado com sucesso!");
      if (isLoggedIn) {
        navigate("/orders");
      } else {
        navigate(`/order-success/${result.pedido_id}`);
      }
    } catch {
      toast.error("Erro ao realizar pedido. Tente novamente.");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-4 px-4 md:py-8">
        <Button variant="ghost" onClick={() => navigate("/cart")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-2xl md:text-3xl font-bold mb-6">Checkout</h1>

        {isRestauranteClosed && (
          <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 p-4">
            <p className="font-bold text-red-400 text-lg mb-1">Restaurante fechado</p>
            <p className="text-sm text-red-300">
              No momento não estamos aceitando pedidos.
              {siteInfo?.horario_abertura && siteInfo?.horario_fechamento && (
                <> Horário de funcionamento: <strong>{siteInfo.horario_abertura} às {siteInfo.horario_fechamento}</strong>.</>
              )}
              {siteInfo?.dias_semana_abertos && siteInfo.dias_semana_abertos.length > 0 && (
                <> Dias: <strong>{siteInfo.dias_semana_abertos.join(", ")}</strong>.</>
              )}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Formulário */}
          <div className="lg:col-span-2 space-y-5">

            {/* Dados do Cliente (se não logado) */}
            {!isLoggedIn && (
              <Card className="p-4 md:p-6">
                <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                  <User className="w-5 h-5" />
                  Seus Dados
                </h2>
                <p className="text-sm text-muted-foreground mb-3">
                  <button onClick={() => navigate("/login")} className="underline font-semibold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                    Faça login
                  </button>{" "}
                  para salvar seus dados e acompanhar pedidos.
                </p>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-bold mb-1 block">Nome *</label>
                    <input
                      type="text"
                      value={nomeCliente}
                      onChange={e => setNomeCliente(e.target.value)}
                      placeholder="Seu nome completo"
                      className="dark-input"
                      style={{ "--tw-ring-color": "var(--cor-primaria, #E31A24)" } as React.CSSProperties}
                    />
                  </div>
                  <div>
                    <label className="text-sm font-bold mb-1 block">Telefone *</label>
                    <input
                      type="tel"
                      value={telefoneCliente}
                      onChange={e => setTelefoneCliente(e.target.value)}
                      placeholder="(11) 99999-9999"
                      className="dark-input"
                      style={{ "--tw-ring-color": "var(--cor-primaria, #E31A24)" } as React.CSSProperties}
                    />
                  </div>
                </div>
              </Card>
            )}

            {/* Tipo de Entrega */}
            <Card className="p-4 md:p-6">
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <MapPin className="w-5 h-5" />
                Tipo de Entrega
              </h2>
              <div className="space-y-3">
                <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-[var(--bg-card-hover)]">
                  <input
                    type="radio"
                    name="delivery"
                    value="entrega"
                    checked={deliveryType === "entrega"}
                    onChange={() => setDeliveryType("entrega")}
                  />
                  <div>
                    <div className="font-bold">Entrega em Casa</div>
                    <div className="text-sm text-muted-foreground">
                      {calculandoTaxa
                        ? "Calculando taxa..."
                        : deliveryFee > 0
                          ? `Taxa: R$ ${deliveryFee.toFixed(2)} | ${deliveryMsg}`
                          : `Tempo: ~${siteInfo?.tempo_entrega_estimado || 50} min`}
                    </div>
                  </div>
                </label>
                <label className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-[var(--bg-card-hover)]">
                  <input
                    type="radio"
                    name="delivery"
                    value="retirada"
                    checked={deliveryType === "retirada"}
                    onChange={() => setDeliveryType("retirada")}
                  />
                  <div>
                    <div className="font-bold">Retirada na Loja</div>
                    <div className="text-sm text-muted-foreground">
                      Sem taxa | Tempo: ~{siteInfo?.tempo_retirada_estimado || 20} min
                    </div>
                  </div>
                </label>
              </div>
            </Card>

            {/* Endereço de Entrega */}
            {deliveryType === "entrega" && (
              <Card className="p-4 md:p-6">
                <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                  <MapPin className="w-5 h-5" />
                  Endereço de Entrega
                </h2>

                {isLoggedIn && enderecos.length > 0 ? (
                  <div className="space-y-3">
                    {enderecos.map(end => (
                      <label
                        key={end.id}
                        className={`flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-[var(--bg-card-hover)] ${
                          selectedEnderecoId === end.id ? "border-2 bg-[var(--bg-card-hover)]" : ""
                        }`}
                        style={selectedEnderecoId === end.id ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}
                      >
                        <input
                          type="radio"
                          name="endereco"
                          checked={selectedEnderecoId === end.id}
                          onChange={() => setSelectedEnderecoId(end.id)}
                        />
                        <div>
                          {end.apelido && <div className="font-bold text-sm">{end.apelido}</div>}
                          <div className="text-sm">
                            {end.endereco_completo}
                            {end.numero ? `, ${end.numero}` : ""}
                            {end.complemento ? ` - ${end.complemento}` : ""}
                          </div>
                          {end.bairro && <div className="text-xs text-muted-foreground">{end.bairro}</div>}
                        </div>
                      </label>
                    ))}

                    {!showNewAddress && (
                      <Button variant="outline" size="sm" className="w-full" onClick={() => setShowNewAddress(true)}>
                        <Plus className="w-4 h-4 mr-1" />
                        Novo endereço
                      </Button>
                    )}
                  </div>
                ) : isLoggedIn ? (
                  <div>
                    <p className="text-sm text-muted-foreground mb-3">Nenhum endereço salvo.</p>
                    {!showNewAddress && (
                      <Button variant="outline" size="sm" onClick={() => setShowNewAddress(true)}>
                        <Plus className="w-4 h-4 mr-1" />
                        Adicionar endereço
                      </Button>
                    )}
                  </div>
                ) : (
                  /* Não logado — campo com autocomplete */
                  <div className="relative">
                    <label className="text-sm font-bold mb-1 block">Endereço completo *</label>
                    <div className="relative">
                      <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
                      <input
                        type="text"
                        value={enderecoTexto}
                        onChange={e => handleEnderecoChange(e.target.value)}
                        onBlur={() => setTimeout(() => setShowSugestoes(false), 200)}
                        onFocus={() => sugestoes.length > 0 && setShowSugestoes(true)}
                        placeholder="Digite seu endereço..."
                        className="dark-input pl-10"
                        style={{ "--tw-ring-color": "var(--cor-primaria, #E31A24)" } as React.CSSProperties}
                      />
                    </div>
                    {showSugestoes && sugestoes.length > 0 && (
                      <div data-autocomplete-dropdown className="absolute z-50 w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto">
                        {sugestoes.map((s, i) => (
                          <button
                            key={i}
                            className="w-full text-left px-4 py-3 hover:bg-[var(--bg-card-hover)] text-sm border-b last:border-b-0"
                            onMouseDown={() => selecionarSugestao(s)}
                          >
                            <MapPin className="w-3 h-3 inline mr-2 text-muted-foreground" />
                            {s.place_name}
                          </button>
                        ))}
                      </div>
                    )}
                    {selectedLat && deliveryFee > 0 && (
                      <p className="text-sm mt-2 font-semibold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                        Taxa de entrega: R$ {deliveryFee.toFixed(2)} | {deliveryMsg}
                      </p>
                    )}
                    {selectedLat && deliveryFee === 0 && deliveryMsg && (
                      <p className="text-sm mt-2 text-red-400 font-semibold">{deliveryMsg}</p>
                    )}
                  </div>
                )}

                {/* Form novo endereço (logado) com autocomplete */}
                {isLoggedIn && showNewAddress && (
                  <div className="mt-4 p-4 border border-[var(--border-subtle)] rounded-lg bg-[var(--bg-surface)] space-y-3">
                    <h3 className="font-bold text-sm">Novo endereço</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="col-span-1 md:col-span-2 relative">
                        <label className="text-xs font-bold mb-1 block">Rua / Avenida *</label>
                        <div className="relative">
                          <Search className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
                          <input
                            type="text"
                            value={newEndereco}
                            onChange={e => handleNewEnderecoChange(e.target.value)}
                            onBlur={() => setTimeout(() => setShowNewSugestoes(false), 200)}
                            onFocus={() => newSugestoes.length > 0 && setShowNewSugestoes(true)}
                            placeholder="Digite o endereço..."
                            className="dark-input pl-10 text-sm"
                            style={{ "--tw-ring-color": "var(--cor-primaria, #E31A24)" } as React.CSSProperties}
                          />
                        </div>
                        {showNewSugestoes && newSugestoes.length > 0 && (
                          <div data-autocomplete-dropdown className="absolute z-50 w-full bg-[var(--bg-card)] border border-[var(--border-subtle)] rounded-lg shadow-lg mt-1 max-h-48 overflow-y-auto">
                            {newSugestoes.map((s, i) => (
                              <button
                                key={i}
                                className="w-full text-left px-4 py-3 hover:bg-[var(--bg-card-hover)] text-sm border-b last:border-b-0"
                                onMouseDown={() => selecionarNewSugestao(s)}
                              >
                                <MapPin className="w-3 h-3 inline mr-2 text-muted-foreground" />
                                {s.place_name}
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                      <div>
                        <label className="text-xs font-bold mb-1 block">Número</label>
                        <input type="text" value={newNumero} onChange={e => setNewNumero(e.target.value)}
                          placeholder="123" className="dark-input text-sm" />
                      </div>
                      <div>
                        <label className="text-xs font-bold mb-1 block">Complemento</label>
                        <input type="text" value={newComplemento} onChange={e => setNewComplemento(e.target.value)}
                          placeholder="Apto 302" className="dark-input text-sm" />
                      </div>
                      <div>
                        <label className="text-xs font-bold mb-1 block">Bairro</label>
                        <input type="text" value={newBairro} onChange={e => setNewBairro(e.target.value)}
                          placeholder="Centro" className="dark-input text-sm" />
                      </div>
                      <div>
                        <label className="text-xs font-bold mb-1 block">Apelido</label>
                        <input type="text" value={newApelido} onChange={e => setNewApelido(e.target.value)}
                          placeholder="Casa, Trabalho..." className="dark-input text-sm" />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSaveNewAddress} style={{ background: `var(--cor-primaria, #E31A24)` }} className="text-white">
                        Salvar
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowNewAddress(false)}>
                        Cancelar
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            )}

            {/* Forma de Pagamento */}
            <Card className="p-4 md:p-6">
              <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
                <CreditCard className="w-5 h-5" />
                Forma de Pagamento
              </h2>
              <div className="space-y-3">
                {paymentMethods.map(method => (
                  <label key={method.value} className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-[var(--bg-card-hover)]">
                    <input type="radio" name="payment" value={method.value}
                      checked={paymentMethod === method.value} onChange={() => setPaymentMethod(method.value)} />
                    <span className="font-semibold">{method.label}</span>
                  </label>
                ))}
              </div>

              {paymentMethod === "Dinheiro" && (
                <div className="mt-4">
                  <label className="text-sm font-bold mb-1 block">Troco para (R$):</label>
                  <input type="number" value={troco} onChange={e => setTroco(e.target.value)}
                    placeholder="Ex: 100" className="dark-input" />
                </div>
              )}
            </Card>

            {/* Observações */}
            <Card className="p-4 md:p-6">
              <div className="space-y-4">
                <div>
                  <label className="text-sm font-bold mb-1 block">Cupom de desconto</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={cupom}
                      onChange={e => { setCupom(e.target.value.toUpperCase()); setCupomValidado(null); }}
                      placeholder="Digite o código do cupom"
                      className="dark-input flex-1"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleValidarCupom}
                      disabled={validandoCupom || !cupom.trim()}
                      className="shrink-0"
                    >
                      {validandoCupom ? "..." : "Aplicar"}
                    </Button>
                  </div>
                  {cupomValidado && (
                    <p className={`text-sm mt-1 font-semibold ${cupomValidado.valido ? "text-green-400" : "text-red-400"}`}>
                      {cupomValidado.mensagem}
                      {cupomValidado.valido && ` (-R$ ${cupomValidado.desconto.toFixed(2)})`}
                    </p>
                  )}
                </div>
                <div>
                  <label className="text-sm font-bold mb-1 block">Observações</label>
                  <textarea value={observacao} onChange={e => setObservacao(e.target.value)}
                    placeholder="Ex: Campainha estragada, apto 302..." className="dark-input" rows={3} />
                </div>
              </div>
            </Card>
          </div>

          {/* Resumo */}
          <div>
            <Card className="p-4 md:p-6 sticky top-4">
              <h2 className="text-lg font-bold mb-4">Resumo do Pedido</h2>

              <div className="space-y-3 mb-4 pb-4 border-b max-h-64 overflow-y-auto">
                {cartItems.map((item, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <div>
                      <span>{item.nome} x{item.quantidade}</span>
                      {item.variacoes && item.variacoes.length > 0 && (
                        <p className="text-xs text-muted-foreground">
                          {item.variacoes.map(v => v.nome).join(", ")}
                        </p>
                      )}
                    </div>
                    <span className="font-bold">R$ {item.subtotal.toFixed(2)}</span>
                  </div>
                ))}
              </div>

              <div className="space-y-2 mb-4 pb-4 border-b">
                <div className="flex items-center justify-between">
                  <span>Subtotal:</span>
                  <span className="font-bold">R$ {subtotal.toFixed(2)}</span>
                </div>
                {deliveryType === "entrega" && (
                  <div className="flex items-center justify-between">
                    <span>Entrega:</span>
                    <span className="font-bold">
                      {calculandoTaxa ? "..." : deliveryFee > 0 ? `R$ ${deliveryFee.toFixed(2)}` : "A calcular"}
                    </span>
                  </div>
                )}
                {descontoCupom > 0 && (
                  <div className="flex items-center justify-between text-green-400">
                    <span>Desconto (cupom):</span>
                    <span className="font-bold">-R$ {descontoCupom.toFixed(2)}</span>
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between mb-6 text-lg">
                <span className="font-bold">Total:</span>
                <span className="font-extrabold" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                  R$ {total.toFixed(2)}
                </span>
              </div>

              <Button
                onClick={handlePlaceOrder}
                disabled={isProcessing || !!isRestauranteClosed}
                className="w-full py-6 text-lg font-bold text-white disabled:opacity-50"
                style={{ background: isRestauranteClosed ? undefined : `var(--cor-primaria, #E31A24)` }}
              >
                {isProcessing ? "Processando..." : isRestauranteClosed ? "Restaurante Fechado" : "Confirmar Pedido"}
              </Button>

              <Button variant="outline" className="w-full mt-2" onClick={() => navigate("/cart")} disabled={isProcessing}>
                Voltar ao Carrinho
              </Button>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
