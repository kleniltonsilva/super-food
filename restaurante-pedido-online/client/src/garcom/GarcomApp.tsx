import { Route, Switch } from "wouter";
import { GarcomAuthProvider, useGarcomAuth } from "@/garcom/contexts/GarcomAuthContext";
import GarcomPrivateRoute from "@/garcom/components/GarcomPrivateRoute";
import GarcomLogin from "@/garcom/pages/GarcomLogin";
import GarcomGrid from "@/garcom/pages/GarcomGrid";
import GarcomAbrirMesa from "@/garcom/pages/GarcomAbrirMesa";
import GarcomMesa from "@/garcom/pages/GarcomMesa";
import GarcomMenu from "@/garcom/pages/GarcomMenu";
import GarcomTransferir from "@/garcom/pages/GarcomTransferir";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useGarcomWebSocket } from "@/garcom/hooks/useGarcomWebSocket";

/** Componente interno que ativa WebSocket quando garçom está logado */
function GarcomWebSocket() {
  const { garcom, isLoggedIn } = useGarcomAuth();
  useGarcomWebSocket({
    restauranteId: isLoggedIn && garcom ? garcom.restaurante.id : null,
    somAtivo: true,
  });
  return null;
}

function GarcomRouter() {
  return (
    <Switch>
      <Route path="/login" component={GarcomLogin} />

      <Route path="/abrir/:mesaId">
        <GarcomPrivateRoute><GarcomAbrirMesa /></GarcomPrivateRoute>
      </Route>

      <Route path="/mesa/:sessaoId">
        <GarcomPrivateRoute><GarcomMesa /></GarcomPrivateRoute>
      </Route>

      <Route path="/menu/:sessaoId">
        <GarcomPrivateRoute><GarcomMenu /></GarcomPrivateRoute>
      </Route>

      <Route path="/transferir/:mesaId/:sessaoId">
        <GarcomPrivateRoute><GarcomTransferir /></GarcomPrivateRoute>
      </Route>

      <Route path="/">
        <GarcomPrivateRoute><GarcomGrid /></GarcomPrivateRoute>
      </Route>

      {/* Fallback */}
      <Route>
        <GarcomPrivateRoute><GarcomGrid /></GarcomPrivateRoute>
      </Route>
    </Switch>
  );
}

export default function GarcomApp() {
  return (
    <GarcomAuthProvider>
      <TooltipProvider>
        <Toaster />
        <GarcomWebSocket />
        <GarcomRouter />
      </TooltipProvider>
    </GarcomAuthProvider>
  );
}
