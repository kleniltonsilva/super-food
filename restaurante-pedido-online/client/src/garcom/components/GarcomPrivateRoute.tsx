import { useGarcomAuth } from "@/garcom/contexts/GarcomAuthContext";
import { Redirect } from "wouter";
import { Spinner } from "@/components/ui/spinner";

interface PrivateRouteProps {
  children: React.ReactNode;
}

export default function GarcomPrivateRoute({ children }: PrivateRouteProps) {
  const { isLoggedIn, loading } = useGarcomAuth();

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0806]">
        <Spinner className="h-8 w-8 text-amber-500" />
      </div>
    );
  }

  if (!isLoggedIn) {
    return <Redirect to="/login" />;
  }

  return <>{children}</>;
}
