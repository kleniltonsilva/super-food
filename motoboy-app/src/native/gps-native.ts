/**
 * GPS Nativo Capacitor — Background Tracking com Foreground Service
 *
 * - Foreground: @capacitor/geolocation (alta precisão, proxied por navigator.geolocation)
 * - Background: @capacitor-community/background-geolocation (foreground service Android)
 */
import { Capacitor, registerPlugin } from "@capacitor/core";
import { Geolocation } from "@capacitor/geolocation";
import type { BackgroundGeolocationPlugin } from "@capacitor-community/background-geolocation";

// Registra o plugin nativo de background geolocation
const BackgroundGeolocation = registerPlugin<BackgroundGeolocationPlugin>(
  "BackgroundGeolocation"
);

export interface NativePosition {
  latitude: number;
  longitude: number;
  speed: number | null;
  accuracy: number;
  heading: number | null;
  timestamp: number;
}

type PositionCallback = (pos: NativePosition) => void;
type ErrorCallback = (err: { code: number; message: string }) => void;

let bgWatcherId: string | null = null;
let isTracking = false;

/** Verifica se está rodando como app nativo Capacitor */
export function isNativePlatform(): boolean {
  return Capacitor.isNativePlatform();
}

/** Verifica se permissão de localização já foi concedida (sem pedir) */
export async function checkLocationPermissions(): Promise<"granted" | "denied" | "prompt"> {
  if (!isNativePlatform()) return "granted";

  try {
    const status = await Geolocation.checkPermissions();
    if (status.location === "granted" || status.coarseLocation === "granted") {
      return "granted";
    }
    if (status.location === "denied") {
      return "denied";
    }
    return "prompt";
  } catch {
    return "prompt";
  }
}

/** Solicita permissões de localização (mostra dialog Android) */
export async function requestLocationPermissions(): Promise<boolean> {
  if (!isNativePlatform()) return true;

  try {
    const status = await Geolocation.requestPermissions({ permissions: ["location", "coarseLocation"] });
    return status.location === "granted" || status.coarseLocation === "granted";
  } catch {
    return false;
  }
}

/** Inicia tracking GPS nativo com background support */
export async function startNativeTracking(
  onPosition: PositionCallback,
  onError: ErrorCallback,
  options?: { interval?: number; distanceFilter?: number }
): Promise<void> {
  if (!isNativePlatform() || isTracking) return;

  try {
    const granted = await requestLocationPermissions();
    if (!granted) {
      onError({ code: 1, message: "Permissão de localização negada" });
      return;
    }

    // Background geolocation com foreground service
    bgWatcherId = await BackgroundGeolocation.addWatcher(
      {
        backgroundMessage: "Derekh Entregador — Rastreamento ativo",
        backgroundTitle: "Rastreamento de Entrega",
        requestPermissions: true,
        stale: false,
        distanceFilter: options?.distanceFilter ?? 5,
      },
      (location, error) => {
        if (error) {
          if (error.code === "NOT_AUTHORIZED") {
            onError({ code: 1, message: "Permissão de localização em background negada" });
          }
          return;
        }
        if (location) {
          onPosition({
            latitude: location.latitude,
            longitude: location.longitude,
            speed: location.speed ?? null,
            accuracy: location.accuracy,
            heading: location.bearing ?? null,
            timestamp: location.time ? location.time : Date.now(),
          });
        }
      }
    );

    isTracking = true;
  } catch (err) {
    onError({
      code: 2,
      message: err instanceof Error ? err.message : "Erro ao iniciar GPS nativo",
    });
  }
}

/** Para tracking GPS nativo */
export async function stopNativeTracking(): Promise<void> {
  if (!isNativePlatform() || !isTracking) return;

  try {
    if (bgWatcherId) {
      await BackgroundGeolocation.removeWatcher({ id: bgWatcherId });
      bgWatcherId = null;
    }
  } catch {
    // Ignora erros ao parar
  }

  isTracking = false;
}

/** Retorna posição atual (single shot) */
export async function getCurrentNativePosition(): Promise<NativePosition | null> {
  if (!isNativePlatform()) return null;

  try {
    const pos = await Geolocation.getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
    });
    return {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      speed: pos.coords.speed,
      accuracy: pos.coords.accuracy,
      heading: pos.coords.heading,
      timestamp: pos.timestamp,
    };
  } catch {
    return null;
  }
}

/** Registra GPS nativo — chamado uma vez na inicialização do app */
export function registerNativeGPS(): void {
  if (!isNativePlatform()) return;
  // Solicita permissão ao iniciar; resultado tratado no App.tsx
  requestLocationPermissions().catch((err) => {
    console.warn("GPS: falha ao solicitar permissão na inicialização:", err);
  });
}
