import { useState, useEffect, useRef, useCallback } from "react";
import { useLocation } from "wouter";
import { useEsqueciSenha, useRedefinirSenha } from "@/hooks/useQueries";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { ArrowLeft, KeyRound, Mail, RefreshCw, CheckCircle2, AlertCircle, Eye, EyeOff } from "lucide-react";

const CODE_LENGTH = 6;
const EXPIRY_SECONDS = 10 * 60;
const RESEND_COOLDOWN = 60;

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

type Etapa = "email" | "codigo";

export default function EsqueciSenha() {
  const [, navigate] = useLocation();

  // Estado geral
  const [etapa, setEtapa] = useState<Etapa>("email");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  // OTP
  const [digits, setDigits] = useState<string[]>(Array(CODE_LENGTH).fill(""));
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Nova senha
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);

  // Timers
  const [expirySeconds, setExpirySeconds] = useState(EXPIRY_SECONDS);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [expired, setExpired] = useState(false);

  // Mutations
  const esqueciMutation = useEsqueciSenha();
  const redefinirMutation = useRedefinirSenha();

  // Timer de expiração
  useEffect(() => {
    if (etapa !== "codigo" || expirySeconds <= 0) return;
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
  }, [etapa, expirySeconds]);

  // Timer de cooldown reenvio
  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Auto-focus OTP
  useEffect(() => {
    if (etapa === "codigo") {
      inputRefs.current[0]?.focus();
    }
  }, [etapa]);

  // Enviar email
  const handleEnviarEmail = useCallback(() => {
    if (!email.trim()) {
      setError("Digite seu email");
      return;
    }
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email.trim())) {
      setError("Email inválido");
      return;
    }

    setError("");
    esqueciMutation.mutate(email.trim(), {
      onSuccess: () => {
        toast.success("Se o email estiver cadastrado, você receberá um código");
        setEtapa("codigo");
        setExpirySeconds(EXPIRY_SECONDS);
        setExpired(false);
        setResendCooldown(RESEND_COOLDOWN);
      },
      onError: () => {
        // Sempre mostrar sucesso por segurança
        toast.success("Se o email estiver cadastrado, você receberá um código");
        setEtapa("codigo");
        setExpirySeconds(EXPIRY_SECONDS);
        setExpired(false);
        setResendCooldown(RESEND_COOLDOWN);
      },
    });
  }, [email, esqueciMutation]);

  // OTP handlers
  const handleDigitChange = useCallback(
    (index: number, value: string) => {
      const digit = value.replace(/\D/g, "").slice(-1);
      const newDigits = [...digits];
      newDigits[index] = digit;
      setDigits(newDigits);
      setError("");
      if (digit && index < CODE_LENGTH - 1) {
        inputRefs.current[index + 1]?.focus();
      }
    },
    [digits]
  );

  const handleKeyDown = useCallback(
    (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === "Backspace" && !digits[index] && index > 0) {
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
    const nextEmpty = newDigits.findIndex((d) => !d);
    inputRefs.current[nextEmpty === -1 ? CODE_LENGTH - 1 : nextEmpty]?.focus();
  }, []);

  // Redefinir senha
  const handleRedefinir = useCallback(() => {
    const codigo = digits.join("");
    if (codigo.length !== CODE_LENGTH) {
      setError("Digite o código completo de 6 dígitos");
      return;
    }
    if (!novaSenha || novaSenha.length < 6) {
      setError("A senha deve ter no mínimo 6 caracteres");
      return;
    }
    if (novaSenha !== confirmarSenha) {
      setError("As senhas não coincidem");
      return;
    }

    setError("");
    redefinirMutation.mutate(
      { email: email.trim(), codigo, nova_senha: novaSenha.trim() },
      {
        onSuccess: () => {
          toast.success("Senha redefinida com sucesso!");
          navigate("/login");
        },
        onError: (err: any) => {
          const detail = err?.response?.data?.detail;
          setError(typeof detail === "string" ? detail : "Código inválido ou expirado");
        },
      }
    );
  }, [digits, novaSenha, confirmarSenha, email, redefinirMutation, navigate]);

  // Reenviar
  const handleReenviar = useCallback(() => {
    if (resendCooldown > 0 || esqueciMutation.isPending) return;
    esqueciMutation.mutate(email.trim(), {
      onSuccess: () => {
        toast.success("Novo código enviado!");
        setResendCooldown(RESEND_COOLDOWN);
        setExpirySeconds(EXPIRY_SECONDS);
        setExpired(false);
        setDigits(Array(CODE_LENGTH).fill(""));
        setError("");
        inputRefs.current[0]?.focus();
      },
      onError: () => {
        toast.success("Novo código enviado!");
        setResendCooldown(RESEND_COOLDOWN);
      },
    });
  }, [resendCooldown, email, esqueciMutation]);

  const codigoCompleto = digits.every((d) => d !== "");

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 max-w-md mx-auto">
        <Button
          variant="ghost"
          onClick={() => (etapa === "codigo" ? setEtapa("email") : navigate("/login"))}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {etapa === "codigo" ? "Voltar" : "Voltar ao Login"}
        </Button>

        <div className="text-center mb-6">
          <div
            className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
            style={{ background: `color-mix(in srgb, var(--cor-primaria, #E31A24) 15%, transparent)` }}
          >
            <KeyRound className="w-8 h-8" style={{ color: `var(--cor-primaria, #E31A24)` }} />
          </div>
          <h1 className="text-2xl font-bold">
            {etapa === "email" ? "Esqueci minha senha" : "Redefinir senha"}
          </h1>
          <p className="text-muted-foreground text-sm mt-2">
            {etapa === "email"
              ? "Digite seu email para receber um código de recuperação"
              : "Digite o código enviado para seu email e escolha uma nova senha"}
          </p>
        </div>

        {/* ETAPA 1: Email */}
        {etapa === "email" && (
          <Card className="p-6">
            <div className="space-y-4">
              <div>
                <label className="text-sm font-bold mb-1 block">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setError("");
                  }}
                  placeholder="seu@email.com"
                  className="dark-input"
                  onKeyDown={(e) => e.key === "Enter" && handleEnviarEmail()}
                />
              </div>

              {error && (
                <div className="flex items-center gap-2 text-destructive text-sm">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Button
                onClick={handleEnviarEmail}
                disabled={esqueciMutation.isPending || !email.trim()}
                className="w-full py-5 text-lg font-bold text-white"
                style={{ background: `var(--cor-primaria, #E31A24)` }}
              >
                {esqueciMutation.isPending ? (
                  <span className="flex items-center gap-2">
                    <RefreshCw className="w-5 h-5 animate-spin" />
                    Enviando...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Mail className="w-5 h-5" />
                    Enviar código
                  </span>
                )}
              </Button>
            </div>
          </Card>
        )}

        {/* ETAPA 2: Código + Nova Senha */}
        {etapa === "codigo" && (
          <Card className="p-6">
            {/* Timer */}
            <div className="text-center mb-5">
              {expired ? (
                <div className="flex items-center justify-center gap-2 text-destructive">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-semibold">Código expirado</span>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Código expira em{" "}
                  <span className="font-mono font-bold text-foreground">
                    {formatTime(expirySeconds)}
                  </span>
                </p>
              )}
            </div>

            {/* OTP Inputs */}
            <div className="flex justify-center gap-2 sm:gap-3 mb-5">
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
                  disabled={expired || redefinirMutation.isPending}
                  className="dark-input w-11 h-14 sm:w-13 sm:h-16 text-center text-2xl font-bold rounded-lg
                    focus:outline-none focus:ring-2 transition-all"
                  aria-label={`Dígito ${i + 1}`}
                />
              ))}
            </div>

            {/* Nova senha */}
            <div className="space-y-3 mb-5">
              <div>
                <label className="text-sm font-bold mb-1 block">Nova senha</label>
                <div className="relative">
                  <input
                    type={showSenha ? "text" : "password"}
                    value={novaSenha}
                    onChange={(e) => {
                      setNovaSenha(e.target.value);
                      setError("");
                    }}
                    placeholder="Mínimo 6 caracteres"
                    className="dark-input pr-10"
                    disabled={expired}
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowSenha(!showSenha)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showSenha ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Confirmar senha</label>
                <input
                  type={showSenha ? "text" : "password"}
                  value={confirmarSenha}
                  onChange={(e) => {
                    setConfirmarSenha(e.target.value);
                    setError("");
                  }}
                  placeholder="Repita a nova senha"
                  className="dark-input"
                  disabled={expired}
                />
              </div>
            </div>

            {/* Erro */}
            {error && (
              <div className="flex items-center gap-2 text-destructive text-sm mb-4">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Botão redefinir */}
            <Button
              onClick={handleRedefinir}
              disabled={!codigoCompleto || expired || !novaSenha || redefinirMutation.isPending}
              className="w-full py-5 text-lg font-bold text-white"
              style={{ background: `var(--cor-primaria, #E31A24)` }}
            >
              {redefinirMutation.isPending ? (
                <span className="flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Redefinindo...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <CheckCircle2 className="w-5 h-5" />
                  Redefinir senha
                </span>
              )}
            </Button>

            {/* Reenviar */}
            <div className="text-center mt-5">
              <button
                onClick={handleReenviar}
                disabled={resendCooldown > 0 && !expired}
                className="text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ color: `var(--cor-primaria, #E31A24)` }}
              >
                {esqueciMutation.isPending
                  ? "Reenviando..."
                  : resendCooldown > 0 && !expired
                    ? `Reenviar código (${resendCooldown}s)`
                    : "Reenviar código"}
              </button>
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
