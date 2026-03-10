import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft } from "lucide-react";
import { useLocation } from "wouter";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useAuth } from "@/contexts/AuthContext";
import { loginCliente, registrarCliente } from "@/lib/apiClient";
import { toast } from "sonner";
import { useState, useEffect } from "react";

type AuthTab = "login" | "registro";

export default function Login() {
  const [, navigate] = useLocation();
  const { siteInfo } = useRestaurante();
  const { isLoggedIn, login } = useAuth();
  const [tab, setTab] = useState<AuthTab>("login");
  const [processing, setProcessing] = useState(false);

  // Login form
  const [loginEmail, setLoginEmail] = useState("");
  const [loginSenha, setLoginSenha] = useState("");

  // Registro form
  const [regNome, setRegNome] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regTelefone, setRegTelefone] = useState("");
  const [regSenha, setRegSenha] = useState("");
  const [regSenhaConfirm, setRegSenhaConfirm] = useState("");

  // Redireciona se já logado
  useEffect(() => {
    if (isLoggedIn) {
      navigate("/");
    }
  }, [isLoggedIn, navigate]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!loginEmail || !loginSenha) {
      toast.error("Preencha email e senha");
      return;
    }

    setProcessing(true);
    try {
      // trim() na senha para ignorar espaços acidentais (defesa em profundidade — backend também faz strip)
      const data = await loginCliente(loginEmail, loginSenha.trim());
      login(data.access_token, data.cliente);
      toast.success(`Bem-vindo, ${data.cliente.nome}!`);
      navigate("/");
    } catch {
      toast.error("Email ou senha incorretos");
    } finally {
      setProcessing(false);
    }
  };

  const handleRegistro = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regNome || !regEmail || !regTelefone || !regSenha) {
      toast.error("Preencha todos os campos obrigatórios");
      return;
    }
    // Validar nome
    if (regNome.trim().length < 2) {
      toast.error("Nome deve ter no mínimo 2 caracteres");
      return;
    }
    // Validar email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(regEmail.trim())) {
      toast.error("Email inválido");
      return;
    }
    // Validar telefone (mín 10 dígitos)
    const telDigitos = regTelefone.replace(/\D/g, "");
    if (telDigitos.length < 10) {
      toast.error("Telefone inválido — mínimo 10 dígitos");
      return;
    }
    if (regSenha !== regSenhaConfirm) {
      toast.error("As senhas não coincidem");
      return;
    }
    if (regSenha.length < 6) {
      toast.error("A senha deve ter no mínimo 6 caracteres");
      return;
    }

    setProcessing(true);
    try {
      // trim() na senha para ignorar espaços acidentais (defesa em profundidade)
      const data = await registrarCliente({
        nome: regNome.trim(),
        email: regEmail.trim(),
        telefone: telDigitos,
        senha: regSenha.trim(),
      });
      login(data.access_token, data.cliente);
      toast.success(`Conta criada com sucesso! Bem-vindo, ${data.cliente.nome}!`);
      navigate("/");
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      let msg = "Erro ao criar conta";
      if (status === 409 || (typeof detail === "string" && detail.toLowerCase().includes("já"))) {
        msg = "Este email já está cadastrado. Tente fazer login.";
      } else if (status === 422) {
        msg = "Dados inválidos — verifique os campos e tente novamente";
      } else if (status === 404) {
        msg = "Restaurante não encontrado";
      } else if (typeof detail === "string") {
        msg = detail;
      }
      toast.error(msg);
    } finally {
      setProcessing(false);
    }
  };

  const nomeRestaurante = siteInfo?.nome_fantasia || "Restaurante";

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8 max-w-md mx-auto">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar ao Cardápio
        </Button>

        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold">{nomeRestaurante}</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Entre ou crie sua conta para fazer pedidos
          </p>
        </div>

        {/* Tabs */}
        <div className="flex mb-6 border rounded-lg overflow-hidden">
          <button
            onClick={() => setTab("login")}
            className={`flex-1 py-3 font-semibold text-sm transition-all ${
              tab === "login"
                ? "text-white"
                : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
            }`}
            style={tab === "login" ? { background: `var(--cor-primaria, #E31A24)` } : {}}
          >
            Entrar
          </button>
          <button
            onClick={() => setTab("registro")}
            className={`flex-1 py-3 font-semibold text-sm transition-all ${
              tab === "registro"
                ? "text-white"
                : "bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]"
            }`}
            style={tab === "registro" ? { background: `var(--cor-primaria, #E31A24)` } : {}}
          >
            Criar Conta
          </button>
        </div>

        {/* Login Form */}
        {tab === "login" && (
          <Card className="p-6">
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="text-sm font-bold mb-1 block">Email</label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={e => setLoginEmail(e.target.value)}
                  placeholder="seu@email.com"
                  className="dark-input"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Senha</label>
                <input
                  type="password"
                  value={loginSenha}
                  onChange={e => setLoginSenha(e.target.value)}
                  placeholder="Sua senha"
                  className="dark-input"
                  required
                />
              </div>
              <Button
                type="submit"
                disabled={processing}
                className="w-full py-5 text-lg font-bold text-white"
                style={{ background: `var(--cor-primaria, #E31A24)` }}
              >
                {processing ? "Entrando..." : "Entrar"}
              </Button>
            </form>
          </Card>
        )}

        {/* Registro Form */}
        {tab === "registro" && (
          <Card className="p-6">
            <form onSubmit={handleRegistro} className="space-y-4">
              <div>
                <label className="text-sm font-bold mb-1 block">Nome completo *</label>
                <input
                  type="text"
                  value={regNome}
                  onChange={e => setRegNome(e.target.value)}
                  placeholder="Seu nome"
                  className="dark-input"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Email *</label>
                <input
                  type="email"
                  value={regEmail}
                  onChange={e => setRegEmail(e.target.value)}
                  placeholder="seu@email.com"
                  className="dark-input"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Telefone *</label>
                <input
                  type="tel"
                  value={regTelefone}
                  onChange={e => setRegTelefone(e.target.value)}
                  placeholder="(11) 99999-9999"
                  className="dark-input"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Senha *</label>
                <input
                  type="password"
                  value={regSenha}
                  onChange={e => setRegSenha(e.target.value)}
                  placeholder="Mínimo 6 caracteres"
                  className="dark-input"
                  required
                  minLength={6}
                />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Confirmar senha *</label>
                <input
                  type="password"
                  value={regSenhaConfirm}
                  onChange={e => setRegSenhaConfirm(e.target.value)}
                  placeholder="Repita a senha"
                  className="dark-input"
                  required
                />
              </div>
              <Button
                type="submit"
                disabled={processing}
                className="w-full py-5 text-lg font-bold text-white"
                style={{ background: `var(--cor-primaria, #E31A24)` }}
              >
                {processing ? "Criando conta..." : "Criar Conta"}
              </Button>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}
