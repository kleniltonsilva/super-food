import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/kds/lib/kdsApiClient";

export const KDS_QUERY_KEYS = {
  pedidos: ["kds", "pedidos"] as const,
  config: ["kds", "config"] as const,
};

export function usePedidosKds(statusFilter?: string) {
  return useQuery({
    queryKey: [...KDS_QUERY_KEYS.pedidos, statusFilter],
    queryFn: () => api.getPedidosKds(statusFilter),
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useAtualizarStatusKds() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.atualizarStatusKds(id, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos }),
  });
}

export function useAssumirPedidoKds() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.assumirPedidoKds,
    onSuccess: () => qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos }),
  });
}

export function useRefazerPedidoKds() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.refazerPedidoKds,
    onSuccess: () => qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos }),
  });
}

export function useConfigKds() {
  return useQuery({
    queryKey: KDS_QUERY_KEYS.config,
    queryFn: api.getConfigKds,
    staleTime: 60_000,
  });
}
