import { useLocation } from "wouter";
import { cn } from "@/lib/utils";
import { useSuperAdminAuth } from "@/superadmin/contexts/SuperAdminAuthContext";
import {
  LayoutDashboard,
  Store,
  PlusCircle,
  CreditCard,
  AlertTriangle,
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
          "fixed top-0 left-0 z-50 flex h-full w-64 flex-col border-r border-gray-800 bg-gray-900 transition-transform duration-200 lg:static lg:z-auto lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex flex-col border-b border-gray-800">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center gap-2">
              <span className="text-xl">👑</span>
              <span className="text-lg font-bold text-white truncate">
                Super Admin
              </span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden text-gray-400 hover:text-white"
              onClick={onClose}
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          {admin && (
            <div className="flex items-center gap-2 px-4 pb-3">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/20 px-2.5 py-0.5 text-xs font-medium text-amber-400">
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
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
                        ? "bg-amber-600 text-white"
                        : "text-gray-400 hover:bg-gray-800 hover:text-white"
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
        <div className="border-t border-gray-800 p-3">
          <p className="text-center text-xs text-gray-500">
            Super Food v4.0
          </p>
        </div>
      </aside>
    </>
  );
}
