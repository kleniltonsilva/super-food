import AdminLayout from "@/admin/components/AdminLayout";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Rocket, Smartphone, Printer, Network, Plug, BookOpen,
  ChevronRight, ExternalLink,
} from "lucide-react";

const BASE_URL = window.location.origin;

function StepList({ steps }: { steps: string[] }) {
  return (
    <ol className="space-y-2 ml-1">
      {steps.map((step, i) => (
        <li key={i} className="flex gap-3 text-sm text-zinc-300">
          <span className="shrink-0 flex h-6 w-6 items-center justify-center rounded-full bg-amber-500/20 text-amber-400 text-xs font-bold">
            {i + 1}
          </span>
          <span className="pt-0.5">{step}</span>
        </li>
      ))}
    </ol>
  );
}

function AppCard({ nome, rota, descricao }: { nome: string; rota: string; descricao: string }) {
  const url = `${BASE_URL}${rota}`;
  return (
    <div className="rounded-lg border border-zinc-700 bg-zinc-800/50 p-4 space-y-2">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-white">{nome}</h4>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-amber-400 hover:text-amber-300 flex items-center gap-1"
        >
          Abrir <ExternalLink className="h-3 w-3" />
        </a>
      </div>
      <p className="text-xs text-zinc-400">{descricao}</p>
      <div className="rounded bg-zinc-900 px-3 py-2 font-mono text-xs text-zinc-300 select-all">
        {url}
      </div>
      <StepList steps={[
        "Abra o Google Chrome no celular",
        `Acesse o endereço: ${url}`,
        "Toque no menu (3 pontos) no canto superior direito",
        'Selecione "Adicionar à tela inicial"',
        "Confirme — o app aparecerá como ícone no celular",
        "Faça login com suas credenciais",
      ]} />
    </div>
  );
}

export default function Onboarding() {
  return (
    <AdminLayout>
      <div className="mx-auto max-w-3xl space-y-6 py-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Guia de Início</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Siga os passos abaixo para configurar seu restaurante no Derekh Food.
          </p>
        </div>

        <Accordion type="multiple" defaultValue={["primeiros-passos"]} className="space-y-3">
          {/* 1. Primeiros Passos */}
          <AccordionItem value="primeiros-passos" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-500/20">
                  <Rocket className="h-5 w-5 text-amber-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Primeiros Passos</p>
                  <p className="text-xs text-zinc-400">Configure o básico do seu restaurante</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5">
              <StepList steps={[
                "Acesse o painel administrativo com o email e senha recebidos",
                "Vá em Configurações e complete os dados do restaurante (logo, horários, taxa de entrega)",
                "Acesse Categorias e crie as categorias do seu cardápio (ex: Pizzas, Bebidas, Sobremesas)",
                "Acesse Produtos e adicione os itens de cada categoria (nome, preço, foto, descrição)",
                "Vá em Bairros e defina as áreas de entrega com os valores de taxa para cada região",
                "Faça um pedido de teste pelo site do cliente para validar todo o fluxo",
              ]} />
            </AccordionContent>
          </AccordionItem>

          {/* 2. Instalar Apps (PWA) */}
          <AccordionItem value="instalar-apps" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/20">
                  <Smartphone className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Instalar Apps no Celular (PWA)</p>
                  <p className="text-xs text-zinc-400">Motoboy, KDS Cozinha e Garçom</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5 space-y-4">
              <p className="text-sm text-zinc-300">
                Os apps funcionam como Progressive Web Apps (PWA). Basta acessar pelo Chrome e adicionar à tela inicial — não precisa baixar na loja.
              </p>

              <AppCard
                nome="App Motoboy"
                rota="/entregador"
                descricao="App para os entregadores aceitarem e acompanharem entregas em tempo real."
              />

              <AppCard
                nome="KDS Cozinha"
                rota="/cozinha"
                descricao="Display de cozinha para acompanhar e gerenciar pedidos em preparo. Antes de usar, crie um cozinheiro no painel (menu Cozinha Digital)."
              />

              <AppCard
                nome="App Garçom"
                rota="/garcom"
                descricao="App para garçons fazerem pedidos de mesa, abrirem e fecharem contas. Antes de usar, crie garçons e mesas no painel (menu Garçons)."
              />
            </AccordionContent>
          </AccordionItem>

          {/* 3. Impressora de Cupons */}
          <AccordionItem value="impressora" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-green-500/20">
                  <Printer className="h-5 w-5 text-green-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Impressora de Cupons</p>
                  <p className="text-xs text-zinc-400">Impressão automática com impressora térmica</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5 space-y-3">
              <div className="rounded-lg bg-zinc-900 p-4 space-y-2">
                <p className="text-sm font-medium text-white">Requisitos:</p>
                <ul className="text-sm text-zinc-300 space-y-1 ml-4 list-disc">
                  <li>Computador com Windows</li>
                  <li>Impressora térmica ESC/POS conectada via USB</li>
                  <li>Driver da impressora instalado</li>
                </ul>
              </div>
              <StepList steps={[
                "Baixe o agente de impressão DerekhFood-Bridge.exe (link disponível em breve)",
                "Execute o instalador e siga as instruções",
                "Na tela de configuração, faça login com suas credenciais do painel",
                "Selecione a impressora térmica na lista de impressoras detectadas",
                "Faça um pedido de teste para verificar se a impressão funciona",
              ]} />
              <p className="text-xs text-zinc-500">O agente roda em segundo plano e imprime automaticamente cada pedido recebido.</p>
            </AccordionContent>
          </AccordionItem>

          {/* 4. Bridge Agent */}
          <AccordionItem value="bridge" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/20">
                  <Network className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Bridge Agent (Interceptar Pedidos iFood/Rappi)</p>
                  <p className="text-xs text-zinc-400">Captura pedidos impressos de outras plataformas</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5 space-y-3">
              <p className="text-sm text-zinc-300">
                O Bridge Agent intercepta pedidos que são impressos por outras plataformas (iFood, Rappi, 99Food) e os importa automaticamente para o Derekh Food. Assim você gerencia tudo em um só lugar.
              </p>
              <div className="rounded-lg bg-zinc-900 p-4 space-y-2">
                <p className="text-sm font-medium text-white">Requisitos:</p>
                <ul className="text-sm text-zinc-300 space-y-1 ml-4 list-disc">
                  <li>Computador com Windows onde as plataformas imprimem</li>
                  <li>Impressora compartilhada (a que recebe pedidos das plataformas)</li>
                </ul>
              </div>
              <StepList steps={[
                "Instale o DerekhFood-Bridge.exe no mesmo computador das plataformas",
                "Configure o Bridge Agent para monitorar a impressora correta",
                "Os pedidos interceptados aparecerão automaticamente no painel em Bridge Impressora",
                "Revise e aprove cada pedido interceptado para integrá-lo ao seu fluxo",
              ]} />
            </AccordionContent>
          </AccordionItem>

          {/* 5. Integrações */}
          <AccordionItem value="integracoes" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-orange-500/20">
                  <Plug className="h-5 w-5 text-orange-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Integrações</p>
                  <p className="text-xs text-zinc-400">iFood, Pix Online, WhatsApp Humanoide</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5 space-y-4">
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <ChevronRight className="h-4 w-4 text-amber-400" /> iFood
                </h4>
                <p className="text-sm text-zinc-300 ml-6">
                  Acesse o menu Integrações no painel e clique em "Conectar iFood". Você será redirecionado para autorizar o acesso. Após conectar, seus pedidos do iFood aparecerão automaticamente no painel.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <ChevronRight className="h-4 w-4 text-amber-400" /> Pix Online
                </h4>
                <p className="text-sm text-zinc-300 ml-6">
                  Acesse o menu Pix no painel e ative sua chave Pix. O sistema irá gerar QR Codes automaticamente para seus clientes pagarem online. Sem taxa para você — apenas R$0,85 por transação cobrada pela Woovi.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <ChevronRight className="h-4 w-4 text-amber-400" /> WhatsApp Humanoide
                </h4>
                <p className="text-sm text-zinc-300 ml-6">
                  Atendimento automatizado por IA no WhatsApp. Disponível como add-on ou incluso no plano Premium. Entre em contato com o suporte para solicitar a ativação.
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* 6. Manual de Uso Básico */}
          <AccordionItem value="manual" className="rounded-xl border border-zinc-700 bg-zinc-800/60 overflow-hidden">
            <AccordionTrigger className="px-5 py-4 hover:no-underline [&[data-state=open]>svg]:rotate-90">
              <div className="flex items-center gap-3 text-left">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-cyan-500/20">
                  <BookOpen className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <p className="font-semibold text-white">Manual de Uso Básico</p>
                  <p className="text-xs text-zinc-400">Guia rápido do dia a dia</p>
                </div>
              </div>
            </AccordionTrigger>
            <AccordionContent className="px-5 pb-5 space-y-4">
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white">Receber e gerenciar pedidos</h4>
                <p className="text-sm text-zinc-300">
                  Pedidos aparecem automaticamente na tela de Pedidos. Você pode aceitar, preparar, despachar e finalizar cada pedido. Se o KDS estiver ativo, a cozinha gerencia o preparo.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white">Despachar para motoboy</h4>
                <p className="text-sm text-zinc-300">
                  Quando o pedido estiver pronto, clique em "Despachar" e selecione um motoboy disponível. O motoboy receberá a notificação no app dele.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white">Gerenciar cardápio</h4>
                <p className="text-sm text-zinc-300">
                  Use os menus Categorias e Produtos para adicionar, editar ou desativar itens. Alterações são refletidas imediatamente no site do cliente.
                </p>
              </div>
              <div className="space-y-2">
                <h4 className="text-sm font-semibold text-white">Relatórios e dashboard</h4>
                <p className="text-sm text-zinc-300">
                  O Dashboard exibe métricas em tempo real (pedidos, faturamento, ticket médio). A página Relatórios oferece análises detalhadas com filtros por período.
                </p>
              </div>
              <div className="mt-4 rounded-lg bg-amber-500/10 border border-amber-500/30 p-4">
                <p className="text-sm text-amber-300">
                  <strong>Precisa de ajuda?</strong> Entre em contato pelo WhatsApp do suporte ou envie um email. Estamos aqui para ajudar!
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </AdminLayout>
  );
}
