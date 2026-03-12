import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/admin/lib/adminApiClient";

// ─── Query Keys ────────────────────────────────────────
export const ADMIN_QUERY_KEYS = {
  dashboard: ["admin", "dashboard"] as const,
  dashboardGrafico: ["admin", "dashboard", "grafico"] as const,
  pedidos: ["admin", "pedidos"] as const,
  pedido: (id: number) => ["admin", "pedidos", id] as const,
  categorias: ["admin", "categorias"] as const,
  produtos: ["admin", "produtos"] as const,
  produto: (id: number) => ["admin", "produtos", id] as const,
  variacoes: (produtoId: number) => ["admin", "variacoes", produtoId] as const,
  combos: ["admin", "combos"] as const,
  motoboys: ["admin", "motoboys"] as const,
  rankingMotoboys: ["admin", "motoboys", "ranking"] as const,
  solicitacoesMotoboys: ["admin", "motoboys", "solicitacoes"] as const,
  caixaAtual: ["admin", "caixa", "atual"] as const,
  historicoCaixa: ["admin", "caixa", "historico"] as const,
  config: ["admin", "config"] as const,
  configSite: ["admin", "config", "site"] as const,
  bairros: ["admin", "bairros"] as const,
  promocoes: ["admin", "promocoes"] as const,
  premios: ["admin", "fidelidade", "premios"] as const,
  relatorioVendas: ["admin", "relatorios", "vendas"] as const,
  relatorioMotoboys: ["admin", "relatorios", "motoboys"] as const,
  relatorioProdutos: ["admin", "relatorios", "produtos"] as const,
  entregasAtivas: ["admin", "entregas", "ativas"] as const,
  diagnosticoTempo: ["admin", "entregas", "diagnostico-tempo"] as const,
};

// ─── Dashboard ─────────────────────────────────────────
export function useDashboard() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.dashboard,
    queryFn: api.getDashboard,
    staleTime: 30 * 1000,
  });
}

export function useDashboardGrafico(periodo?: string) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.dashboardGrafico, periodo],
    queryFn: () => api.getDashboardGrafico(periodo),
    staleTime: 30 * 1000,
  });
}

// ─── Pedidos ───────────────────────────────────────────
export function usePedidos(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.pedidos, params],
    queryFn: () => api.getPedidos(params),
    staleTime: 15 * 1000,
  });
}

export function usePedido(id: number) {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.pedido(id),
    queryFn: () => api.getPedido(id),
    staleTime: 15 * 1000,
    enabled: !!id,
  });
}

export function useCriarPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarPedido,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
    },
  });
}

export function useAtualizarStatusPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      api.atualizarStatusPedido(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
    },
  });
}

export function useDespacharPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, motoboy_id }: { id: number; motoboy_id: number }) =>
      api.despacharPedido(id, motoboy_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
    },
  });
}

export function useCancelarPedido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, senha }: { id: number; senha?: string }) =>
      api.cancelarPedido(id, senha),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual });
    },
  });
}

// ─── Categorias ────────────────────────────────────────
export function useCategorias() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.categorias,
    queryFn: api.getCategorias,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCriarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.criarCategoria(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.categorias }),
  });
}

export function useAtualizarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarCategoria(id, payload as { nome?: string; ordem?: number }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.categorias }),
  });
}

export function useDeletarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarCategoria,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.categorias }),
  });
}

export function useReordenarCategorias() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.reordenarCategorias,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.categorias }),
  });
}

// ─── Produtos ──────────────────────────────────────────
export function useProdutos(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.produtos, params],
    queryFn: () => api.getProdutos(params),
    staleTime: 2 * 60 * 1000,
    placeholderData: (prev: unknown) => prev,
  });
}

export function useProduto(id: number) {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.produto(id),
    queryFn: () => api.getProduto(id),
    staleTime: 2 * 60 * 1000,
    enabled: !!id,
  });
}

export function useCriarProduto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarProduto,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.produtos }),
  });
}

export function useAtualizarProduto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarProduto(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.produtos }),
  });
}

export function useDeletarProduto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarProduto,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.produtos }),
  });
}

export function useToggleDisponibilidade() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, disponivel }: { id: number; disponivel: boolean }) =>
      api.toggleDisponibilidade(id, disponivel),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.produtos }),
  });
}

// ─── Variações ─────────────────────────────────────────
export function useVariacoes(produtoId: number) {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.variacoes(produtoId),
    queryFn: () => api.getVariacoes(produtoId),
    staleTime: 2 * 60 * 1000,
    enabled: !!produtoId,
  });
}

export function useCriarVariacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ produtoId, ...payload }: { produtoId: number } & Record<string, unknown>) =>
      api.criarVariacao(produtoId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.variacoes(vars.produtoId) });
    },
  });
}

export function useAtualizarVariacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarVariacao(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "variacoes"] }),
  });
}

export function useDeletarVariacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarVariacao,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "variacoes"] }),
  });
}

// ─── Combos ────────────────────────────────────────────
export function useCombos() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.combos,
    queryFn: api.getCombos,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCriarCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarCombo,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.combos }),
  });
}

export function useAtualizarCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarCombo(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.combos }),
  });
}

export function useDeletarCombo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarCombo,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.combos }),
  });
}

// ─── Motoboys ──────────────────────────────────────────
export function useMotoboys() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.motoboys,
    queryFn: api.getMotoboys,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCriarMotoboy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarMotoboy,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys }),
  });
}

export function useAtualizarMotoboy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarMotoboy(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys }),
  });
}

export function useDeletarMotoboy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarMotoboy,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys }),
  });
}

export function useRankingMotoboys() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.rankingMotoboys,
    queryFn: api.getRankingMotoboys,
    staleTime: 60 * 1000,
  });
}

export function useSolicitacoesMotoboys() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.solicitacoesMotoboys,
    queryFn: api.getSolicitacoesMotoboys,
    staleTime: 30 * 1000,
  });
}

export function useResponderSolicitacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, aprovado }: { id: number; aprovado: boolean }) =>
      api.responderSolicitacao(id, { aprovado }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.solicitacoesMotoboys });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
    },
  });
}

// ─── Caixa ─────────────────────────────────────────────
export function useCaixaAtual() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.caixaAtual,
    queryFn: api.getCaixaAtual,
    staleTime: 30 * 1000,
  });
}

export function useAbrirCaixa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valor_inicial: number) => api.abrirCaixa(valor_inicial),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual }),
  });
}

export function useRegistrarMovimentacao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.registrarMovimentacao,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual }),
  });
}

export function useFecharCaixa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (valor_contado: number) => api.fecharCaixa(valor_contado),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.historicoCaixa });
    },
  });
}

export function useHistoricoCaixa(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.historicoCaixa, params],
    queryFn: () => api.getHistoricoCaixa(params),
    staleTime: 60 * 1000,
  });
}

// ─── Configurações ─────────────────────────────────────
export function useConfig() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.config,
    queryFn: api.getConfig,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAtualizarConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.atualizarConfig,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.config }),
  });
}

export function useConfigSite() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.configSite,
    queryFn: api.getConfigSite,
    staleTime: 5 * 60 * 1000,
  });
}

export function useAtualizarConfigSite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.atualizarConfigSite,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.configSite }),
  });
}

// ─── Bairros ───────────────────────────────────────────
export function useBairros() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.bairros,
    queryFn: api.getBairros,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCriarBairro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.criarBairro(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.bairros }),
  });
}

export function useAtualizarBairro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarBairro(id, payload as { nome?: string; taxa_entrega?: number }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.bairros }),
  });
}

export function useDeletarBairro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarBairro,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.bairros }),
  });
}

// ─── Promoções ─────────────────────────────────────────
export function usePromocoes() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.promocoes,
    queryFn: api.getPromocoes,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCriarPromocao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarPromocao,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.promocoes }),
  });
}

export function useAtualizarPromocao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarPromocao(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.promocoes }),
  });
}

export function useDeletarPromocao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarPromocao,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.promocoes }),
  });
}

// ─── Fidelidade ────────────────────────────────────────
export function usePremios() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.premios,
    queryFn: api.getPremios,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCriarPremio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarPremio,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.premios }),
  });
}

export function useAtualizarPremio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number } & Record<string, unknown>) =>
      api.atualizarPremio(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.premios }),
  });
}

export function useDeletarPremio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarPremio,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.premios }),
  });
}

// ─── Relatórios ────────────────────────────────────────
export function useRelatorioVendas(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.relatorioVendas, params],
    queryFn: () => api.getRelatorioVendas(params),
    staleTime: 60 * 1000,
    enabled: false, // manual trigger
  });
}

export function useRelatorioMotoboys(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.relatorioMotoboys, params],
    queryFn: () => api.getRelatorioMotoboys(params),
    staleTime: 60 * 1000,
    enabled: false,
  });
}

export function useRelatorioProdutos(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.relatorioProdutos, params],
    queryFn: () => api.getRelatorioProdutos(params),
    staleTime: 60 * 1000,
    enabled: false,
  });
}

export function useCarregarProdutosModelo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.carregarProdutosModelo,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.produtos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.categorias });
    },
  });
}

// ─── Analytics Avançado ──────────────────────────────
export function useAnalyticsAvancado(params?: { periodo?: string; senha: string }) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.relatorioProdutos, "analytics", params?.periodo],
    queryFn: () => api.getAnalyticsAvancado(params!),
    staleTime: 60 * 1000,
    enabled: !!params?.senha,
  });
}

// ─── Entregas Ativas ──────────────────────────────────
export function useEntregasAtivas() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.entregasAtivas,
    queryFn: api.getEntregasAtivas,
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  });
}

// ─── Diagnóstico de Tempo ─────────────────────────────
export function useDiagnosticoTempo() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo,
    queryFn: api.getDiagnosticoTempo,
    staleTime: 15 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useAjustarTempo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.ajustarTempoAutomatico,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.configSite });
    },
  });
}
