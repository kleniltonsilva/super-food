import { useState, useEffect } from "react";
import { useLocation, useRoute } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useProduto,
  useCategorias,
  useCriarProduto,
  useAtualizarProduto,
  useVariacoes,
  useCriarVariacao,
  useAtualizarVariacao,
  useDeletarVariacao,
  useAplicarMaxSabores,
} from "@/admin/hooks/useAdminQueries";
import { uploadImagem } from "@/admin/lib/adminApiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ArrowLeft, Plus, Trash2, Upload, Loader2, X } from "lucide-react";
import { toast } from "sonner";

interface VariacaoLocal {
  id?: number;
  tipo_variacao: string;
  nome: string;
  descricao: string;
  preco_adicional: number;
  ordem: number;
  max_sabores: number;
  isNew?: boolean;
}

export default function ProdutoForm() {
  const [, navigate] = useLocation();
  const [, paramsEdit] = useRoute("/produtos/:id");
  const prodId = paramsEdit?.id && paramsEdit.id !== "novo" ? Number(paramsEdit.id) : null;
  const isEdit = prodId !== null;

  const { data: produto, isLoading: loadingProduto } = useProduto(prodId || 0);
  const { data: categorias } = useCategorias();
  const { data: variacoesBD } = useVariacoes(prodId || 0);
  const criarProduto = useCriarProduto();
  const atualizarProduto = useAtualizarProduto();
  const criarVariacao = useCriarVariacao();
  const atualizarVariacao = useAtualizarVariacao();
  const deletarVariacao = useDeletarVariacao();

  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [preco, setPreco] = useState("");
  const [categoriaId, setCategoriaId] = useState<string>("");
  const [imagemUrl, setImagemUrl] = useState("");
  const [destaque, setDestaque] = useState(false);
  const [promocao, setPromocao] = useState(false);
  const [precoPromocional, setPrecoPromocional] = useState("");
  const [disponivel, setDisponivel] = useState(true);
  const [estoqueIlimitado, setEstoqueIlimitado] = useState(true);
  const [estoqueQuantidade, setEstoqueQuantidade] = useState("");
  const [ordemExibicao, setOrdemExibicao] = useState("0");
  const [uploading, setUploading] = useState(false);
  const [variacoes, setVariacoes] = useState<VariacaoLocal[]>([]);
  const [variacoesOriginais, setVariacoesOriginais] = useState<VariacaoLocal[]>([]);
  const [ingredientes, setIngredientes] = useState<string[]>([]);
  const [novoIngrediente, setNovoIngrediente] = useState("");
  const aplicarMaxSabores = useAplicarMaxSabores();
  const [saboresDialog, setSaboresDialog] = useState<{ nome: string; max_sabores: number } | null>(null);

  // Populate form when editing
  useEffect(() => {
    if (isEdit && produto) {
      setNome(produto.nome || "");
      setDescricao(produto.descricao || "");
      setPreco(String(produto.preco || ""));
      setCategoriaId(produto.categoria_id ? String(produto.categoria_id) : "");
      setImagemUrl(produto.imagem_url || "");
      setDestaque(!!produto.destaque);
      setPromocao(!!produto.promocao);
      setPrecoPromocional(produto.preco_promocional ? String(produto.preco_promocional) : "");
      setDisponivel(produto.disponivel !== false);
      setEstoqueIlimitado(produto.estoque_ilimitado !== false);
      setEstoqueQuantidade(produto.estoque_quantidade ? String(produto.estoque_quantidade) : "");
      setOrdemExibicao(String(produto.ordem_exibicao ?? 0));
      setIngredientes(produto.ingredientes_json || []);
    }
  }, [isEdit, produto]);

  useEffect(() => {
    if (isEdit && variacoesBD) {
      const mapped = (variacoesBD as Record<string, unknown>[]).map((v) => ({
        id: v.id as number,
        tipo_variacao: (v.tipo_variacao as string) || "tamanho",
        nome: v.nome as string,
        descricao: (v.descricao as string) || "",
        preco_adicional: Number(v.preco_adicional || 0),
        ordem: Number(v.ordem ?? 0),
        max_sabores: Number(v.max_sabores ?? 0),
      }));
      setVariacoes(mapped);
      setVariacoesOriginais(mapped.map((v) => ({ ...v })));
    }
  }, [isEdit, variacoesBD]);

  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const data = await uploadImagem(file);
      setImagemUrl(data.url || data.path || "");
      toast.success("Imagem enviada");
    } catch {
      toast.error("Erro ao enviar imagem");
    } finally {
      setUploading(false);
    }
  }

  function addVariacao() {
    setVariacoes([...variacoes, { tipo_variacao: "tamanho", nome: "", descricao: "", preco_adicional: 0, ordem: 0, max_sabores: 0, isNew: true }]);
  }

  function removeVariacao(idx: number) {
    const v = variacoes[idx];
    if (v.id) {
      deletarVariacao.mutate(v.id, {
        onSuccess: () => toast.success("Variação removida"),
        onError: () => toast.error("Erro ao remover variação"),
      });
    }
    setVariacoes(variacoes.filter((_, i) => i !== idx));
  }

  function updateVariacao(idx: number, field: string, value: string | number) {
    setVariacoes(variacoes.map((v, i) => (i === idx ? { ...v, [field]: value } : v)));
  }

  async function handleSubmit() {
    if (!nome.trim()) { toast.error("Informe o nome do produto"); return; }
    if (!preco || Number(preco) <= 0) { toast.error("Informe um preço válido"); return; }

    const payload: Record<string, unknown> = {
      nome: nome.trim(),
      descricao: descricao.trim() || null,
      preco: Number(preco),
      categoria_id: categoriaId ? Number(categoriaId) : null,
      imagem_url: imagemUrl || null,
      destaque,
      promocao,
      preco_promocional: promocao && precoPromocional ? Number(precoPromocional) : null,
      disponivel,
      estoque_ilimitado: estoqueIlimitado,
      estoque_quantidade: !estoqueIlimitado && estoqueQuantidade ? Number(estoqueQuantidade) : null,
      ordem_exibicao: Number(ordemExibicao) || 0,
      ingredientes_json: ingredientes.length > 0 ? ingredientes : null,
    };

    try {
      if (isEdit) {
        await atualizarProduto.mutateAsync({ id: prodId!, ...payload });
        // Save variações
        for (const v of variacoes) {
          const varPayload: Record<string, unknown> = {
            tipo_variacao: v.tipo_variacao,
            nome: v.nome.trim(),
            descricao: v.descricao.trim() || null,
            preco_adicional: v.preco_adicional,
            ordem: v.ordem,
          };
          if (v.tipo_variacao === "tamanho") {
            varPayload.max_sabores = v.max_sabores || null;
          }

          if (v.isNew && v.nome.trim()) {
            await criarVariacao.mutateAsync({
              produtoId: prodId!,
              ...varPayload,
            });
          } else if (v.id && v.nome.trim()) {
            await atualizarVariacao.mutateAsync({
              id: v.id,
              ...varPayload,
            });
          }
        }
        toast.success("Produto atualizado!");

        // Verifica se max_sabores mudou em algum tamanho — oferece aplicar a todos
        const tamanhoAlterado = variacoes.find((v) => {
          if (v.tipo_variacao !== "tamanho" || !v.max_sabores) return false;
          const original = variacoesOriginais.find((o) => o.id === v.id);
          return original && original.max_sabores !== v.max_sabores;
        });
        if (tamanhoAlterado) {
          setSaboresDialog({ nome: tamanhoAlterado.nome, max_sabores: tamanhoAlterado.max_sabores });
          return; // Não navega ainda — espera resposta do dialog
        }
      } else {
        await criarProduto.mutateAsync(payload);
        toast.success("Produto criado!");
      }
      navigate("/produtos");
    } catch {
      toast.error("Erro ao salvar produto");
    }
  }

  if (isEdit && loadingProduto) {
    return (
      <AdminLayout>
        <div className="space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-64 w-full" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={() => navigate("/produtos")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            {isEdit ? "Editar Produto" : "Novo Produto"}
          </h2>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {/* Form principal */}
          <div className="space-y-4 lg:col-span-2">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Informações</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Nome *</label>
                  <Input
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    className="dark-input"
                    placeholder="Nome do produto"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Descrição</label>
                  <Textarea
                    value={descricao}
                    onChange={(e) => setDescricao(e.target.value)}
                    className="dark-input"
                    placeholder="Descrição do produto..."
                    rows={3}
                  />
                </div>

                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">Preço *</label>
                    <Input
                      type="number"
                      step="0.01"
                      value={preco}
                      onChange={(e) => setPreco(e.target.value)}
                      className="dark-input"
                      placeholder="0.00"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">Categoria</label>
                    <Select value={categoriaId} onValueChange={setCategoriaId}>
                      <SelectTrigger className="dark-input">
                        <SelectValue placeholder="Selecione..." />
                      </SelectTrigger>
                      <SelectContent>
                        {(categorias || []).map((c: Record<string, unknown>) => (
                          <SelectItem key={c.id as number} value={String(c.id)}>
                            {c.nome as string}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">Ordem Exibição</label>
                    <Input
                      type="number"
                      value={ordemExibicao}
                      onChange={(e) => setOrdemExibicao(e.target.value)}
                      className="dark-input"
                      placeholder="0"
                    />
                  </div>
                </div>

                {/* Imagem */}
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">Imagem</label>
                  <div className="flex items-center gap-3">
                    {imagemUrl && (
                      <img src={imagemUrl} alt="" className="h-16 w-16 rounded-lg object-cover" />
                    )}
                    <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[var(--border-subtle)] px-4 py-3 text-sm text-[var(--text-muted)] hover:bg-[var(--bg-card-hover)]">
                      {uploading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      {uploading ? "Enviando..." : "Enviar imagem"}
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleImageUpload}
                        disabled={uploading}
                      />
                    </label>
                  </div>
                </div>

                {/* Ingredientes */}
                <div className="space-y-1.5">
                  <label className="text-sm font-medium text-[var(--text-secondary)]">
                    Ingredientes
                  </label>
                  <p className="text-xs text-[var(--text-muted)]">
                    Ingredientes do produto (usado no montador de pizza para permitir remoção)
                  </p>
                  <div className="flex flex-wrap gap-1.5 mb-2">
                    {ingredientes.map((ing, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium bg-[var(--cor-primaria)]/15 text-[var(--cor-primaria)] border border-[var(--cor-primaria)]/20"
                      >
                        {ing}
                        <button
                          type="button"
                          onClick={() => setIngredientes(ingredientes.filter((_, i) => i !== idx))}
                          className="hover:text-red-500 transition-colors"
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <Input
                      value={novoIngrediente}
                      onChange={(e) => setNovoIngrediente(e.target.value)}
                      className="dark-input"
                      placeholder="Ex: Mussarela, Calabresa..."
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          e.preventDefault();
                          const val = novoIngrediente.trim();
                          if (val && !ingredientes.includes(val)) {
                            setIngredientes([...ingredientes, val]);
                            setNovoIngrediente("");
                          }
                        }
                      }}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const val = novoIngrediente.trim();
                        if (val && !ingredientes.includes(val)) {
                          setIngredientes([...ingredientes, val]);
                          setNovoIngrediente("");
                        }
                      }}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Variações */}
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-[var(--text-primary)]">Variações</CardTitle>
                  <Button variant="outline" size="sm" onClick={addVariacao}>
                    <Plus className="mr-1 h-4 w-4" /> Adicionar
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {variacoes.length === 0 ? (
                  <p className="text-sm text-[var(--text-muted)]">
                    Nenhuma variação. Adicione tamanhos, sabores, etc.
                  </p>
                ) : (
                  <div className="space-y-4">
                    {variacoes.map((v, idx) => (
                      <div key={idx} className="rounded-lg border border-[var(--border-subtle)] p-3 space-y-2">
                        <div className="flex items-end gap-2">
                          <div className="w-32 space-y-1">
                            <label className="text-xs text-[var(--text-muted)]">Tipo</label>
                            <Select
                              value={v.tipo_variacao}
                              onValueChange={(val) => updateVariacao(idx, "tipo_variacao", val)}
                            >
                              <SelectTrigger className="dark-input h-9 text-xs">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="tamanho">Tamanho</SelectItem>
                                <SelectItem value="sabor">Sabor</SelectItem>
                                <SelectItem value="adicional">Adicional</SelectItem>
                                <SelectItem value="borda">Borda</SelectItem>
                                <SelectItem value="ponto_carne">Ponto Carne</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="flex-1 space-y-1">
                            <label className="text-xs text-[var(--text-muted)]">Nome</label>
                            <Input
                              value={v.nome}
                              onChange={(e) => updateVariacao(idx, "nome", e.target.value)}
                              className="dark-input h-9 text-sm"
                              placeholder="Ex: Grande, Calabresa..."
                            />
                          </div>
                          <div className="w-24 space-y-1">
                            <label className="text-xs text-[var(--text-muted)]">+Preço</label>
                            <Input
                              type="number"
                              step="0.01"
                              value={v.preco_adicional}
                              onChange={(e) => updateVariacao(idx, "preco_adicional", Number(e.target.value))}
                              className="dark-input h-9 text-sm"
                            />
                          </div>
                          <div className="w-16 space-y-1">
                            <label className="text-xs text-[var(--text-muted)]">Ordem</label>
                            <Input
                              type="number"
                              value={v.ordem}
                              onChange={(e) => updateVariacao(idx, "ordem", Number(e.target.value))}
                              className="dark-input h-9 text-sm"
                            />
                          </div>
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="shrink-0 text-red-400"
                            onClick={() => removeVariacao(idx)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                        <div className="flex gap-2">
                          <div className="flex-1 space-y-1">
                            <label className="text-xs text-[var(--text-muted)]">Descrição</label>
                            <Input
                              value={v.descricao}
                              onChange={(e) => updateVariacao(idx, "descricao", e.target.value)}
                              className="dark-input h-9 text-sm"
                              placeholder={v.tipo_variacao === "tamanho" ? "Ex: 8 Fatias 35cm" : "Descrição da variação (opcional)"}
                            />
                          </div>
                          {v.tipo_variacao === "tamanho" && (
                            <div className="w-28 space-y-1">
                              <label className="text-xs text-[var(--text-muted)]">Máx Sabores</label>
                              <Input
                                type="number"
                                min="0"
                                value={v.max_sabores}
                                onChange={(e) => updateVariacao(idx, "max_sabores", Number(e.target.value))}
                                className="dark-input h-9 text-sm"
                                placeholder="0"
                              />
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar */}
          <div className="space-y-4">
            <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)]">Configurações</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--text-secondary)]">Disponível</label>
                  <Switch checked={disponivel} onCheckedChange={setDisponivel} />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--text-secondary)]">Destaque</label>
                  <Switch checked={destaque} onCheckedChange={setDestaque} />
                </div>
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--text-secondary)]">Em Promoção</label>
                  <Switch checked={promocao} onCheckedChange={setPromocao} />
                </div>
                {promocao && (
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">
                      Preço Promocional
                    </label>
                    <Input
                      type="number"
                      step="0.01"
                      value={precoPromocional}
                      onChange={(e) => setPrecoPromocional(e.target.value)}
                      className="dark-input"
                      placeholder="0.00"
                    />
                  </div>
                )}

                <div className="border-t border-[var(--border-subtle)] pt-4">
                  <div className="flex items-center justify-between">
                    <label className="text-sm text-[var(--text-secondary)]">Estoque Ilimitado</label>
                    <Switch checked={estoqueIlimitado} onCheckedChange={setEstoqueIlimitado} />
                  </div>
                  {!estoqueIlimitado && (
                    <div className="mt-3 space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">
                        Quantidade em Estoque
                      </label>
                      <Input
                        type="number"
                        min="0"
                        value={estoqueQuantidade}
                        onChange={(e) => setEstoqueQuantidade(e.target.value)}
                        className="dark-input"
                        placeholder="0"
                      />
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Button
              className="w-full bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleSubmit}
              disabled={criarProduto.isPending || atualizarProduto.isPending}
            >
              {isEdit ? "Salvar Alterações" : "Criar Produto"}
            </Button>
          </div>
        </div>
      </div>

      {/* Dialog: aplicar max_sabores a todos os tamanhos com mesmo nome */}
      <AlertDialog open={saboresDialog !== null} onOpenChange={() => { setSaboresDialog(null); navigate("/produtos"); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Aplicar a todas as pizzas?</AlertDialogTitle>
            <AlertDialogDescription>
              Você alterou o máximo de sabores do tamanho <strong>{saboresDialog?.nome}</strong> para <strong>{saboresDialog?.max_sabores}</strong>.
              Deseja aplicar essa regra a todos os produtos que possuem o tamanho &quot;{saboresDialog?.nome}&quot;?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => { setSaboresDialog(null); navigate("/produtos"); }}>
              Apenas este produto
            </AlertDialogCancel>
            <AlertDialogAction
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={() => {
                if (saboresDialog) {
                  aplicarMaxSabores.mutate(
                    { nome_tamanho: saboresDialog.nome, max_sabores: saboresDialog.max_sabores },
                    {
                      onSuccess: (res) => {
                        const r = res as { total?: number };
                        toast.success(`Aplicado a ${r.total || 0} variações "${saboresDialog.nome}"`);
                        setSaboresDialog(null);
                        navigate("/produtos");
                      },
                      onError: () => {
                        toast.error("Erro ao aplicar em massa");
                        setSaboresDialog(null);
                        navigate("/produtos");
                      },
                    }
                  );
                }
              }}
            >
              Aplicar a todas as pizzas
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
