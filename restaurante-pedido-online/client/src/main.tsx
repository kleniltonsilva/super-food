/**
 * Main Entry Point - Super Food Site Cliente
 * Adaptado para consumir API FastAPI ao invés de tRPC
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createRoot } from "react-dom/client";
import App from "./App";
import { RestauranteProvider } from "./contexts/RestauranteContext";
import "./index.css";

// Configuração do React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60, // 1 minuto
    },
    mutations: {
      retry: 0,
    },
  },
});

// Log de erros em queries
queryClient.getQueryCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    const error = event.query.state.error;
    console.error("[API Query Error]", error);
  }
});

// Log de erros em mutations
queryClient.getMutationCache().subscribe(event => {
  if (event.type === "updated" && event.action.type === "error") {
    const error = event.mutation.state.error;
    console.error("[API Mutation Error]", error);
  }
});

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <RestauranteProvider>
      <App />
    </RestauranteProvider>
  </QueryClientProvider>
);
