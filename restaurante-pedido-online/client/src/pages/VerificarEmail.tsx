import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useVerificarEmail, useReenviarVerificacao } from "@/hooks/useQueries";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { ArrowLeft, Mail, RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";

const CODE_LENGTH = 6;
const EXPIRY_SECONDS = 10 * 60; // 10 minutos
const RESEND_COOLDOWN = 60; // 60 segundos

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export default function VerificarEmail() {
  const [, navigate] = useLocation();
  const { isLoggedIn, cliente, refreshCliente, loading: authLoading } = useAuth();

  // OTP digits
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Timers
  const [expirySeconds, setExpirySeconds] = useState(EXPIRY_SECONDS);
  const [resendCooldown, setResendCooldown] = useState(RESEND_COOLDOWN);

  // UI state
  const [error, setError] = useState("");
  const [expired, setExpired] = useState(false);

  // Mutations
  const verificarMutation = useVerificarEmail();
  const reenviarMutation = useReenviarVerificacao();

  // Redireciona se nao logado (aguarda auth carregar)
  useEffect(() => {
    if (!authLoading && !isLoggedIn) {
      navigate("/login");
    }
  }, [authLoading, isLoggedIn, navigate]);

  // Auto-focus primeiro input
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  // Timer de expiracao do codigo (10 min)
  useEffect(() => {
    if (expirySeconds <= 0) {
      setExpired(true);
      return;
    }
    const timer = setInterval(() => {
      setExpirySeconds((prev) => {
        if (prev <= 1) {
          setExpired(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [expirySeconds]);

  // Timer de cooldown do reenvio (60s)
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Handlers para os inputs OTP
  const handleDigitChange = useCallback(
    (index: number, value: string) => {
      // Aceitar somente numeros
      const digit = value.replace(/\D/g, "").slice(-1);
      const newDigits = [...digits];
      newDigits[index] = digit;
      setDigits(newDigits);
      setError("");

      // Auto-advance para proximo input
      if (digit && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    },
    [digits]
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace" && !digits[index] && index > 0) {
        // Voltar para input anterior ao apagar vazio
        inputRefs.current[index - 1]?.focus();
      }
      if (e.key === "ArrowLeft" && index > 0) {
        inputRefs.current[index - 1]?.focus();
      }
      if (e.key === "ArrowRight" && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    },
    [digits]
  );

  const handlePaste = useCallback((e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData("text").replace(/\D/g, "").slice(0, CODE_LENGTH);
    if (!pasted) return;

    const newDigits = Array(CODE_LENGTH).fill("");
    for (let i = 0; i < pasted.length; i++) {
      newDigits[i] = pasted[i];
    }
    setDigits(newDigits);
    setError("");

    // Focar no proximo input vazio ou no ultimo
    const nextEmpty = newDigits.findIndex((d) => !d);
    const focusIndex = nextEmpty === -1 ? CODE_LENGTH - 1 : nextEmpty;
    inputRefs.current[focusIndex]?.focus();
  }, []);

  // Verificar codigo
  const handleVerificar = useCallback(async () => {
    const codigo = digits.join("");
    if (codigo.length !== CODE_LENGTH) {
      setError("Digite o codigo completo de 6 digitos");
      return;
    }

    setError("");
    verificarMutation.mutate(codigo, {
      onSuccess: async () => {
        toast.success("Email verificado!");
        await refreshCliente();
        navigate("/");
      },
      onError: (err: any) => {
        const detail = err?.response?.data?.detail;
        if (typeof detail === "string") {
          setError(detail);
        } else {
          setError("Codigo invalido. Verifique e tente novamente.");
        }
      },
    });
  }, [digits, verificarMutation, refreshCliente, navigate]);

  // Reenviar codigo
  const handleReenviar = useCallback(() => {
    if (resendCooldown > 0 || reenviarMutation.isPending) return;

    reenviarMutation.mutate(undefined, {
      onSuccess: () => {
        toast.success("Novo codigo enviado para seu email!");
        setResendCooldown(RESEND_COOLDOWN);
        setExpirySeconds(EXPIRY_SECONDS);
        setExpired(false);
        setDigits(Array(CODE_LENGTH).fill(""));
        setError("");
        inputRefs.current[0]?.focus();
      },
      onError: (err: any) => {
        const detail = err?.response?.data?.detail;
        toast.error(typeof detail === "string" ? detail : "Erro ao reenviar codigo");
      },
    });
  }, [resendCooldown, reenviarMutation]);

  const codigoCompleto = digits.every((d) => d !== "");
  const emailMascarado = cliente?.email
    ? cliente.email.replace(/^(.{2})(.*)(@.*)$/, (_m, start, mid, end) => start + "*".repeat(mid.length) + end)
    : "";

  // Nao renderiza ate auth carregar
  if (authLoading) return null;

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 max-w-md mx-auto">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <div className="text-center mb-6">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
            style={{ background: `color-mix(in srgb, var(--cor-primaria, #E31A24) 15%, transparent)` }}
          >
            <Mail
              className="w-8 h-8"
              style={{ color: `var(--cor-primaria, #E31A24)` }}
            />
          </div>
          <h1 className="text-2xl font-bold">Verificar email</h1>
          <p className="text-muted-foreground text-sm mt-2">
            Enviamos um codigo de 6 digitos para{" "}
            <span className="font-semibold text-foreground">{emailMascarado}</span>
          </p>
        </div>

        <Card className="p-6">
          {/* Timer */}
          <div className="text-center mb-6">
            {expired ? (
              <div className="flex items-center justify-center gap-2 text-destructive">
                <AlertCircle className="w-4 h-4" />
                <span className="text-sm font-semibold">Codigo expirado</span>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Codigo expira em{" "}
                <span className="font-mono font-bold text-foreground">
                  {formatTime(expirySeconds)}
                </span>
              </p>
            )}
          </div>

          {/* OTP Inputs */}
          <div className="flex justify-center gap-2 sm:gap-3 mb-6">
            {digits.map((digit, i) => (
              <input
                key={i}
                ref={(el) => {
                  inputRefs.current[i] = el;
                }}
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={1}
                value={digit}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                onPaste={i === 0 ? handlePaste : undefined}
                disabled={expired || verificarMutation.isPending}
                className="dark-input w-11 h-14 sm:w-13 sm:h-16 text-center text-2xl font-bold rounded-lg
                  focus:outline-none focus:ring-2 transition-all"
                style={{
                  borderColor: error ? "hsl(var(--destructive))" : undefined,
                }}
                aria-label={`Digito ${i + 1}`}
              />
            ))}
          </div>

          {/* Erro inline */}
          {error && (
            <div className="flex items-center gap-2 text-destructive text-sm mb-4 justify-center">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Botao verificar */}
          <Button
            onClick={handleVerificar}
            disabled={!codigoCompleto || expired || verificarMutation.isPending}
            className="w-full py-5 text-lg font-bold text-white"
            style={{ background: `var(--cor-primaria, #E31A24)` }}
          >
            {verificarMutation.isPending ? (
              <span className="flex items-center gap-2">
                <RefreshCw className="w-5 h-5 animate-spin" />
                Verificando...
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5" />
                Verificar
              </span>
            )}
          </Button>

          {/* Reenviar */}
          <div className="text-center mt-5">
            <p className="text-sm text-muted-foreground mb-1">Nao recebeu o codigo?</p>
            <button
              onClick={handleReenviar}
              disabled={resendCooldown > 0 && !expired}
              className="text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ color: `var(--cor-primaria, #E31A24)` }}
            >
              {reenviarMutation.isPending
                ? "Reenviando..."
                : resendCooldown > 0 && !expired
                  ? `Reenviar codigo (${resendCooldown}s)`
                  : "Reenviar codigo"}
            </button>
          </div>
        </Card>

        {/* Pular verificacao */}
        <div className="text-center mt-6">
          <button
            onClick={() => navigate("/")}
            className="text-sm text-muted-foreground hover:text-foreground transition-colors underline underline-offset-4"
          >
            Pular por agora
          </button>
        </div>
      </div>
    </div>
  );
}
