import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface MapTrackingProps {
  motoboyLat: number;
  motoboyLng: number;
  motoboyNome: string;
  destinoLat?: number;
  destinoLng?: number;
  destinoLabel?: string;
}

/**
 * Calcula bearing (direção em graus) de ponto A para ponto B.
 * Usado para rotacionar o ícone da moto na direção do movimento.
 */
function calcBearing(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLng = toRad(lng2 - lng1);
  const lat1R = toRad(lat1);
  const lat2R = toRad(lat2);
  const y = Math.sin(dLng) * Math.cos(lat2R);
  const x = Math.cos(lat1R) * Math.sin(lat2R) - Math.sin(lat1R) * Math.cos(lat2R) * Math.cos(dLng);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

/** Cria o HTML do ícone da moto com rotação e animação de pulso */
function motoboyIconHtml(rotation = 0) {
  return `
    <div style="position:relative;width:48px;height:48px;">
      <div style="
        position:absolute;inset:0;border-radius:50%;
        background:rgba(227,26,36,0.2);
        animation:moto-pulse 1.5s ease-in-out infinite;
      "></div>
      <div style="
        position:absolute;inset:4px;
        background:#E31A24;color:white;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        font-size:22px;
        box-shadow:0 2px 10px rgba(0,0,0,0.4);
        border:2px solid white;
        transform:rotate(${rotation}deg);
        transition:transform 0.5s ease;
      ">🏍️</div>
    </div>
  `;
}

/** Ícone da casa do cliente */
const destinoIconHtml = `
  <div style="position:relative;width:44px;height:52px;display:flex;flex-direction:column;align-items:center;">
    <div style="
      background:#22c55e;color:white;border-radius:50%;
      width:40px;height:40px;
      display:flex;align-items:center;justify-content:center;
      font-size:22px;
      box-shadow:0 2px 10px rgba(0,0,0,0.35);
      border:2px solid white;
    ">🏠</div>
    <div style="
      width:0;height:0;
      border-left:8px solid transparent;
      border-right:8px solid transparent;
      border-top:10px solid #22c55e;
      margin-top:-2px;
    "></div>
  </div>
`;

// Injetar keyframes de animação no document (uma vez)
if (typeof document !== "undefined" && !document.getElementById("moto-pulse-style")) {
  const style = document.createElement("style");
  style.id = "moto-pulse-style";
  style.textContent = `
    @keyframes moto-pulse {
      0%, 100% { transform: scale(1); opacity: 0.4; }
      50% { transform: scale(1.6); opacity: 0; }
    }
  `;
  document.head.appendChild(style);
}

export default function MapTracking({
  motoboyLat,
  motoboyLng,
  motoboyNome,
  destinoLat,
  destinoLng,
  destinoLabel,
}: MapTrackingProps) {
  const mapRef = useRef<L.Map | null>(null);
  const motoboyMarkerRef = useRef<L.Marker | null>(null);
  const destinoMarkerRef = useRef<L.Marker | null>(null);
  const routeLineRef = useRef<L.Polyline | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevPosRef = useRef<{ lat: number; lng: number } | null>(null);
  const bearingRef = useRef<number>(0);

  // Inicializar mapa (apenas uma vez)
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [motoboyLat, motoboyLng],
      zoom: 15,
      zoomControl: true,
      attributionControl: false,
    });

    // Tiles OpenStreetMap com visual limpo
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(map);

    // Marker do motoboy
    const motoIcon = L.divIcon({
      className: "",
      html: motoboyIconHtml(0),
      iconSize: [48, 48],
      iconAnchor: [24, 24],
      popupAnchor: [0, -28],
    });

    const motoboyMarker = L.marker([motoboyLat, motoboyLng], { icon: motoIcon })
      .addTo(map)
      .bindPopup(`<strong>🏍️ ${motoboyNome}</strong><br><small>Entregador em rota</small>`, {
        closeButton: false,
      });
    motoboyMarkerRef.current = motoboyMarker;

    // Marker do destino (casa do cliente)
    if (destinoLat && destinoLng) {
      const destIcon = L.divIcon({
        className: "",
        html: destinoIconHtml,
        iconSize: [44, 52],
        iconAnchor: [22, 52],
        popupAnchor: [0, -54],
      });

      const destMarker = L.marker([destinoLat, destinoLng], { icon: destIcon })
        .addTo(map)
        .bindPopup(`<strong>🏠 Seu endereço</strong><br><small>${destinoLabel || "Destino de entrega"}</small>`, {
          closeButton: false,
        });
      destinoMarkerRef.current = destMarker;

      // Linha tracejada ligando motoboy ao destino
      const routeLine = L.polyline(
        [[motoboyLat, motoboyLng], [destinoLat, destinoLng]],
        {
          color: "#E31A24",
          weight: 3,
          opacity: 0.6,
          dashArray: "8, 10",
        }
      ).addTo(map);
      routeLineRef.current = routeLine;

      // Centralizar mapa para mostrar motoboy e destino
      const bounds = L.latLngBounds(
        [motoboyLat, motoboyLng],
        [destinoLat, destinoLng]
      );
      map.fitBounds(bounds, { padding: [60, 60] });
    }

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      motoboyMarkerRef.current = null;
      destinoMarkerRef.current = null;
      routeLineRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Atualizar posição do motoboy com rotação em tempo real
  useEffect(() => {
    if (!motoboyMarkerRef.current || !mapRef.current) return;

    const newLatLng = L.latLng(motoboyLat, motoboyLng);

    // Calcular bearing para rotacionar o ícone na direção do movimento
    if (prevPosRef.current) {
      const { lat: pLat, lng: pLng } = prevPosRef.current;
      const dist = Math.hypot(motoboyLat - pLat, motoboyLng - pLng);
      if (dist > 0.00005) { // só atualiza bearing se moveu o suficiente
        bearingRef.current = calcBearing(pLat, pLng, motoboyLat, motoboyLng);
      }
    }
    prevPosRef.current = { lat: motoboyLat, lng: motoboyLng };

    // Atualizar posição e ícone com nova rotação
    motoboyMarkerRef.current.setLatLng(newLatLng);
    const updatedIcon = L.divIcon({
      className: "",
      html: motoboyIconHtml(bearingRef.current),
      iconSize: [48, 48],
      iconAnchor: [24, 24],
      popupAnchor: [0, -28],
    });
    motoboyMarkerRef.current.setIcon(updatedIcon);

    // Atualizar linha tracejada
    if (routeLineRef.current && destinoLat && destinoLng) {
      routeLineRef.current.setLatLngs([
        [motoboyLat, motoboyLng],
        [destinoLat, destinoLng],
      ]);
    }

    // Ajustar bounds para manter ambos visíveis com suavidade
    if (destinoLat && destinoLng) {
      const bounds = L.latLngBounds(
        [motoboyLat, motoboyLng],
        [destinoLat, destinoLng]
      );
      mapRef.current.fitBounds(bounds, { padding: [60, 60], animate: true });
    } else {
      mapRef.current.panTo(newLatLng, { animate: true });
    }
  }, [motoboyLat, motoboyLng, destinoLat, destinoLng]);

  return (
    <div style={{ position: "relative" }}>
      <div
        ref={containerRef}
        style={{ width: "100%", height: "340px", borderRadius: "12px", overflow: "hidden" }}
      />
      {/* Badge "ao vivo" */}
      <div style={{
        position: "absolute",
        top: 10,
        left: 10,
        background: "rgba(0,0,0,0.7)",
        color: "white",
        borderRadius: "20px",
        padding: "4px 10px",
        fontSize: "11px",
        display: "flex",
        alignItems: "center",
        gap: "5px",
        backdropFilter: "blur(4px)",
        zIndex: 1000,
      }}>
        <span style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#22c55e",
          display: "inline-block",
          animation: "moto-pulse 1.5s ease-in-out infinite",
        }} />
        Ao vivo
      </div>
    </div>
  );
}
