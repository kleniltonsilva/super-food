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

// ─── Inadimplentes ─────────────────────────────────────
export function useInadimplentes(dias_tolerancia?: number) {
  return useQuery({
    queryKey: ["superadmin", "inadimplentes", dias_tolerancia],
    queryFn: () => getInadimplentes(dias_tolerancia),
    staleTime: 30_000,
  });
}
