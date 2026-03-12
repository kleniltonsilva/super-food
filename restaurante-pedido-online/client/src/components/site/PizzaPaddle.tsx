/**
 * PizzaPaddle.tsx — Visual da pá de madeira com pizza segmentada.
 *
 * Renderiza uma tábua de madeira circular com a pizza dividida em segmentos
 * conforme o número de sabores selecionados. Cada segmento mostra a foto
 * do sabor usando clip-path CSS. Slots vazios mostram "+Sabor".
 *
 * Melhorias: pizzaSize 82%, sombras realistas, borda dourada 4px, animação crossfade.
 */

import { useMemo } from "react";

interface SaborSelecionado {
  id: number;
  nome: string;
  imagem_url: string | null;
}

interface PizzaPaddleProps {
  maxSabores: number;
  saboresSelecionados: SaborSelecionado[];
  tamanhoLabel?: string;
  bordaLabel?: string;
  size?: number;
}

function getClipPath(index: number, total: number): string {
  if (total === 1) return "circle(50% at 50% 50%)";
  if (total === 2) {
    return index === 0
      ? "polygon(50% 0%, 0% 0%, 0% 100%, 50% 100%)"
      : "polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)";
  }
  if (total === 3) {
    const segments = [
      "polygon(50% 50%, 50% 0%, 100% 0%, 100% 75%, 50% 50%)",
      "polygon(50% 50%, 100% 75%, 50% 100%, 0% 100%, 0% 75%)",
      "polygon(50% 50%, 0% 75%, 0% 0%, 50% 0%)",
    ];
    return segments[index] || "";
  }
  // 4 sabores: quadrantes
  const quads = [
    "polygon(50% 50%, 50% 0%, 0% 0%, 0% 50%)",
    "polygon(50% 50%, 50% 0%, 100% 0%, 100% 50%)",
    "polygon(50% 50%, 100% 50%, 100% 100%, 50% 100%)",
    "polygon(50% 50%, 0% 50%, 0% 100%, 50% 100%)",
  ];
  return quads[index] || "";
}

function getDividerLines(total: number): Array<{ x1: string; y1: string; x2: string; y2: string }> {
  if (total <= 1) return [];
  if (total === 2) return [{ x1: "50%", y1: "0%", x2: "50%", y2: "100%" }];
  if (total === 3) {
    return [
      { x1: "50%", y1: "50%", x2: "50%", y2: "0%" },
      { x1: "50%", y1: "50%", x2: "100%", y2: "75%" },
      { x1: "50%", y1: "50%", x2: "0%", y2: "75%" },
    ];
  }
  return [
    { x1: "0%", y1: "50%", x2: "100%", y2: "50%" },
    { x1: "50%", y1: "0%", x2: "50%", y2: "100%" },
  ];
}

const PIZZA_COLORS = [
  "linear-gradient(135deg, #e8a54b 0%, #d4943a 50%, #c48330 100%)",
  "linear-gradient(135deg, #d4943a 0%, #c48330 50%, #b37225 100%)",
  "linear-gradient(135deg, #c48330 0%, #b37225 50%, #a26120 100%)",
  "linear-gradient(135deg, #b37225 0%, #a26120 50%, #915015 100%)",
];

const PIZZA_EMOJIS = ["🍕", "🧀", "🍖", "🌿"];

export default function PizzaPaddle({
  maxSabores,
  saboresSelecionados,
  tamanhoLabel,
  bordaLabel,
  size = 280,
}: PizzaPaddleProps) {
  const slots = useMemo(() => {
    const result: Array<SaborSelecionado | null> = [];
    for (let i = 0; i < maxSabores; i++) {
      result.push(saboresSelecionados[i] || null);
    }
    return result;
  }, [maxSabores, saboresSelecionados]);

  const dividers = useMemo(() => getDividerLines(maxSabores), [maxSabores]);
  const pizzaSize = size * 0.82;

  return (
    <div className="pizza-paddle" style={{ width: size, margin: "0 auto" }}>
      {/* Tábua de madeira */}
      <div className="pizza-paddle-board" style={{ width: size, height: size }}>
        <img
          src="/themes/pizzaria/wood-board.png"
          alt="Tábua"
          className="pizza-paddle-board-img"
          style={{ width: size, height: size }}
        />

        {/* Pizza circle */}
        <div
          className="pizza-circle"
          style={{
            width: pizzaSize,
            height: pizzaSize,
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
          }}
        >
          {/* Segmentos */}
          {slots.map((sabor, i) => {
            const clipPath = getClipPath(i, maxSabores);
            const hasImage = sabor?.imagem_url;

            return (
              <div
                key={sabor?.id ?? `empty-${i}`}
                className={`pizza-segment ${sabor ? "pizza-segment--filled" : "pizza-segment--empty"}`}
                style={{ clipPath }}
              >
                {hasImage ? (
                  <img
                    src={sabor!.imagem_url!}
                    alt={sabor!.nome}
                    className="pizza-segment-img"
                  />
                ) : sabor ? (
                  <div className="pizza-segment-fallback" style={{ background: PIZZA_COLORS[i % 4] }}>
                    <span className="text-2xl">{PIZZA_EMOJIS[i % 4]}</span>
                    <span className="pizza-segment-name">{sabor.nome}</span>
                  </div>
                ) : (
                  <div className="pizza-segment-empty">
                    <span className="pizza-segment-plus">+</span>
                    <span className="pizza-segment-add-label">Sabor</span>
                  </div>
                )}
              </div>
            );
          })}

          {/* Linhas divisórias */}
          {dividers.length > 0 && (
            <svg className="pizza-dividers" viewBox="0 0 100 100" preserveAspectRatio="none">
              {dividers.map((line, i) => (
                <line
                  key={i}
                  x1={line.x1}
                  y1={line.y1}
                  x2={line.x2}
                  y2={line.y2}
                  stroke="#8B6914"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                />
              ))}
            </svg>
          )}
        </div>
      </div>

      {/* Labels abaixo */}
      {(tamanhoLabel || bordaLabel) && (
        <div className="pizza-paddle-labels">
          {tamanhoLabel && <span className="pizza-paddle-label-size">{tamanhoLabel}</span>}
          {tamanhoLabel && bordaLabel && <span className="pizza-paddle-label-sep"> - </span>}
          {bordaLabel && <span className="pizza-paddle-label-borda">Borda {bordaLabel}</span>}
        </div>
      )}
    </div>
  );
}
