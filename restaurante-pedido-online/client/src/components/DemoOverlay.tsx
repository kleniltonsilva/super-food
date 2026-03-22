import { useState, useEffect, useCallback } from "react";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useLocation } from "wouter";
import { ChevronDown, X } from "lucide-react";

/**
 * DemoOverlay — Chip contextual discreto para visitantes demo.
 *
 * Em vez de um painel grande que atrapalha, mostra um pequeno chip
 * no topo da tela com uma dica breve baseada na etapa atual.
 * Funciona bem no mobile sem bloquear conteúdo.
 */

const HINTS: Record<string, { emoji: string; text: string }> = {
  home: { emoji: "👆", text: "Toque em um produto para explorar" },
  product: { emoji: "🛒", text: "Adicione ao carrinho para testar" },
  cart: { emoji: "✅", text: "Finalize — é só demonstração!" },
  checkout: { emoji: "✅", text: "Complete o pedido de teste!" },
  order: { emoji: "🚀", text: "Veja o pedido avançar em tempo real!" },
  tracking: { emoji: "📍", text: "Acompanhe o motoboy no mapa GPS!" },
};

function detectHintKey(path: string): string {
  if (/^\/order/.test(path)) return "order";
  if (/^\/tracking/.test(path)) return "tracking";
  if (/^\/checkout/.test(path)) return "checkout";
  if (/^\/cart/.test(path)) return "cart";
  if (/^\/product\//.test(path)) return "product";
  return "home";
}

export default function DemoOverlay() {
  const { siteInfo } = useRestaurante();
  const [location] = useLocation();
  const [dismissed, setDismissed] = useState(false);
  const [visible, setVisible] = useState(true);

  // Hooks ANTES de qualquer return condicional
  useEffect(() => {
    if (sessionStorage.getItem("demo_dismissed") === "true") {
      setDismissed(true);
    }
  }, []);

  // Auto-hide após 8 segundos, reaparece ao mudar de rota
  useEffect(() => {
    setVisible(true);
    const timer = setTimeout(() => setVisible(false), 8000);
    return () => clearTimeout(timer);
  }, [location]);

  const handleDismiss = useCallback(() => {
    setDismissed(true);
    sessionStorage.setItem("demo_dismissed", "true");
  }, []);

  // Não mostra se não é demo ou já dispensou
  if (!siteInfo?.is_demo || dismissed) return null;

  const hintKey = detectHintKey(location);
  const hint = HINTS[hintKey];

  return (
    <>
      {/* Chip discreto no topo */}
      <div
        className={`fixed top-2 left-1/2 -translate-x-1/2 z-[9998] transition-all duration-500 ${
          visible
            ? "opacity-100 translate-y-0"
            : "opacity-0 -translate-y-4 pointer-events-none"
        }`}
      >
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full shadow-lg text-white text-xs font-medium backdrop-blur-md border border-white/20"
          style={{ background: "rgba(0, 0, 0, 0.75)" }}
        >
          {/* Badge "DEMO" */}
          <span
            className="px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider"
            style={{ background: "linear-gradient(135deg, #EA580C, #F97316)" }}
          >
            Demo
          </span>

          {/* Dica contextual */}
          <span className="whitespace-nowrap">
            {hint.emoji} {hint.text}
          </span>

          {/* Botão fechar */}
          <button
            onClick={handleDismiss}
            className="ml-1 p-0.5 rounded-full hover:bg-white/20 transition-colors"
            title="Fechar dicas"
          >
            <X className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Botão discreto para reabrir quando chip desaparece */}
      {!visible && (
        <button
          onClick={() => setVisible(true)}
          className="fixed top-2 right-2 z-[9997] flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-bold text-white/70 hover:text-white transition-all"
          style={{ background: "rgba(0, 0, 0, 0.5)" }}
        >
          <ChevronDown className="w-3 h-3" />
          Demo
        </button>
      )}
    </>
  );
}
