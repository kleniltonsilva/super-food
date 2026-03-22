import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe } from "@/garcom/lib/garcomApiClient";

export interface GarcomData {
  id: number;
  nome: string;
  login: string;
  modo_secao: string;
  secao_inicio?: number;
  secao_fim?: number;
  avatar_emoji?: string;
  ativo: boolean;
  criado_em?: string;
  mesa_ids: number[];
  restaurante: {
    id: number;
    nome: string;
    nome_fantasia?: string;
    codigo_acesso: string;
    logo_url?: string;
  };
}

interface GarcomAuthContextType {
  garcom: GarcomData | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, garcom: GarcomData) => void;
  logout: () => void;
  refreshGarcom: () => Promise<void>;
}

const GarcomAuthContext = createContext<GarcomAuthContextType>({
  garcom: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshGarcom: async () => {},
});

function getCachedGarcom(): GarcomData | null {
  try {
    const cached = localStorage.getItem("sf_garcom_data");
    if (cached) return JSON.parse(cached);
  } catch {
    localStorage.removeItem("sf_garcom_data");
  }
  return null;
}

export function GarcomAuthProvider({ children }: { children: ReactNode }) {
  const hasToken = !!localStorage.getItem("sf_garcom_token");
  const [garcom, setGarcom] = useState<GarcomData | null>(
    hasToken ? getCachedGarcom() : null
  );
  const [loading, setLoading] = useState(hasToken);

  const loadGarcom = useCallback(async () => {
    const token = localStorage.getItem("sf_garcom_token");
    if (!token) {
      setGarcom(null);
      localStorage.removeItem("sf_garcom_data");
      setLoading(false);
      return;
    }
    try {
      const data = await getMe();
      setGarcom(data);
      localStorage.setItem("sf_garcom_data", JSON.stringify(data));
    } catch {
      localStorage.removeItem("sf_garcom_token");
      localStorage.removeItem("sf_garcom_data");
      setGarcom(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadGarcom();
  }, [loadGarcom]);

  // Sync multi-aba
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_garcom_token") {
        if (e.newValue) {
          loadGarcom();
        } else {
          setGarcom(null);
          localStorage.removeItem("sf_garcom_data");
        }
      }
    }
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadGarcom]);

  const login = useCallback((token: string, garcomData: GarcomData) => {
    localStorage.setItem("sf_garcom_token", token);
    localStorage.setItem("sf_garcom_data", JSON.stringify(garcomData));
    setGarcom(garcomData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("sf_garcom_token");
    localStorage.removeItem("sf_garcom_data");
    setGarcom(null);
  }, []);

  return (
    <GarcomAuthContext.Provider
      value={{
        garcom,
        loading,
        isLoggedIn: !!garcom,
        login,
        logout,
        refreshGarcom: loadGarcom,
      }}
    >
      {children}
    </GarcomAuthContext.Provider>
  );
}

export function useGarcomAuth() {
  return useContext(GarcomAuthContext);
}
