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
  operadoresCaixa: ["admin", "caixa", "operadores"] as const,
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
  mesas: ["admin", "mesas"] as const,
  tempoMedio: ["admin", "tempo-medio"] as const,
  alertasAtraso: ["admin", "alertas-atraso"] as const,
  sugestoesTempo: ["admin", "sugestoes-tempo"] as const,
  notificacoes: ["admin", "notificacoes"] as const,
  integracoes: ["admin", "integracoes"] as const,
  ifoodStatus: ["admin", "integracoes", "ifood", "status"] as const,
  billingStatus: ["admin", "billing", "status"] as const,
  faturas: ["admin", "billing", "faturas"] as const,
  planosDisponiveis: ["admin", "billing", "planos"] as const,
  pixConfig: ["admin", "pix", "config"] as const,
  pixSaques: ["admin", "pix", "saques"] as const,
  cozinheiros: ["admin", "cozinha", "cozinheiros"] as const,
  configCozinha: ["admin", "cozinha", "config"] as const,
  dashboardCozinha: ["admin", "cozinha", "dashboard"] as const,
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
    mutationFn: ({ id, motoboy_id }: { id: number; motoboy_id?: number }) =>
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

export function useAplicarMaxSabores() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dados: { nome_tamanho: string; max_sabores: number }) =>
      api.aplicarMaxSabores(dados),
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
    mutationFn: (payload: { valor_abertura: number; operador_nome: string; senha: string; criar_operador?: boolean }) =>
      api.abrirCaixa(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.operadoresCaixa });
    },
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
    mutationFn: (payload: { valor_contado: number; operador_nome: string; senha: string }) =>
      api.fecharCaixa(payload),
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

export function useOperadoresCaixa() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.operadoresCaixa,
    queryFn: api.getOperadoresCaixa,
    staleTime: 2 * 60 * 1000,
  });
}

export function useCriarOperadorCaixa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { nome: string; senha: string }) => api.criarOperadorCaixa(payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.operadoresCaixa }),
  });
}

export function useDeletarOperadorCaixa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, senha }: { id: number; senha: string }) => api.deletarOperadorCaixa(id, senha),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.operadoresCaixa }),
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

// ─── Mesas ────────────────────────────────────────────
export function useMesas() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.mesas,
    queryFn: api.getMesas,
    staleTime: 10 * 1000,
    refetchInterval: 30 * 1000,
  });
}

export function usePagarMesa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ numero_mesa, forma_pagamento }: { numero_mesa: string; forma_pagamento?: string }) =>
      api.pagarMesa(numero_mesa, forma_pagamento),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.caixaAtual });
    },
  });
}

export function useAdicionarPedidoMesa() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      numero_mesa,
      ...payload
    }: {
      numero_mesa: string;
      itens: string;
      valor_total: number;
      observacoes?: string;
      forma_pagamento?: string;
    }) => api.adicionarPedidoMesa(numero_mesa, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
    },
  });
}

// ─── Tempo Médio ─────────────────────────────────────
export function useTempoMedio() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.tempoMedio,
    queryFn: api.getTempoMedio,
    staleTime: 15 * 1000,
    refetchInterval: 60 * 1000,
  });
}

// ─── Alertas de Atraso ──────────────────────────────
export function useAlertasAtraso(periodo?: string, tipo?: string) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.alertasAtraso, periodo, tipo],
    queryFn: () => api.getAlertasAtraso({ periodo, tipo }),
    staleTime: 30 * 1000,
  });
}

// ─── Sugestões de Tempo ─────────────────────────────
export function useSugestoesTempo() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.sugestoesTempo,
    queryFn: api.getSugestoesTempo,
    staleTime: 60 * 1000,
  });
}

export function useRejeitarSugestao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.rejeitarSugestaoTempo,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.sugestoesTempo });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.diagnosticoTempo });
    },
  });
}

// ─── Notificações ───────────────────────────────────
export function useNotificacoes() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.notificacoes,
    queryFn: api.getNotificacoes,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
}

export function useMarcarNotificacaoLida() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.marcarNotificacaoLida,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.notificacoes }),
  });
}

// ─── Pedido Rápido Mesa ─────────────────────────────
export function useAdicionarPedidoMesaRapido() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      numero_mesa,
      itens,
    }: {
      numero_mesa: string;
      itens: Array<{ produto_id: number; quantidade: number; observacao?: string; variacoes?: Array<{ nome: string; preco_adicional: number }> }>;
    }) => api.adicionarPedidoMesaRapido(numero_mesa, { itens }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.mesas });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
    },
  });
}

// ─── Integrações Marketplace ─────────────────────────
export function useIntegracoes() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.integracoes,
    queryFn: api.getIntegracoes,
    staleTime: 60 * 1000,
  });
}

export function useIFoodStatus() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.ifoodStatus,
    queryFn: api.getIFoodStatus,
    staleTime: 30 * 1000,
  });
}

export function useConnectIFood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.connectIFood,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.integracoes }),
  });
}

export function useIFoodAuthStatus() {
  return useQuery({
    queryKey: ["admin", "integracoes", "ifood", "auth-status"] as const,
    queryFn: api.getIFoodAuthStatus,
    staleTime: 5 * 1000,
    refetchInterval: 5 * 1000,
    enabled: false,
  });
}

export function useDisconnectIFood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.disconnectIFood,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.integracoes });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.ifoodStatus });
    },
  });
}

export function useToggleIntegracao() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.toggleIntegracao,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.integracoes });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.ifoodStatus });
    },
  });
}

export function useSyncCatalogIFood() {
  return useMutation({ mutationFn: api.syncCatalogIFood });
}

export function useConnectOpenDelivery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.connectOpenDelivery,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.integracoes }),
  });
}

export function useDisconnectMarketplace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.disconnectMarketplace,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.integracoes }),
  });
}

// ─── Billing ────────────────────────────────────────────
export function useBillingStatus() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.billingStatus,
    queryFn: api.getBillingStatus,
    staleTime: 30_000,
  });
}

export function useFaturas(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.faturas, params],
    queryFn: () => api.getFaturas(params),
    staleTime: 30_000,
  });
}

export function usePlanosDisponiveis() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.planosDisponiveis,
    queryFn: api.getPlanosDisponiveis,
    staleTime: 60_000,
  });
}

export function useSelecionarPlano() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.selecionarPlano,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.billingStatus });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.faturas });
    },
  });
}

// ─── Pix Online ─────────────────────────────────────────
export function usePixConfig() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.pixConfig,
    queryFn: api.getPixConfig,
    staleTime: 30_000,
  });
}

export function useAtivarPix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.ativarPix,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pixConfig }),
  });
}

export function useDesativarPix() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.desativarPix,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pixConfig }),
  });
}

export function useConfigSaqueAuto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.configSaqueAuto,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pixConfig }),
  });
}

export function usePreviewSaque() {
  return useMutation({
    mutationFn: api.previewSaque,
  });
}

export function useSolicitarSaque() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.confirmarSaque,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pixConfig });
      qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pixSaques });
    },
  });
}

export function usePixSaques(params?: { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: [...ADMIN_QUERY_KEYS.pixSaques, params],
    queryFn: () => api.getPixSaques(params),
    staleTime: 30_000,
  });
}

// ─── KDS / Cozinha Digital ──────────────────────────────
export function useCozinheiros() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.cozinheiros,
    queryFn: api.getCozinheiros,
    staleTime: 30_000,
  });
}

export function useCriarCozinheiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.criarCozinheiro,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.cozinheiros }),
  });
}

export function useAtualizarCozinheiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...payload }: { id: number; nome?: string; login?: string; senha?: string; modo?: string; avatar_emoji?: string; produto_ids?: number[] }) =>
      api.atualizarCozinheiro(id, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.cozinheiros }),
  });
}

export function useDeletarCozinheiro() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deletarCozinheiro,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.cozinheiros }),
  });
}

export function useConfigCozinha() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.configCozinha,
    queryFn: api.getConfigCozinha,
    staleTime: 30_000,
  });
}

export function useAtualizarConfigCozinha() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.atualizarConfigCozinha,
    onSuccess: () => qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.configCozinha }),
  });
}

export function useDashboardCozinha() {
  return useQuery({
    queryKey: ADMIN_QUERY_KEYS.dashboardCozinha,
    queryFn: api.getDashboardCozinha,
    staleTime: 15_000,
    refetchInterval: 30_000,
  });
}
