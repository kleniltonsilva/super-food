/**
 * useQueries.ts — Hooks centrais de cache com React Query (TanStack Query v5)
 *
 * Centraliza TODAS as queries e mutations do site cliente.
 * Cada hook define seu próprio staleTime baseado na volatilidade do dado:
 *
 *   - siteInfo / categorias / combos / premios: dados estáveis → staleTime alto
 *   - produtos: muda quando restaurante edita cardápio → staleTime médio
 *   - carrinho: dado em tempo real → staleTime baixo
 *   - pedidos: atualiza conforme status muda → staleTime baixo
 *
 * Padrão de invalidação: toda mutation invalida as queries relacionadas,
 * garantindo que o cache nunca mostre dados desatualizados após uma ação.
 *
 * Uso: importar o hook diretamente na página.
 *   const { data: categorias, isLoading } = useCategorias();
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSiteInfo,
  getCategorias,
  getProdutos,
  getProdutoDetalhe,
  getSaboresDisponiveis,
  getCombos,
  getCarrinho,
  adicionarAoCarrinho,
  atualizarQuantidade,
  removerDoCarrinho,
  limparCarrinho,
  finalizarPedido,
  getMeusPedidos,
  getEnderecos,
  criarEndereco,
  getPontosFidelidade,
  getPremiosFidelidade,
  resgatarPremio,
  getPixStatusPedido,
} from "@/lib/apiClient";

// =============================================================================
// QUERY KEYS — constantes centralizadas para invalidação segura.
// Usar sempre estas chaves (nunca strings soltas) para evitar bugs de typo.
// =============================================================================

export const QUERY_KEYS = {
  siteInfo: ["siteInfo"] as const,
  categorias: ["categorias"] as const,
  produtos: (categoriaId?: number) => ["produtos", categoriaId] as const,
  todosOsProdutos: ["todosOsProdutos"] as const,
  combos: ["combos"] as const,
  carrinho: ["carrinho"] as const,
  meusPedidos: ["meusPedidos"] as const,
  enderecos: ["enderecos"] as const,
  pontosFidelidade: (clienteId: number) => ["pontosFidelidade", clienteId] as const,
  premiosFidelidade: ["premiosFidelidade"] as const,
  produtoDetalhe: (id: number) => ["produtoDetalhe", id] as const,
  saboresDisponiveis: (id: number) => ["saboresDisponiveis", id] as const,
  pixStatus: (pedidoId: number) => ["pixStatus", pedidoId] as const,
} as const;

// =============================================================================
// QUERIES — hooks de leitura com cache inteligente
// =============================================================================

/**
 * Informações do restaurante (nome, logo, cores, horário, status, etc).
 * staleTime: 2 min — status aberto/fechado precisa refletir rápido.
 * WebSocket invalida instantaneamente via evento config_atualizada.
 * refetchInterval: 5 min — fallback caso WebSocket desconecte.
 */
export function useSiteInfo() {
  return useQuery({
    queryKey: QUERY_KEYS.siteInfo,
    queryFn: getSiteInfo,
    staleTime: 2 * 60 * 1000,      // 2 min
    gcTime: 10 * 60 * 1000,        // 10 min
    refetchInterval: 5 * 60 * 1000, // 5 min polling fallback
  });
}

/**
 * Lista de categorias do cardápio.
 * staleTime: 15 min — muda quando restaurante edita cardápio (raro durante operação).
 */
export function useCategorias() {
  return useQuery({
    queryKey: QUERY_KEYS.categorias,
    queryFn: getCategorias,
    staleTime: 15 * 60 * 1000,     // 15 min
  });
}

/**
 * Produtos filtrados por categoria.
 * staleTime: 5 min — pode mudar quando restaurante desativa produto.
 * placeholderData: keepPreviousData → ao trocar de categoria, mantém dados
 * anteriores visíveis enquanto carrega a nova categoria (evita flash branco).
 */
export function useProdutos(categoriaId?: number | null) {
  return useQuery({
    queryKey: QUERY_KEYS.produtos(categoriaId ?? undefined),
    queryFn: () => getProdutos(categoriaId ?? undefined),
    enabled: !!categoriaId,         // Só executa se tiver categoria selecionada
    staleTime: 5 * 60 * 1000,      // 5 min
    placeholderData: (prev: any) => prev,  // Mantém dados anteriores enquanto carrega
  });
}

/**
 * Todos os produtos do cardápio (sem filtro de categoria).
 * staleTime: 5 min — usado na Home para exibir seções por categoria.
 */
export function useTodosProdutos() {
  return useQuery({
    queryKey: QUERY_KEYS.todosOsProdutos,
    queryFn: () => getProdutos(),
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Combos/ofertas do restaurante.
 * staleTime: 15 min — similar a categorias, muda raramente.
 */
export function useCombos() {
  return useQuery({
    queryKey: QUERY_KEYS.combos,
    queryFn: getCombos,
    staleTime: 15 * 60 * 1000,     // 15 min
  });
}

/**
 * Carrinho do cliente (anônimo ou logado).
 * staleTime: 30s — dado quase em tempo real, precisa estar fresco.
 * refetchOnMount: always → sempre busca ao montar componente.
 */
export function useCarrinho() {
  return useQuery({
    queryKey: QUERY_KEYS.carrinho,
    queryFn: getCarrinho,
    staleTime: 30 * 1000,          // 30 segundos
    refetchOnMount: "always",      // Sempre re-busca ao montar
  });
}

/**
 * Pedidos do cliente logado.
 * staleTime: 1 min — status pode mudar frequentemente.
 * enabled: precisa de token para funcionar (verificado pelo interceptor).
 */
export function useMeusPedidos(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEYS.meusPedidos,
    queryFn: getMeusPedidos,
    staleTime: 60 * 1000,          // 1 min
    enabled,
  });
}

/**
 * Endereços salvos do cliente logado.
 * staleTime: 5 min — muda apenas quando cliente edita endereços.
 */
export function useEnderecos(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEYS.enderecos,
    queryFn: getEnderecos,
    staleTime: 5 * 60 * 1000,      // 5 min
    enabled,
  });
}

/**
 * Pontos de fidelidade do cliente.
 * staleTime: 5 min — muda após pedidos ou resgates.
 */
export function usePontosFidelidade(clienteId: number | undefined) {
  return useQuery({
    queryKey: QUERY_KEYS.pontosFidelidade(clienteId!),
    queryFn: () => getPontosFidelidade(clienteId!),
    enabled: !!clienteId,
    staleTime: 5 * 60 * 1000,      // 5 min
  });
}

/**
 * Prêmios disponíveis no programa de fidelidade.
 * staleTime: 15 min — muda quando restaurante edita prêmios.
 */
export function usePremiosFidelidade(enabled = true) {
  return useQuery({
    queryKey: QUERY_KEYS.premiosFidelidade,
    queryFn: getPremiosFidelidade,
    staleTime: 15 * 60 * 1000,     // 15 min
    enabled,
  });
}

/**
 * Detalhes completos de um produto (com variações agrupadas + ingredientes).
 * staleTime: 5 min — usado pelo PizzaBuilder e ProductDetail.
 */
export function useProdutoDetalhe(produtoId: number | null) {
  return useQuery({
    queryKey: QUERY_KEYS.produtoDetalhe(produtoId!),
    queryFn: () => getProdutoDetalhe(produtoId!),
    enabled: !!produtoId,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Sabores disponíveis (produtos da mesma categoria) para montagem de pizza.
 * staleTime: 5 min — muda quando restaurante edita cardápio.
 */
export function useSaboresDisponiveis(produtoId: number | null) {
  return useQuery({
    queryKey: QUERY_KEYS.saboresDisponiveis(produtoId!),
    queryFn: () => getSaboresDisponiveis(produtoId!),
    enabled: !!produtoId,
    staleTime: 5 * 60 * 1000,
  });
}

// =============================================================================
// MUTATIONS — ações que modificam dados + invalidam cache automaticamente
// =============================================================================

/**
 * Adicionar item ao carrinho.
 * Após sucesso, invalida cache do carrinho para refletir o novo item.
 */
export function useAdicionarCarrinho() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (item: {
      produto_id: number;
      quantidade: number;
      observacao?: string;
      variacoes?: { variacao_id: number }[];
    }) => adicionarAoCarrinho(item),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
    },
  });
}

/**
 * Atualizar quantidade de um item no carrinho.
 */
export function useAtualizarQuantidade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ itemIndex, quantidade }: { itemIndex: number; quantidade: number }) =>
      atualizarQuantidade(itemIndex, quantidade),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
    },
  });
}

/**
 * Remover item do carrinho.
 */
export function useRemoverCarrinho() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (itemIndex: number) => removerDoCarrinho(itemIndex),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
    },
  });
}

/**
 * Limpar todo o carrinho.
 */
export function useLimparCarrinho() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: limparCarrinho,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
    },
  });
}

/**
 * Finalizar pedido (checkout).
 * Invalida carrinho (que fica vazio) e pedidos (novo pedido aparece).
 */
export function useFinalizarPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      tipo_entrega: string;
      forma_pagamento: string;
      cliente_nome?: string;
      cliente_telefone?: string;
      endereco_entrega?: string;
      latitude?: number;
      longitude?: number;
      troco_para?: number;
      observacoes?: string;
      cupom_desconto?: string;
      valor_desconto?: number;
    }) => finalizarPedido(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.meusPedidos });
    },
  });
}

/**
 * Criar novo endereço.
 * Invalida cache de endereços para aparecer na lista.
 */
export function useCriarEndereco() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: {
      apelido?: string;
      cep?: string;
      endereco_completo: string;
      numero?: string;
      complemento?: string;
      bairro?: string;
      cidade?: string;
      estado?: string;
      referencia?: string;
      latitude?: number;
      longitude?: number;
      padrao?: boolean;
    }) => criarEndereco(dados),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.enderecos });
    },
  });
}

/**
 * Resgatar prêmio de fidelidade.
 * Invalida pontos (reduz saldo) e prêmios (pode desativar se esgotou).
 */
export function useResgatarPremio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ clienteId, premioId }: { clienteId: number; premioId: number }) =>
      resgatarPremio(clienteId, premioId),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: QUERY_KEYS.pontosFidelidade(variables.clienteId) });
      qc.invalidateQueries({ queryKey: QUERY_KEYS.premiosFidelidade });
    },
  });
}

/**
 * Polling do status de pagamento Pix.
 * refetchInterval: 3s quando ativo, para detectar pagamento rápido.
 */
export function usePixStatusPedido(pedidoId: number | null) {
  return useQuery({
    queryKey: QUERY_KEYS.pixStatus(pedidoId || 0),
    queryFn: () => getPixStatusPedido(pedidoId!),
    enabled: !!pedidoId,
    refetchInterval: 3000,
    staleTime: 0,
  });
}
