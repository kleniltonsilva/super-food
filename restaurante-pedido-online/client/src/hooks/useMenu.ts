/**
 * Hooks para Menu - Substitui tRPC.menu
 */
import { useQuery } from '@tanstack/react-query';
import * as api from '@/lib/apiClient';

export function useCategories() {
  return useQuery({
    queryKey: ['menu', 'categories'],
    queryFn: api.getCategorias,
    staleTime: 1000 * 60 * 5, // 5 minutos
  });
}

export function useProducts(params?: {
  categoryId?: number;
  destaque?: boolean;
  promocao?: boolean;
  busca?: string;
}) {
  return useQuery({
    queryKey: ['menu', 'products', params],
    queryFn: () => api.getProdutos({
      categoria_id: params?.categoryId,
      destaque: params?.destaque,
      promocao: params?.promocao,
      busca: params?.busca,
    }),
    enabled: params?.categoryId !== undefined || params?.destaque !== undefined || params?.promocao !== undefined,
    staleTime: 1000 * 60 * 5,
  });
}

export function useProductsByCategory(categoryId: number | null) {
  return useQuery({
    queryKey: ['menu', 'products', 'category', categoryId],
    queryFn: () => api.getProdutos({ categoria_id: categoryId! }),
    enabled: categoryId !== null,
    staleTime: 1000 * 60 * 5,
  });
}

export function useProductDetail(productId: number | null) {
  return useQuery({
    queryKey: ['menu', 'product', productId],
    queryFn: () => api.getProdutoDetalhado(productId!),
    enabled: productId !== null,
    staleTime: 1000 * 60 * 5,
  });
}
