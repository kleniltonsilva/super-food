/**
 * Hooks para Carrinho - Substitui tRPC.cart
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/lib/apiClient';

export function useCartItems(clienteId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['cart', clienteId],
    queryFn: () => api.getCarrinho(clienteId!),
    enabled: enabled && clienteId !== null,
    staleTime: 1000 * 30, // 30 segundos
  });
}

export function useAddToCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      cliente_id: number;
      produto_id: number;
      quantidade: number;
      variacoes?: number[];
      observacoes?: string;
    }) => api.adicionarAoCarrinho(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['cart', variables.cliente_id] });
    },
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, quantidade }: { itemId: number; quantidade: number }) =>
      api.atualizarItemCarrinho(itemId, quantidade),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useRemoveFromCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: number) => api.removerItemCarrinho(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cart'] });
    },
  });
}

export function useClearCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (clienteId: number) => api.limparCarrinho(clienteId),
    onSuccess: (_, clienteId) => {
      queryClient.invalidateQueries({ queryKey: ['cart', clienteId] });
    },
  });
}
