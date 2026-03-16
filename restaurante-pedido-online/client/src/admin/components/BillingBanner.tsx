import { useBillingStatus } from "@/admin/hooks/useAdminQueries";
import { AlertTriangle, Clock, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useLocation } from "wouter";
import { useState } from "react";

export default function BillingBanner() {
  const { data: billing } = useBillingStatus();
  const [, navigate] = useLocation();
  const storageKey = "billing_banner_dismissed";
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem(storageKey) === "1");

  if (dismissed || !billing) return null;

  const trialFim = billing.trial_fim ? new Date(billing.trial_fim) : null;
  const diasTrial = trialFim ? Math.max(0, Math.ceil((trialFim.getTime() - Date.now()) / 86400000)) : 0;

  let content: { bg: string; icon: React.ReactNode; text: string; action?: string } | null = null;

  if (billing.billing_status === "trial" && diasTrial <= 5) {
    content = {
      bg: "bg-yellow-500/10 border-yellow-500/30",
      icon: <Clock className="h-4 w-4 text-yellow-400 shrink-0" />,
      text: `Seu periodo de teste termina em ${diasTrial} dia${diasTrial !== 1 ? "s" : ""}`,
      action: "Escolher plano",
    };
  } else if (billing.billing_status === "overdue") {
    content = {
      bg: "bg-red-500/10 border-red-500/30",
      icon: <AlertTriangle className="h-4 w-4 text-red-400 shrink-0" />,
      text: `Pagamento atrasado ha ${billing.dias_vencido || 0} dias`,
      action: "Pagar agora",
    };
  }

  if (!content) return null;

  return (
    <div className={`flex items-center gap-3 px-4 py-2 border rounded-lg mx-4 mt-2 ${content.bg}`}>
      {content.icon}
      <p className="flex-1 text-sm text-[var(--text-primary)]">{content.text}</p>
      {content.action && (
        <Button size="sm" variant="outline" onClick={() => navigate(billing.billing_status === "overdue" ? "/billing" : "/billing/planos")}>
          {content.action}
        </Button>
      )}
      <button onClick={() => { sessionStorage.setItem(storageKey, "1"); setDismissed(true); }} className="text-[var(--text-muted)] hover:text-[var(--text-primary)]">
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
