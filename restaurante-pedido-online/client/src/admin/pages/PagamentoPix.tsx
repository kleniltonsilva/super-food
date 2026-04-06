import { useState } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import {
  usePixConfig,
  usePixPreAtivacao,
  useAtivarPix,
  useDesativarPix,
  useSolicitarSaque,
  useConfigSaqueAuto,
  usePixSaques,
} from "@/admin/hooks/useAdminQueries";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  QrCode,
  Wallet,
  ArrowDownToLine,
  Settings,
  CheckCircle2,
  XCircle,
  Copy,
  AlertTriangle,
  Loader2,
  Building2,
  ShieldCheck,
} from "lucide-react";
import { toast } from "sonner";

const STATUS_SAQUE: Record<string, { label: string; color: string }> = {
  concluido: { label: "Concluido", color: "bg-green-500/20 text-green-400" },
  solicitado: { label: "Processando", color: "bg-yellow-500/20 text-yellow-400" },
  falhou: { label: "Falhou", color: "bg-red-500/20 text-red-400" },
};

function formatCentavos(centavos: number): string {
  return (centavos / 100).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function mascararChave(chave: string): string {
  if (!chave || chave.length < 4) return "***";
  return `***${chave.slice(-4)}`;
}

export default function PagamentoPix() {
  const { data: pixConfig, isLoading } = usePixConfig();
  const { data: preAtivacao, isLoading: loadingPre } = usePixPreAtivacao();
  const ativarPix = useAtivarPix();
  const desativarPix = useDesativarPix();
  const solicitarSaque = useSolicitarSaque();
  const configSaqueAuto = useConfigSaqueAuto();
  const { data: saquesData } = usePixSaques(pixConfig?.ativo ? undefined : undefined);

  // Form de adesao
  const [aceitouTermos, setAceitouTermos] = useState(false);

  // Saque
  const [valorSaque, setValorSaque] = useState("");
  const [saqueDialogOpen, setSaqueDialogOpen] = useState(false);

  // Desativar
  const [desativarDialogOpen, setDesativarDialogOpen] = useState(false);

  if (isLoading || loadingPre) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin h-8 w-8 border-4 border-[var(--cor-primaria)] border-t-transparent rounded-full" />
        </div>
      </AdminLayout>
    );
  }

  // ─── Estado 1: Pix Nao Ativo ────────────────────────────
  if (!pixConfig?.ativo) {
    const podeAtivar = preAtivacao?.pode_ativar;

    const handleAtivar = () => {
      ativarPix.mutate(
        { termos_aceitos: true },
        {
          onSuccess: () => {
            toast.success("Pix Online ativado com sucesso!");
            setAceitouTermos(false);
          },
          onError: (err: any) => {
            const msg = err?.response?.data?.detail || err?.message || "Erro ao ativar Pix";
            toast.error(msg);
          },
        }
      );
    }

    return (
      <AdminLayout>
        <div className="space-y-6 max-w-2xl">
          <div className="flex items-center gap-3">
            <QrCode className="h-7 w-7 text-[var(--cor-primaria)]" />
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Pagamentos Online</h1>
          </div>

          <Card className="bg-[var(--bg-card)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                <Wallet className="h-5 w-5 text-[var(--cor-primaria)]" />
                Receba pagamentos Pix online dos seus clientes!
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <ul className="space-y-3 text-sm text-[var(--text-secondary)]">
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>A Derekh Food oferece este servico <strong className="text-[var(--text-primary)]">100% gratuito</strong> para seu negocio crescer sem barreiras</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>Utilizamos o sistema de split de pagamentos da Woovi (instituicao regulada pelo Banco Central)</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>A Woovi cobra <strong className="text-[var(--text-primary)]">R$0,85 por pagamento Pix</strong> recebido — a Derekh Food nao cobra nada</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>Saques para sua conta: <strong className="text-[var(--text-primary)]">R$1,00 por saque</strong> (gratis para saques &ge; R$500)</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>Voce pode configurar saque automatico para nunca pagar taxa</span>
                </li>
                <li className="flex items-start gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                  <span>Nao e necessario criar conta na Woovi — tudo e gerenciado pelo seu painel Derekh</span>
                </li>
              </ul>

              <hr className="border-[var(--border-subtle)]" />

              {/* Dados da empresa para ativacao */}
              <div className="space-y-4">
                <h3 className="text-base font-semibold text-[var(--text-primary)]">Ativar Pix Online</h3>

                {!podeAtivar ? (
                  <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
                    <AlertTriangle className="h-5 w-5 text-yellow-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium text-yellow-400">CNPJ/CPF nao cadastrado</p>
                      <p className="text-sm text-[var(--text-muted)] mt-1">{preAtivacao?.motivo}</p>
                      <Button
                        variant="outline"
                        size="sm"
                        className="mt-3"
                        onClick={() => window.location.href = "/configuracoes"}
                      >
                        Ir para Configuracoes
                      </Button>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Dados que serao usados (somente leitura) */}
                    <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-4 space-y-3">
                      <div className="flex items-center gap-2 mb-2">
                        <ShieldCheck className="h-4 w-4 text-[var(--cor-primaria)]" />
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          Dados da sua empresa (cadastro oficial)
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--text-muted)]">Chave Pix ({preAtivacao.tipo_chave === "cnpj" ? "CNPJ" : "CPF"})</span>
                        <span className="text-sm font-mono font-medium text-[var(--text-primary)]">
                          {preAtivacao.pix_chave_formatada}
                        </span>
                      </div>

                      <div className="flex items-center justify-between">
                        <span className="text-sm text-[var(--text-muted)]">Nome da subconta</span>
                        <span className="text-sm font-medium text-[var(--text-primary)]">
                          {preAtivacao.nome_subconta}
                        </span>
                      </div>

                      <p className="text-xs text-[var(--text-muted)] mt-2 flex items-center gap-1.5">
                        <Building2 className="h-3 w-3" />
                        Para alterar, atualize o CNPJ e Razao Social nas Configuracoes.
                      </p>
                    </div>

                    <div className="flex items-start gap-3 rounded-lg border border-[var(--border-subtle)] p-3">
                      <Checkbox
                        id="termos-pix"
                        checked={aceitouTermos}
                        onCheckedChange={(checked) => setAceitouTermos(checked === true)}
                        className="mt-0.5"
                      />
                      <label htmlFor="termos-pix" className="text-sm text-[var(--text-secondary)] cursor-pointer leading-relaxed">
                        Li e concordo com as regras de pagamento Pix online. Estou ciente de que a Woovi cobra R$0,85 por transacao recebida e R$1,00 por saque (isento para saques &ge; R$500).
                      </label>
                    </div>

                    <Button
                      className="w-full bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                      disabled={!aceitouTermos || ativarPix.isPending}
                      onClick={handleAtivar}
                    >
                      {ativarPix.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <QrCode className="mr-2 h-4 w-4" />
                      )}
                      {ativarPix.isPending ? "Ativando..." : "Ativar Pix Online"}
                    </Button>
                  </>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </AdminLayout>
    );
  }

  // ─── Estado 2: Pix Ativo ────────────────────────────────
  const saldoCentavos = pixConfig?.saldo_centavos ?? 0;
  const loadingSaldo = isLoading;
  const valorSaqueCentavos = Math.round(parseFloat(valorSaque || "0") * 100);
  const taxaSaque = valorSaqueCentavos >= 50000 ? 0 : 100;
  const valorLiquido = valorSaqueCentavos - taxaSaque;

  const saques = saquesData?.saques ?? [];

  function handleAbrirSaqueDialog() {
    if (!valorSaque || valorSaqueCentavos < 100) {
      toast.error("Informe um valor minimo de R$ 1,00");
      return;
    }
    if (valorSaqueCentavos > saldoCentavos) {
      toast.error("Valor excede o saldo disponivel");
      return;
    }
    setSaqueDialogOpen(true);
  }

  const handleConfirmarSaque = () => {
    solicitarSaque.mutate(
      valorSaqueCentavos,
      {
        onSuccess: () => {
          toast.success("Saque solicitado com sucesso!");
          setValorSaque("");
          setSaqueDialogOpen(false);
        },
        onError: (err: any) => {
          const msg = err?.response?.data?.detail || err?.message || "Erro ao solicitar saque";
          toast.error(msg);
        },
      }
    );
  }

  function handleDesativar() {
    desativarPix.mutate(undefined, {
      onSuccess: () => {
        toast.success("Pix Online desativado");
        setDesativarDialogOpen(false);
      },
      onError: (err: any) => {
        const msg = err?.response?.data?.detail || err?.message || "Erro ao desativar";
        toast.error(msg);
      },
    });
  }

  const handleToggleSaqueAuto = (ativo: boolean) => {
    configSaqueAuto.mutate(
      {
        saque_automatico: ativo,
        saque_minimo_centavos: pixConfig?.saque_minimo_centavos ?? 50000,
      },
      {
        onSuccess: () => toast.success(ativo ? "Saque automatico ativado" : "Saque automatico desativado"),
        onError: () => toast.error("Erro ao atualizar configuracao"),
      }
    );
  };

  const handleAlterarMinimoSaque = (valor: string) => {
    configSaqueAuto.mutate(
      {
        saque_automatico: pixConfig?.saque_automatico ?? false,
        saque_minimo_centavos: parseInt(valor),
      },
      {
        onSuccess: () => toast.success("Valor minimo de saque atualizado"),
        onError: () => toast.error("Erro ao atualizar configuracao"),
      }
    );
  };

  const TIPOS_CHAVE_MAP: Record<string, string> = { cpf: "CPF", cnpj: "CNPJ", email: "E-mail", celular: "Celular", aleatoria: "Aleatória" };
  const tipoChaveLabel = TIPOS_CHAVE_MAP[pixConfig.tipo_chave] || pixConfig.tipo_chave;

  return (
    <AdminLayout>
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <QrCode className="h-7 w-7 text-[var(--cor-primaria)]" />
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Pagamentos Online</h1>
          <Badge className="bg-green-500/20 text-green-400">Pix Ativo</Badge>
        </div>

        <Tabs defaultValue="saldo">
          <TabsList>
            <TabsTrigger value="saldo" className="flex items-center gap-1.5">
              <Wallet className="h-4 w-4" /> Saldo
            </TabsTrigger>
            <TabsTrigger value="saques" className="flex items-center gap-1.5">
              <ArrowDownToLine className="h-4 w-4" /> Saques
            </TabsTrigger>
            <TabsTrigger value="config" className="flex items-center gap-1.5">
              <Settings className="h-4 w-4" /> Configuracoes
            </TabsTrigger>
          </TabsList>

          {/* ─── Tab Saldo ──────────────────────────────────── */}
          <TabsContent value="saldo">
            <div className="grid gap-4 md:grid-cols-2">
              {/* Card Chave Pix */}
              <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm text-[var(--text-muted)]">Chave Pix Cadastrada</CardTitle>
                  <QrCode className="h-4 w-4 text-[var(--text-muted)]" />
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-[var(--text-primary)]">
                      {mascararChave(pixConfig.pix_chave)}
                    </span>
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(pixConfig.pix_chave);
                        toast.success("Chave copiada");
                      }}
                      className="text-[var(--text-muted)] hover:text-[var(--cor-primaria)] transition-colors"
                      title="Copiar chave"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                  </div>
                  <p className="text-xs text-[var(--text-muted)] mt-1">Tipo: {tipoChaveLabel}</p>
                </CardContent>
              </Card>

              {/* Card Saldo */}
              <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm text-[var(--text-muted)]">Saldo Disponivel</CardTitle>
                  <Wallet className="h-4 w-4 text-[var(--text-muted)]" />
                </CardHeader>
                <CardContent>
                  {loadingSaldo ? (
                    <div className="flex items-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-[var(--text-muted)]" />
                      <span className="text-sm text-[var(--text-muted)]">Consultando...</span>
                    </div>
                  ) : (
                    <div className="text-2xl font-bold text-[var(--text-primary)]">
                      R$ {formatCentavos(saldoCentavos)}
                    </div>
                  )}
                  <p className="text-xs text-[var(--text-muted)] mt-1">Atualizado a cada 30 segundos</p>
                </CardContent>
              </Card>

              {/* Secao Sacar */}
              <Card className="md:col-span-2 bg-[var(--bg-surface)] border-[var(--border-subtle)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                    <ArrowDownToLine className="h-5 w-5" /> Sacar
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-[var(--text-secondary)]">Quanto deseja sacar?</label>
                    <div className="flex gap-3">
                      <div className="relative flex-1">
                        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)] text-sm">R$</span>
                        <Input
                          type="number"
                          step="0.01"
                          min="1"
                          max={saldoCentavos / 100}
                          value={valorSaque}
                          onChange={(e) => setValorSaque(e.target.value)}
                          className="dark-input pl-9"
                          placeholder="0,00"
                        />
                      </div>
                      <Button
                        onClick={handleAbrirSaqueDialog}
                        disabled={!valorSaque || valorSaqueCentavos < 100 || valorSaqueCentavos > saldoCentavos}
                        className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
                      >
                        <ArrowDownToLine className="mr-2 h-4 w-4" />
                        Sacar
                      </Button>
                    </div>
                  </div>

                  {valorSaque && valorSaqueCentavos >= 100 && (
                    <div className={`flex items-center gap-2 rounded-md px-3 py-2 ${
                      valorSaqueCentavos >= 50000
                        ? "bg-green-500/10 border border-green-500/30"
                        : "bg-yellow-500/10 border border-yellow-500/30"
                    }`}>
                      {valorSaqueCentavos >= 50000 ? (
                        <>
                          <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
                          <p className="text-xs text-green-400">
                            Saque sem taxa! Voce recebera R$ {formatCentavos(valorSaqueCentavos)}
                          </p>
                        </>
                      ) : (
                        <>
                          <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0" />
                          <p className="text-xs text-yellow-400">
                            Sera cobrada taxa de R$1,00 pela Woovi. Voce recebera R$ {formatCentavos(Math.max(0, valorSaqueCentavos - 100))}
                          </p>
                        </>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* ─── Tab Saques ─────────────────────────────────── */}
          <TabsContent value="saques">
            <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
              <CardHeader>
                <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                  <ArrowDownToLine className="h-5 w-5" /> Historico de Saques
                </CardTitle>
              </CardHeader>
              <CardContent>
                {saques.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-[var(--border-subtle)]">
                          <th className="text-left py-2 text-[var(--text-muted)]">Data</th>
                          <th className="text-left py-2 text-[var(--text-muted)]">Valor</th>
                          <th className="text-left py-2 text-[var(--text-muted)]">Taxa</th>
                          <th className="text-left py-2 text-[var(--text-muted)]">Liquido</th>
                          <th className="text-left py-2 text-[var(--text-muted)]">Status</th>
                          <th className="text-left py-2 text-[var(--text-muted)]">Tipo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {saques.map((saque: any) => {
                          const statusInfo = STATUS_SAQUE[saque.status] || {
                            label: saque.status,
                            color: "bg-gray-500/20 text-gray-400",
                          };
                          const liquido = saque.valor_centavos - (saque.taxa_centavos || 0);
                          return (
                            <tr key={saque.id} className="border-b border-[var(--border-subtle)]">
                              <td className="py-2 text-[var(--text-primary)]">
                                {saque.solicitado_em
                                  ? new Date(saque.solicitado_em).toLocaleDateString("pt-BR", {
                                      day: "2-digit",
                                      month: "2-digit",
                                      year: "2-digit",
                                      hour: "2-digit",
                                      minute: "2-digit",
                                    })
                                  : "\u2014"}
                              </td>
                              <td className="py-2 text-[var(--text-primary)]">
                                R$ {formatCentavos(saque.valor_centavos)}
                              </td>
                              <td className="py-2 text-[var(--text-secondary)]">
                                {saque.taxa_centavos > 0
                                  ? `R$ ${formatCentavos(saque.taxa_centavos)}`
                                  : "Isento"}
                              </td>
                              <td className="py-2 text-[var(--text-primary)] font-medium">
                                R$ {formatCentavos(Math.max(0, liquido))}
                              </td>
                              <td className="py-2">
                                <Badge className={statusInfo.color}>{statusInfo.label}</Badge>
                              </td>
                              <td className="py-2 text-[var(--text-secondary)]">
                                {saque.automatico ? "Automatico" : "Manual"}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-[var(--text-muted)] text-center py-8">Nenhum saque realizado</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* ─── Tab Configuracoes ──────────────────────────── */}
          <TabsContent value="config">
            <div className="grid gap-4 max-w-lg">
              {/* Saque Automatico */}
              <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                    <Settings className="h-5 w-5" /> Saque Automatico
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-[var(--text-primary)]">Saque automatico</p>
                      <p className="text-xs text-[var(--text-muted)]">Sacar automaticamente quando o saldo atingir o valor configurado</p>
                    </div>
                    <Switch
                      checked={!!pixConfig.saque_automatico}
                      onCheckedChange={handleToggleSaqueAuto}
                      disabled={configSaqueAuto.isPending}
                    />
                  </div>

                  {pixConfig.saque_automatico && (
                    <div className="space-y-1.5">
                      <label className="text-sm font-medium text-[var(--text-secondary)]">Sacar quando saldo atingir:</label>
                      <Select
                        value={String(pixConfig.saque_minimo_centavos ?? 50000)}
                        onValueChange={handleAlterarMinimoSaque}
                      >
                        <SelectTrigger className="dark-input">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="50000">R$ 500,00 (recomendado — sem taxa)</SelectItem>
                          <SelectItem value="100000">R$ 1.000,00</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  <div className="flex items-start gap-2 rounded-md bg-[var(--bg-card-hover)] border border-[var(--border-subtle)] px-3 py-2">
                    <CheckCircle2 className="h-4 w-4 text-green-400 mt-0.5 shrink-0" />
                    <p className="text-xs text-[var(--text-muted)]">
                      O saque automatico e feito para sua chave Pix cadastrada. Sem taxa para saques &ge; R$500.
                    </p>
                  </div>
                </CardContent>
              </Card>

              {/* Desativar Pix */}
              <Card className="bg-[var(--bg-surface)] border-red-500/30">
                <CardHeader>
                  <CardTitle className="text-[var(--text-primary)] flex items-center gap-2">
                    <XCircle className="h-5 w-5 text-red-400" /> Desativar Pix Online
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm text-[var(--text-muted)]">
                    Ao desativar, seus clientes nao poderao mais pagar com Pix online. Seu saldo restante ainda podera ser sacado.
                  </p>
                  <Button
                    variant="destructive"
                    onClick={() => setDesativarDialogOpen(true)}
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    Desativar Pix Online
                  </Button>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* ─── Dialog Confirmar Saque ─────────────────────────── */}
      <Dialog open={saqueDialogOpen} onOpenChange={setSaqueDialogOpen}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Confirmar Saque</DialogTitle>
            <DialogDescription className="text-[var(--text-muted)]">
              Revise os detalhes do saque antes de confirmar.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="rounded-lg border border-[var(--border-subtle)] p-4 space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-muted)]">Valor do saque</span>
                <span className="text-[var(--text-primary)] font-medium">R$ {formatCentavos(valorSaqueCentavos)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-muted)]">Taxa Woovi</span>
                <span className={taxaSaque > 0 ? "text-yellow-400" : "text-green-400"}>
                  {taxaSaque > 0 ? `R$ ${formatCentavos(taxaSaque)}` : "Isento"}
                </span>
              </div>
              <hr className="border-[var(--border-subtle)]" />
              <div className="flex justify-between text-sm">
                <span className="text-[var(--text-muted)]">Voce recebera</span>
                <span className="text-[var(--text-primary)] font-bold text-base">R$ {formatCentavos(Math.max(0, valorLiquido))}</span>
              </div>
            </div>

            {valorSaqueCentavos >= 50000 ? (
              <div className="flex items-center gap-2 rounded-md bg-green-500/10 border border-green-500/30 px-3 py-2">
                <CheckCircle2 className="h-4 w-4 text-green-400 shrink-0" />
                <p className="text-xs text-green-400">Saque sem taxa! Voce recebera R$ {formatCentavos(valorSaqueCentavos)}</p>
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-3 py-2">
                <AlertTriangle className="h-4 w-4 text-yellow-400 shrink-0" />
                <p className="text-xs text-yellow-400">
                  Sera cobrada taxa de R$1,00 pela Woovi. Voce recebera R$ {formatCentavos(Math.max(0, valorLiquido))}
                </p>
              </div>
            )}

            <div className="flex items-center gap-2 text-sm text-[var(--text-muted)]">
              <span>Destino:</span>
              <span className="text-[var(--text-primary)] font-medium">Chave Pix: {mascararChave(pixConfig.pix_chave)}</span>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSaqueDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              className="bg-[var(--cor-primaria)] hover:bg-[var(--cor-primaria)]/90"
              onClick={handleConfirmarSaque}
              disabled={solicitarSaque.isPending}
            >
              {solicitarSaque.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <ArrowDownToLine className="mr-2 h-4 w-4" />
              )}
              {solicitarSaque.isPending ? "Processando..." : "Confirmar Saque"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ─── Dialog Confirmar Desativacao ───────────────────── */}
      <Dialog open={desativarDialogOpen} onOpenChange={setDesativarDialogOpen}>
        <DialogContent className="bg-[var(--bg-surface)]">
          <DialogHeader>
            <DialogTitle className="text-[var(--text-primary)]">Desativar Pix Online</DialogTitle>
            <DialogDescription className="text-[var(--text-muted)]">
              Tem certeza que deseja desativar o Pix Online?
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3">
            <div className="flex items-start gap-2 rounded-md bg-yellow-500/10 border border-yellow-500/30 px-3 py-2">
              <AlertTriangle className="h-4 w-4 text-yellow-400 mt-0.5 shrink-0" />
              <p className="text-xs text-yellow-400">
                Seus clientes nao poderao mais pagar com Pix online. Se houver saldo restante, voce ainda podera saca-lo entrando em contato com o suporte.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDesativarDialogOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={handleDesativar}
              disabled={desativarPix.isPending}
            >
              {desativarPix.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <XCircle className="mr-2 h-4 w-4" />
              )}
              {desativarPix.isPending ? "Desativando..." : "Sim, Desativar"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminLayout>
  );
}
