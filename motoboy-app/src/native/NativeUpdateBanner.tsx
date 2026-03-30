/**
 * Modal bloqueante de atualização — aparece quando há versão nova do APK
 *
 * - updateRequired: bloqueia totalmente o app (versão abaixo do mínimo)
 * - updateAvailable: mostra botão para atualizar (pode fechar se não obrigatório)
 */
import { useState } from "react";
import { Download, AlertTriangle, RefreshCw } from "lucide-react";
import type { UpdateStatus } from "./update-checker";

interface NativeUpdateBannerProps {
  status: UpdateStatus;
  onDownload: () => void;
  onDismiss?: () => void;
}

export default function NativeUpdateBanner({
  status,
  onDownload,
  onDismiss,
}: NativeUpdateBannerProps) {
  const [downloading, setDownloading] = useState(false);

  if (!status.updateAvailable && !status.updateRequired) return null;

  const isRequired = status.updateRequired;

  function handleDownload() {
    setDownloading(true);
    onDownload();
  }

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-sm rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        {/* Ícone */}
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20">
          {isRequired ? (
            <AlertTriangle className="h-8 w-8 text-amber-400" />
          ) : (
            <Download className="h-8 w-8 text-green-400" />
          )}
        </div>

        {/* Título */}
        <h2 className="mb-2 text-center text-xl font-bold text-white">
          {isRequired ? "Atualização Obrigatória" : "Nova Versão Disponível!"}
        </h2>

        {/* Descrição */}
        <p className="mb-1 text-center text-sm text-gray-400">
          {isRequired
            ? "Esta versão não é mais compatível. Atualize para continuar usando o app."
            : "Uma versão mais recente do Derekh Entregador está disponível com melhorias."}
        </p>

        {/* Versões */}
        <div className="mb-6 flex items-center justify-center gap-3 text-xs text-gray-500">
          <span>Atual: v{status.currentVersion}</span>
          <span>→</span>
          <span className="font-medium text-green-400">
            v{status.latestVersion}
          </span>
        </div>

        {/* Botão principal */}
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-green-600 py-3 text-sm font-semibold text-white transition-colors hover:bg-green-700 disabled:opacity-60"
        >
          {downloading ? (
            <>
              <RefreshCw className="h-4 w-4 animate-spin" />
              Abrindo download...
            </>
          ) : (
            <>
              <Download className="h-4 w-4" />
              Atualizar Agora
            </>
          )}
        </button>

        {/* Botão secundário (só se não obrigatório) */}
        {!isRequired && onDismiss && (
          <button
            onClick={onDismiss}
            className="mt-3 w-full py-2 text-center text-xs text-gray-500 transition-colors hover:text-gray-300"
          >
            Lembrar depois
          </button>
        )}
      </div>
    </div>
  );
}
