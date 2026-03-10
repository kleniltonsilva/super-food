import { useState, useEffect } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useConfig,
  useAtualizarConfig,
  useConfigSite,
  useAtualizarConfigSite,
} from "@/admin/hooks/useAdminQueries";
import { uploadImagem, atualizarPerfil } from "@/admin/lib/adminApiClient";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Save, Upload, Loader2, AlertTriangle, MapPin, Eye } from "lucide-react";
import { toast } from "sonner";
import { getThemeConfig, tiposRestaurante } from "@/config/themeConfig";

export default function Configuracoes() {
  const { data: config, isLoading: loadingConfig, refetch: refetchConfig } = useConfig();
  const { data: siteConfig, isLoading: loadingSite } = useConfigSite();
  const atualizarConfig = useAtualizarConfig();
  const atualizarSite = useAtualizarConfigSite();
  const { refreshRestaurante } = useAdminAuth();

  // Config do restaurante
  const [restForm, setRestForm] = useState<Record<string, unknown>>({});
  // Config do site
  const [siteForm, setSiteForm] = useState<Record<string, unknown>>({});
  const [uploading, setUploading] = useState<string | null>(null);
  const [geocoding, setGeocoding] = useState(false);

  useEffect(() => {
    if (config) setRestForm({ ...config });
  }, [config]);

  useEffect(() => {
    if (siteConfig) setSiteForm({ ...siteConfig });
  }, [siteConfig]);

  function handleSaveConfig() {
    const { id, ...payload } = restForm;
    atualizarConfig.mutate(payload, {
      onSuccess: () => toast.success("Configurações salvas!"),
      onError: () => toast.error("Erro ao salvar"),
    });
  }

  function handleSaveSite() {
    const { id, ...payload } = siteForm;
    atualizarSite.mutate(payload, {
      onSuccess: () => toast.success("Configurações do site salvas!"),
      onError: () => toast.error("Erro ao salvar"),
    });
  }

  async function handleImageUpload(field: string, e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(field);
    try {
      const data = await uploadImagem(file);
      setSiteForm({ ...siteForm, [field]: data.url || data.path || "" });
      toast.success("Imagem enviada");
    } catch {
      toast.error("Erro ao enviar imagem");
    } finally {
      setUploading(null);
    }
  }

  function updateRest(field: string, value: unknown) {
    setRestForm({ ...restForm, [field]: value });
  }

  function updateSite(field: string, value: unknown) {
    setSiteForm({ ...siteForm, [field]: value });
  }

  return (
    <AdminLayout>
      <div className="space-y-4">
        <h2 className="text-2xl font-bold text-[var(--text-primary)]">Configurações</h2>

        <Tabs defaultValue="restaurante">
          <TabsList>
            <TabsTrigger value="restaurante">Restaurante</TabsTrigger>
            <TabsTrigger value="site">Site / Cardápio</TabsTrigger>
          </TabsList>

          {/* Config Restaurante */}
          <TabsContent value="restaurante">
            {loadingConfig ? (
              <Skeleton className="h-96 w-full" />
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {/* Operação */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Operação</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Status</label>
                      <Select value={(restForm.status_atual as string) || "aberto"} onValueChange={(v) => updateRest("status_atual", v)}>
                        <SelectTrigger className="dark-input"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="aberto">Aberto</SelectItem>
                          <SelectItem value="fechado">Fechado</SelectItem>
                          <SelectItem value="pausado">Pausado</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Horário Abertura</label>
                        <Input value={(restForm.horario_abertura as string) || ""} onChange={(e) => updateRest("horario_abertura", e.target.value)} className="dark-input" placeholder="08:00" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Horário Fechamento</label>
                        <Input value={(restForm.horario_fechamento as string) || ""} onChange={(e) => updateRest("horario_fechamento", e.target.value)} className="dark-input" placeholder="23:00" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Entrega — Modo Prioridade */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Entrega</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Modo Prioridade de Entrega</label>
                      <div className="space-y-2">
                        {[
                          { value: "rapido_economico", label: "Rápido Econômico", desc: "Otimiza por proximidade (TSP)" },
                          { value: "cronologico_inteligente", label: "Cronológico Inteligente", desc: "Agrupa pedidos por tempo" },
                          { value: "manual", label: "Manual", desc: "Você atribui cada pedido" },
                        ].map((opt) => (
                          <label
                            key={opt.value}
                            className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                              (restForm.modo_prioridade_entrega || "manual") === opt.value
                                ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/5"
                                : "border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)]"
                            }`}
                          >
                            <input
                              type="radio"
                              name="modo_prioridade"
                              value={opt.value}
                              checked={(restForm.modo_prioridade_entrega || "manual") === opt.value}
                              onChange={() => updateRest("modo_prioridade_entrega", opt.value)}
                              className="mt-0.5"
                            />
                            <div>
                              <p className="text-sm font-medium text-[var(--text-primary)]">{opt.label}</p>
                              <p className="text-xs text-[var(--text-muted)]">{opt.desc}</p>
                            </div>
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Máx. Pedidos por Rota</label>
                      <Input
                        type="number"
                        min="1"
                        max="10"
                        value={(restForm.max_pedidos_por_rota as number) || 3}
                        onChange={(e) => updateRest("max_pedidos_por_rota", Number(e.target.value))}
                        className="dark-input"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Raio Entrega (km)</label>
                        <Input type="number" step="0.1" value={(restForm.raio_entrega_km as number) || ""} onChange={(e) => updateRest("raio_entrega_km", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Taxa Base (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.taxa_entrega_base as number) || ""} onChange={(e) => updateRest("taxa_entrega_base", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Dist. Base (km)</label>
                        <Input type="number" step="0.1" value={(restForm.distancia_base_km as number) || ""} onChange={(e) => updateRest("distancia_base_km", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Taxa KM Extra (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.taxa_km_extra as number) || ""} onChange={(e) => updateRest("taxa_km_extra", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="text-sm text-[var(--text-secondary)]">Permitir Motoboy Ver Saldo</label>
                      <Switch checked={!!restForm.permitir_ver_saldo_motoboy} onCheckedChange={(v) => updateRest("permitir_ver_saldo_motoboy", v)} />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Permitir Finalizar Fora do Raio</label>
                        <Switch checked={!!restForm.permitir_finalizar_fora_raio} onCheckedChange={(v) => updateRest("permitir_finalizar_fora_raio", v)} />
                      </div>
                      {!!restForm.permitir_finalizar_fora_raio && (
                        <div className="flex items-center gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-3 py-2">
                          <AlertTriangle className="h-4 w-4 shrink-0 text-yellow-400" />
                          <p className="text-xs text-yellow-400">
                            Motoboys poderão finalizar entregas mesmo fora do raio de entrega configurado.
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Pagamento Motoboy */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Pagamento Motoboy</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Valor Base (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.valor_base_motoboy as number) || ""} onChange={(e) => updateRest("valor_base_motoboy", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">KM Extra (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.valor_km_extra_motoboy as number) || ""} onChange={(e) => updateRest("valor_km_extra_motoboy", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Taxa Diária (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.taxa_diaria as number) || ""} onChange={(e) => updateRest("taxa_diaria", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Valor Lanche (R$)</label>
                        <Input type="number" step="0.01" value={(restForm.valor_lanche as number) || ""} onChange={(e) => updateRest("valor_lanche", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Endereço */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Endereço</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Endereço Completo</label>
                      <Textarea
                        value={(restForm.endereco_completo as string) || ""}
                        onChange={(e) => updateRest("endereco_completo", e.target.value)}
                        className="dark-input"
                        placeholder="Rua, número, bairro, cidade - UF"
                        rows={3}
                      />
                    </div>
                    {(config?.latitude || config?.longitude) && (
                      <p className="text-xs text-[var(--text-muted)]">
                        Coordenadas atuais: {Number(config.latitude).toFixed(6)}, {Number(config.longitude).toFixed(6)}
                      </p>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={geocoding || !(restForm.endereco_completo as string)?.trim()}
                      onClick={async () => {
                        const endereco = (restForm.endereco_completo as string)?.trim();
                        if (!endereco) { toast.error("Informe o endereço"); return; }
                        setGeocoding(true);
                        try {
                          const result = await atualizarPerfil({ endereco_completo: endereco });
                          if (result.latitude && result.longitude) {
                            toast.success(`Endereço geocodificado! (${Number(result.latitude).toFixed(6)}, ${Number(result.longitude).toFixed(6)})`);
                          } else {
                            toast.warning("Endereço salvo, mas não foi possível geocodificar");
                          }
                          await refreshRestaurante();
                          await refetchConfig();
                        } catch {
                          toast.error("Erro ao salvar endereço");
                        } finally {
                          setGeocoding(false);
                        }
                      }}
                    >
                      {geocoding ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <MapPin className="mr-1 h-4 w-4" />}
                      Salvar e Geocodificar
                    </Button>
                  </CardContent>
                </Card>

                <div className="lg:col-span-2">
                  <Button
                    className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                    onClick={handleSaveConfig}
                    disabled={atualizarConfig.isPending}
                  >
                    <Save className="mr-2 h-4 w-4" /> Salvar Configurações
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Config Site */}
          <TabsContent value="site">
            {loadingSite ? (
              <Skeleton className="h-96 w-full" />
            ) : (
              <div className="grid gap-4 lg:grid-cols-2">
                {/* Aparência */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Aparência</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Tipo de Restaurante</label>
                      <Select value={(siteForm.tipo_restaurante as string) || "restaurante"} onValueChange={(v) => updateSite("tipo_restaurante", v)}>
                        <SelectTrigger className="dark-input"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {tiposRestaurante.map((t) => (
                            <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Preview do tema selecionado */}
                    {(() => {
                      const previewTheme = getThemeConfig((siteForm.tipo_restaurante as string) || "restaurante");
                      const prim = (siteForm.tema_cor_primaria as string) || previewTheme.colors.primary;
                      const sec = (siteForm.tema_cor_secundaria as string) || previewTheme.colors.secondary;
                      return (
                        <div className="space-y-1.5">
                          <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                            <Eye className="w-3.5 h-3.5" />
                            Preview do Tema: {previewTheme.label}
                          </label>
                          <div className="rounded-lg overflow-hidden border border-[var(--border-subtle)]" style={{ background: previewTheme.colors.bodyBg }}>
                            {/* Mini header */}
                            <div className="px-3 py-2 flex items-center justify-between" style={{ background: previewTheme.colors.headerBg }}>
                              <span className="text-xs font-bold" style={{ color: previewTheme.isDark || previewTheme.headerStyle === "dark" ? "#fff" : previewTheme.colors.textPrimary, fontFamily: previewTheme.fonts.heading }}>{(siteForm.nome_fantasia as string) || "Seu Restaurante"}</span>
                              <div className="w-4 h-4 rounded-full" style={{ background: prim }} />
                            </div>
                            {/* Mini banner */}
                            <div className="h-8" style={{ background: `linear-gradient(135deg, ${prim}, ${sec})` }} />
                            {/* Mini cards */}
                            <div className="p-2 flex gap-2">
                              {[1, 2, 3].map(i => (
                                <div key={i} className="flex-1 rounded-md overflow-hidden" style={{ background: previewTheme.colors.cardBg, border: `1px solid ${previewTheme.colors.cardBorder}`, borderRadius: previewTheme.cardRadius }}>
                                  <div className="h-6" style={{ background: previewTheme.isDark ? "rgba(255,255,255,0.04)" : "#eee" }} />
                                  <div className="p-1">
                                    <div className="h-1.5 rounded-full w-3/4 mb-1" style={{ background: previewTheme.colors.textMuted, opacity: 0.3 }} />
                                    <div className="h-2 rounded-full w-1/2" style={{ background: previewTheme.colors.priceColor }} />
                                  </div>
                                </div>
                              ))}
                            </div>
                            {/* Mini footer */}
                            <div className="px-3 py-1.5" style={{ background: previewTheme.colors.footerBg, borderTop: previewTheme.footerBorderTop || undefined }}>
                              <span className="text-[8px]" style={{ color: previewTheme.isDark ? "rgba(255,255,255,0.5)" : previewTheme.colors.textMuted }}>Powered by Super Food</span>
                            </div>
                          </div>
                          <p className="text-[10px] text-[var(--text-muted)]">{previewTheme.mood} — {previewTheme.isDark ? "Tema escuro" : "Tema claro"}</p>
                        </div>
                      );
                    })()}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Cor Primária</label>
                        <div className="flex gap-2">
                          <input
                            type="color"
                            value={(siteForm.tema_cor_primaria as string) || "#ff6600"}
                            onChange={(e) => updateSite("tema_cor_primaria", e.target.value)}
                            className="h-9 w-9 cursor-pointer rounded border-0"
                          />
                          <Input value={(siteForm.tema_cor_primaria as string) || ""} onChange={(e) => updateSite("tema_cor_primaria", e.target.value)} className="dark-input" />
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Cor Secundária</label>
                        <div className="flex gap-2">
                          <input
                            type="color"
                            value={(siteForm.tema_cor_secundaria as string) || "#333333"}
                            onChange={(e) => updateSite("tema_cor_secundaria", e.target.value)}
                            className="h-9 w-9 cursor-pointer rounded border-0"
                          />
                          <Input value={(siteForm.tema_cor_secundaria as string) || ""} onChange={(e) => updateSite("tema_cor_secundaria", e.target.value)} className="dark-input" />
                        </div>
                      </div>
                    </div>

                    {/* Logo */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Logo</label>
                      <div className="flex items-center gap-3">
                        {siteForm.logo_url ? (
                          <img src={siteForm.logo_url as string} alt="" className="h-12 w-12 rounded-lg object-contain" />
                        ) : null}
                        <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-muted)]">
                          {uploading === "logo_url" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                          Enviar logo
                          <input type="file" accept="image/*" className="hidden" onChange={(e) => handleImageUpload("logo_url", e)} />
                        </label>
                      </div>
                    </div>

                    {/* Banner */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Banner Principal</label>
                      <div className="flex items-center gap-3">
                        {siteForm.banner_principal_url ? (
                          <img src={siteForm.banner_principal_url as string} alt="" className="h-12 w-24 rounded-lg object-cover" />
                        ) : null}
                        <label className="flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[var(--border-subtle)] px-3 py-2 text-sm text-[var(--text-muted)]">
                          {uploading === "banner_principal_url" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
                          Enviar banner
                          <input type="file" accept="image/*" className="hidden" onChange={(e) => handleImageUpload("banner_principal_url", e)} />
                        </label>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Pedidos */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Pedidos & Pagamento</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Pedido Mínimo (R$)</label>
                        <Input type="number" step="0.01" value={(siteForm.pedido_minimo as number) || ""} onChange={(e) => updateSite("pedido_minimo", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)]">Tempo Entrega (min)</label>
                        <Input type="number" value={(siteForm.tempo_entrega_estimado as number) || ""} onChange={(e) => updateSite("tempo_entrega_estimado", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Tempo Retirada Estimado (min)</label>
                      <Input type="number" value={(siteForm.tempo_retirada_estimado as number) || ""} onChange={(e) => updateSite("tempo_retirada_estimado", Number(e.target.value))} className="dark-input" placeholder="15" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">WhatsApp</label>
                      <Input value={(siteForm.whatsapp_numero as string) || ""} onChange={(e) => updateSite("whatsapp_numero", e.target.value)} className="dark-input" placeholder="5511999999999" />
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Site Ativo</label>
                        <Switch checked={!!siteForm.site_ativo} onCheckedChange={(v) => updateSite("site_ativo", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">WhatsApp Ativo</label>
                        <Switch checked={!!siteForm.whatsapp_ativo} onCheckedChange={(v) => updateSite("whatsapp_ativo", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Aceita Dinheiro</label>
                        <Switch checked={!!siteForm.aceita_dinheiro} onCheckedChange={(v) => updateSite("aceita_dinheiro", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Aceita Cartão</label>
                        <Switch checked={!!siteForm.aceita_cartao} onCheckedChange={(v) => updateSite("aceita_cartao", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Aceita PIX</label>
                        <Switch checked={!!siteForm.aceita_pix} onCheckedChange={(v) => updateSite("aceita_pix", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">Aceita Vale Refeição</label>
                        <Switch checked={!!siteForm.aceita_vale_refeicao} onCheckedChange={(v) => updateSite("aceita_vale_refeicao", v)} />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* SEO */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] lg:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">SEO</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Meta Title</label>
                      <Input value={(siteForm.meta_title as string) || ""} onChange={(e) => updateSite("meta_title", e.target.value)} className="dark-input" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Meta Description</label>
                      <Input value={(siteForm.meta_description as string) || ""} onChange={(e) => updateSite("meta_description", e.target.value)} className="dark-input" />
                    </div>
                  </CardContent>
                </Card>

                <div className="lg:col-span-2">
                  <Button
                    className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                    onClick={handleSaveSite}
                    disabled={atualizarSite.isPending}
                  >
                    <Save className="mr-2 h-4 w-4" /> Salvar Configurações do Site
                  </Button>
                </div>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}
