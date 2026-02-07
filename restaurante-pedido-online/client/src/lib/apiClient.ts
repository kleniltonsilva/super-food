import axios from "axios";

// Codigo do restaurante injetado pelo servidor
function getCodigoAcesso(): string {
  return (window as any).RESTAURANTE_CODIGO || "demo";
}

// Session ID para carrinho anonimo
function getSessionId(): string {
  let sid = localStorage.getItem("sf_session_id");
  if (!sid) {
    sid = crypto.randomUUID();
    localStorage.setItem("sf_session_id", sid);
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
  const token = localStorage.getItem("sf_token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

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
  bairro?: string;
}) {
  const { data } = await api.post(`/site/${getCodigoAcesso()}/validar-entrega`, payload);
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
  const { data } = await api.get(`/site/${getCodigoAcesso()}/autocomplete-endereco`, { params: { q } });
  return data;
}

// ==================== CARRINHO ====================

export async function getCarrinho() {
  const { data } = await api.get("/carrinho/");
  return data;
}

export async function adicionarAoCarrinho(item: {
  produto_id: number;
  quantidade: number;
  observacao?: string;
  variacoes?: { variacao_id: number; quantidade?: number }[];
}) {
  const { data } = await api.post("/carrinho/adicionar", {
    ...item,
    codigo_acesso: getCodigoAcesso(),
  });
  return data;
}

export async function atualizarQuantidade(itemIndex: number, quantidade: number) {
  const { data } = await api.put(`/carrinho/atualizar-quantidade/${itemIndex}`, { quantidade });
  return data;
}

export async function removerDoCarrinho(itemIndex: number) {
  const { data } = await api.delete(`/carrinho/remover/${itemIndex}`);
  return data;
}

export async function limparCarrinho() {
  const { data } = await api.delete("/carrinho/limpar");
  return data;
}

export async function finalizarPedido(payload: {
  tipo_entrega: "delivery" | "retirada";
  endereco_id?: number;
  forma_pagamento: string;
  troco_para?: number;
  cupom_codigo?: string;
  observacao?: string;
}) {
  const { data } = await api.post("/carrinho/finalizar", {
    ...payload,
    codigo_acesso: getCodigoAcesso(),
  });
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
