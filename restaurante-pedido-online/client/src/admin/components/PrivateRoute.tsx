import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { Redirect } from "wouter";
import { Spinner } from "@/components/ui/spinner";

interface PrivateRouteProps {
  children: React.ReactNode;
}

export default function PrivateRoute({ children }: PrivateRouteProps) {
  const { isLoggedIn, loading } = useAdminAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[var(--bg-base)]">
        <Spinner className="h-8 w-8 text-[var(--cor-primaria)]" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
