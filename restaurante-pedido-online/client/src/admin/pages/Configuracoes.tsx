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
import { Save, Upload, Loader2, AlertTriangle, MapPin, Eye, Plus, Trash2 } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";
import { toast } from "sonner";
import { getThemeConfig, tiposRestaurante } from "@/config/themeConfig";
import AddressAutocomplete from "@/components/AddressAutocomplete";
import { autocompleteEndereco } from "@/admin/lib/adminApiClient";

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
    const tipo = field === "logo_url" ? "logo" : "banner";
    try {
      const data = await uploadImagem(file, tipo);
      setSiteForm({ ...siteForm, [field]: data.url || data.path || "" });
      toast.success("Imagem enviada");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao enviar imagem";
      toast.error(msg);
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Status
                        <InfoTooltip text="Define se aceita pedidos. Aberto=aceita, Fechado=bloqueia, Pausado=exibe aviso temporário no site." />
                      </label>
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
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Horário Abertura
                          <InfoTooltip text="Horário de funcionamento exibido no site. Fora do horário, o site mostra 'Fechado' e bloqueia novos pedidos." />
                        </label>
                        <Input value={(restForm.horario_abertura as string) || ""} onChange={(e) => updateRest("horario_abertura", e.target.value)} className="dark-input" placeholder="08:00" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Horário Fechamento
                          <InfoTooltip text="Horário em que o site para de aceitar pedidos automaticamente." />
                        </label>
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Modo Prioridade de Entrega
                        <InfoTooltip text="Rápido Econômico=otimiza rota por menor distância (TSP). Cronológico=agrupa pedidos por tempo de criação. Manual=operador escolhe o motoboy para cada pedido." />
                      </label>
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

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Tolerância para Alerta de Atraso
                        <InfoTooltip text="Minutos extras além do tempo estimado antes de marcar a entrega como atrasada. O painel exibirá alerta vermelho pulsante quando ultrapassar." />
                      </label>
                      <div className="flex gap-2">
                        {[5, 8, 10, 15].map((min) => (
                          <label
                            key={min}
                            className={`flex items-center justify-center rounded-lg border px-3 py-2 text-sm font-medium cursor-pointer transition-colors ${
                              (restForm.tolerancia_atraso_min as number || 10) === min
                                ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/10 text-[var(--cor-primaria)]"
                                : "border-[var(--border-subtle)] text-[var(--text-muted)] hover:bg-[var(--bg-card-hover)]"
                            }`}
                          >
                            <input
                              type="radio"
                              name="tolerancia_atraso"
                              value={min}
                              checked={(restForm.tolerancia_atraso_min as number || 10) === min}
                              onChange={() => updateRest("tolerancia_atraso_min", min)}
                              className="sr-only"
                            />
                            {min} min
                          </label>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Máx. Pedidos por Rota
                        <InfoTooltip text="Quantos pedidos o motoboy pode carregar por saída (1 a 10). Mais pedidos por rota = menos viagens, mas entregas podem demorar mais." />
                      </label>
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
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Raio Entrega (km)
                          <InfoTooltip text="Distância máxima aceita para entrega. Pedidos com endereço fora deste raio serão recusados automaticamente no checkout." />
                        </label>
                        <Input type="number" step="0.1" value={(restForm.raio_entrega_km as number) || ""} onChange={(e) => updateRest("raio_entrega_km", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Taxa Base (R$)
                          <InfoTooltip text="Valor mínimo de frete cobrado do cliente, válido até a distância base configurada." />
                        </label>
                        <Input type="number" step="0.01" value={(restForm.taxa_entrega_base as number) || ""} onChange={(e) => updateRest("taxa_entrega_base", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Dist. Base (km)
                          <InfoTooltip text="Distância incluída na taxa base. Além desta distância, será cobrado o valor de KM Extra por quilômetro adicional." />
                        </label>
                        <Input type="number" step="0.1" value={(restForm.distancia_base_km as number) || ""} onChange={(e) => updateRest("distancia_base_km", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Taxa KM Extra (R$)
                          <InfoTooltip text="Valor adicional cobrado do cliente por cada km que excede a distância base. Ex: Dist. Base 3km, Taxa KM Extra R$1,50 → 5km = Taxa Base + 2×R$1,50." />
                        </label>
                        <Input type="number" step="0.01" value={(restForm.taxa_km_extra as number) || ""} onChange={(e) => updateRest("taxa_km_extra", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                        Permitir Motoboy Ver Saldo
                        <InfoTooltip text="Quando ativado, o motoboy pode ver seus ganhos acumulados (base + extras) no app de entregas." />
                      </label>
                      <Switch checked={!!restForm.permitir_ver_saldo_motoboy} onCheckedChange={(v) => updateRest("permitir_ver_saldo_motoboy", v)} />
                    </div>

                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Permitir Finalizar Fora do Raio
                          <InfoTooltip text="Antifraude GPS. Quando desativado, o motoboy só consegue finalizar a entrega se estiver a menos de 50 metros do endereço de destino." />
                        </label>
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

                {/* Modo Preço Pizza */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Pizza</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Modo de preço para múltiplos sabores
                        <InfoTooltip text="Define como calcular o preço da pizza com mais de 1 sabor. Mais Caro: cobra pelo sabor de maior preço (ex: Calabresa R$30 + Especial R$45 → R$45). Proporcional: divide proporcionalmente (ex: Calabresa R$30 + Especial R$45 → R$15 + R$22,50 = R$37,50)." />
                      </label>
                      <Select
                        value={(restForm.modo_preco_pizza as string) || "mais_caro"}
                        onValueChange={(v) => updateRest("modo_preco_pizza", v)}
                      >
                        <SelectTrigger className="dark-input"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="mais_caro">Mais Caro (cobra pelo sabor mais caro)</SelectItem>
                          <SelectItem value="proporcional">Proporcional (divide entre sabores)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </CardContent>
                </Card>

                {/* Pedidos do Site */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Pedidos do Site</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Aceitar pedidos automaticamente
                          <InfoTooltip text="Quando ativado, pedidos do site são aceitos automaticamente para clientes com ao menos 1 pedido concluído. O primeiro pedido de cada cliente ainda exige aceitação manual." />
                        </label>
                        <Switch
                          checked={!!restForm.aceitar_pedido_site_auto}
                          onCheckedChange={(v) => updateRest("aceitar_pedido_site_auto", v)}
                        />
                      </div>
                      {!!restForm.aceitar_pedido_site_auto ? (
                        <div className="flex items-start gap-2 rounded-md bg-green-500/10 border border-green-500/30 px-3 py-2">
                          <p className="text-xs text-green-400">
                            Clientes com pedido anterior concluído terão seus novos pedidos aceitos automaticamente. O primeiro pedido sempre precisará de confirmação manual.
                          </p>
                        </div>
                      ) : (
                        <div className="flex items-start gap-2 rounded-md bg-[var(--bg-card-hover)] border border-[var(--border-subtle)] px-3 py-2">
                          <p className="text-xs text-[var(--text-muted)]">
                            Todos os pedidos do site precisam de aceitação manual no painel.
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
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Valor Base (R$)
                          <InfoTooltip text="Valor pago ao motoboy por entrega, independente da distância percorrida." />
                        </label>
                        <Input type="number" step="0.01" value={(restForm.valor_base_motoboy as number) || ""} onChange={(e) => updateRest("valor_base_motoboy", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          KM Extra (R$)
                          <InfoTooltip text="Adicional pago ao motoboy por cada km além da distância base. Somado ao valor base." />
                        </label>
                        <Input type="number" step="0.01" value={(restForm.valor_km_extra_motoboy as number) || ""} onChange={(e) => updateRest("valor_km_extra_motoboy", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Taxa Diária (R$)
                          <InfoTooltip text="Valor fixo pago ao motoboy por dia trabalhado, independente de quantas entregas fizer. 0 = não pagar taxa diária." />
                        </label>
                        <Input type="number" step="0.01" value={(restForm.taxa_diaria as number) || ""} onChange={(e) => updateRest("taxa_diaria", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Valor Lanche (R$)
                          <InfoTooltip text="Auxílio alimentação diário pago ao motoboy. 0 = não aplicar auxílio alimentação." />
                        </label>
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Endereço Completo
                        <InfoTooltip text="Endereço do restaurante. Ao geocodificar, converte em coordenadas GPS usadas para calcular distâncias e taxas de entrega." />
                      </label>
                      <AddressAutocomplete
                        value={(restForm.endereco_completo as string) || ""}
                        onChange={(v) => updateRest("endereco_completo", v)}
                        fetchSuggestions={autocompleteEndereco}
                        placeholder="Rua, número, bairro, cidade - UF"
                        multiline
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Tipo de Restaurante
                        <InfoTooltip text="Define o tema visual completo do site (cores, fontes, layout dos cards, header, footer). A mudança é instantânea para o cliente." />
                      </label>
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
                              <span className="text-[8px]" style={{ color: previewTheme.isDark ? "rgba(255,255,255,0.5)" : previewTheme.colors.textMuted }}>Powered by Derekh Food</span>
                            </div>
                          </div>
                          <p className="text-[10px] text-[var(--text-muted)]">{previewTheme.mood} — {previewTheme.isDark ? "Tema escuro" : "Tema claro"}</p>
                        </div>
                      );
                    })()}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Cor Primária
                          <InfoTooltip text="Sobrescreve a cor primária do tema selecionado. Use o seletor de cor ou insira um código hex (#ff6600)." />
                        </label>
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
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Cor Secundária
                          <InfoTooltip text="Sobrescreve a cor secundária do tema. Usada em fundos, bordas e elementos de destaque." />
                        </label>
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Logo
                        <InfoTooltip text="Exibida no header do site. Recomendado: imagem quadrada 200x200px em PNG ou WebP com fundo transparente." />
                      </label>
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
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Banner Principal
                        <InfoTooltip text="Imagem de destaque na página inicial do site. Recomendado: 1200x400px. Se não definido, usa o banner padrão do tema." />
                      </label>
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
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Pedido Mínimo (R$)
                          <InfoTooltip text="Valor mínimo em produtos (sem frete) para o cliente finalizar o pedido. 0 = sem valor mínimo." />
                        </label>
                        <Input type="number" step="0.01" value={(siteForm.pedido_minimo as number) || ""} onChange={(e) => updateSite("pedido_minimo", Number(e.target.value))} className="dark-input" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                          Tempo Entrega (min)
                          <InfoTooltip text="Tempo estimado exibido ao cliente. O sistema pode ajustar automaticamente com base no histórico real de entregas." />
                        </label>
                        <Input type="number" value={(siteForm.tempo_entrega_estimado as number) || ""} onChange={(e) => updateSite("tempo_entrega_estimado", Number(e.target.value))} className="dark-input" />
                      </div>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Tempo Retirada Estimado (min)
                        <InfoTooltip text="Tempo estimado para o cliente retirar o pedido no balcão. Exibido quando o cliente escolhe 'Retirada'." />
                      </label>
                      <Input type="number" value={(siteForm.tempo_retirada_estimado as number) || ""} onChange={(e) => updateSite("tempo_retirada_estimado", Number(e.target.value))} className="dark-input" placeholder="15" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        WhatsApp
                        <InfoTooltip text="Número com código do país e DDD (ex: 5511999999999). Exibe botão de contato flutuante no site do cliente." />
                      </label>
                      <Input value={(siteForm.whatsapp_numero as string) || ""} onChange={(e) => updateSite("whatsapp_numero", e.target.value)} className="dark-input" placeholder="5511999999999" />
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Site Ativo
                          <InfoTooltip text="Quando desativado, o site fica inacessível e exibe uma página de manutenção para os clientes." />
                        </label>
                        <Switch checked={!!siteForm.site_ativo} onCheckedChange={(v) => updateSite("site_ativo", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)]">WhatsApp Ativo</label>
                        <Switch checked={!!siteForm.whatsapp_ativo} onCheckedChange={(v) => updateSite("whatsapp_ativo", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Aceita Dinheiro
                          <InfoTooltip text="Habilita dinheiro como forma de pagamento no checkout. O campo 'troco para' aparece quando selecionado." />
                        </label>
                        <Switch checked={!!siteForm.aceita_dinheiro} onCheckedChange={(v) => updateSite("aceita_dinheiro", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Aceita Cartão
                          <InfoTooltip text="Habilita cartão de crédito/débito na maquininha como opção de pagamento na entrega." />
                        </label>
                        <Switch checked={!!siteForm.aceita_cartao} onCheckedChange={(v) => updateSite("aceita_cartao", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Aceita PIX
                          <InfoTooltip text="Habilita PIX como forma de pagamento. O cliente seleciona no checkout e paga diretamente." />
                        </label>
                        <Switch checked={!!siteForm.aceita_pix} onCheckedChange={(v) => updateSite("aceita_pix", v)} />
                      </div>
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                          Aceita Vale Refeição
                          <InfoTooltip text="Habilita vale-refeição/alimentação como forma de pagamento aceita na entrega." />
                        </label>
                        <Switch checked={!!siteForm.aceita_vale_refeicao} onCheckedChange={(v) => updateSite("aceita_vale_refeicao", v)} />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Ingredientes Adicionais Pizza */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] lg:col-span-2">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-[var(--text-primary)] flex items-center gap-1.5">
                        Ingredientes Adicionais (Pizza)
                        <InfoTooltip text="Lista de ingredientes extras disponíveis no montador de pizza. O cliente pode adicionar qualquer um destes ao montar sua pizza, cada um com seu preço adicional." />
                      </CardTitle>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          const lista = ((siteForm.ingredientes_adicionais_pizza as Array<{nome: string; preco: number}>) || []);
                          updateSite("ingredientes_adicionais_pizza", [...lista, { nome: "", preco: 0 }]);
                        }}
                      >
                        <Plus className="mr-1 h-4 w-4" /> Adicionar
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {(() => {
                      const lista = ((siteForm.ingredientes_adicionais_pizza as Array<{nome: string; preco: number}>) || []);
                      if (lista.length === 0) {
                        return (
                          <p className="text-sm text-[var(--text-muted)]">
                            Nenhum ingrediente adicional cadastrado. Adicione ingredientes como Bacon, Champignon, Cheddar, etc.
                          </p>
                        );
                      }
                      return (
                        <div className="space-y-2">
                          <div className="grid grid-cols-[1fr_100px_40px] gap-2 text-xs font-medium text-[var(--text-muted)] px-1">
                            <span>Nome</span>
                            <span>Preço (R$)</span>
                            <span></span>
                          </div>
                          {lista.map((ing, idx) => (
                            <div key={idx} className="grid grid-cols-[1fr_100px_40px] gap-2 items-center">
                              <Input
                                value={ing.nome}
                                onChange={(e) => {
                                  const next = [...lista];
                                  next[idx] = { ...next[idx], nome: e.target.value };
                                  updateSite("ingredientes_adicionais_pizza", next);
                                }}
                                className="dark-input h-9 text-sm"
                                placeholder="Ex: Bacon"
                              />
                              <Input
                                type="number"
                                step="0.01"
                                value={ing.preco}
                                onChange={(e) => {
                                  const next = [...lista];
                                  next[idx] = { ...next[idx], preco: Number(e.target.value) };
                                  updateSite("ingredientes_adicionais_pizza", next);
                                }}
                                className="dark-input h-9 text-sm"
                                placeholder="0.00"
                              />
                              <Button
                                variant="ghost"
                                size="icon-sm"
                                className="text-red-400"
                                onClick={() => {
                                  const next = lista.filter((_, i) => i !== idx);
                                  updateSite("ingredientes_adicionais_pizza", next);
                                }}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          ))}
                        </div>
                      );
                    })()}
                  </CardContent>
                </Card>

                {/* SEO */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)] lg:col-span-2">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">SEO</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Meta Title
                        <InfoTooltip text="Título exibido na aba do navegador e nos resultados de busca do Google. Recomendado: até 60 caracteres." />
                      </label>
                      <Input value={(siteForm.meta_title as string) || ""} onChange={(e) => updateSite("meta_title", e.target.value)} className="dark-input" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Meta Description
                        <InfoTooltip text="Descrição que aparece abaixo do título nos resultados do Google. Recomendado: até 160 caracteres." />
                      </label>
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
