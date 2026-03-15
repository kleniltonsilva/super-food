/**
 * Home.tsx — Página principal do site cliente.
 *
 * Layout temático adaptável por tipo de restaurante usando themeConfig.
 * Componentes extraídos:
 * - RestauranteHeader (TopBar + Header sticky + busca + carrinho)
 * - HeroBanner (banner/hero com overlay ou gradiente)
 * - CategoryNav (nav categorias com scroll horizontal)
 * - ComboSection (cards de combos)
 * - ProductCard (cards de produto temáticos)
 * - FooterSection (footer 3 colunas temático)
 * - FAB carrinho mobile
 */

import { ShoppingCart } from "lucide-react";
import { useState, useMemo, useEffect, useCallback } from "react";
import { useCategorias, useTodosProdutos, useCombos, useCarrinho } from "@/hooks/useQueries";
import { useRestaurante, useRestauranteTheme } from "@/contexts/RestauranteContext";

import RestauranteHeader from "@/components/site/RestauranteHeader";
import HeroBanner from "@/components/site/HeroBanner";
import CategoryNav from "@/components/site/CategoryNav";
import ComboSection from "@/components/site/ComboSection";
import ProductCard from "@/components/site/ProductCard";
import ProductCarousel from "@/components/site/ProductCarousel";
import FooterSection from "@/components/site/FooterSection";
import CartSidebar from "@/components/site/CartSidebar";
import PizzaBuilder from "@/components/site/PizzaBuilder";
import AgeVerification, { useAgeVerification } from "@/components/site/AgeVerification";

interface Variacao {
  id: number;
  tipo_variacao: string;
  nome: string;
  preco_adicional: number;
  max_sabores?: number;
}

interface Produto {
  id: number;
  nome: string;
  descricao: string | null;
  preco: number;
  preco_promocional: number | null;
  imagem_url: string | null;
  destaque: boolean;
  promocao: boolean;
  categoria_id: number;
  eh_pizza?: boolean;
  variacoes: Variacao[];
}

interface Categoria {
  id: number;
  nome: string;
  icone: string | null;
  ordem_exibicao: number;
}

export default function Home() {
  const { siteInfo, loading: siteLoading, error: siteError } = useRestaurante();
  const theme = useRestauranteTheme();
  const [activeSection, setActiveSection] = useState<number | null>(null);
  const [busca, setBusca] = useState("");
  const [cartOpen, setCartOpen] = useState(false);
  const [pizzaBuilderId, setPizzaBuilderId] = useState<number | null>(null);
  const { needsVerification, confirmAge } = useAgeVerification(siteInfo?.tipo_restaurante || "");

  // React Query
  const { data: categorias = [], isLoading: loadingCat } = useCategorias();
  const { data: todosProdutos = [], isLoading: loadingProd } = useTodosProdutos();
  const { data: combos = [] } = useCombos();
  const { data: carrinho } = useCarrinho();

  // Contagem itens carrinho
  const cartCount = useMemo(() => {
    const itens = carrinho?.itens_json || carrinho?.itens || [];
    return itens.reduce((sum: number, i: any) => sum + (i.quantidade || 1), 0);
  }, [carrinho]);

  // Filtrar produtos pela busca
  const produtosFiltrados = useMemo(() => {
    if (!busca.trim()) return todosProdutos;
    const termo = busca.trim().toLowerCase();
    return todosProdutos.filter((p: Produto) =>
      p.nome.toLowerCase().includes(termo) ||
      (p.descricao && p.descricao.toLowerCase().includes(termo))
    );
  }, [todosProdutos, busca]);

  // Agrupar produtos por categoria_id
  const produtosPorCategoria = useMemo(() => {
    const map = new Map<number, Produto[]>();
    produtosFiltrados.forEach((p: Produto) => {
      const list = map.get(p.categoria_id) || [];
      list.push(p);
      map.set(p.categoria_id, list);
    });
    return map;
  }, [produtosFiltrados]);

  // Contagem de produtos por categoria (para CategoryNav)
  const produtoCounts = useMemo(() => {
    const map = new Map<number, number>();
    produtosPorCategoria.forEach((prods, catId) => {
      map.set(catId, prods.length);
    });
    return map;
  }, [produtosPorCategoria]);

  // Emoji baseado na categoria do produto
  function getEmoji(produto: Produto): string {
    const cat = categorias.find((c: Categoria) => c.id === produto.categoria_id);
    if (!cat) return "\u{1F37D}\uFE0F";
    const nome = cat.nome.toLowerCase();
    if (nome.includes("pizza") && nome.includes("doce")) return "\u{1F370}";
    if (nome.includes("pizza")) return "\u{1F355}";
    if (nome.includes("bebid")) return "\u{1F964}";
    if (nome.includes("sobremes")) return "\u{1F368}";
    if (nome.includes("hambur") || nome.includes("lanch")) return "\u{1F354}";
    return cat.icone || "\u{1F37D}\uFE0F";
  }

  // Scroll suave para seção
  const scrollToSection = useCallback((catId: number) => {
    setActiveSection(catId);
    const el = document.getElementById(`cat-${catId}`);
    if (el) {
      const offset = 140;
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: "smooth" });
    }
    const navBtn = document.querySelector(`[data-cat-id="${catId}"]`);
    if (navBtn) {
      navBtn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }
  }, []);

  // IntersectionObserver para auto-highlight da categoria ativa
  useEffect(() => {
    if (loadingProd || categorias.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const id = parseInt(entry.target.id.replace("cat-", ""));
            if (!isNaN(id)) {
              setActiveSection(id);
              const navBtn = document.querySelector(`[data-cat-id="${id}"]`);
              if (navBtn) {
                navBtn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
              }
            }
          }
        }
      },
      { rootMargin: "-20% 0px -60% 0px", threshold: 0 }
    );

    categorias.forEach((cat: Categoria) => {
      const el = document.getElementById(`cat-${cat.id}`);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [loadingProd, categorias]);

  // Loading state
  if (siteLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: theme.colors.bodyBg }}>
        <div className="text-center">
          <div className="text-5xl mb-4 animate-pulse-subtle">{theme.label.charAt(0)}</div>
          <p style={{ color: theme.colors.textMuted }}>Carregando...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (siteError) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: theme.colors.bodyBg }}>
        <div className="text-center">
          <div className="text-5xl mb-4">{"\u{1F615}"}</div>
          <p style={{ color: theme.colors.textMuted }}>{siteError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: theme.colors.bodyBg }}>

      {/* ═══════════ Verificação de Idade (Bebidas) ═══════════ */}
      {needsVerification && <AgeVerification onConfirm={confirmAge} />}

      {/* ═══════════ Header Temático ═══════════ */}
      <RestauranteHeader
        cartCount={cartCount}
        busca={busca}
        onBuscaChange={setBusca}
      />

      {/* ═══════════ Nav Categorias ═══════════ */}
      <CategoryNav
        categorias={categorias}
        loading={loadingCat}
        activeSection={activeSection}
        produtoCounts={produtoCounts}
        onCategoryClick={scrollToSection}
      />

      {/* ═══════════ Hero Banner ═══════════ */}
      <HeroBanner />

      {/* Status do restaurante */}
      {siteInfo && !siteInfo.status_aberto && (
        <div
          className="text-center py-2.5 text-sm font-semibold"
          style={{
            background: "rgba(234, 179, 8, 0.1)",
            borderBottom: "1px solid rgba(234, 179, 8, 0.2)",
            color: theme.isDark ? "#FACC15" : "#B45309",
          }}
        >
          Estamos fechados no momento. Horário: {siteInfo.horario_abertura} - {siteInfo.horario_fechamento}
        </div>
      )}

      {/* Pedidos online desativados */}
      {siteInfo && !siteInfo.pedidos_online_ativos && (
        <div className="text-center py-2.5 text-sm font-semibold" style={{ background: "rgba(245, 158, 11, 0.15)", borderBottom: "1px solid rgba(245, 158, 11, 0.3)", color: theme.isDark ? "#FBBF24" : "#92400E" }}>
          Pedidos online temporariamente indisponíveis{siteInfo.controle_pedidos_motivo ? ` — ${siteInfo.controle_pedidos_motivo}` : ""}
        </div>
      )}

      {/* Entregas desativadas */}
      {siteInfo && siteInfo.pedidos_online_ativos && !siteInfo.entregas_ativas && (
        <div className="text-center py-2.5 text-sm font-semibold" style={{ background: "rgba(59, 130, 246, 0.1)", borderBottom: "1px solid rgba(59, 130, 246, 0.2)", color: theme.isDark ? "#60A5FA" : "#1E40AF" }}>
          Entregas temporariamente indisponíveis. Apenas retirada no balcão.
        </div>
      )}

      {/* ═══════════ Main Content + CartSidebar ═══════════ */}
      <div className="lg:grid lg:grid-cols-[1fr_340px]">
        {/* ── Conteúdo principal ── */}
        <main className="container py-6 px-4 md:py-8 lg:max-w-none">

          {/* ── Combos e Ofertas ── */}
          <ComboSection combos={combos} />

          {/* ── Skeleton loading ── */}
          {loadingProd && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
                <div
                  key={i}
                  className="overflow-hidden"
                  style={{
                    background: theme.colors.cardBg,
                    border: `1px solid ${theme.colors.cardBorder}`,
                    borderRadius: theme.cardRadius,
                  }}
                >
                  <div
                    className="aspect-square animate-pulse"
                    style={{ background: theme.isDark ? "rgba(255,255,255,0.04)" : "#e8e8e8" }}
                  />
                  <div className="p-3 space-y-2">
                    <div
                      className="h-4 rounded w-2/3 animate-pulse"
                      style={{ background: theme.isDark ? "rgba(255,255,255,0.06)" : "#e0e0e0" }}
                    />
                    <div
                      className="h-3 rounded w-full animate-pulse"
                      style={{ background: theme.isDark ? "rgba(255,255,255,0.04)" : "#e8e8e8" }}
                    />
                    <div
                      className="h-5 rounded w-1/3 animate-pulse"
                      style={{ background: theme.isDark ? "rgba(255,255,255,0.06)" : "#e0e0e0" }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* ── Categorias como Seções ── */}
          {!loadingProd && categorias.map((cat: Categoria) => {
            const produtos = produtosPorCategoria.get(cat.id);
            if (!produtos || produtos.length === 0) return null;

            return (
              <section key={cat.id} id={`cat-${cat.id}`} className="mb-10 animate-fade-in-up">
                {/* Header da categoria */}
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-1 h-7 rounded-full" style={{ background: theme.colors.primary }} />
                  {cat.icone && <span className="text-2xl">{cat.icone}</span>}
                  <h3
                    className="text-lg font-bold"
                    style={{
                      color: theme.colors.textPrimary,
                      fontFamily: theme.fonts.special || theme.fonts.heading,
                    }}
                  >
                    {cat.nome.replace(/^[^\w\s]+\s*/, "")}
                  </h3>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full"
                    style={{
                      background: theme.isDark ? "rgba(255,255,255,0.06)" : "#f0f0f0",
                      color: theme.colors.textMuted,
                    }}
                  >
                    {produtos.length} {produtos.length === 1 ? "item" : "itens"}
                  </span>
                </div>

                {/* Grid ou Carousel de produtos */}
                {produtos.length > 6 ? (
                  <ProductCarousel
                    produtos={produtos}
                    getEmoji={getEmoji}
                    onPizzaBuilderOpen={setPizzaBuilderId}
                  />
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-3 gap-4">
                    {produtos.map((produto: Produto) => (
                      <ProductCard
                        key={produto.id}
                        produto={produto}
                        emoji={getEmoji(produto)}
                        onPizzaBuilderOpen={setPizzaBuilderId}
                      />
                    ))}
                  </div>
                )}
              </section>
            );
          })}

          {/* Nenhum produto */}
          {!loadingProd && todosProdutos.length === 0 && (
            <p className="text-center py-12" style={{ color: theme.colors.textMuted }}>
              Nenhum produto disponível no cardápio.
            </p>
          )}
        </main>

        {/* ── CartSidebar desktop ── */}
        <CartSidebar open={cartOpen} onOpenChange={setCartOpen} />
      </div>

      {/* ═══════════ Footer Temático ═══════════ */}
      <FooterSection />

      {/* ═══════════ WhatsApp FAB ═══════════ */}
      {siteInfo?.whatsapp_ativo && siteInfo.whatsapp_numero && (
        <a
          href={`https://wa.me/${siteInfo.whatsapp_numero.replace(/\D/g, "")}?text=${encodeURIComponent(siteInfo.whatsapp_mensagem_padrao || "Olá!")}`}
          target="_blank"
          rel="noopener noreferrer"
          className="fixed z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-transform"
          style={{ bottom: "6rem", right: "1.5rem" }}
        >
          <img src="/btn_whatsapp.png" alt="WhatsApp" className="w-14 h-14" />
        </a>
      )}

      {/* ═══════════ FAB Carrinho (mobile) ═══════════ */}
      <button
        className="lg:hidden fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center text-white fab-pulse btn-press"
        style={{ background: theme.colors.primary }}
        onClick={() => setCartOpen(true)}
      >
        <ShoppingCart className="w-6 h-6" />
        {cartCount > 0 && (
          <span
            className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-white text-[10px] font-bold flex items-center justify-center"
            style={{ color: theme.colors.primary }}
          >
            {cartCount}
          </span>
        )}
      </button>

      {/* ═══════════ Pizza Builder Modal ═══════════ */}
      {pizzaBuilderId && (
        <PizzaBuilder
          produtoId={pizzaBuilderId}
          onClose={() => setPizzaBuilderId(null)}
        />
      )}
    </div>
  );
}
