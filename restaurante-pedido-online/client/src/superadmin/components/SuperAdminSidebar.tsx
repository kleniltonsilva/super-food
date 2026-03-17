import { useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useSuperAdminAuth } from "@/superadmin/contexts/SuperAdminAuthContext";
import {
  LayoutDashboard,
  Store,
  PlusCircle,
  CreditCard,
  AlertTriangle,
  Bug,
  Plug,
  Receipt,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  open: boolean;
  onClose: () => void;
}

const menuItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/restaurantes", label: "Restaurantes", icon: Store },
  { path: "/restaurantes/novo", label: "Novo Restaurante", icon: PlusCircle },
  { path: "/planos", label: "Planos", icon: CreditCard },
  { path: "/inadimplentes", label: "Inadimplentes", icon: AlertTriangle },
  { path: "/billing", label: "Billing", icon: Receipt },
  { path: "/integracoes", label: "Integrações", icon: Plug },
  { path: "/erros", label: "Erros (Sentry)", icon: Bug },
];

export default function SuperAdminSidebar({ open, onClose }: Props) {
  const [location, navigate] = useLocation();
  const { admin } = useSuperAdminAuth();

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
          "fixed top-0 left-0 z-50 flex h-full w-64 flex-col border-r border-[var(--sa-border)] bg-[var(--sa-bg-surface)] transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex flex-col border-b border-[var(--sa-border)]">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">👑</span>
              <span className="text-lg font-bold text-[var(--sa-text-primary)] truncate">
                Super Admin
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          {admin && (
            <div className="flex items-center gap-2 px-4 pb-3">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[var(--sa-accent-bg)] px-2.5 py-0.5 text-xs font-medium text-[var(--sa-accent-text)]">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--sa-accent-text)]" />
                {admin.usuario}
              </span>
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
                        ? "bg-[var(--sa-accent)] text-white"
                        : "text-[var(--sa-text-muted)] hover:bg-[var(--sa-bg-hover)] hover:text-[var(--sa-text-primary)]"
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
        <div className="border-t border-[var(--sa-border)] p-3">
          <p className="text-center text-xs text-[var(--sa-text-dimmed)]">
            Derekh Food v4.0
          </p>
        </div>
      </aside>
    </>
  );
}
