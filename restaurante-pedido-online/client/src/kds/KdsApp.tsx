import { Route, Switch } from "wouter";
import { KdsAuthProvider, useKdsAuth } from "@/kds/contexts/KdsAuthContext";
import KdsPrivateRoute from "@/kds/components/KdsPrivateRoute";
import KdsLogin from "@/kds/pages/KdsLogin";
import KdsMain from "@/kds/pages/KdsMain";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useKdsWebSocket } from "@/kds/hooks/useKdsWebSocket";

/** Componente interno que ativa WebSocket quando cozinheiro está logado */
function KdsWebSocket() {
  const { cozinheiro, isLoggedIn } = useKdsAuth();
  useKdsWebSocket({
    restauranteId: isLoggedIn && cozinheiro ? cozinheiro.restaurante.id : null,
    somAtivo: true,
  });
  return null;
}

function KdsRouter() {
  return (
    <Switch>
      <Route path="/login" component={KdsLogin} />

      <Route path="/">
        <KdsPrivateRoute><KdsMain /></KdsPrivateRoute>
      </Route>

      {/* Fallback */}
      <Route>
        <KdsPrivateRoute><KdsMain /></KdsPrivateRoute>
      </Route>
    </Switch>
  );
}

export default function KdsApp() {
  return (
    <KdsAuthProvider>
      <TooltipProvider>
        <Toaster />
        <KdsWebSocket />
        <KdsRouter />
      </TooltipProvider>
    </KdsAuthProvider>
  );
}
