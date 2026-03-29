import AdminLayout from "@/admin/components/AdminLayout";
import { usePlanosDisponiveis, useSelecionarPlano, useBillingStatus } from "@/admin/hooks/useAdminQueries";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Check, ArrowLeft, Info } from "lucide-react";
import { useState } from "react";
import { useLocation } from "wouter";
import { toast } from "sonner";

export default function SelecionarPlano() {
  const [, navigate] = useLocation();
  const { refreshRestaurante } = useAdminAuth();
  const { data: planos, isLoading } = usePlanosDisponiveis();
  const { data: billing } = useBillingStatus();
  const selecionarPlano = useSelecionarPlano();

  const [ciclo, setCiclo] = useState<"MONTHLY" | "YEARLY">("MONTHLY");
  const [confirmDialog, setConfirmDialog] = useState<{ plano: string; valor: number } | null>(null);
  const [billingType, setBillingType] = useState("PIX");

  function handleAssinar() {
    if (!confirmDialog) return;
    selecionarPlano.mutate(
      { plano: confirmDialog.plano, ciclo, billing_type: billingType },
      {
        onSuccess: async () => {
          toast.success("Plano selecionado com sucesso!");
          setConfirmDialog(null);
          await refreshRestaurante();
          navigate("/billing");
        },
        onError: (err: any) => {
          toast.error(err?.response?.data?.detail || "Erro ao selecionar plano");
        },
      }
    );
  }

  const trialFim = billing?.trial_fim ? new Date(billing.trial_fim) : null;
  const diasTrial = trialFim ? Math.max(0, Math.ceil((trialFim.getTime() - Date.now()) / 86400000)) : 0;
  const isTrial = billing?.billing_status === "trial" && diasTrial > 0;

  if (isLoading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-[var(--cor-primaria)] border-t-transparent rounded-full" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon-sm" onClick={() => navigate("/billing")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Escolher Plano</h1>
        </div>

        {/* Info Trial */}
        {isTrial && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
            <Info className="h-5 w-5 text-blue-400 shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="text-[var(--text-primary)] font-medium">
                Voce ainda tem {diasTrial} dia{diasTrial !== 1 ? "s" : ""} de teste gratuito
              </p>
              <p className="text-[var(--text-muted)] mt-1">
                Pode assinar agora — a primeira cobranca sera apenas em {trialFim!.toLocaleDateString("pt-BR")}, quando o teste terminar.
              </p>
            </div>
          </div>
        )}

        {/* Toggle Ciclo */}
        <div className="flex justify-center">
          <div className="inline-flex rounded-lg border border-[var(--border-subtle)] p-1">
            <button
              onClick={() => setCiclo("MONTHLY")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                ciclo === "MONTHLY" ? "bg-[var(--cor-primaria)] text-white" : "text-[var(--text-secondary)]"
              }`}
            >
              Mensal
            </button>
            <button
              onClick={() => setCiclo("YEARLY")}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                ciclo === "YEARLY" ? "bg-[var(--cor-primaria)] text-white" : "text-[var(--text-secondary)]"
              }`}
            >
              Anual <Badge className="ml-1 bg-green-500/20 text-green-400 text-xs">-{planos?.[0]?.desconto_anual_percentual || 20}%</Badge>
            </button>
          </div>
        </div>

        {/* Cards de Planos */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {planos?.map((plano: any) => {
            const isAtual = billing?.plano === plano.nome;
            const valor = ciclo === "MONTHLY" ? plano.valor_mensal : plano.valor_anual_mensal;
            return (
              <Card
                key={plano.nome}
                className={`bg-[var(--bg-surface)] border-[var(--border-subtle)] relative ${
                  isAtual ? "ring-2 ring-[var(--cor-primaria)]" : ""
                }`}
              >
                {isAtual && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-[var(--cor-primaria)] text-white">Atual</Badge>
                  </div>
                )}
                <CardHeader className="text-center pb-2">
                  <CardTitle className="text-lg text-[var(--text-primary)]">{plano.nome}</CardTitle>
                  <p className="text-xs text-[var(--text-muted)]">{plano.descricao}</p>
                </CardHeader>
                <CardContent className="text-center space-y-4">
                  <div>
                    {ciclo === "YEARLY" && (
                      <p className="text-sm text-[var(--text-muted)] line-through">R$ {plano.valor_mensal.toFixed(2)}/mes</p>
                    )}
                    <p className="text-3xl font-bold text-[var(--text-primary)]">
                      R$ {valor.toFixed(2)}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">/mes</p>
                    {ciclo === "YEARLY" && (
                      <p className="text-xs text-green-400">R$ {plano.valor_anual_total.toFixed(2)}/ano</p>
                    )}
                  </div>

                  {plano.tier === 4 && (
                    <div className="flex items-center justify-center">
                      <Badge className="bg-green-500/20 text-green-400 text-xs">WhatsApp Humanoide incluso</Badge>
                    </div>
                  )}

                  <ul className="text-sm text-[var(--text-secondary)] space-y-1.5 text-left max-h-48 overflow-y-auto">
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-400 shrink-0" />
                      {plano.limite_motoboys >= 999 ? "Motoboys ilimitados" : `Ate ${plano.limite_motoboys} motoboys`}
                    </li>
                    {plano.features?.map((f: any) => (
                      <li key={f.key} className="flex items-center gap-2">
                        <Check className={`h-4 w-4 shrink-0 ${f.new ? "text-[var(--cor-primaria)]" : "text-green-400"}`} />
                        <span className={f.new ? "font-medium text-[var(--text-primary)]" : ""}>
                          {f.label}
                        </span>
                      </li>
                    )) ?? (
                      <>
                        <li className="flex items-center gap-2"><Check className="h-4 w-4 text-green-400 shrink-0" /> Pedidos ilimitados</li>
                        <li className="flex items-center gap-2"><Check className="h-4 w-4 text-green-400 shrink-0" /> Site personalizado</li>
                      </>
                    )}
                  </ul>

                  <Button
                    className="w-full"
                    variant={isAtual ? "outline" : "default"}
                    disabled={isAtual}
                    onClick={() => setConfirmDialog({
                      plano: plano.nome,
                      valor: ciclo === "MONTHLY" ? plano.valor_mensal : plano.valor_anual_total,
                    })}
                  >
                    {isAtual ? "Plano Atual" : "Assinar"}
                  </Button>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Dialog de Confirmacao */}
      <Dialog open={!!confirmDialog} onOpenChange={() => setConfirmDialog(null)}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Confirmar Assinatura</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-[var(--text-secondary)]">
              Plano: <strong className="text-[var(--text-primary)]">{confirmDialog?.plano}</strong>
            </p>
            <p className="text-[var(--text-secondary)]">
              Ciclo: <strong className="text-[var(--text-primary)]">{ciclo === "MONTHLY" ? "Mensal" : "Anual"}</strong>
            </p>
            <p className="text-[var(--text-secondary)]">
              Valor: <strong className="text-[var(--text-primary)]">R$ {confirmDialog?.valor?.toFixed(2)}</strong>
              {ciclo === "YEARLY" ? "/ano" : "/mes"}
            </p>
            {isTrial && (
              <div className="flex items-center gap-2 p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
                <Info className="h-4 w-4 text-blue-400 shrink-0" />
                <p className="text-xs text-blue-300">
                  Primeira cobranca em {trialFim!.toLocaleDateString("pt-BR")} (apos o trial)
                </p>
              </div>
            )}
            <div>
              <label className="text-sm text-[var(--text-muted)] mb-1 block">Forma de pagamento</label>
              <Select value={billingType} onValueChange={setBillingType}>
                <SelectTrigger className="bg-[var(--bg-base)] border-[var(--border-subtle)] text-[var(--text-primary)]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PIX">PIX</SelectItem>
                  <SelectItem value="BOLETO">Boleto</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDialog(null)}>Cancelar</Button>
            <Button onClick={handleAssinar} disabled={selecionarPlano.isPending}>
              {selecionarPlano.isPending ? "Processando..." : "Confirmar Assinatura"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
