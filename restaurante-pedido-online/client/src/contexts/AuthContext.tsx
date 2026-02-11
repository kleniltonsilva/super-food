/**
 * AuthContext — Gerencia autenticação do cliente no site.
 *
 * Estratégias de persistência de sessão:
 *
 * 1. TOKEN (sf_token): JWT armazenado no localStorage.
 *    Sobrevive a reloads e fechamento de aba.
 *
 * 2. CACHE DO CLIENTE (sf_cliente): dados do cliente (nome, email, etc)
 *    armazenados como JSON no localStorage. Permite restaurar o estado
 *    imediatamente no mount (sem flash de UI deslogada) enquanto valida
 *    o token em background com a API.
 *
 * 3. SYNC MULTI-ABA: listener de StorageEvent. Quando uma aba faz login
 *    ou logout (altera sf_token), todas as outras abas recebem o evento
 *    e sincronizam automaticamente.
 *
 * 4. INTERCEPTOR 401: quando a API retorna 401 (token expirado), o
 *    interceptor do apiClient.ts remove o token e dispara StorageEvent,
 *    que é capturado aqui para deslogar o usuário.
 */

import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { getClienteMe } from "@/lib/apiClient";

interface Cliente {
  id: number;
  nome: string;
  email: string;
  telefone: string;
  cpf?: string | null;
}

interface AuthContextType {
  cliente: Cliente | null;
  loading: boolean;
  isLoggedIn: boolean;
  login: (token: string, cliente: Cliente) => void;
  logout: () => void;
  refreshCliente: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  cliente: null,
  loading: true,
  isLoggedIn: false,
  login: () => {},
  logout: () => {},
  refreshCliente: async () => {},
});

/**
 * Tenta restaurar dados do cliente do cache localStorage.
 * Retorna null se não houver cache ou se o JSON for inválido.
 */
function getCachedCliente(): Cliente | null {
  try {
    const cached = localStorage.getItem("sf_cliente");
    if (cached) return JSON.parse(cached);
  } catch {
    // JSON inválido — limpa cache corrompido
    localStorage.removeItem("sf_cliente");
  }
  return null;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Restaura cliente do cache imediatamente (sem esperar API)
  // Isso evita o "flash" de UI deslogada durante o mount
  const hasToken = !!localStorage.getItem("sf_token");
  const [cliente, setCliente] = useState<Cliente | null>(hasToken ? getCachedCliente() : null);
  const [loading, setLoading] = useState(hasToken);

  /**
   * Valida token com a API e atualiza cache local.
   * Se token inválido/expirado, faz cleanup completo.
   */
  const loadCliente = useCallback(async () => {
    const token = localStorage.getItem("sf_token");
    if (!token) {
      setCliente(null);
      localStorage.removeItem("sf_cliente");
      setLoading(false);
      return;
    }

    try {
      const data = await getClienteMe();
      setCliente(data);
      // Atualiza cache para próximos mounts
      localStorage.setItem("sf_cliente", JSON.stringify(data));
    } catch {
      // Token expirado ou inválido — cleanup
      localStorage.removeItem("sf_token");
      localStorage.removeItem("sf_cliente");
      setCliente(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Validação em background no mount
  useEffect(() => {
    loadCliente();
  }, [loadCliente]);

  /**
   * Sync multi-aba: escuta mudanças no localStorage.
   *
   * Quando outra aba altera sf_token (login/logout/401), este listener
   * sincroniza o estado automaticamente. O evento "storage" só dispara
   * em OUTRAS abas (não na que fez a mudança).
   *
   * Para capturar mudanças NA MESMA aba (ex: interceptor 401), usamos
   * window.addEventListener("storage") que também captura StorageEvents
   * disparados manualmente via window.dispatchEvent().
   */
  useEffect(() => {
    function handleStorageChange(e: StorageEvent) {
      if (e.key === "sf_token") {
        if (e.newValue) {
          // Outra aba fez login — recarrega dados do cliente
          loadCliente();
        } else {
          // Outra aba fez logout ou token expirou — desloga aqui também
          setCliente(null);
          localStorage.removeItem("sf_cliente");
        }
      }
    }

    window.addEventListener("storage", handleStorageChange);
    return () => window.removeEventListener("storage", handleStorageChange);
  }, [loadCliente]);

  /**
   * Login: salva token + dados do cliente no localStorage.
   * O cache em sf_cliente permite mount instantâneo no próximo reload.
   */
  const login = useCallback((token: string, clienteData: Cliente) => {
    localStorage.setItem("sf_token", token);
    localStorage.setItem("sf_cliente", JSON.stringify(clienteData));
    setCliente(clienteData);
  }, []);

  /**
   * Logout: remove token e cache do cliente.
   * Não dispara StorageEvent manual porque o efeito já é imediato.
   */
  const logout = useCallback(() => {
    localStorage.removeItem("sf_token");
    localStorage.removeItem("sf_cliente");
    setCliente(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        cliente,
        loading,
        isLoggedIn: !!cliente,
        login,
        logout,
        refreshCliente: loadCliente,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
