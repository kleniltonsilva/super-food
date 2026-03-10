import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useSuperAdminAuth } from "@/superadmin/contexts/SuperAdminAuthContext";
import { loginAdmin } from "@/superadmin/lib/superAdminApiClient";
import { toast } from "sonner";
import { Loader2, Shield } from "lucide-react";

export default function SuperAdminLogin() {
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, isLoggedIn } = useSuperAdminAuth();
  const [, navigate] = useLocation();

  if (isLoggedIn) {
    navigate("/");
    return null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!usuario.trim() || !senha.trim()) {
      toast.error("Preencha usuário e senha");
      return;
    }
    setLoading(true);
    try {
      const data = await loginAdmin(usuario.trim(), senha.trim());
      login(data.access_token, data.admin);
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
      <Card className="w-full max-w-md border-gray-800 bg-gray-900">
        <CardHeader className="text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-amber-600/20">
            <Shield className="h-7 w-7 text-amber-500" />
          </div>
          <CardTitle className="text-2xl text-white">
            Super Admin
          </CardTitle>
          <p className="text-sm text-gray-400">
            Sistema de Gerenciamento - Super Food
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">
                Usuário
              </label>
              <Input
                type="text"
                placeholder="superadmin"
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
                placeholder="••••••••"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                autoComplete="current-password"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-amber-600 hover:bg-amber-700 text-white"
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
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
