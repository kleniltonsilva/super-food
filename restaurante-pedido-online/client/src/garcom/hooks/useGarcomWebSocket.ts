import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { GARCOM_QUERY_KEYS } from "./useGarcomQueries";

interface UseGarcomWebSocketOptions {
  restauranteId: number | null;
  somAtivo?: boolean;
}

// ─── Sons via Web Audio API ───

const audioCtx = typeof window !== "undefined" ? new (window.AudioContext || (window as any).webkitAudioContext)() : null;

function playTone(freq: number, duration: number, type: OscillatorType = "sine", gain: number = 0.3, startTime: number = 0) {
  if (!audioCtx) return;
  const osc = audioCtx.createOscillator();
  const g = audioCtx.createGain();
  osc.connect(g);
  g.connect(audioCtx.destination);
  osc.frequency.value = freq;
  osc.type = type;
  g.gain.setValueAtTime(gain, audioCtx.currentTime + startTime);
  g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + startTime + duration);
  osc.start(audioCtx.currentTime + startTime);
  osc.stop(audioCtx.currentTime + startTime + duration);
}

/** Pedido pronto - 3 notas ascendentes (C5, E5, G5) */
export function sndReady() {
  playTone(523.25, 0.15, "sine", 0.3, 0);
  playTone(659.25, 0.15, "sine", 0.3, 0.18);
  playTone(783.99, 0.2, "sine", 0.3, 0.36);
}

/** Item esgotado / 86 - 2 notas descendentes (A4, F#3) */
export function snd86() {
  playTone(440, 0.15, "square", 0.15, 0);
  playTone(330, 0.2, "square", 0.15, 0.18);
}

/** Click suave */
export function sndClick() {
  playTone(600, 0.05, "sine", 0.06, 0);
}

export function useGarcomWebSocket({ restauranteId, somAtivo = true }: UseGarcomWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const qc = useQueryClient();
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!restauranteId) return;

    const token = localStorage.getItem("sf_garcom_token");
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/garcom/${restauranteId}?token=${token}`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const tipo = msg.tipo || msg.type;

        if (audioCtx?.state === "suspended") audioCtx.resume();

        if (tipo === "garcom:pedido_pronto") {
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
          if (somAtivo) sndReady();
        } else if (tipo === "garcom:item_esgotado") {
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.itensEsgotados });
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.cardapio });
          if (somAtivo) snd86();
        } else if (tipo === "garcom:item_disponivel") {
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.itensEsgotados });
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.cardapio });
        } else if (tipo === "garcom:mesa_fechada") {
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.mesas });
          qc.invalidateQueries({ queryKey: GARCOM_QUERY_KEYS.sessao });
          if (somAtivo) sndReady();
        }
      } catch {
        // Ignore parse errors
      }
    };

    ws.onclose = () => {
      wsRef.current = null;
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
