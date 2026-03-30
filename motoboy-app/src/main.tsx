/**
 * Entry point do app Derekh Entregador nativo (Capacitor)
 *
 * Importa o MotoboyApp do monorepo e adiciona camada nativa:
 * - GPS background com foreground service
 * - Auto-update checker
 * - Providers (QueryClient, etc)
 */
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

// CSS do monorepo (Tailwind + temas)
import "@/index.css";

// Registro GPS nativo (solicita permissões ao iniciar)
import { registerNativeGPS } from "./native/gps-native";

// App wrapper com update checker
import App from "./App";

// Inicializa GPS nativo (no-op se não estiver no Capacitor)
registerNativeGPS();

// QueryClient compartilhado
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>
);
