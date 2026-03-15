import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "./sentry";

// Codigo do restaurante injetado pelo servidor
function getCodigoAcesso(): string {
  return (window as any).RESTAURANTE_CODIGO || "demo";
}

// Chaves do localStorage com namespace por restaurante (isolamento multi-tenant)
function getTokenKey(): string {
  return `sf_token_${getCodigoAcesso()}`;
}
function getClienteKey(): string {
  return `sf_cliente_${getCodigoAcesso()}`;
}

// Session ID para carrinho anonimo (namespace por restaurante)
function getSessionId(): string {
  const key = `sf_session_id_${getCodigoAcesso()}`;
  let sid = localStorage.getItem(key);
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem(key, sid);
  }
  return sid;
}

const api = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Interceptor: adiciona headers em toda request
api.interceptors.request.use((config) => {
  config.headers["X-Session-ID"] = getSessionId();
  const token = localStorage.getItem(getTokenKey());
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

/**
 * Interceptor de resposta: trata erros 401 (token expirado/inválido).
 *
 * Quando a API retorna 401:
 * 1. Remove o token do localStorage (sessão inválida)
 * 2. Dispara StorageEvent para sincronizar logout em todas as abas
 * 3. Propaga o erro para o chamador (React Query trata como error)
 *
 * Ignora rotas de login/registro que retornam 401 como "credenciais inválidas".
 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || "";
      // Não faz logout em rotas de autenticação (401 = "senha errada", não "token expirado")
      const isAuthRoute = url.includes("/auth/cliente/login") || url.includes("/auth/cliente/registro");
      if (!isAuthRoute) {
        localStorage.removeItem(getTokenKey());
        localStorage.removeItem(getClienteKey());
        // Dispara evento para sync entre abas (AuthContext escuta este evento)
        window.dispatchEvent(new StorageEvent("storage", {
          key: getTokenKey(),
          newValue: null,
        }));
      }
    }
    // Breadcrumb Sentry para erros 5xx
    if (error.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("site", error.config?.method || "get", error.config?.url || "", error.response.status);
    }
    return Promise.reject(error);
  }
);

// ==================== SITE ====================

export async function getSiteInfo() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}`);
  return data;
}

export async function getCategorias() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/categorias`);
  return data;
}

export async function getProdutos(categoriaId?: number, destaque?: boolean) {
  const params: Record<string, any> = {};
  if (categoriaId) params.categoria_id = categoriaId;
  if (destaque) params.destaque = true;
  const { data } = await api.get(`/site/${getCodigoAcesso()}/produtos`, { params });
  return data;
}

export async function getProdutoDetalhe(produtoId: number) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/produto/${produtoId}`);
  return data;
}

// ==================== ENTREGA ====================

export async function validarEntrega(payload: {
  endereco: string;
  latitude?: number;
  longitude?: number;
}) {
  const { data } = await api.post(`/site/${getCodigoAcesso()}/validar-entrega`, {
    endereco_texto: payload.endereco,
    latitude: payload.latitude,
    longitude: payload.longitude,
  });
  return data;
}

export async function getBairros() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/bairros`);
  return data;
}

export async function getTaxaBairro(nomeBairro: string) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/bairro/${encodeURIComponent(nomeBairro)}`);
  return data;
}

export async function autocompleteEndereco(q: string) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/autocomplete-endereco`, { params: { query: q } });
  return data;
}

// ==================== CARRINHO ====================

export async function getCarrinho() {
  const { data } = await api.get("/carrinho/", { params: { codigo_acesso: getCodigoAcesso() } });
  return data;
}

export async function adicionarAoCarrinho(item: {
  produto_id: number;
  quantidade: number;
  observacao?: string;
  variacoes?: { variacao_id: number }[];
}) {
  const { data } = await api.post("/carrinho/adicionar", {
    produto_id: item.produto_id,
    quantidade: item.quantidade,
    observacoes: item.observacao || null,
    variacoes_ids: item.variacoes ? item.variacoes.map(v => v.variacao_id) : [],
  });
  return data;
}

export async function atualizarQuantidade(itemIndex: number, quantidade: number) {
  const { data } = await api.put(`/carrinho/atualizar-quantidade/${itemIndex}`, null, { params: { nova_quantidade: quantidade, codigo_acesso: getCodigoAcesso() } });
  return data;
}

export async function removerDoCarrinho(itemIndex: number) {
  const { data } = await api.delete(`/carrinho/remover/${itemIndex}`, { params: { codigo_acesso: getCodigoAcesso() } });
  return data;
}

export async function limparCarrinho() {
  const { data } = await api.delete("/carrinho/limpar", { params: { codigo_acesso: getCodigoAcesso() } });
  return data;
}

export async function finalizarPedido(payload: {
  tipo_entrega: string;
  forma_pagamento: string;
  cliente_nome?: string;
  cliente_telefone?: string;
  endereco_entrega?: string;
  latitude?: number;
  longitude?: number;
  troco_para?: number;
  observacoes?: string;
}) {
  const { data } = await api.post("/carrinho/finalizar", { ...payload, codigo_acesso: getCodigoAcesso() });
  return data;
}

// ==================== FIDELIDADE ====================

export async function getPontosFidelidade(clienteId: number) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/fidelidade/pontos/${clienteId}`);
  return data;
}

export async function getPremiosFidelidade() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/fidelidade/premios`);
  return data;
}

export async function resgatarPremio(clienteId: number, premioId: number) {
  const { data } = await api.post(`/site/${getCodigoAcesso()}/fidelidade/resgatar/${clienteId}`, {
    premio_id: premioId,
  });
  return data;
}

// ==================== TRACKING ====================

export async function getTrackingPedido(pedidoId: number) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/pedido/${pedidoId}/tracking`);
  return data;
}

// ==================== AUTH CLIENTE ====================

export async function registrarCliente(dados: {
  nome: string;
  email: string;
  telefone: string;
  senha: string;
  cpf?: string;
}) {
  const { data } = await api.post("/auth/cliente/registro", {
    ...dados,
    codigo_acesso_restaurante: getCodigoAcesso(),
  });
  return data;
}

export async function loginCliente(email: string, senha: string) {
  const { data } = await api.post("/auth/cliente/login", {
    email,
    senha,
    codigo_acesso_restaurante: getCodigoAcesso(),
  });
  return data;
}

export async function getClienteMe() {
  const { data } = await api.get("/auth/cliente/me");
  return data;
}

export async function registrarPosPedido(dados: {
  nome: string;
  email: string;
  telefone: string;
  senha: string;
  pedido_id?: number;
}) {
  const { data } = await api.post("/auth/cliente/registro-pos-pedido", {
    ...dados,
    codigo_acesso_restaurante: getCodigoAcesso(),
  });
  return data;
}

export async function atualizarPerfil(dados: {
  nome?: string;
  telefone?: string;
  cpf?: string;
}) {
  const { data } = await api.put("/auth/cliente/perfil", dados);
  return data;
}

// ==================== ENDERECOS ====================

export async function getEnderecos() {
  const { data } = await api.get("/auth/cliente/enderecos");
  return data;
}

export async function criarEndereco(dados: {
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
}) {
  const { data } = await api.post("/auth/cliente/enderecos", dados);
  return data;
}

export async function atualizarEndereco(enderecoId: number, dados: Record<string, unknown>) {
  const { data } = await api.put(`/auth/cliente/enderecos/${enderecoId}`, dados);
  return data;
}

export async function removerEndereco(enderecoId: number) {
  const { data } = await api.delete(`/auth/cliente/enderecos/${enderecoId}`);
  return data;
}

export async function definirEnderecoPadrao(enderecoId: number) {
  const { data } = await api.put(`/auth/cliente/enderecos/${enderecoId}/padrao`);
  return data;
}

// ==================== PEDIDOS CLIENTE ====================

export async function getMeusPedidos() {
  const { data } = await api.get("/auth/cliente/pedidos");
  return data;
}

export async function getPedidoDetalhe(pedidoId: number) {
  const { data } = await api.get(`/auth/cliente/pedidos/${pedidoId}`);
  return data;
}

// ==================== SABORES (PIZZA) ====================

export async function getSaboresDisponiveis(produtoId: number) {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/produto/${produtoId}/sabores`);
  return data;
}

// ==================== COMBOS ====================

export async function getCombos() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/combos`);
  return data;
}

export async function adicionarComboAoCarrinho(comboId: number) {
  const { data } = await api.post("/carrinho/adicionar-combo", { combo_id: comboId });
  return data;
}

// ==================== PROMOCOES ====================

export async function getPromocoes() {
  const { data } = await api.get(`/site/${getCodigoAcesso()}/promocoes`);
  return data;
}

export async function validarCupom(codigo: string, subtotal: number) {
  const { data } = await api.post(`/site/${getCodigoAcesso()}/validar-cupom`, { codigo, subtotal });
  return data;
}

export default api;
