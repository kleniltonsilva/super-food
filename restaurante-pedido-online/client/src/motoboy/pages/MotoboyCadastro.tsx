import { useState } from "react";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cadastroMotoboy } from "@/motoboy/lib/motoboyApiClient";
import { toast } from "sonner";
import { Loader2, UserPlus, ArrowLeft } from "lucide-react";
import { validarCPF, formatarCPF, limparCPF } from "@/utils/cpf";

export default function MotoboyCadastro() {
  const [codigo, setCodigo] = useState("");
  const [nome, setNome] = useState("");
  const [usuario, setUsuario] = useState("");
  const [telefone, setTelefone] = useState("");
  const [cpf, setCpf] = useState("");
  const [loading, setLoading] = useState(false);
  const [sucesso, setSucesso] = useState(false);
  const [, navigate] = useLocation();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    const erros: string[] = [];
    if (!codigo.trim() || codigo.trim().length !== 8) erros.push("Código de acesso deve ter 8 dígitos");
    if (!nome.trim() || nome.trim().length < 3) erros.push("Nome deve ter pelo menos 3 caracteres");
    if (!usuario.trim() || usuario.trim().length < 3) erros.push("Usuário deve ter pelo menos 3 caracteres");
    const telDigits = telefone.replace(/\D/g, "");
    if (telDigits.length < 10) erros.push("Telefone inválido (mínimo 10 dígitos)");
    const cpfLimpo = limparCPF(cpf);
    if (cpfLimpo && !validarCPF(cpfLimpo)) erros.push("CPF inválido");

    if (erros.length > 0) {
      erros.forEach((e) => toast.error(e));
      return;
    }

    setLoading(true);
    try {
      await cadastroMotoboy({
        codigo_acesso: codigo.trim().toUpperCase(),
        nome: nome.trim(),
        usuario: usuario.trim(),
        telefone: telefone.trim(),
        cpf: cpfLimpo || undefined,
      });
      setSucesso(true);
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail || "Erro ao enviar solicitação";
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }

  if (sucesso) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
        <Card className="w-full max-w-sm border-gray-800 bg-gray-900">
          <CardContent className="space-y-4 pt-6 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-green-500/20">
              <UserPlus className="h-7 w-7 text-green-500" />
            </div>
            <h2 className="text-lg font-bold text-white">Solicitação Enviada!</h2>
            <p className="text-sm text-gray-400">
              Aguarde a aprovação do restaurante. Quando aprovado, use:
            </p>
            <div className="space-y-1 rounded-lg bg-gray-800 p-3 text-left text-sm">
              <p className="text-gray-300"><span className="text-gray-500">Código:</span> {codigo.trim().toUpperCase()}</p>
              <p className="text-gray-300"><span className="text-gray-500">Usuário:</span> {usuario.trim().toLowerCase()}</p>
              <p className="text-gray-300"><span className="text-gray-500">Senha:</span> 123456</p>
            </div>
            <Button
              className="w-full bg-green-600 hover:bg-green-700"
              onClick={() => navigate("/login")}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar para Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-950 px-4">
      <Card className="w-full max-w-sm border-gray-800 bg-gray-900">
        <CardHeader className="text-center">
          <CardTitle className="text-xl text-white">Solicitar Cadastro</CardTitle>
          <p className="text-sm text-gray-400">
            Preencha seus dados para solicitar acesso
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Código de Acesso *</label>
              <Input
                type="text"
                placeholder="Solicite ao restaurante (8 dígitos)"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.toUpperCase())}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                maxLength={8}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Nome Completo *</label>
              <Input
                type="text"
                placeholder="Seu nome completo"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Usuário *</label>
              <Input
                type="text"
                placeholder="Escolha um nome de usuário"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">Telefone/WhatsApp *</label>
              <Input
                type="tel"
                placeholder="(11) 99999-9999"
                value={telefone}
                onChange={(e) => setTelefone(e.target.value)}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-300">CPF</label>
              <Input
                type="text"
                placeholder="000.000.000-00"
                value={cpf}
                onChange={(e) => setCpf(formatarCPF(e.target.value))}
                className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                maxLength={14}
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
                  Enviando...
                </>
              ) : (
                <>
                  <UserPlus className="mr-2 h-4 w-4" />
                  Solicitar Cadastro
                </>
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full text-gray-400"
              onClick={() => navigate("/login")}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Voltar para Login
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
