import { Route, Switch } from "wouter";
import { SuperAdminAuthProvider } from "@/superadmin/contexts/SuperAdminAuthContext";
import SuperAdminPrivateRoute from "@/superadmin/components/SuperAdminPrivateRoute";
import SuperAdminLogin from "@/superadmin/pages/SuperAdminLogin";
import SuperAdminDashboard from "@/superadmin/pages/SuperAdminDashboard";
import GerenciarRestaurantes from "@/superadmin/pages/GerenciarRestaurantes";
import NovoRestaurante from "@/superadmin/pages/NovoRestaurante";
import GerenciarPlanos from "@/superadmin/pages/GerenciarPlanos";
import Inadimplentes from "@/superadmin/pages/Inadimplentes";
import ErrosSentry from "@/superadmin/pages/ErrosSentry";
import IntegracoesPlatforma from "@/superadmin/pages/IntegracoesPlatforma";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";

function SuperAdminRouter() {
  return (
    <Switch>
      <Route path="/login" component={SuperAdminLogin} />

      <Route path="/restaurantes/novo">
        <SuperAdminPrivateRoute><NovoRestaurante /></SuperAdminPrivateRoute>
      </Route>

      <Route path="/restaurantes">
        <SuperAdminPrivateRoute><GerenciarRestaurantes /></SuperAdminPrivateRoute>
      </Route>

      <Route path="/planos">
        <SuperAdminPrivateRoute><GerenciarPlanos /></SuperAdminPrivateRoute>
      </Route>

      <Route path="/inadimplentes">
        <SuperAdminPrivateRoute><Inadimplentes /></SuperAdminPrivateRoute>
      </Route>

      <Route path="/erros">
        <SuperAdminPrivateRoute><ErrosSentry /></SuperAdminPrivateRoute>
      </Route>

      <Route path="/integracoes">
        <SuperAdminPrivateRoute><IntegracoesPlatforma /></SuperAdminPrivateRoute>
      </Route>

      {/* Dashboard */}
      <Route path="/">
        <SuperAdminPrivateRoute><SuperAdminDashboard /></SuperAdminPrivateRoute>
      </Route>

      {/* Fallback */}
      <Route>
        <SuperAdminPrivateRoute><SuperAdminDashboard /></SuperAdminPrivateRoute>
      </Route>
    </Switch>
  );
}

export default function SuperAdminApp() {
  return (
    <SuperAdminAuthProvider>
      <TooltipProvider>
        <Toaster />
        <SuperAdminRouter />
      </TooltipProvider>
    </SuperAdminAuthProvider>
  );
}
