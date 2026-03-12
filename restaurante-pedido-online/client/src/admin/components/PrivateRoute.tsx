import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { useLocation } from "wouter";
import { Spinner } from "@/components/ui/spinner";
import { useEffect } from "react";

interface PrivateRouteProps {
  children: React.ReactNode;
}

const REDIRECT_KEY = "sf_admin_redirect";

export default function PrivateRoute({ children }: PrivateRouteProps) {
  const { isLoggedIn, loading } = useAdminAuth();
  const [location, navigate] = useLocation();

  useEffect(() => {
    if (!loading && !isLoggedIn) {
      // Salva rota atual para redirecionar após login
      if (location !== "/login") {
        sessionStorage.setItem(REDIRECT_KEY, location);
      }
      navigate("/login");
    }
  }, [isLoggedIn, loading, location, navigate]);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-base)]">
        <Spinner className="h-8 w-8 text-[var(--cor-primaria)]" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-base)]">
        <Spinner className="h-8 w-8 text-[var(--cor-primaria)]" />
      </div>
    );
  }

  return <>{children}</>;
}

export { REDIRECT_KEY };
