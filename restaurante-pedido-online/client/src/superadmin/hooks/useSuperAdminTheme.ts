import { useState, useEffect, useCallback } from "react";

const STORAGE_KEY = "sf_superadmin_theme";

/**
 * Hook para toggle dark/light no Super Admin.
 * Persiste globalmente via localStorage.
 * Aplica/remove classe `sa-light` no wrapper `.superadmin`.
 */
export function useSuperAdminTheme() {
  const [theme, setTheme] = useState<"dark" | "light">(() => {
    return (localStorage.getItem(STORAGE_KEY) as "dark" | "light") || "dark";
  });

  const toggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === "dark" ? "light" : "dark";
      localStorage.setItem(STORAGE_KEY, next);
      return next;
    });
  }, []);

  const isDark = theme === "dark";

  return { theme, toggleTheme, isDark };
}
