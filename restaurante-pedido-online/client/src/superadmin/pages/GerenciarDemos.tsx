import { useState } from "react";
import { useLocation } from "wouter";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useDemos, useResetDemo } from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ExternalLink, Pencil, RotateCcw, ShoppingBag, Layers } from "lucide-react";
import { toast } from "sonner";

const TIPO_EMOJIS: Record<string, string> = {
  pizzaria: "🍕",
  hamburgueria: "🍔",
  japonesa: "🍣",
  acaiteria: "🍇",
  padaria: "🥐",
  marmitaria: "🍱",
  doceria: "🧁",
  churrascaria: "🥩",
  restaurante: "🍽️",
  geral: "🍽️",
};

export default function GerenciarDemos() {
  const [, navigate] = useLocation();
  const { data: demos = [], isLoading } = useDemos();
  const resetMutation = useResetDemo();
  const [confirmResetId, setConfirmResetId] = useState<number | null>(null);

  function handleReset(id: number) {
    if (confirmResetId === id) {
      resetMutation.mutate(id, {
        onSuccess: (data) => {
          toast.success(`Demo resetado: ${data.pedidos_removidos} pedidos, ${data.clientes_removidos} clientes removidos`);
          setConfirmResetId(null);
        },
        onError: () => toast.error("Erro ao resetar demo"),
      });
    } else {
      setConfirmResetId(id);
      setTimeout(() => setConfirmResetId(null), 5000);
    }
  }

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--sa-text-primary)]">Restaurantes Demo</h1>
          <p className="text-sm text-[var(--sa-text-muted)] mt-1">
            Gerencie os 8 restaurantes de demonstração. Edite fotos, cardápio e configurações.
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <span className="text-[var(--sa-text-muted)]">Carregando demos...</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {demos.map((demo: any) => {
              const emoji = TIPO_EMOJIS[demo.tipo_restaurante] || "🍽️";
              return (
                <Card
                  key={demo.id}
                  className="overflow-hidden border border-[var(--sa-border)] bg-[var(--sa-bg-surface)]"
                >
                  {/* Thumbnail/banner */}
                  <div
                    className="h-28 flex items-center justify-center text-5xl"
                    style={{
                      background: demo.banner_principal_url
                        ? `url(${demo.banner_principal_url}) center/cover`
                        : `linear-gradient(135deg, ${demo.tema_cor_primaria}, ${demo.tema_cor_secundaria})`,
                    }}
                  >
                    {!demo.banner_principal_url && emoji}
                  </div>

                  <div className="p-4 space-y-3">
                    {/* Nome + tipo */}
                    <div>
                      <h3 className="font-bold text-[var(--sa-text-primary)] truncate">
                        {emoji} {demo.nome_fantasia}
                      </h3>
                      <p className="text-xs text-[var(--sa-text-muted)] capitalize">
                        {demo.tipo_restaurante} | {demo.codigo_acesso}
                      </p>
                    </div>

                    {/* Stats */}
                    <div className="flex gap-3 text-xs text-[var(--sa-text-muted)]">
                      <span className="flex items-center gap-1">
                        <ShoppingBag className="w-3 h-3" />
                        {demo.total_produtos} produtos
                      </span>
                      <span className="flex items-center gap-1">
                        <Layers className="w-3 h-3" />
                        {demo.total_categorias} cat.
                      </span>
                    </div>

                    {/* Badge status */}
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        demo.ativo
                          ? "bg-green-500/10 text-green-400"
                          : "bg-red-500/10 text-red-400"
                      }`}>
                        {demo.ativo ? "Ativo" : "Inativo"}
                      </span>
                      {demo.pedidos_recentes_24h > 0 && (
                        <span className="inline-flex items-center rounded-full bg-blue-500/10 text-blue-400 px-2 py-0.5 text-xs font-medium">
                          {demo.pedidos_recentes_24h} pedidos 24h
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        className="flex-1 bg-[var(--sa-accent)] text-white hover:bg-[var(--sa-accent)]/90"
                        onClick={() => navigate(`/demos/${demo.id}`)}
                      >
                        <Pencil className="w-3 h-3 mr-1" />
                        Editar
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-[var(--sa-border)] text-[var(--sa-text-muted)]"
                        onClick={() => window.open(`/cliente/${demo.codigo_acesso}`, "_blank")}
                      >
                        <ExternalLink className="w-3 h-3" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className={`border-[var(--sa-border)] ${
                          confirmResetId === demo.id
                            ? "text-red-400 border-red-500/50"
                            : "text-[var(--sa-text-muted)]"
                        }`}
                        onClick={() => handleReset(demo.id)}
                        disabled={resetMutation.isPending}
                      >
                        <RotateCcw className="w-3 h-3" />
                      </Button>
                    </div>
                    {confirmResetId === demo.id && (
                      <p className="text-xs text-red-400">Clique novamente para confirmar reset</p>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {!isLoading && demos.length === 0 && (
          <div className="text-center py-12 text-[var(--sa-text-muted)]">
            Nenhum restaurante demo encontrado. Execute o seed para criar os demos.
          </div>
        )}
      </div>
    </SuperAdminLayout>
  );
}
