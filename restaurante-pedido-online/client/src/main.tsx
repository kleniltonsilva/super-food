import { initSentry } from "./lib/sentry";

// Inicializa Sentry ANTES de qualquer render
initSentry();

import { QueryClient, QueryClientProvider, MutationCache } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import { toast } from "sonner";
import App from "./App";
import "./index.css";

/**
 * Extrai mensagem de erro amigável de um erro de mutation.
 * Prioriza `detail` do backend FastAPI, fallback para mensagem genérica.
 */
function extractErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const resp = (error as any).response;
    if (resp?.data?.detail) {
      // FastAPI retorna { detail: "mensagem" } ou { detail: [{msg: "..."}] }
      const detail = resp.data.detail;
      if (typeof detail === "string") return detail;
      if (Array.isArray(detail) && detail.length > 0) {
        return detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join("; ");
      }
      return JSON.stringify(detail);
    }
    if (resp?.status === 413) return "Arquivo muito grande";
    if (resp?.status === 422) return "Dados inválidos — verifique os campos";
    if (resp?.status === 500) return "Erro interno do servidor";
  }
  if (error instanceof Error) return error.message;
  return "Ocorreu um erro inesperado";
}

/**
 * QueryClient com configuração profissional de cache.
 *
 * staleTime: tempo que o dado é considerado "fresco" (não re-busca).
 * gcTime: tempo que o dado fica em memória após não ter observers (garbage collection).
 * refetchOnWindowFocus: revalida dados ao voltar na aba do navegador.
 * refetchOnReconnect: revalida ao reconectar internet (ex: mobile saindo de túnel).
 *
 * MutationCache.onError: feedback global — mostra toast.error para TODA mutation que falhar,
 * exceto se a mutation já define seu próprio onError (via meta.suppressGlobalError).
 *
 * Valores específicos por tipo de dado são definidos em hooks/useQueries.ts.
 */
const queryClient = new QueryClient({
  mutationCache: new MutationCache({
    onError: (error, _variables, _context, mutation) => {
      // Permite que mutations individuais suprimam o toast global
      if (mutation.options.meta?.suppressGlobalError) return;
      toast.error(extractErrorMessage(error));
    },
  }),
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,        // 5 min padrão — dados semi-estáveis
      gcTime: 30 * 60 * 1000,           // 30 min — mantém cache em memória
      refetchOnWindowFocus: true,        // Revalida ao voltar na aba
      refetchOnReconnect: true,          // Revalida ao reconectar internet
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <App />
  </QueryClientProvider>
);

// Registrar Service Worker (PWA Entregador)
if ("serviceWorker" in navigator && window.location.pathname.startsWith("/entregador")) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // SW registration failed — app works without it
    });
  });
}

// Registrar Service Worker (PWA Site Cliente)
if ("serviceWorker" in navigator && window.location.pathname.startsWith("/cliente/")) {
  window.addEventListener("load", () => {
    const parts = window.location.pathname.split("/");
    const scope = "/" + parts.slice(1, 3).join("/") + "/";
    navigator.serviceWorker.register("/sw-cliente.js", { scope }).catch(() => {});
  });
}
