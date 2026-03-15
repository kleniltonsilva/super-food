import { useState, useEffect, useCallback } from "react";
import { useLocation } from "wouter";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useDashboard,
  useDashboardGrafico,
  usePedidos,
  useCaixaAtual,
  useAtualizarConfig,
  useConfig,
  useEntregasAtivas,
  useDiagnosticoTempo,
  useAjustarTempo,
  useAlertasAtraso,
  useMesas,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ShoppingBag,
  DollarSign,
  TrendingUp,
  Users,
  Bike,
  Vault,
  Store,
  Eye,
  Clock,
  AlertTriangle,
  Truck,
  Timer,
} from "lucide-react";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pendente: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
  em_preparo: { label: "Em Preparo", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  pronto: { label: "Pronto", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  em_entrega: { label: "Em Entrega", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  entregue: { label: "Entregue", color: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" },
  cancelado: { label: "Cancelado", color: "bg-red-500/20 text-red-400 border-red-500/30" },
};

const MODO_LABELS: Record<string, string> = {
  rapido_economico: "Rápido",
  cronologico_inteligente: "Cronológico",
  manual: "Manual",
};

export default function Dashboard() {
  const [, navigate] = useLocation();
  const { data, isLoading } = useDashboard();
  const { data: graficoData } = useDashboardGrafico("7d");
  const { data: config } = useConfig();
  const { data: pedidosData } = usePedidos({ limite: 5 });
  const { data: caixaData } = useCaixaAtual();
  const { data: entregasData } = useEntregasAtivas();
  const { data: diagnostico } = useDiagnosticoTempo();
  const atualizarConfig = useAtualizarConfig();
  const ajustarTempo = useAjustarTempo();

  const pedidosRecentes = pedidosData?.pedidos || [];
  const caixaAberto = caixaData?.status === "aberto";
  const restauranteAberto = config?.status_atual === "aberto";
  const totalAtrasadas = entregasData?.total_atrasadas ?? 0;
  const totalAtivas = entregasData?.total_ativas ?? 0;
  const modoDespacho = config?.modo_prioridade_entrega || "rapido_economico";
  const { data: alertasData } = useAlertasAtraso("hoje");
  const { data: mesasData } = useMesas();
  const totalAlertasHoje = alertasData?.resumo?.total ?? 0;
  const mediaAtrasoHoje = alertasData?.resumo?.media_atraso_min ?? 0;
  const totalMesasAbertas = mesasData?.total_abertas ?? 0;

  // Estado do modal de ajuste de tempo
  const [mostrarAjusteTempo, setMostrarAjusteTempo] = useState(false);
  const [ajusteJaVisto, setAjusteJaVisto] = useState(false);

  // Som de alerta para ajuste de tempo
  const tocarSomAjuste = useCallback(() => {
    try {
      const ctx = new AudioContext();
      [0, 0.3, 0.6].forEach((t) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = 523;
        osc.type = "triangle";
        gain.gain.setValueAtTime(0.3, ctx.currentTime + t);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.25);
        osc.start(ctx.currentTime + t);
        osc.stop(ctx.currentTime + t + 0.25);
      });
    } catch { /* sem audio */ }
  }, []);

  // Som de erro — buzzer grave e agressivo para chamar atenção
  const tocarSomErro = useCallback(() => {
    try {
      const ctx = new AudioContext();
      // 3 bips curtos graves + 1 longo
      const notas = [
        { freq: 200, start: 0, dur: 0.15 },
        { freq: 200, start: 0.2, dur: 0.15 },
        { freq: 200, start: 0.4, dur: 0.15 },
        { freq: 150, start: 0.6, dur: 0.4 },
      ];
      notas.forEach(({ freq, start, dur }) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.value = freq;
        osc.type = "square";
        gain.gain.setValueAtTime(0.4, ctx.currentTime + start);
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur);
        osc.start(ctx.currentTime + start);
        osc.stop(ctx.currentTime + start + dur);
      });
    } catch { /* sem audio */ }
  }, []);

  // Detectar quando precisa ajustar tempo
  useEffect(() => {
    if (diagnostico?.precisa_aumentar && !ajusteJaVisto) {
      setMostrarAjusteTempo(true);
      tocarSomAjuste();
    } else if (diagnostico?.pode_diminuir && !ajusteJaVisto) {
      setMostrarAjusteTempo(true);
      tocarSomAjuste();
    }
  }, [diagnostico?.precisa_aumentar, diagnostico?.pode_diminuir, ajusteJaVisto, tocarSomAjuste]);

  function handleAceitarAjuste() {
    if (!diagnostico) return;
    ajustarTempo.mutate(
      {
        tempo_entrega_estimado: diagnostico.tempo_sugerido_entrega,
        tempo_retirada_estimado: diagnostico.tempo_sugerido_retirada,
      },
      {
        onSuccess: () => {
          toast.success(
            diagnostico.precisa_aumentar
              ? `Tempos ajustados: entrega ${diagnostico.tempo_sugerido_entrega}min, retirada ${diagnostico.tempo_sugerido_retirada}min`
              : `Tempos normalizados: entrega ${diagnostico.tempo_sugerido_entrega}min, retirada ${diagnostico.tempo_sugerido_retirada}min`
          );
          setMostrarAjusteTempo(false);
          setAjusteJaVisto(true);
          // Resetar flag após 5 min para verificar novamente
          setTimeout(() => setAjusteJaVisto(false), 5 * 60 * 1000);
        },
        onError: () => toast.error("Erro ao ajustar tempos"),
      }
    );
  }

  function handleRecusarAjuste() {
    setMostrarAjusteTempo(false);
    setAjusteJaVisto(true);
    setTimeout(() => setAjusteJaVisto(false), 5 * 60 * 1000);
  }

  const [alertaCaixaAberto, setAlertaCaixaAberto] = useState(false);

  function toggleRestaurante() {
    // Se está fechando e o caixa está aberto, bloquear com alerta
    if (restauranteAberto && caixaAberto) {
      tocarSomErro();
      setAlertaCaixaAberto(true);
      return;
    }
    const novoStatus = restauranteAberto ? "fechado" : "aberto";
    atualizarConfig.mutate(
      { status_atual: novoStatus },
      {
        onSuccess: () => toast.success(`Restaurante ${novoStatus === "aberto" ? "aberto" : "fechado"}!`),
        onError: () => toast.error("Erro ao alterar status"),
      }
    );
  }

  function handleAbrirCaixa() {
    navigate("/caixa");
  }

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    const d = new Date(iso);
    return d.toLocaleString("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Banner de alerta de atraso */}
        {totalAtrasadas > 0 && (
          <div className="flex items-center justify-between rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 animate-pulse">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-red-400" />
              <span className="font-medium text-red-400">
                {totalAtrasadas} entrega{totalAtrasadas > 1 ? "s" : ""} atrasada{totalAtrasadas > 1 ? "s" : ""} — verifique!
              </span>
            </div>
            <Button
              size="sm"
              variant="outline"
              className="border-red-500/30 text-red-400 hover:bg-red-500/10"
              onClick={() => navigate("/pedidos")}
            >
              Ver Entregas
            </Button>
          </div>
        )}

        {/* Alerta: tentou fechar restaurante com caixa aberto */}
        {alertaCaixaAberto && (
          <div className="rounded-lg border-2 border-red-500 bg-red-500/15 px-4 py-4 space-y-3 animate-pulse shadow-lg shadow-red-500/20">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-500/20">
                <AlertTriangle className="h-6 w-6 text-red-400" />
              </div>
              <div>
                <p className="font-bold text-red-400 text-lg">Caixa ainda está aberto!</p>
                <p className="text-sm text-red-300/80">
                  Você precisa fechar o caixa antes de encerrar o expediente do restaurante.
                </p>
              </div>
            </div>
            <div className="flex gap-2 pt-1">
              <Button
                size="sm"
                className="bg-red-600 hover:bg-red-700 text-white"
                onClick={() => { setAlertaCaixaAberto(false); navigate("/caixa"); }}
              >
                <Vault className="mr-1 h-4 w-4" /> Ir para o Caixa
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                onClick={() => setAlertaCaixaAberto(false)}
              >
                Entendi
              </Button>
            </div>
          </div>
        )}

        {/* Modal de ajuste automático de tempo */}
        {mostrarAjusteTempo && diagnostico && (diagnostico.precisa_aumentar || diagnostico.pode_diminuir) && (
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-4 space-y-3">
            <div className="flex items-center gap-3">
              <Timer className="h-5 w-5 text-amber-400" />
              <div>
                <p className="font-medium text-amber-400">
                  {diagnostico.precisa_aumentar
                    ? "Tempos de entrega precisam ser ajustados"
                    : "Movimento normalizou — tempos podem voltar ao padrão"}
                </p>
                <p className="text-sm text-[var(--text-muted)]">
                  {diagnostico.motivo}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="rounded-md bg-[var(--bg-surface)] p-3">
                <p className="text-[var(--text-muted)]">Entrega</p>
                <p className="text-[var(--text-primary)]">
                  Atual: <strong>{diagnostico.tempo_entrega_atual}min</strong> →
                  Sugerido: <strong className="text-amber-400">{diagnostico.tempo_sugerido_entrega}min</strong>
                </p>
              </div>
              <div className="rounded-md bg-[var(--bg-surface)] p-3">
                <p className="text-[var(--text-muted)]">Retirada</p>
                <p className="text-[var(--text-primary)]">
                  Atual: <strong>{diagnostico.tempo_retirada_atual}min</strong> →
                  Sugerido: <strong className="text-amber-400">{diagnostico.tempo_sugerido_retirada}min</strong>
                </p>
              </div>
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              Quando o movimento normalizar, o sistema sugerirá voltar aos tempos padrão automaticamente.
            </p>
            <div className="flex gap-2">
              <Button
                size="sm"
                className="bg-amber-600 hover:bg-amber-700"
                onClick={handleAceitarAjuste}
                disabled={ajustarTempo.isPending}
              >
                Sim, ajustar tempos
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="border-[var(--border-subtle)] text-[var(--text-secondary)]"
                onClick={handleRecusarAjuste}
              >
                Não, manter atual
              </Button>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-2xl font-bold text-[var(--text-primary)]">Dashboard</h2>
            <Badge className="bg-[var(--cor-primaria)]/10 text-[var(--cor-primaria)] border-[var(--cor-primaria)]/30 border text-xs">
              {MODO_LABELS[modoDespacho] || modoDespacho}
            </Badge>
          </div>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant={restauranteAberto ? "outline" : "default"}
              className={restauranteAberto
                ? "border-red-500/30 text-red-400 hover:bg-red-500/10"
                : "bg-green-600 hover:bg-green-700"
              }
              onClick={toggleRestaurante}
              disabled={atualizarConfig.isPending}
            >
              <Store className="mr-1 h-4 w-4" />
              {restauranteAberto ? "Fechar Restaurante" : "Abrir Restaurante"}
            </Button>
            {!caixaAberto && (
              <Button
                size="sm"
                className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                onClick={handleAbrirCaixa}
                disabled={false}
              >
                <Vault className="mr-1 h-4 w-4" /> Abrir Caixa
              </Button>
            )}
          </div>
        </div>

        {/* Cards de métricas */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          <MetricCard
            title="Pedidos Hoje"
            value={data?.pedidos_hoje}
            icon={ShoppingBag}
            loading={isLoading}
          />
          <MetricCard
            title="Pendentes"
            value={data?.pedidos_pendentes ?? 0}
            icon={Clock}
            loading={isLoading}
            valueColor={(data?.pedidos_pendentes ?? 0) > 0 ? "text-yellow-400" : undefined}
          />
          <MetricCard
            title="Faturamento Hoje"
            value={data?.faturamento_hoje != null ? `R$ ${Number(data.faturamento_hoje).toFixed(2)}` : undefined}
            icon={DollarSign}
            loading={isLoading}
          />
          <MetricCard
            title="Entregas Ativas"
            value={totalAtivas}
            icon={Truck}
            loading={isLoading}
            valueColor={totalAtrasadas > 0 ? "text-red-400" : totalAtivas > 0 ? "text-purple-400" : undefined}
            extra={totalAtrasadas > 0 ? `${totalAtrasadas} atrasada${totalAtrasadas > 1 ? "s" : ""}` : undefined}
          />
          <MetricCard
            title="Ticket Médio"
            value={data?.ticket_medio != null ? `R$ ${Number(data.ticket_medio).toFixed(2)}` : undefined}
            icon={TrendingUp}
            loading={isLoading}
          />
          <MetricCard
            title="Motoboys Online"
            value={data?.motoboys_online ?? 0}
            icon={Bike}
            loading={isLoading}
          />
          <MetricCard
            title="Caixa"
            value={caixaAberto ? "Aberto" : "Fechado"}
            icon={Vault}
            loading={isLoading}
            valueColor={caixaAberto ? "text-green-400" : "text-red-400"}
          />
        </div>

        {/* Cards extras: Atrasos + Mesas */}
        {(totalAlertasHoje > 0 || totalMesasAbertas > 0) && (
          <div className="grid gap-4 sm:grid-cols-2">
            {totalAlertasHoje > 0 && (
              <Card
                className="border-red-500/20 bg-red-500/5 cursor-pointer hover:bg-red-500/10 transition-colors"
                onClick={() => navigate("/historico-atrasos")}
              >
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-red-500/20 p-2.5">
                      <AlertTriangle className="h-5 w-5 text-red-400" />
                    </div>
                    <div>
                      <p className="text-sm text-[var(--text-muted)]">Atrasos Hoje</p>
                      <p className="text-xl font-bold text-red-400">{totalAlertasHoje}</p>
                      {mediaAtrasoHoje > 0 && (
                        <p className="text-xs text-[var(--text-muted)]">Média: {mediaAtrasoHoje}min</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            {totalMesasAbertas > 0 && (
              <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-blue-500/20 p-2.5">
                      <Store className="h-5 w-5 text-blue-400" />
                    </div>
                    <div>
                      <p className="text-sm text-[var(--text-muted)]">Mesas Abertas</p>
                      <p className="text-xl font-bold text-blue-400">{totalMesasAbertas}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {/* Gráfico e Pedidos Recentes */}
        <div className="grid gap-4 lg:grid-cols-2">
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader>
              <CardTitle className="text-[var(--text-primary)]">
                Vendas dos Últimos 7 Dias
              </CardTitle>
            </CardHeader>
            <CardContent>
              {graficoData && Array.isArray(graficoData) && graficoData.length > 0 ? (
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={graficoData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
                    <XAxis
                      dataKey="data"
                      tick={{ fill: "var(--text-muted)", fontSize: 12 }}
                      tickFormatter={(v: string) => {
                        const d = new Date(v + "T00:00:00");
                        return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
                      }}
                    />
                    <YAxis tick={{ fill: "var(--text-muted)", fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "var(--bg-surface)",
                        border: "1px solid var(--border-subtle)",
                        borderRadius: 8,
                        color: "var(--text-primary)",
                      }}
                      formatter={(value: number) => [`R$ ${value.toFixed(2)}`, "Faturamento"]}
                      labelFormatter={(label: string) => {
                        const d = new Date(label + "T00:00:00");
                        return d.toLocaleDateString("pt-BR", { weekday: "short", day: "2-digit", month: "2-digit" });
                      }}
                    />
                    <Bar dataKey="faturamento" fill="var(--cor-primaria)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-48 items-center justify-center text-[var(--text-muted)]">
                  Sem dados de vendas no período
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-[var(--text-primary)]">Pedidos Recentes</CardTitle>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-[var(--cor-primaria)]"
                  onClick={() => navigate("/pedidos")}
                >
                  Ver todos
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {pedidosRecentes.length === 0 ? (
                <div className="flex h-48 items-center justify-center text-[var(--text-muted)]">
                  Nenhum pedido recente
                </div>
              ) : (
                <div className="space-y-3">
                  {pedidosRecentes.map((p: Record<string, unknown>) => {
                    const st = STATUS_MAP[p.status as string] || { label: p.status, color: "bg-gray-500/20 text-gray-400" };
                    return (
                      <div
                        key={p.id as number}
                        className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-3 cursor-pointer hover:bg-[var(--bg-card-hover)] transition-colors"
                        onClick={() => navigate(`/pedidos/${p.id}`)}
                      >
                        <div className="flex items-center gap-3">
                          <span className="font-mono text-sm text-[var(--text-muted)]">
                            #{String(p.comanda || p.id)}
                          </span>
                          <div>
                            <p className="text-sm font-medium text-[var(--text-primary)]">
                              {(p.cliente_nome as string) || "Sem nome"}
                            </p>
                            <p className="text-xs text-[var(--text-muted)]">{formatDate(p.data_criacao as string)}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-[var(--text-primary)]">
                            R$ {Number(p.valor_total).toFixed(2)}
                          </span>
                          <Badge className={`${st.color} border text-xs`}>{st.label}</Badge>
                          <Eye className="h-4 w-4 text-[var(--text-muted)]" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AdminLayout>
  );
}

function MetricCard({
  title,
  value,
  icon: Icon,
  loading,
  valueColor,
  extra,
}: {
  title: string;
  value?: string | number;
  icon: React.ComponentType<{ className?: string }>;
  loading: boolean;
  valueColor?: string;
  extra?: string;
}) {
  return (
    <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
      <CardContent className="flex items-center gap-4 p-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-[var(--cor-primaria)]/10">
          <Icon className="h-6 w-6 text-[var(--cor-primaria)]" />
        </div>
        <div>
          <p className="text-sm text-[var(--text-muted)]">{title}</p>
          {loading ? (
            <Skeleton className="mt-1 h-7 w-20" />
          ) : (
            <>
              <p className={`text-2xl font-bold ${valueColor || "text-[var(--text-primary)]"}`}>
                {value ?? "—"}
              </p>
              {extra && (
                <p className="text-xs text-red-400">{extra}</p>
              )}
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
