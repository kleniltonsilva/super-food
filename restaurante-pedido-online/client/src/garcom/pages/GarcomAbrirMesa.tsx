import { useState } from "react";
import { useLocation, useParams } from "wouter";
import { useAbrirMesa } from "@/garcom/hooks/useGarcomQueries";
import { sndClick } from "@/garcom/hooks/useGarcomWebSocket";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ArrowLeft, Minus, Plus, Users } from "lucide-react";
import { toast } from "sonner";

const TAGS = ["Aniversario", "VIP", "Familia", "Casal", "Empresarial", "Amigos"];

export default function GarcomAbrirMesa() {
  const params = useParams<{ mesaId: string }>();
  const mesaId = parseInt(params.mesaId || "0");
  const [, navigate] = useLocation();
  const abrirMesa = useAbrirMesa();

  const [qtdPessoas, setQtdPessoas] = useState(2);
  const [alergia, setAlergia] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [notas, setNotas] = useState("");

  function toggleTag(tag: string) {
    setTags((prev) => prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag]);
  }

  async function handleAbrir() {
    sndClick();
    try {
      await abrirMesa.mutateAsync({
        mesaId,
        qtd_pessoas: qtdPessoas,
        alergia: alergia || undefined,
        tags: tags.length > 0 ? tags : undefined,
        notas: notas || undefined,
      });
      toast.success(`Mesa ${mesaId} aberta!`);
      navigate("/");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Erro ao abrir mesa");
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0806] text-white">
      {/* Header */}
      <header className="flex items-center gap-3 border-b border-white/5 px-4 py-3">
        <Button variant="ghost" size="icon-sm" onClick={() => navigate("/")} className="text-gray-400">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-lg font-semibold" style={{ fontFamily: "'Outfit', sans-serif" }}>
          Abrir Mesa {mesaId}
        </h1>
      </header>

      <div className="p-4 space-y-6 max-w-md mx-auto">
        {/* Quantidade de pessoas */}
        <div className="space-y-2">
          <Label className="text-gray-300">
            <Users className="inline h-4 w-4 mr-1" /> Pessoas
          </Label>
          <div className="flex items-center gap-4">
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => setQtdPessoas(Math.max(1, qtdPessoas - 1))}
              className="border-white/10 text-white hover:bg-white/5"
            >
              <Minus className="h-4 w-4" />
            </Button>
            <span className="text-3xl font-bold font-mono w-12 text-center">{qtdPessoas}</span>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => setQtdPessoas(Math.min(50, qtdPessoas + 1))}
              className="border-white/10 text-white hover:bg-white/5"
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Alergia */}
        <div className="space-y-2">
          <Label className="text-gray-300">Alergias (opcional)</Label>
          <Input
            value={alergia}
            onChange={(e) => setAlergia(e.target.value)}
            placeholder="Ex: amendoim, glúten, lactose"
            className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500"
          />
        </div>

        {/* Tags */}
        <div className="space-y-2">
          <Label className="text-gray-300">Tags (opcional)</Label>
          <div className="flex flex-wrap gap-2">
            {TAGS.map((tag) => (
              <button
                key={tag}
                onClick={() => toggleTag(tag)}
                className={`rounded-full px-3 py-1 text-sm transition-all ${
                  tags.includes(tag)
                    ? "bg-amber-500 text-gray-950 font-medium"
                    : "bg-white/[0.03] border border-white/10 text-gray-400 hover:border-amber-500/30"
                }`}
              >
                {tag}
              </button>
            ))}
          </div>
        </div>

        {/* Notas */}
        <div className="space-y-2">
          <Label className="text-gray-300">Notas (opcional)</Label>
          <Input
            value={notas}
            onChange={(e) => setNotas(e.target.value)}
            placeholder="Observações sobre a mesa"
            className="bg-white/[0.03] border-white/10 text-white placeholder:text-gray-500"
          />
        </div>

        {/* Botão */}
        <Button
          onClick={handleAbrir}
          disabled={abrirMesa.isPending}
          className="w-full bg-amber-500 hover:bg-amber-600 text-gray-950 font-semibold py-6 text-lg"
        >
          {abrirMesa.isPending ? "Abrindo..." : `Abrir Mesa ${mesaId}`}
        </Button>
      </div>
    </div>
  );
}
