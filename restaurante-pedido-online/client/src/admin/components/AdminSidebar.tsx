import { useState, useEffect } from "react";
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
  CreditCard,
  QrCode,
  ChefHat,
  Users,
  Printer,
  Bot,
  Lock,
  X,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ROUTE_FEATURE_MAP } from "@/admin/hooks/useFeatureFlag";

interface AdminSidebarProps {
  open: boolean;
  onClose: () => void;
}

interface MenuItem {
  path: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

interface MenuGroup {
  label: string;
  items: MenuItem[];
}

const dashboardItem: MenuItem = {
  path: "/",
  label: "Dashboard",
  icon: LayoutDashboard,
};

const menuGroups: MenuGroup[] = [
  {
    label: "PEDIDOS & OPERAÇÃO",
    items: [
      { path: "/pedidos", label: "Pedidos", icon: ShoppingBag },
      { path: "/caixa", label: "Caixa", icon: DollarSign },
      { path: "/relatorios", label: "Relatórios", icon: BarChart3 },
      { path: "/historico-atrasos", label: "Hist. Atrasos", icon: Clock },
    ],
  },
  {
    label: "CARDÁPIO",
    items: [
      { path: "/categorias", label: "Categorias", icon: List },
      { path: "/produtos", label: "Produtos", icon: Package },
      { path: "/combos", label: "Combos", icon: Layers },
      { path: "/promocoes", label: "Promoções", icon: Percent },
      { path: "/fidelidade", label: "Fidelidade", icon: Star },
    ],
  },
  {
    label: "CONFIGURAÇÕES",
    items: [
      { path: "/configuracoes", label: "Restaurante", icon: Settings },
      { path: "/motoboys", label: "Motoboys", icon: Bike },
      { path: "/motoboys/mapa", label: "Mapa Entregadores", icon: Map },
      { path: "/cozinha", label: "Cozinha Digital", icon: ChefHat },
      { path: "/garcons", label: "Garçons", icon: Users },
      { path: "/bridge", label: "Bridge Impressora", icon: Printer },
      { path: "/whatsapp-bot", label: "WhatsApp Humanoide", icon: Bot },
      { path: "/bairros", label: "Bairros e Taxas", icon: MapPin },
      { path: "/integracoes", label: "Integrações", icon: Plug },
      { path: "/pix", label: "Pagamento Pix", icon: QrCode },
      { path: "/billing", label: "Assinatura", icon: CreditCard },
    ],
  },
];

function findActiveGroup(location: string): string | null {
  for (const group of menuGroups) {
    for (const item of group.items) {
      const active =
        item.path === "/"
          ? location === "/"
          : location.startsWith(item.path);
      if (active) return group.label;
    }
  }
  return null;
}

export default function AdminSidebar({ open, onClose }: AdminSidebarProps) {
  const [location, navigate] = useLocation();
  const { restaurante } = useAdminAuth();
  const { data: config } = useConfig();

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    try {
      const stored = localStorage.getItem("admin_sidebar_groups");
      return stored ? JSON.parse(stored) : {};
    } catch {
      return {};
    }
  });

  const activeGroup = findActiveGroup(location);

  // Auto-expand group containing active route
  useEffect(() => {
    if (activeGroup && collapsed[activeGroup]) {
      setCollapsed((prev) => {
        const next = { ...prev };
        delete next[activeGroup];
        return next;
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeGroup]);

  // Persist collapsed state
  useEffect(() => {
    localStorage.setItem("admin_sidebar_groups", JSON.stringify(collapsed));
  }, [collapsed]);

  function toggleGroup(label: string) {
    setCollapsed((prev) => ({ ...prev, [label]: !prev[label] }));
  }

  function handleNavigate(path: string) {
    navigate(path);
    onClose();
  }

  function checkActive(path: string) {
    return path === "/" ? location === "/" : location.startsWith(path);
  }

  function renderItem(item: MenuItem) {
    const active = checkActive(item.path);
    const featureKey = ROUTE_FEATURE_MAP[item.path];
    const features = restaurante?.features as
      | Record<string, boolean>
      | undefined;
    const isLocked =
      featureKey && features ? features[featureKey] === false : false;

    return (
      <li key={item.path}>
        <button
          onClick={() => handleNavigate(item.path)}
          className={cn(
            "group/item relative flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium transition-colors",
            "md:justify-center lg:justify-start",
            active
              ? "bg-[var(--cor-primaria)] text-white"
              : isLocked
                ? "text-[var(--text-muted)] opacity-60 hover:bg-[var(--bg-card-hover)]"
                : "text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)]"
          )}
        >
          {isLocked ? (
            <Lock className="h-5 w-5 shrink-0" />
          ) : (
            <item.icon className="h-5 w-5 shrink-0" />
          )}
          <span className="truncate md:hidden lg:inline">{item.label}</span>
          {isLocked && (
            <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-400 px-1.5 py-0.5 rounded md:hidden lg:inline">
              PRO
            </span>
          )}
          {/* Compact mode tooltip (md only) */}
          <span className="pointer-events-none absolute left-full ml-2 hidden md:group-hover/item:block lg:!hidden rounded-md bg-[var(--bg-surface)] border border-[var(--border-subtle)] px-2 py-1 text-sm text-[var(--text-primary)] whitespace-nowrap z-50 shadow-lg">
            {item.label}
          </span>
        </button>
      </li>
    );
  }

  return (
    <>
      {/* Overlay mobile */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-50 flex h-full flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-surface)] transition-transform duration-200",
          "w-64 md:w-16 lg:w-64",
          "md:static md:z-auto",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        {/* Header */}
        <div className="flex flex-col border-b border-[var(--border-subtle)]">
          <div className="flex h-16 items-center justify-between px-4 md:justify-center md:px-2 lg:justify-between lg:px-4">
            <span className="text-lg font-bold text-[var(--text-primary)] truncate md:hidden lg:inline">
              {restaurante?.nome || "Derekh Food"}
            </span>
            <span className="hidden md:inline lg:hidden text-lg font-bold text-[var(--cor-primaria)]">
              DF
            </span>
            <Button
              variant="ghost"
              size="icon-sm"
              className="md:hidden"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          {restaurante && (
            <div className="flex items-center gap-2 px-4 pb-3 md:justify-center md:px-2 lg:justify-start lg:px-4">
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
                  config?.status_atual === "aberto"
                    ? "bg-green-500/20 text-green-400"
                    : "bg-red-500/20 text-red-400"
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    config?.status_atual === "aberto"
                      ? "bg-green-400"
                      : "bg-red-400"
                  )}
                />
                <span className="md:hidden lg:inline">
                  {config?.status_atual === "aberto" ? "Aberto" : "Fechado"}
                </span>
              </span>
              {restaurante.codigo_acesso && (
                <span className="text-xs text-[var(--text-muted)] md:hidden lg:inline">
                  #{restaurante.codigo_acesso}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto p-3 md:p-2 lg:p-3">
          {/* Dashboard — always visible */}
          <ul className="mb-2">{renderItem(dashboardItem)}</ul>

          {/* Groups */}
          {menuGroups.map((group) => {
            const isCollapsed = !!collapsed[group.label];

            return (
              <div key={group.label} className="mb-1">
                {/* Group header (full mode: mobile overlay + lg) */}
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="flex w-full items-center gap-2 px-3 py-2 md:hidden lg:flex"
                >
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    {group.label}
                  </span>
                  <span className="ml-auto text-[var(--text-muted)]">
                    {isCollapsed ? (
                      <ChevronRight className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </span>
                </button>

                {/* Compact divider (md only) */}
                <div className="mx-auto my-2 hidden h-px w-8 bg-[var(--border-subtle)] md:block lg:hidden" />

                {/* Items — always visible in compact (md), collapsible in full mode */}
                <ul
                  className={cn(
                    "space-y-0.5",
                    isCollapsed && "hidden md:block lg:hidden"
                  )}
                >
                  {group.items.map(renderItem)}
                </ul>
              </div>
            );
          })}
        </nav>

        {/* Footer */}
        <div className="border-t border-[var(--border-subtle)] p-3 md:p-2 lg:p-3">
          <p className="text-center text-xs text-[var(--text-muted)] md:hidden lg:block">
            Derekh Food v4.0
          </p>
        </div>
      </aside>
    </>
  );
}
