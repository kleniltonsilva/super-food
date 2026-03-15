/**
 * Integração Sentry para o frontend Derekh Food.
 * Inicializa graciosamente — sem VITE_SENTRY_DSN, tudo funciona normalmente.
 */
import * as Sentry from "@sentry/react";

/**
 * Detecta qual app está rodando pela URL.
 */
function detectAppType(): string {
  const path = window.location.pathname;
  if (path.startsWith("/superadmin")) return "superadmin";
  if (path.startsWith("/admin")) return "admin";
  if (path.startsWith("/entregador")) return "motoboy";
  return "site";
}

/**
 * Inicializa Sentry. Deve ser chamado no main.tsx antes de qualquer render.
 */
export function initSentry(): void {
  const dsn = import.meta.env.VITE_SENTRY_DSN;
  if (!dsn) return;

  try {
    Sentry.init({
      dsn,
      environment: import.meta.env.MODE || "development",
      integrations: [
        Sentry.browserTracingIntegration(),
      ],
      tracesSampleRate: 0, // Sem performance (free tier)
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 0,
      beforeSend(event) {
        // Ignora erros de rede genéricos (conexão do usuário)
        const message = event.exception?.values?.[0]?.value || "";
        if (message.includes("Network Error") || message.includes("Failed to fetch")) {
          return null;
        }
        return event;
      },
    });

    Sentry.setTag("app_type", detectAppType());
  } catch {
    // Sentry init falhou — app continua normalmente
  }
}

/**
 * Seta tags do restaurante atual no Sentry (chamado pelo RestauranteContext).
 */
export function setSentryRestaurante(codigo: string, nome: string, id?: number): void {
  if (!import.meta.env.VITE_SENTRY_DSN) return;
  try {
    Sentry.setTag("restaurante_codigo", codigo);
    Sentry.setTag("restaurante_nome", nome);
    if (id) Sentry.setTag("restaurante_id", String(id));
  } catch {
    // silencioso
  }
}

/**
 * Captura erro no Sentry (para uso em ErrorBoundary e catch blocks).
 */
export function captureError(error: unknown, context?: Record<string, string>): void {
  if (!import.meta.env.VITE_SENTRY_DSN) return;
  try {
    if (context) {
      Sentry.setContext("extra", context);
    }
    Sentry.captureException(error);
  } catch {
    // silencioso
  }
}

/**
 * Adiciona breadcrumb de erro de API (chamado pelos interceptors dos API clients).
 */
export function sentryBreadcrumbFromAxiosError(
  appType: string,
  method: string,
  url: string,
  status: number
): void {
  if (!import.meta.env.VITE_SENTRY_DSN) return;
  if (status < 500) return; // Só breadcrumbs para 5xx
  try {
    Sentry.addBreadcrumb({
      category: `api.${appType}`,
      message: `${method.toUpperCase()} ${url} → ${status}`,
      level: "error",
      data: { method, url, status },
    });
  } catch {
    // silencioso
  }
}
