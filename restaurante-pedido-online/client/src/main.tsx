import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

/**
 * QueryClient com configuração profissional de cache.
 *
 * staleTime: tempo que o dado é considerado "fresco" (não re-busca).
 * gcTime: tempo que o dado fica em memória após não ter observers (garbage collection).
 * refetchOnWindowFocus: revalida dados ao voltar na aba do navegador.
 * refetchOnReconnect: revalida ao reconectar internet (ex: mobile saindo de túnel).
 *
 * Valores específicos por tipo de dado são definidos em hooks/useQueries.ts.
 */
const queryClient = new QueryClient({
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
