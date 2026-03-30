import { useState, useEffect, useMemo } from "react";
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
  Smartphone,
  MapPin,
  Zap,
  Shield,
  Route,
  Bell,
  Fuel,
  Users,
  Play,
  Square,
  QrCode,
  ExternalLink,
  Copy,
  Check,
} from "lucide-react";
import { toast } from "sonner";

interface DownloadItem {
  id: string;
  nome: string;
  descricao?: string;
  versao: string;
  url: string;
  tamanho: string;
  disponivel: boolean;
  plataforma?: string;
}

function StepNumber({ n, color = "green" }: { n: number; color?: "green" | "blue" | "amber" }) {
  const colors = {
    green: "bg-green-500/20 text-green-400",
    blue: "bg-blue-500/20 text-blue-400",
    amber: "bg-amber-500/20 text-amber-400",
  };
  return (
    <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${colors[color]} text-xs font-bold`}>
      {n}
    </span>
  );
}

/** Gera QR Code SVG usando API pública */
function QRCodeImage({ url, size = 200 }: { url: string; size?: number }) {
  const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(url)}&bgcolor=0a0a0a&color=22c55e&format=svg`;
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="rounded-2xl border-2 border-green-500/30 bg-black/50 p-3">
        <img
          src={qrUrl}
          alt="QR Code para download do app"
          width={size}
          height={size}
          className="rounded-xl"
        />
      </div>
      <p className="text-center text-xs text-[var(--text-muted)]">
        Aponte a câmera do celular para baixar
      </p>
    </div>
  );
}

export default function Downloads() {
  const [downloads, setDownloads] = useState<DownloadItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    fetch("/api/public/downloads")
      .then((r) => r.json())
      .then((data) => {
        setDownloads(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const motoboyApp = downloads.find((d) => d.id === "motoboy_app");
  const printerAgent = downloads.find((d) => d.id === "printer_agent");
  const bridgeAgent = downloads.find((d) => d.id === "bridge_agent");

  // URL da página exclusiva para entregadores
  const entregadorPageUrl = useMemo(() => {
    const base = window.location.origin;
    return `${base}/entregador/download`;
  }, []);

  // URL de download direto do APK
  const apkDownloadUrl = useMemo(() => {
    if (motoboyApp?.url) {
      return `${window.location.origin}${motoboyApp.url}`;
    }
    return `${window.location.origin}/static/uploads/downloads/DerekhFood-Entregador.apk`;
  }, [motoboyApp]);

  function copyLink(url: string) {
    navigator.clipboard.writeText(url).then(() => {
      setCopied(true);
      toast.success("Link copiado!");
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <AdminLayout>
      <div className="space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Downloads</h1>
          <p className="text-sm text-[var(--text-muted)]">
            Apps e programas para sua operação de delivery
          </p>
        </div>

        {/* ========== SEÇÃO DESTAQUE — APP ENTREGADOR ========== */}
        <div className="overflow-hidden rounded-2xl border-2 border-green-500/20 bg-gradient-to-br from-green-950/40 via-[var(--bg-card)] to-emerald-950/30">
          {/* Banner header */}
          <div className="border-b border-green-500/20 bg-green-500/5 px-6 py-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-green-500/20">
                <Smartphone className="h-6 w-6 text-green-400" />
              </div>
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-xl font-bold text-[var(--text-primary)]">
                    App Derekh Entregador
                  </h2>
                  <Badge className="border-green-500/30 bg-green-500/10 text-green-400">
                    <Smartphone className="mr-1 h-3 w-3" />
                    Android
                  </Badge>
                  {motoboyApp && (
                    <Badge variant="outline" className="border-green-500/30 text-green-400">
                      v{motoboyApp.versao}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-[var(--text-muted)]">
                  App nativo para seus entregadores com GPS em tempo real e inteligência artificial
                </p>
              </div>
            </div>
          </div>

          <div className="p-6">
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Coluna esquerda — Recursos + Instruções */}
              <div className="space-y-6">
                {/* Recursos do app */}
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-green-400/70">
                    Por que usar o app nativo?
                  </p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[
                      { icon: MapPin, text: "GPS em tempo real, mesmo com tela desligada", highlight: true },
                      { icon: Route, text: "IA Derekh Food cria rotas otimizadas automaticamente" },
                      { icon: Fuel, text: "Economia de combustível com rotas inteligentes" },
                      { icon: Users, text: "Despacho justo entre entregadores" },
                      { icon: Bell, text: "Notificações instantâneas de novos pedidos" },
                      { icon: Zap, text: "Aceite pedidos em 1 toque, sem atrasos" },
                      { icon: Shield, text: "GPS background real com foreground service" },
                      { icon: Play, text: "Atualizações automáticas sem Play Store" },
                    ].map((feat) => (
                      <div
                        key={feat.text}
                        className={`flex items-start gap-2.5 rounded-lg p-2 ${feat.highlight ? "bg-green-500/10" : ""}`}
                      >
                        <feat.icon className="mt-0.5 h-4 w-4 shrink-0 text-green-400" />
                        <span className="text-sm text-[var(--text-secondary)]">{feat.text}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Como funciona o app */}
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-green-400/70">
                    Como funciona na prática
                  </p>
                  <div className="space-y-3 rounded-xl border border-green-500/10 bg-green-500/5 p-4">
                    <div className="flex gap-3">
                      <StepNumber n={1} />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Abrir o app</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          O entregador abre o app e faz login com o código do restaurante, usuário e senha. O GPS é ativado automaticamente.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <StepNumber n={2} />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Ficar disponível</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          Ao ficar online, o entregador aparece no mapa do painel. A IA analisa localização de todos os entregadores para despachar pedidos de forma justa e eficiente.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <StepNumber n={3} />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Receber pedido</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          O app notifica com som e vibração. O entregador vê endereço, itens e valor. Aceita com 1 toque.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <StepNumber n={4} />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Iniciar entrega</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          Toca em "Iniciar Entrega" e a rota é aberta no GPS do celular (Google Maps ou Waze). O GPS continua rastreando em tempo real.
                        </p>
                      </div>
                    </div>
                    <div className="flex gap-3">
                      <StepNumber n={5} />
                      <div>
                        <p className="text-sm font-medium text-[var(--text-primary)]">Finalizar entrega</p>
                        <p className="text-xs text-[var(--text-muted)]">
                          Chegou no destino? Toca em "Finalizar" e confirma. O restaurante é notificado e o entregador já fica disponível para o próximo pedido.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Coluna direita — QR Code + Download + Link */}
              <div className="flex flex-col items-center gap-6">
                {/* QR Code */}
                <QRCodeImage url={entregadorPageUrl} size={180} />

                {/* Botão download direto */}
                {loading ? (
                  <Button disabled className="w-full max-w-xs">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Carregando...
                  </Button>
                ) : motoboyApp?.disponivel ? (
                  <a href={motoboyApp.url} download className="w-full max-w-xs">
                    <Button className="w-full bg-green-600 text-base hover:bg-green-700">
                      <Download className="mr-2 h-5 w-5" />
                      Baixar APK v{motoboyApp.versao}
                      {motoboyApp.tamanho && (
                        <span className="ml-2 text-xs opacity-70">({motoboyApp.tamanho})</span>
                      )}
                    </Button>
                  </a>
                ) : (
                  <Button disabled className="w-full max-w-xs">
                    <Download className="mr-2 h-4 w-4" />
                    APK em breve
                  </Button>
                )}

                {/* Link para página exclusiva do entregador */}
                <div className="w-full max-w-xs space-y-2">
                  <p className="text-center text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
                    Página exclusiva para entregadores
                  </p>
                  <div className="flex items-center gap-2 rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-2">
                    <code className="flex-1 truncate text-xs text-green-400">{entregadorPageUrl}</code>
                    <button
                      onClick={() => copyLink(entregadorPageUrl)}
                      className="shrink-0 rounded-md p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]"
                    >
                      {copied ? <Check className="h-4 w-4 text-green-400" /> : <Copy className="h-4 w-4" />}
                    </button>
                    <a
                      href="/entregador/download"
                      target="_blank"
                      className="shrink-0 rounded-md p-1.5 text-[var(--text-muted)] transition-colors hover:bg-[var(--bg-card)] hover:text-[var(--text-primary)]"
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </div>
                  <p className="text-center text-xs text-[var(--text-muted)]">
                    Envie este link para seus entregadores. A página tem todas as instruções.
                  </p>
                </div>

                {/* Mini-card instrução Android */}
                <div className="w-full max-w-xs rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
                  <div className="flex items-start gap-2">
                    <Shield className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                    <div className="space-y-1.5">
                      <p className="text-sm font-medium text-amber-300">
                        Instalação no Android
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        O entregador precisará permitir a instalação de apps de fontes externas
                        na primeira vez. O Android pede essa confirmação por segurança.
                      </p>
                      <p className="text-xs text-[var(--text-muted)]">
                        <strong className="text-amber-400">Caminho:</strong> Configurações → Segurança → Fontes desconhecidas → Permitir navegador
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ========== SEÇÃO PROGRAMAS WINDOWS ========== */}
        <div>
          <h2 className="mb-4 text-lg font-semibold text-[var(--text-primary)]">
            Programas para Computador
          </h2>
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
                <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
                  <p className="text-xs font-semibold text-[var(--text-muted)]">Requisitos</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    Windows 10 ou superior + impressora térmica USB ou rede (58mm ou 80mm)
                  </p>
                </div>
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
                  <Button disabled className="w-full">Em breve</Button>
                )}
                <Accordion type="single" collapsible>
                  <AccordionItem value="guia" className="border-[var(--border-subtle)]">
                    <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                      Guia de instalação
                    </AccordionTrigger>
                    <AccordionContent>
                      <ol className="space-y-2 text-sm text-[var(--text-secondary)]">
                        {[
                          "Baixe o arquivo e execute como administrador",
                          "Faça login com o código do seu restaurante e senha",
                          "Selecione a impressora térmica na lista",
                          "Pronto! Os pedidos serão impressos automaticamente",
                        ].map((step, i) => (
                          <li key={i} className="flex gap-2">
                            <StepNumber n={i + 1} color="blue" />
                            {step}
                          </li>
                        ))}
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
                <div className="rounded-lg border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-3">
                  <p className="text-xs font-semibold text-[var(--text-muted)]">Requisitos</p>
                  <p className="mt-1 text-sm text-[var(--text-secondary)]">
                    Windows 10 ou superior + impressora das plataformas configurada
                  </p>
                </div>
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
                  <Button disabled className="w-full">Em breve</Button>
                )}
                <Accordion type="single" collapsible>
                  <AccordionItem value="guia" className="border-[var(--border-subtle)]">
                    <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                      Guia de instalação
                    </AccordionTrigger>
                    <AccordionContent>
                      <ol className="space-y-2 text-sm text-[var(--text-secondary)]">
                        {[
                          "Baixe o arquivo e execute como administrador",
                          "Faça login com o código do seu restaurante e senha",
                          "Selecione as impressoras das plataformas a interceptar",
                          "Os pedidos serão capturados e enviados ao seu painel",
                        ].map((step, i) => (
                          <li key={i} className="flex gap-2">
                            <StepNumber n={i + 1} color="amber" />
                            {step}
                          </li>
                        ))}
                      </ol>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </CardContent>
            </Card>
          </div>
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
              <AccordionItem value="q0" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  O app do entregador funciona no iPhone?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  No momento o app nativo está disponível apenas para <strong>Android</strong>. Entregadores com iPhone podem usar o app pelo navegador acessando <code>/entregador</code>, porém sem GPS em background.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q1" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  O entregador precisa pagar algo?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  Não. O app é <strong>100% gratuito</strong> para os entregadores. Não há cobrança, assinatura ou taxa. O app é parte do seu plano Derekh Food.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q2" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  Como o entregador atualiza o app?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  O app verifica automaticamente se há uma nova versão ao abrir. Se houver, mostra uma tela pedindo para atualizar. Basta tocar em "Atualizar Agora" e o novo APK é baixado automaticamente.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q3" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  O GPS consome muita bateria?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  O app usa um serviço otimizado que envia posição a cada 10 segundos quando em rota e a cada 30 segundos quando parado. O consumo de bateria é similar ao de apps como Waze ou Google Maps durante navegação.
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="q4" className="border-[var(--border-subtle)]">
                <AccordionTrigger className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:no-underline">
                  Programas Windows funcionam no Mac ou Linux?
                </AccordionTrigger>
                <AccordionContent className="text-sm text-[var(--text-muted)]">
                  Não. A Impressora de Pedidos e o Bridge funcionam apenas no Windows 10 ou superior. Estamos avaliando suporte para outras plataformas.
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </AdminLayout>
  );
}
