import { useState, useEffect, useRef } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  useIntegracoes,
  useIFoodStatus,
  useConnectIFood,
  useDisconnectIFood,
  useToggleIntegracao,
  useSyncCatalogIFood,
  useConnectOpenDelivery,
  useDisconnectMarketplace,
} from "@/admin/hooks/useAdminQueries";
import { getIFoodAuthStatus } from "@/admin/lib/adminApiClient";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { Plug, Wifi, WifiOff, Upload, Link2, Unlink } from "lucide-react";
import { toast } from "sonner";

const MARKETPLACE_META: Record<string, { nome: string; cor: string; tipo: string }> = {
  ifood: { nome: "iFood", cor: "bg-red-500", tipo: "ifood" },
  "99food": { nome: "99Food", cor: "bg-yellow-500", tipo: "opendelivery" },
  rappi: { nome: "Rappi", cor: "bg-orange-500", tipo: "proprietario" },
  keeta: { nome: "Keeta", cor: "bg-blue-500", tipo: "opendelivery" },
};

interface IntegracaoItem {
  marketplace: string;
  disponivel: boolean;
  conectado: boolean;
  ativo: boolean;
  authorization_status: string | null;
  merchant_id: string | null;
  authorized_at: string | null;
  token_expires_at: string | null;
}

export default function Integracoes() {
  const { data: integracoes, isLoading } = useIntegracoes();
  const { data: ifoodStatus } = useIFoodStatus();
  const connectIFood = useConnectIFood();
  const disconnectIFood = useDisconnectIFood();
  const toggleIntegracao = useToggleIntegracao();
  const syncCatalog = useSyncCatalogIFood();
  const connectOD = useConnectOpenDelivery();
  const disconnectMk = useDisconnectMarketplace();

  const [disconnectTarget, setDisconnectTarget] = useState<string | null>(null);
  const [userCodeDialog, setUserCodeDialog] = useState<{ code: string; url: string } | null>(null);
  const [pollingAuth, setPollingAuth] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const integsList: IntegracaoItem[] = Array.isArray(integracoes) ? integracoes : [];

  // Polling para autorização iFood (a cada 5s enquanto ativo)
  useEffect(() => {
    if (!pollingAuth) return;

    pollingRef.current = setInterval(async () => {
      try {
        const res = await getIFoodAuthStatus();
        if (res.authorized) {
          setPollingAuth(false);
          setUserCodeDialog(null);
          toast.success(res.mensagem || "iFood conectado com sucesso!");
        }
      } catch {
        // Silenciar erros de polling
      }
    }, 5000);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [pollingAuth]);

  function getInteg(marketplaceId: string) {
    return integsList.find((i) => i.marketplace === marketplaceId);
  }

  async function handleConnect(marketplaceId: string) {
    const meta = MARKETPLACE_META[marketplaceId];
    if (!meta) return;

    try {
      if (meta.tipo === "ifood") {
        const res = await connectIFood.mutateAsync();
        setUserCodeDialog({ code: res.user_code, url: res.verification_url });
        setPollingAuth(true);
      } else {
        const res = await connectOD.mutateAsync(marketplaceId);
        toast.success(res.mensagem || `Webhook configurado para ${meta.nome}`);
      }
    } catch {
      toast.error(`Erro ao conectar ${meta.nome}`);
    }
  }

  async function handleToggle(marketplaceId: string) {
    try {
      const res = await toggleIntegracao.mutateAsync(marketplaceId);
      toast.success(res.mensagem || `${marketplaceId} alternado`);
    } catch {
      toast.error("Erro ao alternar integração");
    }
  }

  async function handleDisconnect() {
    if (!disconnectTarget) return;
    const meta = MARKETPLACE_META[disconnectTarget];
    try {
      if (disconnectTarget === "ifood") {
        await disconnectIFood.mutateAsync();
      } else {
        await disconnectMk.mutateAsync(disconnectTarget);
      }
      toast.success(`${meta?.nome || disconnectTarget} desconectado`);
      setDisconnectTarget(null);
    } catch {
      toast.error("Erro ao desconectar");
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
            Conecte seu restaurante aos marketplaces de delivery
          </p>
        </div>

        {/* iFood Status Card (se conectado) */}
        {ifoodStatus?.configurado && ifoodStatus?.authorization_status === "authorized" && (
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
        {isLoading ? (
          <p className="text-[var(--text-muted)]">Carregando marketplaces...</p>
        ) : integsList.length === 0 ? (
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardContent className="py-8 text-center">
              <Plug className="h-12 w-12 text-[var(--text-muted)] mx-auto mb-3" />
              <p className="text-[var(--text-muted)]">
                Nenhum marketplace disponível. O administrador da plataforma precisa configurar as credenciais primeiro.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {integsList.map((integ) => {
              const meta = MARKETPLACE_META[integ.marketplace] || {
                nome: integ.marketplace,
                cor: "bg-gray-500",
                tipo: "opendelivery",
              };
              const isConnected = integ.conectado;
              const isActive = integ.ativo;

              return (
                <Card key={integ.marketplace} className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg ${meta.cor} flex items-center justify-center`}>
                          <Plug className="h-5 w-5 text-white" />
                        </div>
                        <div>
                          <CardTitle className="text-base text-[var(--text-primary)]">{meta.nome}</CardTitle>
                          <p className="text-xs text-[var(--text-muted)]">
                            {meta.tipo === "ifood" ? "API Proprietária" : meta.tipo === "proprietario" ? "API Proprietária — Em breve" : "Open Delivery (ABRASEL)"}
                          </p>
                        </div>
                      </div>
                      {isConnected && (
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className={isActive ? "bg-green-100 text-green-700 border-green-200" : ""}>
                            {isActive ? "Ativo" : "Inativo"}
                          </Badge>
                          <Switch checked={isActive} onCheckedChange={() => handleToggle(integ.marketplace)} />
                        </div>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {isConnected ? (
                      <div className="mb-3 space-y-1">
                        <p className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                          <Link2 className="h-3 w-3 text-green-500" />
                          Conectado
                          {integ.merchant_id && (
                            <span> — Merchant: <code className="bg-[var(--bg-subtle)] px-1 rounded">{integ.merchant_id}</code></span>
                          )}
                        </p>
                        {integ.authorized_at && (
                          <p className="text-xs text-[var(--text-muted)]">
                            Autorizado em: {new Date(integ.authorized_at).toLocaleDateString("pt-BR")}
                          </p>
                        )}
                      </div>
                    ) : integ.authorization_status === "pending" ? (
                      <p className="text-xs text-yellow-600 mb-3">Autorização pendente...</p>
                    ) : (
                      <p className="text-sm text-[var(--text-secondary)] mb-3">Não conectado</p>
                    )}

                    <Separator className="mb-3" />
                    <div className="flex gap-2 flex-wrap">
                      {!isConnected ? (
                        meta.tipo === "proprietario" ? (
                          <Button size="sm" disabled>
                            <Link2 className="mr-1 h-3 w-3" />
                            Em breve
                          </Button>
                        ) : (
                        <Button
                          size="sm"
                          onClick={() => handleConnect(integ.marketplace)}
                          disabled={connectIFood.isPending || connectOD.isPending}
                        >
                          <Link2 className="mr-1 h-3 w-3" />
                          {connectIFood.isPending || connectOD.isPending ? "Conectando..." : "Conectar"}
                        </Button>
                        )
                      ) : (
                        <>
                          {integ.marketplace === "ifood" && isActive && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={handleSyncCatalog}
                              disabled={syncCatalog.isPending}
                            >
                              <Upload className="mr-1 h-3 w-3" />
                              {syncCatalog.isPending ? "Sincronizando..." : "Sync Cardápio"}
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-red-500 hover:text-red-700"
                            onClick={() => setDisconnectTarget(integ.marketplace)}
                          >
                            <Unlink className="mr-1 h-3 w-3" />
                            Desconectar
                          </Button>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* userCode Dialog (iFood) */}
      <Dialog open={!!userCodeDialog} onOpenChange={() => { setUserCodeDialog(null); setPollingAuth(false); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Conectar ao iFood</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <p className="text-sm text-[var(--text-secondary)]">
              Digite o código abaixo no <strong>Portal do Parceiro iFood</strong> para autorizar este restaurante:
            </p>
            <div className="bg-[var(--bg-subtle)] rounded-lg p-6 text-center">
              <p className="text-4xl font-mono font-bold tracking-widest text-[var(--text-primary)]">
                {userCodeDialog?.code}
              </p>
            </div>
            <p className="text-xs text-[var(--text-muted)]">
              {pollingAuth && "Aguardando autorização... Verificando a cada 5 segundos."}
            </p>
            {userCodeDialog?.url && (
              <a
                href={userCodeDialog.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block text-center text-sm text-blue-500 hover:underline"
              >
                Abrir Portal do Parceiro iFood
              </a>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setUserCodeDialog(null); setPollingAuth(false); }}>
              Cancelar
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disconnect Confirmation */}
      <AlertDialog open={!!disconnectTarget} onOpenChange={() => setDisconnectTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desconectar {MARKETPLACE_META[disconnectTarget || ""]?.nome}?</AlertDialogTitle>
            <AlertDialogDescription>
              Pedidos deste marketplace não serão mais recebidos. Pedidos já existentes não serão afetados.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDisconnect} className="bg-red-600 hover:bg-red-700">
              Desconectar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AdminLayout>
  );
}
