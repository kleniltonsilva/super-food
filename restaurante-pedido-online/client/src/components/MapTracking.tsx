import { useEffect, useRef, useCallback } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

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

/**
 * Calcula distância em km entre dois pontos (Haversine).
 */
function calcDistanciaKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Zoom progressivo baseado na distância entre motoboy e destino.
 */
function getZoomByDistance(distKm: number): number {
  if (distKm > 5) return 13;
  if (distKm > 2) return 14;
  if (distKm > 1) return 15;
  if (distKm > 0.5) return 16;
  return 17;
}

/** Cria elemento HTML do ícone do motoboy */
function criarElementoMotoboy(rotation = 0): HTMLDivElement {
  const el = document.createElement("div");
  el.innerHTML = `
    <div style="position:relative;width:48px;height:48px;">
      <div style="
        position:absolute;inset:0;border-radius:50%;
        background:rgba(227,26,36,0.25);
        animation:moto-pulse 1.5s ease-in-out infinite;
      "></div>
      <div style="
        position:absolute;inset:4px;
        background:#E31A24;color:white;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        font-size:22px;
        box-shadow:0 2px 10px rgba(0,0,0,0.5);
        border:2px solid white;
        transform:rotate(${rotation}deg);
        transition:transform 0.5s ease;
      ">🏍️</div>
    </div>
  `;
  el.style.width = "48px";
  el.style.height = "48px";
  return el;
}

/** Cria elemento HTML do ícone do destino (casa) */
function criarElementoDestino(): HTMLDivElement {
  const el = document.createElement("div");
  el.innerHTML = `
    <div style="position:relative;width:44px;height:52px;display:flex;flex-direction:column;align-items:center;">
      <div style="
        background:#22c55e;color:white;border-radius:50%;
        width:40px;height:40px;
        display:flex;align-items:center;justify-content:center;
        font-size:22px;
        box-shadow:0 2px 10px rgba(0,0,0,0.4);
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
  el.style.width = "44px";
  el.style.height = "52px";
  return el;
}

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
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const motoboyMarkerRef = useRef<mapboxgl.Marker | null>(null);
  const destinoMarkerRef = useRef<mapboxgl.Marker | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const prevPosRef = useRef<{ lat: number; lng: number } | null>(null);
  const bearingRef = useRef<number>(0);
  const ultimaRotaRef = useRef<number>(0); // timestamp da última busca de rota
  const rotaCarregadaRef = useRef(false);

  // Buscar rota real via Mapbox Directions API
  const buscarRota = useCallback(async (
    mLat: number, mLng: number, dLat: number, dLng: number
  ) => {
    if (!MAPBOX_TOKEN || !mapRef.current) return;

    // Rate limit: máx 1 requisição a cada 30s
    const agora = Date.now();
    if (agora - ultimaRotaRef.current < 30000 && rotaCarregadaRef.current) return;
    ultimaRotaRef.current = agora;

    try {
      const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${mLng},${mLat};${dLng},${dLat}?geometries=geojson&overview=full&access_token=${MAPBOX_TOKEN}`;
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      const route = data.routes?.[0]?.geometry;
      if (!route || !mapRef.current) return;

      const map = mapRef.current;
      const source = map.getSource("route") as mapboxgl.GeoJSONSource | undefined;

      if (source) {
        source.setData({
          type: "Feature",
          properties: {},
          geometry: route,
        });
      } else {
        // Adicionar source e layer na primeira vez
        map.addSource("route", {
          type: "geojson",
          data: {
            type: "Feature",
            properties: {},
            geometry: route,
          },
        });
        // Contorno da rota (sombra)
        map.addLayer({
          id: "route-outline",
          type: "line",
          source: "route",
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": "#000000",
            "line-width": 8,
            "line-opacity": 0.3,
          },
        });
        // Rota principal
        map.addLayer({
          id: "route-line",
          type: "line",
          source: "route",
          layout: { "line-join": "round", "line-cap": "round" },
          paint: {
            "line-color": "#E31A24",
            "line-width": 5,
            "line-opacity": 0.85,
          },
        });
      }
      rotaCarregadaRef.current = true;
    } catch {
      // Falha silenciosa — mapa continua funcionando sem rota
    }
  }, []);

  // Inicializar mapa (apenas uma vez)
  useEffect(() => {
    if (!containerRef.current || mapRef.current || !MAPBOX_TOKEN) return;

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [motoboyLng, motoboyLat],
      zoom: 15,
      attributionControl: false,
    });

    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "top-right");

    map.on("load", () => {
      // Marker do motoboy
      const motoboyEl = criarElementoMotoboy(0);
      const motoboyPopup = new mapboxgl.Popup({ offset: 25, closeButton: false }).setHTML(
        `<strong style="color:#333;">🏍️ ${motoboyNome}</strong><br><small style="color:#666;">Entregador em rota</small>`
      );
      const motoboyMarker = new mapboxgl.Marker({ element: motoboyEl, anchor: "center" })
        .setLngLat([motoboyLng, motoboyLat])
        .setPopup(motoboyPopup)
        .addTo(map);
      motoboyMarkerRef.current = motoboyMarker;

      // Marker do destino
      if (destinoLat && destinoLng) {
        const destinoEl = criarElementoDestino();
        const destinoPopup = new mapboxgl.Popup({ offset: 25, closeButton: false }).setHTML(
          `<strong style="color:#333;">🏠 Seu endereço</strong><br><small style="color:#666;">${destinoLabel || "Destino de entrega"}</small>`
        );
        const destinoMarker = new mapboxgl.Marker({ element: destinoEl, anchor: "bottom" })
          .setLngLat([destinoLng, destinoLat])
          .setPopup(destinoPopup)
          .addTo(map);
        destinoMarkerRef.current = destinoMarker;

        // Ajustar bounds para mostrar motoboy e destino
        const bounds = new mapboxgl.LngLatBounds()
          .extend([motoboyLng, motoboyLat])
          .extend([destinoLng, destinoLat]);
        map.fitBounds(bounds, { padding: 70, maxZoom: 16 });

        // Buscar rota real
        buscarRota(motoboyLat, motoboyLng, destinoLat, destinoLng);
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      motoboyMarkerRef.current = null;
      destinoMarkerRef.current = null;
      rotaCarregadaRef.current = false;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Atualizar posição do motoboy em tempo real
  useEffect(() => {
    if (!motoboyMarkerRef.current || !mapRef.current) return;

    const map = mapRef.current;

    // Calcular bearing
    if (prevPosRef.current) {
      const { lat: pLat, lng: pLng } = prevPosRef.current;
      const dist = Math.hypot(motoboyLat - pLat, motoboyLng - pLng);
      if (dist > 0.00005) {
        bearingRef.current = calcBearing(pLat, pLng, motoboyLat, motoboyLng);
      }
    }
    prevPosRef.current = { lat: motoboyLat, lng: motoboyLng };

    // Atualizar posição e ícone com rotação
    motoboyMarkerRef.current.setLngLat([motoboyLng, motoboyLat]);
    const newEl = criarElementoMotoboy(bearingRef.current);
    const markerEl = motoboyMarkerRef.current.getElement();
    markerEl.innerHTML = newEl.innerHTML;

    // Zoom progressivo + flyTo suave
    if (destinoLat && destinoLng) {
      const distKm = calcDistanciaKm(motoboyLat, motoboyLng, destinoLat, destinoLng);
      const targetZoom = getZoomByDistance(distKm);

      // Centralizar entre motoboy e destino
      const centerLat = (motoboyLat + destinoLat) / 2;
      const centerLng = (motoboyLng + destinoLng) / 2;

      map.flyTo({
        center: [centerLng, centerLat],
        zoom: targetZoom,
        speed: 0.8,
        curve: 1,
      });

      // Atualizar rota (rate limited internamente)
      buscarRota(motoboyLat, motoboyLng, destinoLat, destinoLng);
    } else {
      map.flyTo({
        center: [motoboyLng, motoboyLat],
        speed: 0.8,
      });
    }
  }, [motoboyLat, motoboyLng, destinoLat, destinoLng, buscarRota]);

  if (!MAPBOX_TOKEN) {
    return (
      <div style={{
        width: "100%",
        height: "340px",
        borderRadius: "12px",
        background: "#1a1a2e",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#888",
        fontSize: "14px",
      }}>
        Mapa indisponível — token não configurado
      </div>
    );
  }

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
