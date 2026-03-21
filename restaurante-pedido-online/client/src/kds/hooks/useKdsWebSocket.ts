import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { KDS_QUERY_KEYS } from "./useKdsQueries";

interface UseKdsWebSocketOptions {
  restauranteId: number | null;
  somAtivo?: boolean;
}

// ─── Sons via Web Audio API (idênticos ao modelo visual) ───

const audioCtx = typeof window !== "undefined" ? new (window.AudioContext || (window as any).webkitAudioContext)() : null;

function playTone(freq: number, duration: number, startTime: number = 0) {
  if (!audioCtx) return;
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.frequency.value = freq;
  osc.type = "sine";
  gain.gain.setValueAtTime(0.3, audioCtx.currentTime + startTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + startTime + duration);
  osc.start(audioCtx.currentTime + startTime);
  osc.stop(audioCtx.currentTime + startTime + duration);
}

export function sndNew() {
  // 2 notas: 880Hz + 1174.66Hz (alerta novo pedido)
  playTone(880, 0.15, 0);
  playTone(1174.66, 0.15, 0.18);
}

export function sndDone() {
  // 1 nota: 523.25Hz (pedido feito)
  playTone(523.25, 0.2, 0);
}

export function sndReady() {
  // 3 notas ascendentes: 523.25Hz + 659.25Hz + 783.99Hz (pronto)
  playTone(523.25, 0.15, 0);
  playTone(659.25, 0.15, 0.18);
  playTone(783.99, 0.2, 0.36);
}

export function useKdsWebSocket({ restauranteId, somAtivo = true }: UseKdsWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const qc = useQueryClient();
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!restauranteId) return;

    const token = localStorage.getItem("sf_kds_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/kds/${restauranteId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      // Connected
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const tipo = msg.tipo || msg.type;

        if (tipo === "kds:novo_pedido") {
          qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos });
          if (somAtivo) {
            // Resume AudioContext on user gesture
            if (audioCtx?.state === "suspended") audioCtx.resume();
            sndNew();
          }
        } else if (tipo === "kds:pedido_atualizado") {
          qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos });
          const status = msg.dados?.status;
          if (somAtivo) {
            if (audioCtx?.state === "suspended") audioCtx.resume();
            if (status === "FEITO") sndDone();
            else if (status === "PRONTO") sndReady();
          }
        } else if (tipo === "kds:pedido_cancelado") {
          qc.invalidateQueries({ queryKey: KDS_QUERY_KEYS.pedidos });
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
      // Reconnect after 3s
      reconnectTimeoutRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [restauranteId, somAtivo, qc]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null;
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [connect]);
}
