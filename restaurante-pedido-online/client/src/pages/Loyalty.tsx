/**
 * Loyalty.tsx — Programa de fidelidade.
 *
 * Usa React Query (usePontosFidelidade, usePremiosFidelidade) com staleTime 5-15min.
 * Mutation useResgatarPremio invalida pontos e prêmios automaticamente.
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Gift, Zap } from "lucide-react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { usePontosFidelidade, usePremiosFidelidade, useResgatarPremio } from "@/hooks/useQueries";
import { toast } from "sonner";
import { useState } from "react";

interface PontosData {
  pontos_total: number;
  pontos_disponiveis: number;
}

interface Premio {
  id: number;
  nome: string;
  descricao: string | null;
  tipo_premio: string;
  custo_pontos: number;
  ativo: boolean;
}

export default function Loyalty() {
  const [, navigate] = useLocation();
  const { cliente, isLoggedIn } = useAuth();
  const { siteInfo } = useRestaurante();
  const [redeemedRewards, setRedeemedRewards] = useState<number[]>([]);

  // React Query: cache pontos 5min, prêmios 15min, enabled só quando logado
  const isEnabled = isLoggedIn && !!cliente;
  const { data: pontos = null, isLoading: loadingPontos } = usePontosFidelidade(isEnabled ? cliente?.id : undefined);
  const { data: premios = [], isLoading: loadingPremios } = usePremiosFidelidade(isEnabled);
  const resgatarMutation = useResgatarPremio();
  const loading = loadingPontos || loadingPremios;
  const processing = resgatarMutation.isPending;

  const handleRedeemReward = async (premioId: number) => {
    if (!cliente) return;
    try {
      const result = await resgatarMutation.mutateAsync({ clienteId: cliente.id, premioId });
      if (result.sucesso) {
        setRedeemedRewards(prev => [...prev, premioId]);
        toast.success(result.mensagem);
      } else {
        toast.error(result.mensagem);
      }
    } catch {
      toast.error("Erro ao resgatar prêmio");
    }
  };

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <Card className="p-8 text-center">
            <p className="text-muted-foreground mb-4">
              Faça login para ver seu programa de fidelidade
            </p>
            <Button
              onClick={() => navigate("/login")}
              style={{ background: `var(--cor-primaria, #E31A24)` }}
              className="text-white"
            >
              Fazer Login
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Programa de Fidelidade</h1>

        {/* Card de Pontos */}
        {pontos && (
          <Card className="p-6 mb-8 text-white" style={{ background: `var(--cor-primaria, #E31A24)` }}>
            <div className="grid grid-cols-2 gap-8">
              <div>
                <p className="text-white/70 text-sm mb-1">Pontos Disponíveis</p>
                <p className="text-4xl font-extrabold">{pontos.pontos_disponiveis}</p>
              </div>
              <div>
                <p className="text-white/70 text-sm mb-1">Pontos Totais</p>
                <p className="text-4xl font-extrabold">{pontos.pontos_total}</p>
              </div>
            </div>
          </Card>
        )}

        {/* Como Funciona */}
        <Card className="p-6 mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Como Funciona
          </h2>
          <div className="space-y-3 text-sm">
            <p>A cada R$ 1,00 gasto, você ganha 1 ponto.</p>
            <p>Acumule pontos e troque por prêmios exclusivos!</p>
            <p>Os prêmios são aplicados automaticamente no seu próximo pedido.</p>
          </div>
        </Card>

        {/* Prêmios */}
        <div>
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Gift className="w-6 h-6" />
            Prêmios Disponíveis
          </h2>

          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3].map(i => (
                <Card key={i} className="p-6 animate-pulse">
                  <div className="h-32 bg-muted rounded" />
                </Card>
              ))}
            </div>
          ) : premios.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {premios.map((premio: Premio) => {
                const canRedeem = pontos && pontos.pontos_disponiveis >= premio.custo_pontos && !redeemedRewards.includes(premio.id);
                return (
                  <Card key={premio.id} className="p-6">
                    <h3 className="font-bold text-lg mb-2">{premio.nome}</h3>
                    {premio.descricao && (
                      <p className="text-sm text-muted-foreground mb-3">
                        {premio.descricao}
                      </p>
                    )}

                    <div className="flex items-center justify-between mb-4">
                      <span className="font-extrabold text-lg" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                        {premio.custo_pontos} pts
                      </span>
                      <span className="text-xs bg-muted px-2 py-1 rounded">
                        {premio.tipo_premio === "desconto" ? "Desconto"
                          : premio.tipo_premio === "produto_gratis" ? "Item Grátis"
                          : "Presente"}
                      </span>
                    </div>

                    <Button
                      onClick={() => handleRedeemReward(premio.id)}
                      disabled={!canRedeem || processing}
                      className="w-full text-white"
                      style={{ background: canRedeem ? `var(--cor-primaria, #E31A24)` : undefined }}
                    >
                      {redeemedRewards.includes(premio.id)
                        ? "Resgatado!"
                        : pontos && pontos.pontos_disponiveis < premio.custo_pontos
                        ? "Pontos Insuficientes"
                        : "Resgatar"}
                    </Button>
                  </Card>
                );
              })}
            </div>
          ) : (
            <Card className="p-8 text-center">
              <p className="text-muted-foreground">
                Nenhum prêmio disponível no momento
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
