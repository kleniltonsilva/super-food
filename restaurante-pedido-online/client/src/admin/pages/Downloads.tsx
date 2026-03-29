import { useState, useEffect } from "react";
import AdminLayout from "@/admin/components/AdminLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Printer,
  MonitorSmartphone,
  Download,
  CheckCircle2,
  Monitor,
  HelpCircle,
  Loader2,
} from "lucide-react";

interface DownloadItem {
  id: string;
  nome: string;
  versao: string;
  url: string;
  tamanho: string;
  disponivel: boolean;
}

export default function Downloads() {
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/public/downloads")
      .then((r) => r.json())
      .then((data) => {
        setDownloads(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const printerAgent = downloads.find((d) => d.id === "printer_agent");
  const bridgeAgent = downloads.find((d) => d.id === "bridge_agent");

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Downloads</h1>
          <p className="text-sm text-[var(--text-muted)]">Baixe os sistemas para seu computador</p>
        </div>

        {/* Cards de download */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Card 1 — Impressora de Pedidos */}
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/20">
                    <Printer className="h-6 w-6 text-blue-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-[var(--text-primary)]">
                      Impressora de Pedidos
                    </CardTitle>
                    <p className="text-sm text-[var(--text-muted)]">Printer Agent</p>
                  </div>
                </div>
                <Badge variant="outline" className="border-blue-500/30 bg-blue-500/10 text-blue-400">
                  <Monitor className="mr-1 h-3 w-3" />
                  Windows
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-[var(--text-secondary)]">
                Imprime automaticamente os pedidos na sua impressora térmica assim que entram no
                sistema. Sem precisar abrir o painel.
              </p>

              {/* Funcionalidades */}
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Funcionalidades
                </p>
                <ul className="space-y-1.5 text-sm text-[var(--text-secondary)]">
                  {[
                    "Impressão automática via WebSocket (tempo real)",
                    "Formato ESC/POS para impressoras térmicas",
                    "Fila de impressão com retentativa",
                    "Reconexão automática ao servidor",
                  ].map((feat) => (
                    <li key={feat} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-400" />
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Requisitos */}
              <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
                <p className="text-xs font-semibold text-[var(--text-muted)]">Requisitos</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  Windows 10 ou superior + impressora térmica USB ou rede (58mm ou 80mm)
                </p>
              </div>

              {/* Botão download */}
              {loading ? (
                <Button disabled className="w-full">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Carregando...
                </Button>
              ) : printerAgent?.disponivel ? (
                <a href={printerAgent.url} download>
                  <Button className="w-full bg-blue-600 hover:bg-blue-700">
                    <Download className="mr-2 h-4 w-4" />
                    Baixar v{printerAgent.versao}
                    <span className="ml-2 text-xs opacity-70">({printerAgent.tamanho})</span>
                  </Button>
                </a>
              ) : (
                <Button disabled className="w-full">
                  Em breve
                </Button>
              )}

              {/* Guia de instalação */}
              <Accordion type="single" collapsible>
                <AccordionItem value="guia" className="border-[var(--border-subtle)]">
                  <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                    Guia de instalação
                  </AccordionTrigger>
                  <AccordionContent>
                    <ol className="space-y-2 text-sm text-[var(--text-secondary)]">
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-400">
                          1
                        </span>
                        Baixe o arquivo e execute como administrador
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-400">
                          2
                        </span>
                        Faça login com o código do seu restaurante e senha
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-400">
                          3
                        </span>
                        Selecione a impressora térmica na lista
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-blue-500/20 text-xs font-bold text-blue-400">
                          4
                        </span>
                        Pronto! Os pedidos serão impressos automaticamente
                      </li>
                    </ol>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </CardContent>
          </Card>

          {/* Card 2 — Bridge Impressora */}
          <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/20">
                    <MonitorSmartphone className="h-6 w-6 text-amber-400" />
                  </div>
                  <div>
                    <CardTitle className="text-lg text-[var(--text-primary)]">
                      Bridge Impressora
                    </CardTitle>
                    <p className="text-sm text-[var(--text-muted)]">Bridge Agent</p>
                  </div>
                </div>
                <Badge variant="outline" className="border-amber-500/30 bg-amber-500/10 text-amber-400">
                  <Monitor className="mr-1 h-3 w-3" />
                  Windows
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-[var(--text-secondary)]">
                Intercepta pedidos do iFood, Rappi e outras plataformas e centraliza tudo no seu
                painel Derekh Food.
              </p>

              {/* Funcionalidades */}
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                  Funcionalidades
                </p>
                <ul className="space-y-1.5 text-sm text-[var(--text-secondary)]">
                  {[
                    "Interceptação automática do spooler de impressão",
                    "IA que aprende os padrões de cada plataforma",
                    "14 plataformas suportadas (iFood, Rappi, 99Food...)",
                    "Criação automática de pedidos no painel",
                  ].map((feat) => (
                    <li key={feat} className="flex items-start gap-2">
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-400" />
                      {feat}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Requisitos */}
              <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
                <p className="text-xs font-semibold text-[var(--text-muted)]">Requisitos</p>
                <p className="mt-1 text-sm text-[var(--text-secondary)]">
                  Windows 10 ou superior + impressora das plataformas (iFood, Rappi, etc.) configurada
                </p>
              </div>

              {/* Botão download */}
              {loading ? (
                <Button disabled className="w-full">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Carregando...
                </Button>
              ) : bridgeAgent?.disponivel ? (
                <a href={bridgeAgent.url} download>
                  <Button className="w-full bg-amber-600 hover:bg-amber-700">
                    <Download className="mr-2 h-4 w-4" />
                    Baixar v{bridgeAgent.versao}
                    <span className="ml-2 text-xs opacity-70">({bridgeAgent.tamanho})</span>
                  </Button>
                </a>
              ) : (
                <Button disabled className="w-full">
                  Em breve
                </Button>
              )}

              {/* Guia de instalação */}
              <Accordion type="single" collapsible>
                <AccordionItem value="guia" className="border-[var(--border-subtle)]">
                  <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                    Guia de instalação
                  </AccordionTrigger>
                  <AccordionContent>
                    <ol className="space-y-2 text-sm text-[var(--text-secondary)]">
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400">
                          1
                        </span>
                        Baixe o arquivo e execute como administrador
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400">
                          2
                        </span>
                        Faça login com o código do seu restaurante e senha
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400">
                          3
                        </span>
                        Selecione as impressoras das plataformas que deseja interceptar
                      </li>
                      <li className="flex gap-2">
                        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-amber-500/20 text-xs font-bold text-amber-400">
                          4
                        </span>
                        Os pedidos serão capturados automaticamente e enviados ao seu painel
                      </li>
                    </ol>
                  </AccordionContent>
                </AccordionItem>
              </Accordion>
            </CardContent>
          </Card>
        </div>

        {/* FAQ */}
        <Card className="border-[var(--border-subtle)] bg-[var(--bg-card)]">
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5 text-[var(--text-muted)]" />
              <CardTitle className="text-base text-[var(--text-primary)]">
                Perguntas frequentes
              </CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="q1" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  Funciona no Mac ou Linux?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  No momento, os dois programas funcionam apenas no Windows (10 ou superior). Estamos
                  avaliando suporte para outras plataformas no futuro.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q2" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  Preciso dos dois programas?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  Depende da sua operação. A <strong>Impressora de Pedidos</strong> serve para
                  imprimir automaticamente os pedidos que entram pelo Derekh Food. O{" "}
                  <strong>Bridge Impressora</strong> é para quem também usa iFood, Rappi ou outras
                  plataformas e quer centralizar tudo num só lugar.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q3" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  Como atualizar para uma nova versão?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  Basta baixar a nova versão e substituir o arquivo antigo. Suas configurações
                  (login, impressoras) são salvas automaticamente e serão mantidas.
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
