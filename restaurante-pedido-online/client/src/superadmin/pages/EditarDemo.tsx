import { useState } from "react";
import { useLocation, useParams } from "wouter";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useDemo,
  useAtualizarDemo,
  useAtualizarProdutoDemo,
  useAtualizarSiteConfigDemo,
} from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Save, ExternalLink, Upload, ImageIcon } from "lucide-react";
import { toast } from "sonner";

type TabId = "visual" | "cardapio" | "config" | "preview";

export default function EditarDemo() {
  const params = useParams<{ id: string }>();
  const demoId = params.id ? parseInt(params.id) : null;
  const [, navigate] = useLocation();
  const { data: demo, isLoading } = useDemo(demoId);

  const atualizarDemoMutation = useAtualizarDemo();
  const atualizarProdutoMutation = useAtualizarProdutoDemo();
  const atualizarSiteConfigMutation = useAtualizarSiteConfigDemo();

  const [activeTab, setActiveTab] = useState<TabId>("visual");

  // Visual form state
  const [logoUrl, setLogoUrl] = useState("");
  const [bannerUrl, setBannerUrl] = useState("");
  const [corPrimaria, setCorPrimaria] = useState("");
  const [corSecundaria, setCorSecundaria] = useState("");

  // Editing product
  const [editingProduct, setEditingProduct] = useState<number | null>(null);
  const [editNome, setEditNome] = useState("");
  const [editPreco, setEditPreco] = useState("");
  const [editImagem, setEditImagem] = useState("");

  // Config form
  const [editNomeFantasia, setEditNomeFantasia] = useState("");

  // Initialize form when data loads
  if (demo && !logoUrl && !corPrimaria) {
    if (demo.site_config) {
      setLogoUrl(demo.site_config.logo_url || "");
      setBannerUrl(demo.site_config.banner_principal_url || "");
      setCorPrimaria(demo.site_config.tema_cor_primaria || "#E31A24");
      setCorSecundaria(demo.site_config.tema_cor_secundaria || "#1A1A2E");
    }
    setEditNomeFantasia(demo.nome_fantasia || "");
  }

  if (isLoading || !demo) {
    return (
      <SuperAdminLayout>
        <div className="flex items-center justify-center py-12">
          <span className="text-[var(--sa-text-muted)]">Carregando...</span>
        </div>
      </SuperAdminLayout>
    );
  }

  function handleSaveVisual() {
    if (!demoId) return;
    const payload: Record<string, unknown> = {};
    if (logoUrl !== (demo.site_config?.logo_url || "")) payload.logo_url = logoUrl || null;
    if (bannerUrl !== (demo.site_config?.banner_principal_url || "")) payload.banner_principal_url = bannerUrl || null;
    if (corPrimaria !== (demo.site_config?.tema_cor_primaria || "")) payload.tema_cor_primaria = corPrimaria;
    if (corSecundaria !== (demo.site_config?.tema_cor_secundaria || "")) payload.tema_cor_secundaria = corSecundaria;

    if (Object.keys(payload).length === 0) {
      toast.info("Nenhuma alteração");
      return;
    }

    atualizarSiteConfigMutation.mutate(
      { demoId, payload },
      {
        onSuccess: () => toast.success("Visual atualizado!"),
        onError: () => toast.error("Erro ao atualizar visual"),
      }
    );
  }

  function handleSaveConfig() {
    if (!demoId) return;
    const payload: Record<string, unknown> = {};
    if (editNomeFantasia !== demo.nome_fantasia) payload.nome_fantasia = editNomeFantasia;

    if (Object.keys(payload).length === 0) {
      toast.info("Nenhuma alteração");
      return;
    }

    atualizarDemoMutation.mutate(
      { id: demoId, payload },
      {
        onSuccess: () => toast.success("Config atualizada!"),
        onError: () => toast.error("Erro ao atualizar config"),
      }
    );
  }

  function startEditProduct(produto: any) {
    setEditingProduct(produto.id);
    setEditNome(produto.nome);
    setEditPreco(String(produto.preco));
    setEditImagem(produto.imagem_url || "");
  }

  function handleSaveProduct() {
    if (!demoId || !editingProduct) return;
    const payload: Record<string, unknown> = {};
    if (editNome) payload.nome = editNome;
    if (editPreco) payload.preco = parseFloat(editPreco);
    if (editImagem !== undefined) payload.imagem_url = editImagem || null;

    atualizarProdutoMutation.mutate(
      { demoId, produtoId: editingProduct, payload },
      {
        onSuccess: () => {
          toast.success("Produto atualizado!");
          setEditingProduct(null);
        },
        onError: () => toast.error("Erro ao atualizar produto"),
      }
    );
  }

  async function handleUploadImage(
    file: File,
    onSuccess: (url: string) => void,
    tipo: string = "produto"
  ) {
    if (!demo?.id) {
      toast.error("Demo não carregado");
      return;
    }
    const formData = new FormData();
    formData.append("arquivo", file);
    formData.append("tipo", tipo);
    formData.append("restaurante_id", String(demo.id));
    try {
      const token = localStorage.getItem("sf_superadmin_token");
      const res = await fetch("/api/upload/admin/imagem", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        toast.error(err.detail || "Erro no upload");
        return;
      }
      const data = await res.json();
      if (data.url) {
        onSuccess(data.url);
        toast.success("Imagem enviada!");
      } else {
        toast.error("Erro no upload");
      }
    } catch {
      toast.error("Erro no upload");
    }
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: "visual", label: "Visual" },
    { id: "cardapio", label: "Cardápio" },
    { id: "config", label: "Config" },
    { id: "preview", label: "Preview" },
  ];

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/demos")}
              className="text-[var(--sa-text-muted)]"
            >
              <ArrowLeft className="w-4 h-4 mr-1" />
              Demos
            </Button>
            <h1 className="text-xl font-bold text-[var(--sa-text-primary)]">
              {demo.nome_fantasia}
            </h1>
            <span className="text-xs text-[var(--sa-text-muted)]">
              {demo.codigo_acesso}
            </span>
          </div>
          <Button
            size="sm"
            variant="outline"
            className="border-[var(--sa-border)] text-[var(--sa-text-muted)]"
            onClick={() => window.open(`/cliente/${demo.codigo_acesso}`, "_blank")}
          >
            <ExternalLink className="w-4 h-4 mr-1" />
            Ver Site
          </Button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 border-b border-[var(--sa-border)]">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                activeTab === tab.id
                  ? "border-[var(--sa-accent)] text-[var(--sa-accent)]"
                  : "border-transparent text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab: Visual */}
        {activeTab === "visual" && (
          <Card className="p-6 border-[var(--sa-border)] bg-[var(--sa-bg-surface)] space-y-5">
            <h2 className="text-lg font-bold text-[var(--sa-text-primary)]">Aparência do Site</h2>

            {/* Logo */}
            <div>
              <label className="text-sm font-semibold text-[var(--sa-text-primary)] mb-1 block">Logo URL</label>
              <div className="flex gap-2">
                <input
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="URL da logo..."
                  className="flex-1 rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-primary)]"
                />
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleUploadImage(f, setLogoUrl, "logo");
                    }}
                  />
                  <span className="inline-flex items-center gap-1 rounded-lg border border-[var(--sa-border)] px-3 py-2 text-sm text-[var(--sa-text-muted)] hover:bg-[var(--sa-bg-hover)]">
                    <Upload className="w-4 h-4" />
                  </span>
                </label>
              </div>
              {logoUrl && (
                <img src={logoUrl} alt="Logo preview" className="mt-2 h-16 rounded-lg object-contain bg-[var(--sa-bg)]" />
              )}
            </div>

            {/* Banner */}
            <div>
              <label className="text-sm font-semibold text-[var(--sa-text-primary)] mb-1 block">Banner URL</label>
              <div className="flex gap-2">
                <input
                  value={bannerUrl}
                  onChange={(e) => setBannerUrl(e.target.value)}
                  placeholder="URL do banner..."
                  className="flex-1 rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-primary)]"
                />
                <label className="cursor-pointer">
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleUploadImage(f, setBannerUrl, "banner");
                    }}
                  />
                  <span className="inline-flex items-center gap-1 rounded-lg border border-[var(--sa-border)] px-3 py-2 text-sm text-[var(--sa-text-muted)] hover:bg-[var(--sa-bg-hover)]">
                    <Upload className="w-4 h-4" />
                  </span>
                </label>
              </div>
              {bannerUrl && (
                <img src={bannerUrl} alt="Banner preview" className="mt-2 h-24 w-full rounded-lg object-cover" />
              )}
            </div>

            {/* Cores */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-[var(--sa-text-primary)] mb-1 block">Cor Primária</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={corPrimaria}
                    onChange={(e) => setCorPrimaria(e.target.value)}
                    className="w-10 h-10 rounded cursor-pointer border-0"
                  />
                  <input
                    value={corPrimaria}
                    onChange={(e) => setCorPrimaria(e.target.value)}
                    className="flex-1 rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-primary)]"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-semibold text-[var(--sa-text-primary)] mb-1 block">Cor Secundária</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="color"
                    value={corSecundaria}
                    onChange={(e) => setCorSecundaria(e.target.value)}
                    className="w-10 h-10 rounded cursor-pointer border-0"
                  />
                  <input
                    value={corSecundaria}
                    onChange={(e) => setCorSecundaria(e.target.value)}
                    className="flex-1 rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-primary)]"
                  />
                </div>
              </div>
            </div>

            <Button
              onClick={handleSaveVisual}
              disabled={atualizarSiteConfigMutation.isPending}
              className="bg-[var(--sa-accent)] text-white hover:bg-[var(--sa-accent)]/90"
            >
              <Save className="w-4 h-4 mr-2" />
              {atualizarSiteConfigMutation.isPending ? "Salvando..." : "Salvar Visual"}
            </Button>
          </Card>
        )}

        {/* Tab: Cardápio */}
        {activeTab === "cardapio" && (
          <div className="space-y-4">
            {demo.categorias?.map((cat: any) => (
              <Card key={cat.id} className="p-4 border-[var(--sa-border)] bg-[var(--sa-bg-surface)]">
                <h3 className="text-base font-bold text-[var(--sa-text-primary)] mb-3">
                  {cat.nome} ({cat.produtos.length} produtos)
                </h3>
                <div className="space-y-2">
                  {cat.produtos.map((prod: any) => (
                    <div key={prod.id}>
                      {editingProduct === prod.id ? (
                        <div className="flex flex-wrap gap-2 items-end p-3 bg-[var(--sa-bg)] rounded-lg border border-[var(--sa-accent)]/30">
                          <div className="flex-1 min-w-[200px]">
                            <label className="text-xs font-medium text-[var(--sa-text-muted)]">Nome</label>
                            <input
                              value={editNome}
                              onChange={(e) => setEditNome(e.target.value)}
                              className="w-full rounded border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] px-2 py-1 text-sm text-[var(--sa-text-primary)]"
                            />
                          </div>
                          <div className="w-24">
                            <label className="text-xs font-medium text-[var(--sa-text-muted)]">Preço</label>
                            <input
                              value={editPreco}
                              onChange={(e) => setEditPreco(e.target.value)}
                              type="number"
                              step="0.01"
                              className="w-full rounded border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] px-2 py-1 text-sm text-[var(--sa-text-primary)]"
                            />
                          </div>
                          <div className="flex-1 min-w-[200px]">
                            <label className="text-xs font-medium text-[var(--sa-text-muted)]">Imagem URL</label>
                            <div className="flex gap-1">
                              <input
                                value={editImagem}
                                onChange={(e) => setEditImagem(e.target.value)}
                                placeholder="URL da imagem..."
                                className="flex-1 rounded border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] px-2 py-1 text-sm text-[var(--sa-text-primary)]"
                              />
                              <label className="cursor-pointer">
                                <input
                                  type="file"
                                  accept="image/*"
                                  className="hidden"
                                  onChange={(e) => {
                                    const f = e.target.files?.[0];
                                    if (f) handleUploadImage(f, setEditImagem);
                                  }}
                                />
                                <span className="inline-flex items-center rounded border border-[var(--sa-border)] px-1.5 py-1 text-xs text-[var(--sa-text-muted)] hover:bg-[var(--sa-bg-hover)]">
                                  <Upload className="w-3 h-3" />
                                </span>
                              </label>
                            </div>
                          </div>
                          <div className="flex gap-1">
                            <Button
                              size="sm"
                              onClick={handleSaveProduct}
                              disabled={atualizarProdutoMutation.isPending}
                              className="bg-[var(--sa-accent)] text-white text-xs"
                            >
                              Salvar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setEditingProduct(null)}
                              className="border-[var(--sa-border)] text-xs"
                            >
                              Cancelar
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <div
                          className="flex items-center gap-3 p-2 rounded-lg hover:bg-[var(--sa-bg-hover)] cursor-pointer transition-colors"
                          onClick={() => startEditProduct(prod)}
                        >
                          {prod.imagem_url ? (
                            <img
                              src={prod.imagem_url}
                              alt={prod.nome}
                              className="w-12 h-12 rounded-lg object-cover"
                            />
                          ) : (
                            <div className="w-12 h-12 rounded-lg bg-[var(--sa-bg)] flex items-center justify-center">
                              <ImageIcon className="w-5 h-5 text-[var(--sa-text-dimmed)]" />
                            </div>
                          )}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-[var(--sa-text-primary)] truncate">
                              {prod.nome}
                            </p>
                            <p className="text-xs text-[var(--sa-text-muted)] truncate">
                              {prod.descricao || "Sem descrição"}
                            </p>
                          </div>
                          <span className="text-sm font-bold text-[var(--sa-text-primary)]">
                            R$ {prod.preco.toFixed(2)}
                          </span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}

            {(!demo.categorias || demo.categorias.length === 0) && (
              <div className="text-center py-8 text-[var(--sa-text-muted)]">
                Nenhuma categoria/produto encontrado neste demo.
              </div>
            )}
          </div>
        )}

        {/* Tab: Config */}
        {activeTab === "config" && (
          <Card className="p-6 border-[var(--sa-border)] bg-[var(--sa-bg-surface)] space-y-5">
            <h2 className="text-lg font-bold text-[var(--sa-text-primary)]">Configurações</h2>

            <div>
              <label className="text-sm font-semibold text-[var(--sa-text-primary)] mb-1 block">Nome Fantasia</label>
              <input
                value={editNomeFantasia}
                onChange={(e) => setEditNomeFantasia(e.target.value)}
                className="w-full rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-primary)]"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-[var(--sa-text-muted)] mb-1 block">Código Acesso</label>
                <input
                  value={demo.codigo_acesso}
                  readOnly
                  className="w-full rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-muted)] opacity-60"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-[var(--sa-text-muted)] mb-1 block">Email</label>
                <input
                  value={demo.email}
                  readOnly
                  className="w-full rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg)] px-3 py-2 text-sm text-[var(--sa-text-muted)] opacity-60"
                />
              </div>
            </div>

            {demo.site_config && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-[var(--sa-text-muted)] mb-1 block">Pedido Mínimo</label>
                  <p className="text-sm text-[var(--sa-text-primary)]">R$ {demo.site_config.pedido_minimo?.toFixed(2) || "0.00"}</p>
                </div>
                <div>
                  <label className="text-sm font-semibold text-[var(--sa-text-muted)] mb-1 block">Tempo Entrega</label>
                  <p className="text-sm text-[var(--sa-text-primary)]">{demo.site_config.tempo_entrega_estimado || 50} min</p>
                </div>
              </div>
            )}

            <Button
              onClick={handleSaveConfig}
              disabled={atualizarDemoMutation.isPending}
              className="bg-[var(--sa-accent)] text-white hover:bg-[var(--sa-accent)]/90"
            >
              <Save className="w-4 h-4 mr-2" />
              {atualizarDemoMutation.isPending ? "Salvando..." : "Salvar Config"}
            </Button>
          </Card>
        )}

        {/* Tab: Preview */}
        {activeTab === "preview" && (
          <Card className="border-[var(--sa-border)] bg-[var(--sa-bg-surface)] overflow-hidden">
            <div className="p-4 border-b border-[var(--sa-border)] flex items-center justify-between">
              <h2 className="text-base font-bold text-[var(--sa-text-primary)]">Preview do Site Demo</h2>
              <Button
                size="sm"
                variant="outline"
                className="border-[var(--sa-border)] text-[var(--sa-text-muted)]"
                onClick={() => window.open(`/cliente/${demo.codigo_acesso}`, "_blank")}
              >
                <ExternalLink className="w-4 h-4 mr-1" />
                Abrir em nova aba
              </Button>
            </div>
            <iframe
              src={`/cliente/${demo.codigo_acesso}`}
              className="w-full border-0"
              style={{ height: "70vh" }}
              title="Preview Demo"
            />
          </Card>
        )}
      </div>
    </SuperAdminLayout>
  );
}
