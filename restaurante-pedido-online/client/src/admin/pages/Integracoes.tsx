import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useIntegracoes,
  useIFoodStatus,
  useSetupIFood,
  useTestIFood,
  useToggleIFood,
  useRemoveIFood,
  useSyncCatalogIFood,
  useSetupOpenDelivery,
  useToggleOpenDelivery,
  useRemoveOpenDelivery,
} from "@/admin/hooks/useAdminQueries";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Plug, Wifi, WifiOff, RefreshCw, Trash2, TestTube, Upload, ExternalLink } from "lucide-react";
import { toast } from "sonner";

// Marketplace configs
const MARKETPLACES = [
  {
    id: "ifood",
    nome: "iFood",
    descricao: "Receba pedidos do iFood automaticamente. Polling a cada 30s.",
    cor: "bg-red-500",
    corBadge: "bg-red-100 text-red-700 border-red-200",
    tipo: "ifood",
  },
  {
    id: "99food",
    nome: "99Food",
    descricao: "Integração via Open Delivery (ABRASEL). Receba pedidos via webhook.",
    cor: "bg-yellow-500",
    corBadge: "bg-yellow-100 text-yellow-700 border-yellow-200",
    tipo: "opendelivery",
  },
  {
    id: "rappi",
    nome: "Rappi",
    descricao: "Integração via Open Delivery (ABRASEL). Receba pedidos via webhook.",
    cor: "bg-orange-500",
    corBadge: "bg-orange-100 text-orange-700 border-orange-200",
    tipo: "opendelivery",
  },
  {
    id: "keeta",
    nome: "Keeta",
    descricao: "Integração via Open Delivery (ABRASEL). Receba pedidos via webhook.",
    cor: "bg-blue-500",
    corBadge: "bg-blue-100 text-blue-700 border-blue-200",
    tipo: "opendelivery",
  },
];

export default function Integracoes() {
  const { data: integracoes, isLoading } = useIntegracoes();
  const { data: ifoodStatus } = useIFoodStatus();
  const setupIFood = useSetupIFood();
  const testIFood = useTestIFood();
  const toggleIFood = useToggleIFood();
  const removeIFood = useRemoveIFood();
  const syncCatalog = useSyncCatalogIFood();
  const setupOD = useSetupOpenDelivery();
  const toggleOD = useToggleOpenDelivery();
  const removeOD = useRemoveOpenDelivery();

  const [showSetup, setShowSetup] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // Form state
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [merchantId, setMerchantId] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState("");
  const [webhookSecret, setWebhookSecret] = useState("");

  const integsList = Array.isArray(integracoes) ? integracoes : [];

  function getInteg(marketplaceId: string) {
    return integsList.find((i: Record<string, unknown>) => i.marketplace === marketplaceId);
  }

  function handleSetup(marketplaceId: string) {
    const existing = getInteg(marketplaceId);
    setClientId((existing?.client_id as string) || "");
    setClientSecret("");
    setMerchantId((existing?.merchant_id as string) || "");
    setApiBaseUrl("");
    setWebhookSecret("");
    setShowSetup(marketplaceId);
  }

  async function handleSaveSetup() {
    if (!showSetup) return;
    const mp = MARKETPLACES.find((m) => m.id === showSetup);
    if (!mp) return;

    try {
      if (mp.tipo === "ifood") {
        await setupIFood.mutateAsync({ client_id: clientId, client_secret: clientSecret, merchant_id: merchantId });
      } else {
        await setupOD.mutateAsync({
          marketplace: showSetup,
          client_id: clientId || undefined,
          client_secret: clientSecret || undefined,
          merchant_id: merchantId || undefined,
          api_base_url: apiBaseUrl || undefined,
          webhook_secret: webhookSecret || undefined,
        });
      }
      toast.success(`${mp.nome} configurado com sucesso`);
      setShowSetup(null);
    } catch {
      toast.error("Erro ao salvar configuração");
    }
  }

  async function handleToggle(marketplaceId: string) {
    const mp = MARKETPLACES.find((m) => m.id === marketplaceId);
    if (!mp) return;
    try {
      if (mp.tipo === "ifood") {
        const res = await toggleIFood.mutateAsync();
        toast.success(res.mensagem || `${mp.nome} ${res.ativo ? "ativado" : "desativado"}`);
      } else {
        const res = await toggleOD.mutateAsync(marketplaceId);
        toast.success(res.mensagem || `${mp.nome} ${res.ativo ? "ativado" : "desativado"}`);
      }
    } catch {
      toast.error("Erro ao alternar integração");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    const mp = MARKETPLACES.find((m) => m.id === deleteTarget);
    if (!mp) return;
    try {
      if (mp.tipo === "ifood") {
        await removeIFood.mutateAsync();
      } else {
        await removeOD.mutateAsync(deleteTarget);
      }
      toast.success(`${mp.nome} removido`);
      setDeleteTarget(null);
    } catch {
      toast.error("Erro ao remover integração");
    }
  }

  async function handleTest() {
    try {
      const res = await testIFood.mutateAsync();
      if (res.success) {
        toast.success(res.mensagem);
      } else {
        toast.error(res.mensagem);
      }
    } catch {
      toast.error("Erro ao testar conexão");
    }
  }

  async function handleSyncCatalog() {
    try {
      const res = await syncCatalog.mutateAsync();
      if (res.success) {
        toast.success(`Sincronizado: ${res.categories_synced} categorias, ${res.products_synced} produtos`);
      } else {
        toast.error(`Sincronização parcial: ${res.errors?.length || 0} erros`);
      }
    } catch {
      toast.error("Erro ao sincronizar catálogo");
    }
  }

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Integrações</h1>
          <p className="text-sm text-[var(--text-muted)]">
            Conecte seu restaurante aos principais marketplaces de delivery
          </p>
        </div>

        {/* iFood Status Card (se configurado) */}
        {ifoodStatus?.configurado && (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2 text-[var(--text-primary)]">
                {ifoodStatus.polling_ativo ? (
                  <Wifi className="h-4 w-4 text-green-500" />
                ) : (
                  <WifiOff className="h-4 w-4 text-red-500" />
                )}
                Status iFood
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-[var(--text-muted)]">Polling</p>
                  <p className="font-medium text-[var(--text-primary)]">
                    {ifoodStatus.polling_ativo ? "Ativo" : "Inativo"}
                  </p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Token</p>
                  <p className="font-medium text-[var(--text-primary)]">
                    {ifoodStatus.token_valido ? "Válido" : "Expirado"}
                  </p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Pedidos Hoje</p>
                  <p className="font-medium text-[var(--text-primary)]">{ifoodStatus.pedidos_hoje || 0}</p>
                </div>
                <div>
                  <p className="text-[var(--text-muted)]">Último Evento</p>
                  <p className="font-medium text-[var(--text-primary)]">
                    {ifoodStatus.ultimo_evento
                      ? `${ifoodStatus.ultimo_evento.tipo} (${new Date(ifoodStatus.ultimo_evento.data).toLocaleTimeString("pt-BR")})`
                      : "Nenhum"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Marketplace Cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {MARKETPLACES.map((mp) => {
            const integ = getInteg(mp.id);
            const isConfigured = !!integ;
            const isActive = integ?.ativo === true;

            return (
              <Card key={mp.id} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg ${mp.cor} flex items-center justify-center`}>
                        <Plug className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <CardTitle className="text-base text-[var(--text-primary)]">{mp.nome}</CardTitle>
                        <p className="text-xs text-[var(--text-muted)]">
                          {mp.tipo === "ifood" ? "API Proprietária" : "Open Delivery (ABRASEL)"}
                        </p>
                      </div>
                    </div>
                    {isConfigured && (
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={isActive ? "bg-green-100 text-green-700 border-green-200" : ""}>
                          {isActive ? "Ativo" : "Inativo"}
                        </Badge>
                        <Switch checked={isActive} onCheckedChange={() => handleToggle(mp.id)} />
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[var(--text-secondary)] mb-4">{mp.descricao}</p>
                  {isConfigured && integ?.merchant_id && (
                    <p className="text-xs text-[var(--text-muted)] mb-3">
                      Merchant ID: <code className="bg-[var(--bg-subtle)] px-1 rounded">{integ.merchant_id as string}</code>
                    </p>
                  )}
                  <Separator className="mb-3" />
                  <div className="flex gap-2 flex-wrap">
                    <Button size="sm" variant="outline" onClick={() => handleSetup(mp.id)}>
                      {isConfigured ? "Editar" : "Configurar"}
                    </Button>
                    {isConfigured && mp.tipo === "ifood" && (
                      <>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleTest}
                          disabled={testIFood.isPending}
                        >
                          <TestTube className="mr-1 h-3 w-3" />
                          {testIFood.isPending ? "Testando..." : "Testar"}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={handleSyncCatalog}
                          disabled={syncCatalog.isPending || !isActive}
                        >
                          <Upload className="mr-1 h-3 w-3" />
                          {syncCatalog.isPending ? "Sincronizando..." : "Sync Cardápio"}
                        </Button>
                      </>
                    )}
                    {isConfigured && mp.tipo === "opendelivery" && (
                      <div className="flex items-center gap-1 text-xs text-[var(--text-muted)]">
                        <ExternalLink className="h-3 w-3" />
                        Webhook: /webhooks/opendelivery/{"{id}"}
                      </div>
                    )}
                    {isConfigured && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-red-500 hover:text-red-700"
                        onClick={() => setDeleteTarget(mp.id)}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Setup Dialog */}
      <Dialog open={!!showSetup} onOpenChange={() => setShowSetup(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Configurar {MARKETPLACES.find((m) => m.id === showSetup)?.nome}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {showSetup === "ifood" ? (
              <>
                <div>
                  <label className="text-sm font-medium">Client ID</label>
                  <Input value={clientId} onChange={(e) => setClientId(e.target.value)} placeholder="Seu client_id do iFood" />
                </div>
                <div>
                  <label className="text-sm font-medium">Client Secret</label>
                  <Input
                    type="password"
                    value={clientSecret}
                    onChange={(e) => setClientSecret(e.target.value)}
                    placeholder="Seu client_secret do iFood"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Merchant ID</label>
                  <Input value={merchantId} onChange={(e) => setMerchantId(e.target.value)} placeholder="ID do seu restaurante no iFood" />
                </div>
              </>
            ) : (
              <>
                <div>
                  <label className="text-sm font-medium">Client ID (opcional)</label>
                  <Input value={clientId} onChange={(e) => setClientId(e.target.value)} />
                </div>
                <div>
                  <label className="text-sm font-medium">Client Secret (opcional)</label>
                  <Input type="password" value={clientSecret} onChange={(e) => setClientSecret(e.target.value)} />
                </div>
                <div>
                  <label className="text-sm font-medium">Merchant ID (opcional)</label>
                  <Input value={merchantId} onChange={(e) => setMerchantId(e.target.value)} />
                </div>
                <div>
                  <label className="text-sm font-medium">API Base URL (opcional)</label>
                  <Input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} placeholder="https://api.marketplace.com" />
                </div>
                <div>
                  <label className="text-sm font-medium">Webhook Secret (opcional)</label>
                  <Input value={webhookSecret} onChange={(e) => setWebhookSecret(e.target.value)} placeholder="Para validação HMAC" />
                </div>
              </>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSetup(null)}>Cancelar</Button>
            <Button onClick={handleSaveSetup} disabled={setupIFood.isPending || setupOD.isPending}>
              {setupIFood.isPending || setupOD.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover integração?</AlertDialogTitle>
            <AlertDialogDescription>
              Todas as credenciais serão apagadas. Os pedidos já recebidos não serão afetados.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
