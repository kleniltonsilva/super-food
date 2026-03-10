import { useState } from "react";
import { useLocation } from "wouter";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useCriarRestaurante } from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { Loader2, ArrowLeft, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { tiposRestaurante } from "@/config/themeConfig";

const PLANOS = [
  { nome: "Básico", valor: 199.0, motoboys: 3, descricao: "Ideal para pequenos restaurantes - até 3 motoboys simultâneos" },
  { nome: "Essencial", valor: 269.0, motoboys: 6, descricao: "Bom equilíbrio - até 6 motoboys simultâneos" },
  { nome: "Avançado", valor: 360.0, motoboys: 12, descricao: "Para crescimento - até 12 motoboys simultâneos" },
  { nome: "Premium", valor: 599.0, motoboys: 999, descricao: "Top: motoboys ilimitados + suporte prioritário" },
];

interface FormData {
  nome_fantasia: string;
  razao_social: string;
  cnpj: string;
  email: string;
  telefone: string;
  endereco_completo: string;
  cidade: string;
  estado: string;
  cep: string;
  plano: string;
  criar_site: boolean;
  tipo_restaurante: string;
  whatsapp: string;
}

export default function NovoRestaurante() {
  const [, navigate] = useLocation();
  const criarMut = useCriarRestaurante();

  const [form, setForm] = useState<FormData>({
    nome_fantasia: "",
    razao_social: "",
    cnpj: "",
    email: "",
    telefone: "",
    endereco_completo: "",
    cidade: "",
    estado: "",
    cep: "",
    plano: "Básico",
    criar_site: true,
    tipo_restaurante: "geral",
    whatsapp: "",
  });

  const [resultado, setResultado] = useState<{
    codigo_acesso: string;
    senha_padrao: string;
    nome_fantasia: string;
  } | null>(null);

  function updateField(field: keyof FormData, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  const planoSelecionado = PLANOS.find((p) => p.nome === form.plano) || PLANOS[0];

  function validar(): string[] {
    const erros: string[] = [];
    if (!form.nome_fantasia.trim() || form.nome_fantasia.trim().length < 3) {
      erros.push("Nome Fantasia é obrigatório (mínimo 3 caracteres)");
    }
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!form.email.trim() || !emailRegex.test(form.email.trim())) {
      erros.push("Email inválido");
    }
    const telDigits = form.telefone.replace(/\D/g, "");
    if (telDigits.length < 10) {
      erros.push("Telefone inválido (mínimo 10 dígitos)");
    }
    if (!form.endereco_completo.trim() || form.endereco_completo.trim().length < 10) {
      erros.push("Endereço completo é obrigatório (mínimo 10 caracteres)");
    }
    if (form.cnpj.trim()) {
      const cnpjDigits = form.cnpj.replace(/\D/g, "");
      if (cnpjDigits.length !== 14) {
        erros.push("CNPJ deve ter 14 dígitos");
      }
    }
    return erros;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const erros = validar();
    if (erros.length > 0) {
      erros.forEach((err) => toast.error(err));
      return;
    }

    criarMut.mutate(
      {
        nome_fantasia: form.nome_fantasia.trim(),
        razao_social: form.razao_social.trim() || undefined,
        cnpj: form.cnpj.trim() || undefined,
        email: form.email.trim().toLowerCase(),
        telefone: form.telefone.replace(/\D/g, ""),
        endereco_completo: form.endereco_completo.trim(),
        cidade: form.cidade.trim() || undefined,
        estado: form.estado.trim() || undefined,
        cep: form.cep.trim() || undefined,
        plano: form.plano,
        valor_plano: planoSelecionado.valor,
        limite_motoboys: planoSelecionado.motoboys,
        criar_site: form.criar_site,
        tipo_restaurante: form.tipo_restaurante,
        whatsapp: form.whatsapp.trim() || undefined,
      },
      {
        onSuccess: (data) => {
          toast.success("Restaurante criado com sucesso!");
          setResultado({
            codigo_acesso: data.codigo_acesso,
            senha_padrao: data.senha_padrao,
            nome_fantasia: data.nome_fantasia,
          });
        },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao criar restaurante";
          toast.error(msg);
        },
      }
    );
  }

  // Tela de sucesso
  if (resultado) {
    return (
      <SuperAdminLayout>
        <div className="mx-auto max-w-lg space-y-6 py-10">
          <div className="text-center">
            <CheckCircle className="mx-auto h-16 w-16 text-green-500" />
            <h2 className="mt-4 text-2xl font-bold text-white">Restaurante Criado!</h2>
            <p className="mt-1 text-gray-400">{resultado.nome_fantasia}</p>
          </div>

          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 space-y-4">
            <div>
              <p className="text-sm text-gray-400">Código de Acesso</p>
              <p className="text-lg font-mono font-bold text-amber-400">{resultado.codigo_acesso}</p>
            </div>
            <div>
              <p className="text-sm text-gray-400">Senha Padrão</p>
              <p className="text-lg font-mono font-bold text-white">{resultado.senha_padrao}</p>
            </div>
            <p className="text-xs text-gray-500">
              O restaurante pode acessar o painel com o email e esta senha.
            </p>
          </div>

          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1 border-gray-700 text-gray-300 hover:bg-gray-800"
              onClick={() => {
                setResultado(null);
                setForm({
                  nome_fantasia: "", razao_social: "", cnpj: "", email: "", telefone: "",
                  endereco_completo: "", cidade: "", estado: "", cep: "",
                  plano: "Básico", criar_site: true, tipo_restaurante: "geral", whatsapp: "",
                });
              }}
            >
              Criar Outro
            </Button>
            <Button
              className="flex-1 bg-amber-600 hover:bg-amber-700 text-white"
              onClick={() => navigate("/restaurantes")}
            >
              Ver Restaurantes
            </Button>
          </div>
        </div>
      </SuperAdminLayout>
    );
  }

  return (
    <SuperAdminLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="text-gray-400 hover:text-white"
            onClick={() => navigate("/restaurantes")}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h2 className="text-2xl font-bold text-white">Novo Restaurante</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Bloco 1 - Dados Básicos */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Dados Básicos</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Nome Fantasia *</label>
                <Input
                  placeholder="Ex: Burger Elite"
                  value={form.nome_fantasia}
                  onChange={(e) => updateField("nome_fantasia", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Razão Social</label>
                <Input
                  placeholder="Ex: Burger Elite LTDA"
                  value={form.razao_social}
                  onChange={(e) => updateField("razao_social", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Email *</label>
                <Input
                  type="email"
                  placeholder="contato@burgerelite.com.br"
                  value={form.email}
                  onChange={(e) => updateField("email", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Telefone/WhatsApp *</label>
                <Input
                  placeholder="(11) 99999-9999"
                  value={form.telefone}
                  onChange={(e) => updateField("telefone", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">CNPJ</label>
                <Input
                  placeholder="00.000.000/0000-00"
                  value={form.cnpj}
                  onChange={(e) => updateField("cnpj", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                />
              </div>
            </div>
          </div>

          {/* Bloco 2 - Endereço */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Endereço</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Endereço Completo *</label>
                <Textarea
                  placeholder="Rua Augusta 123, Bairro Centro, São Paulo, SP, Brasil, CEP 01000-000"
                  value={form.endereco_completo}
                  onChange={(e) => updateField("endereco_completo", e.target.value)}
                  className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  rows={2}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Cidade</label>
                  <Input
                    placeholder="São Paulo"
                    value={form.cidade}
                    onChange={(e) => updateField("cidade", e.target.value)}
                    className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">Estado</label>
                  <Input
                    placeholder="SP"
                    value={form.estado}
                    onChange={(e) => updateField("estado", e.target.value)}
                    className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-gray-300">CEP</label>
                  <Input
                    placeholder="01000-000"
                    value={form.cep}
                    onChange={(e) => updateField("cep", e.target.value)}
                    className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bloco 3 - Site do Cliente */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Site do Cliente</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="criar_site"
                  checked={form.criar_site}
                  onCheckedChange={(checked) => updateField("criar_site", !!checked)}
                />
                <label htmlFor="criar_site" className="text-sm text-gray-300">
                  Criar site automaticamente
                </label>
              </div>
              {form.criar_site && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">Tipo de Restaurante *</label>
                    <Select value={form.tipo_restaurante} onValueChange={(v) => updateField("tipo_restaurante", v)}>
                      <SelectTrigger className="border-gray-700 bg-gray-800 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {tiposRestaurante.map((t) => (
                          <SelectItem key={t.id} value={t.id}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-300">WhatsApp (com DDD)</label>
                    <Input
                      placeholder="11999999999"
                      value={form.whatsapp}
                      onChange={(e) => updateField("whatsapp", e.target.value)}
                      className="border-gray-700 bg-gray-800 text-white placeholder:text-gray-500"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bloco 4 - Plano */}
          <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h3 className="mb-4 text-lg font-semibold text-white">Plano de Assinatura</h3>
            <div className="grid gap-3 sm:grid-cols-2">
              {PLANOS.map((p) => (
                <button
                  key={p.nome}
                  type="button"
                  onClick={() => updateField("plano", p.nome)}
                  className={cn(
                    "rounded-lg border p-4 text-left transition-all",
                    form.plano === p.nome
                      ? "border-amber-500 bg-amber-500/10"
                      : "border-gray-700 bg-gray-800 hover:border-gray-600"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-white">{p.nome}</span>
                    <span className="text-lg font-bold text-amber-400">
                      R$ {p.valor.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-gray-400">{p.descricao}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            className="w-full bg-amber-600 hover:bg-amber-700 text-white py-3"
            disabled={criarMut.isPending}
          >
            {criarMut.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Criando...
              </>
            ) : (
              "Criar Restaurante"
            )}
          </Button>
        </form>
      </div>
    </SuperAdminLayout>
  );
}
