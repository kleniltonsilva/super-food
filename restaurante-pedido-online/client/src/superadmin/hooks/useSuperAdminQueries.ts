import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMetricas,
  getRestaurantes,
  criarRestaurante,
  atualizarRestaurante,
  atualizarStatusRestaurante,
  getPlanos,
  atualizarPlano,
  getInadimplentes,
  getAnalytics,
  getErrosSentry,
  getErroDetalheSentry,
  getDominiosRestaurante,
  criarDominioRestaurante,
  verificarDominioDNS,
  deletarDominio,
  getCredenciaisPlataforma,
  salvarCredencialPlataforma,
  deletarCredencialPlataforma,
  toggleCredencialPlataforma,
  getStatusIntegracoes,
  getBillingConfig,
  atualizarBillingConfig,
  getBillingDashboard,
  getBillingAuditLog,
  iniciarTrialRestaurante,
  estenderTrialRestaurante,
  reativarRestauranteBilling,
  migrarRestauranteAsaas,
  atualizarPlanoRestaurante,
  cancelarAssinaturaRestaurante,
  getDemos,
  getDemo,
  atualizarDemo,
  atualizarProdutoDemo,
  atualizarSiteConfigDemo,
  resetDemo,
  consultarCnpj,
  getBotInstancias,
  criarBotInstancia,
  atualizarBotInstancia,
  deletarBotInstancia,
} from "@/superadmin/lib/superAdminApiClient";

// ─── Métricas ──────────────────────────────────────────
export function useMetricas() {
  return useQuery({
    queryKey: ["superadmin", "metricas"],
    queryFn: getMetricas,
    staleTime: 30_000,
  });
}

// ─── Restaurantes ──────────────────────────────────────
export function useRestaurantes(params?: {
  status?: string;
  plano?: string;
  busca?: string;
}) {
  return useQuery({
    queryKey: ["superadmin", "restaurantes", params],
    queryFn: () => getRestaurantes(params),
    staleTime: 30_000,
  });
}

export function useCriarRestaurante() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: criarRestaurante,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "metricas"] });
    },
  });
}

export function useAtualizarRestaurante() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      atualizarRestaurante(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "metricas"] });
    },
  });
}

export function useAtualizarStatusRestaurante() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) =>
      atualizarStatusRestaurante(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "metricas"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "inadimplentes"] });
    },
  });
}

// ─── Planos ────────────────────────────────────────────
export function usePlanos() {
  return useQuery({
    queryKey: ["superadmin", "planos"],
    queryFn: getPlanos,
    staleTime: 60_000,
  });
}

export function useAtualizarPlano() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ nome, payload }: { nome: string; payload: { valor?: number; motoboys?: number; descricao?: string } }) =>
      atualizarPlano(nome, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "planos"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
    },
  });
}

// ─── Analytics ────────────────────────────────────────
export function useAnalytics(periodo?: string) {
  return useQuery({
    queryKey: ["superadmin", "analytics", periodo],
    queryFn: () => getAnalytics(periodo ? { periodo } : undefined),
    staleTime: 60_000,
  });
}

// ─── Inadimplentes ─────────────────────────────────────
export function useInadimplentes(dias_tolerancia?: number) {
  return useQuery({
    queryKey: ["superadmin", "inadimplentes", dias_tolerancia],
    queryFn: () => getInadimplentes(dias_tolerancia),
    staleTime: 30_000,
  });
}

// ─── Erros Sentry ─────────────────────────────────────
export function useErrosSentry(projeto: string = "api", periodo: string = "24h", statusFiltro: string = "todos") {
  return useQuery({
    queryKey: ["superadmin", "erros-sentry", projeto, periodo, statusFiltro],
    queryFn: () => getErrosSentry(projeto, periodo, statusFiltro),
    staleTime: 30_000,
  });
}

export function useErroDetalheSentry(issueId: string | null) {
  return useQuery({
    queryKey: ["superadmin", "erro-detalhe-sentry", issueId],
    queryFn: () => getErroDetalheSentry(issueId!),
    enabled: !!issueId,
    staleTime: 60_000,
  });
}

// ─── Domínios Personalizados ─────────────────────────
export function useDominiosRestaurante(restauranteId: number | null) {
  return useQuery({
    queryKey: ["superadmin", "dominios", restauranteId],
    queryFn: () => getDominiosRestaurante(restauranteId!),
    enabled: !!restauranteId,
    staleTime: 30_000,
  });
}

export function useCriarDominio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ restauranteId, dominio }: { restauranteId: number; dominio: string }) =>
      criarDominioRestaurante(restauranteId, { dominio }),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["superadmin", "dominios", variables.restauranteId] });
    },
  });
}

export function useVerificarDominioDNS() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dominioId: number) => verificarDominioDNS(dominioId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "dominios"] });
    },
  });
}

export function useDeletarDominio() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (dominioId: number) => deletarDominio(dominioId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "dominios"] });
    },
  });
}

// ─── Credenciais Plataforma (Integrações Marketplace) ──
export function useCredenciaisPlataforma() {
  return useQuery({
    queryKey: ["superadmin", "credenciais-plataforma"],
    queryFn: getCredenciaisPlataforma,
    staleTime: 30_000,
  });
}

export function useSalvarCredencial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: salvarCredencialPlataforma,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "credenciais-plataforma"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "status-integracoes"] });
    },
  });
}

export function useDeletarCredencial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletarCredencialPlataforma,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "credenciais-plataforma"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "status-integracoes"] });
    },
  });
}

export function useToggleCredencial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: toggleCredencialPlataforma,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "credenciais-plataforma"] });
    },
  });
}

export function useStatusIntegracoes() {
  return useQuery({
    queryKey: ["superadmin", "status-integracoes"],
    queryFn: getStatusIntegracoes,
    staleTime: 30_000,
  });
}

// ─── Billing ────────────────────────────────────────────
export function useBillingConfig() {
  return useQuery({
    queryKey: ["superadmin", "billing-config"],
    queryFn: getBillingConfig,
    staleTime: 60_000,
  });
}

export function useAtualizarBillingConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: atualizarBillingConfig,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-config"] });
    },
  });
}

export function useBillingDashboard() {
  return useQuery({
    queryKey: ["superadmin", "billing-dashboard"],
    queryFn: getBillingDashboard,
    staleTime: 30_000,
  });
}

export function useBillingAuditLog(params?: Record<string, unknown>) {
  return useQuery({
    queryKey: ["superadmin", "billing-audit", params],
    queryFn: () => getBillingAuditLog(params),
    staleTime: 30_000,
  });
}

export function useIniciarTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: iniciarTrialRestaurante,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

export function useEstenderTrial() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, dias }: { id: number; dias: number }) => estenderTrialRestaurante(id, dias),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

export function useReativarBilling() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: reativarRestauranteBilling,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

export function useMigrarAsaas() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: migrarRestauranteAsaas,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

export function useAtualizarPlanoAdmin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: { plano: string; ciclo?: string; valor_override?: number } }) =>
      atualizarPlanoRestaurante(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

export function useCancelarAssinatura() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: cancelarAssinaturaRestaurante,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "restaurantes"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "billing-dashboard"] });
    },
  });
}

// ─── CNPJ Lookup ──────────────────────────────────────
export function useConsultarCnpj() {
  return useMutation({
    mutationFn: consultarCnpj,
  });
}

// ─── Demos ─────────────────────────────────────────────
export function useDemos() {
  return useQuery({
    queryKey: ["superadmin", "demos"],
    queryFn: getDemos,
    staleTime: 30_000,
  });
}

export function useDemo(id: number | null) {
  return useQuery({
    queryKey: ["superadmin", "demo", id],
    queryFn: () => getDemo(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

export function useAtualizarDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: Record<string, unknown> }) =>
      atualizarDemo(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "demos"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "demo"] });
    },
  });
}

export function useAtualizarProdutoDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ demoId, produtoId, payload }: { demoId: number; produtoId: number; payload: Record<string, unknown> }) =>
      atualizarProdutoDemo(demoId, produtoId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["superadmin", "demo", variables.demoId] });
    },
  });
}

export function useAtualizarSiteConfigDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ demoId, payload }: { demoId: number; payload: Record<string, unknown> }) =>
      atualizarSiteConfigDemo(demoId, payload),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ["superadmin", "demo", variables.demoId] });
      qc.invalidateQueries({ queryKey: ["superadmin", "demos"] });
    },
  });
}

export function useResetDemo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: resetDemo,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "demos"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "demo"] });
    },
  });
}

// ─── Bot WhatsApp Humanoide ─────────────────────────────
export function useBotInstancias() {
  return useQuery({
    queryKey: ["superadmin", "bot", "instancias"] as const,
    queryFn: getBotInstancias,
    staleTime: 30_000,
  });
}

export function useCriarBotInstancia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ restauranteId, payload }: { restauranteId: number; payload: Record<string, unknown> }) =>
      criarBotInstancia(restauranteId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "bot", "instancias"] });
    },
  });
}

export function useAtualizarBotInstancia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ configId, payload }: { configId: number; payload: Record<string, unknown> }) =>
      atualizarBotInstancia(configId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "bot", "instancias"] });
    },
  });
}

export function useDeletarBotInstancia() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deletarBotInstancia,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "bot", "instancias"] });
    },
  });
}
