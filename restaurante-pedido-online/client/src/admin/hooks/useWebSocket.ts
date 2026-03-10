import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { ADMIN_QUERY_KEYS } from "@/admin/hooks/useAdminQueries";

// ─── Tipos de eventos que o servidor envia ──────────────
export type WsEventTipo =
  | "novo_pedido"
  | "pedido_atualizado"
  | "pedido_cancelado"
  | "motoboy_posicao"
  | "ping";

export interface WsEvent {
  tipo: WsEventTipo;
  dados?: Record<string, unknown>;
}

// ─── Gera som de notificação via Web Audio API ──────────
function tocarSomNotificacao() {
  try {
    const ctx = new AudioContext();
    const tempos = [0, 0.15, 0.3];
    tempos.forEach((t) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 880;
      osc.type = "sine";
      gain.gain.setValueAtTime(0.4, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.12);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.12);
    });
  } catch {
    // AudioContext não disponível no ambiente
  }
}

// ─── Notificação do sistema operacional ─────────────────
async function notificarSistema(titulo: string, corpo: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") {
    await Notification.requestPermission();
  }
  if (Notification.permission === "granted") {
    new Notification(titulo, { body: corpo, icon: "/favicon.ico" });
  }
}

// ─── Hook principal ─────────────────────────────────────
interface UseWebSocketOptions {
  restauranteId: number | null;
  onEvento?: (evento: WsEvent) => void;
  habilitarSom?: boolean;
  habilitarNotificacaoSistema?: boolean;
}

export function useWebSocket({
  restauranteId,
  onEvento,
  habilitarSom = true,
  habilitarNotificacaoSistema = false,
}: UseWebSocketOptions) {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const tentativasRef = useRef(0);
  const reconectarTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const desconectadoIntencionalmente = useRef(false);

  const invalidarQueries = useCallback(
    (tipo: WsEventTipo) => {
      switch (tipo) {
        case "novo_pedido":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          if (habilitarSom) tocarSomNotificacao();
          if (habilitarNotificacaoSistema) {
            notificarSistema("Novo Pedido!", "Você recebeu um novo pedido.");
          }
          break;
        case "pedido_atualizado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          break;
        case "pedido_cancelado":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.pedidos });
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.dashboard });
          break;
        case "motoboy_posicao":
          qc.invalidateQueries({ queryKey: ADMIN_QUERY_KEYS.motoboys });
          break;
      }
    },
    [qc, habilitarSom, habilitarNotificacaoSistema]
  );

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
        const evento: WsEvent = JSON.parse(e.data);
        if (evento.tipo === "ping") return;
        invalidarQueries(evento.tipo);
        onEvento?.(evento);
      } catch {
        // ignorar mensagens mal-formatadas
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      if (desconectadoIntencionalmente.current) return;

      // Reconexão com backoff exponencial (máx 30s)
      const delay = Math.min(1000 * 2 ** tentativasRef.current, 30000);
      tentativasRef.current += 1;
      reconectarTimeoutRef.current = setTimeout(conectar, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [restauranteId, invalidarQueries, onEvento]);

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

  return { tocarSomNotificacao };
}
