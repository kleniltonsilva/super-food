/**
 * Auto-Update Checker — Verifica versão e força atualização
 *
 * Fluxo:
 * 1. App abre → busca /api/public/app-version
 * 2. Compara versão local (App.getInfo) com versão remota
 * 3. Se desatualizado: mostra modal bloqueante para atualizar
 * 4. Se min_version > local: bloqueia completamente o app
 */
import { Capacitor } from "@capacitor/core";
import { App } from "@capacitor/app";

export interface AppVersionInfo {
  version: string;
  minVersion: string;
  downloadUrl: string;
  forceUpdate: boolean;
}

export interface UpdateStatus {
  checking: boolean;
  updateAvailable: boolean;
  updateRequired: boolean;
  currentVersion: string;
  latestVersion: string;
  downloadUrl: string;
}

const API_BASE = (() => {
  // No Capacitor nativo, sempre usar produção (não há servidor local)
  try {
    if (Capacitor.isNativePlatform()) {
      return "https://superfood-api.fly.dev";
    }
  } catch { /* não é nativo */ }

  if (typeof window !== "undefined" && window.location) {
    const { protocol, host } = window.location;
    if (host.includes("superfood-api.fly.dev")) {
      return "https://superfood-api.fly.dev";
    }
    return `${protocol}//${host}`;
  }
  return "https://superfood-api.fly.dev";
})();

/** Compara versões semver (ex: "1.0.2" > "1.0.0") */
function compareVersions(a: string, b: string): number {
  const pa = a.split(".").map(Number);
  const pb = b.split(".").map(Number);
  for (let i = 0; i < 3; i++) {
    const va = pa[i] || 0;
    const vb = pb[i] || 0;
    if (va > vb) return 1;
    if (va < vb) return -1;
  }
  return 0;
}

/** Busca versão mais recente do servidor */
async function fetchRemoteVersion(): Promise<AppVersionInfo | null> {
  try {
    const res = await fetch(`${API_BASE}/api/public/app-version`, {
      headers: { Accept: "application/json" },
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) return null;
    const data = await res.json();
    const app = data.motoboy_app;
    if (!app) return null;
    return {
      version: app.version,
      minVersion: app.min_version,
      downloadUrl: app.download_url.startsWith("http")
        ? app.download_url
        : `${API_BASE}${app.download_url}`,
      forceUpdate: app.force_update ?? true,
    };
  } catch {
    return null;
  }
}

/** Obtém versão local do app */
async function getLocalVersion(): Promise<string> {
  if (!Capacitor.isNativePlatform()) return "0.0.0";
  try {
    const info = await App.getInfo();
    return info.version;
  } catch {
    return "0.0.0";
  }
}

/** Verifica se há atualização disponível */
export async function checkForUpdates(): Promise<UpdateStatus> {
  const status: UpdateStatus = {
    checking: true,
    updateAvailable: false,
    updateRequired: false,
    currentVersion: "0.0.0",
    latestVersion: "0.0.0",
    downloadUrl: "",
  };

  if (!Capacitor.isNativePlatform()) {
    return { ...status, checking: false };
  }

  try {
    const [localVersion, remoteInfo] = await Promise.all([
      getLocalVersion(),
      fetchRemoteVersion(),
    ]);

    status.currentVersion = localVersion;
    status.checking = false;

    if (!remoteInfo) return status;

    status.latestVersion = remoteInfo.version;
    status.downloadUrl = remoteInfo.downloadUrl;

    // Verifica se versão local está abaixo do mínimo (bloqueio total)
    if (compareVersions(localVersion, remoteInfo.minVersion) < 0) {
      status.updateRequired = true;
      status.updateAvailable = true;
      return status;
    }

    // Verifica se há versão mais nova disponível
    if (compareVersions(localVersion, remoteInfo.version) < 0) {
      status.updateAvailable = true;
      return status;
    }

    return status;
  } catch {
    return { ...status, checking: false };
  }
}

/** Abre URL de download no browser nativo */
export async function openDownloadUrl(url: string): Promise<void> {
  // window.open funciona tanto no browser quanto no Capacitor WebView
  window.open(url, "_blank");
}
