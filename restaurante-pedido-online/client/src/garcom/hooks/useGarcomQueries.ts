import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/garcom/lib/garcomApiClient";

export const GARCOM_QUERY_KEYS = {
  mesas: ["garcom", "mesas"] as const,
  sessao: ["garcom", "sessao"] as const,
  cardapio: ["garcom", "cardapio"] as const,
  itensEsgotados: ["garcom", "itens-esgotados"] as const,
};

export function useMesas() {
  return useQuery({
    queryKey: GARCOM_QUERY_KEYS.mesas,
    queryFn: api.getMesas,
    staleTime: 10_000,
    refetchInterval: 15_000,
  });
}

export function useAbrirMesa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mesaId, ...payload }: { mesaId: number; qtd_pessoas: number; alergia?: string; tags?: string[]; notas?: string }) =>
      api.abrirMesa(mesaId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas }),
  });
}

export function useTransferirMesa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ mesaId, mesaDestinoId }: { mesaId: number; mesaDestinoId: number }) =>
      api.transferirMesa(mesaId, mesaDestinoId),
    onSuccess: () => qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas }),
  });
}

export function useSessao(sessaoId: number | null) {
  return useQuery({
    queryKey: [...GARCOM_QUERY_KEYS.sessao, sessaoId],
    queryFn: () => api.getSessao(sessaoId!),
    enabled: !!sessaoId,
    staleTime: 5_000,
    refetchInterval: 10_000,
  });
}

export function useCriarPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessaoId, ...payload }: {
      sessaoId: number;
      itens: Array<{ item_cardapio_id: number; qty: number; obs?: string; course?: string }>;
      observacoes?: string;
    }) => api.criarPedidoSessao(sessaoId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
    },
  });
}

export function useSolicitarFechamento() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.solicitarFechamento,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
    },
  });
}

export function useRepetirRodada() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.repetirRodada,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
    },
  });
}

export function useCancelarItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ pedidoId, itemId }: { pedidoId: number; itemId: number }) =>
      api.cancelarItem(pedidoId, itemId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
    },
  });
}

export function useCardapio() {
  return useQuery({
    queryKey: GARCOM_QUERY_KEYS.cardapio,
    queryFn: api.getCardapio,
    staleTime: 60_000,
  });
}

export function useItensEsgotados() {
  return useQuery({
    queryKey: GARCOM_QUERY_KEYS.itensEsgotados,
    queryFn: api.getItensEsgotados,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}

export function useMarcarEsgotado() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.marcarEsgotado,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.itensEsgotados });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.cardapio });
    },
  });
}

export function useDesmarcarEsgotado() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.desmarcarEsgotado,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.itensEsgotados });
      qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.cardapio });
    },
  });
}
