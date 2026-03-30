import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig } from "vite";

// Build separado para o app motoboy nativo — importa do monorepo sem duplicar
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      // Aponta para o código fonte do monorepo
      "@": path.resolve(import.meta.dirname, "..", "restaurante-pedido-online", "client", "src"),
      // Forçar React único — sem isso, componentes do monorepo usam
      // restaurante-pedido-online/node_modules/react (instância diferente)
      // causando "Cannot read properties of null (reading 'useState')"
      "react": path.resolve(import.meta.dirname, "node_modules", "react"),
      "react-dom": path.resolve(import.meta.dirname, "node_modules", "react-dom"),
      "react/jsx-runtime": path.resolve(import.meta.dirname, "node_modules", "react", "jsx-runtime.js"),
      "react/jsx-dev-runtime": path.resolve(import.meta.dirname, "node_modules", "react", "jsx-dev-runtime.js"),
    },
    // Garantia extra: deduplicar pacotes compartilhados
    dedupe: ["react", "react-dom", "@tanstack/react-query", "wouter"],
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, "dist"),
    emptyOutDir: true,
  },
  server: {
    port: 5174,
    proxy: {
      "/site": { target: "http://localhost:8000", changeOrigin: true },
      "/carrinho": { target: "http://localhost:8000", changeOrigin: true },
      "/auth": { target: "http://localhost:8000", changeOrigin: true },
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/static": { target: "http://localhost:8000", changeOrigin: true },
      "/painel": { target: "http://localhost:8000", changeOrigin: true },
      "/motoboy": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
