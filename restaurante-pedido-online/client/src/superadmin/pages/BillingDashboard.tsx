import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useBillingDashboard,
  useBillingAuditLog,
  useRestaurantes,
  useEstenderTrial,
  useReativarBilling,
  useMigrarAsaas,
  useCancelarAssinatura,
} from "@/superadmin/hooks/useSuperAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  DollarSign, TrendingUp, Users, AlertTriangle, Clock,
  Settings, Play, RotateCcw, Upload, XCircle,
} from "lucide-react";
import { useState } from "react";
import { useLocation } from "wouter";
import { toast } from "sonner";

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  manual: { label: "Manual", color: "bg-gray-500/20 text-gray-400" },
  trial: { label: "Trial", color: "bg-blue-500/20 text-blue-400" },
  active: { label: "Ativo", color: "bg-green-500/20 text-green-400" },
  overdue: { label: "Vencido", color: "bg-yellow-500/20 text-yellow-400" },
  suspended_billing: { label: "Suspenso", color: "bg-red-500/20 text-red-400" },
  canceled_billing: { label: "Cancelado", color: "bg-red-700/20 text-red-500" },
};

const AUDIT_LABELS: Record<string, string> = {
  trial_started: "Trial iniciado",
  trial_extended: "Trial estendido",
  plan_selected: "Plano selecionado",
  plan_changed_admin: "Plano alterado (admin)",
  payment_overdue: "Pagamento vencido",
  suspended_billing: "Suspenso",
  reactivated_payment: "Reativado (pagamento)",
  reactivated_admin: "Reativado (admin)",
  canceled_billing: "Cancelado (automático)",
  canceled_admin: "Cancelado (admin)",
  migrated_to_asaas: "Migrado para Asaas",
};

export default function BillingDashboard() {
  const [, navigate] = useLocation();
  const { data: dashboard, isLoading } = useBillingDashboard();
  const { data: restaurantesData } = useRestaurantes();
  const { data: auditData } = useBillingAuditLog({ limit: 30 });

  const estenderTrial = useEstenderTrial();
  const reativarBilling = useReativarBilling();
  const migrarAsaas = useMigrarAsaas();
  const cancelarAssinatura = useCancelarAssinatura();

  const [tabAtiva, setTabAtiva] = useState("todos");
  const [trialDialog, setTrialDialog] = useState<{ id: number; nome: string } | null>(null);
  const [trialDias, setTrialDias] = useState(15);

  function handleEstenderTrial() {
    if (!trialDialog) return;
    estenderTrial.mutate(
      { id: trialDialog.id, dias: trialDias },
      {
        onSuccess: () => { toast.success("Trial estendido!"); setTrialDialog(null); },
        onError: (e: any) => toast.error(e?.response?.data?.detail || "Erro"),
      }
    );
  }

  function handleReativar(id: number) {
    reativarBilling.mutate(id, {
      onSuccess: () => toast.success("Restaurante reativado!"),
      onError: (e: any) => toast.error(e?.response?.data?.detail || "Erro"),
    });
  }

  function handleMigrar(id: number) {
    migrarAsaas.mutate(id, {
      onSuccess: () => toast.success("Migrado para Asaas!"),
      onError: (e: any) => toast.error(e?.response?.data?.detail || "Erro"),
    });
  }

  function handleCancelar(id: number) {
    if (!confirm("Tem certeza que deseja cancelar a assinatura?")) return;
    cancelarAssinatura.mutate(id, {
      onSuccess: () => toast.success("Assinatura cancelada"),
      onError: (e: any) => toast.error(e?.response?.data?.detail || "Erro"),
    });
  }

  const restaurantes = restaurantesData || [];
  const filtrados = tabAtiva === "todos"
    ? restaurantes
    : restaurantes.filter((r: any) => r.billing_status === tabAtiva);

  if (isLoading) {
    return (
      <SuperAdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-amber-500 border-t-transparent rounded-full" />
        </div>
      </SuperAdminLayout>
    );
  }

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Billing Dashboard</h1>
          <Button variant="outline" onClick={() => navigate("/billing/config")}>
            <Settings className="h-4 w-4 mr-2" /> Configuração
          </Button>
        </div>

        {/* Cards KPI */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-gray-400">MRR</CardTitle>
              <DollarSign className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">R$ {dashboard?.mrr?.toFixed(2) || "0,00"}</div>
              <p className="text-xs text-gray-500">Receita mensal recorrente</p>
            </CardContent>
          </Card>

          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-gray-400">Receita Projetada/Ano</CardTitle>
              <TrendingUp className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">R$ {dashboard?.receita_anual_projetada?.toFixed(2) || "0,00"}</div>
            </CardContent>
          </Card>

          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-gray-400">Restaurantes Ativos</CardTitle>
              <Users className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-white">{dashboard?.total_ativos || 0}</div>
              <p className="text-xs text-gray-500">{dashboard?.total_trials || 0} em trial</p>
            </CardContent>
          </Card>

          <Card className="bg-gray-900 border-gray-800">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-gray-400">Inadimplentes</CardTitle>
              <AlertTriangle className="h-4 w-4 text-gray-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-400">
                {(dashboard?.total_overdue || 0) + (dashboard?.total_suspensos || 0)}
              </div>
              <p className="text-xs text-gray-500">{dashboard?.total_overdue || 0} vencidos, {dashboard?.total_suspensos || 0} suspensos</p>
            </CardContent>
          </Card>
        </div>

        {/* Restaurantes por Status */}
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Restaurantes por Status</CardTitle>
          </CardHeader>
          <CardContent>
            <Tabs value={tabAtiva} onValueChange={setTabAtiva}>
              <TabsList className="bg-gray-800">
                <TabsTrigger value="todos">Todos ({restaurantes.length})</TabsTrigger>
                <TabsTrigger value="trial">Trial ({dashboard?.total_trials || 0})</TabsTrigger>
                <TabsTrigger value="active">Ativos ({dashboard?.total_ativos || 0})</TabsTrigger>
                <TabsTrigger value="overdue">Vencidos ({dashboard?.total_overdue || 0})</TabsTrigger>
                <TabsTrigger value="suspended_billing">Suspensos ({dashboard?.total_suspensos || 0})</TabsTrigger>
                <TabsTrigger value="manual">Manuais ({dashboard?.total_manuais || 0})</TabsTrigger>
              </TabsList>

              <TabsContent value={tabAtiva} className="mt-4">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-800">
                        <th className="text-left py-2 text-gray-400">Restaurante</th>
                        <th className="text-left py-2 text-gray-400">Plano</th>
                        <th className="text-left py-2 text-gray-400">Status</th>
                        <th className="text-left py-2 text-gray-400">Dias Vencido</th>
                        <th className="text-right py-2 text-gray-400">Ações</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filtrados.map((r: any) => {
                        const badge = STATUS_BADGES[r.billing_status] || STATUS_BADGES.manual;
                        return (
                          <tr key={r.id} className="border-b border-gray-800">
                            <td className="py-2">
                              <div className="text-white font-medium">{r.nome_fantasia}</div>
                              <div className="text-xs text-gray-500">{r.email}</div>
                            </td>
                            <td className="py-2 text-gray-300">{r.plano}</td>
                            <td className="py-2"><Badge className={badge.color}>{badge.label}</Badge></td>
                            <td className="py-2 text-gray-300">{r.dias_vencido || 0}</td>
                            <td className="py-2 text-right space-x-1">
                              {r.billing_status === "manual" && (
                                <Button size="sm" variant="outline" onClick={() => handleMigrar(r.id)} title="Migrar para Asaas">
                                  <Upload className="h-3 w-3" />
                                </Button>
                              )}
                              {r.billing_status === "trial" && (
                                <Button size="sm" variant="outline" onClick={() => setTrialDialog({ id: r.id, nome: r.nome_fantasia })} title="Estender trial">
                                  <Clock className="h-3 w-3" />
                                </Button>
                              )}
                              {["suspended_billing", "canceled_billing", "overdue"].includes(r.billing_status) && (
                                <Button size="sm" variant="outline" onClick={() => handleReativar(r.id)} title="Reativar">
                                  <RotateCcw className="h-3 w-3" />
                                </Button>
                              )}
                              {["active", "overdue", "trial"].includes(r.billing_status) && (
                                <Button size="sm" variant="ghost" className="text-red-400" onClick={() => handleCancelar(r.id)} title="Cancelar">
                                  <XCircle className="h-3 w-3" />
                                </Button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                      {filtrados.length === 0 && (
                        <tr>
                          <td colSpan={5} className="text-center py-8 text-gray-500">Nenhum restaurante</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>

        {/* Audit Log Recente */}
        <Card className="bg-gray-900 border-gray-800">
          <CardHeader>
            <CardTitle className="text-white">Atividade Recente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {auditData?.logs?.map((log: any) => (
                <div key={log.id} className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
                  <div className="flex-1">
                    <span className="text-sm text-white">{AUDIT_LABELS[log.acao] || log.acao}</span>
                    {log.restaurante_nome && (
                      <span className="text-sm text-gray-400"> — {log.restaurante_nome}</span>
                    )}
                    {log.automatico && <Badge className="ml-2 bg-gray-700 text-gray-400 text-xs">Auto</Badge>}
                  </div>
                  <span className="text-xs text-gray-500">
                    {log.criado_em ? new Date(log.criado_em).toLocaleString("pt-BR") : ""}
                  </span>
                </div>
              ))}
              {(!auditData?.logs || auditData.logs.length === 0) && (
                <p className="text-center py-4 text-gray-500">Nenhuma atividade registrada</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dialog Estender Trial */}
      <Dialog open={!!trialDialog} onOpenChange={() => setTrialDialog(null)}>
        <DialogContent className="bg-gray-900 border-gray-800">
          <DialogHeader>
            <DialogTitle className="text-white">Estender Trial — {trialDialog?.nome}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm text-gray-400">Dias a adicionar</label>
            <Input
              type="number"
              value={trialDias}
              onChange={(e) => setTrialDias(parseInt(e.target.value) || 0)}
              className="bg-gray-800 border-gray-700 text-white"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTrialDialog(null)}>Cancelar</Button>
            <Button onClick={handleEstenderTrial} disabled={estenderTrial.isPending} className="bg-amber-600 hover:bg-amber-700">
              {estenderTrial.isPending ? "Salvando..." : "Estender"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SuperAdminLayout>
  );
}
