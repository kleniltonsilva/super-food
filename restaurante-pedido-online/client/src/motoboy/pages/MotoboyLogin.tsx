import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { loginMotoboy } from "@/motoboy/lib/motoboyApiClient";
import { toast } from "sonner";
import { Loader2, Bike, Smartphone, X } from "lucide-react";

/** Detecta se está rodando como app nativo Capacitor */
function isNativeApp(): boolean {
  try {
    const w = window as unknown as Record<string, unknown>;
    return !!w.Capacitor && (w.Capacitor as { isNativePlatform?: () => boolean }).isNativePlatform?.() === true;
  } catch {
    return false;
  }
}

/** Banner para instalar o app nativo Android */
function InstallAppBanner() {
  const [visible, setVisible] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState("");

  useEffect(() => {
    // Não mostra no app nativo
    if (isNativeApp()) return;

    // Verifica dismiss por 7 dias
    const dismissedAt = localStorage.getItem("sf_app_banner_dismissed");
    if (dismissedAt) {
      const days = (Date.now() - parseInt(dismissedAt)) / (1000 * 60 * 60 * 24);
      if (days < 7) return;
    }

    // Buscar URL de download
    fetch("/api/public/app-version")
      .then((r) => r.json())
      .then((data) => {
        if (data.motoboy_app?.download_url) {
          setDownloadUrl(data.motoboy_app.download_url);
          setVisible(true);
        }
      })
      .catch(() => {});
  }, []);

  if (!visible) return null;

  function dismiss() {
    localStorage.setItem("sf_app_banner_dismissed", String(Date.now()));
    setVisible(false);
  }

  return (
    <div className="mx-auto mb-4 w-full max-w-sm animate-in fade-in slide-in-from-top-2">
      <div className="relative rounded-xl border border-green-500/30 bg-green-950/50 p-4">
        <button
          onClick={dismiss}
          className="absolute right-2 top-2 rounded-full p-1 text-green-400/60 transition-colors hover:text-green-300"
        >
          <X className="h-4 w-4" />
        </button>
        <div className="flex items-start gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-500/20">
            <Smartphone className="h-5 w-5 text-green-400" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-semibold text-green-300">
              App Derekh Entregador
            </p>
            <p className="mt-0.5 text-xs text-green-400/80">
              GPS em tempo real, mesmo com tela desligada. Receba notificações instantâneas.
            </p>
            {downloadUrl && (
              <a
                href={downloadUrl}
                className="mt-2 inline-flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-green-700"
              >
                <Smartphone className="h-3.5 w-3.5" />
                Baixar APK
              </a>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MotoboyLogin() {
  const [codigo, setCodigo] = useState("");
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, isLoggedIn } = useMotoboyAuth();
  const [, navigate] = useLocation();

  if (isLoggedIn) {
    navigate("/");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!codigo.trim() || !usuario.trim() || !senha.trim()) {
      toast.error("Preencha todos os campos");
      return;
    }
    setLoading(true);
    try {
      const data = await loginMotoboy(codigo.trim(), usuario.trim(), senha.trim());
      // O login retorna motoboy básico, mas precisamos do /me completo
      // Vamos usar os dados do /me que o context carrega automaticamente
      login(data.access_token, {
        ...data.motoboy,
        restaurante: data.restaurante,
        // Campos que virão do /me no refresh automático
        telefone: data.motoboy.telefone || "",
        status: "ativo",
        ordem_hierarquia: 0,
        capacidade_entregas: 3,
        total_km: 0,
      });
      toast.success("Login realizado com sucesso!");
      navigate("/");
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Erro ao fazer login";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-950 px-4">
      <InstallAppBanner />
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-green-500/20">
            <Bike className="h-7 w-7 text-green-500" />
          </div>
          <CardTitle className="text-xl text-white">
            App Entregador
          </CardTitle>
          <p className="text-sm text-gray-400">
            Faça login para iniciar suas entregas
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Código do Restaurante
              </label>
              <Input
                type="text"
                placeholder="Ex: ABC12345"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.toUpperCase())}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                autoComplete="off"
                maxLength={8}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Usuário
              </label>
              <Input
                type="text"
                placeholder="Seu nome de usuário"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                autoComplete="username"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Senha
              </label>
              <Input
                type="password"
                placeholder="Padrão: 123456"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                autoComplete="current-password"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-green-600 text-white hover:bg-green-700"
              disabled={loading}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Entrando...
                </>
              ) : (
                "Entrar"
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full text-gray-400"
              onClick={() => navigate("/cadastro")}
            >
              Solicitar Cadastro
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
