import { Menu, LogOut, User, ShoppingBag, Bike, DollarSign } from "lucide-react";
import NotificationBell from "@/admin/components/NotificationBell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { usePedidos, useCaixaAtual } from "@/admin/hooks/useAdminQueries";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useLocation } from "wouter";

interface AdminTopbarProps {
  onToggleSidebar: () => void;
}

export default function AdminTopbar({ onToggleSidebar }: AdminTopbarProps) {
  const { restaurante, logout } = useAdminAuth();
  const [location, navigate] = useLocation();

  // Dados para badges
  const { data: pedidos } = usePedidos({ status: "pendente" });
  const { data: caixa } = useCaixaAtual();

  const pedidosPendentes = Array.isArray(pedidos) ? pedidos.length : 0;
  const caixaAberto = !!(caixa && (caixa as Record<string, unknown>).id);

  const initials = restaurante?.nome
    ? restaurante.nome
        .split(" ")
        .map((w) => w[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "SF";

  const quickItems = [
    {
      path: "/pedidos",
      label: "Pedidos",
      icon: ShoppingBag,
      badge: pedidosPendentes > 0 ? pedidosPendentes : null,
      badgeColor: "bg-red-500",
    },
    {
      path: "/motoboys",
      label: "Motoboys",
      icon: Bike,
      badge: null,
      badgeColor: "",
    },
    {
      path: "/caixa",
      label: "Caixa",
      icon: DollarSign,
      badge: caixaAberto ? null : "!",
      badgeColor: caixaAberto ? "" : "bg-yellow-500",
    },
  ];

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-4">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={onToggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold text-[var(--text-primary)] max-sm:hidden">
          {restaurante?.nome || "Painel Admin"}
        </h1>
      </div>

      {/* Quick Access: Pedidos, Motoboys, Caixa */}
      <div className="flex items-center gap-1">
        {quickItems.map((item) => {
          const isActive = location.startsWith(item.path);
          return (
            <Button
              key={item.path}
              variant={isActive ? "default" : "ghost"}
              size="sm"
              className={`relative gap-1.5 ${isActive ? "bg-[var(--cor-primaria)] text-white hover:bg-[var(--cor-primaria)]/90" : ""}`}
              onClick={() => navigate(item.path)}
            >
              <item.icon className="h-4 w-4" />
              <span className="max-sm:hidden">{item.label}</span>
              {item.badge !== null && (
                <Badge
                  className={`${item.badgeColor} text-white text-[10px] h-5 min-w-5 px-1 flex items-center justify-center absolute -top-1.5 -right-1.5 rounded-full`}
                >
                  {item.badge}
                </Badge>
              )}
            </Button>
          );
        })}

        {/* Notification Bell */}
        <NotificationBell />

        {/* Separator */}
        <div className="mx-2 h-6 w-px bg-[var(--border-subtle)]" />

        {/* User Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="flex items-center gap-2 px-2">
              <Avatar className="h-8 w-8">
                <AvatarImage src={restaurante?.logo_url || undefined} />
                <AvatarFallback className="bg-[var(--cor-primaria)] text-white text-xs">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <span className="text-sm text-[var(--text-primary)] max-sm:hidden">
                {restaurante?.nome}
              </span>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem className="gap-2" disabled>
              <User className="h-4 w-4" />
              Meu Perfil
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="gap-2 text-destructive" onClick={logout}>
              <LogOut className="h-4 w-4" />
              Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
