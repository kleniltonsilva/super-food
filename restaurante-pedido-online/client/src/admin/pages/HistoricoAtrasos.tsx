import { useState } from "react";
import { Clock, AlertTriangle, TrendingUp, ArrowUpDown, CheckCircle, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAlertasAtraso, useSugestoesTempo } from "@/admin/hooks/useAdminQueries";

const tipoLabels: Record<string, string> = {
  entrega: "Entrega",
  retirada: "Retirada",
  mesa: "Mesa",
};

export default function HistoricoAtrasos() {
  const [periodo, setPeriodo] = useState("hoje");
  const [filtroTipo, setFiltroTipo] = useState("todos");

  const { data: alertasData, isLoading: loadingAlertas } = useAlertasAtraso(periodo, filtroTipo);
  const { data: sugestoesData, isLoading: loadingSugestoes } = useSugestoesTempo();

  const alertas = alertasData?.alertas || [];
  const resumo = alertasData?.resumo || { total: 0, media_atraso_min: 0, maior_atraso_min: 0 };
  const sugestoes = sugestoesData?.sugestoes || [];
  const estatisticas = sugestoesData?.estatisticas || { total: 0, aceitas: 0, rejeitadas: 0 };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Histórico de Atrasos</h1>
          <p className="text-sm text-muted-foreground">
            Acompanhe atrasos e decisões sobre tempos configurados
          </p>
        </div>
      </div>

      <Tabs defaultValue="alertas">
        <TabsList>
          <TabsTrigger value="alertas">
            <AlertTriangle className="mr-1.5 h-4 w-4" />
            Alertas ({resumo.total})
          </TabsTrigger>
          <TabsTrigger value="decisoes">
            <ArrowUpDown className="mr-1.5 h-4 w-4" />
            Decisões ({estatisticas.total})
          </TabsTrigger>
        </TabsList>

        {/* ── Aba Alertas ── */}
        <TabsContent value="alertas" className="space-y-4">
          {/* Filtros */}
          <div className="flex gap-2 flex-wrap">
            <Select value={periodo} onValueChange={setPeriodo}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="hoje">Hoje</SelectItem>
                <SelectItem value="7d">7 dias</SelectItem>
                <SelectItem value="30d">30 dias</SelectItem>
              </SelectContent>
            </Select>
            <Select value={filtroTipo} onValueChange={setFiltroTipo}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="todos">Todos</SelectItem>
                <SelectItem value="entrega">Entrega</SelectItem>
                <SelectItem value="retirada">Retirada</SelectItem>
                <SelectItem value="mesa">Mesa</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Cards Resumo */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-red-100 p-2.5">
                    <AlertTriangle className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Total Atrasos</p>
                    <p className="text-2xl font-bold">{resumo.total}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-yellow-100 p-2.5">
                    <Clock className="h-5 w-5 text-yellow-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Média Atraso</p>
                    <p className="text-2xl font-bold">{resumo.media_atraso_min}min</p>
                  </div>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-center gap-3">
                  <div className="rounded-full bg-orange-100 p-2.5">
                    <TrendingUp className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Maior Atraso</p>
                    <p className="text-2xl font-bold">{resumo.maior_atraso_min}min</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Tabela */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Alertas de Atraso</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingAlertas ? (
                <div className="text-center py-8 text-muted-foreground">Carregando...</div>
              ) : alertas.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Nenhum atraso neste período
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4">Tipo</th>
                        <th className="pb-2 pr-4">Configurado</th>
                        <th className="pb-2 pr-4">Real</th>
                        <th className="pb-2 pr-4">Atraso</th>
                        <th className="pb-2">Data</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alertas.map((a: Record<string, unknown>) => (
                        <tr key={a.id as number} className="border-b last:border-0">
                          <td className="py-2 pr-4">
                            <Badge variant="outline">
                              {tipoLabels[(a.tipo_pedido as string) || ""] || String(a.tipo_pedido)}
                            </Badge>
                          </td>
                          <td className="py-2 pr-4 font-mono">{a.tempo_estimado_min as number}min</td>
                          <td className="py-2 pr-4 font-mono font-medium text-red-600">
                            {a.tempo_real_min as number}min
                          </td>
                          <td className="py-2 pr-4">
                            <Badge variant="destructive">+{a.atraso_min as number}min</Badge>
                          </td>
                          <td className="py-2 text-muted-foreground text-xs">
                            {a.criado_em
                              ? new Date(a.criado_em as string).toLocaleString("pt-BR", {
                                  day: "2-digit",
                                  month: "2-digit",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })
                              : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Aba Decisões do Operador ── */}
        <TabsContent value="decisoes" className="space-y-4">
          {/* Insight */}
          {estatisticas.rejeitadas > 0 && (
            <Card className="border-yellow-200 bg-yellow-50">
              <CardContent className="pt-6">
                <p className="text-sm text-yellow-800">
                  <strong>Atenção:</strong> {estatisticas.rejeitadas} sugestão(ões) rejeitada(s)
                  {estatisticas.aceitas > 0 && ` de ${estatisticas.total} total`}.
                  Quando sugestões são ignoradas, o tempo configurado pode não refletir a realidade.
                </p>
              </CardContent>
            </Card>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card>
              <CardContent className="pt-6 text-center">
                <p className="text-2xl font-bold">{estatisticas.total}</p>
                <p className="text-sm text-muted-foreground">Total</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <p className="text-2xl font-bold text-green-600">{estatisticas.aceitas}</p>
                <p className="text-sm text-muted-foreground">Aceitas</p>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6 text-center">
                <p className="text-2xl font-bold text-red-600">{estatisticas.rejeitadas}</p>
                <p className="text-sm text-muted-foreground">Rejeitadas</p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Histórico de Sugestões</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingSugestoes ? (
                <div className="text-center py-8 text-muted-foreground">Carregando...</div>
              ) : sugestoes.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  Nenhuma sugestão registrada
                </div>
              ) : (
                <div className="space-y-2">
                  {sugestoes.map((s: Record<string, unknown>) => (
                    <div
                      key={s.id as number}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        {s.aceita ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500" />
                        )}
                        <div>
                          <p className="text-sm font-medium">
                            {tipoLabels[(s.tipo as string) || ""] || String(s.tipo)}: {s.valor_antes as number}min → {s.valor_sugerido as number}min
                          </p>
                          <p className="text-xs text-muted-foreground">{s.motivo as string}</p>
                        </div>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {s.criado_em
                          ? new Date(s.criado_em as string).toLocaleString("pt-BR", {
                              day: "2-digit",
                              month: "2-digit",
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          : "—"}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
