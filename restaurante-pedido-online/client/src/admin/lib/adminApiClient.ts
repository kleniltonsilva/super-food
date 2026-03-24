import axios from "axios";
import { sentryBreadcrumbFromAxiosError } from "@/lib/sentry";

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
    // Breadcrumb Sentry para erros 5xx
    if (err.response?.status >= 500) {
      sentryBreadcrumbFromAxiosError("admin", err.config?.method || "get", err.config?.url || "", err.response.status);
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

export async function abrirCaixa(payload: {
  valor_abertura: number;
  operador_nome: string;
  senha: string;
  criar_operador?: boolean;
}) {
  const { data } = await adminApi.post("/painel/caixa/abrir", payload);
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

export async function fecharCaixa(payload: {
  valor_contado: number;
  operador_nome: string;
  senha: string;
}) {
  const { data } = await adminApi.post("/painel/caixa/fechar", payload);
  return data;
}

export async function getHistoricoCaixa(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/caixa/historico", { params });
  return data;
}

export async function getOperadoresCaixa() {
  const { data } = await adminApi.get("/painel/caixa/operadores");
  return data;
}

export async function criarOperadorCaixa(payload: { nome: string; senha: string }) {
  const { data } = await adminApi.post("/painel/caixa/operadores", payload);
  return data;
}

export async function deletarOperadorCaixa(id: number, senha: string) {
  const { data } = await adminApi.delete(`/painel/caixa/operadores/${id}`, { params: { senha } });
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

// ─── Autocomplete Endereço ─────────────────────────────
export async function autocompleteEndereco(query: string) {
  const { data } = await adminApi.get("/painel/autocomplete-endereco", { params: { query } });
  return data;
}

// ─── Mesas ────────────────────────────────────────────
export async function getMesas() {
  const { data } = await adminApi.get("/painel/mesas");
  return data;
}

export async function pagarMesa(numero_mesa: string, forma_pagamento?: string) {
  const { data } = await adminApi.post(`/painel/mesas/${encodeURIComponent(numero_mesa)}/pagar`, {
    forma_pagamento,
  });
  return data;
}

export async function adicionarPedidoMesa(
  numero_mesa: string,
  payload: { itens: string; valor_total: number; observacoes?: string; forma_pagamento?: string }
) {
  const { data } = await adminApi.post(`/painel/mesas/${encodeURIComponent(numero_mesa)}/pedido`, payload);
  return data;
}

// ─── Tempo Médio ──────────────────────────────────────
export async function getTempoMedio() {
  const { data } = await adminApi.get("/painel/tempo-medio");
  return data;
}

// ─── Alertas de Atraso ────────────────────────────────
export async function getAlertasAtraso(params?: { periodo?: string; tipo?: string }) {
  const { data } = await adminApi.get("/painel/alertas-atraso", { params });
  return data;
}

// ─── Sugestões de Tempo ──────────────────────────────
export async function getSugestoesTempo() {
  const { data } = await adminApi.get("/painel/sugestoes-tempo/historico");
  return data;
}

export async function rejeitarSugestaoTempo(payload: {
  tipo: string;
  valor_antes: number;
  valor_sugerido: number;
  motivo?: string;
}) {
  const { data } = await adminApi.post("/painel/sugestoes-tempo/rejeitar", payload);
  return data;
}

// ─── Notificações ────────────────────────────────────
export async function getNotificacoes() {
  const { data } = await adminApi.get("/painel/notificacoes");
  return data;
}

export async function marcarNotificacaoLida(id: number) {
  const { data } = await adminApi.put(`/painel/notificacoes/${id}/lida`);
  return data;
}

// ─── Pedido Rápido Mesa ──────────────────────────────
export async function adicionarPedidoMesaRapido(
  numero_mesa: string,
  payload: { itens: Array<{ produto_id: number; quantidade: number; observacao?: string; variacoes?: Array<{ nome: string; preco_adicional: number }> }> }
) {
  const { data } = await adminApi.post(`/painel/mesas/${encodeURIComponent(numero_mesa)}/pedido-rapido`, payload);
  return data;
}

// ─── Billing ────────────────────────────────────────────
export async function getBillingStatus() {
  const { data } = await adminApi.get("/painel/billing/status");
  return data;
}

export async function getFaturas(params?: Record<string, unknown>) {
  const { data } = await adminApi.get("/painel/billing/faturas", { params });
  return data;
}

export async function getFaturaPix(faturaId: number) {
  const { data } = await adminApi.get(`/painel/billing/faturas/${faturaId}/pix`);
  return data;
}

export async function selecionarPlano(payload: { plano: string; ciclo: string; billing_type: string }) {
  const { data } = await adminApi.post("/painel/billing/selecionar-plano", payload);
  return data;
}

export async function getPlanosDisponiveis() {
  const { data } = await adminApi.get("/painel/billing/planos");
  return data;
}

// ─── Upload ────────────────────────────────────────────
// ─── Integrações Marketplace ────────────────────────
export async function getIntegracoes() {
  const { data } = await adminApi.get("/painel/integracoes");
  return data;
}

export async function connectIFood() {
  const { data } = await adminApi.post("/painel/integracoes/ifood/connect");
  return data;
}

export async function getIFoodAuthStatus() {
  const { data } = await adminApi.get("/painel/integracoes/ifood/auth-status");
  return data;
}

export async function disconnectIFood() {
  const { data } = await adminApi.post("/painel/integracoes/ifood/disconnect");
  return data;
}

export async function getIFoodStatus() {
  const { data } = await adminApi.get("/painel/integracoes/ifood/status");
  return data;
}

export async function toggleIntegracao(marketplace: string) {
  const { data } = await adminApi.put(`/painel/integracoes/${marketplace}/toggle`);
  return data;
}

export async function syncCatalogIFood() {
  const { data } = await adminApi.post("/painel/integracoes/ifood/catalog-sync");
  return data;
}

export async function connectOpenDelivery(marketplace: string) {
  const { data } = await adminApi.post(`/painel/integracoes/${marketplace}/connect`);
  return data;
}

export async function disconnectMarketplace(marketplace: string) {
  const { data } = await adminApi.post(`/painel/integracoes/${marketplace}/disconnect`);
  return data;
}

// ==================== KDS / COZINHA DIGITAL ====================

export async function getCozinheiros() {
  const { data } = await adminApi.get("/painel/cozinha/cozinheiros");
  return data;
}

export async function criarCozinheiro(payload: {
  nome: string;
  login: string;
  senha: string;
  modo: string;
  avatar_emoji?: string;
  produto_ids?: number[];
}) {
  const { data } = await adminApi.post("/painel/cozinha/cozinheiros", payload);
  return data;
}

export async function atualizarCozinheiro(
  id: number,
  payload: {
    nome?: string;
    login?: string;
    senha?: string;
    modo?: string;
    avatar_emoji?: string;
    produto_ids?: number[];
  }
) {
  const { data } = await adminApi.put(`/painel/cozinha/cozinheiros/${id}`, payload);
  return data;
}

export async function deletarCozinheiro(id: number) {
  const { data } = await adminApi.delete(`/painel/cozinha/cozinheiros/${id}`);
  return data;
}

export async function getConfigCozinha() {
  const { data } = await adminApi.get("/painel/cozinha/config");
  return data;
}

export async function atualizarConfigCozinha(payload: {
  kds_ativo?: boolean;
  tempo_alerta_min?: number;
  tempo_critico_min?: number;
  som_novo_pedido?: boolean;
}) {
  const { data } = await adminApi.put("/painel/cozinha/config", payload);
  return data;
}

export async function getDashboardCozinha() {
  const { data } = await adminApi.get("/painel/cozinha/dashboard");
  return data;
}

export async function getDesempenhoCozinha(periodo: string = "hoje") {
  const { data } = await adminApi.get(`/painel/cozinha/desempenho?periodo=${periodo}`);
  return data;
}

export async function pausarPedidoCozinha(pedidoId: number) {
  const { data } = await adminApi.post(`/painel/pedidos/${pedidoId}/pausar`);
  return data;
}

export async function despausarPedidoCozinha(pedidoId: number) {
  const { data } = await adminApi.post(`/painel/pedidos/${pedidoId}/despausar`);
  return data;
}

// ==================== GARÇOM ====================

export async function getGarcons() {
  const { data } = await adminApi.get("/painel/garcom/garcons");
  return data;
}

export async function criarGarcom(payload: {
  nome: string; login: string; senha: string;
  modo_secao?: string; secao_inicio?: number; secao_fim?: number;
  avatar_emoji?: string; mesa_ids?: number[];
}) {
  const { data } = await adminApi.post("/painel/garcom/garcons", payload);
  return data;
}

export async function atualizarGarcom(id: number, payload: Record<string, any>) {
  const { data } = await adminApi.put(`/painel/garcom/garcons/${id}`, payload);
  return data;
}

export async function deletarGarcom(id: number) {
  const { data } = await adminApi.delete(`/painel/garcom/garcons/${id}`);
  return data;
}

export async function getConfigGarcom() {
  const { data } = await adminApi.get("/painel/garcom/config");
  return data;
}

export async function atualizarConfigGarcom(payload: Record<string, any>) {
  const { data } = await adminApi.put("/painel/garcom/config", payload);
  return data;
}

export async function getSessoesGarcom() {
  const { data } = await adminApi.get("/painel/garcom/sessoes");
  return data;
}

export async function fecharSessaoGarcom(sessaoId: number) {
  const { data } = await adminApi.post(`/painel/garcom/sessoes/${sessaoId}/fechar`);
  return data;
}

// ==================== PIX ONLINE ====================

export async function getPixConfig() {
  const { data } = await adminApi.get("/painel/pix/status");
  return data;
}

export async function ativarPix(payload: { pix_chave: string; tipo_chave: string; nome: string; termos_aceitos: boolean }) {
  const { data } = await adminApi.post("/painel/pix/ativar", payload);
  return data;
}

export async function desativarPix() {
  const { data } = await adminApi.post("/painel/pix/desativar");
  return data;
}

export async function configSaqueAuto(payload: { saque_automatico: boolean; saque_minimo_centavos: number }) {
  const { data } = await adminApi.put("/painel/pix/config-saque", payload);
  return data;
}

export async function previewSaque(valor_centavos: number) {
  const { data } = await adminApi.post("/painel/pix/sacar", { valor_centavos });
  return data;
}

export async function confirmarSaque(valor_centavos: number) {
  const { data } = await adminApi.post("/painel/pix/sacar/confirmar", { valor_centavos });
  return data;
}

export async function getPixSaques(params?: { limit?: number; offset?: number }) {
  const { data } = await adminApi.get("/painel/pix/saques", { params });
  return data;
}

// ─── Smart Client Lookup ────────────────────────────────
export async function buscarCliente(q: string) {
  const { data } = await adminApi.get("/painel/clientes/buscar", { params: { q } });
  return data;
}

// ─── Bridge Printer ─────────────────────────────────────
export async function getBridgePatterns() {
  const { data } = await adminApi.get("/painel/bridge/patterns");
  return data;
}

export async function deletarBridgePattern(id: number) {
  const { data } = await adminApi.delete(`/painel/bridge/patterns/${id}`);
  return data;
}

export async function getBridgeOrders(params?: { status?: string; limit?: number; offset?: number }) {
  const { data } = await adminApi.get("/painel/bridge/orders", { params });
  return data;
}

export async function criarPedidoFromBridge(intercepted_order_id: number) {
  const { data } = await adminApi.post("/painel/bridge/orders", { intercepted_order_id });
  return data;
}

export async function validarEAprenderBridge(orderId: number, gerarPattern: boolean = true) {
  const { data } = await adminApi.post(`/painel/bridge/orders/${orderId}/validar`, { gerar_pattern: gerarPattern });
  return data;
}

export async function reparseBridgeOrder(orderId: number) {
  const { data } = await adminApi.post(`/painel/bridge/orders/${orderId}/reparse`);
  return data;
}

export async function getBridgeStatus() {
  const { data } = await adminApi.get("/painel/bridge/status");
  return data;
}

export async function criarBridgePattern(payload: {
  plataforma: string;
  nome_pattern?: string;
  regex_detectar: string;
  mapeamento_json: Record<string, string>;
  confianca?: number;
}) {
  const { data } = await adminApi.post("/painel/bridge/patterns", payload);
  return data;
}

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
