import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "@/lib/sentry";

const motoboyApi = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — adiciona JWT do motoboy
motoboyApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_motoboy_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Endpoints que NUNCA devem causar logout — falhas transitórias são ignoradas.
// GPS envia a cada 10s: um 401 transitório NÃO pode deslogar o motoboy.
const ENDPOINTS_SEM_LOGOUT = [
  "/api/gps/update-auth",   // GPS background (10s)
  "/motoboy/status",        // heartbeat de status
  "/motoboy/entregas/pendentes",
  "/motoboy/entregas/em-rota",
];

// Response interceptor — 401 só causa logout em endpoints de autenticação explícita
motoboyApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      const isLoginRoute = url.includes("/auth/motoboy/login");
      const isRefreshRoute = url.includes("/auth/motoboy/refresh");
      const isSemLogout = ENDPOINTS_SEM_LOGOUT.some((e) => url.includes(e));

      // Só desloga se for endpoint de validação de identidade (não GPS ou background)
      if (!isLoginRoute && !isRefreshRoute && !isSemLogout) {
        localStorage.removeItem("sf_motoboy_token");
        localStorage.removeItem("sf_motoboy_data");
        window.dispatchEvent(
          new StorageEvent("storage", { key: "sf_motoboy_token", newValue: null })
        );
      }
    }
    // Breadcrumb Sentry para erros 5xx
    if (err.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("motoboy", err.config?.method || "get", err.config?.url || "", err.response.status);
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────
export async function loginMotoboy(codigo_restaurante: string, usuario: string, senha: string) {
  const { data } = await motoboyApi.post("/auth/motoboy/login", {
    codigo_restaurante,
    usuario,
    senha,
  });
  return data;
}

export async function getMe() {
  const { data } = await motoboyApi.get("/auth/motoboy/me");
  return data;
}

export async function refreshToken() {
  const { data } = await motoboyApi.post("/auth/motoboy/refresh");
  return data as { access_token: string; token_type: string };
}

export async function alterarSenha(senha_atual: string, nova_senha: string) {
  const { data } = await motoboyApi.put("/auth/motoboy/senha", { senha_atual, nova_senha });
  return data;
}

export async function cadastroMotoboy(payload: {
  codigo_acesso: string;
  nome: string;
  usuario: string;
  telefone: string;
  cpf?: string;
}) {
  const { data } = await motoboyApi.post("/auth/motoboy/cadastro", payload);
  return data;
}

// ─── Entregas ──────────────────────────────────────────
export async function getEntregasPendentes() {
  const { data } = await motoboyApi.get("/motoboy/entregas/pendentes");
  return data;
}

export async function getEntregasEmRota() {
  const { data } = await motoboyApi.get("/motoboy/entregas/em-rota");
  return data;
}

export async function iniciarEntrega(entregaId: number) {
  const { data } = await motoboyApi.post(`/motoboy/entregas/${entregaId}/iniciar`);
  return data;
}

export async function finalizarEntrega(entregaId: number, payload: {
  motivo: string;
  distancia_km?: number;
  lat_atual?: number;
  lon_atual?: number;
  observacao?: string;
  forma_pagamento_real?: string;
  valor_pago_dinheiro?: number;
  valor_pago_cartao?: number;
}) {
  const { data } = await motoboyApi.post(`/motoboy/entregas/${entregaId}/finalizar`, payload);
  return data;
}

export async function getHistoricoEntregas(params?: {
  data_inicio?: string;
  data_fim?: string;
  page?: number;
  limit?: number;
}) {
  const { data } = await motoboyApi.get("/motoboy/entregas/historico", { params });
  return data;
}

// ─── Status ────────────────────────────────────────────
export async function atualizarStatus(disponivel: boolean, latitude?: number, longitude?: number) {
  const { data } = await motoboyApi.put("/motoboy/status", { disponivel, latitude, longitude });
  return data;
}

// ─── Config ────────────────────────────────────────────
export async function getConfigMotoboy() {
  const { data } = await motoboyApi.get("/motoboy/config");
  return data;
}

// ─── Estatísticas e Ganhos ─────────────────────────────
export async function getEstatisticas() {
  const { data } = await motoboyApi.get("/motoboy/estatisticas");
  return data;
}

export async function getGanhosDetalhado(dataStr?: string) {
  const { data } = await motoboyApi.get("/motoboy/ganhos/detalhado", {
    params: dataStr ? { data: dataStr } : undefined,
  });
  return data;
}

// ─── GPS ───────────────────────────────────────────────
export async function enviarGPS(payload: {
  latitude: number;
  longitude: number;
  velocidade?: number;
  precisao?: number;
  heading?: number;
}) {
  const { data } = await motoboyApi.post("/api/gps/update-auth", payload);
  return data;
}
