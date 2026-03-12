import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useInadimplentes,
  useAtualizarStatusRestaurante,
} from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";
import { AlertTriangle, Play, XCircle, RefreshCw } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";
import { cn } from "@/lib/utils";

interface Inadimplente {
  id: number;
  nome_fantasia: string;
  email: string;
  telefone: string;
  plano: string;
  valor_plano: number;
  status: string | null;
  data_vencimento: string | null;
  dias_vencido: number;
}

function formatDate(dateStr: string | null) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleDateString("pt-BR");
}

export default function Inadimplentes() {
  const [diasTolerancia, setDiasTolerancia] = useState(0);
  const { data: inadimplentes, isLoading } = useInadimplentes(diasTolerancia);
  const atualizarStatus = useAtualizarStatusRestaurante();

  function handleRenovar(id: number) {
    atualizarStatus.mutate(
      { id, status: "ativo" },
      {
        onSuccess: () => toast.success("Assinatura renovada por +30 dias!"),
        onError: () => toast.error("Erro ao renovar"),
      }
    );
  }

  function handleSuspender(id: number) {
    atualizarStatus.mutate(
      { id, status: "suspenso" },
      {
        onSuccess: () => toast.success("Restaurante suspenso"),
        onError: () => toast.error("Erro ao suspender"),
      }
    );
  }

  function handleCancelar(id: number) {
    atualizarStatus.mutate(
      { id, status: "cancelado" },
      {
        onSuccess: () => toast.success("Restaurante cancelado"),
        onError: () => toast.error("Erro ao cancelar"),
      }
    );
  }

  const lista: Inadimplente[] = inadimplentes || [];
  const debitTotal = lista.reduce((acc, r) => acc + r.valor_plano, 0);

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h2 className="text-2xl font-bold text-white">Inadimplentes</h2>
          <div className="flex items-center gap-2">
            <label className="text-sm text-gray-400 whitespace-nowrap flex items-center gap-1.5">
              Tolerância (dias):
              <InfoTooltip text="Dias de carência após o vencimento antes de listar como inadimplente. 0 = mostra todos vencidos imediatamente." />
            </label>
            <Input
              type="number"
              min={0}
              value={diasTolerancia}
              onChange={(e) => setDiasTolerancia(parseInt(e.target.value) || 0)}
              className="w-20 border-gray-700 bg-gray-800 text-white"
            />
          </div>
        </div>

        {/* Resumo */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-5">
            <p className="text-sm text-gray-400">Total Inadimplentes</p>
            <p className="mt-1 text-2xl font-bold text-red-400">{lista.length}</p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            <p className="text-sm text-gray-400">Débito Total Mensal</p>
            <p className="mt-1 text-2xl font-bold text-amber-400">
              {debitTotal.toLocaleString("pt-BR", { style: "currency", currency: "BRL" })}
            </p>
          </div>
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            <p className="text-sm text-gray-400">Maior Atraso</p>
            <p className="mt-1 text-2xl font-bold text-white">
              {lista.length > 0 ? `${Math.max(...lista.map((r) => r.dias_vencido))} dias` : "-"}
            </p>
          </div>
        </div>

        {/* Tabela */}
        {isLoading ? (
          <div className="flex h-40 items-center justify-center">
            <Spinner className="h-6 w-6 text-amber-500" />
          </div>
        ) : lista.length === 0 ? (
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-10 text-center">
            <AlertTriangle className="mx-auto h-12 w-12 text-green-500" />
            <p className="mt-3 text-gray-400">Nenhum inadimplente encontrado</p>
            <p className="text-sm text-gray-500">Todos os restaurantes estão em dia!</p>
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-gray-800">
            <Table>
              <TableHeader>
                <TableRow className="border-gray-800 hover:bg-transparent">
                  <TableHead className="text-gray-400">Restaurante</TableHead>
                  <TableHead className="text-gray-400">Plano</TableHead>
                  <TableHead className="text-gray-400">Status</TableHead>
                  <TableHead className="text-gray-400">Vencimento</TableHead>
                  <TableHead className="text-gray-400">Dias Vencido</TableHead>
                  <TableHead className="text-gray-400 text-right">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {lista.map((r) => (
                  <TableRow key={r.id} className="border-gray-800 hover:bg-gray-800/50">
                    <TableCell>
                      <div>
                        <p className="font-medium text-white">{r.nome_fantasia}</p>
                        <p className="text-xs text-gray-500">{r.email}</p>
                        <p className="text-xs text-gray-500">{r.telefone}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="border-gray-600 text-gray-300">
                        {r.plano}
                      </Badge>
                      <p className="mt-0.5 text-xs text-gray-500">
                        R$ {r.valor_plano.toFixed(2)}/mês
                      </p>
                    </TableCell>
                    <TableCell>
                      <span className={cn(
                        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                        r.status === "suspenso"
                          ? "bg-yellow-500/20 text-yellow-400"
                          : "bg-green-500/20 text-green-400"
                      )}>
                        {r.status || "ativo"}
                      </span>
                    </TableCell>
                    <TableCell className="text-gray-300">{formatDate(r.data_vencimento)}</TableCell>
                    <TableCell>
                      <span className={cn(
                        "font-semibold",
                        r.dias_vencido > 30 ? "text-red-400" : r.dias_vencido > 7 ? "text-orange-400" : "text-yellow-400"
                      )}>
                        {r.dias_vencido} dias
                      </span>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-green-400 hover:text-green-300"
                          onClick={() => handleRenovar(r.id)}
                          disabled={atualizarStatus.isPending}
                        >
                          <RefreshCw className="mr-1 h-4 w-4" />
                          <span className="hidden sm:inline">Renovar</span>
                        </Button>
                        {r.status !== "suspenso" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-yellow-400 hover:text-yellow-300"
                            onClick={() => handleSuspender(r.id)}
                            disabled={atualizarStatus.isPending}
                          >
                            <Play className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-red-400 hover:text-red-300"
                          onClick={() => handleCancelar(r.id)}
                          disabled={atualizarStatus.isPending}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </div>
    </SuperAdminLayout>
  );
}
