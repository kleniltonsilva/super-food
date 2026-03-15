/**
 * useClienteWebSocket.ts — WebSocket para o site do cliente.
 *
 * Conecta em /ws/{restauranteId} e escuta eventos:
 * - pedido_atualizado: status do pedido mudou
 * - pedido_cancelado: pedido foi cancelado
 * - pedido_despachado: motoboy foi atribuído
 * - config_atualizada: restaurante abriu/fechou ou mudou config
 *
 * Invalida queries automaticamente + chama onEvento() callback.
 * Reconexão automática com backoff exponencial (máx 30s).
 */

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/hooks/useQueries";

export interface ClienteWsEvent {
  tipo: string;
  dados?: Record<string, unknown>;
}

interface UseClienteWebSocketOptions {
  restauranteId: number | null | undefined;
  onEvento?: (evento: ClienteWsEvent) => void;
}

export function useClienteWebSocket({ restauranteId, onEvento }: UseClienteWebSocketOptions) {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const tentativasRef = useRef(0);
  const reconectarTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const desconectadoIntencionalmente = useRef(false);
  const onEventoRef = useRef(onEvento);
  onEventoRef.current = onEvento;

  const conectar = useCallback(() => {
    if (!restauranteId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocolo}//${host}/ws/${restauranteId}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      tentativasRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const evento: ClienteWsEvent = JSON.parse(e.data);
        if (evento.tipo === "ping") return;

        // Invalidar queries relevantes automaticamente
        switch (evento.tipo) {
          case "config_atualizada":
            qc.invalidateQueries({ queryKey: QUERY_KEYS.siteInfo });
            break;
          case "tempo_ajustado":
            qc.invalidateQueries({ queryKey: QUERY_KEYS.siteInfo });
            break;
          case "pedido_atualizado":
          case "pedido_cancelado":
          case "pedido_despachado":
            qc.invalidateQueries({ queryKey: QUERY_KEYS.meusPedidos });
            break;
        }

        onEventoRef.current?.(evento);
      } catch {
        // ignorar mensagens mal-formatadas
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (desconectadoIntencionalmente.current) return;
      const delay = Math.min(1000 * 2 ** tentativasRef.current, 30000);
      tentativasRef.current += 1;
      reconectarTimeoutRef.current = setTimeout(conectar, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [restauranteId, qc]);

  useEffect(() => {
    desconectadoIntencionalmente.current = false;
    conectar();

    return () => {
      desconectadoIntencionalmente.current = true;
      if (reconectarTimeoutRef.current) {
        clearTimeout(reconectarTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [conectar]);
}
