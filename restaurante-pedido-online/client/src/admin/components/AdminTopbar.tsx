import { Menu, LogOut, User, ShoppingBag, Bike, DollarSign, Clock, ArrowRight, Printer } from "lucide-react";
import NotificationBell from "@/admin/components/NotificationBell";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { usePedidos, useCaixaAtual, useTempoMedio } from "@/admin/hooks/useAdminQueries";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useLocation } from "wouter";

interface AdminTopbarProps {
  onToggleSidebar: () => void;
}

const statusColors: Record<string, string> = {
  otimo: "bg-green-500/15 text-green-700 border-green-300",
  ok: "bg-green-500/10 text-green-600 border-green-200",
  atencao: "bg-yellow-500/15 text-yellow-700 border-yellow-300",
  critico: "bg-red-500/15 text-red-700 border-red-300",
  sem_dados: "bg-gray-100 text-gray-500 border-gray-200",
};

const statusLabels: Record<string, string> = {
  otimo: "Mais rápido que o prometido!",
  ok: "Dentro da margem aceitável",
  atencao: "Ligeiro atraso detectado",
  critico: "Atraso grave — considere ajustar tempos",
  sem_dados: "Sem dados suficientes",
};

const tipoLabels: Record<string, string> = {
  entrega: "Entrega",
  retirada: "Retirada",
  mesa: "Mesa",
};

interface TempoData {
  configurado_min: number;
  real_min: number | null;
  base_pedidos: number;
  status: string;
}

function TempoChip({ tipo, data }: { tipo: string; data: TempoData }) {
  const cor = statusColors[data.status] || statusColors.sem_dados;
  const real = data.real_min !== null ? `${data.real_min}` : "—";

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium transition-colors hover:opacity-80 cursor-pointer ${cor}`}
        >
          <span className="max-md:hidden">{tipoLabels[tipo]}</span>
          <span className="font-mono">{data.configurado_min}</span>
          <ArrowRight className="h-3 w-3" />
          <span className="font-mono font-bold">{real}</span>
          <span className="max-lg:hidden">min</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-3" align="center">
        <div className="space-y-2">
          <div className="font-semibold text-sm">{tipoLabels[tipo]}</div>
          <div className="text-xs text-muted-foreground space-y-1">
            <div className="flex justify-between">
              <span>Configurado:</span>
              <span className="font-mono font-medium">{data.configurado_min}min</span>
            </div>
            <div className="flex justify-between">
              <span>Real (média):</span>
              <span className="font-mono font-medium">{real}min</span>
            </div>
            <div className="flex justify-between">
              <span>Base:</span>
              <span>{data.base_pedidos} pedido(s)</span>
            </div>
          </div>
          <div className={`rounded px-2 py-1 text-xs ${cor}`}>
            {data.real_min !== null && data.real_min < data.configurado_min
              ? `Equipe ${data.configurado_min - data.real_min}min mais rápida!`
              : statusLabels[data.status]}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}

export default function AdminTopbar({ onToggleSidebar }: AdminTopbarProps) {
  const { restaurante, logout } = useAdminAuth();
  const [location, navigate] = useLocation();

  // Dados para badges
  const { data: pedidos } = usePedidos({ status: "pendente" });
  const { data: caixa } = useCaixaAtual();
  const { data: tempoMedio } = useTempoMedio();
  const qc = useQueryClient();
  const printerStatus = qc.getQueryData<Record<string, unknown>>(["printer_status"]);
  const printerOnline = !!(printerStatus && printerStatus.online);

  const pedidosPendentes = Array.isArray(pedidos) ? pedidos.length : 0;
  const caixaAberto = !!(caixa && (caixa as Record<string, unknown>).id);

  const initials = restaurante?.nome
    ? restaurante.nome
        .split(" ")
        .map((w: string) => w[0])
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

  const tempoData = tempoMedio as Record<string, TempoData> | undefined;

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

        {/* Tempo Configurado vs Real chips */}
        {tempoData && (
          <>
            <div className="mx-1.5 h-6 w-px bg-[var(--border-subtle)] max-sm:hidden" />
            <div className="flex items-center gap-1 max-sm:hidden">
              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
              {(["entrega", "retirada", "mesa"] as const).map((tipo) =>
                tempoData[tipo] ? (
                  <TempoChip key={tipo} tipo={tipo} data={tempoData[tipo]} />
                ) : null
              )}
            </div>
          </>
        )}

        {/* Printer Status Indicator */}
        {printerStatus && (
          <Popover>
            <PopoverTrigger asChild>
              <button className="relative p-1.5 rounded-md hover:bg-accent transition-colors" title={printerOnline ? "Impressora conectada" : "Impressora desconectada"}>
                <Printer className="h-4 w-4 text-muted-foreground" />
                <span className={`absolute top-0.5 right-0.5 h-2 w-2 rounded-full ${printerOnline ? "bg-green-500" : "bg-red-500"}`} />
              </button>
            </PopoverTrigger>
            <PopoverContent className="w-48 p-3" align="center">
              <div className="text-sm font-medium">{printerOnline ? "Impressora Online" : "Impressora Offline"}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {printerOnline ? "Agente de impressão conectado" : "Agente de impressão desconectado"}
              </div>
            </PopoverContent>
          </Popover>
        )}

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
