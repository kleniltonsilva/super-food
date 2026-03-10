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

const GPS_INTERVAL = 10_000; // 10 segundos

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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPositionRef = useRef<GeolocationPosition | null>(null);

  const enviar = useCallback(async (pos: GeolocationPosition) => {
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

    // Iniciar watch
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        lastPositionRef.current = pos;
        setState((s) => ({
          ...s,
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          velocidade: pos.coords.speed,
          precisao: pos.coords.accuracy,
          heading: pos.coords.heading,
          status: s.status === "idle" || s.status === "sem_permissao" ? "ativo" : s.status,
        }));
      },
      (err) => {
        if (err.code === err.PERMISSION_DENIED) {
          setState((s) => ({ ...s, status: "sem_permissao", erro: "Permissão GPS negada" }));
        } else {
          setState((s) => ({ ...s, status: "erro", erro: err.message }));
        }
      },
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 }
    );

    // Enviar a cada intervalo
    intervalRef.current = setInterval(() => {
      if (lastPositionRef.current) {
        enviar(lastPositionRef.current);
      }
    }, GPS_INTERVAL);

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
        watchIdRef.current = null;
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [ativo, enviar]);

  return state;
}
