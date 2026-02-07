/**
 * Contexto do Restaurante
 * Gerencia o código do restaurante e informações globais do site
 */
import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { setRestauranteCodigo, getRestauranteCodigo, getSiteInfo } from '@/lib/apiClient';

interface SiteInfo {
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
  codigo: string | null;
  siteInfo: SiteInfo | null;
  loading: boolean;
  error: string | null;
  restauranteId: number | null;
}

const RestauranteContext = createContext<RestauranteContextType>({
  codigo: null,
  siteInfo: null,
  loading: true,
  error: null,
  restauranteId: null,
});

export function useRestaurante() {
  return useContext(RestauranteContext);
}

interface RestauranteProviderProps {
  children: ReactNode;
}

export function RestauranteProvider({ children }: RestauranteProviderProps) {
  const [codigo, setCodigo] = useState<string | null>(null);
  const [siteInfo, setSiteInfo] = useState<SiteInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Extrai código da URL
    const params = new URLSearchParams(window.location.search);
    const codigoUrl = params.get('restaurante');

    if (codigoUrl) {
      setCodigo(codigoUrl);
      setRestauranteCodigo(codigoUrl);

      // Busca informações do site
      getSiteInfo()
        .then((info) => {
          setSiteInfo(info);
          setLoading(false);

          // Aplica cores do tema
          if (info.tema_cor_primaria) {
            document.documentElement.style.setProperty('--primary', info.tema_cor_primaria);
          }
          if (info.tema_cor_secundaria) {
            document.documentElement.style.setProperty('--secondary', info.tema_cor_secundaria);
          }

          // Atualiza título da página
          document.title = info.nome_fantasia;
        })
        .catch((err) => {
          console.error('Erro ao carregar site:', err);
          setError('Restaurante não encontrado ou indisponível');
          setLoading(false);
        });
    } else {
      setError('Código do restaurante não informado');
      setLoading(false);
    }
  }, []);

  return (
    <RestauranteContext.Provider
      value={{
        codigo,
        siteInfo,
        loading,
        error,
        restauranteId: siteInfo?.restaurante_id ?? null,
      }}
    >
      {children}
    </RestauranteContext.Provider>
  );
}
