import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { usePlanos, useAtualizarPlano } from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import { CreditCard, Edit, Users, Loader2 } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";

interface Plano {
  nome: string;
  valor: number;
  motoboys: number;
  descricao: string;
  total_assinantes: number;
}

const CORES_PLANOS: Record<string, string> = {
  "Básico": "border-blue-500/30 bg-blue-500/5",
  "Essencial": "border-green-500/30 bg-green-500/5",
  "Avançado": "border-amber-500/30 bg-amber-500/5",
  "Premium": "border-purple-500/30 bg-purple-500/5",
};

const CORES_BADGE: Record<string, string> = {
  "Básico": "bg-blue-500",
  "Essencial": "bg-green-500",
  "Avançado": "bg-amber-500",
  "Premium": "bg-purple-500",
};

export default function GerenciarPlanos() {
  const { data: planos, isLoading } = usePlanos();
  const atualizarPlano = useAtualizarPlano();
  const [editPlano, setEditPlano] = useState<Plano | null>(null);
  const [editForm, setEditForm] = useState({ valor: "", motoboys: "", descricao: "" });

  function openEdit(plano: Plano) {
    setEditForm({
      valor: plano.valor.toString(),
      motoboys: plano.motoboys.toString(),
      descricao: plano.descricao,
    });
    setEditPlano(plano);
  }

  function handleSave() {
    if (!editPlano) return;

    const payload: { valor?: number; motoboys?: number; descricao?: string } = {};
    const novoValor = parseFloat(editForm.valor);
    const novoMotoboys = parseInt(editForm.motoboys);

    if (!isNaN(novoValor) && novoValor !== editPlano.valor) payload.valor = novoValor;
    if (!isNaN(novoMotoboys) && novoMotoboys !== editPlano.motoboys) payload.motoboys = novoMotoboys;
    if (editForm.descricao !== editPlano.descricao) payload.descricao = editForm.descricao;

    if (Object.keys(payload).length === 0) {
      toast.info("Nenhuma alteração detectada");
      setEditPlano(null);
      return;
    }

    atualizarPlano.mutate(
      { nome: editPlano.nome, payload },
      {
        onSuccess: (data) => {
          toast.success(data.mensagem || "Plano atualizado!");
          if (data.restaurantes_atualizados > 0) {
            toast.info(`${data.restaurantes_atualizados} restaurante(s) atualizado(s)`);
          }
          setEditPlano(null);
        },
        onError: () => toast.error("Erro ao atualizar plano"),
      }
    );
  }

  const lista: Plano[] = planos || [];
  const receitaTotal = lista.reduce((acc, p) => acc + p.valor * p.total_assinantes, 0);
  const totalAssinantes = lista.reduce((acc, p) => acc + p.total_assinantes, 0);

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <h2 className="text-2xl font-bold text-[var(--sa-text-primary)]">Gerenciar Planos</h2>

        {/* Resumo */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-5">
            <p className="text-sm text-[var(--sa-text-muted)]">Total Assinantes</p>
            <p className="mt-1 text-2xl font-bold text-[var(--sa-text-primary)]">{totalAssinantes}</p>
          </div>
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-5">
            <p className="text-sm text-[var(--sa-text-muted)]">Receita Mensal</p>
            <p className="mt-1 text-2xl font-bold text-green-400">
              {receitaTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-5">
            <p className="text-sm text-[var(--sa-text-muted)]">Receita Anual Projetada</p>
            <p className="mt-1 text-2xl font-bold text-amber-400">
              {(receitaTotal * 12).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
        </div>

        {/* Cards de planos */}
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Spinner className="h-6 w-6 text-amber-500" />
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {lista.map((plano) => (
              <div
                key={plano.nome}
                className={`rounded-xl border p-6 transition-all ${CORES_PLANOS[plano.nome] || "border-[var(--sa-border)] bg-[var(--sa-bg-surface)]"}`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`h-3 w-3 rounded-full ${CORES_BADGE[plano.nome] || "bg-gray-500"}`} />
                    <h3 className="text-lg font-bold text-[var(--sa-text-primary)]">{plano.nome}</h3>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
                    onClick={() => openEdit(plano)}
                  >
                    <Edit className="h-4 w-4" />
                  </Button>
                </div>

                <p className="mt-3 text-3xl font-bold text-[var(--sa-text-primary)]">
                  R$ {plano.valor.toFixed(2)}
                  <span className="text-sm font-normal text-[var(--sa-text-muted)]">/mês</span>
                </p>

                <div className="mt-4 space-y-2">
                  <div className="flex items-center gap-2 text-sm text-[var(--sa-text-secondary)]">
                    <Users className="h-4 w-4 text-[var(--sa-text-dimmed)]" />
                    <span>{plano.motoboys === 999 ? "Ilimitados" : `Até ${plano.motoboys}`} motoboys</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-[var(--sa-text-secondary)]">
                    <CreditCard className="h-4 w-4 text-[var(--sa-text-dimmed)]" />
                    <span>{plano.total_assinantes} assinante(s)</span>
                  </div>
                </div>

                <p className="mt-3 text-xs text-[var(--sa-text-dimmed)]">{plano.descricao}</p>

                {plano.total_assinantes > 0 && (
                  <p className="mt-3 text-sm font-medium text-green-400">
                    Receita: {(plano.valor * plano.total_assinantes).toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}/mês
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal Editar Plano */}
      <Dialog open={!!editPlano} onOpenChange={(open) => !open && setEditPlano(null)}>
        <DialogContent className="border-[var(--sa-border)] bg-[var(--sa-bg-surface)] text-[var(--sa-text-primary)] sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Editar Plano: {editPlano?.nome}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                Valor Mensal (R$)
                <InfoTooltip text="Valor cobrado mensalmente do restaurante. Ao alterar, todos os restaurantes com este plano serão atualizados." />
              </label>
              <Input
                type="number"
                step="0.01"
                value={editForm.valor}
                onChange={(e) => setEditForm({ ...editForm, valor: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                Limite de Motoboys
                <InfoTooltip text="Quantidade máxima de motoboys ativos que o restaurante pode ter. 999 = ilimitados." />
              </label>
              <Input
                type="number"
                value={editForm.motoboys}
                onChange={(e) => setEditForm({ ...editForm, motoboys: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                Descrição
                <InfoTooltip text="Descrição exibida na seleção de plano ao criar novo restaurante." />
              </label>
              <Input
                value={editForm.descricao}
                onChange={(e) => setEditForm({ ...editForm, descricao: e.target.value })}
                className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]"
              />
            </div>
            <p className="text-xs text-yellow-400">
              Alterar valores afetará todos os restaurantes com este plano.
            </p>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setEditPlano(null)} className="text-[var(--sa-text-muted)]">
              Cancelar
            </Button>
            <Button
              className="bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)] text-[var(--sa-text-primary)]"
              onClick={handleSave}
              disabled={atualizarPlano.isPending}
            >
              {atualizarPlano.isPending ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Salvando...</>
              ) : (
                "Salvar"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SuperAdminLayout>
  );
}
