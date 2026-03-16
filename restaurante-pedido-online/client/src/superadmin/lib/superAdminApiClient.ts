import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "@/lib/sentry";

const superAdminApi = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — adiciona JWT do super admin
superAdminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_superadmin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 remove token e dispara StorageEvent
superAdminApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      if (!url.includes("/auth/admin/login")) {
        localStorage.removeItem("sf_superadmin_token");
        localStorage.removeItem("sf_superadmin_data");
        window.dispatchEvent(
          new StorageEvent("storage", { key: "sf_superadmin_token", newValue: null })
        );
      }
    }
    // Breadcrumb Sentry para erros 5xx
    if (err.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("superadmin", err.config?.method || "get", err.config?.url || "", err.response.status);
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────
export async function loginAdmin(usuario: string, senha: string) {
  const { data } = await superAdminApi.post("/auth/admin/login", { usuario, senha });
  return data;
}

export async function getMe() {
  const { data } = await superAdminApi.get("/auth/admin/me");
  return data;
}

// ─── Restaurantes ──────────────────────────────────────
export async function getRestaurantes(params?: {
  status?: string;
  plano?: string;
  busca?: string;
}) {
  const { data } = await superAdminApi.get("/api/admin/restaurantes", { params });
  return data;
}

export async function criarRestaurante(payload: {
  nome_fantasia: string;
  email: string;
  telefone: string;
  endereco_completo: string;
  razao_social?: string;
  cnpj?: string;
  cidade?: string;
  estado?: string;
  cep?: string;
  plano?: string;
  valor_plano?: number;
  limite_motoboys?: number;
  criar_site?: boolean;
  tipo_restaurante?: string;
  whatsapp?: string;
}) {
  const { data } = await superAdminApi.post("/api/admin/restaurantes", payload);
  return data;
}

export async function atualizarRestaurante(
  id: number,
  payload: Record<string, unknown>
) {
  const { data } = await superAdminApi.put(`/api/admin/restaurantes/${id}`, payload);
  return data;
}

export async function atualizarStatusRestaurante(
  id: number,
  status: string
) {
  const { data } = await superAdminApi.put(`/api/admin/restaurantes/${id}/status`, { status });
  return data;
}

// ─── Planos ────────────────────────────────────────────
export async function getPlanos() {
  const { data } = await superAdminApi.get("/api/admin/planos");
  return data;
}

export async function atualizarPlano(
  nome: string,
  payload: { valor?: number; motoboys?: number; descricao?: string }
) {
  const { data } = await superAdminApi.put(`/api/admin/planos/${encodeURIComponent(nome)}`, payload);
  return data;
}

// ─── Métricas ──────────────────────────────────────────
export async function getMetricas() {
  const { data } = await superAdminApi.get("/api/admin/metricas");
  return data;
}

// ─── Analytics ────────────────────────────────────────
export async function getAnalytics(params?: { periodo?: string }) {
  const { data } = await superAdminApi.get("/api/admin/analytics", { params });
  return data;
}

// ─── Autocomplete Endereço ─────────────────────────────
export async function autocompleteEndereco(query: string) {
  const { data } = await superAdminApi.get("/api/admin/autocomplete-endereco", { params: { query } });
  return data;
}

// ─── Inadimplentes ─────────────────────────────────────
export async function getInadimplentes(dias_tolerancia?: number) {
  const { data } = await superAdminApi.get("/api/admin/inadimplentes", {
    params: dias_tolerancia !== undefined ? { dias_tolerancia } : undefined,
  });
  return data;
}

// ─── Erros Sentry ─────────────────────────────────────
export async function getErrosSentry(projeto: string = "api", periodo: string = "24h", statusFiltro: string = "todos") {
  const { data } = await superAdminApi.get("/api/admin/erros", {
    params: { projeto, periodo, status_filtro: statusFiltro },
  });
  return data;
}

export async function getErroDetalheSentry(issueId: string) {
  const { data } = await superAdminApi.get(`/api/admin/erros/${issueId}`);
  return data;
}

// ─── Domínios Personalizados ─────────────────────────
export async function getDominiosRestaurante(restauranteId: number) {
  const { data } = await superAdminApi.get(`/api/admin/restaurantes/${restauranteId}/dominios`);
  return data;
}

export async function criarDominioRestaurante(restauranteId: number, payload: { dominio: string }) {
  const { data } = await superAdminApi.post(`/api/admin/restaurantes/${restauranteId}/dominios`, payload);
  return data;
}

export async function verificarDominioDNS(dominioId: number) {
  const { data } = await superAdminApi.post(`/api/admin/dominios/${dominioId}/verificar`);
  return data;
}

export async function deletarDominio(dominioId: number) {
  const { data } = await superAdminApi.delete(`/api/admin/dominios/${dominioId}`);
  return data;
}

// ─── Credenciais Plataforma (Integrações Marketplace) ──
export async function getCredenciaisPlataforma() {
  const { data } = await superAdminApi.get("/api/admin/integracoes/plataformas");
  return data;
}

export async function salvarCredencialPlataforma(payload: {
  marketplace: string;
  client_id: string;
  client_secret: string;
  config_json?: Record<string, unknown>;
}) {
  const { data } = await superAdminApi.post("/api/admin/integracoes/plataformas", payload);
  return data;
}

export async function deletarCredencialPlataforma(marketplace: string) {
  const { data } = await superAdminApi.delete(`/api/admin/integracoes/plataformas/${marketplace}`);
  return data;
}

export async function toggleCredencialPlataforma(marketplace: string) {
  const { data } = await superAdminApi.put(`/api/admin/integracoes/plataformas/${marketplace}/toggle`);
  return data;
}

export async function getStatusIntegracoes() {
  const { data } = await superAdminApi.get("/api/admin/integracoes/status");
  return data;
}

// ─── Billing ────────────────────────────────────────────
export async function getBillingConfig() {
  const { data } = await superAdminApi.get("/api/admin/billing/config");
  return data;
}

export async function atualizarBillingConfig(payload: Record<string, unknown>) {
  const { data } = await superAdminApi.put("/api/admin/billing/config", payload);
  return data;
}

export async function getBillingDashboard() {
  const { data } = await superAdminApi.get("/api/admin/billing/dashboard");
  return data;
}

export async function getBillingAuditLog(params?: Record<string, unknown>) {
  const { data } = await superAdminApi.get("/api/admin/billing/audit-log", { params });
  return data;
}

export async function iniciarTrialRestaurante(restauranteId: number) {
  const { data } = await superAdminApi.post(`/api/admin/billing/restaurantes/${restauranteId}/iniciar-trial`);
  return data;
}

export async function estenderTrialRestaurante(restauranteId: number, dias: number) {
  const { data } = await superAdminApi.post(`/api/admin/billing/restaurantes/${restauranteId}/estender-trial`, { dias });
  return data;
}

export async function reativarRestauranteBilling(restauranteId: number) {
  const { data } = await superAdminApi.post(`/api/admin/billing/restaurantes/${restauranteId}/reativar`);
  return data;
}

export async function migrarRestauranteAsaas(restauranteId: number) {
  const { data } = await superAdminApi.post(`/api/admin/billing/restaurantes/${restauranteId}/migrar-asaas`);
  return data;
}

export async function atualizarPlanoRestaurante(restauranteId: number, payload: { plano: string; ciclo?: string; valor_override?: number }) {
  const { data } = await superAdminApi.put(`/api/admin/billing/restaurantes/${restauranteId}/plano`, payload);
  return data;
}

export async function cancelarAssinaturaRestaurante(restauranteId: number) {
  const { data } = await superAdminApi.post(`/api/admin/billing/restaurantes/${restauranteId}/cancelar`);
  return data;
}
