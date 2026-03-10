import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe } from "@/motoboy/lib/motoboyApiClient";

export interface MotoboyData {
  id: number;
  nome: string;
  usuario: string;
  telefone: string;
  cpf?: string;
  status: string;
  disponivel: boolean;
  em_rota: boolean;
  entregas_pendentes: number;
  ordem_hierarquia: number;
  capacidade_entregas: number;
  total_entregas: number;
  total_ganhos: number;
  total_km: number;
  latitude_atual?: number;
  longitude_atual?: number;
  ultima_atualizacao_gps?: string;
  ultimo_status_online?: string;
  ultima_entrega_em?: string;
  data_cadastro?: string;
  restaurante: {
    id: number;
    nome: string;
    nome_fantasia?: string;
    codigo_acesso: string;
    telefone?: string;
    endereco_completo?: string;
    logo_url?: string;
    latitude?: number;
    longitude?: number;
  };
}

interface MotoboyAuthContextType {
  motoboy: MotoboyData | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, motoboy: MotoboyData) => void;
  logout: () => void;
  refreshMotoboy: () => Promise<void>;
}

const MotoboyAuthContext = createContext<MotoboyAuthContextType>({
  motoboy: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshMotoboy: async () => {},
});

function getCachedMotoboy(): MotoboyData | null {
  try {
    const cached = localStorage.getItem("sf_motoboy_data");
    if (cached) return JSON.parse(cached);
  } catch {
    localStorage.removeItem("sf_motoboy_data");
  }
  return null;
}

export function MotoboyAuthProvider({ children }: { children: ReactNode }) {
  const hasToken = !!localStorage.getItem("sf_motoboy_token");
  const [motoboy, setMotoboy] = useState<MotoboyData | null>(
    hasToken ? getCachedMotoboy() : null
  );
  const [loading, setLoading] = useState(hasToken);

  const loadMotoboy = useCallback(async () => {
    const token = localStorage.getItem("sf_motoboy_token");
    if (!token) {
      setMotoboy(null);
      localStorage.removeItem("sf_motoboy_data");
      setLoading(false);
      return;
    }
    try {
      const data = await getMe();
      setMotoboy(data);
      localStorage.setItem("sf_motoboy_data", JSON.stringify(data));
    } catch {
      localStorage.removeItem("sf_motoboy_token");
      localStorage.removeItem("sf_motoboy_data");
      setMotoboy(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMotoboy();
  }, [loadMotoboy]);

  // Sync multi-aba
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_motoboy_token") {
        if (e.newValue) {
          loadMotoboy();
        } else {
          setMotoboy(null);
          localStorage.removeItem("sf_motoboy_data");
        }
      }
    }
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadMotoboy]);

  const login = useCallback((token: string, motoboyData: MotoboyData) => {
    localStorage.setItem("sf_motoboy_token", token);
    localStorage.setItem("sf_motoboy_data", JSON.stringify(motoboyData));
    setMotoboy(motoboyData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("sf_motoboy_token");
    localStorage.removeItem("sf_motoboy_data");
    setMotoboy(null);
  }, []);

  return (
    <MotoboyAuthContext.Provider
      value={{
        motoboy,
        loading,
        isLoggedIn: !!motoboy,
        login,
        logout,
        refreshMotoboy: loadMotoboy,
      }}
    >
      {children}
    </MotoboyAuthContext.Provider>
  );
}

export function useMotoboyAuth() {
  return useContext(MotoboyAuthContext);
}
