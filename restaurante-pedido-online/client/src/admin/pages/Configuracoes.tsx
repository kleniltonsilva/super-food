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
import { Save, Upload, Loader2, AlertTriangle, MapPin, Copy, Clock, Printer } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";
import { toast } from "sonner";
import AddressAutocomplete from "@/components/AddressAutocomplete";
import { autocompleteEndereco } from "@/admin/lib/adminApiClient";

const DIAS_SEMANA = [
  { key: "segunda", label: "Segunda" },
  { key: "terca", label: "Terça" },
  { key: "quarta", label: "Quarta" },
  { key: "quinta", label: "Quinta" },
  { key: "sexta", label: "Sexta" },
  { key: "sabado", label: "Sábado" },
  { key: "domingo", label: "Domingo" },
] as const;

type HorarioDia = { ativo: boolean; abertura: string; fechamento: string };
type HorariosPorDia = Record<string, HorarioDia>;

function criarHorariosPadrao(abertura?: string, fechamento?: string, diasAbertos?: string): HorariosPorDia {
  const ab = abertura || "18:00";
  const fe = fechamento || "23:00";
  const dias = diasAbertos ? diasAbertos.split(",").map(d => d.trim()) : DIAS_SEMANA.map(d => d.key);
  const result: HorariosPorDia = {};
  for (const dia of DIAS_SEMANA) {
    result[dia.key] = { ativo: dias.includes(dia.key), abertura: ab, fechamento: fe };
  }
  return result;
}

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
    // Sync horario_abertura/fechamento from horarios_por_dia for backward compatibility
    const horarios = payload.horarios_por_dia as HorariosPorDia | undefined;
    if (horarios) {
      // Use Monday's hours as the general fallback
      const seg = horarios.segunda;
      if (seg?.ativo) {
        payload.horario_abertura = seg.abertura;
        payload.horario_fechamento = seg.fechamento;
      }
      // Build dias_semana_abertos string
      const diasAtivos = DIAS_SEMANA.filter(d => horarios[d.key]?.ativo).map(d => d.key);
      payload.dias_semana_abertos = diasAtivos.join(",");
    }
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
            <TabsTrigger value="impressora">Impressora</TabsTrigger>
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
                    {/* Grade de Horários por Dia da Semana */}
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        <Clock className="h-4 w-4" />
                        Horários de Funcionamento
                        <InfoTooltip text="Configure o horário de abertura e fechamento para cada dia da semana. Dias desativados aparecem como 'Fechado' no site." />
                      </label>
                      {(() => {
                        const horarios: HorariosPorDia = (restForm.horarios_por_dia as HorariosPorDia) ||
                          criarHorariosPadrao(
                            restForm.horario_abertura as string,
                            restForm.horario_fechamento as string,
                            restForm.dias_semana_abertos as string
                          );

                        const updateHorario = (diaKey: string, field: keyof HorarioDia, value: unknown) => {
                          const updated = { ...horarios };
                          updated[diaKey] = { ...updated[diaKey], [field]: value };
                          updateRest("horarios_por_dia", updated);
                        };

                        const aplicarATodos = (diaRef: string) => {
                          const ref = horarios[diaRef];
                          if (!ref) return;
                          const updated = { ...horarios };
                          for (const dia of DIAS_SEMANA) {
                            updated[dia.key] = { ...updated[dia.key], abertura: ref.abertura, fechamento: ref.fechamento };
                          }
                          updateRest("horarios_por_dia", updated);
                          toast.success(`Horário de ${DIAS_SEMANA.find(d => d.key === diaRef)?.label} aplicado a todos os dias`);
                        };

                        return (
                          <div className="space-y-2">
                            <div className="grid grid-cols-[1fr_auto_80px_80px_auto] gap-2 items-center text-xs font-medium text-[var(--text-muted)] px-1">
                              <span>Dia</span>
                              <span>Ativo</span>
                              <span>Abertura</span>
                              <span>Fechamento</span>
                              <span></span>
                            </div>
                            {DIAS_SEMANA.map((dia) => {
                              const diaH = horarios[dia.key] || { ativo: false, abertura: "", fechamento: "" };
                              return (
                                <div key={dia.key} className={`grid grid-cols-[1fr_auto_80px_80px_auto] gap-2 items-center rounded-lg border px-3 py-2 ${diaH.ativo ? "border-[var(--border-subtle)] bg-[var(--bg-card)]" : "border-[var(--border-subtle)] bg-[var(--bg-card)] opacity-50"}`}>
                                  <span className="text-sm font-medium text-[var(--text-primary)]">{dia.label}</span>
                                  <Switch
                                    checked={diaH.ativo}
                                    onCheckedChange={(v) => updateHorario(dia.key, "ativo", v)}
                                  />
                                  <Input
                                    type="time"
                                    value={diaH.abertura}
                                    onChange={(e) => updateHorario(dia.key, "abertura", e.target.value)}
                                    className="dark-input text-xs h-8"
                                    disabled={!diaH.ativo}
                                  />
                                  <Input
                                    type="time"
                                    value={diaH.fechamento}
                                    onChange={(e) => updateHorario(dia.key, "fechamento", e.target.value)}
                                    className="dark-input text-xs h-8"
                                    disabled={!diaH.ativo}
                                  />
                                  <button
                                    type="button"
                                    onClick={() => aplicarATodos(dia.key)}
                                    className="text-[var(--text-muted)] hover:text-[var(--cor-primaria)] transition-colors"
                                    title="Aplicar este horário a todos os dias"
                                  >
                                    <Copy className="h-3.5 w-3.5" />
                                  </button>
                                </div>
                              );
                            })}
                          </div>
                        );
                      })()}
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

                {/* Controle de Pedidos Online */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Controle de Pedidos Online</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                        Aceitar Pedidos Online
                        <InfoTooltip text="Quando desativado, nenhum pedido pode ser feito pelo site. O site exibirá aviso de indisponibilidade." />
                      </label>
                      <Switch
                        checked={restForm.pedidos_online_ativos !== false}
                        onCheckedChange={(v) => updateRest("pedidos_online_ativos", v)}
                      />
                    </div>

                    <div className="flex items-center justify-between">
                      <label className="text-sm text-[var(--text-secondary)] flex items-center gap-1.5">
                        Aceitar Entregas
                        <InfoTooltip text="Quando desativado, apenas retirada no balcão fica disponível. O site bloqueará a opção de entrega." />
                      </label>
                      <Switch
                        checked={restForm.entregas_ativas !== false}
                        onCheckedChange={(v) => updateRest("entregas_ativas", v)}
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Motivo (exibido ao cliente)
                        <InfoTooltip text="Mensagem opcional exibida no banner de aviso do site quando pedidos ou entregas estiverem desativados." />
                      </label>
                      <Input
                        value={(restForm.controle_pedidos_motivo as string) || ""}
                        onChange={(e) => updateRest("controle_pedidos_motivo", e.target.value || null)}
                        className="dark-input"
                        placeholder="Ex: Estamos em manutenção"
                      />
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
                        Duração
                        <InfoTooltip text="Indefinido mantém desativado até você reativar manualmente. 'Até data' reativa automaticamente na data/hora especificada." />
                      </label>
                      <div className="space-y-2">
                        <label className="flex items-center gap-2 text-sm text-[var(--text-primary)] cursor-pointer">
                          <input
                            type="radio"
                            name="duracao_controle"
                            checked={!restForm.controle_pedidos_ate}
                            onChange={() => updateRest("controle_pedidos_ate", null)}
                          />
                          Indefinido
                        </label>
                        <label className="flex items-center gap-2 text-sm text-[var(--text-primary)] cursor-pointer">
                          <input
                            type="radio"
                            name="duracao_controle"
                            checked={!!restForm.controle_pedidos_ate}
                            onChange={() => {
                              // Set default: tomorrow same time
                              const d = new Date();
                              d.setDate(d.getDate() + 1);
                              updateRest("controle_pedidos_ate", d.toISOString().slice(0, 16));
                            }}
                          />
                          Até data/hora
                        </label>
                        {!!restForm.controle_pedidos_ate && (
                          <Input
                            type="datetime-local"
                            value={typeof restForm.controle_pedidos_ate === "string" ? (restForm.controle_pedidos_ate as string).slice(0, 16) : ""}
                            onChange={(e) => updateRest("controle_pedidos_ate", e.target.value || null)}
                            className="dark-input"
                          />
                        )}
                      </div>
                    </div>

                    {(restForm.pedidos_online_ativos === false || restForm.entregas_ativas === false) && (
                      <div className="flex items-center gap-2 rounded-md bg-amber-500/10 border border-amber-500/30 px-3 py-2">
                        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                        <p className="text-xs text-amber-400">
                          {restForm.pedidos_online_ativos === false
                            ? "Pedidos online estão desativados. O site exibirá aviso de indisponibilidade."
                            : "Entregas estão desativadas. Apenas retirada no balcão estará disponível no site."
                          }
                        </p>
                      </div>
                    )}
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
                {/* Logo e Banner */}
                <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader>
                    <CardTitle className="text-[var(--text-primary)]">Logo e Banner</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
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

          {/* Config Impressora */}
          <TabsContent value="impressora">
            <div className="grid gap-4 max-w-lg">
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                    <Printer className="h-5 w-5" /> Impressão de Comandas
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium text-[var(--text-primary)]">Impressão Automática</div>
                      <div className="text-xs text-[var(--text-muted)]">Imprime comanda automaticamente ao receber pedido</div>
                    </div>
                    <Switch
                      checked={!!(restForm.impressao_automatica)}
                      onCheckedChange={(v) => setRestForm({ ...restForm, impressao_automatica: v })}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">Largura da Impressora</label>
                    <Select
                      value={String(restForm.largura_impressao || 80)}
                      onValueChange={(v) => setRestForm({ ...restForm, largura_impressao: Number(v) })}
                    >
                      <SelectTrigger className="dark-input">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="80">80mm (padrão)</SelectItem>
                        <SelectItem value="58">58mm (compacta)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    className="w-full bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                    onClick={handleSaveConfig}
                    disabled={atualizarConfig.isPending}
                  >
                    <Save className="mr-2 h-4 w-4" />
                    {atualizarConfig.isPending ? "Salvando..." : "Salvar"}
                  </Button>
                </CardContent>
              </Card>

              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] text-base">Agente de Impressão</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-[var(--text-muted)]">
                    Para imprimir comandas automaticamente, instale o agente de impressão no computador do restaurante.
                  </p>
                  <ol className="text-sm text-[var(--text-secondary)] space-y-1 list-decimal list-inside">
                    <li>Baixe o <strong>DerekhFood-Impressora.exe</strong></li>
                    <li>Execute e faça login com o email e senha do restaurante</li>
                    <li>Selecione a impressora térmica instalada</li>
                    <li>O agente conectará automaticamente e imprimirá as comandas</li>
                  </ol>
                  <div className="rounded-md bg-muted/50 p-3">
                    <div className="text-xs text-[var(--text-muted)]">Endereço do servidor:</div>
                    <code className="text-sm font-mono text-[var(--text-primary)]">{window.location.origin}</code>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </AdminLayout>
  );
}
