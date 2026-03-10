import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as api from "@/motoboy/lib/motoboyApiClient";

// ─── Query Keys ────────────────────────────────────────
export const MOTOBOY_QUERY_KEYS = {
  me: ["motoboy", "me"],
  config: ["motoboy", "config"],
  entregasPendentes: ["motoboy", "entregas", "pendentes"],
  entregasEmRota: ["motoboy", "entregas", "em-rota"],
  historico: ["motoboy", "entregas", "historico"],
  estatisticas: ["motoboy", "estatisticas"],
  ganhos: ["motoboy", "ganhos"],
};

// ─── Auth ──────────────────────────────────────────────
export function useMotoboyMe() {
  return useQuery({
    queryKey: MOTOBOY_QUERY_KEYS.me,
    queryFn: api.getMe,
    staleTime: 30 * 1000,
  });
}

// ─── Config ────────────────────────────────────────────
export function useMotoboyConfig() {
  return useQuery({
    queryKey: MOTOBOY_QUERY_KEYS.config,
    queryFn: api.getConfigMotoboy,
    staleTime: 5 * 60 * 1000,
  });
}

// ─── Entregas Pendentes ────────────────────────────────
export function useEntregasPendentes() {
  return useQuery({
    queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes,
    queryFn: api.getEntregasPendentes,
    staleTime: 10 * 1000,
    refetchInterval: 15 * 1000,
  });
}

// ─── Entregas Em Rota ──────────────────────────────────
export function useEntregasEmRota() {
  return useQuery({
    queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota,
    queryFn: api.getEntregasEmRota,
    staleTime: 10 * 1000,
    refetchInterval: 15 * 1000,
  });
}

// ─── Iniciar Entrega ───────────────────────────────────
export function useIniciarEntrega() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entregaId: number) => api.iniciarEntrega(entregaId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.me });
    },
  });
}

// ─── Finalizar Entrega ─────────────────────────────────
export function useFinalizarEntrega() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ entregaId, payload }: {
      entregaId: number;
      payload: Parameters<typeof api.finalizarEntrega>[1];
    }) => api.finalizarEntrega(entregaId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.estatisticas });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.ganhos });
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.me });
    },
  });
}

// ─── Histórico ─────────────────────────────────────────
export function useHistoricoEntregas(params?: {
  data_inicio?: string;
  data_fim?: string;
  page?: number;
  limit?: number;
}) {
  return useQuery({
    queryKey: [...MOTOBOY_QUERY_KEYS.historico, params],
    queryFn: () => api.getHistoricoEntregas(params),
    staleTime: 30 * 1000,
  });
}

// ─── Status (Online/Offline) ───────────────────────────
export function useAtualizarStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ disponivel, latitude, longitude }: {
      disponivel: boolean;
      latitude?: number;
      longitude?: number;
    }) => api.atualizarStatus(disponivel, latitude, longitude),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.me });
    },
  });
}

// ─── Estatísticas ──────────────────────────────────────
export function useEstatisticas() {
  return useQuery({
    queryKey: MOTOBOY_QUERY_KEYS.estatisticas,
    queryFn: api.getEstatisticas,
    staleTime: 30 * 1000,
  });
}

// ─── Ganhos Detalhado ──────────────────────────────────
export function useGanhosDetalhado(data?: string) {
  return useQuery({
    queryKey: [...MOTOBOY_QUERY_KEYS.ganhos, data],
    queryFn: () => api.getGanhosDetalhado(data),
    staleTime: 30 * 1000,
  });
}

// ─── Alterar Senha ─────────────────────────────────────
export function useAlterarSenha() {
  return useMutation({
    mutationFn: ({ senha_atual, nova_senha }: { senha_atual: string; nova_senha: string }) =>
      api.alterarSenha(senha_atual, nova_senha),
  });
}

// ─── GPS ───────────────────────────────────────────────
export function useEnviarGPS() {
  return useMutation({
    mutationFn: api.enviarGPS,
  });
}
