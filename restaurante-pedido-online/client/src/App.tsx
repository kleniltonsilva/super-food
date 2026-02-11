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
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { RestauranteProvider } from "./contexts/RestauranteContext";
import { AuthProvider } from "./contexts/AuthContext";

function Router() {
  return (
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
      <Route path={"/account"} component={Account} />
      <Route path={"/404"} component={NotFound} />
      {/* Final fallback route */}
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="light">
        <RestauranteProvider>
          <AuthProvider>
            <TooltipProvider>
              <Toaster />
              <Router />
            </TooltipProvider>
          </AuthProvider>
        </RestauranteProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
