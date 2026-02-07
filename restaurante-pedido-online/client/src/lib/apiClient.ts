/**
 * API Client para Super Food FastAPI
 * Substitui tRPC para consumir a API REST do backend Python
 */
import axios from 'axios';

// URL base da API FastAPI (configurável via env)
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Código do restaurante (extraído da URL ou armazenado)
let restauranteCodigo: string | null = null;

export function setRestauranteCodigo(codigo: string) {
  restauranteCodigo = codigo;
}

export function getRestauranteCodigo(): string | null {
  if (!restauranteCodigo) {
    // Tenta de window (injetado pelo FastAPI)
    restauranteCodigo = (window as any).RESTAURANTE_CODIGO;
    // Fallback: URL query param
    if (!restauranteCodigo) {
      const params = new URLSearchParams(window.location.search);
      restauranteCodigo = params.get('restaurante');
    }
    // Fallback: path /cliente/CODIGO
    if (!restauranteCodigo) {
      const match = window.location.pathname.match(/\/cliente\/([^\/]+)/);
      if (match) restauranteCodigo = match[1];
    }
  }
  return restauranteCodigo;
}

// Instância axios configurada
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor para adicionar token de autenticação
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ==================== SITE INFO ====================
export async function getSiteInfo() {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}`);
  return response.data;
}

// ==================== MENU ====================
export async function getCategorias() {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/categorias`);
  return response.data;
}

export async function getProdutos(params?: {
  categoria_id?: number;
  destaque?: boolean;
  promocao?: boolean;
  busca?: string;
}) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/produtos`, { params });
  return response.data;
}

export async function getProdutoDetalhado(produtoId: number) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/produto/${produtoId}`);
  return response.data;
}

// ==================== BAIRROS ====================
export async function getBairros() {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/bairros`);
  return response.data;
}

export async function getBairroPorNome(nomeBairro: string) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/bairro/${encodeURIComponent(nomeBairro)}`);
  return response.data;
}

// ==================== ENTREGA ====================
export async function validarEntrega(data: {
  endereco_texto?: string;
  latitude?: number;
  longitude?: number;
}) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.post(`/site/${codigo}/validar-entrega`, data);
  return response.data;
}

export async function autocompleteEndereco(query: string) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/autocomplete-endereco`, {
    params: { query },
  });
  return response.data;
}

// ==================== FIDELIDADE ====================
export async function getPontosFidelidade(clienteId: number) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/fidelidade/pontos/${clienteId}`);
  return response.data;
}

export async function getPremiosFidelidade() {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/fidelidade/premios`);
  return response.data;
}

export async function resgatarPremio(clienteId: number, premioId: number) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.post(`/site/${codigo}/fidelidade/resgatar/${clienteId}`, {
    premio_id: premioId,
  });
  return response.data;
}

// ==================== PROMOCOES ====================
export async function getPromocoes() {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.get(`/site/${codigo}/promocoes`);
  return response.data;
}

export async function validarCupom(codigoCupom: string, valorPedido: number) {
  const codigo = getRestauranteCodigo();
  if (!codigo) throw new Error('Código do restaurante não definido');
  const response = await api.post(`/site/${codigo}/validar-cupom`, {
    codigo_cupom: codigoCupom,
    valor_pedido: valorPedido,
  });
  return response.data;
}

// ==================== CARRINHO (via API principal) ====================
export async function getCarrinho(clienteId: number) {
  const codigo = getRestauranteCodigo();
  const response = await api.get(`/carrinho/${clienteId}`, {
    params: { restaurante_codigo: codigo },
  });
  return response.data;
}

export async function adicionarAoCarrinho(data: {
  cliente_id: number;
  produto_id: number;
  quantidade: number;
  variacoes?: number[];
  observacoes?: string;
}) {
  const codigo = getRestauranteCodigo();
  const response = await api.post(`/carrinho/adicionar`, {
    ...data,
    restaurante_codigo: codigo,
  });
  return response.data;
}

export async function atualizarItemCarrinho(itemId: number, quantidade: number) {
  const response = await api.put(`/carrinho/item/${itemId}`, { quantidade });
  return response.data;
}

export async function removerItemCarrinho(itemId: number) {
  const response = await api.delete(`/carrinho/item/${itemId}`);
  return response.data;
}

export async function limparCarrinho(clienteId: number) {
  const response = await api.delete(`/carrinho/${clienteId}/limpar`);
  return response.data;
}

// ==================== PEDIDOS ====================
export async function criarPedido(data: {
  cliente_id: number;
  tipo_entrega: 'entrega' | 'retirada';
  forma_pagamento: string;
  endereco_entrega?: string;
  observacoes?: string;
  cupom_codigo?: string;
}) {
  const codigo = getRestauranteCodigo();
  const response = await api.post(`/pedidos/criar`, {
    ...data,
    restaurante_codigo: codigo,
  });
  return response.data;
}

export async function getPedidosCliente(clienteId: number) {
  const codigo = getRestauranteCodigo();
  const response = await api.get(`/pedidos/cliente/${clienteId}`, {
    params: { restaurante_codigo: codigo },
  });
  return response.data;
}

export async function getPedidoDetalhes(pedidoId: number) {
  const response = await api.get(`/pedidos/${pedidoId}`);
  return response.data;
}

export default api;
