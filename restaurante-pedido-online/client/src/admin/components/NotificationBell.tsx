/**
 * NotificationBell — Sino de notificações no topbar admin.
 *
 * Mostra badge com contagem de não-lidas.
 * Dropdown com lista de notificações, cada uma clicável para navegar.
 */

import { Bell, Check, Trash2, AlertTriangle, Package, Truck, XCircle, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useNotifications, type AdminNotification } from "@/admin/contexts/NotificationContext";
import { useLocation } from "wouter";

function getIcon(tipo: AdminNotification["tipo"]) {
  switch (tipo) {
    case "novo_pedido": return <Package className="h-4 w-4 text-green-500 shrink-0" />;
    case "pedido_cancelado": return <XCircle className="h-4 w-4 text-red-500 shrink-0" />;
    case "entrega_atrasada": return <AlertTriangle className="h-4 w-4 text-yellow-500 shrink-0" />;
    case "entrega_finalizada": return <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />;
    case "pedido_despachado": return <Truck className="h-4 w-4 text-blue-500 shrink-0" />;
    default: return <Bell className="h-4 w-4 text-muted-foreground shrink-0" />;
  }
}

function timeAgo(date: Date): string {
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return "agora";
  if (diff < 3600) return `${Math.floor(diff / 60)}min`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

export default function NotificationBell() {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearAll } = useNotifications();
  const [, navigate] = useLocation();

  const handleClick = (notif: AdminNotification) => {
    markAsRead(notif.id);
    if (notif.acao) {
      navigate(notif.acao);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <Badge className="bg-red-500 text-white text-[10px] h-5 min-w-5 px-1 flex items-center justify-center absolute -top-1 -right-1 rounded-full animate-pulse">
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80 max-h-96 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-2">
          <span className="text-sm font-bold">Notificações</span>
          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={markAllAsRead}>
                <Check className="h-3 w-3" />
                Ler todas
              </Button>
            )}
            {notifications.length > 0 && (
              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1 text-muted-foreground" onClick={clearAll}>
                <Trash2 className="h-3 w-3" />
              </Button>
            )}
          </div>
        </div>
        <DropdownMenuSeparator />

        {notifications.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            Nenhuma notificação
          </div>
        ) : (
          notifications.slice(0, 30).map((notif) => (
            <DropdownMenuItem
              key={notif.id}
              className={`flex items-start gap-3 px-3 py-2.5 cursor-pointer ${!notif.lida ? "bg-[var(--cor-primaria)]/5" : ""}`}
              onClick={() => handleClick(notif)}
            >
              <div className="mt-0.5">{getIcon(notif.tipo)}</div>
              <div className="flex-1 min-w-0">
                <p className={`text-xs leading-tight ${!notif.lida ? "font-bold" : ""}`}>
                  {notif.titulo}
                </p>
                <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight truncate">
                  {notif.mensagem}
                </p>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0 mt-0.5">
                {timeAgo(notif.timestamp)}
              </span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
