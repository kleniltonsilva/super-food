import { useState, useEffect, useCallback } from "react";

/**
 * Hook para toggle dark/light no painel Admin (restaurante).
 * Persiste por restaurante via localStorage.
 * Aplica/remove classe `admin-light` no <html>.
 */
export function useAdminTheme(restauranteId: number | string | undefined) {
  const key = restauranteId ? `sf_admin_theme_${restauranteId}` : null;

  const [theme, setTheme] = useState<"dark" | "light">(() => {
    if (!key) return "dark";
    return (localStorage.getItem(key) as "dark" | "light") || "dark";
  });

  // Sincronizar ao trocar de restaurante
  useEffect(() => {
    if (!key) return;
    const stored = (localStorage.getItem(key) as "dark" | "light") || "dark";
    setTheme(stored);
  }, [key]);

  // Aplicar classe no <html>
  useEffect(() => {
    const html = document.documentElement;
    if (theme === "light") {
      html.classList.add("admin-light");
    } else {
      html.classList.remove("admin-light");
    }
    return () => {
      html.classList.remove("admin-light");
    };
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      if (key) localStorage.setItem(key, next);
      return next;
    });
  }, [key]);

  const isDark = theme === "dark";

  return { theme, toggleTheme, isDark };
}
