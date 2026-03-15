import { useState } from "react";
import { useErrosSentry, useErroDetalheSentry } from "@/superadmin/hooks/useSuperAdminQueries";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Bug, Copy, Check, RefreshCw, ExternalLink, AlertCircle, Server, Monitor, CheckCircle2, XCircle, EyeOff, ListFilter } from "lucide-react";
import { toast } from "sonner";

interface SentryIssue {
  id: string;
  titulo: string;
  culprit: string;
  tipo: string;
  valor: string;
  arquivo: string;
  funcao: string;
  contagem: number;
  usuarios_afetados: number;
  primeira_vez: string;
  ultima_vez: string;
  nivel: string;
  status: string;
  link: string;
}

interface Contadores {
  total: number;
  unresolved: number;
  resolved: number;
  ignored: number;
}

const STATUS_TABS = [
  { value: "todos", label: "Todos", icon: ListFilter, color: "text-foreground" },
  { value: "unresolved", label: "Abertos", icon: XCircle, color: "text-red-500" },
  { value: "resolved", label: "Resolvidos", icon: CheckCircle2, color: "text-green-500" },
  { value: "ignored", label: "Ignorados", icon: EyeOff, color: "text-muted-foreground" },
] as const;

export default function ErrosSentry() {
  const [projeto, setProjeto] = useState("api");
  const [periodo, setPeriodo] = useState("24h");
  const [statusFiltro, setStatusFiltro] = useState("todos");
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  const { data, isLoading, error, refetch } = useErrosSentry(projeto, periodo, statusFiltro);
  const { data: detalhe, isLoading: detalheLoading } = useErroDetalheSentry(selectedIssueId);

  const erros: SentryIssue[] = data?.erros || [];
  const contadores: Contadores = data?.contadores || { total: 0, unresolved: 0, resolved: 0, ignored: 0 };

  function formatDate(dateStr: string | null) {
    if (!dateStr) return "--";
    const d = new Date(dateStr);
    return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" });
  }

  function timeAgo(dateStr: string | null) {
    if (!dateStr) return "";
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "agora";
    if (diffMin < 60) return `${diffMin}min`;
    const diffH = Math.floor(diffMin / 60);
    if (diffH < 24) return `${diffH}h`;
    const diffD = Math.floor(diffH / 24);
    return `${diffD}d`;
  }

  function nivelBadge(nivel: string) {
    switch (nivel) {
      case "fatal": return { variant: "destructive" as const, label: "FATAL" };
      case "error": return { variant: "destructive" as const, label: "ERROR" };
      case "warning": return { variant: "secondary" as const, label: "WARNING" };
      case "info": return { variant: "outline" as const, label: "INFO" };
      default: return { variant: "outline" as const, label: nivel.toUpperCase() };
    }
  }

  function statusBadge(status: string) {
    switch (status) {
      case "resolved": return { className: "bg-green-100 text-green-700 border-green-200", label: "Resolvido" };
      case "ignored": return { className: "bg-gray-100 text-gray-500 border-gray-200", label: "Ignorado" };
      default: return { className: "bg-red-100 text-red-700 border-red-200", label: "Aberto" };
    }
  }

  async function copiarParaClaude() {
    if (!detalhe?.texto_claude) return;
    try {
      await navigator.clipboard.writeText(detalhe.texto_claude);
      setCopiado(true);
      toast.success("Texto copiado para a area de transferencia!");
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      toast.error("Falha ao copiar -- copie manualmente");
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-100 rounded-lg">
            <Bug className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold">Monitoramento de Erros</h1>
            <p className="text-sm text-muted-foreground">Sentry -- logs em tempo real de todo o sistema</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isLoading}>
          <RefreshCw className={`w-4 h-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      {/* Cards de contadores */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {STATUS_TABS.map((tab) => {
          const count = tab.value === "todos" ? contadores.total : contadores[tab.value as keyof Omit<Contadores, "total">] || 0;
          const Icon = tab.icon;
          const isActive = statusFiltro === tab.value;
          return (
            <Card
              key={tab.value}
              className={`cursor-pointer transition-all hover:shadow-md ${isActive ? "ring-2 ring-primary shadow-md" : "hover:bg-muted/50"}`}
              onClick={() => setStatusFiltro(tab.value)}
            >
              <CardContent className="p-4 flex items-center gap-3">
                <Icon className={`w-5 h-5 ${tab.color}`} />
                <div>
                  <p className="text-2xl font-bold">{count}</p>
                  <p className="text-xs text-muted-foreground">{tab.label}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-3">
        <div className="w-44">
          <Select value={projeto} onValueChange={setProjeto}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="api">
                <div className="flex items-center gap-2">
                  <Server className="w-4 h-4" />
                  API (Backend)
                </div>
              </SelectItem>
              <SelectItem value="frontend">
                <div className="flex items-center gap-2">
                  <Monitor className="w-4 h-4" />
                  Frontend (React)
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="w-40">
          <Select value={periodo} onValueChange={setPeriodo}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Ultima hora</SelectItem>
              <SelectItem value="24h">Ultimas 24h</SelectItem>
              <SelectItem value="7d">Ultimos 7 dias</SelectItem>
              <SelectItem value="30d">Ultimos 30 dias</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Estado de erro */}
      {error && (
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-3 text-amber-600">
              <AlertCircle className="w-5 h-5" />
              <div>
                <p className="font-medium">Sentry nao configurado</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Configure SENTRY_AUTH_TOKEN via <code className="bg-muted px-1 rounded">fly secrets set SENTRY_AUTH_TOKEN=...</code>
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      )}

      {/* Lista de erros */}
      {!isLoading && !error && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center justify-between">
              <span>{contadores.total} {contadores.total === 1 ? "erro" : "erros"} no periodo</span>
              <span className="text-xs font-normal text-muted-foreground">
                {projeto === "api" ? "Backend (FastAPI)" : "Frontend (React)"} -- {periodo}
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {erros.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-green-300" />
                <p className="text-lg font-medium">Nenhum erro encontrado</p>
                <p className="text-sm mt-1">O sistema esta funcionando perfeitamente neste periodo.</p>
              </div>
            ) : (
              <div className="divide-y">
                {erros.map((erro) => {
                  const nivel = nivelBadge(erro.nivel);
                  const status = statusBadge(erro.status);
                  return (
                    <div
                      key={erro.id}
                      className="py-3 px-3 hover:bg-muted/50 cursor-pointer rounded-lg transition-colors"
                      onClick={() => setSelectedIssueId(erro.id)}
                    >
                      <div className="flex items-start justify-between gap-4">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                            <Badge variant={nivel.variant} className="text-[10px] px-1.5 py-0">
                              {nivel.label}
                            </Badge>
                            <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${status.className}`}>
                              {status.label}
                            </Badge>
                            <span className="font-medium text-sm truncate">{erro.titulo}</span>
                          </div>
                          <p className="text-xs text-muted-foreground truncate">
                            {erro.culprit || erro.arquivo || "--"}
                          </p>
                          <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                            <span>Primeira: {formatDate(erro.primeira_vez)}</span>
                            <span>Ultima: {timeAgo(erro.ultima_vez)}</span>
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0">
                          <div className="text-lg font-bold">{erro.contagem}x</div>
                          <div className="text-xs text-muted-foreground">
                            {erro.usuarios_afetados > 0 ? `${erro.usuarios_afetados} user${erro.usuarios_afetados > 1 ? "s" : ""}` : ""}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Modal de detalhe */}
      <Dialog open={!!selectedIssueId} onOpenChange={(open) => !open && setSelectedIssueId(null)}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bug className="w-5 h-5 text-red-500" />
              Detalhe do Erro
            </DialogTitle>
          </DialogHeader>

          {detalheLoading && (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          )}

          {detalhe && (
            <div className="space-y-4">
              {/* Info basica */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">Titulo:</span>
                  <p className="font-medium">{detalhe.issue?.titulo}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Projeto:</span>
                  <p className="font-medium">{detalhe.issue?.projeto}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Ocorrencias:</span>
                  <p className="font-medium">{detalhe.issue?.contagem}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Usuarios afetados:</span>
                  <p className="font-medium">{detalhe.issue?.usuarios_afetados}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Primeira vez:</span>
                  <p className="font-medium">{formatDate(detalhe.issue?.primeira_vez)}</p>
                </div>
                <div>
                  <span className="text-muted-foreground">Ultima vez:</span>
                  <p className="font-medium">{formatDate(detalhe.issue?.ultima_vez)}</p>
                </div>
              </div>

              {/* Stack trace */}
              <div>
                <h3 className="font-medium mb-2">Stack Trace</h3>
                <pre className="bg-muted p-4 rounded-lg text-xs overflow-x-auto whitespace-pre-wrap max-h-64">
                  {detalhe.stack_trace || "Stack trace nao disponivel"}
                </pre>
              </div>

              {/* Link Sentry */}
              {detalhe.issue?.link && (
                <a
                  href={detalhe.issue.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-blue-600 hover:underline"
                >
                  <ExternalLink className="w-4 h-4" />
                  Ver no Sentry
                </a>
              )}

              {/* Botao copiar para Claude */}
              <div className="pt-4 border-t">
                <Button
                  onClick={copiarParaClaude}
                  className="w-full"
                  variant={copiado ? "outline" : "default"}
                >
                  {copiado ? (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Copiado!
                    </>
                  ) : (
                    <>
                      <Copy className="w-4 h-4 mr-2" />
                      Copiar para Claude Code
                    </>
                  )}
                </Button>
                <p className="text-xs text-muted-foreground text-center mt-2">
                  Cole o texto copiado diretamente no Claude Code para analise e correcao automatica
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
