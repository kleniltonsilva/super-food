/**
 * useMotoboyWebSocket.ts — WebSocket para o app motoboy.
 *
 * Conecta em /ws/{restauranteId} e escuta eventos relevantes:
 * - pedido_despachado: invalida queries de entregas + toca som + vibra + notificação
 * - pedido_cancelado: invalida queries de entregas + alerta se entrega era do motoboy
 * - pedido_atualizado: invalida queries de entregas
 *
 * Reconexão automática com backoff exponencial (máx 30s).
 */

import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { MOTOBOY_QUERY_KEYS } from "@/motoboy/hooks/useMotoboyQueries";

type WsEventTipo =
  | "novo_pedido"
  | "pedido_atualizado"
  | "pedido_cancelado"
  | "pedido_despachado"
  | "entrega_atrasada"
  | "tempo_ajustado"
  | "motoboy_posicao"
  | "ping";

interface WsEvent {
  tipo: WsEventTipo;
  dados?: Record<string, unknown>;
}

/** Som urgente para nova entrega: 3 beeps longos com vibração */
function tocarSomNovaEntrega() {
  try {
    const ctx = new AudioContext();
    for (let i = 0; i < 3; i++) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "sine";
      osc.frequency.value = 880;
      gain.gain.setValueAtTime(0.4, ctx.currentTime + i * 0.5);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.5 + 0.4);
      osc.start(ctx.currentTime + i * 0.5);
      osc.stop(ctx.currentTime + i * 0.5 + 0.4);
    }
  } catch {
    // AudioContext não disponível
  }
  // Vibração
  if (navigator.vibrate) {
    navigator.vibrate([200, 100, 200, 100, 300]);
  }
}

/** Som de cancelamento: alarme grave urgente (4 bips square 440Hz descendentes) */
function tocarSomCancelamento() {
  try {
    const ctx = new AudioContext();
    const freqs = [660, 550, 440, 330];
    freqs.forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.type = "square";
      osc.frequency.value = freq;
      const t = i * 0.3;
      gain.gain.setValueAtTime(0.35, ctx.currentTime + t);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + t + 0.25);
      osc.start(ctx.currentTime + t);
      osc.stop(ctx.currentTime + t + 0.25);
    });
  } catch {
    // AudioContext não disponível
  }
  // Vibração longa de alerta
  if (navigator.vibrate) {
    navigator.vibrate([500, 200, 500, 200, 500]);
  }
}

/** Notificação push do sistema */
function notificarSistema(titulo: string, corpo: string) {
  if (!("Notification" in window)) return;
  if (Notification.permission === "granted") {
    new Notification(titulo, {
      body: corpo,
      icon: "/icons/icon-192.png",
      requireInteraction: true,
    });
  }
}

interface UseMotoboyWebSocketOptions {
  restauranteId: number | null;
  motoboyId?: number | null;
}

export function useMotoboyWebSocket({ restauranteId, motoboyId }: UseMotoboyWebSocketOptions) {
  const qc = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  const tentativasRef = useRef(0);
  const reconectarTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const desconectadoIntencionalmente = useRef(false);
  const motoboyIdRef = useRef(motoboyId);
  motoboyIdRef.current = motoboyId;

  const invalidarQueries = useCallback(
    (evento: WsEvent) => {
      switch (evento.tipo) {
        case "pedido_despachado":
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes });
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota });
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.me });
          tocarSomNovaEntrega();
          notificarSistema("Nova entrega!", "Você recebeu uma nova entrega. Abra o app para aceitar.");
          break;
        case "pedido_cancelado": {
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes });
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota });
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.me });

          // Se a entrega cancelada era deste motoboy, alertar
          const eventMotoboyId = evento.dados?.motoboy_id as number | undefined;
          const comanda = evento.dados?.comanda as string | undefined;
          if (eventMotoboyId && motoboyIdRef.current && eventMotoboyId === motoboyIdRef.current) {
            tocarSomCancelamento();
            notificarSistema(
              "Entrega Cancelada!",
              `Pedido ${comanda ? `#${comanda}` : ""} foi cancelado pelo restaurante. Retorne ao restaurante com o pedido.`
            );
            toast.error(
              `Pedido ${comanda ? `#${comanda}` : ""} CANCELADO pelo restaurante! Retorne ao restaurante com o pedido.`,
              { duration: 15000 }
            );
          }
          break;
        }
        case "pedido_atualizado":
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasPendentes });
          qc.invalidateQueries({ queryKey: MOTOBOY_QUERY_KEYS.entregasEmRota });
          break;
      }
    },
    [qc]
  );

  const conectar = useCallback(() => {
    if (!restauranteId) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Detecta Capacitor nativo → usa produção diretamente
    let url: string;
    try {
      const w = window as unknown as Record<string, unknown>;
      if (w.Capacitor && (w.Capacitor as { isNativePlatform?: () => boolean }).isNativePlatform?.()) {
        url = `wss://superfood-api.fly.dev/ws/${restauranteId}`;
      } else {
        const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
        url = `${protocolo}//${window.location.host}/ws/${restauranteId}`;
      }
    } catch {
      const protocolo = window.location.protocol === "https:" ? "wss:" : "ws:";
      url = `${protocolo}//${window.location.host}/ws/${restauranteId}`;
    }

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      tentativasRef.current = 0;
    };

    ws.onmessage = (e) => {
      try {
        const evento: WsEvent = JSON.parse(e.data);
        if (evento.tipo === "ping") return;
        invalidarQueries(evento);
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
  }, [restauranteId, invalidarQueries]);

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

  // Pedir permissão de notificação ao montar
  useEffect(() => {
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
  }, []);
}
