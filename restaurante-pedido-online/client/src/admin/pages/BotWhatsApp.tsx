import { useState, useEffect, useCallback, useRef } from "react";
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
  BarChart3,
  Users,
  Shield,
  MapPin,
  ThumbsUp,
  ThumbsDown,
  FileText,
  UserMinus,
  Gift,
  Send,
  Mail,
  CheckSquare,
  Square,
  Search,
  Smartphone,
  ArrowRight,
  Upload,
  CheckCircle2,
  Loader2,
  Pencil,
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
  useEnviarMensagemBot,
  useEscalarConversaBot,
  useRecusarHandoffBot,
  useDevolverBotConversa,
  useBotRelatorioEficiencia,
  useBotRelatorioSatisfacao,
  useBotRelatorioClientesInativos,
  useBotRelatorioErrosContornados,
  useBotRepescagemHistorico,
  useCriarRepescagemEmMassa,
  usePhoneStatus,
  useAddonPaymentStatus,
  useRegistrarPhone,
  useSolicitarCodigo,
  useVerificarCodigo,
  useAtualizarPerfilPhone,
  useUploadFotoPerfilPhone,
  useTrocarNumero,
  useEmbeddedSignupConfig,
  useEmbeddedSignupCallback,
  useContratarAddonBot,
} from "@/admin/hooks/useAdminQueries";
import { useFeatureFlag } from "@/admin/hooks/useFeatureFlag";
import { cn } from "@/lib/utils";

type TabType = "dashboard" | "config" | "conversas" | "relatorios" | "repescagem";

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

const POLITICA_ACOES = [
  { value: "desculpar", label: "Apenas pedir desculpas" },
  { value: "desconto_proximo", label: "Cupom desconto próximo pedido" },
  { value: "brinde_reenviar", label: "Item como brinde + reenviar correto" },
  { value: "reembolso_parcial", label: "Reembolso parcial" },
];

const PERIODOS = [
  { value: "7d", label: "7 dias" },
  { value: "30d", label: "30 dias" },
  { value: "90d", label: "90 dias" },
];

export default function BotWhatsApp() {
  const [tab, setTab] = useState<TabType>("dashboard");
  const [conversaSelecionada, setConversaSelecionada] = useState<number | null>(null);
  const [showDesativarDialog, setShowDesativarDialog] = useState(false);
  const [configLocal, setConfigLocal] = useState<Record<string, unknown>>({});
  const [configDirty, setConfigDirty] = useState(false);
  const [msgTexto, setMsgTexto] = useState("");
  const [senhaHandoff, setSenhaHandoff] = useState("");
  const [showHandoffDialog, setShowHandoffDialog] = useState<number | null>(null);
  const [buscaConversas, setBuscaConversas] = useState("");
  const [buscaDebounced, setBuscaDebounced] = useState("");
  const [showEditarPerfil, setShowEditarPerfil] = useState(false);
  const [showTrocarNumero, setShowTrocarNumero] = useState(false);
  const [periodoRelatorio, setPeriodoRelatorio] = useState("30d");

  // Auto-selecionar conversa vinda da notificação (?conversa=ID)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const conversaParam = params.get("conversa");
    if (conversaParam) {
      const id = Number(conversaParam);
      if (id > 0) {
        setTab("conversas");
        setConversaSelecionada(id);
      }
      // Limpar param da URL sem reload
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, []);

  // Debounce busca conversas (500ms)
  useEffect(() => {
    const timer = setTimeout(() => setBuscaDebounced(buscaConversas), 500);
    return () => clearTimeout(timer);
  }, [buscaConversas]);

  const { hasFeature, requiredPlano, addonActive, canSubscribeAddon } = useFeatureFlag("bot_whatsapp");
  const { data: botConfig, isLoading: loadingConfig, refetch: refetchConfig } = useBotConfig();
  const { data: phoneStatusData, refetch: refetchPhone } = usePhoneStatus();
  const { data: dashboard, isLoading: loadingDash } = useBotDashboard();
  const { data: conversasData, isLoading: loadingConversas } = useBotConversas({
    limit: 50,
    busca: buscaDebounced || undefined,
  });
  const conversasList = conversasData?.conversas || [];
  const { data: mensagensData } = useBotMensagens(conversaSelecionada || 0);

  const ativarBot = useAtivarBot();
  const desativarBot = useDesativarBot();
  const atualizarConfig = useAtualizarBotConfig();
  const enviarMensagem = useEnviarMensagemBot();
  const escalarConversa = useEscalarConversaBot();
  const recusarHandoff = useRecusarHandoffBot();
  const devolverBot = useDevolverBotConversa();

  const { data: relEficiencia } = useBotRelatorioEficiencia(periodoRelatorio);
  const { data: relSatisfacao } = useBotRelatorioSatisfacao(periodoRelatorio);
  const { data: relInativos } = useBotRelatorioClientesInativos();
  const { data: relErros } = useBotRelatorioErrosContornados(periodoRelatorio);

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

  // Feature bloqueada — só bloquear se NÃO pode contratar addon (plano Basico)
  // Essencial/Avançado sem addon: deixar entrar no wizard (backend cuida do billing inline)
  if (!hasFeature && !canSubscribeAddon) {
    return (
      <AdminLayout>
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Bot className="h-16 w-16 text-[var(--text-muted)] mb-4" />
          <h2 className="text-xl font-bold text-[var(--text-primary)] mb-2">
            WhatsApp Humanoide
          </h2>
          <p className="text-[var(--text-secondary)] mb-4 max-w-md">
            Atendimento inteligente por WhatsApp com IA.
            {` Disponivel a partir do plano ${requiredPlano}.`}
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

  // Wizard de onboarding self-service (se telefone não está ativo)
  const regStatus = phoneStatusData?.registration_status || "none";
  const needsOnboarding = (!botConfig?.configurado || regStatus !== "active") && regStatus !== "active";

  if (!loadingConfig && needsOnboarding && hasFeature) {
    return (
      <AdminLayout>
        <PhoneOnboardingWizard
          phoneStatus={phoneStatusData}
          regStatus={regStatus}
          refetchPhone={refetchPhone}
          refetchConfig={refetchConfig}
          addonLiberado={hasFeature}
        />
      </AdminLayout>
    );
  }

  const tabs: { id: TabType; label: string; icon: typeof Bot }[] = [
    { id: "dashboard", label: "Dashboard", icon: TrendingUp },
    { id: "config", label: "Configurações", icon: Settings2 },
    { id: "conversas", label: "Conversas", icon: MessageSquare },
    { id: "relatorios", label: "Relatórios", icon: BarChart3 },
    { id: "repescagem", label: "Repescagem", icon: UserMinus },
  ];

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Banner add-on */}
        {addonActive && (
          <div className="flex items-center gap-3 p-3 rounded-lg bg-green-500/10 border border-green-500/30">
            <Bot className="h-5 w-5 text-green-400 shrink-0" />
            <p className="text-sm text-green-400">
              Ativo via add-on (+R$99,45/mes) —{" "}
              <a href="/admin/billing" className="underline hover:no-underline">
                Gerenciar assinatura
              </a>
            </p>
          </div>
        )}

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

        {/* Número ativo + status */}
        {phoneStatusData?.registration_status === "active" && phoneStatusData?.whatsapp_numero && (
          <Card className="p-4 bg-[var(--bg-card)] border-green-500/30">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Smartphone className="h-5 w-5 text-green-400" />
                <div>
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    Número ativo: {phoneStatusData.whatsapp_numero?.replace(/(\d{2})(\d{2})(\d{5})(\d{4})/, "+$1 ($2) $3-$4")}
                  </p>
                  <p className="text-xs text-[var(--text-muted)]">
                    {phoneStatusData.display_name || "WhatsApp Business"}
                  </p>
                </div>
                <Badge className="bg-green-500/20 text-green-400 text-xs">Conectado</Badge>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-[var(--border-subtle)] text-xs"
                  onClick={() => setShowEditarPerfil(true)}
                >
                  <Pencil className="h-3 w-3 mr-1" />
                  Editar Perfil
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-[var(--border-subtle)] text-xs"
                  onClick={() => setShowTrocarNumero(true)}
                >
                  <Phone className="h-3 w-3 mr-1" />
                  Trocar Numero
                </Button>
              </div>
            </div>
          </Card>
        )}

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

            {/* Tokens movidos para Super Admin */}

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

            {/* Políticas de Erro */}
            <ConfigSection title="Políticas de Erro" icon={Shield}>
              <p className="text-xs text-[var(--text-muted)] mb-4">
                Configure ações automáticas quando o bot detectar problemas em pedidos.
              </p>
              {[
                { key: "politica_atraso", label: "Se a entrega atrasar..." },
                { key: "politica_pedido_errado", label: "Se o pedido vier errado..." },
                { key: "politica_item_faltando", label: "Se faltar um item..." },
                { key: "politica_qualidade", label: "Se houver problema de qualidade..." },
              ].map((pol) => {
                const politica = (cfg[pol.key] as Record<string, unknown>) || { acao: "desculpar", desconto_pct: 0, mensagem: "" };
                return (
                  <div key={pol.key} className="mb-4 p-3 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
                    <Label className="text-[var(--text-primary)] text-sm font-medium">{pol.label}</Label>
                    <div className="grid md:grid-cols-2 gap-3 mt-2">
                      <Select
                        value={(politica.acao as string) || "desculpar"}
                        onValueChange={(v) =>
                          updateLocal(pol.key, { ...politica, acao: v })
                        }
                      >
                        <SelectTrigger className="bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {POLITICA_ACOES.map((a) => (
                            <SelectItem key={a.value} value={a.value}>
                              {a.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {["desconto_proximo", "cupom_fixo", "reembolso_parcial"].includes(
                        (politica.acao as string) || ""
                      ) && (
                        <div>
                          <Label className="text-[var(--text-secondary)] text-xs">Desconto (%)</Label>
                          <Input
                            type="number"
                            min={1}
                            max={50}
                            value={(politica.desconto_pct as number) ?? 10}
                            onChange={(e) =>
                              updateLocal(pol.key, { ...politica, desconto_pct: Number(e.target.value) })
                            }
                            className="bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-primary)] w-24"
                          />
                        </div>
                      )}
                    </div>
                    <div className="mt-2">
                      <Label className="text-[var(--text-secondary)] text-xs">Mensagem personalizada (opcional)</Label>
                      <Input
                        value={(politica.mensagem as string) || ""}
                        onChange={(e) =>
                          updateLocal(pol.key, { ...politica, mensagem: e.target.value })
                        }
                        placeholder="Ex: Pedimos desculpas pelo transtorno!"
                        className="bg-[var(--bg-card)] border-[var(--border-subtle)] text-[var(--text-primary)]"
                      />
                    </div>
                  </div>
                );
              })}
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
                <ToggleRow
                  label="Perguntar se houve problema antes da nota"
                  desc="O bot pergunta 'tudo ok?' antes de pedir nota 1-5"
                  icon={MessageCircle}
                  checked={!!cfg.avaliacao_perguntar_problemas}
                  onChange={(v) => updateLocal("avaliacao_perguntar_problemas", v)}
                />
                <ToggleRow
                  label="Pedir review no Google Maps (5 estrelas)"
                  desc="Quando cliente dá nota máxima, sugere avaliar no Google Maps"
                  icon={MapPin}
                  checked={!!cfg.avaliacao_pedir_google_review}
                  onChange={(v) => updateLocal("avaliacao_pedir_google_review", v)}
                />
                {!!cfg.avaliacao_pedir_google_review && (
                  <div className="ml-10">
                    <Label className="text-[var(--text-secondary)] text-xs">
                      URL Google Maps do restaurante
                    </Label>
                    <Input
                      value={(cfg.google_maps_url as string) || ""}
                      onChange={(e) => updateLocal("google_maps_url", e.target.value)}
                      placeholder="https://g.page/r/..."
                      className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
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
                  <div className="ml-10 space-y-3">
                    <ToggleRow
                      label="Detectar frequência individual"
                      desc="Usa IA para calcular o intervalo médio de compra de cada cliente"
                      icon={TrendingUp}
                      checked={!!cfg.repescagem_usar_frequencia}
                      onChange={(v) => updateLocal("repescagem_usar_frequencia", v)}
                    />
                    {!cfg.repescagem_usar_frequencia && (
                      <div>
                        <Label className="text-[var(--text-secondary)] text-xs">
                          Dias de inatividade (modo fixo)
                        </Label>
                        <Input
                          type="number"
                          min={3}
                          max={90}
                          value={(cfg.repescagem_dias_inativo as number) ?? 15}
                          onChange={(e) =>
                            updateLocal("repescagem_dias_inativo", Number(e.target.value))
                          }
                          className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] w-32"
                        />
                      </div>
                    )}
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
                        className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] w-32"
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
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-[var(--text-muted)]" />
                <Input
                  placeholder="Buscar por nome ou telefone..."
                  value={buscaConversas}
                  onChange={(e) => setBuscaConversas(e.target.value)}
                  className="pl-9 h-9 bg-[var(--bg-surface)] border-[var(--border-subtle)] text-sm"
                />
              </div>
              {loadingConversas && (
                <p className="text-sm text-[var(--text-muted)]">Carregando...</p>
              )}
              {!loadingConversas && conversasList.length === 0 && (
                <div className="flex flex-col items-center py-8 text-center">
                  <MessageSquare className="h-10 w-10 text-[var(--text-muted)] mb-2" />
                  <p className="text-sm text-[var(--text-muted)]">
                    Nenhuma conversa ainda
                  </p>
                </div>
              )}
              {conversasList.map((c: any) => (
                  <button
                    key={c.id}
                    onClick={() => setConversaSelecionada(c.id)}
                    className={cn(
                      "w-full text-left p-3 rounded-lg border transition-colors",
                      conversaSelecionada === c.id
                        ? "border-[var(--cor-primaria)] bg-[var(--cor-primaria)]/10"
                        : "border-[var(--border-subtle)] bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)]",
                      (c.status === "aguardando_handoff") && "ring-2 ring-red-500/50 animate-pulse"
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
                            : c.status === "handoff"
                            ? "bg-blue-500/20 text-blue-400"
                            : c.status === "aguardando_handoff"
                            ? "bg-red-500/20 text-red-400"
                            : "bg-amber-500/20 text-amber-400"
                        )}
                      >
                        {c.status === "aguardando_handoff" ? "QUER HUMANO" : c.status === "handoff" ? "ADMIN" : c.status}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-xs text-[var(--text-muted)]">
                        {c.msgs_recebidas} msg recebidas • {c.msgs_enviadas} enviadas
                      </span>
                    </div>
                    {c.handoff_motivo && (c.status === "aguardando_handoff" || c.status === "handoff") && (
                      <span className="text-xs text-red-400 italic block mt-0.5">
                        {c.handoff_motivo}
                      </span>
                    )}
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
                  {/* Header conversa + controles handoff */}
                  {mensagensData?.conversa && (
                    <div className="flex items-center justify-between pb-3 border-b border-[var(--border-subtle)]">
                      <div className="flex items-center gap-2">
                        <User className="h-5 w-5 text-[var(--text-muted)]" />
                        <div>
                          <p className="text-sm font-medium text-[var(--text-primary)]">
                            {mensagensData.conversa.nome_cliente || "Cliente"}
                          </p>
                          <p className="text-xs text-[var(--text-muted)]">
                            {mensagensData.conversa.telefone}
                          </p>
                        </div>
                        <Badge
                          className={cn(
                            "text-[10px] ml-2",
                            mensagensData.conversa.status === "handoff"
                              ? "bg-blue-500/20 text-blue-400"
                              : mensagensData.conversa.status === "aguardando_handoff"
                              ? "bg-red-500/20 text-red-400 animate-pulse"
                              : "bg-green-500/20 text-green-400"
                          )}
                        >
                          {mensagensData.conversa.status === "handoff" ? "ADMIN" : mensagensData.conversa.status === "aguardando_handoff" ? "QUER HUMANO" : mensagensData.conversa.status}
                        </Badge>
                      </div>
                      <div className="flex gap-1.5">
                        {/* Botões handoff */}
                        {mensagensData.conversa.status === "aguardando_handoff" && (
                          <>
                            <Button
                              size="sm"
                              variant="default"
                              className="h-7 text-xs bg-green-600 hover:bg-green-700 text-white"
                              onClick={() => {
                                setSenhaHandoff("");
                                setShowHandoffDialog(conversaSelecionada);
                              }}
                            >
                              Aceitar
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-7 text-xs border-red-500/50 text-red-400 hover:bg-red-500/10"
                              disabled={recusarHandoff.isPending}
                              onClick={() => {
                                recusarHandoff.mutate(conversaSelecionada!, {
                                  onSuccess: () => toast.info("Handoff recusado — bot sugeriu ligar"),
                                  onError: () => toast.error("Erro ao recusar handoff"),
                                });
                              }}
                            >
                              Recusar
                            </Button>
                          </>
                        )}
                        {mensagensData.conversa.status === "ativa" && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs"
                            onClick={() => {
                              setSenhaHandoff("");
                              setShowHandoffDialog(conversaSelecionada);
                            }}
                          >
                            <Shield className="h-3 w-3 mr-1" />
                            Assumir
                          </Button>
                        )}
                        {mensagensData.conversa.status === "handoff" && (
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-7 text-xs border-green-500/50 text-green-400 hover:bg-green-500/10"
                            disabled={devolverBot.isPending}
                            onClick={() => {
                              devolverBot.mutate(conversaSelecionada!, {
                                onSuccess: () => toast.success("Conversa devolvida ao bot"),
                                onError: () => toast.error("Erro ao devolver conversa"),
                              });
                            }}
                          >
                            <Bot className="h-3 w-3 mr-1" />
                            Devolver ao Bot
                          </Button>
                        )}
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
                              ? m.conteudo?.startsWith("[ADMIN]")
                                ? "bg-blue-600/20 text-[var(--text-primary)] border border-blue-500/30"
                                : "bg-green-600/20 text-[var(--text-primary)]"
                              : "bg-[var(--bg-surface)] text-[var(--text-primary)]"
                          )}
                        >
                          {m.conteudo?.startsWith("[ADMIN]") && (
                            <span className="text-[10px] text-blue-400 font-semibold block mb-0.5">ADMIN</span>
                          )}
                          <p className="whitespace-pre-wrap">
                            {m.conteudo?.startsWith("[ADMIN] ") ? m.conteudo.slice(8) : m.conteudo}
                          </p>
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
                              {Array.isArray(m.function_calls)
                                ? m.function_calls.map((fc: any) => fc.nome || fc).join(", ")
                                : m.function_calls}
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

                  {/* Input enviar mensagem manual (só quando em handoff) */}
                  {mensagensData?.conversa?.status === "handoff" && (
                    <div className="pt-3 border-t border-[var(--border-subtle)] flex gap-2">
                      <Input
                        value={msgTexto}
                        onChange={(e) => setMsgTexto(e.target.value)}
                        placeholder="Digitar mensagem como admin..."
                        className="flex-1 h-9 text-sm"
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey && msgTexto.trim()) {
                            e.preventDefault();
                            enviarMensagem.mutate(
                              { conversaId: conversaSelecionada!, texto: msgTexto.trim() },
                              {
                                onSuccess: () => { setMsgTexto(""); toast.success("Mensagem enviada"); },
                                onError: () => toast.error("Erro ao enviar mensagem"),
                              }
                            );
                          }
                        }}
                      />
                      <Button
                        size="sm"
                        className="h-9 text-white"
                        style={{ backgroundColor: "var(--cor-primaria)" }}
                        disabled={!msgTexto.trim() || enviarMensagem.isPending}
                        onClick={() => {
                          if (msgTexto.trim()) {
                            enviarMensagem.mutate(
                              { conversaId: conversaSelecionada!, texto: msgTexto.trim() },
                              {
                                onSuccess: () => { setMsgTexto(""); toast.success("Mensagem enviada"); },
                                onError: () => toast.error("Erro ao enviar mensagem"),
                              }
                            );
                          }
                        }}
                      >
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </Card>
              )}

              {/* Dialog senha para handoff */}
              <AlertDialog open={showHandoffDialog !== null} onOpenChange={(open) => { if (!open) setShowHandoffDialog(null); }}>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Assumir controle da conversa</AlertDialogTitle>
                    <AlertDialogDescription>
                      O bot irá parar de responder nesta conversa. Você poderá enviar mensagens manualmente.
                      Digite sua senha de admin para confirmar.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <Input
                    type="password"
                    placeholder="Senha do admin"
                    value={senhaHandoff}
                    onChange={(e) => setSenhaHandoff(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && senhaHandoff.trim() && showHandoffDialog) {
                        escalarConversa.mutate(
                          { conversaId: showHandoffDialog, senha: senhaHandoff.trim() },
                          {
                            onSuccess: () => { setShowHandoffDialog(null); setSenhaHandoff(""); toast.success("Controle assumido!"); },
                            onError: (err: any) => toast.error(err.response?.data?.detail || "Senha incorreta"),
                          }
                        );
                      }
                    }}
                  />
                  <AlertDialogFooter>
                    <AlertDialogCancel onClick={() => { setShowHandoffDialog(null); setSenhaHandoff(""); }}>Cancelar</AlertDialogCancel>
                    <AlertDialogAction
                      disabled={!senhaHandoff.trim() || escalarConversa.isPending}
                      onClick={() => {
                        if (showHandoffDialog && senhaHandoff.trim()) {
                          escalarConversa.mutate(
                            { conversaId: showHandoffDialog, senha: senhaHandoff.trim() },
                            {
                              onSuccess: () => { setShowHandoffDialog(null); setSenhaHandoff(""); toast.success("Controle assumido!"); },
                              onError: (err: any) => toast.error(err.response?.data?.detail || "Senha incorreta"),
                            }
                          );
                        }
                      }}
                    >
                      {escalarConversa.isPending ? "Verificando..." : "Confirmar"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        )}
        {/* ═══ TAB: Relatórios ═══ */}
        {tab === "relatorios" && (
          <div className="space-y-6">
            {/* Filtro período */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--text-secondary)]">Período:</span>
              {PERIODOS.map((p) => (
                <button
                  key={p.value}
                  onClick={() => setPeriodoRelatorio(p.value)}
                  className={cn(
                    "px-3 py-1.5 rounded-lg text-xs font-medium transition-colors",
                    periodoRelatorio === p.value
                      ? "text-white"
                      : "text-[var(--text-secondary)] bg-[var(--bg-card)] hover:bg-[var(--bg-card-hover)]"
                  )}
                  style={
                    periodoRelatorio === p.value
                      ? { backgroundColor: "var(--cor-primaria)" }
                      : undefined
                  }
                >
                  {p.label}
                </button>
              ))}
            </div>

            {/* Eficiência */}
            <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-blue-400" />
                Eficiência do Bot
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <MetricCard
                  icon={MessageSquare}
                  label="Conversas"
                  value={relEficiencia?.total_conversas ?? 0}
                  sub={`${relEficiencia?.total_pedidos_bot ?? 0} pedidos`}
                  color="text-blue-400"
                />
                <MetricCard
                  icon={ShoppingBag}
                  label="Taxa conversão"
                  value={`${relEficiencia?.taxa_conversao ?? 0}%`}
                  sub="conversas → pedidos"
                  color="text-green-400"
                />
                <MetricCard
                  icon={Clock}
                  label="Tempo resposta"
                  value={
                    relEficiencia?.tempo_medio_resposta_ms
                      ? `${(relEficiencia.tempo_medio_resposta_ms / 1000).toFixed(1)}s`
                      : "—"
                  }
                  sub="média por mensagem"
                  color="text-purple-400"
                />
                <MetricCard
                  icon={Bot}
                  label="Resolução bot"
                  value={`${relEficiencia?.taxa_resolucao_bot ?? 0}%`}
                  sub={`${relEficiencia?.conversas_escaladas ?? 0} escaladas`}
                  color="text-emerald-400"
                />
              </div>
              {relEficiencia?.pedidos_por_dia && relEficiencia.pedidos_por_dia.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-2">Pedidos por dia</p>
                    <div className="flex items-end gap-1 h-24">
                      {relEficiencia.pedidos_por_dia.slice(-14).map((d: any, i: number) => {
                        const max = Math.max(...relEficiencia.pedidos_por_dia.map((x: any) => x.pedidos), 1);
                        return (
                          <div
                            key={i}
                            className="flex-1 rounded-t"
                            style={{
                              backgroundColor: "var(--cor-primaria)",
                              height: `${(d.pedidos / max) * 100}%`,
                              minHeight: d.pedidos > 0 ? "4px" : "1px",
                              opacity: d.pedidos > 0 ? 1 : 0.2,
                            }}
                            title={`${d.data}: ${d.pedidos} pedidos`}
                          />
                        );
                      })}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-[var(--text-muted)] mb-2">Faturamento por dia</p>
                    <div className="flex items-end gap-1 h-24">
                      {relEficiencia.faturamento_por_dia?.slice(-14).map((d: any, i: number) => {
                        const max = Math.max(...(relEficiencia.faturamento_por_dia || []).map((x: any) => x.valor), 1);
                        return (
                          <div
                            key={i}
                            className="flex-1 bg-emerald-500 rounded-t"
                            style={{
                              height: `${(d.valor / max) * 100}%`,
                              minHeight: d.valor > 0 ? "4px" : "1px",
                              opacity: d.valor > 0 ? 1 : 0.2,
                            }}
                            title={`${d.data}: R$${d.valor.toFixed(2)}`}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </Card>

            {/* Satisfação */}
            <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                <Star className="h-4 w-4 text-amber-400" />
                Satisfação
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <MetricCard
                  icon={TrendingUp}
                  label="NPS"
                  value={relSatisfacao?.nps ?? "—"}
                  sub={
                    (relSatisfacao?.nps ?? 0) >= 50
                      ? "Excelente!"
                      : (relSatisfacao?.nps ?? 0) >= 0
                      ? "Bom"
                      : "Precisa melhorar"
                  }
                  color={
                    (relSatisfacao?.nps ?? 0) >= 50
                      ? "text-green-400"
                      : (relSatisfacao?.nps ?? 0) >= 0
                      ? "text-amber-400"
                      : "text-red-400"
                  }
                />
                <MetricCard
                  icon={Star}
                  label="Média geral"
                  value={relSatisfacao?.media_geral ? `${relSatisfacao.media_geral}/5` : "—"}
                  sub={`${relSatisfacao?.total_avaliacoes ?? 0} avaliações`}
                  color="text-amber-400"
                />
                <MetricCard
                  icon={ThumbsUp}
                  label="Satisfeitos"
                  value={relSatisfacao?.clientes_satisfeitos ?? 0}
                  sub="nota ≥ 4"
                  color="text-green-400"
                />
                <MetricCard
                  icon={ThumbsDown}
                  label="Insatisfeitos"
                  value={relSatisfacao?.clientes_insatisfeitos ?? 0}
                  sub="nota ≤ 2"
                  color="text-red-400"
                />
              </div>
              {/* Distribuição de notas */}
              {relSatisfacao?.distribuicao_notas && (
                <div className="mb-4">
                  <p className="text-xs text-[var(--text-muted)] mb-2">Distribuição de notas</p>
                  <div className="flex items-end gap-2 h-20">
                    {[1, 2, 3, 4, 5].map((n) => {
                      const qtd = relSatisfacao.distribuicao_notas[String(n)] || 0;
                      const max = Math.max(
                        ...Object.values(relSatisfacao.distribuicao_notas as Record<string, number>),
                        1
                      );
                      const cores = ["bg-red-500", "bg-orange-500", "bg-amber-500", "bg-lime-500", "bg-green-500"];
                      return (
                        <div key={n} className="flex-1 flex flex-col items-center gap-1">
                          <div
                            className={cn("w-full rounded-t", cores[n - 1])}
                            style={{
                              height: `${(qtd / max) * 100}%`,
                              minHeight: qtd > 0 ? "8px" : "2px",
                              opacity: qtd > 0 ? 1 : 0.2,
                            }}
                          />
                          <span className="text-[10px] text-[var(--text-muted)]">{n}★</span>
                          <span className="text-[10px] text-[var(--text-secondary)]">{qtd}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
              {/* Categorias de problemas */}
              {relSatisfacao?.categorias_problemas && relSatisfacao.categorias_problemas.length > 0 && (
                <div>
                  <p className="text-xs text-[var(--text-muted)] mb-2">Problemas por categoria</p>
                  <div className="space-y-2">
                    {relSatisfacao.categorias_problemas.map((cat: any) => (
                      <div key={cat.tipo} className="flex items-center justify-between text-sm">
                        <span className="text-[var(--text-secondary)] capitalize">{cat.tipo.replace("_", " ")}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[var(--text-primary)]">{cat.total}</span>
                          <Badge className="bg-green-500/20 text-green-400 text-[10px]">
                            {cat.resolvido_bot} auto
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {relSatisfacao?.google_reviews_solicitados > 0 && (
                <p className="text-xs text-[var(--text-muted)] mt-3">
                  <MapPin className="h-3 w-3 inline mr-1" />
                  {relSatisfacao.google_reviews_solicitados} reviews Google Maps solicitados
                </p>
              )}
            </Card>

            {/* Clientes Inativos */}
            <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                <Users className="h-4 w-4 text-orange-400" />
                Clientes Inativos
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <MetricCard
                  icon={Users}
                  label="15-30 dias"
                  value={relInativos?.resumo?.inativos_15_30 ?? 0}
                  sub="inativos recentes"
                  color="text-amber-400"
                />
                <MetricCard
                  icon={Users}
                  label="30-60 dias"
                  value={relInativos?.resumo?.inativos_30_60 ?? 0}
                  sub="em risco"
                  color="text-orange-400"
                />
                <MetricCard
                  icon={Users}
                  label="60+ dias"
                  value={relInativos?.resumo?.inativos_60_plus ?? 0}
                  sub="muito inativos"
                  color="text-red-400"
                />
                <MetricCard
                  icon={Heart}
                  label="Taxa retorno"
                  value={`${relInativos?.repescagens?.taxa_retorno ?? 0}%`}
                  sub={`${relInativos?.repescagens?.retornaram ?? 0}/${relInativos?.repescagens?.enviadas_total ?? 0} repescagens`}
                  color="text-green-400"
                />
              </div>
              {relInativos?.clientes && relInativos.clientes.length > 0 && (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="text-[var(--text-muted)] border-b border-[var(--border-subtle)]">
                        <th className="text-left py-2">Cliente</th>
                        <th className="text-center py-2">Pedidos</th>
                        <th className="text-center py-2">Freq. (dias)</th>
                        <th className="text-center py-2">Inativo</th>
                        <th className="text-center py-2">Nota</th>
                        <th className="text-center py-2">Repescagem</th>
                      </tr>
                    </thead>
                    <tbody>
                      {relInativos.clientes.slice(0, 15).map((c: any) => (
                        <tr key={c.id} className="border-b border-[var(--border-subtle)]">
                          <td className="py-2 text-[var(--text-primary)]">{c.nome}</td>
                          <td className="text-center text-[var(--text-secondary)]">{c.total_pedidos}</td>
                          <td className="text-center text-[var(--text-secondary)]">
                            {c.media_intervalo_dias ? `~${c.media_intervalo_dias}` : "—"}
                          </td>
                          <td className="text-center">
                            <Badge
                              className={cn(
                                "text-[10px]",
                                c.dias_inativo >= 60
                                  ? "bg-red-500/20 text-red-400"
                                  : c.dias_inativo >= 30
                                  ? "bg-orange-500/20 text-orange-400"
                                  : "bg-amber-500/20 text-amber-400"
                              )}
                            >
                              {c.dias_inativo}d
                            </Badge>
                          </td>
                          <td className="text-center text-[var(--text-secondary)]">
                            {c.ultima_avaliacao ? `${c.ultima_avaliacao}★` : "—"}
                          </td>
                          <td className="text-center">
                            {c.repescagem_enviada ? (
                              <Badge
                                className={cn(
                                  "text-[10px]",
                                  c.retornou
                                    ? "bg-green-500/20 text-green-400"
                                    : "bg-blue-500/20 text-blue-400"
                                )}
                              >
                                {c.retornou ? "Voltou!" : "Enviada"}
                              </Badge>
                            ) : (
                              <span className="text-[var(--text-muted)]">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            {/* Erros Contornados */}
            <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
              <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
                <Shield className="h-4 w-4 text-purple-400" />
                Erros Contornados
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <MetricCard
                  icon={AlertTriangle}
                  label="Total problemas"
                  value={relErros?.total_problemas ?? 0}
                  sub="no período"
                  color="text-amber-400"
                />
                <MetricCard
                  icon={Bot}
                  label="Resolvidos pelo bot"
                  value={relErros?.resolvidos_bot ?? 0}
                  sub={`${relErros?.taxa_resolucao_automatica ?? 0}% automático`}
                  color="text-green-400"
                />
                <MetricCard
                  icon={User}
                  label="Escalados humano"
                  value={relErros?.escalados_humano ?? 0}
                  sub="precisaram intervenção"
                  color="text-orange-400"
                />
                <MetricCard
                  icon={Percent}
                  label="Cupons gerados"
                  value={relErros?.cupons_gerados ?? 0}
                  sub="como compensação"
                  color="text-purple-400"
                />
              </div>
              {/* Por tipo */}
              {relErros?.por_tipo && relErros.por_tipo.length > 0 && (
                <div className="mb-4">
                  <p className="text-xs text-[var(--text-muted)] mb-2">Por tipo de problema</p>
                  <div className="space-y-2">
                    {relErros.por_tipo.map((t: any) => (
                      <div key={t.tipo} className="flex items-center justify-between text-sm">
                        <span className="text-[var(--text-secondary)] capitalize">
                          {t.tipo.replace("_", " ")}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-[var(--text-primary)]">{t.total}</span>
                          <Badge className="bg-green-500/20 text-green-400 text-[10px]">
                            {t.auto_resolvidos} auto
                          </Badge>
                          <Badge className="bg-orange-500/20 text-orange-400 text-[10px]">
                            {t.escalados} humano
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Por política */}
              {relErros?.por_politica && relErros.por_politica.length > 0 && (
                <div>
                  <p className="text-xs text-[var(--text-muted)] mb-2">Por ação aplicada</p>
                  <div className="flex flex-wrap gap-2">
                    {relErros.por_politica.map((p: any) => (
                      <Badge
                        key={p.acao}
                        className="bg-purple-500/20 text-purple-400 text-xs"
                      >
                        {p.acao?.replace("_", " ")} ({p.vezes_usada}x)
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* ═══ TAB: Repescagem ═══ */}
        {tab === "repescagem" && <RepescagemTab />}
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

// ─── Wizard de Onboarding Self-Service ──────────────────────────

function PhoneOnboardingWizard({
  phoneStatus,
  regStatus,
  refetchPhone,
  refetchConfig,
  addonLiberado,
}: {
  phoneStatus: any;
  regStatus: string;
  refetchPhone: () => void;
  refetchConfig: () => void;
  addonLiberado: boolean;
}) {
  // ── Todos os hooks no TOPO (antes de qualquer early return) ──
  const [codigo, setCodigo] = useState("");
  const [about, setAbout] = useState("");
  const [description, setDescription] = useState("");
  const [nomeAtendente, setNomeAtendente] = useState("Bia");
  const [cooldown, setCooldown] = useState(0);
  const [connectingFb, setConnectingFb] = useState(false);

  const solicitar = useSolicitarCodigo();
  const verificar = useVerificarCodigo();
  const atualizarPerfil = useAtualizarPerfilPhone();
  const uploadFoto = useUploadFotoPerfilPhone();
  const contratarAddon = useContratarAddonBot();
  const [paymentTab, setPaymentTab] = useState<"pix" | "boleto">("pix");
  const [paymentData, setPaymentData] = useState<any>(null);
  const [copiedPix, setCopiedPix] = useState(false);

  const showFbButton = addonLiberado && (regStatus === "none" || regStatus === "pending_signup");
  const signupConfig = useEmbeddedSignupConfig(showFbButton);
  const signupCallback = useEmbeddedSignupCallback();

  // Polling pagamento add-on (só ativo quando pending_payment)
  const addonPayment = useAddonPaymentStatus(regStatus === "pending_payment");

  const fbSdkLoaded = useRef(false);

  // Auto-transicionar quando pagamento confirmado
  useEffect(() => {
    if (addonPayment.data?.status === "confirmed") {
      toast.success("Pagamento confirmado! Agora conecte pelo Facebook.");
      refetchPhone();
    }
  }, [addonPayment.data?.status]);

  // Cooldown timer para reenvio de codigo
  useEffect(() => {
    if (cooldown <= 0) return;
    const t = setTimeout(() => setCooldown((c) => c - 1), 1000);
    return () => clearTimeout(t);
  }, [cooldown]);

  // Carregar Facebook SDK
  useEffect(() => {
    if (fbSdkLoaded.current) return;
    if (!signupConfig.data?.app_id) return;

    const appId = signupConfig.data.app_id;

    // Listener para sessionInfo do Embedded Signup (captura waba_id + phone_number_id)
    (window as any).__fbEmbeddedSignupInfo = null;
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== "https://www.facebook.com" && event.origin !== "https://web.facebook.com") return;
      try {
        const data = typeof event.data === "string" ? JSON.parse(event.data) : event.data;
        if (data.type === "WA_EMBEDDED_SIGNUP") {
          (window as any).__fbEmbeddedSignupInfo = {
            phone_number_id: data.data?.phone_number_id,
            waba_id: data.data?.waba_id,
          };
        }
      } catch { /* ignore non-JSON messages */ }
    };
    window.addEventListener("message", handleMessage);

    // Carregar SDK
    (window as any).fbAsyncInit = function () {
      (window as any).FB.init({
        appId,
        autoLogAppEvents: true,
        xfbml: false,
        version: "v22.0",
      });
    };

    if (!document.getElementById("facebook-jssdk")) {
      const script = document.createElement("script");
      script.id = "facebook-jssdk";
      script.src = "https://connect.facebook.net/en_US/sdk.js";
      script.async = true;
      script.defer = true;
      document.body.appendChild(script);
    }

    fbSdkLoaded.current = true;
    return () => window.removeEventListener("message", handleMessage);
  }, [signupConfig.data?.app_id]);

  const processSignupResponse = useCallback(async (response: any) => {
    if (response.authResponse?.code) {
      const code = response.authResponse.code;
      // Aguardar sessionInfoListener capturar waba_id/phone_number_id
      await new Promise((r) => setTimeout(r, 500));
      const info = (window as any).__fbEmbeddedSignupInfo || {};
      const waba_id = info.waba_id || "";
      const phone_number_id = info.phone_number_id || "";

      if (!waba_id || !phone_number_id) {
        toast.error("Nao foi possivel obter dados do WhatsApp. Tente novamente.");
        setConnectingFb(false);
        return;
      }

      try {
        const result = await signupCallback.mutateAsync({ code, waba_id, phone_number_id });
        if (result.aguardando_pagamento) {
          setPaymentData(result);
          toast.success("Cobranca criada! Efetue o pagamento para continuar.");
        } else {
          toast.success(result.mensagem || "WhatsApp conectado com sucesso!");
        }
        refetchPhone();
        refetchConfig();
      } catch (err: any) {
        toast.error(err?.response?.data?.detail || "Erro ao conectar WhatsApp");
      }
    } else {
      toast.error("Login cancelado ou falhou.");
    }
    setConnectingFb(false);
  }, [signupCallback, refetchPhone, refetchConfig]);

  const handleEmbeddedSignup = useCallback(() => {
    const FB = (window as any).FB;
    if (!FB) {
      toast.error("Facebook SDK nao carregou. Recarregue a pagina.");
      return;
    }
    const configId = signupConfig.data?.config_id;
    if (!configId) {
      toast.error("Configuracao do Embedded Signup nao disponivel.");
      return;
    }

    setConnectingFb(true);
    (window as any).__fbEmbeddedSignupInfo = null;

    FB.login(
      (response: any) => { processSignupResponse(response); },
      {
        config_id: configId,
        response_type: "code",
        override_default_response_type: true,
        extras: {
          feature: "whatsapp_embedded_signup",
          version: 2,
          sessionInfoVersion: 2,
        },
      },
    );
  }, [signupConfig.data?.config_id, processSignupResponse]);

  async function handleVerificar() {
    if (!codigo || codigo.length !== 6) {
      toast.error("Digite o codigo de 6 digitos");
      return;
    }
    try {
      await verificar.mutateAsync(codigo);
      toast.success("Numero verificado!");
      refetchPhone();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Codigo invalido");
    }
  }

  async function handleReenviar(metodo: string) {
    try {
      await solicitar.mutateAsync(metodo);
      setCooldown(60);
      toast.success(`Codigo reenviado via ${metodo}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erro ao reenviar");
    }
  }

  async function handleAtivarComPerfil() {
    try {
      await atualizarPerfil.mutateAsync({
        about,
        description,
        nome_atendente: nomeAtendente,
        ativar: true,
      });
      toast.success("Humanoide ativado com sucesso!");
      refetchPhone();
      refetchConfig();
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || "Erro ao ativar");
    }
  }

  // Estado 0: Precisa contratar add-on primeiro (Essencial/Avançado sem addon)
  if (regStatus === "none" && !addonLiberado) {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10">
            <Bot className="h-8 w-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            WhatsApp Humanoide
          </h2>
          <p className="text-[var(--text-secondary)] max-w-md mx-auto">
            Atendimento inteligente por WhatsApp com IA para seu restaurante.
          </p>
        </div>

        <Card className="p-6 bg-[var(--bg-card)] border-[var(--border-subtle)] space-y-4">
          <div className="text-center space-y-2">
            <p className="text-3xl font-bold text-[var(--text-primary)]">R$ 99,45<span className="text-sm font-normal text-[var(--text-muted)]">/mes</span></p>
            <p className="text-sm text-[var(--text-secondary)]">Add-on — cobranca separada da sua assinatura</p>
          </div>

          <div className="space-y-2 text-sm text-[var(--text-secondary)]">
            <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" /> Atendente IA 24/7 no WhatsApp</div>
            <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" /> Cria pedidos automaticamente</div>
            <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" /> Responde duvidas e envia cardapio</div>
            <div className="flex items-center gap-2"><CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" /> Avaliacao e repescagem de clientes</div>
          </div>

          <Button
            className="w-full bg-green-600 hover:bg-green-700 text-white font-medium py-3"
            onClick={async () => {
              try {
                const result = await contratarAddon.mutateAsync();
                if (result.ja_liberado) {
                  toast.success("Add-on ja esta ativo!");
                  refetchPhone();
                  return;
                }
                setPaymentData(result);
                toast.success("Cobranca criada! Efetue o pagamento.");
                refetchPhone();
              } catch (err: any) {
                toast.error(err?.response?.data?.detail || "Erro ao criar cobranca");
              }
            }}
            disabled={contratarAddon.isPending}
          >
            {contratarAddon.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <ShoppingBag className="h-4 w-4 mr-2" />
            )}
            Contratar WhatsApp Humanoide
          </Button>
        </Card>
      </div>
    );
  }

  // Estado 1: Addon liberado, conectar via Facebook (Premium, addon ativo, ou pós-pagamento)
  if (regStatus === "none" || regStatus === "pending_signup") {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10">
            <Smartphone className="h-8 w-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            Conectar WhatsApp Business
          </h2>
          <p className="text-[var(--text-secondary)] max-w-md mx-auto">
            Conecte a conta WhatsApp Business do seu restaurante para ativar a atendente IA.
          </p>
        </div>

        <Card className="p-6 bg-[var(--bg-card)] border-[var(--border-subtle)] space-y-4">
          <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
            <p className="text-xs text-blue-300">
              <strong>Processo seguro:</strong> A conexao e feita diretamente pelo Facebook.
              Seu numero sera vinculado automaticamente ao Derekh Food.
            </p>
          </div>

          <div className="space-y-2 text-sm text-[var(--text-secondary)]">
            <p className="font-medium text-[var(--text-primary)]">Como funciona:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Clique no botao abaixo para abrir o Facebook</li>
              <li>Faca login e selecione sua conta Business</li>
              <li>Escolha ou crie uma conta WhatsApp Business</li>
              <li>Selecione o numero de telefone do seu restaurante</li>
            </ol>
          </div>

          <Button
            className="w-full bg-[#1877F2] hover:bg-[#166FE5] text-white font-medium py-3"
            onClick={handleEmbeddedSignup}
            disabled={connectingFb || signupCallback.isPending || !signupConfig.data?.config_id}
          >
            {(connectingFb || signupCallback.isPending) ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <svg className="h-5 w-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
              </svg>
            )}
            Conectar com Facebook
          </Button>

          {signupConfig.isError && (
            <p className="text-xs text-red-400 text-center">
              Embedded Signup nao configurado. Contate o suporte.
            </p>
          )}
        </Card>
      </div>
    );
  }

  // Estado 2.5: Aguardando pagamento do add-on
  if (regStatus === "pending_payment") {
    const pData = paymentData || addonPayment.data || {};
    const pixCode = pData.pix_copia_cola || "";
    const qrCode = pData.pix_qr_code || "";
    const boletoUrl = pData.boleto_url || "";
    const invoiceUrl = pData.invoice_url || "";

    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/10">
            <Clock className="h-8 w-8 text-amber-400 animate-pulse" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            Pagamento do Add-on WhatsApp Humanoide
          </h2>
          <p className="text-[var(--text-secondary)]">
            R$ 99,45/mes — cobranca separada da sua assinatura
          </p>
        </div>

        <Card className="p-6 bg-[var(--bg-card)] border-[var(--border-subtle)] space-y-4">
          {/* Tabs Pix / Boleto */}
          <div className="flex gap-2">
            <button
              onClick={() => setPaymentTab("pix")}
              className={cn(
                "flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors",
                paymentTab === "pix"
                  ? "bg-green-600 text-white"
                  : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
              )}
            >
              Pix
            </button>
            <button
              onClick={() => setPaymentTab("boleto")}
              className={cn(
                "flex-1 py-2 px-4 rounded-lg text-sm font-medium transition-colors",
                paymentTab === "boleto"
                  ? "bg-green-600 text-white"
                  : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
              )}
            >
              Boleto
            </button>
          </div>

          {paymentTab === "pix" && (
            <div className="space-y-4">
              {qrCode && (
                <div className="flex justify-center">
                  <img
                    src={`data:image/png;base64,${qrCode}`}
                    alt="QR Code Pix"
                    className="w-56 h-56 rounded-lg border border-[var(--border-subtle)]"
                  />
                </div>
              )}
              {pixCode && (
                <div className="space-y-2">
                  <Label className="text-[var(--text-primary)]">Pix copia e cola</Label>
                  <div className="flex gap-2">
                    <Input
                      readOnly
                      value={pixCode}
                      className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] text-xs font-mono"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(pixCode);
                        setCopiedPix(true);
                        setTimeout(() => setCopiedPix(false), 2000);
                        toast.success("Codigo Pix copiado!");
                      }}
                      className="shrink-0"
                    >
                      {copiedPix ? <CheckCircle2 className="h-4 w-4" /> : "Copiar"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}

          {paymentTab === "boleto" && (
            <div className="space-y-4 text-center">
              {(boletoUrl || invoiceUrl) ? (
                <>
                  <p className="text-sm text-[var(--text-secondary)]">
                    O boleto pode levar ate 2 dias uteis para compensar.
                  </p>
                  <a
                    href={invoiceUrl || boletoUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                  >
                    <FileText className="h-4 w-4" />
                    Abrir Boleto
                  </a>
                </>
              ) : (
                <p className="text-sm text-[var(--text-muted)]">
                  Boleto nao disponivel. Use o Pix para pagamento imediato.
                </p>
              )}
            </div>
          )}

          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center gap-3">
            <Loader2 className="h-4 w-4 animate-spin text-amber-400 shrink-0" />
            <p className="text-xs text-amber-300">
              Aguardando pagamento... Apos a confirmacao, voce podera conectar seu WhatsApp pelo Facebook.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  // Estado 2: Aguardando codigo de verificacao
  if (regStatus === "pending_code") {
    const numMascarado = phoneStatus?.whatsapp_numero
      ? phoneStatus.whatsapp_numero.replace(/(\d{4})(\d+)(\d{4})/, "$1****$3")
      : "***";

    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-amber-500/10">
            <MessageCircle className="h-8 w-8 text-amber-400" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            Verificar Numero
          </h2>
          <p className="text-[var(--text-secondary)]">
            Codigo enviado para <strong>{numMascarado}</strong>
          </p>
        </div>

        <Card className="p-6 bg-[var(--bg-card)] border-[var(--border-subtle)] space-y-4">
          <div className="space-y-2">
            <Label className="text-[var(--text-primary)]">Codigo de verificacao (6 digitos)</Label>
            <Input
              placeholder="000000"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
              className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)] text-center text-2xl tracking-widest font-mono"
              maxLength={6}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter" && codigo.length === 6) handleVerificar();
              }}
            />
          </div>

          <Button
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            onClick={handleVerificar}
            disabled={verificar.isPending || codigo.length !== 6}
          >
            {verificar.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4 mr-2" />
            )}
            Verificar Codigo
          </Button>

          <div className="flex items-center justify-between text-sm">
            <button
              onClick={() => handleReenviar("SMS")}
              disabled={cooldown > 0 || solicitar.isPending}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50"
            >
              {cooldown > 0 ? `Reenviar SMS (${cooldown}s)` : "Reenviar por SMS"}
            </button>
            <button
              onClick={() => handleReenviar("VOICE")}
              disabled={cooldown > 0 || solicitar.isPending}
              className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50"
            >
              Enviar por ligacao
            </button>
          </div>
        </Card>
      </div>
    );
  }

  // Estado 3: Verificado/registrado — configurar perfil
  if (regStatus === "verified" || regStatus === "registered") {
    return (
      <div className="max-w-xl mx-auto py-12 space-y-6">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10">
            <CheckCircle2 className="h-8 w-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            Numero Verificado!
          </h2>
          <p className="text-[var(--text-secondary)]">
            Configure o perfil da atendente e ative o Humanoide.
          </p>
        </div>

        <Card className="p-6 bg-[var(--bg-card)] border-[var(--border-subtle)] space-y-4">
          <div className="space-y-2">
            <Label className="text-[var(--text-primary)]">Nome da atendente IA</Label>
            <Input
              placeholder="Bia"
              value={nomeAtendente}
              onChange={(e) => setNomeAtendente(e.target.value)}
              className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
              maxLength={100}
            />
            <p className="text-xs text-[var(--text-muted)]">
              A atendente se apresentara com este nome aos clientes.
            </p>
          </div>

          <div className="space-y-2">
            <Label className="text-[var(--text-primary)]">Mensagem "Sobre" (max 139 caracteres)</Label>
            <Input
              placeholder="Delivery e retirada — Pedidos 24h"
              value={about}
              onChange={(e) => setAbout(e.target.value.slice(0, 139))}
              className="bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-primary)]"
              maxLength={139}
            />
            <p className="text-xs text-[var(--text-muted)]">{about.length}/139</p>
          </div>

          <div className="space-y-2">
            <Label className="text-[var(--text-primary)]">Descricao do negocio (max 512 caracteres)</Label>
            <textarea
              placeholder="Pizzaria artesanal com delivery rapido. Funcionamos de segunda a domingo."
              value={description}
              onChange={(e) => setDescription(e.target.value.slice(0, 512))}
              className="w-full min-h-[80px] p-2 rounded-md bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] text-sm resize-none"
              maxLength={512}
            />
            <p className="text-xs text-[var(--text-muted)]">{description.length}/512</p>
          </div>

          <div className="space-y-2">
            <Label className="text-[var(--text-primary)]">Foto de perfil (opcional)</Label>
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 px-4 py-2 rounded-lg border border-dashed border-[var(--border-subtle)] cursor-pointer hover:bg-[var(--bg-card-hover)] text-sm text-[var(--text-secondary)]">
                <Upload className="h-4 w-4" />
                Enviar foto
                <input
                  type="file"
                  accept="image/jpeg,image/png"
                  className="hidden"
                  onChange={async (e) => {
                    const file = e.target.files?.[0];
                    if (!file) return;
                    if (file.size > 5 * 1024 * 1024) {
                      toast.error("Imagem muito grande (max 5MB)");
                      return;
                    }
                    try {
                      await uploadFoto.mutateAsync(file);
                      toast.success("Foto enviada!");
                      refetchPhone();
                    } catch {
                      toast.error("Erro ao enviar foto");
                    }
                  }}
                />
              </label>
              {uploadFoto.isPending && <Loader2 className="h-4 w-4 animate-spin text-[var(--text-muted)]" />}
              {phoneStatus?.profile_photo_url && (
                <Badge className="bg-green-500/20 text-green-400 text-xs">Foto enviada</Badge>
              )}
            </div>
          </div>

          <Button
            className="w-full bg-green-600 hover:bg-green-700 text-white"
            onClick={handleAtivarComPerfil}
            disabled={atualizarPerfil.isPending}
          >
            {atualizarPerfil.isPending ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Power className="h-4 w-4 mr-2" />
            )}
            Ativar Humanoide
          </Button>
        </Card>
      </div>
    );
  }

  // Fallback — caso de status desconhecido, mostrar mensagem genérica
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <Loader2 className="h-8 w-8 text-[var(--text-muted)] animate-spin mb-4" />
      <p className="text-[var(--text-secondary)]">Carregando configuracao...</p>
    </div>
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

function RepescagemTab() {
  const { data: inativos, isLoading: loadingInativos } = useBotRelatorioClientesInativos();
  const [paginaHistorico, setPaginaHistorico] = useState(1);
  const { data: historico, isLoading: loadingHistorico } = useBotRepescagemHistorico(paginaHistorico);
  const criarRepescagem = useCriarRepescagemEmMassa();

  const [selecionados, setSelecionados] = useState<Set<number>>(new Set());
  const [descontoPct, setDescontoPct] = useState(10);
  const [validadeDias, setValidadeDias] = useState(7);
  const [canal, setCanal] = useState("whatsapp");

  const clientes = inativos?.clientes || [];
  const resumo = inativos?.resumo || {};
  const repsResumo = inativos?.repescagens || {};

  function toggleCliente(id: number) {
    setSelecionados((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function toggleTodos() {
    if (selecionados.size === clientes.length) {
      setSelecionados(new Set());
    } else {
      setSelecionados(new Set(clientes.map((c: any) => c.id)));
    }
  }

  async function enviarRepescagem() {
    if (selecionados.size === 0) {
      toast.error("Selecione ao menos um cliente");
      return;
    }
    try {
      const result = await criarRepescagem.mutateAsync({
        cliente_ids: Array.from(selecionados),
        desconto_pct: descontoPct,
        validade_dias: validadeDias,
        canal,
      });
      toast.success(`Repescagem enviada para ${result.total} clientes!`);
      setSelecionados(new Set());
    } catch {
      toast.error("Erro ao enviar repescagem");
    }
  }

  return (
    <div className="space-y-6">
      {/* Cards resumo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard icon={Users} label="Total inativos" value={clientes.length} sub="com pedidos" color="text-yellow-400" />
        <MetricCard icon={UserMinus} label="15-30 dias" value={resumo.inativos_15_30 || 0} sub="inativos" color="text-orange-400" />
        <MetricCard icon={UserMinus} label="30-60 dias" value={resumo.inativos_30_60 || 0} sub="inativos" color="text-red-400" />
        <MetricCard icon={Gift} label="Taxa retorno" value={`${repsResumo.taxa_retorno || 0}%`} sub={`${repsResumo.retornaram || 0}/${repsResumo.enviadas_total || 0}`} color="text-green-400" />
      </div>

      {/* Config envio em massa */}
      <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
          <Send className="h-4 w-4" /> Envio em massa
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
          <div>
            <Label className="text-xs text-[var(--text-secondary)]">Desconto (%)</Label>
            <Input type="number" min={5} max={50} value={descontoPct} onChange={(e) => setDescontoPct(Number(e.target.value))}
              className="bg-[var(--bg-surface)] border-[var(--border-subtle)]" />
          </div>
          <div>
            <Label className="text-xs text-[var(--text-secondary)]">Validade (dias)</Label>
            <Input type="number" min={1} max={30} value={validadeDias} onChange={(e) => setValidadeDias(Number(e.target.value))}
              className="bg-[var(--bg-surface)] border-[var(--border-subtle)]" />
          </div>
          <div>
            <Label className="text-xs text-[var(--text-secondary)]">Canal</Label>
            <Select value={canal} onValueChange={setCanal}>
              <SelectTrigger className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="whatsapp">WhatsApp</SelectItem>
                <SelectItem value="email">Email</SelectItem>
                <SelectItem value="ambos">Ambos</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button
          onClick={enviarRepescagem}
          disabled={selecionados.size === 0 || criarRepescagem.isPending}
          className="text-white"
          style={{ backgroundColor: "var(--cor-primaria)" }}
        >
          {criarRepescagem.isPending ? (
            <><RefreshCw className="h-4 w-4 mr-2 animate-spin" /> Enviando...</>
          ) : (
            <><Send className="h-4 w-4 mr-2" /> Enviar para {selecionados.size} selecionado{selecionados.size !== 1 ? "s" : ""}</>
          )}
        </Button>
      </Card>

      {/* Lista clientes inativos */}
      <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-[var(--text-primary)] flex items-center gap-2">
            <Users className="h-4 w-4" /> Clientes inativos ({clientes.length})
          </h3>
          <button onClick={toggleTodos} className="text-xs font-medium flex items-center gap-1" style={{ color: "var(--cor-primaria)" }}>
            {selecionados.size === clientes.length ? <CheckSquare className="h-3.5 w-3.5" /> : <Square className="h-3.5 w-3.5" />}
            {selecionados.size === clientes.length ? "Desmarcar todos" : "Selecionar todos"}
          </button>
        </div>

        {loadingInativos ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-[var(--bg-surface)] animate-pulse rounded-lg" />)}
          </div>
        ) : clientes.length === 0 ? (
          <p className="text-sm text-[var(--text-muted)] text-center py-6">Nenhum cliente inativo encontrado</p>
        ) : (
          <div className="space-y-1 max-h-96 overflow-y-auto">
            {clientes.map((c: any) => (
              <div
                key={c.id}
                onClick={() => toggleCliente(c.id)}
                className={cn(
                  "flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors",
                  selecionados.has(c.id) ? "bg-[var(--cor-primaria)]/10 border border-[var(--cor-primaria)]/30" : "hover:bg-[var(--bg-surface)]"
                )}
              >
                {selecionados.has(c.id) ? (
                  <CheckSquare className="h-4 w-4 shrink-0" style={{ color: "var(--cor-primaria)" }} />
                ) : (
                  <Square className="h-4 w-4 shrink-0 text-[var(--text-muted)]" />
                )}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[var(--text-primary)] truncate">{c.nome}</span>
                    {c.repescagem_enviada && (
                      <Badge variant="outline" className="text-[10px] py-0">
                        {c.retornou ? "Retornou" : "Enviada"}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[var(--text-muted)]">
                    <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{c.telefone}</span>
                    <span>{c.total_pedidos} pedidos</span>
                    <span className="font-semibold text-orange-400">{c.dias_inativo}d inativo</span>
                    {c.ultima_avaliacao != null && (
                      <span className="flex items-center gap-0.5">
                        <Star className="h-3 w-3 text-yellow-400" />{c.ultima_avaliacao}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Histórico de repescagens */}
      <Card className="p-5 bg-[var(--bg-card)] border-[var(--border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-4 flex items-center gap-2">
          <Clock className="h-4 w-4" /> Histórico de repescagens
        </h3>

        {loadingHistorico ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-[var(--bg-surface)] animate-pulse rounded-lg" />)}
          </div>
        ) : !historico?.items?.length ? (
          <p className="text-sm text-[var(--text-muted)] text-center py-6">Nenhuma repescagem enviada ainda</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-[var(--text-muted)] border-b border-[var(--border-subtle)]">
                    <th className="text-left py-2 px-2">Cliente</th>
                    <th className="text-left py-2 px-2">Cupom</th>
                    <th className="text-left py-2 px-2">Canal</th>
                    <th className="text-left py-2 px-2">Data</th>
                    <th className="text-left py-2 px-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {historico.items.map((r: any) => (
                    <tr key={r.id} className="border-b border-[var(--border-subtle)]/50">
                      <td className="py-2 px-2">
                        <div className="text-[var(--text-primary)] font-medium">{r.cliente_nome}</div>
                        <div className="text-xs text-[var(--text-muted)]">{r.cliente_telefone}</div>
                      </td>
                      <td className="py-2 px-2">
                        <code className="text-xs bg-[var(--bg-surface)] px-2 py-0.5 rounded font-mono">
                          {r.cupom_codigo}
                        </code>
                        <span className="text-xs text-[var(--text-muted)] ml-1">{r.cupom_desconto_pct}%</span>
                      </td>
                      <td className="py-2 px-2">
                        <Badge variant="outline" className="text-[10px]">
                          {r.canal === "whatsapp" ? "WA" : r.canal === "email" ? "Email" : "WA+Email"}
                        </Badge>
                      </td>
                      <td className="py-2 px-2 text-xs text-[var(--text-muted)]">
                        {r.criado_em ? new Date(r.criado_em).toLocaleDateString("pt-BR") : "-"}
                      </td>
                      <td className="py-2 px-2">
                        {r.retornou ? (
                          <Badge className="bg-green-500/20 text-green-400 text-[10px]">Retornou</Badge>
                        ) : r.lembrete_enviado ? (
                          <Badge className="bg-yellow-500/20 text-yellow-400 text-[10px]">Lembrete enviado</Badge>
                        ) : (
                          <Badge variant="outline" className="text-[10px]">Aguardando</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Paginação */}
            {historico.paginas > 1 && (
              <div className="flex items-center justify-center gap-2 mt-4">
                <Button size="sm" variant="outline" disabled={paginaHistorico <= 1}
                  onClick={() => setPaginaHistorico((p) => p - 1)}>
                  Anterior
                </Button>
                <span className="text-xs text-[var(--text-muted)]">
                  Página {paginaHistorico} de {historico.paginas}
                </span>
                <Button size="sm" variant="outline" disabled={paginaHistorico >= historico.paginas}
                  onClick={() => setPaginaHistorico((p) => p + 1)}>
                  Próxima
                </Button>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
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
