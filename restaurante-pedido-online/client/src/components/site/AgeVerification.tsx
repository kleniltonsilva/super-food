/**
 * AgeVerification.tsx — Modal de verificação de idade.
 *
 * Exibido no primeiro acesso para restaurantes do tipo "Bebidas".
 * Pergunta se o cliente é maior de 18 anos.
 * Armazena resposta no sessionStorage para não perguntar novamente.
 */

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { useRestauranteTheme } from "@/contexts/RestauranteContext";

interface AgeVerificationProps {
  onConfirm: () => void;
}

export default function AgeVerification({ onConfirm }: AgeVerificationProps) {
  const theme = useRestauranteTheme();

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div
        className="rounded-2xl p-8 max-w-sm w-full mx-4 text-center shadow-2xl"
        style={{ background: theme.colors.cardBg, border: `2px solid ${theme.colors.primary}` }}
      >
        <div className="text-6xl mb-4">{"🍺"}</div>
        <h2
          className="text-xl font-bold mb-2"
          style={{ color: theme.colors.textPrimary, fontFamily: theme.fonts.heading }}
        >
          Verificação de Idade
        </h2>
        <p className="text-sm mb-6" style={{ color: theme.colors.textSecondary }}>
          Este estabelecimento vende bebidas alcoólicas.
          Você confirma que é maior de 18 anos?
        </p>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="flex-1"
            onClick={() => window.history.back()}
            style={{ borderColor: theme.colors.cardBorder, color: theme.colors.textSecondary }}
          >
            Não, sou menor
          </Button>
          <Button
            className="flex-1 text-white"
            onClick={onConfirm}
            style={{ background: theme.colors.primary }}
          >
            Sim, sou maior de 18
          </Button>
        </div>
      </div>
    </div>
  );
}

/**
 * Hook que controla a exibição do modal de verificação de idade.
 * Só exibe para tipo "bebidas" e se o usuário ainda não confirmou nesta sessão.
 */
export function useAgeVerification(tipoRestaurante: string): {
  needsVerification: boolean;
  confirmAge: () => void;
} {
  const [verified, setVerified] = useState(() => {
    return sessionStorage.getItem("age_verified") === "true";
  });

  const isBebidas = (tipoRestaurante || "").toLowerCase().includes("bebid");

  return {
    needsVerification: isBebidas && !verified,
    confirmAge: () => {
      sessionStorage.setItem("age_verified", "true");
      setVerified(true);
    },
  };
}
