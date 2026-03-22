import { useState } from "react";
import { useLocation } from "wouter";
import { useGarcomAuth } from "@/garcom/contexts/GarcomAuthContext";
import { loginGarcom } from "@/garcom/lib/garcomApiClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Users, Eye, EyeOff } from "lucide-react";

export default function GarcomLogin() {
  const [, navigate] = useLocation();
  const { login } = useGarcomAuth();
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
      const res = await loginGarcom(codigo.trim(), loginField.trim(), senha);
      const garcomData = {
        ...res.garcom,
        restaurante: res.restaurante,
      };
      login(res.access_token, garcomData);
      navigate("/");
    } catch (err: any) {
      setErro(err.response?.data?.detail || "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0806] p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-24 w-24 items-center justify-center rounded-2xl bg-amber-500/10 border border-amber-500/20">
            <Users className="h-12 w-12 text-amber-500" />
          </div>
          <h1 className="text-2xl font-bold text-white" style={{ fontFamily: "'Outfit', sans-serif" }}>
            Derekh Food
          </h1>
          <p className="mt-1 text-sm text-gray-400">App Garçom</p>
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
              className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500 focus:border-amber-500/50"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-gray-300">Login</Label>
            <Input
              value={loginField}
              onChange={(e) => setLoginField(e.target.value)}
              placeholder="Seu login"
              className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500 focus:border-amber-500/50"
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
                className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500 pr-10 focus:border-amber-500/50"
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
            {loading ? "Entrando..." : "Entrar"}
          </Button>
        </form>
      </div>
    </div>
  );
}
