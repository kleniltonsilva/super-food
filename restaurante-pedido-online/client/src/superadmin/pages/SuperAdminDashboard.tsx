import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useMetricas, usePlanos } from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import {
  Store,
  TrendingUp,
  DollarSign,
  Bike,
  ShoppingBag,
  AlertTriangle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";

const CORES_PLANOS: Record<string, string> = {
  "Básico": "#3b82f6",
  "Essencial": "#10b981",
  "Avançado": "#f59e0b",
  "Premium": "#8b5cf6",
};

function formatCurrency(value: number | undefined | null) {
  if (value == null || isNaN(value)) return "R$ 0,00";
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: React.ElementType;
  color: string;
  subtitle?: string;
}

function MetricCard({ label, value, icon: Icon, color, subtitle }: MetricCardProps) {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="mt-1 text-2xl font-bold text-white">{value ?? 0}</p>
          {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
        </div>
        <div className={`flex h-12 w-12 items-center justify-center rounded-lg ${color}`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
      </div>
    </div>
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function renderPieLabel(entry: any) {
  const nome = entry?.nome || entry?.name || "";
  const total = entry?.total ?? entry?.value ?? 0;
  return `${nome}: ${total}`;
}

export default function SuperAdminDashboard() {
  const { data: metricas, isLoading: loadingMetricas } = useMetricas();
  const { data: planos, isLoading: loadingPlanos } = usePlanos();

  if (loadingMetricas) {
    return (
      <SuperAdminLayout>
        <div className="flex h-64 items-center justify-center">
          <Spinner className="h-8 w-8 text-amber-500" />
        </div>
      </SuperAdminLayout>
    );
  }

  const m = metricas ?? {};
  const totalRest = m.total_restaurantes ?? 0;
  const ativos = m.restaurantes_ativos ?? 0;
  const suspensos = m.restaurantes_suspensos ?? 0;
  const cancelados = m.restaurantes_cancelados ?? 0;
  const receitaMensal = m.receita_mensal ?? 0;
  const receitaAnual = m.receita_anual_projetada ?? 0;
  const ticketMedio = m.ticket_medio ?? 0;
  const pedidosHoje = m.total_pedidos_hoje ?? 0;
  const pedidosMes = m.total_pedidos_mes ?? 0;
  const totalMotoboys = m.total_motoboys ?? 0;
  const motoboysOnline = m.motoboys_online ?? 0;

  // Dados para gráfico de distribuição de planos
  const distPlanos = (m.distribuicao_planos || {}) as Record<string, number>;
  const dadosPlanos = Object.entries(distPlanos).map(([nome, total]) => ({
    nome,
    total: total ?? 0,
    cor: CORES_PLANOS[nome] || "#6b7280",
  }));

  // Dados para gráfico de barras dos planos com valores
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const dadosBarras = (planos || []).map((p: any) => ({
    nome: p.nome ?? "",
    assinantes: p.total_assinantes ?? 0,
    receita: (p.total_assinantes ?? 0) * (p.valor ?? 0),
  }));

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-white">Dashboard Geral</h2>

        {/* Cards métricas */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <MetricCard
            label="Total Restaurantes"
            value={totalRest}
            icon={Store}
            color="bg-blue-600"
            subtitle={`${ativos} ativos`}
          />
          <MetricCard
            label="Receita Mensal"
            value={formatCurrency(receitaMensal)}
            icon={DollarSign}
            color="bg-green-600"
            subtitle={`Anual: ${formatCurrency(receitaAnual)}`}
          />
          <MetricCard
            label="Ticket Médio"
            value={formatCurrency(ticketMedio)}
            icon={TrendingUp}
            color="bg-amber-600"
          />
          <MetricCard
            label="Pedidos Hoje"
            value={pedidosHoje}
            icon={ShoppingBag}
            color="bg-purple-600"
            subtitle={`${pedidosMes} no mês`}
          />
          <MetricCard
            label="Motoboys Ativos"
            value={totalMotoboys}
            icon={Bike}
            color="bg-cyan-600"
            subtitle={`${motoboysOnline} online`}
          />
          <MetricCard
            label="Suspensos"
            value={suspensos}
            icon={AlertTriangle}
            color="bg-orange-600"
            subtitle={`${cancelados} cancelados`}
          />
        </div>

        {/* Gráficos */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Distribuição de Planos (pizza) */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            <h3 className="mb-4 text-lg font-semibold text-white">Distribuição por Plano</h3>
            {dadosPlanos.length > 0 ? (
              <div className="flex flex-col items-center">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={dadosPlanos}
                      cx="50%"
                      cy="50%"
                      outerRadius={90}
                      dataKey="total"
                      nameKey="nome"
                      label={renderPieLabel}
                    >
                      {dadosPlanos.map((entry, index) => (
                        <Cell key={index} fill={entry.cor} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                      labelStyle={{ color: "#fff" }}
                      itemStyle={{ color: "#d1d5db" }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="mt-2 flex flex-wrap justify-center gap-3">
                  {dadosPlanos.map((p) => (
                    <div key={p.nome} className="flex items-center gap-1.5">
                      <span className="h-3 w-3 rounded-full" style={{ backgroundColor: p.cor }} />
                      <span className="text-xs text-gray-400">{p.nome} ({p.total})</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-center text-gray-500">Nenhum dado disponível</p>
            )}
          </div>

          {/* Receita por Plano (barras) */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            <h3 className="mb-4 text-lg font-semibold text-white">Receita por Plano</h3>
            {!loadingPlanos && dadosBarras.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dadosBarras}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="nome" stroke="#9ca3af" fontSize={12} />
                  <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(v: number) => `R$${v}`} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#1f2937", border: "1px solid #374151", borderRadius: "8px" }}
                    labelStyle={{ color: "#fff" }}
                    formatter={(value: number) => [formatCurrency(value), "Receita"]}
                  />
                  <Bar dataKey="receita" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-center text-gray-500">Nenhum dado disponível</p>
            )}
          </div>
        </div>
      </div>
    </SuperAdminLayout>
  );
}
