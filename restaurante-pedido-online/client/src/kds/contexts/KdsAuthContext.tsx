import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe } from "@/kds/lib/kdsApiClient";

export interface CozinheiroData {
  id: number;
  nome: string;
  login: string;
  modo: string;
  avatar_emoji?: string;
  ativo: boolean;
  criado_em?: string;
  produto_ids: number[];
  restaurante: {
    id: number;
    nome: string;
    nome_fantasia?: string;
    codigo_acesso: string;
    logo_url?: string;
  };
}

interface KdsAuthContextType {
  cozinheiro: CozinheiroData | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, cozinheiro: CozinheiroData) => void;
  logout: () => void;
  refreshCozinheiro: () => Promise<void>;
}

const KdsAuthContext = createContext<KdsAuthContextType>({
  cozinheiro: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshCozinheiro: async () => {},
});

function getCachedCozinheiro(): CozinheiroData | null {
  try {
    const cached = localStorage.getItem("sf_kds_data");
    if (cached) return JSON.parse(cached);
  } catch {
    localStorage.removeItem("sf_kds_data");
  }
  return null;
}

export function KdsAuthProvider({ children }: { children: ReactNode }) {
  const hasToken = !!localStorage.getItem("sf_kds_token");
  const [cozinheiro, setCozinheiro] = useState<CozinheiroData | null>(
    hasToken ? getCachedCozinheiro() : null
  );
  const [loading, setLoading] = useState(hasToken);

  const loadCozinheiro = useCallback(async () => {
    const token = localStorage.getItem("sf_kds_token");
    if (!token) {
      setCozinheiro(null);
      localStorage.removeItem("sf_kds_data");
      setLoading(false);
      return;
    }
    try {
      const data = await getMe();
      setCozinheiro(data);
      localStorage.setItem("sf_kds_data", JSON.stringify(data));
    } catch {
      localStorage.removeItem("sf_kds_token");
      localStorage.removeItem("sf_kds_data");
      setCozinheiro(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCozinheiro();
  }, [loadCozinheiro]);

  // Sync multi-aba
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_kds_token") {
        if (e.newValue) {
          loadCozinheiro();
        } else {
          setCozinheiro(null);
          localStorage.removeItem("sf_kds_data");
        }
      }
    }
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadCozinheiro]);

  const login = useCallback((token: string, cozinheiroData: CozinheiroData) => {
    localStorage.setItem("sf_kds_token", token);
    localStorage.setItem("sf_kds_data", JSON.stringify(cozinheiroData));
    setCozinheiro(cozinheiroData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("sf_kds_token");
    localStorage.removeItem("sf_kds_data");
    setCozinheiro(null);
  }, []);

  return (
    <KdsAuthContext.Provider
      value={{
        cozinheiro,
        loading,
        isLoggedIn: !!cozinheiro,
        login,
        logout,
        refreshCozinheiro: loadCozinheiro,
      }}
    >
      {children}
    </KdsAuthContext.Provider>
  );
}

export function useKdsAuth() {
  return useContext(KdsAuthContext);
}
