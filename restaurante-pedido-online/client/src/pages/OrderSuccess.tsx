import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { CheckCircle, Package, User } from "lucide-react";
import { useLocation, useParams } from "wouter";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useAuth } from "@/contexts/AuthContext";
import { registrarPosPedido } from "@/lib/apiClient";
import { toast } from "sonner";
import { useState } from "react";

export default function OrderSuccess() {
  const [, navigate] = useLocation();
  const params = useParams<{ id: string }>();
  const pedidoId = parseInt(params.id || "0");
  const { siteInfo } = useRestaurante();
  const { isLoggedIn, login } = useAuth();

  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [telefone, setTelefone] = useState("");
  const [senha, setSenha] = useState("");
  const [registrando, setRegistrando] = useState(false);
  const [registrado, setRegistrado] = useState(false);

  const corPrimaria = "var(--cor-primaria, #E31A24)";

  const handleRegistro = async () => {
    if (!nome.trim()) { toast.error("Digite seu nome"); return; }
    if (!email.trim()) { toast.error("Digite seu email"); return; }
    if (!telefone.trim()) { toast.error("Digite seu telefone"); return; }
    if (senha.length < 6) { toast.error("Senha deve ter no mínimo 6 caracteres"); return; }

    setRegistrando(true);
    try {
      // trim() na senha para ignorar espaços acidentais (defesa em profundidade)
      const result = await registrarPosPedido({
        nome: nome.trim(),
        email: email.trim(),
        telefone: telefone.trim(),
        senha: senha.trim(),
        pedido_id: pedidoId || undefined,
      });

      // Auto-login com o token recebido
      login(result.access_token, result.cliente);

      setRegistrado(true);
      toast.success("Conta criada com sucesso!");

      // Redireciona para tracking após 2s
      setTimeout(() => {
        navigate(`/order/${pedidoId}`);
      }, 2000);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || "Erro ao criar conta";
      toast.error(msg);
    } finally {
      setRegistrando(false);
    }
  };

  // Se já logado ou acabou de registrar, mostra tela simples
  if (isLoggedIn || registrado) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-md w-full p-8 text-center space-y-4">
          <CheckCircle className="w-16 h-16 mx-auto" style={{ color: "#22c55e" }} />
          <h1 className="text-2xl font-bold">Pedido Realizado!</h1>
          <p className="text-muted-foreground">
            Seu pedido #{pedidoId} foi recebido e está sendo preparado.
          </p>
          {registrado && (
            <p className="text-sm font-semibold" style={{ color: corPrimaria }}>
              Conta criada! Redirecionando para acompanhamento...
            </p>
          )}
          <div className="pt-4 space-y-2">
            <Button
              onClick={() => navigate(`/order/${pedidoId}`)}
              className="w-full text-white font-bold"
              style={{ background: corPrimaria }}
            >
              <Package className="w-4 h-4 mr-2" />
              Acompanhar Pedido
            </Button>
            <Button variant="outline" className="w-full" onClick={() => navigate("/")}>
              Voltar ao Cardápio
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="max-w-md w-full p-6 md:p-8 space-y-6">
        {/* Sucesso */}
        <div className="text-center space-y-2">
          <CheckCircle className="w-16 h-16 mx-auto" style={{ color: "#22c55e" }} />
          <h1 className="text-2xl font-bold">Pedido Realizado!</h1>
          <p className="text-muted-foreground">
            Seu pedido #{pedidoId} foi recebido com sucesso.
          </p>
        </div>

        {/* Formulário de cadastro */}
        <div className="border-t pt-6 space-y-4">
          <div className="text-center">
            <h2 className="text-lg font-bold flex items-center justify-center gap-2">
              <User className="w-5 h-5" />
              Crie sua conta
            </h2>
            <p className="text-sm text-muted-foreground mt-1">
              Acompanhe seus pedidos e ganhe vantagens!
            </p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-sm font-bold mb-1 block">Nome *</label>
              <input
                type="text"
                value={nome}
                onChange={e => setNome(e.target.value)}
                placeholder="Seu nome completo"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
                style={{ "--tw-ring-color": corPrimaria } as React.CSSProperties}
              />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Email *</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
                style={{ "--tw-ring-color": corPrimaria } as React.CSSProperties}
              />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Telefone *</label>
              <input
                type="tel"
                value={telefone}
                onChange={e => setTelefone(e.target.value)}
                placeholder="(11) 99999-9999"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
                style={{ "--tw-ring-color": corPrimaria } as React.CSSProperties}
              />
            </div>
            <div>
              <label className="text-sm font-bold mb-1 block">Senha *</label>
              <input
                type="password"
                value={senha}
                onChange={e => setSenha(e.target.value)}
                placeholder="Mínimo 6 caracteres"
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2"
                style={{ "--tw-ring-color": corPrimaria } as React.CSSProperties}
              />
            </div>
          </div>

          <Button
            onClick={handleRegistro}
            disabled={registrando}
            className="w-full py-5 text-white font-bold"
            style={{ background: corPrimaria }}
          >
            {registrando ? "Criando conta..." : "Criar Conta e Acompanhar"}
          </Button>
        </div>

        {/* Link pular */}
        <div className="text-center border-t pt-4">
          <button
            onClick={() => navigate(`/order/${pedidoId}`)}
            className="text-sm underline text-muted-foreground hover:text-foreground"
          >
            Pular - Acompanhar sem conta
          </button>
          <span className="block text-xs text-muted-foreground mt-1">ou</span>
          <button
            onClick={() => navigate("/")}
            className="text-sm underline text-muted-foreground hover:text-foreground mt-1"
          >
            Voltar ao cardápio
          </button>
        </div>
      </Card>
    </div>
  );
}
