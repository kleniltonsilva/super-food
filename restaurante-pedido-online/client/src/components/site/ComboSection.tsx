/**
 * ComboSection.tsx — Seção de combos temática com agrupamento por tipo.
 *
 * Agrupa combos em 3 seções:
 * - "Combo do Dia" — destaque com barra de dias da semana
 * - "Combos e Ofertas" — grid padrão
 * - "Kits Festa" — grid com badge "Para X pessoas"
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { adicionarComboAoCarrinho } from "@/lib/apiClient";
import { useRestauranteTheme } from "@/contexts/RestauranteContext";
import { useQueryClient } from "@tanstack/react-query";
import { QUERY_KEYS } from "@/hooks/useQueries";
import { toast } from "sonner";
import ComboDetailModal from "./ComboDetailModal";

interface ComboItem {
  produto_id: number;
  produto_nome: string;
  quantidade: number;
  produto_imagem_url: string | null;
}

interface Combo {
  id: number;
  nome: string;
  descricao: string | null;
  preco_combo: number;
  preco_original: number;
  imagem_url: string | null;
  tipo_combo?: string;
  dia_semana?: number | null;
  quantidade_pessoas?: number | null;
  itens: ComboItem[];
}

interface ComboSectionProps {
  combos: Combo[];
}

const DIAS_CURTOS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

export default function ComboSection({ combos }: ComboSectionProps) {
  const theme = useRestauranteTheme();
  const qc = useQueryClient();
  const [addingCombo, setAddingCombo] = useState<number | null>(null);
  const [selectedCombo, setSelectedCombo] = useState<Combo | null>(null);

  if (combos.length === 0) return null;

  const combosNormais = combos.filter(c => !c.tipo_combo || c.tipo_combo === "padrao");
  const combosDoDia = combos.filter(c => c.tipo_combo === "do_dia");
  const kitsFesta = combos.filter(c => c.tipo_combo === "kit_festa");

  const cardStyle: React.CSSProperties = {
    background: theme.colors.cardBg,
    border: `1px solid ${theme.colors.cardBorder}`,
    borderRadius: theme.cardRadius,
    boxShadow: theme.colors.shadowCard,
  };

  const handleAdd = async (e: React.MouseEvent, comboId: number) => {
    e.stopPropagation();
    setAddingCombo(comboId);
    try {
      await adicionarComboAoCarrinho(comboId);
      qc.invalidateQueries({ queryKey: QUERY_KEYS.carrinho });
      toast.success("Combo adicionado ao carrinho!");
    } catch {
      toast.error("Erro ao adicionar combo");
    } finally {
      setAddingCombo(null);
    }
  };

  function renderComboCard(combo: Combo) {
    const economia = combo.preco_original - combo.preco_combo;
    const pct = combo.preco_original > 0 ? Math.round((economia / combo.preco_original) * 100) : 0;
    return (
      <div
        key={combo.id}
        className="overflow-hidden card-hover group cursor-pointer"
        style={cardStyle}
        onClick={() => setSelectedCombo(combo)}
      >
        <div className="flex flex-row">
          {/* Imagem */}
          <div
            className="w-36 h-36 md:w-44 md:h-44 flex-shrink-0 flex items-center justify-center relative overflow-hidden"
            style={{ background: theme.isDark ? "rgba(255,255,255,0.04)" : "#f0f0f0" }}
          >
            {combo.imagem_url ? (
              <img src={combo.imagem_url} alt={combo.nome} className="w-full h-full object-cover img-zoom" />
            ) : (
              <span className="text-5xl">{"\u{1F381}"}</span>
            )}
            {pct > 0 && (
              <span
                className="absolute top-2 left-2 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider"
                style={{ background: theme.colors.primary }}
              >
                -{pct}%
              </span>
            )}
            {/* Badge Kit Festa */}
            {combo.tipo_combo === "kit_festa" && combo.quantidade_pessoas && (
              <span
                className="absolute bottom-2 left-2 text-white text-[10px] font-bold px-2 py-0.5 rounded-full"
                style={{ background: "#7c3aed" }}
              >
                Para {combo.quantidade_pessoas} pessoas
              </span>
            )}
          </div>
          {/* Info */}
          <div className="flex-1 p-4 flex flex-col justify-between">
            <div>
              <h3
                className="font-bold text-base mb-1"
                style={{
                  color: theme.colors.textPrimary,
                  fontFamily: theme.fonts.special || theme.fonts.heading,
                }}
              >
                {combo.nome}
              </h3>
              {combo.descricao && (
                <p className="text-sm mb-1 line-clamp-2" style={{ color: theme.colors.textMuted }}>
                  {combo.descricao}
                </p>
              )}
              <div className="text-xs mb-2" style={{ color: theme.colors.textMuted }}>
                {combo.itens.map((it, i) => (
                  <span key={i}>{it.quantidade}x {it.produto_nome}{i < combo.itens.length - 1 ? " + " : ""}</span>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex flex-col">
                {combo.preco_original > combo.preco_combo && (
                  <span className="text-xs line-through" style={{ color: theme.colors.textMuted }}>
                    R$ {combo.preco_original.toFixed(2)}
                  </span>
                )}
                <span
                  className="font-extrabold text-lg"
                  style={{
                    color: theme.colors.priceColor,
                    fontFamily: theme.fonts.special || theme.fonts.heading,
                  }}
                >
                  R$ {combo.preco_combo.toFixed(2)}
                </span>
              </div>
              <Button
                size="sm"
                disabled={addingCombo === combo.id}
                className="text-white btn-press"
                onClick={(e) => handleAdd(e, combo.id)}
                style={{
                  background: theme.colors.btnComprar,
                  borderBottom: `3px solid ${theme.colors.btnComprarBorder}`,
                }}
              >
                {addingCombo === combo.id ? "..." : "Adicionar"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  function renderSectionHeader(title: string) {
    return (
      <div className="flex items-center gap-3 mb-5">
        <div className="w-1 h-7 rounded-full" style={{ background: theme.colors.primary }} />
        <h2
          className="text-xl font-bold"
          style={{
            color: theme.colors.textPrimary,
            fontFamily: theme.fonts.special || theme.fonts.heading,
          }}
        >
          {title}
        </h2>
      </div>
    );
  }

  // Barra de dias da semana para combos do dia
  function renderDiasBar() {
    const hoje = new Date().getDay();
    // JS: 0=Dom, 1=Seg... converter para 0=Seg...6=Dom
    const diaAtual = hoje === 0 ? 6 : hoje - 1;
    return (
      <div className="flex gap-1 mb-4 overflow-x-auto">
        {DIAS_CURTOS.map((dia, idx) => (
          <span
            key={idx}
            className="px-3 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all"
            style={{
              background: idx === diaAtual ? theme.colors.primary : theme.isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.05)",
              color: idx === diaAtual ? "#fff" : theme.colors.textMuted,
            }}
          >
            {dia}
          </span>
        ))}
      </div>
    );
  }

  return (
    <>
      {/* Combos do Dia */}
      {combosDoDia.length > 0 && (
        <section className="mb-10 animate-fade-in-up">
          {renderSectionHeader("Combo do Dia")}
          {renderDiasBar()}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {combosDoDia.map(renderComboCard)}
          </div>
        </section>
      )}

      {/* Combos Padrão */}
      {combosNormais.length > 0 && (
        <section className="mb-10 animate-fade-in-up">
          {renderSectionHeader("Combos e Ofertas")}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {combosNormais.map(renderComboCard)}
          </div>
        </section>
      )}

      {/* Kits Festa */}
      {kitsFesta.length > 0 && (
        <section className="mb-10 animate-fade-in-up">
          {renderSectionHeader("Kits Festa")}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {kitsFesta.map(renderComboCard)}
          </div>
        </section>
      )}

      {/* Modal de detalhe do combo */}
      {selectedCombo && (
        <ComboDetailModal
          combo={selectedCombo}
          onClose={() => setSelectedCombo(null)}
        />
      )}
    </>
  );
}
