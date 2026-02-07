/**
 * Hooks para Pedidos - Substitui tRPC.orders
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/lib/apiClient';

export function useClientOrders(clienteId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['orders', 'client', clienteId],
    queryFn: () => api.getPedidosCliente(clienteId!),
    enabled: enabled && clienteId !== null,
    staleTime: 1000 * 30, // 30 segundos
  });
}

export function useOrderDetail(orderId: number | null, enabled = true) {
  return useQuery({
    queryKey: ['orders', 'detail', orderId],
    queryFn: () => api.getPedidoDetalhes(orderId!),
    enabled: enabled && orderId !== null,
    staleTime: 1000 * 30,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: {
      cliente_id: number;
      tipo_entrega: 'entrega' | 'retirada';
      forma_pagamento: string;
      endereco_entrega?: string;
      observacoes?: string;
      cupom_codigo?: string;
    }) => api.criarPedido(data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['orders', 'client', variables.cliente_id] });
      queryClient.invalidateQueries({ queryKey: ['cart', variables.cliente_id] });
    },
  });
}
