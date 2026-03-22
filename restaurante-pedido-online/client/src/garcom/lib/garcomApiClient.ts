import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "@/lib/sentry";

const garcomApi = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — adiciona JWT do garçom
garcomApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_garcom_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 remove token
garcomApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      if (!url.includes("/garcom/auth/login")) {
        localStorage.removeItem("sf_garcom_token");
        localStorage.removeItem("sf_garcom_data");
        window.dispatchEvent(
          new StorageEvent("storage", { key: "sf_garcom_token", newValue: null })
        );
      }
    }
    if (err.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("garcom", err.config?.method || "get", err.config?.url || "", err.response.status);
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────
export async function loginGarcom(codigo_restaurante: string, login: string, senha: string) {
  const { data } = await garcomApi.post("/garcom/auth/login", { codigo_restaurante, login, senha });
  return data;
}

export async function getMe() {
  const { data } = await garcomApi.get("/garcom/auth/me");
  return data;
}

// ─── Mesas ─────────────────────────────────────────────
export async function getMesas() {
  const { data } = await garcomApi.get("/garcom/mesas");
  return data;
}

export async function abrirMesa(mesaId: number, payload: { qtd_pessoas: number; alergia?: string; tags?: string[]; notas?: string }) {
  const { data } = await garcomApi.post(`/garcom/mesas/${mesaId}/abrir`, payload);
  return data;
}

export async function transferirMesa(mesaId: number, mesaDestinoId: number) {
  const { data } = await garcomApi.post(`/garcom/mesas/${mesaId}/transferir`, { mesa_destino_id: mesaDestinoId });
  return data;
}

// ─── Sessões ───────────────────────────────────────────
export async function getSessao(sessaoId: number) {
  const { data } = await garcomApi.get(`/garcom/sessoes/${sessaoId}`);
  return data;
}

export async function criarPedidoSessao(sessaoId: number, payload: {
  itens: Array<{ item_cardapio_id: number; qty: number; obs?: string; course?: string }>;
  observacoes?: string;
}) {
  const { data } = await garcomApi.post(`/garcom/sessoes/${sessaoId}/pedidos`, payload);
  return data;
}

export async function solicitarFechamento(sessaoId: number) {
  const { data } = await garcomApi.post(`/garcom/sessoes/${sessaoId}/solicitar-fechamento`);
  return data;
}

export async function repetirRodada(sessaoId: number) {
  const { data } = await garcomApi.post(`/garcom/sessoes/${sessaoId}/repetir-rodada`);
  return data;
}

// ─── Itens Pedido ──────────────────────────────────────
export async function cancelarItem(pedidoId: number, itemId: number) {
  const { data } = await garcomApi.delete(`/garcom/pedidos/${pedidoId}/itens/${itemId}`);
  return data;
}

// ─── Itens Esgotados ──────────────────────────────────
export async function getItensEsgotados() {
  const { data } = await garcomApi.get("/garcom/itens-esgotados");
  return data;
}

export async function marcarEsgotado(itemCardapioId: number) {
  const { data } = await garcomApi.post("/garcom/itens-esgotados", { item_cardapio_id: itemCardapioId });
  return data;
}

export async function desmarcarEsgotado(id: number) {
  const { data } = await garcomApi.delete(`/garcom/itens-esgotados/${id}`);
  return data;
}

// ─── Cardápio ─────────────────────────────────────────
export async function getCardapio() {
  const { data } = await garcomApi.get("/garcom/cardapio");
  return data;
}
