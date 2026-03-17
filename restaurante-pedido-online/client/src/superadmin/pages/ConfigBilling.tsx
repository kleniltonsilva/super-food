import { useState, useEffect } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useBillingConfig, useAtualizarBillingConfig } from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Save, Settings, Shield, Copy } from "lucide-react";
import { toast } from "sonner";

export default function ConfigBilling() {
  const { data: config, isLoading } = useBillingConfig();
  const atualizarConfig = useAtualizarBillingConfig();

  const [form, setForm] = useState({
    trial_dias: 20,
    trial_plano: "Premium",
    dias_lembrete_antes: 5,
    dias_suspensao: 2,
    dias_aviso_cancelamento: 5,
    dias_cancelamento: 15,
    dias_preservacao_dados: 90,
    desconto_anual_percentual: 20,
    asaas_webhook_token: "",
  });

  useEffect(() => {
    if (config) {
      setForm({
        trial_dias: config.trial_dias ?? 20,
        trial_plano: config.trial_plano ?? "Premium",
        dias_lembrete_antes: config.dias_lembrete_antes ?? 5,
        dias_suspensao: config.dias_suspensao ?? 2,
        dias_aviso_cancelamento: config.dias_aviso_cancelamento ?? 5,
        dias_cancelamento: config.dias_cancelamento ?? 15,
        dias_preservacao_dados: config.dias_preservacao_dados ?? 90,
        desconto_anual_percentual: config.desconto_anual_percentual ?? 20,
        asaas_webhook_token: config.asaas_webhook_token ?? "",
      });
    }
  }, [config]);

  function handleSave() {
    atualizarConfig.mutate(form, {
      onSuccess: () => toast.success("Configuração salva!"),
      onError: () => toast.error("Erro ao salvar"),
    });
  }

  function copyWebhookUrl() {
    const url = `${window.location.origin}/webhooks/asaas`;
    navigator.clipboard.writeText(url);
    toast.success("URL copiada!");
  }

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
      <div className="space-y-6 max-w-3xl">
        <h1 className="text-2xl font-bold text-[var(--sa-text-primary)] flex items-center gap-2">
          <Settings className="h-6 w-6" /> Configuração de Billing
        </h1>

        {/* Trial */}
        <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
          <CardHeader>
            <CardTitle className="text-[var(--sa-text-primary)] text-lg">Período de Teste</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Dias de trial</label>
                <Input
                  type="number"
                  value={form.trial_dias}
                  onChange={(e) => setForm({ ...form, trial_dias: parseInt(e.target.value) || 0 })}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Plano do trial</label>
                <Select value={form.trial_plano} onValueChange={(v) => setForm({ ...form, trial_plano: v })}>
                  <SelectTrigger className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Básico">Básico</SelectItem>
                    <SelectItem value="Essencial">Essencial</SelectItem>
                    <SelectItem value="Avançado">Avançado</SelectItem>
                    <SelectItem value="Premium">Premium</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1">
              <label className="text-sm text-[var(--sa-text-muted)]">Dias de aviso antes do fim do trial</label>
              <Input
                type="number"
                value={form.dias_lembrete_antes}
                onChange={(e) => setForm({ ...form, dias_lembrete_antes: parseInt(e.target.value) || 0 })}
                className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
              />
            </div>
          </CardContent>
        </Card>

        {/* Inadimplência */}
        <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
          <CardHeader>
            <CardTitle className="text-[var(--sa-text-primary)] text-lg">Regras de Inadimplência</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Dias até suspensão (após vencimento)</label>
                <Input
                  type="number"
                  value={form.dias_suspensao}
                  onChange={(e) => setForm({ ...form, dias_suspensao: parseInt(e.target.value) || 0 })}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Dias de aviso antes do cancelamento</label>
                <Input
                  type="number"
                  value={form.dias_aviso_cancelamento}
                  onChange={(e) => setForm({ ...form, dias_aviso_cancelamento: parseInt(e.target.value) || 0 })}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Dias até cancelamento (após suspensão)</label>
                <Input
                  type="number"
                  value={form.dias_cancelamento}
                  onChange={(e) => setForm({ ...form, dias_cancelamento: parseInt(e.target.value) || 0 })}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                />
              </div>
              <div className="space-y-1">
                <label className="text-sm text-[var(--sa-text-muted)]">Dias de preservação de dados</label>
                <Input
                  type="number"
                  value={form.dias_preservacao_dados}
                  onChange={(e) => setForm({ ...form, dias_preservacao_dados: parseInt(e.target.value) || 0 })}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Preços */}
        <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
          <CardHeader>
            <CardTitle className="text-[var(--sa-text-primary)] text-lg">Descontos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1">
              <label className="text-sm text-[var(--sa-text-muted)]">Desconto anual (%)</label>
              <Input
                type="number"
                step="0.1"
                value={form.desconto_anual_percentual}
                onChange={(e) => setForm({ ...form, desconto_anual_percentual: parseFloat(e.target.value) || 0 })}
                className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)] max-w-xs"
              />
            </div>
          </CardContent>
        </Card>

        {/* Asaas */}
        <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
          <CardHeader>
            <CardTitle className="text-[var(--sa-text-primary)] text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" /> Asaas
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-[var(--sa-text-muted)]">Ambiente:</span>
              <Badge className={config?.asaas_environment === "production" ? "bg-green-500/20 text-green-400" : "bg-yellow-500/20 text-yellow-400"}>
                {config?.asaas_environment === "production" ? "Produção" : "Sandbox"}
              </Badge>
              <Badge className={config?.asaas_configured ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"}>
                {config?.asaas_configured ? "Configurado" : "Não Configurado"}
              </Badge>
            </div>

            <div className="space-y-1">
              <label className="text-sm text-[var(--sa-text-muted)]">Webhook Token (para validar webhooks recebidos)</label>
              <Input
                value={form.asaas_webhook_token}
                onChange={(e) => setForm({ ...form, asaas_webhook_token: e.target.value })}
                className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-primary)]"
                placeholder="Token secreto"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm text-[var(--sa-text-muted)]">URL do Webhook (copie e configure no Asaas)</label>
              <div className="flex gap-2">
                <Input
                  readOnly
                  value={`${window.location.origin}/webhooks/asaas`}
                  className="bg-[var(--sa-bg-hover)] border-[var(--sa-border-input)] text-[var(--sa-text-secondary)]"
                />
                <Button variant="outline" size="icon" onClick={copyWebhookUrl}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Button onClick={handleSave} disabled={atualizarConfig.isPending} className="bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)]">
          <Save className="h-4 w-4 mr-2" />
          {atualizarConfig.isPending ? "Salvando..." : "Salvar Configuração"}
        </Button>
      </div>
    </SuperAdminLayout>
  );
}
