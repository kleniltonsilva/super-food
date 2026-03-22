import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN as string | undefined;

interface DemoMapAnimationProps {
  centroLat: number;
  centroLng: number;
  duration?: number; // duração em ms (default: 60000 = 1 min)
}

/**
 * Rota pré-definida com offsets relativos ao centro (destino).
 * Simula rota urbana em L — motoboy começa distante e chega ao destino.
 */
const ROUTE_OFFSETS: [number, number][] = [
  [+0.0030, -0.0040], // Início: norte-oeste
  [+0.0030, -0.0020], // Leste (rua horizontal)
  [+0.0030, +0.0000], // Leste (continua)
  [+0.0015, +0.0000], // Sul (vira esquina)
  [+0.0015, +0.0015], // Sudeste
  [+0.0000, +0.0015], // Sul (vira esquina)
  [+0.0000, +0.0000], // Chega ao destino (centro)
];

/** Distância entre dois pontos (simplificado, graus) */
function dist(a: [number, number], b: [number, number]): number {
  const dlat = b[0] - a[0];
  const dlng = b[1] - a[1];
  return Math.sqrt(dlat * dlat + dlng * dlng);
}

/** Calcula bearing (graus) de A para B */
function bearing(a: [number, number], b: [number, number]): number {
  const dLng = ((b[1] - a[1]) * Math.PI) / 180;
  const lat1 = (a[0] * Math.PI) / 180;
  const lat2 = (b[0] * Math.PI) / 180;
  const y = Math.sin(dLng) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);
  return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
}

/** Interpola posição ao longo da polyline por distância acumulada (velocidade constante) */
function interpolateByDistance(
  points: [number, number][],
  cumulDists: number[],
  totalDist: number,
  progress: number,
): [number, number] {
  const targetDist = progress * totalDist;

  // Encontra segmento
  for (let i = 0; i < cumulDists.length - 1; i++) {
    if (targetDist <= cumulDists[i + 1]) {
      const segStart = cumulDists[i];
      const segLen = cumulDists[i + 1] - segStart;
      const t = segLen > 0 ? (targetDist - segStart) / segLen : 0;
      const lat = points[i][0] + (points[i + 1][0] - points[i][0]) * t;
      const lng = points[i][1] + (points[i + 1][1] - points[i][1]) * t;
      return [lat, lng];
    }
  }
  return points[points.length - 1];
}

/** Cria elemento HTML do ícone do motoboy */
function criarElementoMotoboy(): HTMLDivElement {
  const el = document.createElement("div");
  el.innerHTML = `
    <div style="position:relative;width:48px;height:48px;">
      <div class="demo-moto-pulse" style="
        position:absolute;inset:0;border-radius:50%;
        background:rgba(227,26,36,0.25);
      "></div>
      <div class="demo-moto-icon" style="
        position:absolute;inset:4px;
        background:#E31A24;color:white;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        font-size:22px;
        box-shadow:0 2px 10px rgba(0,0,0,0.5);
        border:2px solid white;
        transition:transform 0.3s ease;
      ">🏍️</div>
    </div>
  `;
  el.style.width = "48px";
  el.style.height = "48px";
  return el;
}

/** Cria elemento HTML do ícone do destino */
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

// Injetar keyframes (uma vez)
if (typeof document !== "undefined" && !document.getElementById("demo-map-anim-style")) {
  const style = document.createElement("style");
  style.id = "demo-map-anim-style";
  style.textContent = `
    @keyframes demo-pulse {
      0%, 100% { transform: scale(1); opacity: 0.4; }
      50% { transform: scale(1.6); opacity: 0; }
    }
    .demo-moto-pulse {
      animation: demo-pulse 1.5s ease-in-out infinite;
    }
  `;
  document.head.appendChild(style);
}

export default function DemoMapAnimation({
  centroLat,
  centroLng,
  duration = 60000,
}: DemoMapAnimationProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markerRef = useRef<mapboxgl.Marker | null>(null);
  const animRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  useEffect(() => {
    if (!containerRef.current || !MAPBOX_TOKEN) return;

    // Calcular rota absoluta
    const routePoints: [number, number][] = ROUTE_OFFSETS.map(([dlat, dlng]) => [
      centroLat + dlat,
      centroLng + dlng,
    ]);

    // Pré-calcular distâncias acumuladas para interpolação uniforme
    const cumulDists: number[] = [0];
    for (let i = 1; i < routePoints.length; i++) {
      cumulDists.push(cumulDists[i - 1] + dist(routePoints[i - 1], routePoints[i]));
    }
    const totalDist = cumulDists[cumulDists.length - 1];

    // GeoJSON da rota (lng, lat para Mapbox)
    const routeGeoJSON: GeoJSON.Feature<GeoJSON.LineString> = {
      type: "Feature",
      properties: {},
      geometry: {
        type: "LineString",
        coordinates: routePoints.map(([lat, lng]) => [lng, lat]),
      },
    };

    mapboxgl.accessToken = MAPBOX_TOKEN;

    const map = new mapboxgl.Map({
      container: containerRef.current,
      style: "mapbox://styles/mapbox/satellite-streets-v12",
      center: [centroLng, centroLat],
      zoom: 15,
      attributionControl: false,
    });

    mapRef.current = map;

    map.on("load", () => {
      // Fit bounds para mostrar toda a rota
      const bounds = new mapboxgl.LngLatBounds();
      routePoints.forEach(([lat, lng]) => bounds.extend([lng, lat]));
      map.fitBounds(bounds, { padding: 60, maxZoom: 16 });

      // Desenhar rota completa — contorno preto
      map.addSource("demo-route", {
        type: "geojson",
        data: routeGeoJSON,
      });

      map.addLayer({
        id: "demo-route-outline",
        type: "line",
        source: "demo-route",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#000000",
          "line-width": 8,
          "line-opacity": 0.3,
        },
      });

      // Rota completa (fundo — mais transparente)
      map.addLayer({
        id: "demo-route-bg",
        type: "line",
        source: "demo-route",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#E31A24",
          "line-width": 5,
          "line-opacity": 0.35,
        },
      });

      // Rota percorrida (destaque — mais opaca)
      map.addSource("demo-route-progress", {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: [routeGeoJSON.geometry.coordinates[0]] },
        },
      });

      map.addLayer({
        id: "demo-route-progress-line",
        type: "line",
        source: "demo-route-progress",
        layout: { "line-join": "round", "line-cap": "round" },
        paint: {
          "line-color": "#E31A24",
          "line-width": 5,
          "line-opacity": 0.9,
        },
      });

      // Marcador destino (casa verde)
      const destinoEl = criarElementoDestino();
      new mapboxgl.Marker({ element: destinoEl, anchor: "bottom" })
        .setLngLat([centroLng, centroLat])
        .addTo(map);

      // Marcador motoboy (início da rota)
      const motoboyEl = criarElementoMotoboy();
      const motoboyMarker = new mapboxgl.Marker({ element: motoboyEl, anchor: "center" })
        .setLngLat([routePoints[0][1], routePoints[0][0]])
        .addTo(map);
      markerRef.current = motoboyMarker;

      // Iniciar animação
      startTimeRef.current = performance.now();

      function animate(now: number) {
        const elapsed = now - startTimeRef.current;
        const progress = Math.min(elapsed / duration, 1.0);

        // Interpolar posição
        const [lat, lng] = interpolateByDistance(routePoints, cumulDists, totalDist, progress);

        // Mover marcador
        if (markerRef.current) {
          markerRef.current.setLngLat([lng, lat]);

          // Calcular bearing para rotação do ícone
          const nextProgress = Math.min(progress + 0.02, 1.0);
          const [nextLat, nextLng] = interpolateByDistance(routePoints, cumulDists, totalDist, nextProgress);
          if (nextLat !== lat || nextLng !== lng) {
            const rot = bearing([lat, lng], [nextLat, nextLng]);
            const iconEl = markerRef.current.getElement().querySelector(".demo-moto-icon") as HTMLElement;
            if (iconEl) iconEl.style.transform = `rotate(${rot}deg)`;
          }
        }

        // Atualizar linha de progresso
        const progressSource = map.getSource("demo-route-progress") as mapboxgl.GeoJSONSource | undefined;
        if (progressSource) {
          // Pegar coordenadas da rota até a posição atual
          const coords: [number, number][] = [];
          for (let i = 0; i < routePoints.length; i++) {
            const ptDist = cumulDists[i] / totalDist;
            if (ptDist <= progress) {
              coords.push([routePoints[i][1], routePoints[i][0]]);
            } else {
              break;
            }
          }
          coords.push([lng, lat]);

          progressSource.setData({
            type: "Feature",
            properties: {},
            geometry: { type: "LineString", coordinates: coords },
          });
        }

        if (progress < 1.0) {
          animRef.current = requestAnimationFrame(animate);
        }
      }

      animRef.current = requestAnimationFrame(animate);
    });

    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
  }, [centroLat, centroLng, duration]);

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
        <span className="demo-moto-pulse" style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "#22c55e",
          display: "inline-block",
        }} />
        Ao vivo
      </div>
    </div>
  );
}
