import { useState, useEffect, useRef } from "react";
import { useLocation } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import { useCriarPedido, useProdutos, useCategorias, useVariacoes, useBuscarCliente } from "@/admin/hooks/useAdminQueries";
import { getVariacoes } from "@/admin/lib/adminApiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
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
import { ArrowLeft, Plus, Minus, Trash2, UserCheck, X as XIcon } from "lucide-react";
import { toast } from "sonner";
import AddressAutocomplete from "@/components/AddressAutocomplete";
import { autocompleteEndereco } from "@/admin/lib/adminApiClient";

interface ItemVariacao {
  tipo: string;
  nome: string;
  preco_adicional: number;
}

interface ItemPedido {
  produto_id: number;
  nome: string;
  preco: number;
  quantidade: number;
  variacoes: ItemVariacao[];
}

export default function NovoPedido() {
  const [, navigate] = useLocation();
  const criarPedido = useCriarPedido();
  const { data: produtos } = useProdutos();
  const { data: categorias } = useCategorias();

  // Parsear ?mesa=X da URL
  const urlParams = new URLSearchParams(window.location.search);
  const mesaParam = urlParams.get("mesa");

  const [tipoEntrega, setTipoEntrega] = useState(mesaParam ? "mesa" : "retirada");
  const [clienteNome, setClienteNome] = useState(mesaParam ? `Mesa ${mesaParam}` : "");
  const [clienteTelefone, setClienteTelefone] = useState("");
  const [enderecoEntrega, setEnderecoEntrega] = useState("");
  const [numeroMesa, setNumeroMesa] = useState(mesaParam || "");
  const [formaPagamento, setFormaPagamento] = useState("");
  const [trocoPara, setTrocoPara] = useState("");
  const [tempoEstimado, setTempoEstimado] = useState("");
  const [observacoes, setObservacoes] = useState("");
  const [itens, setItens] = useState<ItemPedido[]>([]);
  const [catFilter, setCatFilter] = useState<string>("todas");
  const [clienteId, setClienteId] = useState<number | null>(null);
  const [clienteVinculado, setClienteVinculado] = useState<string | null>(null);

  // Debounce telefone para busca de cliente
  const [telDebounced, setTelDebounced] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const limpo = clienteTelefone.replace(/\D/g, "");
      setTelDebounced(limpo.length >= 3 ? limpo : "");
    }, 500);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [clienteTelefone]);

  const { data: clienteLookup } = useBuscarCliente(telDebounced);

  function usarCliente(c: { id: number; nome: string; telefone: string; ultimo_endereco?: string }) {
    setClienteId(c.id);
    setClienteNome(c.nome);
    setClienteVinculado(c.nome);
    if (c.ultimo_endereco && tipoEntrega === "entrega") {
      setEnderecoEntrega(c.ultimo_endereco);
    }
    toast.success(`Cliente "${c.nome}" vinculado`);
  }

  function desvincularCliente() {
    setClienteId(null);
    setClienteVinculado(null);
  }

  // Variação dialog
  const [varDialogOpen, setVarDialogOpen] = useState(false);
  const [varProduto, setVarProduto] = useState<Record<string, unknown> | null>(null);
  const [varList, setVarList] = useState<Record<string, unknown>[]>([]);
  const [varSelecionadas, setVarSelecionadas] = useState<ItemVariacao[]>([]);
  const [varLoading, setVarLoading] = useState(false);

  const produtosFiltrados = (produtos || []).filter((p: Record<string, unknown>) => {
    if (!p.disponivel) return false;
    if (catFilter !== "todas" && p.categoria_id !== Number(catFilter)) return false;
    return true;
  });

  async function handleAddProduct(prod: Record<string, unknown>) {
    // Check if product has variations
    try {
      setVarLoading(true);
      const vars = await getVariacoes(prod.id as number);
      if (Array.isArray(vars) && vars.length > 0) {
        setVarProduto(prod);
        setVarList(vars);
        setVarSelecionadas([]);
        setVarDialogOpen(true);
        return;
      }
    } catch {
      // No variations, add directly
    } finally {
      setVarLoading(false);
    }
    addItemDirect(prod, []);
  }

  function addItemDirect(prod: Record<string, unknown>, variacoes: ItemVariacao[]) {
    const varKey = variacoes.map((v) => v.nome).sort().join(",");
    const existing = itens.find(
      (i) => i.produto_id === prod.id && i.variacoes.map((v) => v.nome).sort().join(",") === varKey
    );
    if (existing) {
      setItens(itens.map((i) =>
        i === existing ? { ...i, quantidade: i.quantidade + 1 } : i
      ));
    } else {
      setItens([...itens, {
        produto_id: prod.id as number,
        nome: prod.nome as string,
        preco: Number(prod.preco),
        quantidade: 1,
        variacoes,
      }]);
    }
  }

  function handleConfirmVariacoes() {
    if (!varProduto) return;
    addItemDirect(varProduto, varSelecionadas);
    setVarDialogOpen(false);
    setVarProduto(null);
  }

  function toggleVariacao(v: Record<string, unknown>) {
    const nome = v.nome as string;
    const exists = varSelecionadas.find((s) => s.nome === nome);
    if (exists) {
      setVarSelecionadas(varSelecionadas.filter((s) => s.nome !== nome));
    } else {
      setVarSelecionadas([...varSelecionadas, {
        tipo: (v.tipo_variacao as string) || "adicional",
        nome,
        preco_adicional: Number(v.preco_adicional || 0),
      }]);
    }
  }

  function updateQtd(idx: number, delta: number) {
    setItens(itens.map((i, iIdx) => {
      if (iIdx !== idx) return i;
      const novaQtd = i.quantidade + delta;
      return novaQtd > 0 ? { ...i, quantidade: novaQtd } : i;
    }));
  }

  function removeItem(idx: number) {
    setItens(itens.filter((_, i) => i !== idx));
  }

  function calcPrecoItem(item: ItemPedido) {
    const varExtra = item.variacoes.reduce((a, v) => a + v.preco_adicional, 0);
    return (item.preco + varExtra) * item.quantidade;
  }

  const valorTotal = itens.reduce((acc, i) => acc + calcPrecoItem(i), 0);

  function handleSubmit() {
    if (!clienteNome.trim()) { toast.error("Informe o nome do cliente"); return; }
    if (itens.length === 0) { toast.error("Adicione pelo menos um item"); return; }
    if (tipoEntrega === "entrega" && !enderecoEntrega.trim()) { toast.error("Informe o endereço"); return; }

    const itensTexto = itens.map((i) => {
      const varTexto = i.variacoes.length > 0
        ? ` (${i.variacoes.map((v) => v.nome).join(", ")})`
        : "";
      return `${i.quantidade}x ${i.nome}${varTexto}`;
    }).join(", ");

    const payload: Record<string, unknown> = {
      tipo_entrega: tipoEntrega,
      cliente_nome: clienteNome.trim(),
      cliente_telefone: clienteTelefone.trim() || undefined,
      endereco_entrega: tipoEntrega === "entrega" ? enderecoEntrega.trim() : undefined,
      numero_mesa: tipoEntrega === "mesa" ? numeroMesa.trim() : undefined,
      itens: itensTexto,
      valor_total: valorTotal,
      forma_pagamento: formaPagamento || undefined,
      observacoes: observacoes.trim() || undefined,
      cliente_id: clienteId || undefined,
    };

    if (formaPagamento === "dinheiro" && trocoPara) {
      payload.troco_para = Number(trocoPara);
    }
    if (tempoEstimado) {
      payload.tempo_estimado = Number(tempoEstimado);
    }

    criarPedido.mutate(
      payload,
      {
        onSuccess: (data) => {
          toast.success(`Pedido #${data.comanda} criado!`);
          navigate("/pedidos");
        },
        onError: () => toast.error("Erro ao criar pedido"),
      }
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={() => navigate("/pedidos")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">Novo Pedido</h2>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* Catálogo */}
          <div className="space-y-4 lg:col-span-2">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Produtos</CardTitle>
                  <Select value={catFilter} onValueChange={setCatFilter}>
                    <SelectTrigger className="w-40 dark-input">
                      <SelectValue />
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
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid gap-2 sm:grid-cols-2">
                  {produtosFiltrados.map((p: Record<string, unknown>) => (
                    <button
                      key={p.id as number}
                      onClick={() => handleAddProduct(p)}
                      disabled={varLoading}
                      className="flex items-center gap-3 rounded-lg border border-[var(--border-subtle)] p-3 text-left transition-colors hover:bg-[var(--bg-card-hover)]"
                    >
                      {p.imagem_url ? (
                        <img
                          src={p.imagem_url as string}
                          alt=""
                          className="h-12 w-12 rounded-lg object-cover"
                        />
                      ) : (
                        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[var(--bg-base)] text-xl">
                          🍽️
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                          {p.nome as string}
                        </p>
                        <p className="text-sm font-semibold text-[var(--cor-primaria)]">
                          R$ {Number(p.preco).toFixed(2)}
                        </p>
                      </div>
                      <Plus className="h-5 w-5 shrink-0 text-[var(--cor-primaria)]" />
                    </button>
                  ))}
                  {produtosFiltrados.length === 0 && (
                    <p className="col-span-2 py-8 text-center text-sm text-[var(--text-muted)]">
                      Nenhum produto disponível
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Sidebar: dados do pedido */}
          <div className="space-y-4">
            {/* Itens selecionados */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">
                  Itens ({itens.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                {itens.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">Clique em um produto para adicionar</p>
                ) : (
                  <div className="space-y-3">
                    {itens.map((item, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="truncate text-sm text-[var(--text-primary)]">{item.nome}</p>
                          {item.variacoes.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-0.5">
                              {item.variacoes.map((v, vi) => (
                                <Badge key={vi} variant="outline" className="text-[10px] border-[var(--border-subtle)] text-[var(--text-muted)]">
                                  {v.nome} {v.preco_adicional > 0 ? `+R$${v.preco_adicional.toFixed(2)}` : ""}
                                </Badge>
                              ))}
                            </div>
                          )}
                          <p className="text-xs text-[var(--text-muted)]">
                            R$ {(item.preco + item.variacoes.reduce((a, v) => a + v.preco_adicional, 0)).toFixed(2)} un.
                          </p>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => updateQtd(idx, -1)}
                          >
                            <Minus className="h-3 w-3" />
                          </Button>
                          <span className="w-6 text-center text-sm text-[var(--text-primary)]">
                            {item.quantidade}
                          </span>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => updateQtd(idx, 1)}
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            onClick={() => removeItem(idx)}
                            className="text-red-400"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                    <div className="flex justify-between border-t border-[var(--border-subtle)] pt-2 text-base font-bold text-[var(--text-primary)]">
                      <span>Total</span>
                      <span>R$ {valorTotal.toFixed(2)}</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Dados do cliente */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Dados do Pedido</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Tipo</label>
                  <Select value={tipoEntrega} onValueChange={setTipoEntrega}>
                    <SelectTrigger className="dark-input">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="retirada">Retirada</SelectItem>
                      <SelectItem value="entrega">Entrega</SelectItem>
                      <SelectItem value="mesa">Mesa</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Nome do Cliente *</label>
                  <Input
                    value={clienteNome}
                    onChange={(e) => setClienteNome(e.target.value)}
                    className="dark-input"
                    placeholder="Nome"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Telefone</label>
                  <Input
                    value={clienteTelefone}
                    onChange={(e) => setClienteTelefone(e.target.value)}
                    className="dark-input"
                    placeholder="(00) 00000-0000"
                  />
                </div>

                {/* Smart Client Lookup */}
                {clienteVinculado ? (
                  <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/10 p-2.5">
                    <UserCheck className="h-4 w-4 text-green-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-green-300 truncate">
                        Cliente vinculado: {clienteVinculado}
                      </p>
                    </div>
                    <Button variant="ghost" size="icon-sm" onClick={desvincularCliente}>
                      <XIcon className="h-3.5 w-3.5 text-green-400" />
                    </Button>
                  </div>
                ) : clienteLookup?.encontrado && !clienteId ? (
                  <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 space-y-2">
                    <p className="text-xs font-medium text-emerald-400">Cliente encontrado!</p>
                    <div className="text-sm text-[var(--text-primary)]">
                      <p className="font-medium">{clienteLookup.cliente.nome}</p>
                      <p className="text-xs text-[var(--text-muted)]">
                        {clienteLookup.cliente.total_pedidos} pedido(s) anteriores
                      </p>
                      {clienteLookup.cliente.ultimo_endereco && (
                        <p className="text-xs text-[var(--text-muted)] truncate mt-0.5">
                          Endereço: {clienteLookup.cliente.ultimo_endereco}
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        className="bg-emerald-600 hover:bg-emerald-700 text-xs h-7"
                        onClick={() => usarCliente(clienteLookup.cliente)}
                      >
                        Usar este cliente
                      </Button>
                    </div>
                  </div>
                ) : null}

                {tipoEntrega === "entrega" && (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-[var(--text-muted)]">Endereço *</label>
                    <AddressAutocomplete
                      value={enderecoEntrega}
                      onChange={setEnderecoEntrega}
                      fetchSuggestions={autocompleteEndereco}
                      placeholder="Rua, número, bairro..."
                      multiline
                      rows={2}
                    />
                  </div>
                )}

                {tipoEntrega === "mesa" && (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-[var(--text-muted)]">Número da Mesa</label>
                    <Input
                      value={numeroMesa}
                      onChange={(e) => setNumeroMesa(e.target.value)}
                      className="dark-input"
                      placeholder="Ex: 5"
                    />
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Pagamento</label>
                  <Select value={formaPagamento} onValueChange={setFormaPagamento}>
                    <SelectTrigger className="dark-input">
                      <SelectValue placeholder="Forma de pagamento" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="dinheiro">Dinheiro</SelectItem>
                      <SelectItem value="pix">PIX</SelectItem>
                      <SelectItem value="credito">Cartão Crédito</SelectItem>
                      <SelectItem value="debito">Cartão Débito</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {formaPagamento === "dinheiro" && (
                  <div className="space-y-1.5">
                    <label className="text-xs font-medium text-[var(--text-muted)]">Troco para (R$)</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={trocoPara}
                      onChange={(e) => setTrocoPara(e.target.value)}
                      className="dark-input"
                      placeholder="Ex: 50.00"
                    />
                    {trocoPara && Number(trocoPara) > valorTotal && (
                      <p className="text-xs text-[var(--text-muted)]">
                        Troco: R$ {(Number(trocoPara) - valorTotal).toFixed(2)}
                      </p>
                    )}
                  </div>
                )}

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Tempo Estimado (min)</label>
                  <Input
                    type="number"
                    min="1"
                    value={tempoEstimado}
                    onChange={(e) => setTempoEstimado(e.target.value)}
                    className="dark-input"
                    placeholder="Ex: 30"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-[var(--text-muted)]">Observações</label>
                  <Textarea
                    value={observacoes}
                    onChange={(e) => setObservacoes(e.target.value)}
                    className="dark-input"
                    placeholder="Observações do pedido..."
                    rows={2}
                  />
                </div>

                <Button
                  className="w-full bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                  onClick={handleSubmit}
                  disabled={criarPedido.isPending || itens.length === 0}
                >
                  Criar Pedido — R$ {valorTotal.toFixed(2)}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Dialog de variações */}
      <Dialog open={varDialogOpen} onOpenChange={setVarDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Selecione as Variações — {varProduto?.nome as string}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 max-h-[400px] overflow-y-auto">
            {(() => {
              const grouped: Record<string, Record<string, unknown>[]> = {};
              for (const v of varList) {
                const tipo = (v.tipo_variacao as string) || "outro";
                if (!grouped[tipo]) grouped[tipo] = [];
                grouped[tipo].push(v);
              }
              return Object.entries(grouped).map(([tipo, vars]) => (
                <div key={tipo}>
                  <p className="text-sm font-medium text-[var(--text-secondary)] capitalize mb-2">{tipo.replace("_", " ")}</p>
                  <div className="space-y-1">
                    {vars.map((v) => {
                      const nome = v.nome as string;
                      const selected = varSelecionadas.some((s) => s.nome === nome);
                      return (
                        <label
                          key={v.id as number}
                          className={`flex items-center justify-between rounded-lg border p-2.5 cursor-pointer transition-colors ${
                            selected
                              ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/5"
                              : "border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)]"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <input
                              type="checkbox"
                              checked={selected}
                              onChange={() => toggleVariacao(v)}
                              className="rounded"
                            />
                            <span className="text-sm text-[var(--text-primary)]">{nome}</span>
                          </div>
                          {Number(v.preco_adicional) > 0 && (
                            <span className="text-sm text-[var(--cor-primaria)]">
                              +R$ {Number(v.preco_adicional).toFixed(2)}
                            </span>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
              ));
            })()}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setVarDialogOpen(false)}>Cancelar</Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleConfirmVariacoes}
            >
              Adicionar ao Pedido
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
