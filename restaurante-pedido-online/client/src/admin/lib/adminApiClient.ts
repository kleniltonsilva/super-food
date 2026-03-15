import axios from "axios";

const adminApi = axios.create({
  baseURL: "/",
  headers: { "Content-Type": "application/json" },
});

// Request interceptor — adiciona JWT do admin
adminApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("sf_admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor — 401 remove token e dispara StorageEvent
adminApi.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      const url = err.config?.url || "";
      if (!url.includes("/auth/restaurante/login")) {
        localStorage.removeItem("sf_admin_token");
        localStorage.removeItem("sf_admin_restaurante");
        window.dispatchEvent(
          new StorageEvent("storage", { key: "sf_admin_token", newValue: null })
        );
      }
    }
    return Promise.reject(err);
  }
);

// ─── Auth ──────────────────────────────────────────────
export async function loginRestaurante(email: string, senha: string) {
  const { data } = await adminApi.post("/auth/restaurante/login", { email, senha });
  return data;
}

export async function getMe() {
  const { data } = await adminApi.get("/auth/restaurante/me");
  return data;
}

export async function atualizarPerfil(payload: Record<string, unknown>) {
  const { data } = await adminApi.put("/auth/restaurante/perfil", payload);
  return data;
}

export async function alterarSenha(senha_atual: string, nova_senha: string) {
  const { data } = await adminApi.put("/auth/restaurante/senha", { senha_atual, nova_senha });
  return data;
}

// ─── Dashboard ─────────────────────────────────────────
export async function getDashboard() {
  const { data } = await adminApi.get("/painel/dashboard");
  return data;
}

export async function getDashboardGrafico(periodo?: string) {
  const { data } = await adminApi.get("/painel/dashboard/grafico", {
    params: periodo ? { periodo } : undefined,
  });
  return data;
}

// ─── Pedidos ───────────────────────────────────────────
export async function getPedidos(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/pedidos", { params });
  return data;
}

export async function getPedido(id: number) {
  const { data } = await adminApi.get(`/painel/pedidos/${id}`);
  return data;
}

export async function criarPedido(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/pedidos", payload);
  return data;
}

export async function atualizarStatusPedido(id: number, status: string) {
  const { data } = await adminApi.put(`/painel/pedidos/${id}/status`, { status });
  return data;
}

export async function despacharPedido(id: number, motoboy_id?: number) {
  const body = motoboy_id ? { motoboy_id } : {};
  const { data } = await adminApi.post(`/painel/pedidos/${id}/despachar`, body);
  return data;
}

export async function cancelarPedido(id: number, senha?: string) {
  const { data } = await adminApi.put(`/painel/pedidos/${id}/cancelar`, { senha });
  return data;
}

// ─── Categorias ────────────────────────────────────────
export async function getCategorias() {
  const { data } = await adminApi.get("/painel/categorias");
  return data;
}

export async function criarCategoria(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/categorias", payload);
  return data;
}

export async function atualizarCategoria(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/categorias/${id}`, payload);
  return data;
}

export async function deletarCategoria(id: number) {
  const { data } = await adminApi.delete(`/painel/categorias/${id}`);
  return data;
}

export async function reordenarCategorias(ids: number[]) {
  const { data } = await adminApi.put("/painel/categorias/reordenar", { ids });
  return data;
}

// ─── Produtos ──────────────────────────────────────────
export async function getProdutos(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/produtos", { params });
  return data;
}

export async function getProduto(id: number) {
  const { data } = await adminApi.get(`/painel/produtos/${id}`);
  return data;
}

export async function criarProduto(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/produtos", payload);
  return data;
}

export async function atualizarProduto(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/produtos/${id}`, payload);
  return data;
}

export async function deletarProduto(id: number) {
  const { data } = await adminApi.delete(`/painel/produtos/${id}`);
  return data;
}

export async function toggleDisponibilidade(id: number, disponivel: boolean) {
  const { data } = await adminApi.put(`/painel/produtos/${id}/disponibilidade`, { disponivel });
  return data;
}

// ─── Variações ─────────────────────────────────────────
export async function getVariacoes(produtoId: number) {
  const { data } = await adminApi.get(`/painel/produtos/${produtoId}/variacoes`);
  return data;
}

export async function criarVariacao(produtoId: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.post(`/painel/produtos/${produtoId}/variacoes`, payload);
  return data;
}

export async function atualizarVariacao(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/variacoes/${id}`, payload);
  return data;
}

export async function deletarVariacao(id: number) {
  const { data } = await adminApi.delete(`/painel/variacoes/${id}`);
  return data;
}

export async function aplicarMaxSabores(payload: { nome_tamanho: string; max_sabores: number }) {
  const { data } = await adminApi.put("/painel/variacoes/aplicar-max-sabores", payload);
  return data;
}

// ─── Combos ────────────────────────────────────────────
export async function getCombos() {
  const { data } = await adminApi.get("/painel/combos");
  return data;
}

export async function criarCombo(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/combos", payload);
  return data;
}

export async function atualizarCombo(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/combos/${id}`, payload);
  return data;
}

export async function deletarCombo(id: number) {
  const { data } = await adminApi.delete(`/painel/combos/${id}`);
  return data;
}

// ─── Motoboys ──────────────────────────────────────────
export async function getMotoboys() {
  const { data } = await adminApi.get("/painel/motoboys");
  return data;
}

export async function criarMotoboy(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/motoboys", payload);
  return data;
}

export async function atualizarMotoboy(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/motoboys/${id}`, payload);
  return data;
}

export async function deletarMotoboy(id: number) {
  const { data } = await adminApi.delete(`/painel/motoboys/${id}`);
  return data;
}

export async function atualizarHierarquia(id: number, ordem: number) {
  const { data } = await adminApi.put(`/painel/motoboys/${id}/hierarquia`, { ordem });
  return data;
}

export async function getRankingMotoboys() {
  const { data } = await adminApi.get("/painel/motoboys/ranking");
  return data;
}

export async function getSolicitacoesMotoboys() {
  const { data } = await adminApi.get("/painel/motoboys/solicitacoes");
  return data;
}

export async function responderSolicitacao(id: number, payload: { aprovado: boolean }) {
  const { data } = await adminApi.put(`/painel/motoboys/solicitacoes/${id}`, {
    acao: payload.aprovado ? "aprovar" : "rejeitar",
  });
  return data;
}

// ─── Caixa ─────────────────────────────────────────────
export async function getCaixaAtual() {
  const { data } = await adminApi.get("/painel/caixa/atual");
  return data;
}

export async function abrirCaixa(valor_inicial: number) {
  const { data } = await adminApi.post("/painel/caixa/abrir", { valor_abertura: valor_inicial });
  return data;
}

export async function registrarMovimentacao(payload: {
  tipo: string;
  valor: number;
  descricao?: string;
}) {
  const { data } = await adminApi.post("/painel/caixa/movimentacao", payload);
  return data;
}

export async function fecharCaixa(valor_contado: number) {
  const { data } = await adminApi.post("/painel/caixa/fechar", { valor_contado });
  return data;
}

export async function getHistoricoCaixa(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/caixa/historico", { params });
  return data;
}

// ─── Configurações ─────────────────────────────────────
export async function getConfig() {
  const { data } = await adminApi.get("/painel/config");
  return data;
}

export async function atualizarConfig(payload: Record<string, unknown>) {
  const { data } = await adminApi.put("/painel/config", payload);
  return data;
}

export async function getConfigSite() {
  const { data } = await adminApi.get("/painel/config/site");
  return data;
}

export async function atualizarConfigSite(payload: Record<string, unknown>) {
  const { data } = await adminApi.put("/painel/config/site", payload);
  return data;
}

// ─── Bairros ───────────────────────────────────────────
export async function getBairros() {
  const { data } = await adminApi.get("/painel/bairros");
  return data;
}

export async function criarBairro(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/bairros", payload);
  return data;
}

export async function atualizarBairro(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/bairros/${id}`, payload);
  return data;
}

export async function deletarBairro(id: number) {
  const { data } = await adminApi.delete(`/painel/bairros/${id}`);
  return data;
}

// ─── Promoções ─────────────────────────────────────────
export async function getPromocoes() {
  const { data } = await adminApi.get("/painel/promocoes");
  return data;
}

export async function criarPromocao(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/promocoes", payload);
  return data;
}

export async function atualizarPromocao(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/promocoes/${id}`, payload);
  return data;
}

export async function deletarPromocao(id: number) {
  const { data } = await adminApi.delete(`/painel/promocoes/${id}`);
  return data;
}

// ─── Fidelidade ────────────────────────────────────────
export async function getPremios() {
  const { data } = await adminApi.get("/painel/fidelidade/premios");
  return data;
}

export async function criarPremio(payload: Record<string, unknown>) {
  const { data } = await adminApi.post("/painel/fidelidade/premios", payload);
  return data;
}

export async function atualizarPremio(id: number, payload: Record<string, unknown>) {
  const { data } = await adminApi.put(`/painel/fidelidade/premios/${id}`, payload);
  return data;
}

export async function deletarPremio(id: number) {
  const { data } = await adminApi.delete(`/painel/fidelidade/premios/${id}`);
  return data;
}

// ─── Relatórios ────────────────────────────────────────
export async function getRelatorioVendas(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/relatorios/vendas", { params });
  return data;
}

export async function getRelatorioMotoboys(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/relatorios/motoboys", { params });
  return data;
}

export async function getRelatorioProdutos(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/relatorios/produtos", { params });
  return data;
}

// ─── Produtos Modelo ───────────────────────────────────
export async function carregarProdutosModelo() {
  const { data } = await adminApi.post("/painel/produtos/carregar-modelo");
  return data;
}

// ─── Entregas Ativas (tempo real) ─────────────────────
export async function getEntregasAtivas() {
  const { data } = await adminApi.get("/painel/entregas/ativas");
  return data;
}

// ─── Diagnóstico de Tempo ────────────────────────────
export async function getDiagnosticoTempo() {
  const { data } = await adminApi.get("/painel/entregas/diagnostico-tempo");
  return data;
}

export async function ajustarTempoAutomatico(payload: { tempo_entrega_estimado?: number; tempo_retirada_estimado?: number }) {
  const { data } = await adminApi.post("/painel/entregas/ajustar-tempo", payload);
  return data;
}

// ─── Analytics Avançado ────────────────────────────────
export async function getAnalyticsAvancado(params: { periodo?: string; senha: string }) {
  const { data } = await adminApi.get("/painel/relatorios/analytics", { params });
  return data;
}

// ─── Upload ────────────────────────────────────────────
export async function uploadImagem(file: File, tipo: string = "produto") {
  // Obter restaurante_id do localStorage
  const restauranteStr = localStorage.getItem("sf_admin_restaurante");
  let restauranteId = 0;
  if (restauranteStr) {
    try {
      const r = JSON.parse(restauranteStr);
      restauranteId = r.id || 0;
    } catch { /* ignore */ }
  }
  if (!restauranteId) {
    throw new Error("Restaurante não identificado. Faça login novamente.");
  }

  const formData = new FormData();
  formData.append("arquivo", file);
  formData.append("tipo", tipo);
  formData.append("restaurante_id", String(restauranteId));

  const { data } = await adminApi.post("/api/upload/imagem", formData, {
    headers: { "Content-Type": undefined },
  });
  return data;
}
