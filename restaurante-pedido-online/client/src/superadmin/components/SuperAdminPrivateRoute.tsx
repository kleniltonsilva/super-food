import { useSuperAdminAuth } from "@/superadmin/contexts/SuperAdminAuthContext";
import { Redirect } from "wouter";
import { Spinner } from "@/components/ui/spinner";

interface Props {
  children: React.ReactNode;
}

export default function SuperAdminPrivateRoute({ children }: Props) {
  const { isLoggedIn, loading } = useSuperAdminAuth();

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
