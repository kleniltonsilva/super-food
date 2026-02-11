/**
 * RestauranteContext — Contexto global do restaurante.
 *
 * Provê siteInfo (nome, cores, horário, etc) para todos os componentes via useRestaurante().
 * Internamente usa React Query (useSiteInfo) para cache automático com staleTime de 60 min.
 * CSS variables --cor-primaria e --cor-secundaria são aplicadas ao :root via useEffect.
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
  // Isso permite que qualquer componente use var(--cor-primaria) sem prop drilling.
  useEffect(() => {
    if (siteInfo) {
      const root = document.documentElement;
      root.style.setProperty("--cor-primaria", siteInfo.tema_cor_primaria || "#E31A24");
      root.style.setProperty("--cor-secundaria", siteInfo.tema_cor_secundaria || "#FFD700");
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
