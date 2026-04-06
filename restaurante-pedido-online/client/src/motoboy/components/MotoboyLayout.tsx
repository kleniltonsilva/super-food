import { useLocation } from "wouter";
import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { useGPS } from "@/motoboy/hooks/useGPS";
import { useMotoboyConfig } from "@/motoboy/hooks/useMotoboyQueries";
import { Package, DollarSign, User, MapPin, Wifi, WifiOff, Lock } from "lucide-react";

interface MotoboyLayoutProps {
  children: React.ReactNode;
  hideNav?: boolean;
}

function GPSIndicator({ ativo }: { ativo: boolean }) {
  const gps = useGPS(ativo);

  const statusConfig = {
    idle: { cor: "bg-gray-500", icone: MapPin, texto: "GPS..." },
    ativo: { cor: "bg-green-500", icone: MapPin, texto: `GPS ${gps.velocidade != null ? `${(gps.velocidade * 3.6).toFixed(0)} km/h` : "Ativo"}` },
    enviando: { cor: "bg-blue-500", icone: MapPin, texto: "Enviando..." },
    erro: { cor: "bg-red-500", icone: WifiOff, texto: "Erro GPS" },
    sem_permissao: { cor: "bg-orange-500", icone: WifiOff, texto: "GPS Bloqueado" },
  };

  const cfg = statusConfig[gps.status];
  const Icon = cfg.icone;

  if (!ativo) return null;

  return (
    <div
      className={`fixed right-3 z-50 flex items-center gap-1.5 rounded-full ${cfg.cor} px-3 py-1.5 text-xs font-medium text-white shadow-lg`}
      style={{ bottom: "calc(4.5rem + env(safe-area-inset-bottom, 0px) + 0.75rem)" }}
    >
      <Icon className="h-3.5 w-3.5" />
      {cfg.texto}
    </div>
  );
}

export default function MotoboyLayout({ children, hideNav }: MotoboyLayoutProps) {
  const [location, navigate] = useLocation();
  const { motoboy } = useMotoboyAuth();

  const { data: config } = useMotoboyConfig();
  const permitirSaldo = (config as Record<string, boolean> | undefined)?.permitir_ver_saldo ?? true;
  const gpsAtivo = !!motoboy?.disponivel;

  const tabs = [
    { path: "/", label: "Entregas", icon: Package, disabled: false },
    { path: "/ganhos", label: "Ganhos", icon: permitirSaldo ? DollarSign : Lock, disabled: !permitirSaldo },
    { path: "/perfil", label: "Perfil", icon: User, disabled: false },
  ];

  const isActive = (path: string) => {
    if (path === "/") {
      return location === "/" || location.startsWith("/entrega");
    }
    return location.startsWith(path);
  };

  return (
    <div className="flex min-h-screen flex-col bg-gray-950 text-white">
      {/* Header */}
      <header
        className="sticky top-0 z-40 border-b border-gray-800 bg-gray-900/95 px-4 py-3 backdrop-blur"
        style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top, 0px))" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <img
              src="/derekh-motoboy-icon.png"
              alt="Derekh"
              className="h-7 w-7 rounded-md"
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
            <span className="text-sm font-bold tracking-tight">Derekh Entregador</span>
          </div>
          {motoboy && (
            <div className="flex items-center gap-2">
              {motoboy.disponivel ? (
                <span className="flex items-center gap-1.5 rounded-full bg-green-500/20 px-3 py-1 text-xs font-semibold text-green-400">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-green-400" />
                  </span>
                  Online
                </span>
              ) : (
                <span className="flex items-center gap-1.5 rounded-full bg-gray-700/60 px-3 py-1 text-xs font-medium text-gray-400">
                  <WifiOff className="h-3 w-3" /> Offline
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Content — padding bottom accounts for nav bar + safe area */}
      <main
        className="flex-1 overflow-y-auto"
        style={{ paddingBottom: hideNav ? "1rem" : "calc(4.5rem + env(safe-area-inset-bottom, 0px))" }}
      >
        {children}
      </main>

      {/* GPS Indicator */}
      <GPSIndicator ativo={gpsAtivo} />

      {/* Bottom Navigation — respects safe-area-inset-bottom */}
      {!hideNav && (
        <nav
          className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-800 bg-gray-900/95 backdrop-blur-lg"
          style={{ paddingBottom: "env(safe-area-inset-bottom, 0px)" }}
        >
          <div className="flex items-center justify-around">
            {tabs.map((tab) => {
              const active = isActive(tab.path);
              const Icon = tab.icon;
              return (
                <button
                  key={tab.path}
                  onClick={() => !tab.disabled && navigate(tab.path)}
                  disabled={tab.disabled}
                  className={`flex flex-1 flex-col items-center gap-1 py-2.5 transition-colors ${
                    tab.disabled
                      ? "text-gray-700 opacity-60"
                      : active
                        ? "text-green-400"
                        : "text-gray-500 active:text-gray-300"
                  }`}
                >
                  <Icon className={`h-5 w-5 ${active ? "drop-shadow-[0_0_6px_rgba(74,222,128,0.5)]" : ""}`} />
                  <span className={`text-[10px] font-semibold ${active ? "text-green-400" : ""}`}>{tab.label}</span>
                  {active && <span className="h-0.5 w-5 rounded-full bg-green-400" />}
                </button>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
}
