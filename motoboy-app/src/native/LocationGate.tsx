/**
 * LocationGate — Tela bloqueante que exige permissão de localização.
 *
 * Se GPS não autorizado no Capacitor nativo, mostra tela pedindo permissão.
 * Verifica a cada vez que o app volta ao foreground.
 */
import { useEffect, useState, useCallback } from "react";
import { Capacitor } from "@capacitor/core";
import { MapPin, ShieldAlert, RefreshCw } from "lucide-react";
import {
  checkLocationPermissions,
  requestLocationPermissions,
} from "./gps-native";

interface LocationGateProps {
  children: React.ReactNode;
}

export default function LocationGate({ children }: LocationGateProps) {
  const [status, setStatus] = useState<"checking" | "granted" | "denied" | "prompt">("checking");
  const [requesting, setRequesting] = useState(false);

  const verificar = useCallback(async () => {
    if (!Capacitor.isNativePlatform()) {
      setStatus("granted");
      return;
    }
    const result = await checkLocationPermissions();
    setStatus(result);
  }, []);

  // Verificar na montagem
  useEffect(() => {
    verificar();
  }, [verificar]);

  // Re-verificar quando app volta ao foreground
  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return;

    let cleanup: (() => void) | undefined;

    import("@capacitor/app").then(({ App: CapApp }) => {
      const listener = CapApp.addListener("appStateChange", ({ isActive }) => {
        if (isActive) verificar();
      });
      cleanup = () => {
        listener.then((l) => l.remove());
      };
    });

    return () => {
      cleanup?.();
    };
  }, [verificar]);

  async function handleRequest() {
    setRequesting(true);
    const granted = await requestLocationPermissions();
    if (granted) {
      setStatus("granted");
    } else {
      // Se negou de novo, verificar se foi "denied permanently"
      const check = await checkLocationPermissions();
      setStatus(check);
    }
    setRequesting(false);
  }

  // Enquanto verifica, não bloqueia
  if (status === "checking") return <>{children}</>;

  // Permissão concedida — passa direto
  if (status === "granted") return <>{children}</>;

  // Precisa pedir permissão (prompt) ou foi negada (denied)
  const isDenied = status === "denied";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-950 px-6 text-center text-white">
      <div className="mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-orange-500/20">
        {isDenied ? (
          <ShieldAlert className="h-10 w-10 text-orange-400" />
        ) : (
          <MapPin className="h-10 w-10 text-green-400" />
        )}
      </div>

      <h1 className="mb-2 text-xl font-bold">
        {isDenied ? "Localização Bloqueada" : "Permissão de Localização"}
      </h1>

      <p className="mb-6 max-w-sm text-sm text-gray-400">
        {isDenied
          ? 'O acesso à localização foi negado. O app precisa do GPS em tempo real para rastrear suas entregas.'
          : "Para rastrear suas entregas em tempo real, o app precisa acessar a localização do seu dispositivo."}
      </p>

      {isDenied && (
        <div className="mb-6 rounded-xl bg-gray-900 border border-gray-800 p-4 max-w-sm text-left">
          <p className="text-xs font-semibold text-orange-400 mb-2">Como ativar:</p>
          <ol className="text-xs text-gray-400 space-y-1.5 list-decimal list-inside">
            <li>Abra <span className="text-white font-medium">Configurações</span> do celular</li>
            <li>Toque em <span className="text-white font-medium">Apps</span> {'>'} <span className="text-white font-medium">Derekh Entregador</span></li>
            <li>Toque em <span className="text-white font-medium">Permissões</span> {'>'} <span className="text-white font-medium">Localização</span></li>
            <li>Selecione <span className="text-green-400 font-medium">"Permitir o tempo todo"</span></li>
          </ol>
        </div>
      )}

      <div className="flex flex-col gap-3 w-full max-w-xs">
        <button
          onClick={handleRequest}
          disabled={requesting}
          className={`flex items-center justify-center gap-2 rounded-xl px-6 py-3.5 font-semibold text-white shadow-lg disabled:opacity-50 ${
            isDenied
              ? "bg-orange-600 active:bg-orange-700"
              : "bg-green-600 active:bg-green-700"
          }`}
        >
          <MapPin className="h-5 w-5" />
          {requesting
            ? "Solicitando..."
            : isDenied
              ? "Tentar Novamente"
              : "Permitir Localização"}
        </button>

        {isDenied && (
          <button
            onClick={verificar}
            className="flex items-center justify-center gap-2 rounded-xl bg-gray-800 px-6 py-3 text-sm font-medium text-gray-300 active:bg-gray-700"
          >
            <RefreshCw className="h-4 w-4" />
            Já ativei, verificar
          </button>
        )}
      </div>
    </div>
  );
}
