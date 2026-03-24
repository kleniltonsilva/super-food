import { useState, useMemo } from "react";
import { useLocation } from "wouter";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import { useCriarRestaurante, useConsultarCnpj, useBillingConfig } from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import {
  Loader2, ArrowLeft, CheckCircle, Search, Copy, Mail, MailX,
  ExternalLink, Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { tiposRestaurante } from "@/config/themeConfig";
import InfoTooltip from "@/components/InfoTooltip";
import AddressAutocomplete from "@/components/AddressAutocomplete";
import { autocompleteEndereco } from "@/superadmin/lib/superAdminApiClient";
import {
  formatarTelefone,
  formatarCpfCnpj,
  formatarCep,
  validarCpf,
  validarCnpj,
  validarTelefone,
} from "@/superadmin/lib/validators";

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
  iniciar_trial: boolean;
  enviar_email: boolean;
}

interface ResultadoCriacao {
  codigo_acesso: string;
  senha_padrao: string;
  nome_fantasia: string;
  email: string;
  email_enviado: boolean;
  trial_dias: number;
}

const inputBase = "border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)] placeholder:text-[var(--sa-text-dimmed)]";

export default function NovoRestaurante() {
  const [, navigate] = useLocation();
  const criarMut = useCriarRestaurante();
  const cnpjMut = useConsultarCnpj();
  const { data: billingConfig } = useBillingConfig();

  const trialDias = billingConfig?.trial_dias ?? 15;

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
    iniciar_trial: true,
    enviar_email: true,
  });

  const [resultado, setResultado] = useState<ResultadoCriacao | null>(null);
  const [cnpjStatus, setCnpjStatus] = useState<"idle" | "found" | "not_found">("idle");

  function updateField(field: keyof FormData, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  const planoSelecionado = PLANOS.find((p) => p.nome === form.plano) || PLANOS[0];

  // --- Validação em tempo real ---
  const telefoneValidation = useMemo(() => {
    const digits = form.telefone.replace(/\D/g, "");
    if (digits.length < 2) return null;
    return validarTelefone(form.telefone);
  }, [form.telefone]);

  const cpfCnpjValidation = useMemo(() => {
    const digits = form.cnpj.replace(/\D/g, "");
    if (digits.length === 0) return null;
    if (digits.length === 11) return { valido: validarCpf(form.cnpj), tipo: "CPF" as const };
    if (digits.length === 14) return { valido: validarCnpj(form.cnpj), tipo: "CNPJ" as const };
    return { valido: false, tipo: digits.length > 11 ? "CNPJ" as const : "CPF" as const };
  }, [form.cnpj]);

  const cnpjPodeConsultar = cpfCnpjValidation?.tipo === "CNPJ" && cpfCnpjValidation.valido;

  // --- Consulta CNPJ ---
  function handleConsultarCnpj() {
    if (!cnpjPodeConsultar) return;
    setCnpjStatus("idle");
    cnpjMut.mutate(form.cnpj, {
      onSuccess: (data) => {
        setCnpjStatus("found");
        setForm((prev) => {
          const updates: Partial<FormData> = {};
          if (data.nome_fantasia && !prev.nome_fantasia.trim())
            updates.nome_fantasia = data.nome_fantasia;
          if (data.razao_social)
            updates.razao_social = data.razao_social;
          if (data.email && !prev.email.trim())
            updates.email = data.email.toLowerCase();
          if (data.telefone_1 && !prev.telefone.replace(/\D/g, ""))
            updates.telefone = formatarTelefone(data.telefone_1);
          // Montar endereço
          const partes = [data.logradouro, data.numero, data.complemento, data.bairro].filter(Boolean);
          if (partes.length > 0 && !prev.endereco_completo.trim())
            updates.endereco_completo = partes.join(", ");
          if (data.municipio && !prev.cidade.trim())
            updates.cidade = data.municipio;
          if (data.uf && !prev.estado.trim())
            updates.estado = data.uf;
          if (data.cep && !prev.cep.replace(/\D/g, ""))
            updates.cep = formatarCep(data.cep);
          return { ...prev, ...updates };
        });
        toast.success("Dados preenchidos pela Receita Federal");
      },
      onError: (err: unknown) => {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao consultar CNPJ";
        setCnpjStatus("not_found");
        toast.error(msg);
      },
    });
  }

  // --- Validação final ---
  function validar(): string[] {
    const erros: string[] = [];
    if (!form.nome_fantasia.trim() || form.nome_fantasia.trim().length < 3)
      erros.push("Nome Fantasia é obrigatório (mínimo 3 caracteres)");

    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!form.email.trim() || !emailRegex.test(form.email.trim()))
      erros.push("Email inválido");

    const telResult = validarTelefone(form.telefone);
    if (!telResult.valido)
      erros.push(telResult.erro || "Telefone inválido");

    if (!form.endereco_completo.trim() || form.endereco_completo.trim().length < 10)
      erros.push("Endereço completo é obrigatório (mínimo 10 caracteres)");

    if (form.cnpj.replace(/\D/g, "").length > 0) {
      const digits = form.cnpj.replace(/\D/g, "");
      if (digits.length === 11 && !validarCpf(form.cnpj))
        erros.push("CPF inválido (dígitos verificadores incorretos)");
      else if (digits.length === 14 && !validarCnpj(form.cnpj))
        erros.push("CNPJ inválido (dígitos verificadores incorretos)");
      else if (digits.length !== 11 && digits.length !== 14)
        erros.push("CPF deve ter 11 dígitos ou CNPJ deve ter 14 dígitos");
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
        cnpj: form.cnpj.replace(/\D/g, "") || undefined,
        email: form.email.trim().toLowerCase(),
        telefone: form.telefone.replace(/\D/g, ""),
        endereco_completo: form.endereco_completo.trim(),
        cidade: form.cidade.trim() || undefined,
        estado: form.estado.trim() || undefined,
        cep: form.cep.replace(/\D/g, "") || undefined,
        plano: form.plano,
        valor_plano: planoSelecionado.valor,
        limite_motoboys: planoSelecionado.motoboys,
        criar_site: form.criar_site,
        tipo_restaurante: form.tipo_restaurante,
        whatsapp: form.whatsapp.replace(/\D/g, "") || undefined,
        enviar_email: form.enviar_email,
      } as any,
      {
        onSuccess: (data) => {
          toast.success("Restaurante criado com sucesso!");
          setResultado({
            codigo_acesso: data.codigo_acesso,
            senha_padrao: data.senha_padrao,
            nome_fantasia: data.nome_fantasia,
            email: form.email.trim().toLowerCase(),
            email_enviado: data.email_enviado ?? false,
            trial_dias: data.trial_dias ?? trialDias,
          });
        },
        onError: (err: unknown) => {
          const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao criar restaurante";
          toast.error(msg);
        },
      }
    );
  }

  function copiarTexto(texto: string) {
    navigator.clipboard.writeText(texto);
    toast.success("Copiado!");
  }

  // ============== TELA DE SUCESSO ==============
  if (resultado) {
    return (
      <SuperAdminLayout>
        <div className="mx-auto max-w-lg space-y-6 py-10">
          <div className="text-center">
            <CheckCircle className="mx-auto h-16 w-16 text-green-500" />
            <h2 className="mt-4 text-2xl font-bold text-[var(--sa-text-primary)]">Restaurante Criado!</h2>
            <p className="mt-1 text-[var(--sa-text-muted)]">{resultado.nome_fantasia}</p>
          </div>

          {/* Credenciais */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--sa-text-muted)]">Código de Acesso</p>
                <p className="text-lg font-mono font-bold text-[var(--sa-accent-text)]">{resultado.codigo_acesso}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => copiarTexto(resultado.codigo_acesso)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-[var(--sa-text-muted)]">Senha Padrão</p>
                <p className="text-lg font-mono font-bold text-[var(--sa-text-primary)]">{resultado.senha_padrao}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => copiarTexto(resultado.senha_padrao)}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
            <p className="text-xs text-[var(--sa-text-dimmed)]">
              O restaurante pode acessar o painel com o email e esta senha.
            </p>
          </div>

          {/* Badges de status */}
          <div className="space-y-2">
            {resultado.email_enviado ? (
              <div className="flex items-center gap-2 rounded-lg bg-green-500/10 border border-green-500/30 px-4 py-2.5">
                <Mail className="h-4 w-4 text-green-500" />
                <span className="text-sm text-green-400">Email enviado para {resultado.email}</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-lg bg-yellow-500/10 border border-yellow-500/30 px-4 py-2.5">
                <MailX className="h-4 w-4 text-yellow-500" />
                <span className="text-sm text-yellow-400">Email não enviado (Resend não configurado ou desabilitado)</span>
              </div>
            )}
            {form.iniciar_trial && (
              <div className="flex items-center gap-2 rounded-lg bg-blue-500/10 border border-blue-500/30 px-4 py-2.5">
                <Clock className="h-4 w-4 text-blue-400" />
                <span className="text-sm text-blue-400">Trial de {resultado.trial_dias} dias iniciado</span>
              </div>
            )}
          </div>

          {/* Botão Guia de Início */}
          <a
            href="/admin/inicio"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full rounded-lg border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] px-4 py-3 text-sm font-medium text-[var(--sa-text-primary)] hover:bg-[var(--sa-bg-hover)] transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            Abrir Guia de Início (Onboarding)
          </a>

          <div className="flex gap-3">
            <Button
              variant="outline"
              className="flex-1 border-[var(--sa-border-input)] text-[var(--sa-text-secondary)] hover:bg-[var(--sa-bg-hover)]"
              onClick={() => {
                setResultado(null);
                setCnpjStatus("idle");
                setForm({
                  nome_fantasia: "", razao_social: "", cnpj: "", email: "", telefone: "",
                  endereco_completo: "", cidade: "", estado: "", cep: "",
                  plano: "Básico", criar_site: true, tipo_restaurante: "geral", whatsapp: "",
                  iniciar_trial: true, enviar_email: true,
                });
              }}
            >
              Criar Outro
            </Button>
            <Button
              className="flex-1 bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)] text-white"
              onClick={() => navigate("/restaurantes")}
            >
              Ver Restaurantes
            </Button>
          </div>
        </div>
      </SuperAdminLayout>
    );
  }

  // ============== FORMULÁRIO ==============
  return (
    <SuperAdminLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            className="text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
            onClick={() => navigate("/restaurantes")}
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h2 className="text-2xl font-bold text-[var(--sa-text-primary)]">Novo Restaurante</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Bloco 1 - Dados Básicos */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6">
            <h3 className="mb-4 text-lg font-semibold text-[var(--sa-text-primary)]">Dados Básicos</h3>
            <div className="grid gap-4 sm:grid-cols-2">
              {/* CPF/CNPJ — primeiro para auto-preencher o resto */}
              <div className="space-y-2 sm:col-span-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                  CPF/CNPJ
                  <InfoTooltip text="Opcional. CPF (11 dígitos) ou CNPJ (14 dígitos). CNPJ válido permite consultar dados na Receita Federal." />
                </label>
                <div className="flex gap-2">
                  <div className="relative flex-1">
                    <Input
                      placeholder="000.000.000-00 ou 00.000.000/0000-00"
                      value={form.cnpj}
                      onChange={(e) => {
                        updateField("cnpj", formatarCpfCnpj(e.target.value));
                        setCnpjStatus("idle");
                      }}
                      className={cn(
                        inputBase,
                        cpfCnpjValidation && cpfCnpjValidation.valido && "border-green-500 focus-visible:ring-green-500",
                        cpfCnpjValidation && !cpfCnpjValidation.valido && form.cnpj.replace(/\D/g, "").length >= 11 && "border-red-500 focus-visible:ring-red-500",
                      )}
                    />
                  </div>
                  {cnpjPodeConsultar && (
                    <Button
                      type="button"
                      variant="outline"
                      className="shrink-0 border-[var(--sa-border-input)] text-[var(--sa-text-secondary)] hover:bg-[var(--sa-bg-hover)]"
                      onClick={handleConsultarCnpj}
                      disabled={cnpjMut.isPending}
                    >
                      {cnpjMut.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Search className="mr-2 h-4 w-4" />
                      )}
                      Consultar Receita
                    </Button>
                  )}
                </div>
                {/* Badges CNPJ */}
                {cnpjStatus === "found" && (
                  <p className="text-xs text-green-400 flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" /> Dados preenchidos pela Receita Federal
                  </p>
                )}
                {cnpjStatus === "not_found" && (
                  <p className="text-xs text-yellow-400">CNPJ não encontrado na Receita Federal</p>
                )}
                {cpfCnpjValidation && !cpfCnpjValidation.valido && form.cnpj.replace(/\D/g, "").length >= 11 && (
                  <p className="text-xs text-red-400">{cpfCnpjValidation.tipo} inválido (dígitos verificadores incorretos)</p>
                )}
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                  Nome Fantasia *
                  <InfoTooltip text="Nome comercial do restaurante, exibido no site e no painel. Mínimo 3 caracteres." />
                </label>
                <Input
                  placeholder="Ex: Burger Elite"
                  value={form.nome_fantasia}
                  onChange={(e) => updateField("nome_fantasia", e.target.value)}
                  className={inputBase}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Razão Social</label>
                <Input
                  placeholder="Ex: Burger Elite LTDA"
                  value={form.razao_social}
                  onChange={(e) => updateField("razao_social", e.target.value)}
                  className={inputBase}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Email *</label>
                <Input
                  type="email"
                  placeholder="contato@burgerelite.com.br"
                  value={form.email}
                  onChange={(e) => updateField("email", e.target.value)}
                  className={inputBase}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                  Telefone/WhatsApp *
                  <InfoTooltip text="DDD + número. Celulares devem começar com 9 após o DDD." />
                </label>
                <Input
                  placeholder="(11) 99999-9999"
                  value={form.telefone}
                  onChange={(e) => updateField("telefone", formatarTelefone(e.target.value))}
                  className={cn(
                    inputBase,
                    telefoneValidation?.valido === true && "border-green-500 focus-visible:ring-green-500",
                    telefoneValidation?.valido === false && "border-red-500 focus-visible:ring-red-500",
                  )}
                />
                {telefoneValidation && !telefoneValidation.valido && (
                  <p className="text-xs text-red-400">{telefoneValidation.erro}</p>
                )}
              </div>
            </div>
          </div>

          {/* Bloco 2 - Endereço */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6">
            <h3 className="mb-4 text-lg font-semibold text-[var(--sa-text-primary)]">Endereço</h3>
            <div className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Endereço Completo *</label>
                <AddressAutocomplete
                  value={form.endereco_completo}
                  onChange={(v) => updateField("endereco_completo", v)}
                  fetchSuggestions={autocompleteEndereco}
                  placeholder="Rua Augusta 123, Bairro Centro, São Paulo, SP, Brasil, CEP 01000-000"
                  className={inputBase}
                  multiline
                  rows={2}
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Cidade</label>
                  <Input
                    placeholder="São Paulo"
                    value={form.cidade}
                    onChange={(e) => updateField("cidade", e.target.value)}
                    className={inputBase}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--sa-text-secondary)]">Estado</label>
                  <Input
                    placeholder="SP"
                    maxLength={2}
                    value={form.estado}
                    onChange={(e) => updateField("estado", e.target.value.toUpperCase())}
                    className={inputBase}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium text-[var(--sa-text-secondary)]">CEP</label>
                  <Input
                    placeholder="01000-000"
                    value={form.cep}
                    onChange={(e) => updateField("cep", formatarCep(e.target.value))}
                    className={inputBase}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bloco 3 - Site do Cliente */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6">
            <h3 className="mb-4 text-lg font-semibold text-[var(--sa-text-primary)]">Site do Cliente</h3>
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="criar_site"
                  checked={form.criar_site}
                  onCheckedChange={(checked) => updateField("criar_site", !!checked)}
                />
                <label htmlFor="criar_site" className="text-sm text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                  Criar site automaticamente
                  <InfoTooltip text="Gera automaticamente o site do cliente com cardápio, checkout e tracking. Categorias padrão são criadas com base no tipo de restaurante." />
                </label>
              </div>
              {form.criar_site && (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                      Tipo de Restaurante *
                      <InfoTooltip text="Define o tema visual do site (cores, fontes, layout). Cada tipo tem categorias padrão pré-configuradas." />
                    </label>
                    <Select value={form.tipo_restaurante} onValueChange={(v) => updateField("tipo_restaurante", v)}>
                      <SelectTrigger className="border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] text-[var(--sa-text-primary)]">
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
                    <label className="text-sm font-medium text-[var(--sa-text-secondary)] flex items-center gap-1.5">
                      WhatsApp (com DDD)
                      <InfoTooltip text="Número com DDD (ex: 11999999999). Exibe botão de contato no site do cliente." />
                    </label>
                    <Input
                      placeholder="(11) 99999-9999"
                      value={form.whatsapp}
                      onChange={(e) => updateField("whatsapp", formatarTelefone(e.target.value))}
                      className={inputBase}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Bloco 4 - Plano */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6">
            <h3 className="mb-4 text-lg font-semibold text-[var(--sa-text-primary)] flex items-center gap-1.5">
              Plano de Assinatura
              <InfoTooltip text="O plano define o valor mensal e o limite de motoboys simultâneos. Pode ser alterado depois." />
            </h3>
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
                      : "border-[var(--sa-border-input)] bg-[var(--sa-bg-hover)] hover:border-[var(--sa-border-input)]"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-[var(--sa-text-primary)]">{p.nome}</span>
                    <span className="text-lg font-bold text-[var(--sa-accent-text)]">
                      R$ {p.valor.toFixed(2)}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-[var(--sa-text-muted)]">{p.descricao}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Billing — Trial + Email */}
          <div className="rounded-xl border border-[var(--sa-border)] bg-[var(--sa-bg-surface)] p-6 space-y-4">
            <div className="flex items-center gap-3">
              <Checkbox
                id="iniciar_trial"
                checked={form.iniciar_trial}
                onCheckedChange={(v) => updateField("iniciar_trial", !!v)}
              />
              <label htmlFor="iniciar_trial" className="text-sm font-medium text-[var(--sa-text-secondary)] cursor-pointer">
                Iniciar período de teste (trial) de <strong>{trialDias}</strong> dias
              </label>
            </div>
            <p className="text-xs text-[var(--sa-text-dimmed)] ml-7">
              Se marcado, o restaurante terá acesso ao plano Premium durante o trial. Após o período, precisará escolher um plano pago.
            </p>

            <div className="border-t border-[var(--sa-border)] pt-4">
              <div className="flex items-center gap-3">
                <Checkbox
                  id="enviar_email"
                  checked={form.enviar_email}
                  onCheckedChange={(v) => updateField("enviar_email", !!v)}
                />
                <label htmlFor="enviar_email" className="text-sm font-medium text-[var(--sa-text-secondary)] cursor-pointer flex items-center gap-1.5">
                  <Mail className="h-4 w-4" />
                  Enviar email de boas-vindas com credenciais
                </label>
              </div>
              <p className="text-xs text-[var(--sa-text-dimmed)] mt-2 ml-7">
                O restaurante receberá um email com código de acesso, senha e link para o guia de início.
              </p>
            </div>
          </div>

          {/* Submit */}
          <Button
            type="submit"
            className="w-full bg-[var(--sa-accent)] hover:bg-[var(--sa-accent-hover)] text-white py-3"
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
