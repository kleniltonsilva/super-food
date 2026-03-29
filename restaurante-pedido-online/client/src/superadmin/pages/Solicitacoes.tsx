import { useState } from "react";
import SuperAdminLayout from "@/superadmin/components/SuperAdminLayout";
import {
  useSolicitacoes,
  useAtualizarSolicitacao,
  useCriarRestauranteDeSolicitacao,
} from "@/superadmin/hooks/useSuperAdminQueries";
import { Spinner } from "@/components/ui/spinner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
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
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  Clock,
  Store,
  Loader2,
  Eye,
  UserPlus,
} from "lucide-react";

interface Solicitacao {
  id: number;
  nome_fantasia: string;
  nome_responsavel: string;
  email: string;
  telefone: string;
  cnpj: string | null;
  cidade: string | null;
  estado: string | null;
  tipo_restaurante: string;
  mensagem: string | null;
  status: string;
  motivo_rejeicao: string | null;
  restaurante_id: number | null;
  criado_em: string | null;
  atualizado_em: string | null;
  ip_origem: string | null;
}

const STATUS_OPTIONS = [
  { value: "todos", label: "Todos" },
  { value: "pendente", label: "Pendentes" },
  { value: "aprovado", label: "Aprovados" },
  { value: "rejeitado", label: "Rejeitados" },
];

const statusBadge = (status: string) => {
  switch (status) {
    case "pendente":
      return <Badge variant="outline" className="bg-yellow-500/10 text-yellow-500 border-yellow-500/30"><Clock className="h-3 w-3 mr-1" />Pendente</Badge>;
    case "aprovado":
      return <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/30"><CheckCircle2 className="h-3 w-3 mr-1" />Aprovado</Badge>;
    case "rejeitado":
      return <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/30"><XCircle className="h-3 w-3 mr-1" />Rejeitado</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
};

function formatarTelefone(tel: string) {
  const nums = tel.replace(/\D/g, "");
  if (nums.length === 11)
    return `(${nums.slice(0, 2)}) ${nums.slice(2, 7)}-${nums.slice(7)}`;
  if (nums.length === 10)
    return `(${nums.slice(0, 2)}) ${nums.slice(2, 6)}-${nums.slice(6)}`;
  return tel;
}

function formatarData(iso: string | null) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Solicitacoes() {
  const [filtroStatus, setFiltroStatus] = useState("todos");
  const [detalhe, setDetalhe] = useState<Solicitacao | null>(null);
  const [modalCriar, setModalCriar] = useState<Solicitacao | null>(null);
  const [modalRejeitar, setModalRejeitar] = useState<Solicitacao | null>(null);
  const [motivoRejeicao, setMotivoRejeicao] = useState("");
  const [enderecoCriar, setEnderecoCriar] = useState("");
  const [planoCriar, setPlanoCriar] = useState("Básico");

  const statusParam = filtroStatus === "todos" ? undefined : filtroStatus;
  const { data, isLoading } = useSolicitacoes(statusParam);
  const atualizarMut = useAtualizarSolicitacao();
  const criarMut = useCriarRestauranteDeSolicitacao();

  const solicitacoes: Solicitacao[] = data?.solicitacoes || [];
  const totalPendentes: number = data?.total_pendentes || 0;

  const handleRejeitar = () => {
    if (!modalRejeitar) return;
    atualizarMut.mutate(
      { id: modalRejeitar.id, payload: { status: "rejeitado", motivo: motivoRejeicao || undefined } },
      {
        onSuccess: () => {
          toast.success("Solicitação rejeitada");
          setModalRejeitar(null);
          setMotivoRejeicao("");
        },
        onError: (err: any) => {
          toast.error(err.response?.data?.detail || "Erro ao rejeitar");
        },
      }
    );
  };

  const handleCriarRestaurante = () => {
    if (!modalCriar) return;
    criarMut.mutate(
      {
        id: modalCriar.id,
        payload: {
          endereco_completo: enderecoCriar || `${modalCriar.cidade || ""}, ${modalCriar.estado || ""}`.trim().replace(/^,\s*|,\s*$/g, "") || "A definir",
          plano: planoCriar,
          valor_plano: planoCriar === "Básico" ? 169.90 : planoCriar === "Essencial" ? 279.90 : planoCriar === "Avançado" ? 329.90 : 527.00,
          limite_motoboys: planoCriar === "Básico" ? 2 : planoCriar === "Essencial" ? 5 : planoCriar === "Avançado" ? 10 : 999,
          criar_site: true,
          tipo_restaurante: modalCriar.tipo_restaurante || "geral",
          enviar_email: true,
          iniciar_trial: true,
        },
      },
      {
        onSuccess: (res: any) => {
          toast.success(
            `Restaurante criado! Código: ${res.restaurante?.codigo_acesso || "?"} | Senha: ${res.restaurante?.senha_padrao || "?"}`,
            { duration: 10000 }
          );
          setModalCriar(null);
          setEnderecoCriar("");
          setPlanoCriar("Básico");
        },
        onError: (err: any) => {
          toast.error(err.response?.data?.detail || "Erro ao criar restaurante");
        },
      }
    );
  };

  return (
    <SuperAdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-[var(--sa-text-primary)] flex items-center gap-2">
              <ClipboardList className="h-6 w-6" />
              Solicitações de Cadastro
            </h1>
            <p className="text-sm text-[var(--sa-text-muted)]">
              Gerencie solicitações de novos restaurantes
            </p>
          </div>
          {totalPendentes > 0 && (
            <Badge className="bg-yellow-500/20 text-yellow-500 border-yellow-500/30 text-base px-3 py-1">
              {totalPendentes} pendente{totalPendentes > 1 ? "s" : ""}
            </Badge>
          )}
        </div>

        {/* Filtros */}
        <div className="flex gap-3 flex-wrap">
          {STATUS_OPTIONS.map((opt) => (
            <Button
              key={opt.value}
              variant={filtroStatus === opt.value ? "default" : "outline"}
              size="sm"
              onClick={() => setFiltroStatus(opt.value)}
              className={filtroStatus === opt.value ? "bg-[var(--sa-accent)]" : "border-[var(--sa-border)] text-[var(--sa-text-muted)]"}
            >
              {opt.label}
            </Button>
          ))}
        </div>

        {/* Tabela */}
        {isLoading ? (
          <div className="flex justify-center py-12"><Spinner /></div>
        ) : solicitacoes.length === 0 ? (
          <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
            <CardContent className="py-12 text-center text-[var(--sa-text-muted)]">
              Nenhuma solicitação {filtroStatus !== "todos" ? `com status "${filtroStatus}"` : "encontrada"}.
            </CardContent>
          </Card>
        ) : (
          <Card className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
            <Table>
              <TableHeader>
                <TableRow className="border-[var(--sa-border)]">
                  <TableHead className="text-[var(--sa-text-muted)]">Restaurante</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Responsável</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Contato</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Cidade</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Data</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Status</TableHead>
                  <TableHead className="text-[var(--sa-text-muted)]">Ações</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {solicitacoes.map((sol) => (
                  <TableRow key={sol.id} className="border-[var(--sa-border)] hover:bg-[var(--sa-bg-hover)]">
                    <TableCell className="text-[var(--sa-text-primary)] font-medium">
                      {sol.nome_fantasia}
                      <div className="text-xs text-[var(--sa-text-muted)]">{sol.tipo_restaurante}</div>
                    </TableCell>
                    <TableCell className="text-[var(--sa-text-secondary)]">{sol.nome_responsavel}</TableCell>
                    <TableCell className="text-[var(--sa-text-secondary)]">
                      <div>{sol.email}</div>
                      <div className="text-xs text-[var(--sa-text-muted)]">{formatarTelefone(sol.telefone)}</div>
                    </TableCell>
                    <TableCell className="text-[var(--sa-text-secondary)]">
                      {sol.cidade ? `${sol.cidade}${sol.estado ? `/${sol.estado}` : ""}` : "-"}
                    </TableCell>
                    <TableCell className="text-[var(--sa-text-muted)] text-sm">{formatarData(sol.criado_em)}</TableCell>
                    <TableCell>{statusBadge(sol.status)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setDetalhe(sol)}
                          className="h-8 w-8 text-[var(--sa-text-muted)] hover:text-[var(--sa-text-primary)]"
                          title="Ver detalhes"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        {sol.status === "pendente" && (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => {
                                setModalCriar(sol);
                                setEnderecoCriar("");
                                setPlanoCriar("Básico");
                              }}
                              className="h-8 w-8 text-green-500 hover:text-green-400 hover:bg-green-500/10"
                              title="Criar restaurante"
                            >
                              <UserPlus className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => {
                                setModalRejeitar(sol);
                                setMotivoRejeicao("");
                              }}
                              className="h-8 w-8 text-red-500 hover:text-red-400 hover:bg-red-500/10"
                              title="Rejeitar"
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {sol.restaurante_id && (
                          <Badge variant="outline" className="text-xs bg-green-500/10 text-green-500 border-green-500/30">
                            <Store className="h-3 w-3 mr-1" />
                            #{sol.restaurante_id}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        )}
      </div>

      {/* ── Modal Detalhes ── */}
      <Dialog open={!!detalhe} onOpenChange={() => setDetalhe(null)}>
        <DialogContent className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)] text-[var(--sa-text-primary)] max-w-lg">
          <DialogHeader>
            <DialogTitle>Detalhes da Solicitação</DialogTitle>
          </DialogHeader>
          {detalhe && (
            <div className="space-y-3 text-sm">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-[var(--sa-text-muted)]">Restaurante</span>
                  <p className="font-medium">{detalhe.nome_fantasia}</p>
                </div>
                <div>
                  <span className="text-[var(--sa-text-muted)]">Responsável</span>
                  <p className="font-medium">{detalhe.nome_responsavel}</p>
                </div>
                <div>
                  <span className="text-[var(--sa-text-muted)]">Email</span>
                  <p>{detalhe.email}</p>
                </div>
                <div>
                  <span className="text-[var(--sa-text-muted)]">Telefone</span>
                  <p>{formatarTelefone(detalhe.telefone)}</p>
                </div>
                {detalhe.cnpj && (
                  <div>
                    <span className="text-[var(--sa-text-muted)]">CNPJ</span>
                    <p>{detalhe.cnpj}</p>
                  </div>
                )}
                <div>
                  <span className="text-[var(--sa-text-muted)]">Cidade/Estado</span>
                  <p>{detalhe.cidade || "-"}{detalhe.estado ? `/${detalhe.estado}` : ""}</p>
                </div>
                <div>
                  <span className="text-[var(--sa-text-muted)]">Tipo</span>
                  <p>{detalhe.tipo_restaurante}</p>
                </div>
                <div>
                  <span className="text-[var(--sa-text-muted)]">Status</span>
                  <div className="mt-0.5">{statusBadge(detalhe.status)}</div>
                </div>
              </div>
              {detalhe.mensagem && (
                <div>
                  <span className="text-[var(--sa-text-muted)]">Mensagem</span>
                  <p className="mt-1 p-2 bg-[var(--sa-bg-hover)] rounded text-[var(--sa-text-secondary)]">{detalhe.mensagem}</p>
                </div>
              )}
              {detalhe.motivo_rejeicao && (
                <div>
                  <span className="text-red-400">Motivo da rejeição</span>
                  <p className="mt-1 p-2 bg-red-500/5 rounded text-red-400">{detalhe.motivo_rejeicao}</p>
                </div>
              )}
              <div className="flex gap-4 text-xs text-[var(--sa-text-muted)]">
                <span>Criado: {formatarData(detalhe.criado_em)}</span>
                {detalhe.ip_origem && <span>IP: {detalhe.ip_origem}</span>}
              </div>
            </div>
          )}
          <DialogFooter>
            {detalhe?.status === "pendente" && (
              <div className="flex gap-2 w-full">
                <Button
                  onClick={() => {
                    setDetalhe(null);
                    setModalCriar(detalhe);
                    setEnderecoCriar("");
                    setPlanoCriar("Básico");
                  }}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  Criar Restaurante
                </Button>
                <Button
                  variant="outline"
                  onClick={() => {
                    setDetalhe(null);
                    setModalRejeitar(detalhe);
                    setMotivoRejeicao("");
                  }}
                  className="border-red-500/30 text-red-500 hover:bg-red-500/10"
                >
                  Rejeitar
                </Button>
              </div>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Modal Criar Restaurante ── */}
      <Dialog open={!!modalCriar} onOpenChange={() => setModalCriar(null)}>
        <DialogContent className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)] text-[var(--sa-text-primary)] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserPlus className="h-5 w-5 text-green-500" />
              Criar Restaurante
            </DialogTitle>
          </DialogHeader>
          {modalCriar && (
            <div className="space-y-4">
              <div className="p-3 bg-[var(--sa-bg-hover)] rounded-lg space-y-1 text-sm">
                <p><strong>{modalCriar.nome_fantasia}</strong></p>
                <p className="text-[var(--sa-text-muted)]">{modalCriar.nome_responsavel} — {modalCriar.email}</p>
                <p className="text-[var(--sa-text-muted)]">{formatarTelefone(modalCriar.telefone)}{modalCriar.cidade ? ` — ${modalCriar.cidade}/${modalCriar.estado || ""}` : ""}</p>
              </div>

              <div>
                <Label className="text-[var(--sa-text-muted)]">Endereço completo</Label>
                <Input
                  value={enderecoCriar}
                  onChange={(e) => setEnderecoCriar(e.target.value)}
                  placeholder={`${modalCriar.cidade || "Cidade"}, ${modalCriar.estado || "UF"}`}
                  className="bg-[var(--sa-bg-base)] border-[var(--sa-border)] text-[var(--sa-text-primary)] mt-1"
                />
                <p className="text-xs text-[var(--sa-text-muted)] mt-1">Deixe vazio para usar cidade/estado da solicitação</p>
              </div>

              <div>
                <Label className="text-[var(--sa-text-muted)]">Plano (trial 15 dias)</Label>
                <Select value={planoCriar} onValueChange={setPlanoCriar}>
                  <SelectTrigger className="bg-[var(--sa-bg-base)] border-[var(--sa-border)] text-[var(--sa-text-primary)] mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)]">
                    <SelectItem value="Básico" className="text-[var(--sa-text-primary)]">Básico — R$169,90</SelectItem>
                    <SelectItem value="Essencial" className="text-[var(--sa-text-primary)]">Essencial — R$279,90</SelectItem>
                    <SelectItem value="Avançado" className="text-[var(--sa-text-primary)]">Avançado — R$329,90</SelectItem>
                    <SelectItem value="Premium" className="text-[var(--sa-text-primary)]">Premium — R$527,00</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center gap-2 p-2 bg-green-500/5 rounded text-xs text-green-400">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span>Trial 15 dias + email boas-vindas + site automático</span>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalCriar(null)} className="border-[var(--sa-border)] text-[var(--sa-text-muted)]">
              Cancelar
            </Button>
            <Button
              onClick={handleCriarRestaurante}
              disabled={criarMut.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {criarMut.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Criando...</>
              ) : (
                <><Store className="h-4 w-4 mr-2" />Criar Restaurante</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Modal Rejeitar ── */}
      <Dialog open={!!modalRejeitar} onOpenChange={() => setModalRejeitar(null)}>
        <DialogContent className="bg-[var(--sa-bg-surface)] border-[var(--sa-border)] text-[var(--sa-text-primary)] max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-500">
              <XCircle className="h-5 w-5" />
              Rejeitar Solicitação
            </DialogTitle>
          </DialogHeader>
          {modalRejeitar && (
            <div className="space-y-4">
              <p className="text-sm text-[var(--sa-text-muted)]">
                Rejeitar a solicitação de <strong className="text-[var(--sa-text-primary)]">{modalRejeitar.nome_fantasia}</strong>?
              </p>
              <div>
                <Label className="text-[var(--sa-text-muted)]">Motivo (opcional)</Label>
                <Textarea
                  value={motivoRejeicao}
                  onChange={(e) => setMotivoRejeicao(e.target.value)}
                  placeholder="Ex: Dados incompletos, restaurante já cadastrado..."
                  rows={3}
                  className="bg-[var(--sa-bg-base)] border-[var(--sa-border)] text-[var(--sa-text-primary)] mt-1 resize-none"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setModalRejeitar(null)} className="border-[var(--sa-border)] text-[var(--sa-text-muted)]">
              Cancelar
            </Button>
            <Button
              onClick={handleRejeitar}
              disabled={atualizarMut.isPending}
              className="bg-red-600 hover:bg-red-700"
            >
              {atualizarMut.isPending ? (
                <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Rejeitando...</>
              ) : (
                "Rejeitar"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </SuperAdminLayout>
  );
}
