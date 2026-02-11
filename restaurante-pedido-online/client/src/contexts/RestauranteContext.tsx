/**
 * RestauranteContext — Contexto global do restaurante.
 *
 * Provê siteInfo (nome, cores, horário, etc) para todos os componentes via useRestaurante().
 * Internamente usa React Query (useSiteInfo) para cache automático com staleTime de 60 min.
 * CSS variables --cor-primaria, --cor-secundaria e tokens de tema são aplicadas ao :root via useEffect.
 * Presets de cores por tipo_restaurante garantem visual adequado mesmo sem customização.
 */

import React, { createContext, useContext, useEffect } from "react";
import { useSiteInfo } from "@/hooks/useQueries";

// Tipos baseados na resposta da API /site/{codigo_acesso}
export interface SiteInfo {
  restaurante_id: number;
  codigo_acesso: string;
  nome_fantasia: string;
  telefone: string;
  endereco_completo: string;
  tipo_restaurante: string;
  tema_cor_primaria: string;
  tema_cor_secundaria: string;
  logo_url: string | null;
  banner_principal_url: string | null;
  whatsapp_numero: string | null;
  whatsapp_ativo: boolean;
  whatsapp_mensagem_padrao: string | null;
  pedido_minimo: number;
  tempo_entrega_estimado: number;
  tempo_retirada_estimado: number;
  aceita_dinheiro: boolean;
  aceita_cartao: boolean;
  aceita_pix: boolean;
  aceita_vale_refeicao: boolean;
  aceita_agendamento: boolean;
  status_aberto: boolean;
  horario_abertura: string;
  horario_fechamento: string;
  dias_semana_abertos: string[];
}

interface ThemePreset {
  primary: string;
  secondary: string;
}

/**
 * Retorna cores padrão por tipo de restaurante.
 * As cores da API (tema_cor_primaria/secundaria) sempre têm prioridade.
 */
function getThemePreset(tipo: string): ThemePreset {
  const t = (tipo || "").toLowerCase();
  if (t.includes("pizza")) return { primary: "#E31A24", secondary: "#FFD700" };
  if (t.includes("hambur") || t.includes("lanch")) return { primary: "#FF6B00", secondary: "#FFD700" };
  if (t.includes("sushi") || t.includes("japon")) return { primary: "#1A1A2E", secondary: "#E94560" };
  if (t.includes("acai") || t.includes("sorvet")) return { primary: "#7B2D8E", secondary: "#FF69B4" };
  if (t.includes("esfih")) return { primary: "#D4A017", secondary: "#8B4513" };
  if (t.includes("bebid")) return { primary: "#1565C0", secondary: "#42A5F5" };
  if (t.includes("salgad") || t.includes("doce")) return { primary: "#E65100", secondary: "#FFB74D" };
  if (t.includes("churrasco") || t.includes("grill")) return { primary: "#B71C1C", secondary: "#FF8A65" };
  if (t.includes("padaria") || t.includes("cafe")) return { primary: "#795548", secondary: "#D7CCC8" };
  if (t.includes("fitness") || t.includes("sauda")) return { primary: "#2E7D32", secondary: "#81C784" };
  if (t.includes("marmitex") || t.includes("marmita")) return { primary: "#E65100", secondary: "#FFA726" };
  if (t.includes("restaurante") || t.includes("geral")) return { primary: "#2E7D32", secondary: "#FFD700" };
  return { primary: "#E31A24", secondary: "#FFD700" };
}

interface RestauranteContextType {
  siteInfo: SiteInfo | null;
  loading: boolean;
  error: string | null;
  codigoAcesso: string;
}

const RestauranteContext = createContext<RestauranteContextType | undefined>(undefined);

export function RestauranteProvider({ children }: { children: React.ReactNode }) {
  const codigoAcesso = (window as any).RESTAURANTE_CODIGO || "demo";

  // React Query gerencia cache, retry e revalidação automaticamente.
  // staleTime: 60min (definido em useQueries.ts).
  const { data: siteInfo, isLoading, error: queryError } = useSiteInfo();

  // Aplica CSS variables do tema ao :root sempre que siteInfo muda.
  // Usa presets por tipo_restaurante como fallback. API colors têm prioridade.
  useEffect(() => {
    if (siteInfo) {
      const root = document.documentElement;
      const preset = getThemePreset(siteInfo.tipo_restaurante);

      // Cores do restaurante (API > preset > fallback)
      const primary = siteInfo.tema_cor_primaria || preset.primary;
      const secondary = siteInfo.tema_cor_secundaria || preset.secondary;

      root.style.setProperty("--cor-primaria", primary);
      root.style.setProperty("--cor-secundaria", secondary);

      // Atualiza shadcn accent/primary/ring para match
      root.style.setProperty("--primary", primary);
      root.style.setProperty("--accent", primary);
      root.style.setProperty("--ring", primary);
    }
  }, [siteInfo]);

  // Formata mensagem de erro amigável a partir do erro do React Query
  const errorMsg = queryError
    ? (queryError as any)?.response?.data?.detail || "Erro ao carregar dados do restaurante"
    : null;

  return (
    <RestauranteContext.Provider value={{
      siteInfo: siteInfo ?? null,
      loading: isLoading,
      error: errorMsg,
      codigoAcesso,
    }}>
      {children}
    </RestauranteContext.Provider>
  );
}

export function useRestaurante() {
  const context = useContext(RestauranteContext);
  if (!context) {
    throw new Error("useRestaurante deve ser usado dentro de RestauranteProvider");
  }
  return context;
}
