import { Route, Switch } from "wouter";
import { AdminAuthProvider, useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import PrivateRoute from "@/admin/components/PrivateRoute";
import AdminLogin from "@/admin/pages/AdminLogin";
import Dashboard from "@/admin/pages/Dashboard";
import Pedidos from "@/admin/pages/Pedidos";
import PedidoDetalhe from "@/admin/pages/PedidoDetalhe";
import NovoPedido from "@/admin/pages/NovoPedido";
import Categorias from "@/admin/pages/Categorias";
import Produtos from "@/admin/pages/Produtos";
import ProdutoForm from "@/admin/pages/ProdutoForm";
import Combos from "@/admin/pages/Combos";
import Motoboys from "@/admin/pages/Motoboys";
import MapaMotoboys from "@/admin/pages/MapaMotoboys";
import Caixa from "@/admin/pages/Caixa";
import Promocoes from "@/admin/pages/Promocoes";
import Fidelidade from "@/admin/pages/Fidelidade";
import Bairros from "@/admin/pages/Bairros";
import Relatorios from "@/admin/pages/Relatorios";
import Configuracoes from "@/admin/pages/Configuracoes";
import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useWebSocket } from "@/admin/hooks/useWebSocket";

// ─── WebSocket provider (precisa estar dentro do AdminAuthProvider) ────────────
function AdminWebSocket() {
  const { restaurante, isLoggedIn } = useAdminAuth();
  useWebSocket({
    restauranteId: isLoggedIn && restaurante ? restaurante.id : null,
    habilitarSom: true,
    habilitarNotificacaoSistema: false,
  });
  return null;
}

function AdminRouter() {
  return (
    <Switch>
      <Route path="/login" component={AdminLogin} />

      <Route path="/">
        <PrivateRoute><Dashboard /></PrivateRoute>
      </Route>

      <Route path="/pedidos/novo">
        <PrivateRoute><NovoPedido /></PrivateRoute>
      </Route>

      <Route path="/pedidos/:id">
        <PrivateRoute><PedidoDetalhe /></PrivateRoute>
      </Route>

      <Route path="/pedidos">
        <PrivateRoute><Pedidos /></PrivateRoute>
      </Route>

      <Route path="/categorias">
        <PrivateRoute><Categorias /></PrivateRoute>
      </Route>

      <Route path="/produtos/novo">
        <PrivateRoute><ProdutoForm /></PrivateRoute>
      </Route>

      <Route path="/produtos/:id">
        <PrivateRoute><ProdutoForm /></PrivateRoute>
      </Route>

      <Route path="/produtos">
        <PrivateRoute><Produtos /></PrivateRoute>
      </Route>

      <Route path="/combos">
        <PrivateRoute><Combos /></PrivateRoute>
      </Route>

      <Route path="/motoboys/mapa">
        <PrivateRoute><MapaMotoboys /></PrivateRoute>
      </Route>

      <Route path="/motoboys">
        <PrivateRoute><Motoboys /></PrivateRoute>
      </Route>

      <Route path="/caixa">
        <PrivateRoute><Caixa /></PrivateRoute>
      </Route>

      <Route path="/promocoes">
        <PrivateRoute><Promocoes /></PrivateRoute>
      </Route>

      <Route path="/fidelidade">
        <PrivateRoute><Fidelidade /></PrivateRoute>
      </Route>

      <Route path="/bairros">
        <PrivateRoute><Bairros /></PrivateRoute>
      </Route>

      <Route path="/relatorios">
        <PrivateRoute><Relatorios /></PrivateRoute>
      </Route>

      <Route path="/configuracoes">
        <PrivateRoute><Configuracoes /></PrivateRoute>
      </Route>

      {/* Fallback admin */}
      <Route>
        <PrivateRoute><Dashboard /></PrivateRoute>
      </Route>
    </Switch>
  );
}

export default function AdminApp() {
  return (
    <AdminAuthProvider>
      <TooltipProvider>
        <Toaster />
        <AdminWebSocket />
        <AdminRouter />
      </TooltipProvider>
    </AdminAuthProvider>
  );
}
