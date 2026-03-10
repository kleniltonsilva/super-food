import { Route, Switch } from "wouter";
import { MotoboyAuthProvider } from "@/motoboy/contexts/MotoboyAuthContext";
import MotoboyPrivateRoute from "@/motoboy/components/MotoboyPrivateRoute";
import MotoboyLogin from "@/motoboy/pages/MotoboyLogin";
import MotoboyCadastro from "@/motoboy/pages/MotoboyCadastro";
import MotoboyHome from "@/motoboy/pages/MotoboyHome";
import MotoboyEntrega from "@/motoboy/pages/MotoboyEntrega";
import MotoboyGanhos from "@/motoboy/pages/MotoboyGanhos";
import MotoboyPerfil from "@/motoboy/pages/MotoboyPerfil";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

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

export default function MotoboyApp() {
  return (
    <MotoboyAuthProvider>
      <TooltipProvider>
        <Toaster />
        <MotoboyRouter />
      </TooltipProvider>
    </MotoboyAuthProvider>
  );
}
