import { useState } from "react";
import { useLocation } from "wouter";
import { useKdsAuth } from "@/kds/contexts/KdsAuthContext";
import { loginCozinheiro } from "@/kds/lib/kdsApiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ChefHat, Eye, EyeOff } from "lucide-react";

export default function KdsLogin() {
  const [, navigate] = useLocation();
  const { login } = useKdsAuth();
  const [codigo, setCodigo] = useState("");
  const [loginField, setLoginField] = useState("");
  const [senha, setSenha] = useState("");
  const [showSenha, setShowSenha] = useState(false);
  const [loading, setLoading] = useState(false);
  const [erro, setErro] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!codigo.trim() || !loginField.trim() || !senha.trim()) {
      setErro("Preencha todos os campos");
      return;
    }

    setLoading(true);
    setErro("");

    try {
      const res = await loginCozinheiro(codigo.trim(), loginField.trim(), senha);
      const cozinheiroData = {
        ...res.cozinheiro,
        restaurante: res.restaurante,
      };
      login(res.access_token, cozinheiroData);
      navigate("/");
    } catch (err: any) {
      setErro(err.response?.data?.detail || "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <img src="/static/logo-derekh-kds.png" alt="Derekh Food" className="mx-auto mb-4 h-40 w-40 rounded-2xl object-contain" />
          <h1 className="text-2xl font-bold text-white">Cozinha Digital</h1>
          <p className="mt-1 text-sm text-gray-400">KDS — Kitchen Display System</p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label className="text-gray-300">Código do Restaurante</Label>
            <Input
              value={codigo}
              onChange={(e) => setCodigo(e.target.value.toUpperCase())}
              placeholder="Ex: 237CC868"
              maxLength={8}
              className="bg-gray-900 border-gray-700 text-white placeholder:text-gray-500"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Login</Label>
            <Input
              value={loginField}
              onChange={(e) => setLoginField(e.target.value)}
              placeholder="Seu login"
              className="bg-gray-900 border-gray-700 text-white placeholder:text-gray-500"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Senha</Label>
            <div className="relative">
              <Input
                type={showSenha ? "text" : "password"}
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                placeholder="Sua senha"
                className="bg-gray-900 border-gray-700 text-white placeholder:text-gray-500 pr-10"
              />
              <button
                type="button"
                onClick={() => setShowSenha(!showSenha)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300"
              >
                {showSenha ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {erro && (
            <p className="text-sm text-red-400 text-center">{erro}</p>
          )}

          <Button
            type="submit"
            disabled={loading}
            className="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-semibold"
          >
            {loading ? "Entrando..." : "Entrar na Cozinha"}
          </Button>
        </form>
      </div>
    </div>
  );
}
