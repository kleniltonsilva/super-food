import { useKdsAuth } from "@/kds/contexts/KdsAuthContext";
import { Redirect } from "wouter";
import { Spinner } from "@/components/ui/spinner";

interface PrivateRouteProps {
  children: React.ReactNode;
}

export default function KdsPrivateRoute({ children }: PrivateRouteProps) {
  const { isLoggedIn, loading } = useKdsAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <Spinner className="h-8 w-8 text-amber-500" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
