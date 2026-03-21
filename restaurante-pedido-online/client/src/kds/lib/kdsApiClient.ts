import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "@/lib/sentry";

const kdsApi = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — adiciona JWT do cozinheiro
kdsApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_kds_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 remove token
kdsApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      if (!url.includes("/auth/cozinheiro/login")) {
        localStorage.removeItem("sf_kds_token");
        localStorage.removeItem("sf_kds_data");
        window.dispatchEvent(
          new StorageEvent("storage", { key: "sf_kds_token", newValue: null })
        );
      }
    }
    if (err.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("kds", err.config?.method || "get", err.config?.url || "", err.response.status);
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────
export async function loginCozinheiro(codigo_restaurante: string, login: string, senha: string) {
  const { data } = await kdsApi.post("/auth/cozinheiro/login", { codigo_restaurante, login, senha });
  return data;
}

export async function getMe() {
  const { data } = await kdsApi.get("/auth/cozinheiro/me");
  return data;
}

// ─── Pedidos KDS ───────────────────────────────────────
export async function getPedidosKds(statusFilter?: string) {
  const params = statusFilter ? { status_filter: statusFilter } : undefined;
  const { data } = await kdsApi.get("/kds/pedidos", { params });
  return data;
}

export async function atualizarStatusKds(pedidoCozinhaId: number, status: string) {
  const { data } = await kdsApi.patch(`/kds/pedidos/${pedidoCozinhaId}/status`, { status });
  return data;
}

export async function assumirPedidoKds(pedidoCozinhaId: number) {
  const { data } = await kdsApi.post(`/kds/pedidos/${pedidoCozinhaId}/assumir`);
  return data;
}

export async function refazerPedidoKds(pedidoCozinhaId: number) {
  const { data } = await kdsApi.post(`/kds/pedidos/${pedidoCozinhaId}/refazer`);
  return data;
}

// ─── Config ────────────────────────────────────────────
export async function getConfigKds() {
  const { data } = await kdsApi.get("/kds/config");
  return data;
}
