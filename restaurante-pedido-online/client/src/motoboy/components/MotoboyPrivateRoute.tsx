import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { Redirect } from "wouter";
import { Spinner } from "@/components/ui/spinner";

interface PrivateRouteProps {
  children: React.ReactNode;
}

export default function MotoboyPrivateRoute({ children }: PrivateRouteProps) {
  const { isLoggedIn, loading } = useMotoboyAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-950">
        <Spinner className="h-8 w-8 text-green-500" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
