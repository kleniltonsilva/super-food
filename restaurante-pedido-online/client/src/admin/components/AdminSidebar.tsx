import { useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { useConfig } from "@/admin/hooks/useAdminQueries";
import {
  LayoutDashboard,
  ShoppingBag,
  List,
  Package,
  Layers,
  Bike,
  DollarSign,
  Percent,
  Star,
  MapPin,
  Map,
  BarChart3,
  Clock,
  Settings,
  Plug,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
}

const menuItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/pedidos", label: "Pedidos", icon: ShoppingBag },
  { path: "/categorias", label: "Categorias", icon: List },
  { path: "/produtos", label: "Produtos", icon: Package },
  { path: "/combos", label: "Combos", icon: Layers },
  { path: "/motoboys", label: "Motoboys", icon: Bike },
  { path: "/motoboys/mapa", label: "Mapa Motoboys", icon: Map },
  { path: "/caixa", label: "Caixa", icon: DollarSign },
  { path: "/promocoes", label: "Promoções", icon: Percent },
  { path: "/fidelidade", label: "Fidelidade", icon: Star },
  { path: "/bairros", label: "Bairros", icon: MapPin },
  { path: "/relatorios", label: "Relatórios", icon: BarChart3 },
  { path: "/historico-atrasos", label: "Atrasos", icon: Clock },
  { path: "/integracoes", label: "Integrações", icon: Plug },
  { path: "/configuracoes", label: "Configurações", icon: Settings },
];

export default function AdminSidebar({ open, onClose }: AdminSidebarProps) {
  const [location, navigate] = useLocation();
  const { restaurante } = useAdminAuth();
  const { data: config } = useConfig();

  function handleNavigate(path: string) {
    navigate(path);
    onClose();
  }

  return (
    <>
      {/* Overlay mobile */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 flex h-full w-64 flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex flex-col border-b border-[var(--border-subtle)]">
          <div className="flex h-16 items-center justify-between px-4">
            <span className="text-lg font-bold text-[var(--text-primary)] truncate">
              {restaurante?.nome || "Derekh Food"}
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="lg:hidden"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          {restaurante && (
            <div className="flex items-center gap-2 px-4 pb-3">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
                  config?.status_atual === "aberto"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-red-500/20 text-red-400"
                )}
              >
                <span className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  config?.status_atual === "aberto" ? "bg-green-400" : "bg-red-400"
                )} />
                {config?.status_atual === "aberto" ? "Aberto" : "Fechado"}
              </span>
              {restaurante.codigo_acesso && (
                <span className="text-xs text-[var(--text-muted)]">
                  #{restaurante.codigo_acesso}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-3">
          <ul className="space-y-1">
            {menuItems.map((item) => {
              const isActive =
                item.path === "/"
                  ? location === "/"
                  : location.startsWith(item.path);
              return (
                <li key={item.path}>
                  <button
                    onClick={() => handleNavigate(item.path)}
                    className={cn(
                      "flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-[var(--cor-primaria)] text-white"
                        : "text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)]"
                    )}
                  >
                    <item.icon className="h-5 w-5 shrink-0" />
                    {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-[var(--border-subtle)] p-3">
          <p className="text-center text-xs text-[var(--text-muted)]">
            Derekh Food v4.0
          </p>
        </div>
      </aside>
    </>
  );
}
