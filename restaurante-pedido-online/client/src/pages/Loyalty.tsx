import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Gift, Zap } from "lucide-react";
import { useLocation } from "wouter";
import { trpc } from "@/lib/trpc";
import { toast } from "sonner";
import { useState } from "react";

export default function Loyalty() {
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();
  const [redeemedRewards, setRedeemedRewards] = useState<number[]>([]);

  const pointsQuery = trpc.loyalty.getPoints.useQuery();
  const rewardsQuery = trpc.loyalty.getRewards.useQuery();
  const redeemMutation = trpc.loyalty.redeemReward.useMutation();

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <p className="text-center text-muted-foreground">
            Faça login para ver seu programa de fidelidade
          </p>
        </div>
      </div>
    );
  }

  const handleRedeemReward = async (rewardId: number) => {
    try {
      await redeemMutation.mutateAsync({ rewardId });
      setRedeemedRewards([...redeemedRewards, rewardId]);
      toast.success("Prêmio resgatado com sucesso!");
      pointsQuery.refetch();
    } catch (error: any) {
      toast.error(error.message || "Erro ao resgatar prêmio");
    }
  };

  const points = pointsQuery.data;
  const rewards = rewardsQuery.data || [];

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-8">
        <Button
          variant="ghost"
          onClick={() => navigate("/")}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-3xl font-bold mb-8">Programa de Fidelidade</h1>

        {/* Points Card */}
        {points && (
          <Card className="loyalty-card mb-8">
            <div className="grid grid-cols-2 gap-8">
              <div>
                <p className="loyalty-label">Pontos Disponíveis</p>
                <p className="loyalty-points">{points.availablePoints}</p>
              </div>
              <div>
                <p className="loyalty-label">Pontos Totais</p>
                <p className="loyalty-points">{points.totalPoints}</p>
              </div>
            </div>
          </Card>
        )}

        {/* How it Works */}
        <Card className="checkout-section mb-8">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5" />
            Como Funciona
          </h2>
          <div className="space-y-3 text-sm">
            <p>
              🎯 <strong>Ganhe 1 ponto</strong> para cada real gasto em seus pedidos
            </p>
            <p>
              🏆 <strong>Acumule pontos</strong> e troque por prêmios exclusivos
            </p>
            <p>
              🎁 <strong>Resgate prêmios</strong> diretamente na sua conta
            </p>
          </div>
        </Card>

        {/* Rewards */}
        <div>
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Gift className="w-6 h-6" />
            Prêmios Disponíveis
          </h2>

          {rewardsQuery.isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <Card key={i} className="p-6 animate-pulse">
                  <div className="h-32 bg-muted rounded" />
                </Card>
              ))}
            </div>
          ) : rewards.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {rewards.map((reward) => (
                <Card key={reward.id} className="reward-card">
                  <h3 className="font-bold text-lg mb-2">{reward.name}</h3>
                  {reward.description && (
                    <p className="text-sm text-muted-foreground mb-3">
                      {reward.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between mb-4">
                    <span className="reward-price">
                      {reward.pointsCost} pontos
                    </span>
                    <span className="text-xs bg-muted px-2 py-1 rounded">
                      {reward.rewardType === "discount"
                        ? "Desconto"
                        : reward.rewardType === "free_item"
                        ? "Item Grátis"
                        : "Presente"}
                    </span>
                  </div>

                  <Button
                    onClick={() => handleRedeemReward(reward.id)}
                    disabled={
                      !points ||
                      points.availablePoints < reward.pointsCost ||
                      redeemedRewards.includes(reward.id) ||
                      redeemMutation.isPending
                    }
                    className="w-full bg-accent hover:bg-accent/90 text-white"
                  >
                    {redeemedRewards.includes(reward.id)
                      ? "Resgatado"
                      : points && points.availablePoints < reward.pointsCost
                      ? "Pontos Insuficientes"
                      : "Resgatar"}
                  </Button>
                </Card>
              ))}
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
