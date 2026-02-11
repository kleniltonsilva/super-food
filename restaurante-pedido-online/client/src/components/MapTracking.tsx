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

// Ícone do motoboy (moto)
const motoboyIcon = L.divIcon({
  className: "motoboy-marker",
  html: `<div style="background:#E31A24;color:white;border-radius:50%;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 2px 8px rgba(0,0,0,0.3);border:2px solid white;">🏍️</div>`,
  iconSize: [40, 40],
  iconAnchor: [20, 20],
});

// Ícone do destino (casa)
const destinoIcon = L.divIcon({
  className: "destino-marker",
  html: `<div style="background:#22c55e;color:white;border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-size:18px;box-shadow:0 2px 8px rgba(0,0,0,0.3);border:2px solid white;">📍</div>`,
  iconSize: [36, 36],
  iconAnchor: [18, 18],
});

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
  const containerRef = useRef<HTMLDivElement>(null);

  // Inicializar mapa
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [motoboyLat, motoboyLng],
      zoom: 15,
      zoomControl: true,
      attributionControl: false,
    });

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(map);

    // Marker do motoboy
    const motoboyMarker = L.marker([motoboyLat, motoboyLng], { icon: motoboyIcon })
      .addTo(map)
      .bindPopup(`🏍️ ${motoboyNome}`);
    motoboyMarkerRef.current = motoboyMarker;

    // Marker do destino
    if (destinoLat && destinoLng) {
      const destMarker = L.marker([destinoLat, destinoLng], { icon: destinoIcon })
        .addTo(map)
        .bindPopup(`📍 ${destinoLabel || "Seu endereço"}`);
      destinoMarkerRef.current = destMarker;

      // Fit bounds para mostrar motoboy e destino
      const bounds = L.latLngBounds(
        [motoboyLat, motoboyLng],
        [destinoLat, destinoLng]
      );
      map.fitBounds(bounds, { padding: [50, 50] });
    }

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      motoboyMarkerRef.current = null;
      destinoMarkerRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Atualizar posição do motoboy suavemente
  useEffect(() => {
    if (!motoboyMarkerRef.current || !mapRef.current) return;

    const newLatLng = L.latLng(motoboyLat, motoboyLng);
    motoboyMarkerRef.current.setLatLng(newLatLng);

    // Se tem destino, ajustar bounds
    if (destinoLat && destinoLng) {
      const bounds = L.latLngBounds(
        [motoboyLat, motoboyLng],
        [destinoLat, destinoLng]
      );
      mapRef.current.fitBounds(bounds, { padding: [50, 50], animate: true });
    } else {
      mapRef.current.panTo(newLatLng, { animate: true });
    }
  }, [motoboyLat, motoboyLng, destinoLat, destinoLng]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "300px", borderRadius: "12px", overflow: "hidden" }}
    />
  );
}
