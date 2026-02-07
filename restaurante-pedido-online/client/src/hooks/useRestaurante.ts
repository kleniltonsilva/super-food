/**
 * Hooks para Restaurante e Delivery
 */
import { useQuery, useMutation } from '@tanstack/react-query';
import * as api from '@/lib/apiClient';

export function useSiteInfo() {
  return useQuery({
    queryKey: ['site', 'info'],
    queryFn: api.getSiteInfo,
    staleTime: 1000 * 60 * 10, // 10 minutos
  });
}

export function useBairros() {
  return useQuery({
    queryKey: ['delivery', 'bairros'],
    queryFn: api.getBairros,
    staleTime: 1000 * 60 * 10, // 10 minutos
  });
}

export function useBairroPorNome(nome: string | null, enabled = true) {
  return useQuery({
    queryKey: ['delivery', 'bairro', nome],
    queryFn: () => api.getBairroPorNome(nome!),
    enabled: enabled && nome !== null && nome.length > 0,
    staleTime: 1000 * 60 * 5,
  });
}

export function useValidateDelivery() {
  return useMutation({
    mutationFn: (data: {
      endereco_texto?: string;
      latitude?: number;
      longitude?: number;
    }) => api.validarEntrega(data),
  });
}

export function useAddressAutocomplete(query: string, enabled = true) {
  return useQuery({
    queryKey: ['delivery', 'autocomplete', query],
    queryFn: () => api.autocompleteEndereco(query),
    enabled: enabled && query.length >= 3,
    staleTime: 1000 * 60, // 1 minuto
  });
}
