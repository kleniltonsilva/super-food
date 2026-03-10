import { useEffect, useRef, useState, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import AdminLayout from "@/admin/components/AdminLayout";
import { useAdminAuth } from "@/admin/contexts/AdminAuthContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RefreshCw, MapPin, Bike, Clock } from "lucide-react";

// ─── Tipos ──────────────────────────────────────────────
interface MotoboyGPS {
  motoboy_id: number;
  nome: string;
  latitude: number;
  longitude: number;
  velocidade: number;
  ultima_atualizacao: string;
  em_rota: boolean;
  entregas_pendentes: number;
}

// ─── Token do Mapbox via variável de ambiente ───────────
const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

// ─── Formata tempo relativo ──────────────────────────────
function tempoRelativo(isoStr: string): string {
  if (!isoStr) return "—";
  const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 1000);
  if (diff < 60) return `${diff}s atrás`;
  if (diff < 3600) return `${Math.floor(diff / 60)}min atrás`;
  return `${Math.floor(diff / 3600)}h atrás`;
}

// ─── Cria elemento HTML para o marcador ─────────────────
function criarElementoMarcador(nome: string, emRota: boolean): HTMLDivElement {
  const el = document.createElement("div");
  el.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
  `;
  const circulo = document.createElement("div");
  circulo.style.cssText = `
    width: 36px;
    height: 36px;
    border-radius: 50%;
    background: ${emRota ? "#f59e0b" : "#22c55e"};
    border: 3px solid white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  `;
  circulo.textContent = "🏍️";

  const label = document.createElement("div");
  label.style.cssText = `
    margin-top: 2px;
    background: rgba(0,0,0,0.75);
    color: white;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 6px;
    border-radius: 4px;
    white-space: nowrap;
    max-width: 100px;
    overflow: hidden;
    text-overflow: ellipsis;
  `;
  label.textContent = nome.split(" ")[0];
  el.appendChild(circulo);
  el.appendChild(label);
  return el;
}

// ─── Componente sem token configurado ───────────────────
function AvisoSemToken() {
  return (
    <AdminLayout>
      <div className="flex flex-col items-center justify-center h-[70vh] gap-4 text-center">
        <MapPin className="w-16 h-16 text-muted-foreground" />
        <h2 className="text-2xl font-bold">Mapa de Motoboys</h2>
        <p className="text-muted-foreground max-w-md">
          Para usar o mapa, configure a variável de ambiente{" "}
          <code className="bg-muted px-2 py-0.5 rounded text-sm font-mono">
            VITE_MAPBOX_TOKEN
          </code>{" "}
          com seu token do Mapbox GL JS.
        </p>
        <p className="text-sm text-muted-foreground">
          Obtenha seu token gratuito em{" "}
          <a
            href="https://account.mapbox.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-500 underline"
          >
            account.mapbox.com
          </a>
        </p>
      </div>
    </AdminLayout>
  );
}

// ─── Componente principal ────────────────────────────────
export default function MapaMotoboys() {
  if (!MAPBOX_TOKEN) return <AvisoSemToken />;

  return <MapaMotoboyComToken token={MAPBOX_TOKEN} />;
}

function MapaMotoboyComToken({ token }: { token: string }) {
  const { restaurante } = useAdminAuth();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const marcadoresRef = useRef<Map<number, mapboxgl.Marker>>(new Map());
  const [motoboys, setMotoboys] = useState<MotoboyGPS[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [ultimaAtualizacao, setUltimaAtualizacao] = useState<Date | null>(null);
  const [motoboyAtivo, setMotoboyAtivo] = useState<number | null>(null);

  const buscarMotoboys = useCallback(async () => {
    if (!restaurante?.id) return;
    try {
      const token_admin = localStorage.getItem("sf_admin_token");
      const res = await fetch(`/api/gps/motoboys/${restaurante.id}`, {
        headers: token_admin ? { Authorization: `Bearer ${token_admin}` } : {},
      });
      if (!res.ok) return;
      const dados: MotoboyGPS[] = await res.json();
      setMotoboys(dados);
      setUltimaAtualizacao(new Date());
      atualizarMarcadores(dados);
    } catch {
      // falha silenciosa na atualização periódica
    } finally {
      setCarregando(false);
    }
  }, [restaurante?.id]);

  const atualizarMarcadores = useCallback((dados: MotoboyGPS[]) => {
    const map = mapRef.current;
    if (!map) return;

    const idsAtivos = new Set(dados.map((m) => m.motoboy_id));

    // Remover marcadores de motoboys que saíram
    marcadoresRef.current.forEach((marker, id) => {
      if (!idsAtivos.has(id)) {
        marker.remove();
        marcadoresRef.current.delete(id);
      }
    });

    // Adicionar ou atualizar marcadores
    dados.forEach((m) => {
      const existente = marcadoresRef.current.get(m.motoboy_id);
      if (existente) {
        existente.setLngLat([m.longitude, m.latitude]);
      } else {
        const el = criarElementoMarcador(m.nome, m.em_rota);
        const popup = new mapboxgl.Popup({ offset: 25, closeButton: false }).setHTML(`
          <div style="font-family: sans-serif; min-width: 160px;">
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">${m.nome}</div>
            <div style="font-size: 12px; color: #666;">
              ${m.em_rota ? "🟡 Em rota" : "🟢 Disponível"}<br/>
              Entregas pendentes: <b>${m.entregas_pendentes}</b><br/>
              ${m.velocidade > 0 ? `Velocidade: <b>${m.velocidade.toFixed(0)} km/h</b><br/>` : ""}
              Atualizado: ${tempoRelativo(m.ultima_atualizacao)}
            </div>
          </div>
        `);
        const marker = new mapboxgl.Marker({ element: el })
          .setLngLat([m.longitude, m.latitude])
          .setPopup(popup)
          .addTo(map);
        marcadoresRef.current.set(m.motoboy_id, marker);
      }
    });
  }, []);

  // Inicializar mapa
  useEffect(() => {
    if (!mapContainerRef.current) return;
    mapboxgl.accessToken = token;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/streets-v12",
      center: [-46.6333, -23.5505], // São Paulo como padrão
      zoom: 13,
    });

    map.addControl(new mapboxgl.NavigationControl(), "top-right");
    map.addControl(new mapboxgl.GeolocateControl({ trackUserLocation: false }), "top-right");

    mapRef.current = map;

    return () => {
      marcadoresRef.current.forEach((m) => m.remove());
      marcadoresRef.current.clear();
      map.remove();
      mapRef.current = null;
    };
  }, [token]);

  // Busca inicial e polling a cada 15s
  useEffect(() => {
    buscarMotoboys();
    const interval = setInterval(buscarMotoboys, 15_000);
    return () => clearInterval(interval);
  }, [buscarMotoboys]);

  // Centralizar no motoboy selecionado
  const centralizarMotoboy = (m: MotoboyGPS) => {
    setMotoboyAtivo(m.motoboy_id);
    mapRef.current?.flyTo({
      center: [m.longitude, m.latitude],
      zoom: 16,
      speed: 1.5,
    });
    marcadoresRef.current.get(m.motoboy_id)?.togglePopup();
  };

  return (
    <AdminLayout>
      <div className="flex flex-col h-[calc(100vh-120px)] gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Mapa de Motoboys</h1>
            {ultimaAtualizacao && (
              <p className="text-sm text-muted-foreground flex items-center gap-1 mt-0.5">
                <Clock className="w-3 h-3" />
                Atualizado: {ultimaAtualizacao.toLocaleTimeString("pt-BR")} · atualiza a cada 15s
              </p>
            )}
          </div>
          <Button variant="outline" size="sm" onClick={buscarMotoboys} disabled={carregando}>
            <RefreshCw className={`w-4 h-4 mr-2 ${carregando ? "animate-spin" : ""}`} />
            Atualizar
          </Button>
        </div>

        {/* Layout: mapa + sidebar */}
        <div className="flex gap-4 flex-1 overflow-hidden">
          {/* Mapa */}
          <div className="flex-1 rounded-xl overflow-hidden border shadow-sm">
            <div ref={mapContainerRef} className="w-full h-full" />
          </div>

          {/* Sidebar com lista */}
          <div className="w-72 flex flex-col gap-2 overflow-y-auto">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground px-1">
              <Bike className="w-4 h-4" />
              {motoboys.length} motoboys online
            </div>

            {carregando ? (
              <div className="flex flex-col gap-2">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-24 bg-muted rounded-lg animate-pulse" />
                ))}
              </div>
            ) : motoboys.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Bike className="w-10 h-10 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Nenhum motoboy online</p>
              </div>
            ) : (
              motoboys.map((m) => (
                <button
                  key={m.motoboy_id}
                  onClick={() => centralizarMotoboy(m)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors hover:bg-accent ${
                    motoboyAtivo === m.motoboy_id ? "border-primary bg-accent" : "border-border bg-card"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-semibold text-sm truncate">{m.nome}</div>
                    <Badge
                      variant="outline"
                      className={`shrink-0 text-xs ${
                        m.em_rota
                          ? "border-amber-500 text-amber-600"
                          : "border-green-500 text-green-600"
                      }`}
                    >
                      {m.em_rota ? "Em rota" : "Livre"}
                    </Badge>
                  </div>

                  <div className="mt-1.5 space-y-0.5 text-xs text-muted-foreground">
                    {m.entregas_pendentes > 0 && (
                      <div>
                        📦 {m.entregas_pendentes} entrega{m.entregas_pendentes !== 1 ? "s" : ""} pendente
                        {m.entregas_pendentes !== 1 ? "s" : ""}
                      </div>
                    )}
                    {m.velocidade > 0 && <div>⚡ {m.velocidade.toFixed(0)} km/h</div>}
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {tempoRelativo(m.ultima_atualizacao)}
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
