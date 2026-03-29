import AdminLayout from "@/admin/components/AdminLayout";
import { useBillingStatus, useFaturas, useAddons, useAtivarAddonBot, useDesativarAddonBot } from "@/admin/hooks/useAdminQueries";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CreditCard, Calendar, AlertTriangle, FileText, ExternalLink, Bot, Plus, X } from "lucide-react";
import { useLocation } from "wouter";
import { getFaturaPix } from "@/admin/lib/adminApiClient";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { toast } from "sonner";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  manual: { label: "Manual", color: "bg-gray-500/20 text-gray-400" },
  trial: { label: "Teste", color: "bg-blue-500/20 text-blue-400" },
  active: { label: "Ativo", color: "bg-green-500/20 text-green-400" },
  overdue: { label: "Vencido", color: "bg-yellow-500/20 text-yellow-400" },
  suspended_billing: { label: "Suspenso", color: "bg-red-500/20 text-red-400" },
  canceled_billing: { label: "Cancelado", color: "bg-red-700/20 text-red-500" },
};

const FATURA_STATUS: Record<string, { label: string; color: string }> = {
  PENDING: { label: "Pendente", color: "bg-yellow-500/20 text-yellow-400" },
  RECEIVED: { label: "Pago", color: "bg-green-500/20 text-green-400" },
  CONFIRMED: { label: "Confirmado", color: "bg-green-500/20 text-green-400" },
  OVERDUE: { label: "Vencido", color: "bg-red-500/20 text-red-400" },
  REFUNDED: { label: "Estornado", color: "bg-gray-500/20 text-gray-400" },
  DELETED: { label: "Deletado", color: "bg-gray-500/20 text-gray-400" },
};

export default function Billing() {
  const [, navigate] = useLocation();
  const { refreshRestaurante } = useAdminAuth();
  const { data: billing, isLoading } = useBillingStatus();
  const { data: faturasData } = useFaturas();
  const { data: addons } = useAddons();
  const ativarAddon = useAtivarAddonBot();
  const desativarAddon = useDesativarAddonBot();
  const [pixDialog, setPixDialog] = useState<{ qr_code: string; copia_cola: string; valor: number } | null>(null);
  const [loadingPix, setLoadingPix] = useState(false);
  const [addonDialog, setAddonDialog] = useState<"ativar" | "desativar" | null>(null);

  async function handleVerPix(faturaId: number) {
    setLoadingPix(true);
    try {
      const pix = await getFaturaPix(faturaId);
      setPixDialog(pix);
    } catch {
      // ignore
    } finally {
      setLoadingPix(false);
    }
  }

  function handleAtivarAddon() {
    ativarAddon.mutate(undefined, {
      onSuccess: async () => {
        toast.success("Add-on WhatsApp Humanoide ativado!");
        setAddonDialog(null);
        await refreshRestaurante();
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.detail || "Erro ao ativar add-on");
      },
    });
  }

  function handleDesativarAddon() {
    desativarAddon.mutate(undefined, {
      onSuccess: async () => {
        toast.success("Add-on desativado. O bot foi desligado.");
        setAddonDialog(null);
        await refreshRestaurante();
      },
      onError: (err: any) => {
        toast.error(err?.response?.data?.detail || "Erro ao desativar add-on");
      },
    });
  }

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-[var(--cor-primaria)] border-t-transparent rounded-full" />
        </div>
      </AdminLayout>
    );
  }

  const statusInfo = STATUS_LABELS[billing?.billing_status] || STATUS_LABELS.manual;
  const trialFim = billing?.trial_fim ? new Date(billing.trial_fim) : null;
  const diasTrial = trialFim ? Math.max(0, Math.ceil((trialFim.getTime() - Date.now()) / 86400000)) : 0;
  const isTrial = billing?.billing_status === "trial" && diasTrial > 0;
  const isPremium = billing?.plano === "Premium";

  // Add-on bot info
  const botAddon = (addons as any[])?.find((a: any) => a.key === "bot_whatsapp");
  const showAddons = !isTrial && !isPremium && billing?.billing_status === "active";

  // Valor base e addon para breakdown
  const valorBase = billing?.valor_base_plano || (billing?.valor_plano - (billing?.addon_bot_valor || 0));
  const valorAddon = billing?.addon_bot_valor || 0;

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Minha Assinatura</h1>
          <Button onClick={() => navigate("/billing/planos")}>
            {billing?.billing_status === "trial" ? "Escolher Plano" : "Trocar Plano"}
          </Button>
        </div>

        {/* Banner Trial */}
        {isTrial && (
          <Card className="border-blue-500/30 bg-blue-500/10">
            <CardContent className="flex items-center gap-4 p-4">
              <Calendar className="h-6 w-6 text-blue-400 shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-blue-400">
                  Periodo de teste: {diasTrial} dia{diasTrial !== 1 ? "s" : ""} restante{diasTrial !== 1 ? "s" : ""}
                </p>
                <p className="text-sm text-[var(--text-muted)]">
                  Escolha um plano a qualquer momento. A primeira cobranca sera apenas apos o fim do teste ({trialFim?.toLocaleDateString("pt-BR")}).
                </p>
              </div>
              <Button size="sm" onClick={() => navigate("/billing/planos")}>Escolher Plano</Button>
            </CardContent>
          </Card>
        )}

        {/* Cards de Status */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-[var(--text-muted)]">Plano</CardTitle>
              <CreditCard className="h-4 w-4 text-[var(--text-muted)]" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[var(--text-primary)]">{billing?.plano || "\u2014"}</div>
              <p className="text-xs text-[var(--text-muted)]">{billing?.plano_ciclo === "YEARLY" ? "Anual" : "Mensal"}</p>
            </CardContent>
          </Card>

          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-[var(--text-muted)]">Status</CardTitle>
            </CardHeader>
            <CardContent>
              <Badge className={statusInfo.color}>{statusInfo.label}</Badge>
              {billing?.billing_status === "trial" && (
                <p className="text-xs text-[var(--text-muted)] mt-1">{diasTrial} dias restantes</p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-[var(--text-muted)]">Valor</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[var(--text-primary)]">
                R$ {billing?.valor_plano?.toFixed(2) || "0,00"}
              </div>
              <p className="text-xs text-[var(--text-muted)]">/{billing?.plano_ciclo === "YEARLY" ? "ano" : "mes"}</p>
              {valorAddon > 0 && (
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Plano R${valorBase?.toFixed(2)} + Add-on R${valorAddon.toFixed(2)}
                </p>
              )}
            </CardContent>
          </Card>

          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm text-[var(--text-muted)]">Proximo Vencimento</CardTitle>
              <Calendar className="h-4 w-4 text-[var(--text-muted)]" />
            </CardHeader>
            <CardContent>
              <div className="text-lg font-bold text-[var(--text-primary)]">
                {billing?.proximo_vencimento ? new Date(billing.proximo_vencimento).toLocaleDateString("pt-BR") : "\u2014"}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Banner Overdue */}
        {billing?.billing_status === "overdue" && billing?.pix_info && (
          <Card className="border-red-500/50 bg-red-500/10">
            <CardContent className="flex items-center gap-4 p-4">
              <AlertTriangle className="h-6 w-6 text-red-400 shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-red-400">Pagamento atrasado ha {billing.dias_vencido} dias</p>
                <p className="text-sm text-[var(--text-muted)]">
                  Regularize para evitar suspensao em {Math.max(0, (billing.dias_suspensao || 2) - (billing.dias_vencido || 0))} dias
                </p>
              </div>
              {billing.pix_info.invoice_url && (
                <Button variant="destructive" size="sm" asChild>
                  <a href={billing.pix_info.invoice_url} target="_blank" rel="noopener noreferrer">
                    Pagar Agora <ExternalLink className="h-4 w-4 ml-1" />
                  </a>
                </Button>
              )}
            </CardContent>
          </Card>
        )}

        {/* Add-ons */}
        {showAddons && botAddon && (
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                <Bot className="h-5 w-5" /> Add-ons
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between p-4 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-base)]">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <Bot className="h-5 w-5 text-green-400" />
                  </div>
                  <div>
                    <p className="font-medium text-[var(--text-primary)]">WhatsApp Humanoide</p>
                    <p className="text-sm text-[var(--text-muted)]">
                      Atendimento IA humanizado via WhatsApp
                    </p>
                    <p className="text-sm font-semibold text-[var(--cor-primaria)]">+R$99,45/mes</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {botAddon.active ? (
                    <>
                      <Badge className="bg-green-500/20 text-green-400">Ativo</Badge>
                      <Button variant="outline" size="sm" onClick={() => setAddonDialog("desativar")}>
                        <X className="h-4 w-4 mr-1" /> Desativar
                      </Button>
                    </>
                  ) : botAddon.can_subscribe ? (
                    <Button size="sm" onClick={() => setAddonDialog("ativar")}>
                      <Plus className="h-4 w-4 mr-1" /> Ativar
                    </Button>
                  ) : (
                    <Badge className="bg-amber-500/20 text-amber-400">
                      Requer {botAddon.min_plano}+
                    </Badge>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tabela de Faturas */}
        <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
          <CardHeader>
            <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
              <FileText className="h-5 w-5" /> Faturas
            </CardTitle>
          </CardHeader>
          <CardContent>
            {faturasData?.faturas?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border-subtle)]">
                      <th className="text-left py-2 text-[var(--text-muted)]">Data</th>
                      <th className="text-left py-2 text-[var(--text-muted)]">Valor</th>
                      <th className="text-left py-2 text-[var(--text-muted)]">Tipo</th>
                      <th className="text-left py-2 text-[var(--text-muted)]">Status</th>
                      <th className="text-right py-2 text-[var(--text-muted)]">Acoes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {faturasData.faturas.map((f: any) => {
                      const fStatus = FATURA_STATUS[f.status] || { label: f.status, color: "bg-gray-500/20 text-gray-400" };
                      return (
                        <tr key={f.id} className="border-b border-[var(--border-subtle)]">
                          <td className="py-2 text-[var(--text-primary)]">
                            {f.data_vencimento ? new Date(f.data_vencimento).toLocaleDateString("pt-BR") : "\u2014"}
                          </td>
                          <td className="py-2 text-[var(--text-primary)]">R$ {f.valor?.toFixed(2)}</td>
                          <td className="py-2 text-[var(--text-secondary)]">{f.billing_type || "\u2014"}</td>
                          <td className="py-2"><Badge className={fStatus.color}>{fStatus.label}</Badge></td>
                          <td className="py-2 text-right space-x-2">
                            {(f.status === "PENDING" || f.status === "OVERDUE") && (
                              <Button variant="outline" size="sm" onClick={() => handleVerPix(f.id)} disabled={loadingPix}>
                                PIX
                              </Button>
                            )}
                            {f.invoice_url && (
                              <Button variant="ghost" size="sm" asChild>
                                <a href={f.invoice_url} target="_blank" rel="noopener noreferrer">
                                  <ExternalLink className="h-4 w-4" />
                                </a>
                              </Button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-[var(--text-muted)] text-center py-8">Nenhuma fatura encontrada</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Dialog PIX */}
      <Dialog open={!!pixDialog} onOpenChange={() => setPixDialog(null)}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Pagar com PIX</DialogTitle>
          </DialogHeader>
          {pixDialog && (
            <div className="flex flex-col items-center gap-4">
              <p className="text-lg font-bold text-[var(--text-primary)]">R$ {pixDialog.valor?.toFixed(2)}</p>
              {pixDialog.qr_code && (
                <img src={`data:image/png;base64,${pixDialog.qr_code}`} alt="QR Code PIX" className="w-48 h-48" />
              )}
              {pixDialog.copia_cola && (
                <div className="w-full">
                  <p className="text-xs text-[var(--text-muted)] mb-1">Copia e cola:</p>
                  <div className="flex gap-2">
                    <input
                      readOnly
                      value={pixDialog.copia_cola}
                      className="flex-1 text-xs bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-[var(--text-primary)]"
                    />
                    <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(pixDialog.copia_cola)}>
                      Copiar
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dialog Ativar Add-on */}
      <Dialog open={addonDialog === "ativar"} onOpenChange={() => setAddonDialog(null)}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Ativar WhatsApp Humanoide</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-[var(--text-secondary)]">
              O add-on sera adicionado a sua fatura mensal:
            </p>
            <div className="p-4 rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-secondary)]">Plano {billing?.plano}</span>
                <span className="text-[var(--text-primary)]">R$ {valorBase?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-secondary)]">WhatsApp Humanoide</span>
                <span className="text-green-400">+ R$ 99,45</span>
              </div>
              <div className="border-t border-[var(--border-subtle)] pt-2 flex justify-between font-bold">
                <span className="text-[var(--text-primary)]">Total mensal</span>
                <span className="text-[var(--text-primary)]">R$ {((valorBase || 0) + 99.45).toFixed(2)}</span>
              </div>
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              Voce pode desativar a qualquer momento. A proxima fatura ja refletira o novo valor.
            </p>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddonDialog(null)}>Cancelar</Button>
            <Button onClick={handleAtivarAddon} disabled={ativarAddon.isPending}>
              {ativarAddon.isPending ? "Ativando..." : "Confirmar Ativacao"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Dialog Desativar Add-on */}
      <Dialog open={addonDialog === "desativar"} onOpenChange={() => setAddonDialog(null)}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Desativar WhatsApp Humanoide</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-[var(--text-secondary)]">
              Ao desativar, o bot sera desligado imediatamente e o valor sera removido da proxima fatura.
            </p>
            <div className="p-4 rounded-lg bg-[var(--bg-base)] border border-[var(--border-subtle)] space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-secondary)]">Valor atual</span>
                <span className="text-[var(--text-primary)]">R$ {billing?.valor_plano?.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-secondary)]">WhatsApp Humanoide</span>
                <span className="text-red-400">- R$ 99,45</span>
              </div>
              <div className="border-t border-[var(--border-subtle)] pt-2 flex justify-between font-bold">
                <span className="text-[var(--text-primary)]">Novo valor mensal</span>
                <span className="text-[var(--text-primary)]">R$ {valorBase?.toFixed(2)}</span>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddonDialog(null)}>Cancelar</Button>
            <Button variant="destructive" onClick={handleDesativarAddon} disabled={desativarAddon.isPending}>
              {desativarAddon.isPending ? "Desativando..." : "Confirmar Desativacao"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
