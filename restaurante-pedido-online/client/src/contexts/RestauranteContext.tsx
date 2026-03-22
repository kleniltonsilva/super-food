/**
 * RestauranteContext — Contexto global do restaurante.
 *
 * Provê siteInfo (nome, cores, horário, etc) para todos os componentes via useRestaurante().
 * Internamente usa React Query (useSiteInfo) para cache automático com staleTime de 60 min.
 * CSS variables são aplicadas ao :root via useEffect usando themeConfig.ts.
 *
 * useRestauranteTheme() retorna a configuração completa do tema (cores, fontes, isDark, etc).
 */

import React, { createContext, useContext, useEffect, useMemo } from "react";
import { useSiteInfo } from "@/hooks/useQueries";
import { getThemeConfig, themeToCSSVars, type ThemeConfig } from "@/config/themeConfig";
import { setSentryRestaurante } from "@/lib/sentry";

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
  modo_preco_pizza?: string;
  ingredientes_adicionais_pizza?: Array<{ nome: string; preco: number }>;
  pedidos_online_ativos: boolean;
  entregas_ativas: boolean;
  controle_pedidos_motivo?: string;
  billing_suspenso?: boolean;
  is_demo?: boolean;
}

interface RestauranteContextType {
  siteInfo: SiteInfo | null;
  loading: boolean;
  error: string | null;
  codigoAcesso: string;
  theme: ThemeConfig;
}

const RestauranteContext = createContext<RestauranteContextType | undefined>(undefined);

export function RestauranteProvider({ children }: { children: React.ReactNode }) {
  const codigoAcesso = (window as any).RESTAURANTE_CODIGO || "demo";

  // React Query gerencia cache, retry e revalidação automaticamente.
  // staleTime: 60min (definido em useQueries.ts).
  const { data: siteInfo, isLoading, error: queryError } = useSiteInfo();

  // Resolve o tema completo baseado no tipo_restaurante
  const theme = useMemo(() => {
    return getThemeConfig(siteInfo?.tipo_restaurante || "restaurante");
  }, [siteInfo?.tipo_restaurante]);

  // Seta tags do restaurante no Sentry para rastreamento de erros
  useEffect(() => {
    if (siteInfo) {
      setSentryRestaurante(codigoAcesso, siteInfo.nome_fantasia, siteInfo.restaurante_id);
    }
  }, [siteInfo, codigoAcesso]);

  // Aplica CSS variables do tema ao :root sempre que siteInfo ou tema mudam.
  // Cores customizadas do restaurante (API) sempre têm prioridade sobre o preset.
  useEffect(() => {
    if (!siteInfo) return;

    const root = document.documentElement;
    const cssVars = themeToCSSVars(
      theme,
      siteInfo.tema_cor_primaria || undefined,
      siteInfo.tema_cor_secundaria || undefined,
    );

    // Aplica todas as CSS vars ao :root
    for (const [key, value] of Object.entries(cssVars)) {
      root.style.setProperty(key, value);
    }

    // Font families no body
    document.body.style.fontFamily = theme.fonts.special || theme.fonts.body;

    // Classe utilitária no body para temas escuros
    if (theme.isDark) {
      root.classList.add("theme-dark");
      root.classList.remove("theme-light");
    } else {
      root.classList.add("theme-light");
      root.classList.remove("theme-dark");
    }

    // Classe do tipo de tema para CSS específico
    root.dataset.theme = theme.id;

    return () => {
      // Cleanup ao desmontar
      for (const key of Object.keys(cssVars)) {
        root.style.removeProperty(key);
      }
      root.classList.remove("theme-dark", "theme-light");
      delete root.dataset.theme;
      document.body.style.fontFamily = "";
    };
  }, [siteInfo, theme]);

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
      theme,
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

/**
 * Hook que retorna apenas a configuração do tema.
 * Atalho para useRestaurante().theme.
 */
export function useRestauranteTheme(): ThemeConfig {
  const { theme } = useRestaurante();
  return theme;
}
