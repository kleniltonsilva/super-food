import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { loginMotoboy } from "@/motoboy/lib/motoboyApiClient";
import { toast } from "sonner";
import { Loader2, Bike } from "lucide-react";

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
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
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
