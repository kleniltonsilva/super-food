import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
import {
  MessageCircle,
  Bot,
  RefreshCw,
  Power,
  PowerOff,
  ShoppingBag,
  Star,
  TrendingUp,
  MessageSquare,
  Settings2,
  Eye,
  Mic,
  Volume2,
  Percent,
  Ban,
  CalendarClock,
  Printer,
  Heart,
  AlertTriangle,
  ChevronRight,
  Phone,
  User,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import {
  useBotConfig,
  useAtualizarBotConfig,
  useAtivarBot,
  useDesativarBot,
  useBotDashboard,
  useBotConversas,
  useBotMensagens,
} from "@/admin/hooks/useAdminQueries";
import { useFeatureFlag } from "@/admin/hooks/useFeatureFlag";
import { cn } from "@/lib/utils";

type TabType = "dashboard" | "config" | "conversas";

const VOZES = [
  { value: "rex", label: "Rex (masculino)" },
  { value: "leo", label: "Leo (masculino)" },
  { value: "sal", label: "Sal (masculino)" },
  { value: "eve", label: "Eve (feminino)" },
  { value: "ara", label: "Ara (feminino)" },
  { value: "una", label: "Una (feminino)" },
];

const TONS = [
  { value: "amigavel", label: "Amigável e descontraído" },
  { value: "profissional", label: "Profissional e cordial" },
  { value: "divertido", label: "Divertido e bem-humorado" },
  { value: "formal", label: "Formal e respeitoso" },
];

const COMPORTAMENTO_FECHADO = [
  { value: "informar_horario", label: "Informar horário de abertura" },
  { value: "aceitar_agendamento", label: "Aceitar agendamentos" },
  { value: "recusar_educado", label: "Recusar educadamente" },
];

const ESTOQUE_ESGOTADO = [
  { value: "sugerir_similar", label: "Sugerir item similar" },
  { value: "informar_apenas", label: "Apenas informar" },
  { value: "remover_silencioso", label: "Não mostrar item" },
];

const CANCELAMENTO_STATUS = [
  { value: "pendente", label: "Só pendente" },
  { value: "em_preparo", label: "Até em preparo" },
  { value: "pronto", label: "Até pronto" },
];

const RECLAMACAO_ACAO = [
  { value: "desculpar_registrar", label: "Pedir desculpas e registrar" },
  { value: "oferecer_credito", label: "Oferecer crédito automático" },
  { value: "escalar_dono", label: "Escalar para o dono" },
];

export default function BotWhatsApp() {
  const [tab, setTab] = useState<TabType>("dashboard");
  const [conversaSelecionada, setConversaSelecionada] = useState<number | null>(null);
  const [showDesativarDialog, setShowDesativarDialog] = useState(false);
  const [configLocal, setConfigLocal] = useState<Record<string, unknown>>({});
  const [configDirty, setConfigDirty] = useState(false);

  const { hasFeature, requiredPlano } = useFeatureFlag("bot_whatsapp");
  const { data: botConfig, isLoading: loadingConfig, refetch: refetchConfig } = useBotConfig();
  const { data: dashboard, isLoading: loadingDash } = useBotDashboard();
  const { data: conversas, isLoading: loadingConversas } = useBotConversas({ limit: 50 });
  const { data: mensagensData } = useBotMensagens(conversaSelecionada || 0);

  const ativarBot = useAtivarBot();
  const desativarBot = useDesativarBot();
  const atualizarConfig = useAtualizarBotConfig();

  // Merge config do servidor com alterações locais
  const cfg = { ...(botConfig || {}), ...configLocal };

  function updateLocal(campo: string, valor: unknown) {
    setConfigLocal((prev) => ({ ...prev, [campo]: valor }));
    setConfigDirty(true);
  }

  async function salvarConfig() {
    try {
      await atualizarConfig.mutateAsync(configLocal);
      setConfigLocal({});
      setConfigDirty(false);
      toast.success("Configurações salvas!");
    } catch {
      toast.error("Erro ao salvar configurações");
    }
  }

  async function handleAtivar() {
    try {
      await ativarBot.mutateAsync();
      toast.success("Bot WhatsApp ativado!");
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erro ao ativar bot");
    }
  }

  async function handleDesativar() {
    try {
      await desativarBot.mutateAsync();
      setShowDesativarDialog(false);
      toast.success("Bot WhatsApp desativado");
    } catch {
      toast.error("Erro ao desativar bot");
    }
  }

  // Feature bloqueada
  if (!hasFeature) {
    return (
      <AdminLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Bot className="h-16 w-16 text-[var(--text-muted)] mb-4" />
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
            WhatsApp Humanoide
          </h2>
          <p className="text-[var(--text-secondary)] mb-4 max-w-md">
            Atendimento inteligente por WhatsApp com IA. Disponível no plano{" "}
            <strong>{requiredPlano}</strong>.
          </p>
          <Button
            onClick={() => (window.location.href = "/admin/billing/planos")}
            style={{ backgroundColor: "var(--cor-primaria)" }}
          >
            Ver planos
          </Button>
        </div>
      </AdminLayout>
    );
  }

  // Bot não configurado (Super Admin precisa criar a instância)
  if (!loadingConfig && botConfig && !botConfig.configurado) {
    return (
      <AdminLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <MessageCircle className="h-16 w-16 text-amber-400 mb-4" />
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
            Humanoide ainda não configurado
          </h2>
          <p className="text-[var(--text-secondary)] max-w-md">
            O atendente IA WhatsApp precisa ser ativado pela equipe Derekh Food.
            Entre em contato pelo suporte para solicitar a configuração da sua
            instância WhatsApp.
          </p>
        </div>
      </AdminLayout>
    );
  }

  const tabs: { id: TabType; label: string; icon: typeof Bot }[] = [
    { id: "dashboard", label: "Dashboard", icon: TrendingUp },
    { id: "config", label: "Configurações", icon: Settings2 },
    { id: "conversas", label: "Conversas", icon: MessageSquare },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="h-7 w-7 text-green-400" />
            <div>
              <h1 className="text-xl font-bold text-[var(--text-primary)]">
                WhatsApp Humanoide
              </h1>
              <p className="text-sm text-[var(--text-muted)]">
                Atendente IA inteligente — {cfg.nome_atendente || "Bot"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge
              className={cn(
                "text-xs",
                cfg.bot_ativo
                  ? "bg-green-500/20 text-green-400"
                  : "bg-red-500/20 text-red-400"
              )}
            >
              {cfg.bot_ativo ? "Ativo" : "Inativo"}
            </Badge>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => refetchConfig()}
              className="border-[var(--border-subtle)]"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Ativar / Desativar */}
        {cfg.configurado && (
          <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)]">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    "h-3 w-3 rounded-full",
                    cfg.bot_ativo ? "bg-green-400 animate-pulse" : "bg-red-400"
                  )}
                />
                <div>
                  <p className="font-medium text-[var(--text-primary)]">
                    {cfg.bot_ativo ? "Bot está atendendo" : "Bot está desligado"}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {cfg.whatsapp_numero
                      ? `Número: ${cfg.whatsapp_numero}`
                      : "Número não configurado"}
                    {cfg.evolution_instance && ` • Instância: ${cfg.evolution_instance}`}
                  </p>
                </div>
              </div>
              {cfg.bot_ativo ? (
                <Button
                  variant="outline"
                  size="sm"
                  className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                  onClick={() => setShowDesativarDialog(true)}
                >
                  <PowerOff className="h-4 w-4 mr-1" />
                  Desativar
                </Button>
              ) : (
                <Button
                  size="sm"
                  className="bg-green-600 hover:bg-green-700 text-white"
                  onClick={handleAtivar}
                  disabled={ativarBot.isPending}
                >
                  <Power className="h-4 w-4 mr-1" />
                  Ativar Bot
                </Button>
              )}
            </div>
          </Card>
        )}

        {/* Tabs */}
        <div className="flex gap-2">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                tab === t.id
                  ? "text-white"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
              )}
              style={tab === t.id ? { backgroundColor: "var(--cor-primaria)" } : undefined}
            >
              <t.icon className="h-4 w-4" />
              {t.label}
            </button>
          ))}
        </div>

        {/* ═══ TAB: Dashboard ═══ */}
        {tab === "dashboard" && (
          <div className="space-y-4">
            {/* Cards Métricas */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard
                icon={MessageSquare}
                label="Conversas hoje"
                value={dashboard?.conversas_hoje ?? 0}
                sub={`${dashboard?.conversas_semana ?? 0} esta semana`}
                color="text-blue-400"
              />
              <MetricCard
                icon={ShoppingBag}
                label="Pedidos via bot"
                value={dashboard?.pedidos_bot_hoje ?? 0}
                sub={`${dashboard?.pedidos_bot_semana ?? 0} esta semana`}
                color="text-green-400"
              />
              <MetricCard
                icon={TrendingUp}
                label="Faturamento bot"
                value={`R$ ${(dashboard?.faturamento_bot ?? 0).toFixed(2)}`}
                sub="últimos 7 dias"
                color="text-emerald-400"
              />
              <MetricCard
                icon={Star}
                label="Avaliação média"
                value={
                  dashboard?.avaliacao_media
                    ? `${Number(dashboard.avaliacao_media).toFixed(1)} ⭐`
                    : "—"
                }
                sub={`${dashboard?.total_avaliacoes ?? 0} avaliações`}
                color="text-amber-400"
              />
            </div>

            {/* Uso tokens */}
            <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)]">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-[var(--text-primary)]">
                  Uso de tokens hoje
                </span>
                <span className="text-xs text-[var(--text-muted)]">
                  {cfg.tokens_usados_hoje?.toLocaleString() ?? 0} /{" "}
                  {cfg.max_tokens_dia?.toLocaleString() ?? "∞"}
                </span>
              </div>
              <div className="h-2 bg-[var(--bg-surface)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 rounded-full transition-all"
                  style={{
                    width: `${Math.min(
                      100,
                      cfg.max_tokens_dia
                        ? ((cfg.tokens_usados_hoje || 0) / cfg.max_tokens_dia) * 100
                        : 0
                    )}%`,
                  }}
                />
              </div>
            </Card>

            {/* Problemas + Avaliações */}
            <div className="grid md:grid-cols-2 gap-4">
              <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)]">
                <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2 flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  Problemas reportados
                </h3>
                <p className="text-2xl font-bold text-[var(--text-primary)]">
                  {dashboard?.problemas_semana ?? 0}
                </p>
                <p className="text-xs text-[var(--text-muted)]">últimos 7 dias</p>
              </Card>
              <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)]">
                <h3 className="text-sm font-medium text-[var(--text-primary)] mb-2 flex items-center gap-2">
                  <Heart className="h-4 w-4 text-pink-400" />
                  Conversas ativas agora
                </h3>
                <p className="text-2xl font-bold text-[var(--text-primary)]">
                  {dashboard?.conversas_ativas ?? 0}
                </p>
                <p className="text-xs text-[var(--text-muted)]">em atendimento</p>
              </Card>
            </div>
          </div>
        )}

        {/* ═══ TAB: Configurações ═══ */}
        {tab === "config" && (
          <div className="space-y-6">
            {/* Identidade */}
            <ConfigSection title="Identidade do Atendente" icon={User}>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-[var(--text-secondary)]">Nome do atendente</Label>
                  <Input
                    value={(cfg.nome_atendente as string) || ""}
                    onChange={(e) => updateLocal("nome_atendente", e.target.value)}
                    placeholder="Ex: Júlia"
                    className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
                  />
                </div>
                <div>
                  <Label className="text-[var(--text-secondary)]">Tom de personalidade</Label>
                  <Select
                    value={(cfg.tom_personalidade as string) || "amigavel"}
                    onValueChange={(v) => updateLocal("tom_personalidade", v)}
                  >
                    <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {TONS.map((t) => (
                        <SelectItem key={t.value} value={t.value}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[var(--text-secondary)]">Voz (áudio)</Label>
                  <Select
                    value={(cfg.voz_tts as string) || "rex"}
                    onValueChange={(v) => updateLocal("voz_tts", v)}
                  >
                    <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {VOZES.map((v) => (
                        <SelectItem key={v.value} value={v.value}>
                          {v.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </ConfigSection>

            {/* Áudio */}
            <ConfigSection title="Áudio" icon={Volume2}>
              <div className="space-y-3">
                <ToggleRow
                  label="Entender áudios (STT)"
                  desc="O bot transcreve áudios de voz do cliente"
                  icon={Mic}
                  checked={!!cfg.stt_ativo}
                  onChange={(v) => updateLocal("stt_ativo", v)}
                />
                <ToggleRow
                  label="Responder com áudio (TTS)"
                  desc="O bot decide automaticamente quando responder com voz"
                  icon={Volume2}
                  checked={!!cfg.tts_autonomo}
                  onChange={(v) => updateLocal("tts_autonomo", v)}
                />
              </div>
            </ConfigSection>

            {/* Capacidades */}
            <ConfigSection title="Capacidades" icon={Settings2}>
              <div className="space-y-3">
                <ToggleRow
                  label="Criar pedidos"
                  desc="O bot pode anotar e enviar pedidos diretamente para a cozinha"
                  icon={ShoppingBag}
                  checked={!!cfg.pode_criar_pedido}
                  onChange={(v) => updateLocal("pode_criar_pedido", v)}
                />
                <ToggleRow
                  label="Alterar pedidos"
                  desc="Permitir alteração de itens em pedidos já feitos"
                  icon={Settings2}
                  checked={!!cfg.pode_alterar_pedido}
                  onChange={(v) => updateLocal("pode_alterar_pedido", v)}
                />
                <ToggleRow
                  label="Cancelar pedidos"
                  desc="Permitir cancelamento pelo bot"
                  icon={Ban}
                  checked={!!cfg.pode_cancelar_pedido}
                  onChange={(v) => updateLocal("pode_cancelar_pedido", v)}
                />
                {!!cfg.pode_cancelar_pedido && (
                  <div className="ml-10 grid md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-[var(--text-secondary)] text-xs">
                        Cancelar até status
                      </Label>
                      <Select
                        value={(cfg.cancelamento_ate_status as string) || "em_preparo"}
                        onValueChange={(v) => updateLocal("cancelamento_ate_status", v)}
                      >
                        <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {CANCELAMENTO_STATUS.map((s) => (
                            <SelectItem key={s.value} value={s.value}>
                              {s.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-[var(--text-secondary)] text-xs">
                        Taxa cancelamento (%)
                      </Label>
                      <Input
                        type="number"
                        min={0}
                        max={100}
                        value={(cfg.taxa_cancelamento as number) ?? 0}
                        onChange={(e) =>
                          updateLocal("taxa_cancelamento", Number(e.target.value))
                        }
                        className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
                      />
                    </div>
                  </div>
                )}
                <ToggleRow
                  label="Dar descontos"
                  desc="Em situações de problema ou reclamação"
                  icon={Percent}
                  checked={!!cfg.pode_dar_desconto}
                  onChange={(v) => updateLocal("pode_dar_desconto", v)}
                />
                {!!cfg.pode_dar_desconto && (
                  <div className="ml-10">
                    <Label className="text-[var(--text-secondary)] text-xs">
                      Desconto máximo (%)
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      max={50}
                      value={(cfg.desconto_maximo_pct as number) ?? 10}
                      onChange={(e) =>
                        updateLocal("desconto_maximo_pct", Number(e.target.value))
                      }
                      className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] w-32"
                    />
                  </div>
                )}
                <ToggleRow
                  label="Reembolsos"
                  desc="Oferecer reembolso em problemas com pedidos"
                  icon={TrendingUp}
                  checked={!!cfg.pode_reembolsar}
                  onChange={(v) => updateLocal("pode_reembolsar", v)}
                />
                {!!cfg.pode_reembolsar && (
                  <div className="ml-10">
                    <Label className="text-[var(--text-secondary)] text-xs">
                      Valor máximo reembolso (R$)
                    </Label>
                    <Input
                      type="number"
                      min={1}
                      value={(cfg.reembolso_maximo_valor as number) ?? 50}
                      onChange={(e) =>
                        updateLocal("reembolso_maximo_valor", Number(e.target.value))
                      }
                      className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] w-32"
                    />
                  </div>
                )}
                <ToggleRow
                  label="Receber Pix"
                  desc="Gerar cobrança Pix para pagamento online"
                  icon={TrendingUp}
                  checked={!!cfg.pode_receber_pix}
                  onChange={(v) => updateLocal("pode_receber_pix", v)}
                />
                <ToggleRow
                  label="Agendar pedidos"
                  desc="Aceitar pedidos para horário futuro"
                  icon={CalendarClock}
                  checked={!!cfg.pode_agendar}
                  onChange={(v) => updateLocal("pode_agendar", v)}
                />
                <ToggleRow
                  label="Impressão automática"
                  desc="Pedidos via bot vão direto para impressão e cozinha"
                  icon={Printer}
                  checked={!!cfg.impressao_automatica_bot}
                  onChange={(v) => updateLocal("impressao_automatica_bot", v)}
                />
              </div>
            </ConfigSection>

            {/* Comportamento */}
            <ConfigSection title="Comportamento" icon={Bot}>
              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <Label className="text-[var(--text-secondary)]">
                    Quando restaurante fechado
                  </Label>
                  <Select
                    value={(cfg.comportamento_fechado as string) || "informar_horario"}
                    onValueChange={(v) => updateLocal("comportamento_fechado", v)}
                  >
                    <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {COMPORTAMENTO_FECHADO.map((c) => (
                        <SelectItem key={c.value} value={c.value}>
                          {c.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="text-[var(--text-secondary)]">
                    Item esgotado
                  </Label>
                  <Select
                    value={(cfg.estoque_esgotado_acao as string) || "sugerir_similar"}
                    onValueChange={(v) => updateLocal("estoque_esgotado_acao", v)}
                  >
                    <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ESTOQUE_ESGOTADO.map((e) => (
                        <SelectItem key={e.value} value={e.value}>
                          {e.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </ConfigSection>

            {/* Pós-entrega */}
            <ConfigSection title="Pós-entrega" icon={Heart}>
              <div className="space-y-3">
                <ToggleRow
                  label="Avaliação pós-entrega"
                  desc="Enviar mensagem pedindo nota após a entrega"
                  icon={Star}
                  checked={!!cfg.avaliacao_ativa}
                  onChange={(v) => updateLocal("avaliacao_ativa", v)}
                />
                {!!cfg.avaliacao_ativa && (
                  <div className="ml-10">
                    <Label className="text-[var(--text-secondary)] text-xs">
                      Delay após entrega (minutos)
                    </Label>
                    <Input
                      type="number"
                      min={5}
                      max={60}
                      value={(cfg.delay_avaliacao_min as number) ?? 10}
                      onChange={(e) =>
                        updateLocal("delay_avaliacao_min", Number(e.target.value))
                      }
                      className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] w-32"
                    />
                  </div>
                )}
                <div>
                  <Label className="text-[var(--text-secondary)]">
                    Ação em reclamação
                  </Label>
                  <Select
                    value={(cfg.reclamacao_acao as string) || "desculpar_registrar"}
                    onValueChange={(v) => updateLocal("reclamacao_acao", v)}
                  >
                    <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {RECLAMACAO_ACAO.map((r) => (
                        <SelectItem key={r.value} value={r.value}>
                          {r.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </ConfigSection>

            {/* Repescagem */}
            <ConfigSection title="Repescagem" icon={Heart}>
              <div className="space-y-3">
                <ToggleRow
                  label="Repescagem automática"
                  desc="Enviar mensagem para clientes inativos"
                  icon={MessageCircle}
                  checked={!!cfg.repescagem_ativa}
                  onChange={(v) => updateLocal("repescagem_ativa", v)}
                />
                {!!cfg.repescagem_ativa && (
                  <div className="ml-10 grid md:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-[var(--text-secondary)] text-xs">
                        Dias de inatividade
                      </Label>
                      <Input
                        type="number"
                        min={3}
                        max={90}
                        value={(cfg.repescagem_dias_inativo as number) ?? 15}
                        onChange={(e) =>
                          updateLocal("repescagem_dias_inativo", Number(e.target.value))
                        }
                        className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
                      />
                    </div>
                    <div>
                      <Label className="text-[var(--text-secondary)] text-xs">
                        Desconto repescagem (%)
                      </Label>
                      <Input
                        type="number"
                        min={5}
                        max={30}
                        value={(cfg.repescagem_desconto_pct as number) ?? 10}
                        onChange={(e) =>
                          updateLocal("repescagem_desconto_pct", Number(e.target.value))
                        }
                        className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
                      />
                    </div>
                  </div>
                )}
              </div>
            </ConfigSection>

            {/* Botão salvar */}
            {configDirty && (
              <div className="sticky bottom-4 flex justify-end">
                <Button
                  onClick={salvarConfig}
                  disabled={atualizarConfig.isPending}
                  className="text-white shadow-lg"
                  style={{ backgroundColor: "var(--cor-primaria)" }}
                >
                  {atualizarConfig.isPending ? "Salvando..." : "Salvar configurações"}
                </Button>
              </div>
            )}
          </div>
        )}

        {/* ═══ TAB: Conversas ═══ */}
        {tab === "conversas" && (
          <div className="grid md:grid-cols-3 gap-4">
            {/* Lista de conversas */}
            <div className="md:col-span-1 space-y-2">
              <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-2">
                Conversas recentes
              </h3>
              {loadingConversas && (
                <p className="text-sm text-[var(--text-muted)]">Carregando...</p>
              )}
              {!loadingConversas && (!conversas || conversas.length === 0) && (
                <div className="flex flex-col items-center py-8 text-center">
                  <MessageSquare className="h-10 w-10 text-[var(--text-muted)] mb-2" />
                  <p className="text-sm text-[var(--text-muted)]">
                    Nenhuma conversa ainda
                  </p>
                </div>
              )}
              {Array.isArray(conversas) &&
                conversas.map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => setConversaSelecionada(c.id)}
                    className={cn(
                      "w-full text-left p-3 rounded-lg border transition-colors",
                      conversaSelecionada === c.id
                        ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/10"
                        : "border-[var(--border-subtle)] bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)]"
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Phone className="h-3.5 w-3.5 text-[var(--text-muted)]" />
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {c.nome_cliente || c.telefone?.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3") || "Desconhecido"}
                        </span>
                      </div>
                      <Badge
                        className={cn(
                          "text-[10px]",
                          c.status === "ativa"
                            ? "bg-green-500/20 text-green-400"
                            : c.status === "finalizada"
                            ? "bg-gray-500/20 text-gray-400"
                            : "bg-amber-500/20 text-amber-400"
                        )}
                      >
                        {c.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-[var(--text-muted)]">
                        {c.msgs_recebidas} msg recebidas • {c.msgs_enviadas} enviadas
                      </span>
                    </div>
                    {c.intencao_atual && (
                      <span className="text-xs text-[var(--text-muted)] italic">
                        Intenção: {c.intencao_atual}
                      </span>
                    )}
                    {c.atualizado_em && (
                      <span className="text-xs text-[var(--text-muted)] block mt-0.5">
                        <Clock className="h-3 w-3 inline mr-1" />
                        {new Date(c.atualizado_em).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    )}
                  </button>
                ))}
            </div>

            {/* Detalhe conversa */}
            <div className="md:col-span-2">
              {!conversaSelecionada ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <Eye className="h-10 w-10 text-[var(--text-muted)] mb-2" />
                  <p className="text-sm text-[var(--text-muted)]">
                    Selecione uma conversa para ver as mensagens
                  </p>
                </div>
              ) : (
                <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)] h-[60vh] flex flex-col">
                  {/* Header conversa */}
                  {mensagensData?.conversa && (
                    <div className="flex items-center gap-2 pb-3 border-b border-[var(--border-subtle)]">
                      <User className="h-5 w-5 text-[var(--text-muted)]" />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">
                          {mensagensData.conversa.nome_cliente || "Cliente"}
                        </p>
                        <p className="text-xs text-[var(--text-muted)]">
                          {mensagensData.conversa.telefone}
                        </p>
                      </div>
                    </div>
                  )}

                  {/* Mensagens */}
                  <div className="flex-1 overflow-y-auto py-3 space-y-3">
                    {mensagensData?.mensagens?.map((m: any) => (
                      <div
                        key={m.id}
                        className={cn(
                          "flex",
                          m.direcao === "enviada" ? "justify-end" : "justify-start"
                        )}
                      >
                        <div
                          className={cn(
                            "max-w-[75%] rounded-lg px-3 py-2 text-sm",
                            m.direcao === "enviada"
                              ? "bg-green-600/20 text-[var(--text-primary)]"
                              : "bg-[var(--bg-surface)] text-[var(--text-primary)]"
                          )}
                        >
                          <p className="whitespace-pre-wrap">{m.conteudo}</p>
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-[10px] text-[var(--text-muted)]">
                              {m.criado_em &&
                                new Date(m.criado_em).toLocaleTimeString("pt-BR", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                            </span>
                            {m.tipo === "audio" && (
                              <Mic className="h-3 w-3 text-[var(--text-muted)]" />
                            )}
                            {m.tempo_resposta_ms && (
                              <span className="text-[10px] text-[var(--text-muted)]">
                                {m.tempo_resposta_ms}ms
                              </span>
                            )}
                          </div>
                          {m.function_calls && (
                            <p className="text-[10px] text-blue-400 mt-1">
                              {m.function_calls}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                    {(!mensagensData?.mensagens || mensagensData.mensagens.length === 0) && (
                      <p className="text-center text-sm text-[var(--text-muted)] py-8">
                        Nenhuma mensagem
                      </p>
                    )}
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Dialog desativar */}
      <AlertDialog open={showDesativarDialog} onOpenChange={setShowDesativarDialog}>
        <AlertDialogContent className="bg-[var(--bg-card)] border-[var(--border-subtle)]">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-[var(--text-primary)]">
              Desativar bot WhatsApp?
            </AlertDialogTitle>
            <AlertDialogDescription className="text-[var(--text-secondary)]">
              O atendente IA deixará de responder mensagens. Conversas em andamento
              serão encerradas. Você pode reativar a qualquer momento.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[var(--border-subtle)] text-[var(--text-secondary)]">
              Cancelar
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDesativar}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              Desativar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}

// ─── Componentes auxiliares ──────────────────────────────

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: typeof Bot;
  label: string;
  value: string | number;
  sub: string;
  color: string;
}) {
  return (
    <Card className="p-4 bg-[var(--bg-card)] border-[var(--border-subtle)]">
      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn("h-4 w-4", color)} />
        <span className="text-xs text-[var(--text-muted)]">{label}</span>
      </div>
      <p className="text-xl font-bold text-[var(--text-primary)]">{value}</p>
      <p className="text-xs text-[var(--text-muted)]">{sub}</p>
    </Card>
  );
}

function ConfigSection({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: typeof Bot;
  children: React.ReactNode;
}) {
  return (
    <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
      <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
        <Icon className="h-4 w-4 text-[var(--text-muted)]" />
        {title}
      </h3>
      {children}
    </Card>
  );
}

function ToggleRow({
  label,
  desc,
  icon: Icon,
  checked,
  onChange,
}: {
  label: string;
  desc: string;
  icon: typeof Bot;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-3">
        <Icon className="h-4 w-4 text-[var(--text-muted)]" />
        <div>
          <p className="text-sm font-medium text-[var(--text-primary)]">{label}</p>
          <p className="text-xs text-[var(--text-muted)]">{desc}</p>
        </div>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}
