import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe } from "@/admin/lib/adminApiClient";

export interface Restaurante {
  id: number;
  nome: string;
  email: string;
  telefone?: string;
  tipo_restaurante?: string;
  logo_url?: string;
  codigo_acesso?: string;
}

interface AdminAuthContextType {
  restaurante: Restaurante | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, restaurante: Restaurante) => void;
  logout: () => void;
  refreshRestaurante: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextType>({
  restaurante: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshRestaurante: async () => {},
});

function getCachedRestaurante(): Restaurante | null {
  try {
    const cached = localStorage.getItem("sf_admin_restaurante");
    if (cached) return JSON.parse(cached);
  } catch {
    localStorage.removeItem("sf_admin_restaurante");
  }
  return null;
}

export function AdminAuthProvider({ children }: { children: ReactNode }) {
  const hasToken = !!localStorage.getItem("sf_admin_token");
  const [restaurante, setRestaurante] = useState<Restaurante | null>(
    hasToken ? getCachedRestaurante() : null
  );
  const [loading, setLoading] = useState(hasToken);

  const loadRestaurante = useCallback(async () => {
    const token = localStorage.getItem("sf_admin_token");
    if (!token) {
      setRestaurante(null);
      localStorage.removeItem("sf_admin_restaurante");
      setLoading(false);
      return;
    }
    try {
      const data = await getMe();
      // Se o backend retornou token renovado, salvar para estender a sessão
      if (data.refreshed_token) {
        localStorage.setItem("sf_admin_token", data.refreshed_token);
      }
      setRestaurante(data);
      localStorage.setItem("sf_admin_restaurante", JSON.stringify(data));
    } catch {
      localStorage.removeItem("sf_admin_token");
      localStorage.removeItem("sf_admin_restaurante");
      setRestaurante(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRestaurante();
  }, [loadRestaurante]);

  // Sync multi-aba
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_admin_token") {
        if (e.newValue) {
          loadRestaurante();
        } else {
          setRestaurante(null);
          localStorage.removeItem("sf_admin_restaurante");
        }
      }
    }
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadRestaurante]);

  const login = useCallback((token: string, restauranteData: Restaurante) => {
    localStorage.setItem("sf_admin_token", token);
    localStorage.setItem("sf_admin_restaurante", JSON.stringify(restauranteData));
    setRestaurante(restauranteData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("sf_admin_token");
    localStorage.removeItem("sf_admin_restaurante");
    setRestaurante(null);
  }, []);

  return (
    <AdminAuthContext.Provider
      value={{
        restaurante,
        loading,
        isLoggedIn: !!restaurante,
        login,
        logout,
        refreshRestaurante: loadRestaurante,
      }}
    >
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  return useContext(AdminAuthContext);
}
