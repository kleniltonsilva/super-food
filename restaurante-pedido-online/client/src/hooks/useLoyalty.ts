/**
 * Hooks para Fidelidade - Substitui tRPC.loyalty
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/lib/apiClient';

export function useLoyaltyPoints(clienteId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['loyalty', 'points', clienteId],
    queryFn: () => api.getPontosFidelidade(clienteId!),
    enabled: enabled && clienteId !== null,
    staleTime: 1000 * 60, // 1 minuto
  });
}

export function useLoyaltyRewards() {
  return useQuery({
    queryKey: ['loyalty', 'rewards'],
    queryFn: api.getPremiosFidelidade,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
}

export function useRedeemReward() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ clienteId, premioId }: { clienteId: number; premioId: number }) =>
      api.resgatarPremio(clienteId, premioId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['loyalty', 'points', variables.clienteId] });
    },
  });
}

export function usePromotions() {
  return useQuery({
    queryKey: ['promotions'],
    queryFn: api.getPromocoes,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
}

export function useValidateCoupon() {
  return useMutation({
    mutationFn: ({ codigo, valor }: { codigo: string; valor: number }) =>
      api.validarCupom(codigo, valor),
  });
}
