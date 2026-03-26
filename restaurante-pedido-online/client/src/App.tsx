import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import Home from "@/pages/Home";
import ProductDetail from "@/pages/ProductDetail";
import Cart from "@/pages/Cart";
import Checkout from "@/pages/Checkout";
import Orders from "@/pages/Orders";
import Loyalty from "@/pages/Loyalty";
import Login from "@/pages/Login";
import OrderTracking from "@/pages/OrderTracking";
import Account from "@/pages/Account";
import OrderSuccess from "@/pages/OrderSuccess";
import VerificarEmail from "@/pages/VerificarEmail";
import EsqueciSenha from "@/pages/EsqueciSenha";
import { Route, Switch } from "wouter";
import AdminApp from "@/admin/AdminApp";
import MotoboyApp from "@/motoboy/MotoboyApp";
import SuperAdminApp from "@/superadmin/SuperAdminApp";
import KdsApp from "@/kds/KdsApp";
import GarcomApp from "@/garcom/GarcomApp";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { RestauranteProvider } from "./contexts/RestauranteContext";
import { AuthProvider } from "./contexts/AuthContext";
import DemoOverlay from "./components/DemoOverlay";

function ClienteRouter() {
  return (
    <RestauranteProvider>
      <AuthProvider>
        <DemoOverlay />
        <Switch>
          <Route path={"/"} component={Home} />
          <Route path={"/product/:id"} component={ProductDetail} />
          <Route path={"/cart"} component={Cart} />
          <Route path={"/checkout"} component={Checkout} />
          <Route path={"/orders"} component={Orders} />
          <Route path={"/order-success/:id"} component={OrderSuccess} />
          <Route path={"/order/:id"} component={OrderTracking} />
          <Route path={"/loyalty"} component={Loyalty} />
          <Route path={"/login"} component={Login} />
          <Route path={"/verificar-email"} component={VerificarEmail} />
          <Route path={"/esqueci-senha"} component={EsqueciSenha} />
          <Route path={"/account"} component={Account} />
          <Route path={"/404"} component={NotFound} />
          {/* Final fallback route */}
          <Route component={NotFound} />
        </Switch>
      </AuthProvider>
    </RestauranteProvider>
  );
}

function Router() {
  return (
    <Switch>
      <Route path="/superadmin" nest component={SuperAdminApp} />
      <Route path="/admin" nest component={AdminApp} />
      <Route path="/cozinha" nest component={KdsApp} />
      <Route path="/garcom" nest component={GarcomApp} />
      <Route path="/entregador" nest component={MotoboyApp} />
      <Route path="/cliente/:codigo" nest component={ClienteRouter} />
      <Route component={ClienteRouter} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
