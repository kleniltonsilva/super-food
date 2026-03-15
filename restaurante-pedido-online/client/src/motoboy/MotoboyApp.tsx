import { Route, Switch } from "wouter";
import { MotoboyAuthProvider, useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import MotoboyPrivateRoute from "@/motoboy/components/MotoboyPrivateRoute";
import MotoboyLogin from "@/motoboy/pages/MotoboyLogin";
import MotoboyCadastro from "@/motoboy/pages/MotoboyCadastro";
import MotoboyHome from "@/motoboy/pages/MotoboyHome";
import MotoboyEntrega from "@/motoboy/pages/MotoboyEntrega";
import MotoboyGanhos from "@/motoboy/pages/MotoboyGanhos";
import MotoboyPerfil from "@/motoboy/pages/MotoboyPerfil";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useMotoboyWebSocket } from "@/motoboy/hooks/useMotoboyWebSocket";

function MotoboyRouter() {
  return (
    <Switch>
      <Route path="/login" component={MotoboyLogin} />
      <Route path="/cadastro" component={MotoboyCadastro} />

      <Route path="/">
        <MotoboyPrivateRoute><MotoboyHome /></MotoboyPrivateRoute>
      </Route>

      <Route path="/entrega/:id">
        <MotoboyPrivateRoute><MotoboyEntrega /></MotoboyPrivateRoute>
      </Route>

      <Route path="/ganhos">
        <MotoboyPrivateRoute><MotoboyGanhos /></MotoboyPrivateRoute>
      </Route>

      <Route path="/perfil">
        <MotoboyPrivateRoute><MotoboyPerfil /></MotoboyPrivateRoute>
      </Route>

      {/* Fallback motoboy */}
      <Route>
        <MotoboyPrivateRoute><MotoboyHome /></MotoboyPrivateRoute>
      </Route>
    </Switch>
  );
}

/** Componente interno que ativa WebSocket quando motoboy está logado */
function MotoboyWebSocket() {
  const { motoboy, isLoggedIn } = useMotoboyAuth();
  useMotoboyWebSocket({
    restauranteId: isLoggedIn && motoboy ? motoboy.restaurante.id : null,
    motoboyId: isLoggedIn && motoboy ? motoboy.id : null,
  });
  return null;
}

export default function MotoboyApp() {
  return (
    <MotoboyAuthProvider>
      <TooltipProvider>
        <Toaster />
        <MotoboyWebSocket />
        <MotoboyRouter />
      </TooltipProvider>
    </MotoboyAuthProvider>
  );
}
