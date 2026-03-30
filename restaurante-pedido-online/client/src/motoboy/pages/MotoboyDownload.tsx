import { useState, useEffect, useMemo } from "react";
import {
  Smartphone,
  Download,
  MapPin,
  Route,
  Fuel,
  Users,
  Bell,
  Zap,
  Shield,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  Bike,
  Play,
  Square,
  Navigation,
  Star,
} from "lucide-react";

interface AppVersionInfo {
  version: string;
  download_url: string;
  apk_url?: string;
}

function StepBadge({ n }: { n: number }) {
  return (
    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-green-500/20 text-sm font-bold text-green-400">
      {n}
    </span>
  );
}

export default function MotoboyDownload() {
  const [appInfo, setAppInfo] = useState<AppVersionInfo | null>(null);
  const [expandInstall, setExpandInstall] = useState(false);
  const [expandGuide, setExpandGuide] = useState(false);

  useEffect(() => {
    fetch("/api/public/app-version")
      .then((r) => r.json())
      .then((data) => {
        if (data.motoboy_app) {
          setAppInfo(data.motoboy_app);
        }
      })
      .catch(() => {});
  }, []);

  const downloadUrl = useMemo(() => {
    // Usar apk_url (binário direto) para o botão de download na página
    if (appInfo?.apk_url) return appInfo.apk_url;
    return "/static/uploads/downloads/DerekhFood-Entregador.apk";
  }, [appInfo]);

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Hero */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-green-500/10 via-transparent to-transparent" />
        <div className="relative mx-auto max-w-lg px-4 pb-8 pt-12 text-center">
          {/* Logo */}
          <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-2xl bg-gradient-to-br from-green-500 to-emerald-600 shadow-lg shadow-green-500/25">
            <Bike className="h-10 w-10 text-white" />
          </div>

          <h1 className="text-3xl font-bold tracking-tight">
            Derekh <span className="text-green-400">Entregador</span>
          </h1>
          <p className="mt-2 text-base text-gray-400">
            O app oficial para entregadores Derekh Food
          </p>

          {/* Download button */}
          <a href={downloadUrl} download className="mt-6 block">
            <button className="mx-auto flex items-center gap-3 rounded-2xl bg-green-600 px-8 py-4 text-lg font-semibold shadow-lg shadow-green-600/30 transition-all hover:bg-green-500 hover:shadow-green-500/40 active:scale-95">
              <Download className="h-6 w-6" />
              Baixar App
              {appInfo?.version && (
                <span className="rounded-full bg-green-500/30 px-2 py-0.5 text-xs">
                  v{appInfo.version}
                </span>
              )}
            </button>
          </a>

          <p className="mt-3 text-xs text-gray-500">
            Android 8.0+ &middot; Gratuito &middot; Sem Play Store
          </p>
        </div>
      </div>

      {/* Recursos */}
      <div className="mx-auto max-w-lg px-4 py-8">
        <h2 className="mb-4 text-center text-xs font-semibold uppercase tracking-widest text-green-400/70">
          Por que usar o app?
        </h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { icon: MapPin, title: "GPS Tempo Real", desc: "Mesmo com tela desligada" },
            { icon: Route, title: "Rotas com IA", desc: "Otimiza caminho e economia" },
            { icon: Fuel, title: "Economize", desc: "Menos combustível nas rotas" },
            { icon: Users, title: "Despacho Justo", desc: "IA distribui pedidos igualmente" },
            { icon: Bell, title: "Notificações", desc: "Nunca perca um pedido" },
            { icon: Zap, title: "Super Rápido", desc: "Aceite em 1 toque" },
          ].map((feat) => (
            <div
              key={feat.title}
              className="flex items-start gap-3 rounded-xl border border-gray-800 bg-gray-900/50 p-3"
            >
              <feat.icon className="mt-0.5 h-5 w-5 shrink-0 text-green-400" />
              <div>
                <p className="text-sm font-semibold">{feat.title}</p>
                <p className="text-xs text-gray-500">{feat.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Como instalar */}
      <div className="mx-auto max-w-lg px-4 py-6">
        <button
          onClick={() => setExpandInstall(!expandInstall)}
          className="flex w-full items-center justify-between rounded-xl border border-amber-500/20 bg-amber-950/30 p-4"
        >
          <div className="flex items-center gap-3">
            <Shield className="h-5 w-5 text-amber-400" />
            <span className="text-sm font-semibold text-amber-300">
              Como instalar no Android
            </span>
          </div>
          {expandInstall ? (
            <ChevronUp className="h-5 w-5 text-amber-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-amber-400" />
          )}
        </button>

        {expandInstall && (
          <div className="mt-3 space-y-4 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            <div className="flex gap-3">
              <StepBadge n={1} />
              <div>
                <p className="font-medium">Toque em "Baixar App" acima</p>
                <p className="text-sm text-gray-400">
                  O arquivo APK será baixado para seu celular.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <StepBadge n={2} />
              <div>
                <p className="font-medium">Abra o arquivo baixado</p>
                <p className="text-sm text-gray-400">
                  Vá até a pasta Downloads ou toque na notificação de download concluído.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <StepBadge n={3} />
              <div>
                <p className="font-medium">Permitir fontes externas</p>
                <p className="text-sm text-gray-400">
                  Na primeira vez, o Android pedirá permissão. Isso é normal e seguro.
                </p>
                <div className="mt-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                  <p className="text-xs text-amber-300">
                    <strong>Caminho:</strong> Quando aparecer o aviso, toque em{" "}
                    <strong>"Configurações"</strong> → Ative{" "}
                    <strong>"Permitir desta fonte"</strong> → Volte e toque em <strong>"Instalar"</strong>
                  </p>
                </div>
              </div>
            </div>

            <div className="flex gap-3">
              <StepBadge n={4} />
              <div>
                <p className="font-medium">Instalar e abrir</p>
                <p className="text-sm text-gray-400">
                  Toque em "Instalar" e depois "Abrir". O app estará na tela inicial do seu celular.
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <StepBadge n={5} />
              <div>
                <p className="font-medium">Permitir localização</p>
                <p className="text-sm text-gray-400">
                  O app pedirá permissão de GPS. Escolha <strong>"Permitir o tempo todo"</strong> para o GPS funcionar mesmo com o app em segundo plano ou com a tela desligada.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Como usar o app */}
      <div className="mx-auto max-w-lg px-4 py-6">
        <button
          onClick={() => setExpandGuide(!expandGuide)}
          className="flex w-full items-center justify-between rounded-xl border border-green-500/20 bg-green-950/30 p-4"
        >
          <div className="flex items-center gap-3">
            <Play className="h-5 w-5 text-green-400" />
            <span className="text-sm font-semibold text-green-300">
              Como usar o app (passo a passo)
            </span>
          </div>
          {expandGuide ? (
            <ChevronUp className="h-5 w-5 text-green-400" />
          ) : (
            <ChevronDown className="h-5 w-5 text-green-400" />
          )}
        </button>

        {expandGuide && (
          <div className="mt-3 space-y-5 rounded-xl border border-gray-800 bg-gray-900/50 p-5">
            {/* Login */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-green-500/20 px-2 py-0.5 text-xs font-bold text-green-400">
                  LOGIN
                </span>
              </div>
              <div className="space-y-2 text-sm text-gray-300">
                <p>Abra o app e preencha:</p>
                <ul className="space-y-1 pl-4">
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-400" />
                    <span><strong>Código do restaurante</strong> — peça ao seu gerente (8 caracteres, ex: ABC12345)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-400" />
                    <span><strong>Usuário</strong> — seu nome de usuário cadastrado</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-green-400" />
                    <span><strong>Senha</strong> — senha padrão é 123456 (altere depois no perfil)</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Ficar online */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-green-500/20 px-2 py-0.5 text-xs font-bold text-green-400">
                  FICAR DISPONÍVEL
                </span>
              </div>
              <p className="text-sm text-gray-300">
                Após o login, ative seu status para <strong className="text-green-400">Online</strong>. O GPS começa a rastrear sua posição e você aparece no mapa do restaurante. A inteligência artificial da Derekh Food analisa a localização de todos os entregadores para despachar pedidos de forma justa — quem está mais perto e livre recebe primeiro.
              </p>
            </div>

            {/* Receber pedido */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-blue-500/20 px-2 py-0.5 text-xs font-bold text-blue-400">
                  RECEBER PEDIDO
                </span>
              </div>
              <p className="text-sm text-gray-300">
                Quando um pedido for despachado para você, o app <strong>toca um som</strong>, <strong>vibra</strong> e mostra uma <strong>notificação</strong> (mesmo com a tela desligada). Você verá o endereço de entrega, os itens do pedido e o valor. Toque no pedido para ver os detalhes completos.
              </p>
            </div>

            {/* Iniciar entrega */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-amber-500/20 px-2 py-0.5 text-xs font-bold text-amber-400">
                  INICIAR ENTREGA
                </span>
              </div>
              <div className="text-sm text-gray-300">
                <p>
                  Pegou o pedido no restaurante? Toque em <strong>"Iniciar Entrega"</strong>. O app abre a rota no Google Maps ou Waze automaticamente. Durante toda a entrega, seu GPS continua sendo rastreado em tempo real — o restaurante e o cliente acompanham onde você está.
                </p>
                <div className="mt-2 flex items-center gap-2 rounded-lg bg-green-500/10 p-2">
                  <Navigation className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-green-300">
                    A IA otimiza a rota para economizar tempo e combustível
                  </span>
                </div>
              </div>
            </div>

            {/* Finalizar */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-green-500/20 px-2 py-0.5 text-xs font-bold text-green-400">
                  FINALIZAR ENTREGA
                </span>
              </div>
              <p className="text-sm text-gray-300">
                Chegou no destino e entregou? Toque em <strong>"Finalizar Entrega"</strong> e confirme. O restaurante é notificado instantaneamente. Você fica automaticamente disponível para o próximo pedido.
              </p>
            </div>

            {/* Ganhos */}
            <div>
              <div className="mb-2 flex items-center gap-2">
                <span className="rounded-md bg-purple-500/20 px-2 py-0.5 text-xs font-bold text-purple-400">
                  ACOMPANHAR GANHOS
                </span>
              </div>
              <p className="text-sm text-gray-300">
                Na aba <strong>"Ganhos"</strong> você acompanha quanto fez hoje, na semana e no mês. Veja o histórico completo de todas as suas entregas com valores, distâncias e horários.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Botão download fixo no final */}
      <div className="mx-auto max-w-lg px-4 py-8 text-center">
        <a href={downloadUrl} download>
          <button className="mx-auto flex items-center gap-3 rounded-2xl bg-green-600 px-8 py-4 text-lg font-semibold shadow-lg shadow-green-600/30 transition-all hover:bg-green-500 active:scale-95">
            <Download className="h-6 w-6" />
            Baixar App Derekh Entregador
          </button>
        </a>
        <p className="mt-4 text-xs text-gray-600">
          Derekh Food &copy; {new Date().getFullYear()} &middot; Todos os direitos reservados
        </p>
      </div>
    </div>
  );
}
