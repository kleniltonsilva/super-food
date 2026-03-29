// Service Worker — Derekh Food Site Cliente PWA
const CACHE_NAME = "sf-cliente-v1";

// Install — skip waiting
self.addEventListener("install", () => {
  self.skipWaiting();
});

// Activate — cleanup old caches, claim clients
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch strategy
self.addEventListener("fetch", (event) => {
  const { request } = event;

  // Skip non-GET
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  const path = url.pathname;

  // Skip API, auth, WebSocket, site data endpoints
  if (
    path.startsWith("/api/") ||
    path.startsWith("/auth/") ||
    path.startsWith("/ws/") ||
    path.startsWith("/site/") ||
    path.startsWith("/painel/") ||
    path.startsWith("/webhooks/")
  ) {
    return;
  }

  // Static assets (js, css, images, fonts) — cache-first
  if (path.startsWith("/assets/") || path.startsWith("/icons/") || path.startsWith("/themes/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // Static uploads (logos, images) — cache-first
  if (path.startsWith("/static/")) {
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        });
      })
    );
    return;
  }

  // HTML pages — network-first with cache fallback
  if (request.headers.get("accept")?.includes("text/html") || path.startsWith("/cliente/")) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Everything else — network-first
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
