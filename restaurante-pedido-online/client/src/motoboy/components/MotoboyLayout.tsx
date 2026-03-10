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
    <div className={`fixed bottom-20 right-3 z-50 flex items-center gap-1.5 rounded-full ${cfg.cor} px-3 py-1.5 text-xs font-medium text-white shadow-lg`}>
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
      <header className="sticky top-0 z-40 border-b border-gray-800 bg-gray-900/95 px-4 py-3 backdrop-blur">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5 text-green-500" />
            <span className="text-sm font-semibold">Super Food</span>
          </div>
          {motoboy && (
            <div className="flex items-center gap-2">
              {motoboy.disponivel ? (
                <span className="flex items-center gap-1 rounded-full bg-green-500/20 px-2.5 py-0.5 text-xs font-medium text-green-400">
                  <Wifi className="h-3 w-3" /> Online
                </span>
              ) : (
                <span className="flex items-center gap-1 rounded-full bg-gray-700 px-2.5 py-0.5 text-xs font-medium text-gray-400">
                  <WifiOff className="h-3 w-3" /> Offline
                </span>
              )}
            </div>
          )}
        </div>
      </header>

      {/* Content */}
      <main className="flex-1 overflow-y-auto pb-20">
        {children}
      </main>

      {/* GPS Indicator */}
      <GPSIndicator ativo={gpsAtivo} />

      {/* Bottom Navigation */}
      {!hideNav && (
        <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-gray-800 bg-gray-900/95 backdrop-blur">
          <div className="flex items-center justify-around">
            {tabs.map((tab) => {
              const active = isActive(tab.path);
              const Icon = tab.icon;
              return (
                <button
                  key={tab.path}
                  onClick={() => !tab.disabled && navigate(tab.path)}
                  disabled={tab.disabled}
                  className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 transition-colors ${
                    tab.disabled
                      ? "text-gray-700 opacity-60"
                      : active
                        ? "text-green-500"
                        : "text-gray-500"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-[10px] font-medium">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
}
