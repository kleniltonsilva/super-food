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
import HistoricoAtrasos from "@/admin/pages/HistoricoAtrasos";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { useWebSocket, type WsEvent } from "@/admin/hooks/useWebSocket";
import { NotificationProvider, useNotifications } from "@/admin/contexts/NotificationContext";
import { useCallback } from "react";
import { useLocation } from "wouter";

// ─── WebSocket provider (precisa estar dentro do AdminAuthProvider + NotificationProvider) ──
function AdminWebSocket() {
  const { restaurante, isLoggedIn } = useAdminAuth();
  const { addNotification } = useNotifications();
  const [, navigate] = useLocation();

  const handleEvento = useCallback((evento: WsEvent) => {
    const dados = evento.dados || {};
    const comanda = dados.comanda as string | undefined;

    switch (evento.tipo) {
      case "novo_pedido":
        addNotification({
          tipo: "novo_pedido",
          titulo: `Novo pedido${comanda ? ` #${comanda}` : ""}`,
          mensagem: "Um novo pedido foi recebido",
          acao: "/pedidos",
        });
        break;

      case "pedido_cancelado":
        addNotification({
          tipo: "pedido_cancelado",
          titulo: `Pedido${comanda ? ` #${comanda}` : ""} cancelado`,
          mensagem: "O pedido foi cancelado",
          acao: "/pedidos",
        });
        break;

      case "pedido_despachado":
        addNotification({
          tipo: "pedido_despachado",
          titulo: `Pedido${comanda ? ` #${comanda}` : ""} despachado`,
          mensagem: `Motoboy atribuído`,
          acao: "/pedidos",
        });
        break;

      case "entrega_atrasada": {
        const tempoDecorrido = dados.tempo_decorrido_min as number | undefined;
        const tempoEstimado = dados.tempo_estimado_min as number | undefined;
        addNotification({
          tipo: "entrega_atrasada",
          titulo: `Entrega atrasada${comanda ? ` #${comanda}` : ""}`,
          mensagem: tempoDecorrido && tempoEstimado
            ? `${tempoDecorrido}min (estimado: ${tempoEstimado}min)`
            : "Uma entrega ultrapassou o tempo estimado",
          acao: "/pedidos",
          dados,
        });
        // Toast de 5 segundos com ação
        toast.warning(
          `Entrega atrasada${comanda ? ` #${comanda}` : ""}! ${tempoDecorrido ? `${tempoDecorrido}min decorridos` : ""}`,
          {
            duration: 5000,
            action: {
              label: "Ver entregas",
              onClick: () => navigate("/pedidos"),
            },
          }
        );
        break;
      }

      case "entrega_finalizada": {
        const motoboyNome = dados.motoboy_nome as string | undefined;
        const motivo = dados.motivo as string | undefined;
        const motivoLabel = motivo === "entregue" ? "entregue" : motivo === "cliente_ausente" ? "cliente ausente" : "cancelado pelo cliente";
        addNotification({
          tipo: "entrega_finalizada",
          titulo: `Entrega${comanda ? ` #${comanda}` : ""} finalizada`,
          mensagem: `${motoboyNome || "Motoboy"} — ${motivoLabel}`,
          acao: "/pedidos",
        });
        break;
      }
    }
  }, [addNotification, navigate]);

  useWebSocket({
    restauranteId: isLoggedIn && restaurante ? restaurante.id : null,
    habilitarSom: true,
    habilitarNotificacaoSistema: false,
    onEvento: handleEvento,
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

      <Route path="/historico-atrasos">
        <PrivateRoute><HistoricoAtrasos /></PrivateRoute>
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
      <NotificationProvider>
        <TooltipProvider>
          <Toaster />
          <AdminWebSocket />
          <AdminRouter />
        </TooltipProvider>
      </NotificationProvider>
    </AdminAuthProvider>
  );
}
