import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Lock, ArrowRight } from "lucide-react";
import { useLocation } from "wouter";
import { useFeatureFlag, FEATURE_LABELS, TIER_TO_PLANO, FEATURE_MIN_TIER } from "@/admin/hooks/useFeatureFlag";

interface UpgradePromptProps {
  feature: string;
  compact?: boolean;
}

export default function UpgradePrompt({ feature, compact }: UpgradePromptProps) {
  const [, navigate] = useLocation();
  const { plano, requiredPlano, featureLabel } = useFeatureFlag(feature);

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
        <Lock className="h-5 w-5 text-amber-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--text-primary)]">
            {featureLabel} — Plano {requiredPlano}+
          </p>
          <p className="text-xs text-[var(--text-muted)]">
            Seu plano: {plano}
          </p>
        </div>
        <Button size="sm" onClick={() => navigate("/plano")}>
          Upgrade
        </Button>
      </div>
    );
  }

  return (
    <Card className="bg-[var(--bg-surface)] border-amber-500/30">
      <CardContent className="flex flex-col items-center text-center py-12 px-6 space-y-4">
        <div className="h-16 w-16 rounded-full bg-amber-500/20 flex items-center justify-center">
          <Lock className="h-8 w-8 text-amber-400" />
        </div>
        <h2 className="text-xl font-bold text-[var(--text-primary)]">
          {featureLabel}
        </h2>
        <p className="text-[var(--text-secondary)] max-w-md">
          Esta funcionalidade requer o plano <strong className="text-[var(--text-primary)]">{requiredPlano}</strong> ou superior.
          Seu plano atual é <strong>{plano}</strong>.
        </p>
        <Button className="gap-2" onClick={() => navigate("/plano")}>
          Ver Planos <ArrowRight className="h-4 w-4" />
        </Button>
      </CardContent>
    </Card>
  );
}
