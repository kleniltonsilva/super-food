import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useBotTokenUsage } from "@/superadmin/hooks/useSuperAdminQueries";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Bot,
  Cpu,
  DollarSign,
  Mic,
  Users,
  TrendingUp,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

type Periodo = "daily" | "weekly" | "monthly";

const PERIODOS: { value: Periodo; label: string }[] = [
  { value: "daily", label: "Hoje" },
  { value: "weekly", label: "7 dias" },
  { value: "monthly", label: "30 dias" },
];

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export default function BotTokenDashboard() {
  const [periodo, setPeriodo] = useState<Periodo>("daily");
  const { data, isLoading } = useBotTokenUsage({ periodo });

  const totais = data?.totais;
  const chart = data?.chart_diario || [];
  const porRest = data?.por_restaurante || [];
  const audio = data?.audio_stt;

  return (
    <SuperAdminLayout>
      <h1 className="text-2xl font-bold text-[var(--sa-text-primary)] mb-6">
        Bot IA — Uso de Tokens
      </h1>

      {/* Seletor período */}
      <div className="flex gap-2 mb-6">
        {PERIODOS.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriodo(p.value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              periodo === p.value
                ? "bg-[var(--sa-accent)] text-white"
                : "bg-[var(--sa-bg-surface)] text-[var(--sa-text-muted)] hover:bg-[var(--sa-bg-hover)]"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-[var(--sa-text-muted)]">Carregando...</p>
      ) : (
        <>
          {/* Cards resumo */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
            <MetricCard
              icon={Cpu}
              label="Total Tokens"
              value={formatTokens((totais?.tokens_input || 0) + (totais?.tokens_output || 0))}
              sub={`In: ${formatTokens(totais?.tokens_input || 0)} | Out: ${formatTokens(totais?.tokens_output || 0)}`}
              color="text-blue-400"
            />
            <MetricCard
              icon={DollarSign}
              label="Custo USD"
              value={`$${(totais?.custo_usd || 0).toFixed(2)}`}
              sub="Grok-3-fast"
              color="text-green-400"
            />
            <MetricCard
              icon={DollarSign}
              label="Custo BRL"
              value={`R$ ${(totais?.custo_brl || 0).toFixed(2)}`}
              sub="~5.7 USD/BRL"
              color="text-emerald-400"
            />
            <MetricCard
              icon={Mic}
              label="Áudios STT"
              value={audio?.total_transcricoes ?? 0}
              sub="Groq free tier"
              color="text-purple-400"
            />
            <MetricCard
              icon={Users}
              label="Restaurantes"
              value={totais?.restaurantes_ativos ?? 0}
              sub={`${totais?.total_mensagens ?? 0} msgs`}
              color="text-amber-400"
            />
          </div>

          {/* Chart diário */}
          {chart.length > 1 && (
            <Card className="p-4 bg-[var(--sa-bg-surface)] border-[var(--sa-border)] mb-6">
              <h3 className="text-sm font-medium text-[var(--sa-text-primary)] mb-4">
                Uso diário de tokens
              </h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--sa-border)" />
                    <XAxis
                      dataKey="dia"
                      tick={{ fill: "var(--sa-text-muted)", fontSize: 12 }}
                      tickFormatter={(v) => {
                        const d = new Date(v + "T00:00:00");
                        return `${d.getDate()}/${d.getMonth() + 1}`;
                      }}
                    />
                    <YAxis
                      tick={{ fill: "var(--sa-text-muted)", fontSize: 12 }}
                      tickFormatter={(v) => formatTokens(v)}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "var(--sa-bg-surface)",
                        border: "1px solid var(--sa-border)",
                        borderRadius: "8px",
                        color: "var(--sa-text-primary)",
                      }}
                      formatter={(value: number, name: string) => [
                        formatTokens(value),
                        name === "tokens_input" ? "Input" : name === "tokens_output" ? "Output" : name,
                      ]}
                      labelFormatter={(label) => {
                        const d = new Date(label + "T00:00:00");
                        return d.toLocaleDateString("pt-BR");
                      }}
                    />
                    <Legend
                      formatter={(value) =>
                        value === "tokens_input" ? "Input" : value === "tokens_output" ? "Output" : value
                      }
                    />
                    <Line
                      type="monotone"
                      dataKey="tokens_input"
                      stroke="#60a5fa"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="tokens_output"
                      stroke="#f59e0b"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}

          {/* Tabela por restaurante */}
          <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
            <div className="p-4 border-b border-[var(--sa-border)]">
              <h3 className="text-sm font-medium text-[var(--sa-text-primary)]">
                Uso por restaurante
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--sa-border)]">
                    <th className="text-left p-3 text-[var(--sa-text-muted)] font-medium">Restaurante</th>
                    <th className="text-left p-3 text-[var(--sa-text-muted)] font-medium">Plano</th>
                    <th className="text-right p-3 text-[var(--sa-text-muted)] font-medium">Input</th>
                    <th className="text-right p-3 text-[var(--sa-text-muted)] font-medium">Output</th>
                    <th className="text-right p-3 text-[var(--sa-text-muted)] font-medium">Msgs</th>
                    <th className="text-right p-3 text-[var(--sa-text-muted)] font-medium">USD</th>
                    <th className="text-right p-3 text-[var(--sa-text-muted)] font-medium">BRL</th>
                  </tr>
                </thead>
                <tbody>
                  {porRest.length === 0 && (
                    <tr>
                      <td colSpan={7} className="p-6 text-center text-[var(--sa-text-muted)]">
                        Nenhum uso no período
                      </td>
                    </tr>
                  )}
                  {porRest.map((r: any) => (
                    <tr key={r.restaurante_id} className="border-b border-[var(--sa-border)] hover:bg-[var(--sa-bg-hover)]">
                      <td className="p-3 text-[var(--sa-text-primary)] font-medium">{r.nome}</td>
                      <td className="p-3">
                        <Badge className="bg-blue-500/20 text-blue-400 text-xs">{r.plano || "—"}</Badge>
                      </td>
                      <td className="p-3 text-right text-[var(--sa-text-secondary)] tabular-nums">{formatTokens(r.tokens_input)}</td>
                      <td className="p-3 text-right text-[var(--sa-text-secondary)] tabular-nums">{formatTokens(r.tokens_output)}</td>
                      <td className="p-3 text-right text-[var(--sa-text-secondary)] tabular-nums">{r.mensagens}</td>
                      <td className="p-3 text-right text-green-400 tabular-nums">${r.custo_usd.toFixed(2)}</td>
                      <td className="p-3 text-right text-emerald-400 tabular-nums">R$ {r.custo_brl.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </>
      )}
    </SuperAdminLayout>
  );
}

function MetricCard({
  icon: Icon,
  label,
  value,
  sub,
  color,
}: {
  icon: any;
  label: string;
  value: string | number;
  sub: string;
  color: string;
}) {
  return (
    <Card className="p-4 bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`h-4 w-4 ${color}`} />
        <span className="text-xs text-[var(--sa-text-muted)]">{label}</span>
      </div>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-[var(--sa-text-dimmed)] mt-1">{sub}</p>
    </Card>
  );
}
