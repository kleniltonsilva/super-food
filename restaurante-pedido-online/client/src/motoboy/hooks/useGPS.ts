import { useEffect, useRef, useState, useCallback } from "react";
import { enviarGPS } from "@/motoboy/lib/motoboyApiClient";

interface GPSState {
  status: "idle" | "ativo" | "enviando" | "erro" | "sem_permissao";
  latitude: number | null;
  longitude: number | null;
  velocidade: number | null;
  precisao: number | null;
  heading: number | null;
  erro: string | null;
}

// Throttle mínimo entre envios (ms) — evita flood quando GPS dispara muito rápido
const MIN_INTERVALO_MS = 3_000;
// Distância mínima (graus ~= 5 metros) para considerar que o motoboy se moveu
const MIN_DISTANCIA_GRAUS = 0.00005;
// Heartbeat: envia mesmo parado a cada N ms (para o servidor saber que está vivo)
const HEARTBEAT_MS = 30_000;

function distancia(lat1: number, lng1: number, lat2: number, lng2: number): number {
  return Math.hypot(lat2 - lat1, lng2 - lng1);
}

export function useGPS(ativo: boolean) {
  const [state, setState] = useState<GPSState>({
    status: "idle",
    latitude: null,
    longitude: null,
    velocidade: null,
    precisao: null,
    heading: null,
    erro: null,
  });

  const watchIdRef = useRef<number | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastSendRef = useRef<number>(0);
  const lastPosRef = useRef<{ lat: number; lng: number } | null>(null);
  const lastPositionRef = useRef<GeolocationPosition | null>(null);

  const enviar = useCallback(async (pos: GeolocationPosition) => {
    lastSendRef.current = Date.now();
    lastPosRef.current = { lat: pos.coords.latitude, lng: pos.coords.longitude };
    try {
      setState((s) => ({ ...s, status: "enviando" }));
      await enviarGPS({
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        velocidade: pos.coords.speed ?? 0,
        precisao: pos.coords.accuracy,
        heading: pos.coords.heading ?? undefined,
      });
      setState((s) => ({
        ...s,
        status: "ativo",
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        velocidade: pos.coords.speed,
        precisao: pos.coords.accuracy,
        heading: pos.coords.heading,
        erro: null,
      }));
    } catch {
      setState((s) => ({ ...s, status: "erro", erro: "Falha ao enviar GPS" }));
    }
  }, []);

  useEffect(() => {
    if (!ativo || !navigator.geolocation) {
      setState((s) => ({ ...s, status: "idle" }));
      return;
    }

    // navigator.geolocation.watchPosition funciona tanto no browser quanto no Capacitor WebView
    // (Capacitor proxia automaticamente para o GPS nativo do dispositivo)
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        lastPositionRef.current = pos;

        // Atualiza estado local imediatamente (UI reage na hora)
        setState((s) => ({
          ...s,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          velocidade: pos.coords.speed,
          precisao: pos.coords.accuracy,
          heading: pos.coords.heading,
          status: s.status === "idle" || s.status === "sem_permissao" ? "ativo" : s.status,
        }));

        const agora = Date.now();
        const throttleOk = agora - lastSendRef.current >= MIN_INTERVALO_MS;

        // Verifica se moveu o suficiente
        const moveu = !lastPosRef.current || distancia(
          lastPosRef.current.lat, lastPosRef.current.lng,
          pos.coords.latitude, pos.coords.longitude
        ) >= MIN_DISTANCIA_GRAUS;

        // Envia ao servidor: throttle + movimento mínimo
        if (throttleOk && moveu) {
          enviar(pos);
        }
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setState((s) => ({ ...s, status: "sem_permissao", erro: "Permissão GPS negada" }));
        } else {
          setState((s) => ({ ...s, status: "erro", erro: err.message }));
        }
      },
      { enableHighAccuracy: true, maximumAge: 2000, timeout: 15000 }
    );

    // Heartbeat: envia mesmo parado para manter presença no servidor
    heartbeatRef.current = setInterval(() => {
      if (lastPositionRef.current) {
        enviar(lastPositionRef.current);
      }
    }, HEARTBEAT_MS);

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
    };
  }, [ativo, enviar]);

  return state;
}
