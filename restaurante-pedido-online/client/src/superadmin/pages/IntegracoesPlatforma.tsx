import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useCredenciaisPlataforma,
  useSalvarCredencial,
  useDeletarCredencial,
  useToggleCredencial,
  useStatusIntegracoes,
} from "@/superadmin/hooks/useSuperAdminQueries";
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
import { Plug, Trash2, Store, AlertCircle } from "lucide-react";
import { toast } from "sonner";

const MARKETPLACES = [
  {
    id: "ifood",
    nome: "iFood",
    descricao: "API proprietária. Restaurantes autorizam via userCode no Portal do Parceiro.",
    cor: "bg-red-500",
  },
  {
    id: "99food",
    nome: "99Food",
    descricao: "Open Delivery (ABRASEL). Restaurantes autorizam via webhook.",
    cor: "bg-yellow-500",
  },
  {
    id: "rappi",
    nome: "Rappi",
    descricao: "API proprietária — Em breve. Integração ainda não disponível.",
    cor: "bg-orange-500",
  },
  {
    id: "keeta",
    nome: "Keeta",
    descricao: "Open Delivery (ABRASEL). Restaurantes autorizam via webhook.",
    cor: "bg-blue-500",
  },
];

interface CredencialItem {
  id: number;
  marketplace: string;
  client_id: string;
  has_secret: boolean;
  ativo: boolean;
  restaurantes_conectados: number;
  config_json: Record<string, unknown> | null;
}

interface StatusItem {
  marketplace: string;
  credencial_ativa: boolean;
  restaurantes_conectados: number;
  restaurantes_pendentes: number;
  erros_24h: number;
}

export default function IntegracoesPlatforma() {
  const { data: credenciais, isLoading } = useCredenciaisPlataforma();
  const { data: statusData } = useStatusIntegracoes();
  const salvarCredencial = useSalvarCredencial();
  const deletarCredencial = useDeletarCredencial();
  const toggleCredencial = useToggleCredencial();

  const [showSetup, setShowSetup] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");

  const credsList: CredencialItem[] = Array.isArray(credenciais) ? credenciais : [];
  const statusList: StatusItem[] = Array.isArray(statusData) ? statusData : [];

  function getCred(marketplaceId: string) {
    return credsList.find((c) => c.marketplace === marketplaceId);
  }

  function getStatus(marketplaceId: string) {
    return statusList.find((s) => s.marketplace === marketplaceId);
  }

  function handleSetup(marketplaceId: string) {
    const existing = getCred(marketplaceId);
    setClientId(existing?.client_id || "");
    setClientSecret("");
    setShowSetup(marketplaceId);
  }

  async function handleSave() {
    if (!showSetup) return;
    if (!clientId.trim() || !clientSecret.trim()) {
      toast.error("Client ID e Client Secret são obrigatórios");
      return;
    }
    try {
      await salvarCredencial.mutateAsync({
        marketplace: showSetup,
        client_id: clientId.trim(),
        client_secret: clientSecret.trim(),
      });
      toast.success(`Credencial ${showSetup} salva com sucesso`);
      setShowSetup(null);
    } catch {
      toast.error("Erro ao salvar credencial");
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    try {
      await deletarCredencial.mutateAsync(deleteTarget);
      toast.success(`Credencial ${deleteTarget} removida`);
      setDeleteTarget(null);
    } catch {
      toast.error("Erro ao remover credencial");
    }
  }

  async function handleToggle(marketplace: string) {
    try {
      const res = await toggleCredencial.mutateAsync(marketplace);
      toast.success(res.mensagem || `${marketplace} alternado`);
    } catch {
      toast.error("Erro ao alternar credencial");
    }
  }

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Integrações da Plataforma</h1>
          <p className="text-sm text-gray-400">
            Configure as credenciais de API por marketplace. Restaurantes se conectam sem inserir credenciais.
          </p>
        </div>

        {/* Status cards */}
        {statusList.length > 0 && (
          <div className="grid gap-3 md:grid-cols-4">
            {statusList.map((s) => (
              <Card key={s.marketplace} className="border-gray-800 bg-gray-900">
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-white capitalize">{s.marketplace}</span>
                    <Badge variant="outline" className={s.credencial_ativa ? "border-green-500 text-green-400" : "border-gray-600 text-gray-500"}>
                      {s.credencial_ativa ? "Ativa" : "Inativa"}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-lg font-bold text-green-400">{s.restaurantes_conectados}</p>
                      <p className="text-[10px] text-gray-500">Conectados</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-yellow-400">{s.restaurantes_pendentes}</p>
                      <p className="text-[10px] text-gray-500">Pendentes</p>
                    </div>
                    <div>
                      <p className="text-lg font-bold text-red-400">{s.erros_24h}</p>
                      <p className="text-[10px] text-gray-500">Erros 24h</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Marketplace cards */}
        <div className="grid gap-4 md:grid-cols-2">
          {MARKETPLACES.map((mp) => {
            const cred = getCred(mp.id);
            const isConfigured = !!cred;
            const isActive = cred?.ativo === true;

            return (
              <Card key={mp.id} className="border-gray-800 bg-gray-900">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-lg ${mp.cor} flex items-center justify-center`}>
                        <Plug className="h-5 w-5 text-white" />
                      </div>
                      <div>
                        <CardTitle className="text-base text-white">{mp.nome}</CardTitle>
                        <p className="text-xs text-gray-400">{mp.descricao}</p>
                      </div>
                    </div>
                    {isConfigured && (
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={isActive ? "border-green-500 text-green-400" : "border-gray-600 text-gray-500"}>
                          {isActive ? "Ativa" : "Inativa"}
                        </Badge>
                        <Switch checked={isActive} onCheckedChange={() => handleToggle(mp.id)} />
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  {isConfigured && (
                    <div className="mb-3 space-y-1">
                      <p className="text-xs text-gray-400">
                        Client ID: <code className="bg-gray-800 px-1 rounded text-gray-300">{cred.client_id}</code>
                      </p>
                      <p className="text-xs text-gray-400">
                        Secret: <code className="bg-gray-800 px-1 rounded text-gray-300">{cred.has_secret ? "••••••••" : "Não configurado"}</code>
                      </p>
                      {cred.restaurantes_conectados > 0 && (
                        <p className="text-xs text-gray-400 flex items-center gap-1">
                          <Store className="h-3 w-3" /> {cred.restaurantes_conectados} restaurante(s) conectado(s)
                        </p>
                      )}
                    </div>
                  )}
                  <Separator className="mb-3 bg-gray-800" />
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="border-gray-700 text-gray-300 hover:bg-gray-800" onClick={() => handleSetup(mp.id)}>
                      {isConfigured ? "Editar" : "Configurar"}
                    </Button>
                    {isConfigured && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
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

        {/* Info box */}
        <Card className="border-gray-800 bg-gray-900/50">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-sm text-gray-400">
                <p className="font-medium text-amber-400 mb-1">Como funciona</p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>Configure as credenciais de cada marketplace aqui (1 vez por marketplace).</li>
                  <li>Restaurantes conectam pelo painel deles sem precisar inserir credenciais.</li>
                  <li><strong>iFood:</strong> restaurante recebe userCode e digita no Portal do Parceiro.</li>
                  <li><strong>Open Delivery:</strong> restaurante configura webhook no painel do marketplace.</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Setup Dialog */}
      <Dialog open={!!showSetup} onOpenChange={() => setShowSetup(null)}>
        <DialogContent className="bg-gray-900 border-gray-800">
          <DialogHeader>
            <DialogTitle className="text-white">
              Configurar {MARKETPLACES.find((m) => m.id === showSetup)?.nome}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-sm font-medium text-gray-300">Client ID</label>
              <Input
                value={clientId}
                onChange={(e) => setClientId(e.target.value)}
                placeholder="Client ID da plataforma"
                className="bg-gray-800 border-gray-700 text-white"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-300">Client Secret</label>
              <Input
                type="password"
                value={clientSecret}
                onChange={(e) => setClientSecret(e.target.value)}
                placeholder="Client Secret da plataforma"
                className="bg-gray-800 border-gray-700 text-white"
              />
              {getCred(showSetup || "")?.has_secret && (
                <p className="text-xs text-gray-500 mt-1">Deixe em branco para manter o secret atual (não implementado — sempre insira).</p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" className="border-gray-700 text-gray-300" onClick={() => setShowSetup(null)}>Cancelar</Button>
            <Button onClick={handleSave} disabled={salvarCredencial.isPending} className="bg-amber-600 hover:bg-amber-700">
              {salvarCredencial.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent className="bg-gray-900 border-gray-800">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Remover credencial {deleteTarget}?</AlertDialogTitle>
            <AlertDialogDescription className="text-gray-400">
              Todos os restaurantes conectados a este marketplace serão desconectados automaticamente.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-gray-700 text-gray-300">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </SuperAdminLayout>
  );
}
