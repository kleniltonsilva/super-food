import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getMe } from "@/superadmin/lib/superAdminApiClient";

export interface SuperAdminData {
  id: number;
  usuario: string;
  email?: string;
  ativo: boolean;
  criado_em?: string;
}

interface SuperAdminAuthContextType {
  admin: SuperAdminData | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, admin: SuperAdminData) => void;
  logout: () => void;
  refreshAdmin: () => Promise<void>;
}

const SuperAdminAuthContext = createContext<SuperAdminAuthContextType>({
  admin: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshAdmin: async () => {},
});

function getCachedAdmin(): SuperAdminData | null {
  try {
    const cached = localStorage.getItem("sf_superadmin_data");
    if (cached) return JSON.parse(cached);
  } catch {
    localStorage.removeItem("sf_superadmin_data");
  }
  return null;
}

export function SuperAdminAuthProvider({ children }: { children: ReactNode }) {
  const hasToken = !!localStorage.getItem("sf_superadmin_token");
  const [admin, setAdmin] = useState<SuperAdminData | null>(
    hasToken ? getCachedAdmin() : null
  );
  const [loading, setLoading] = useState(hasToken);

  const loadAdmin = useCallback(async () => {
    const token = localStorage.getItem("sf_superadmin_token");
    if (!token) {
      setAdmin(null);
      localStorage.removeItem("sf_superadmin_data");
      setLoading(false);
      return;
    }
    try {
      const data = await getMe();
      setAdmin(data);
      localStorage.setItem("sf_superadmin_data", JSON.stringify(data));
    } catch {
      localStorage.removeItem("sf_superadmin_token");
      localStorage.removeItem("sf_superadmin_data");
      setAdmin(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAdmin();
  }, [loadAdmin]);

  // Sync multi-aba
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_superadmin_token") {
        if (e.newValue) {
          loadAdmin();
        } else {
          setAdmin(null);
          localStorage.removeItem("sf_superadmin_data");
        }
      }
    }
    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadAdmin]);

  const login = useCallback((token: string, adminData: SuperAdminData) => {
    localStorage.setItem("sf_superadmin_token", token);
    localStorage.setItem("sf_superadmin_data", JSON.stringify(adminData));
    setAdmin(adminData);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("sf_superadmin_token");
    localStorage.removeItem("sf_superadmin_data");
    setAdmin(null);
  }, []);

  return (
    <SuperAdminAuthContext.Provider
      value={{
        admin,
        loading,
        isLoggedIn: !!admin,
        login,
        logout,
        refreshAdmin: loadAdmin,
      }}
    >
      {children}
    </SuperAdminAuthContext.Provider>
  );
}

export function useSuperAdminAuth() {
  return useContext(SuperAdminAuthContext);
}
