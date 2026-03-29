import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent } from "@/components/ui/card";
import {
  MessageSquareX,
  Percent,
  BarChart3,
  ClipboardX,
  Globe,
  Bot,
  LayoutDashboard,
  ChefHat,
  Smartphone,
  QrCode,
  LineChart,
  Heart,
  CheckCircle2,
  ArrowRight,
  Loader2,
  Send,
  Utensils,
} from "lucide-react";
import axios from "axios";

const TIPOS_RESTAURANTE = [
  { value: "geral", label: "Restaurante" },
  { value: "pizzaria", label: "Pizzaria" },
  { value: "hamburgueria", label: "Hamburgueria" },
  { value: "acaiteria", label: "Acaiteria" },
  { value: "japonesa", label: "Comida Japonesa" },
  { value: "doceria", label: "Doceria / Confeitaria" },
  { value: "marmitaria", label: "Marmitaria" },
  { value: "padaria", label: "Padaria / Cafeteria" },
];

const ESTADOS = [
  "AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG",
  "PA","PB","PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO",
];

interface FormData {
  nome_fantasia: string;
  nome_responsavel: string;
  email: string;
  telefone: string;
  cidade: string;
  estado: string;
  tipo_restaurante: string;
  mensagem: string;
}

export default function Landing() {
  const formRef = useRef<HTMLDivElement>(null);
  const [formData, setFormData] = useState<FormData>({
    nome_fantasia: "",
    nome_responsavel: "",
    email: "",
    telefone: "",
    cidade: "",
    estado: "",
    tipo_restaurante: "geral",
    mensagem: "",
  });
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(false);
  const [erro, setErro] = useState("");

  const scrollToForm = () => {
    formRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const formatarTelefone = (valor: string) => {
    const nums = valor.replace(/\D/g, "").slice(0, 11);
    if (nums.length <= 2) return nums;
    if (nums.length <= 7) return `(${nums.slice(0, 2)}) ${nums.slice(2)}`;
    if (nums.length <= 10)
      return `(${nums.slice(0, 2)}) ${nums.slice(2, 6)}-${nums.slice(6)}`;
    return `(${nums.slice(0, 2)}) ${nums.slice(2, 7)}-${nums.slice(7)}`;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro("");
    setEnviando(true);

    try {
      await axios.post("/api/public/solicitar-cadastro", {
        ...formData,
        telefone: formData.telefone.replace(/\D/g, ""),
      });
      setSucesso(true);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail ||
        "Erro ao enviar solicitação. Tente novamente.";
      setErro(msg);
    } finally {
      setEnviando(false);
    }
  };

  const updateField = (field: keyof FormData, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* ── Header fixo ── */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-gray-950/80 backdrop-blur-md border-b border-gray-800">
        <div className="max-w-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Utensils className="h-6 w-6 text-orange-500" />
            <span className="text-xl font-bold">
              Derekh <span className="text-orange-500">Food</span>
            </span>
          </div>
          <Button
            onClick={scrollToForm}
            className="bg-orange-600 hover:bg-orange-700 text-white"
          >
            Quero Experimentar
          </Button>
        </div>
      </header>

      {/* ── Seção 1: Hero ── */}
      <section className="relative min-h-screen flex items-center justify-center px-4 pt-16 overflow-hidden">
        {/* Gradiente de fundo */}
        <div className="absolute inset-0 bg-gradient-to-b from-orange-950/20 via-gray-950 to-gray-950" />
        <div className="absolute top-20 left-1/4 w-72 h-72 bg-orange-600/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-orange-600/5 rounded-full blur-3xl" />

        <div className="relative z-10 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 bg-orange-600/10 border border-orange-600/20 rounded-full px-4 py-2 mb-6 text-sm text-orange-400">
            <CheckCircle2 className="h-4 w-4" />
            15 dias grátis — sem compromisso
          </div>
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold leading-tight mb-6">
            Seu restaurante merece{" "}
            <span className="text-orange-500">vender mais</span>
          </h1>
          <p className="text-lg sm:text-xl text-gray-400 mb-8 max-w-2xl mx-auto">
            Sistema completo de delivery que funciona enquanto você cozinha.
            Site próprio, bot WhatsApp, painel de controle e muito mais.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button
              size="lg"
              onClick={scrollToForm}
              className="bg-orange-600 hover:bg-orange-700 text-white text-lg px-8 py-6"
            >
              Quero Experimentar Grátis
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </div>
        </div>
      </section>

      {/* ── Seção 2: Dores ── */}
      <section className="py-20 px-4 bg-gray-900/50">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
            Seu dia a dia é assim?
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Se você se identificou com alguma dessas situações, a Derekh Food
            foi feita pra você.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[
              {
                icon: MessageSquareX,
                title: "Perdendo pedidos pelo WhatsApp?",
                desc: "Clientes mandam mensagem e ninguém responde. Cada mensagem perdida é dinheiro que não entra.",
              },
              {
                icon: Percent,
                title: "Dependendo só do iFood?",
                desc: "Pagando até 27% de comissão em cada pedido. Seu lucro vai embora sem você perceber.",
              },
              {
                icon: BarChart3,
                title: "Sem controle do caixa?",
                desc: "Não sabe quanto entrou hoje, quanto saiu. Fim do mês é sempre uma surpresa.",
              },
              {
                icon: ClipboardX,
                title: "Cardápio desatualizado?",
                desc: "Cliente pede item que acabou. Erro no pedido, reclamação, dor de cabeça.",
              },
            ].map((dor, i) => (
              <Card
                key={i}
                className="bg-gray-800/50 border-gray-700 hover:border-orange-600/50 transition-colors"
              >
                <CardContent className="p-6 flex gap-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-red-500/10 rounded-lg flex items-center justify-center">
                    <dor.icon className="h-6 w-6 text-red-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-white mb-1">
                      {dor.title}
                    </h3>
                    <p className="text-gray-400 text-sm">{dor.desc}</p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* ── Seção 3: Solução (features) ── */}
      <section className="py-20 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl sm:text-4xl font-bold text-center mb-4">
            Tudo que seu restaurante precisa
          </h2>
          <p className="text-gray-400 text-center mb-12 max-w-2xl mx-auto">
            Um único sistema que cuida de todo o seu delivery — do pedido à
            entrega.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Globe,
                title: "Site próprio de delivery",
                desc: "Seu link, sua marca. Sem comissão por pedido. Clientes pedem direto de você.",
              },
              {
                icon: Bot,
                title: "Bot WhatsApp 24h",
                desc: "Atendimento inteligente que faz pedidos, tira dúvidas e nunca perde uma mensagem.",
              },
              {
                icon: LayoutDashboard,
                title: "Painel de controle completo",
                desc: "Pedidos, caixa, motoboys, estoque — tudo em um só lugar, do celular ou computador.",
              },
              {
                icon: ChefHat,
                title: "KDS Cozinha Digital",
                desc: "Tela na cozinha com fila de pedidos. Sem papel, sem confusão, sem erro.",
              },
              {
                icon: Smartphone,
                title: "App Garçom",
                desc: "Atendimento de mesas com comanda digital. Pedidos vão direto pra cozinha.",
              },
              {
                icon: QrCode,
                title: "Pix Online automático",
                desc: "QR Code Pix no checkout. Pagamento confirmado na hora, sem conferência manual.",
              },
              {
                icon: LineChart,
                title: "Relatórios detalhados",
                desc: "Saiba o que vende mais, horários de pico, ticket médio e tendências.",
              },
              {
                icon: Heart,
                title: "Programa de fidelidade",
                desc: "Clientes acumulam pontos e trocam por prêmios. Eles voltam sempre.",
              },
              {
                icon: Send,
                title: "Entregadores rastreados",
                desc: "App para motoboys com GPS. Você e o cliente acompanham a entrega em tempo real.",
              },
            ].map((feature, i) => (
              <div
                key={i}
                className="group p-6 rounded-xl bg-gray-800/30 border border-gray-800 hover:border-orange-600/40 transition-all"
              >
                <div className="w-10 h-10 bg-orange-600/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-orange-600/20 transition-colors">
                  <feature.icon className="h-5 w-5 text-orange-500" />
                </div>
                <h3 className="font-semibold text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-400 text-sm">{feature.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Seção 4: Social Proof ── */}
      <section className="py-16 px-4 bg-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 text-center">
            {[
              { numero: "50+", label: "Restaurantes já usam" },
              { numero: "10.000+", label: "Pedidos processados" },
              { numero: "92%", label: "Dos clientes voltam" },
            ].map((stat, i) => (
              <div key={i}>
                <div className="text-4xl sm:text-5xl font-bold text-orange-500 mb-2">
                  {stat.numero}
                </div>
                <div className="text-gray-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Seção 5: Formulário ── */}
      <section ref={formRef} className="py-20 px-4" id="formulario">
        <div className="max-w-xl mx-auto">
          {sucesso ? (
            <div className="text-center py-12">
              <div className="w-20 h-20 bg-green-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 className="h-10 w-10 text-green-500" />
              </div>
              <h2 className="text-2xl font-bold mb-3">
                Recebemos sua solicitação!
              </h2>
              <p className="text-gray-400 mb-6">
                Entraremos em contato em até 24 horas para liberar seu acesso.
                Fique de olho no seu email!
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  setSucesso(false);
                  setFormData({
                    nome_fantasia: "",
                    nome_responsavel: "",
                    email: "",
                    telefone: "",
                    cidade: "",
                    estado: "",
                    tipo_restaurante: "geral",
                    mensagem: "",
                  });
                }}
                className="border-gray-600 text-gray-300 hover:bg-gray-800"
              >
                Enviar outra solicitação
              </Button>
            </div>
          ) : (
            <>
              <h2 className="text-3xl sm:text-4xl font-bold text-center mb-2">
                Comece agora
              </h2>
              <p className="text-gray-400 text-center mb-8">
                15 dias grátis, sem compromisso. Preencha seus dados e
                liberaremos seu acesso.
              </p>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <Label htmlFor="nome_fantasia" className="text-gray-300">
                    Nome do restaurante *
                  </Label>
                  <Input
                    id="nome_fantasia"
                    required
                    minLength={3}
                    placeholder="Ex: Pizza do João"
                    value={formData.nome_fantasia}
                    onChange={(e) =>
                      updateField("nome_fantasia", e.target.value)
                    }
                    className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1"
                  />
                </div>

                <div>
                  <Label htmlFor="nome_responsavel" className="text-gray-300">
                    Seu nome *
                  </Label>
                  <Input
                    id="nome_responsavel"
                    required
                    minLength={3}
                    placeholder="Nome do responsável"
                    value={formData.nome_responsavel}
                    onChange={(e) =>
                      updateField("nome_responsavel", e.target.value)
                    }
                    className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1"
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="email" className="text-gray-300">
                      Email *
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      required
                      placeholder="contato@restaurante.com"
                      value={formData.email}
                      onChange={(e) => updateField("email", e.target.value)}
                      className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="telefone" className="text-gray-300">
                      Telefone / WhatsApp *
                    </Label>
                    <Input
                      id="telefone"
                      required
                      placeholder="(11) 99999-9999"
                      value={formData.telefone}
                      onChange={(e) =>
                        updateField("telefone", formatarTelefone(e.target.value))
                      }
                      className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="cidade" className="text-gray-300">
                      Cidade
                    </Label>
                    <Input
                      id="cidade"
                      placeholder="São Paulo"
                      value={formData.cidade}
                      onChange={(e) => updateField("cidade", e.target.value)}
                      className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="estado" className="text-gray-300">
                      Estado
                    </Label>
                    <Select
                      value={formData.estado}
                      onValueChange={(v) => updateField("estado", v)}
                    >
                      <SelectTrigger className="bg-gray-800 border-gray-700 text-white mt-1">
                        <SelectValue placeholder="Selecione" />
                      </SelectTrigger>
                      <SelectContent className="bg-gray-800 border-gray-700">
                        {ESTADOS.map((uf) => (
                          <SelectItem
                            key={uf}
                            value={uf}
                            className="text-white hover:bg-gray-700"
                          >
                            {uf}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div>
                  <Label htmlFor="tipo" className="text-gray-300">
                    Tipo de restaurante
                  </Label>
                  <Select
                    value={formData.tipo_restaurante}
                    onValueChange={(v) => updateField("tipo_restaurante", v)}
                  >
                    <SelectTrigger className="bg-gray-800 border-gray-700 text-white mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-gray-800 border-gray-700">
                      {TIPOS_RESTAURANTE.map((t) => (
                        <SelectItem
                          key={t.value}
                          value={t.value}
                          className="text-white hover:bg-gray-700"
                        >
                          {t.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="mensagem" className="text-gray-300">
                    Mensagem (opcional)
                  </Label>
                  <Textarea
                    id="mensagem"
                    rows={3}
                    placeholder="Conte um pouco sobre seu restaurante..."
                    value={formData.mensagem}
                    onChange={(e) => updateField("mensagem", e.target.value)}
                    className="bg-gray-800 border-gray-700 text-white placeholder:text-gray-500 mt-1 resize-none"
                  />
                </div>

                {erro && (
                  <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3 text-red-400 text-sm">
                    {erro}
                  </div>
                )}

                <Button
                  type="submit"
                  disabled={enviando}
                  className="w-full bg-orange-600 hover:bg-orange-700 text-white py-6 text-lg"
                >
                  {enviando ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Enviando...
                    </>
                  ) : (
                    <>
                      Solicitar Acesso
                      <ArrowRight className="ml-2 h-5 w-5" />
                    </>
                  )}
                </Button>

                <p className="text-center text-gray-500 text-xs">
                  Ao solicitar, você concorda em receber comunicações da Derekh
                  Food. Sem spam, prometemos.
                </p>
              </form>
            </>
          )}
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="py-8 px-4 border-t border-gray-800">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-gray-400">
            <Utensils className="h-5 w-5 text-orange-500" />
            <span className="font-semibold text-white">Derekh Food</span>
          </div>
          <p className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Derekh Food. Todos os direitos
            reservados.
          </p>
        </div>
      </footer>
    </div>
  );
}
