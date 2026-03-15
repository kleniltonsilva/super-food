/**
 * NotificationContext — Gerencia notificações do painel admin.
 *
 * Todas as notificações WebSocket ficam salvas aqui e são exibidas no sino do topbar.
 * Notificações com ação (ex: entrega atrasada) mostram toast de 5s e ficam no sino.
 */

import React, { createContext, useContext, useCallback, useState, useRef } from "react";

export interface AdminNotification {
  id: string;
  tipo: "novo_pedido" | "pedido_cancelado" | "pedido_despachado" | "entrega_atrasada" | "entrega_finalizada" | "pedido_atualizado" | "info";
  titulo: string;
  mensagem: string;
  timestamp: Date;
  lida: boolean;
  /** Rota para navegar ao clicar */
  acao?: string;
  dados?: Record<string, unknown>;
}

interface NotificationContextType {
  notifications: AdminNotification[];
  unreadCount: number;
  addNotification: (notif: Omit<AdminNotification, "id" | "timestamp" | "lida">) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearAll: () => void;
}

const NotificationContext = createContext<NotificationContextType>({
  notifications: [],
  unreadCount: 0,
  addNotification: () => {},
  markAsRead: () => {},
  markAllAsRead: () => {},
  clearAll: () => {},
});

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<AdminNotification[]>([]);
  const counterRef = useRef(0);

  const addNotification = useCallback((notif: Omit<AdminNotification, "id" | "timestamp" | "lida">) => {
    counterRef.current += 1;
    const newNotif: AdminNotification = {
      ...notif,
      id: `notif-${counterRef.current}-${Date.now()}`,
      timestamp: new Date(),
      lida: false,
    };
    setNotifications(prev => [newNotif, ...prev].slice(0, 50)); // máx 50 notificações
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, lida: true } : n));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => prev.map(n => ({ ...n, lida: true })));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  const unreadCount = notifications.filter(n => !n.lida).length;

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, addNotification, markAsRead, markAllAsRead, clearAll }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationContext);
}
