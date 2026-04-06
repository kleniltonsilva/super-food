/**
 * App wrapper Capacitor — adiciona update checker + GPS gate + background GPS sobre o MotoboyApp
 */
import { useCallback, useEffect, useState } from "react";
import MotoboyApp from "@/motoboy/MotoboyApp";
import NativeUpdateBanner from "./native/NativeUpdateBanner";
import SplashScreen from "./components/SplashScreen";
import LocationGate from "./native/LocationGate";
import {
  checkForUpdates,
  openDownloadUrl,
  type UpdateStatus,
} from "./native/update-checker";
import {
  isNativePlatform,
  startNativeTracking,
  stopNativeTracking,
} from "./native/gps-native";
import { enviarGPS } from "@/motoboy/lib/motoboyApiClient";
import { Capacitor } from "@capacitor/core";

const initialStatus: UpdateStatus = {
  checking: true,
  updateAvailable: false,
  updateRequired: false,
  currentVersion: "0.0.0",
  latestVersion: "0.0.0",
  downloadUrl: "",
};

// Throttle para envios do background GPS (10s)
const BG_THROTTLE_MS = 10_000;
let lastBgSend = 0;

export default function App() {
  const [showSplash, setShowSplash] = useState(true);
  const [updateStatus, setUpdateStatus] = useState<UpdateStatus>(initialStatus);
  const [dismissed, setDismissed] = useState(false);
  const handleSplashFinish = useCallback(() => setShowSplash(false), []);

  // Update checker
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    checkForUpdates().then(setUpdateStatus);

    import("@capacitor/app").then(({ App: CapApp }) => {
      CapApp.addListener("appStateChange", ({ isActive }) => {
        if (isActive) checkForUpdates().then(setUpdateStatus);
      });
    });
  }, []);

  // Background GPS — ativa quando há token de motoboy no localStorage
  useEffect(() => {
    if (!isNativePlatform()) return;

    const token = localStorage.getItem("sf_motoboy_token");
    if (!token) return;

    startNativeTracking(
      async (pos) => {
        const now = Date.now();
        if (now - lastBgSend < BG_THROTTLE_MS) return;
        lastBgSend = now;

        try {
          await enviarGPS({
            latitude: pos.latitude,
            longitude: pos.longitude,
            velocidade: pos.speed ?? 0,
            precisao: pos.accuracy,
            heading: pos.heading ?? undefined,
          });
        } catch {
          // Falha silenciosa — foreground GPS também envia
        }
      },
      (err) => {
        console.warn("Background GPS erro:", err.message);
      },
      { interval: 10000, distanceFilter: 5 }
    );

    return () => {
      stopNativeTracking();
    };
  }, []);

  function handleDownload() {
    if (updateStatus.downloadUrl) {
      openDownloadUrl(updateStatus.downloadUrl);
    }
  }

  const showBanner =
    !dismissed &&
    !updateStatus.checking &&
    (updateStatus.updateAvailable || updateStatus.updateRequired);

  if (showSplash) {
    return <SplashScreen onFinish={handleSplashFinish} duration={2000} />;
  }

  return (
    <LocationGate>
      <MotoboyApp />
      {showBanner && (
        <NativeUpdateBanner
          status={updateStatus}
          onDownload={handleDownload}
          onDismiss={
            updateStatus.updateRequired ? undefined : () => setDismissed(true)
          }
        />
      )}
    </LocationGate>
  );
}
