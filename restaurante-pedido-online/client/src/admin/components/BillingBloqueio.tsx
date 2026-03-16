import { Button } from "@/components/ui/button";
import { useBillingStatus } from "@/admin/hooks/useAdminQueries";
import { AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";
import { useState } from "react";

export default function BillingBloqueio() {
  const { data: billing, refetch } = useBillingStatus();
  const [polling, setPolling] = useState(false);

  if (!billing || !["suspended_billing", "canceled_billing"].includes(billing.billing_status)) {
    return null;
  }

  async function handleJaPaguei() {
    setPolling(true);
    await refetch();
    setTimeout(() => setPolling(false), 2000);
  }

  const diasRestantes = billing.dias_cancelamento
    ? Math.max(0, billing.dias_cancelamento - (billing.dias_vencido || 0))
    : 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="max-w-md w-full mx-4 bg-[var(--bg-surface)] rounded-2xl p-8 text-center space-y-6 shadow-2xl">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-full bg-red-500/20 flex items-center justify-center">
            <AlertTriangle className="h-8 w-8 text-red-400" />
          </div>
        </div>

        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)]">
            {billing.billing_status === "canceled_billing" ? "Assinatura Cancelada" : "Assinatura Suspensa"}
          </h2>
          <p className="text-sm text-[var(--text-muted)] mt-2">
            {billing.billing_status === "canceled_billing"
              ? "Sua assinatura foi cancelada por falta de pagamento."
              : "Regularize seu pagamento para voltar a usar o sistema."}
          </p>
        </div>

        {/* PIX QR Code */}
        {billing.pix_info?.qr_code && (
          <div className="space-y-2">
            <img
              src={`data:image/png;base64,${billing.pix_info.qr_code}`}
              alt="QR Code PIX"
              className="w-40 h-40 mx-auto rounded-lg"
            />
            {billing.pix_info.copia_cola && (
              <div className="flex gap-2">
                <input
                  readOnly
                  value={billing.pix_info.copia_cola}
                  className="flex-1 text-xs bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded px-2 py-1 text-[var(--text-primary)]"
                />
                <Button size="sm" variant="outline" onClick={() => navigator.clipboard.writeText(billing.pix_info.copia_cola)}>
                  Copiar
                </Button>
              </div>
            )}
            <p className="text-lg font-bold text-[var(--text-primary)]">R$ {billing.pix_info.valor?.toFixed(2)}</p>
          </div>
        )}

        {/* Invoice URL */}
        {billing.pix_info?.invoice_url && (
          <Button variant="destructive" className="w-full" asChild>
            <a href={billing.pix_info.invoice_url} target="_blank" rel="noopener noreferrer">
              Pagar Online <ExternalLink className="h-4 w-4 ml-2" />
            </a>
          </Button>
        )}

        {/* Aviso de cancelamento */}
        {billing.billing_status === "suspended_billing" && diasRestantes <= 10 && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
            <p className="text-sm font-semibold text-red-400">
              Seu contrato sera cancelado em {diasRestantes} dias
            </p>
          </div>
        )}

        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={handleJaPaguei} disabled={polling}>
            <RefreshCw className={`h-4 w-4 mr-2 ${polling ? "animate-spin" : ""}`} />
            {polling ? "Verificando..." : "Ja paguei"}
          </Button>
        </div>
      </div>
    </div>
  );
}
