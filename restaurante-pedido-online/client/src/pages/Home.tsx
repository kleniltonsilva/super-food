/**
 * Home.tsx — Página principal do site cliente.
 *
 * Layout escuro profissional estilo "Expresso Delivery":
 * - TopBar com saudação + links de login/conta
 * - Header sticky com logo + busca + carrinho
 * - Nav de categorias com scroll suave + IntersectionObserver auto-highlight
 * - Banner/Hero com overlay gradiente
 * - Combos em cards horizontais escuros
 * - Todas as categorias como seções com grid de produtos
 * - Cards escuros com hover lift + zoom imagem + badges
 * - Footer escuro profissional
 * - FAB carrinho mobile com pulse
 */

import { Button } from "@/components/ui/button";
import { ShoppingCart, Menu, X, User, LogOut, ChevronRight, Clock, MapPin, Search } from "lucide-react";
import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { adicionarComboAoCarrinho } from "@/lib/apiClient";
import { useCategorias, useTodosProdutos, useCombos, useCarrinho } from "@/hooks/useQueries";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useAuth } from "@/contexts/AuthContext";
import { Link } from "wouter";

interface Variacao {
  id: number;
  tipo_variacao: string;
  nome: string;
  preco_adicional: number;
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
  variacoes: Variacao[];
}

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
  itens: ComboItem[];
}

interface Categoria {
  id: number;
  nome: string;
  icone: string | null;
  ordem_exibicao: number;
}

export default function Home() {
  const { siteInfo, loading: siteLoading, error: siteError } = useRestaurante();
  const { cliente, isLoggedIn, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [addingCombo, setAddingCombo] = useState<number | null>(null);
  const [activeSection, setActiveSection] = useState<number | null>(null);
  const navRef = useRef<HTMLDivElement>(null);

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

  // Agrupar produtos por categoria_id
  const produtosPorCategoria = useMemo(() => {
    const map = new Map<number, Produto[]>();
    todosProdutos.forEach((p: Produto) => {
      const list = map.get(p.categoria_id) || [];
      list.push(p);
      map.set(p.categoria_id, list);
    });
    return map;
  }, [todosProdutos]);

  const nomeRestaurante = siteInfo?.nome_fantasia || "Restaurante";

  // Emoji dinâmico por tipo de restaurante
  function getEmojiRestaurante(): string {
    const tipo = (siteInfo?.tipo_restaurante || "").toLowerCase();
    if (tipo.includes("pizza")) return "\u{1F355}";
    if (tipo.includes("hambur") || tipo.includes("lanch")) return "\u{1F354}";
    if (tipo.includes("sushi") || tipo.includes("japon")) return "\u{1F363}";
    if (tipo.includes("acai") || tipo.includes("sorvet")) return "\u{1F368}";
    if (tipo.includes("churrasco") || tipo.includes("grill")) return "\u{1F969}";
    if (tipo.includes("padaria") || tipo.includes("cafe")) return "\u2615";
    if (tipo.includes("doce") || tipo.includes("confeit") || tipo.includes("bolo")) return "\u{1F382}";
    if (tipo.includes("salgad")) return "\u{1F95F}";
    if (tipo.includes("bebid")) return "\u{1F964}";
    if (tipo.includes("esfih")) return "\u{1F959}";
    if (tipo.includes("restaurante")) return "\u{1F37D}\uFE0F";
    return "\u{1F37D}\uFE0F";
  }

  // Texto "Sobre" dinâmico
  function getSobreTexto(): string {
    const tipo = (siteInfo?.tipo_restaurante || "").toLowerCase();
    const nome = nomeRestaurante;
    if (tipo.includes("pizza")) return `O ${nome} prepara pizzas artesanais com ingredientes selecionados. Qualidade e sabor em cada fatia.`;
    if (tipo.includes("hambur") || tipo.includes("lanch")) return `O ${nome} oferece os melhores hamb\u00FArgueres e lanches da regi\u00E3o. Carnes selecionadas e p\u00E3o artesanal.`;
    if (tipo.includes("sushi") || tipo.includes("japon")) return `O ${nome} traz o melhor da culin\u00E1ria japonesa. Peixes frescos e preparos tradicionais.`;
    if (tipo.includes("acai") || tipo.includes("sorvet")) return `O ${nome} serve a\u00E7a\u00ED cremoso e sorvetes artesanais. Refresque-se com qualidade.`;
    if (tipo.includes("churrasco")) return `O ${nome} oferece carnes nobres grelhadas na brasa. Tradi\u00E7\u00E3o e sabor em cada corte.`;
    if (tipo.includes("esfih")) return `O ${nome} prepara esfihas artesanais com receita tradicional. Sabor aut\u00EAntico.`;
    return `O ${nome} oferece o melhor em qualidade e sabor. Pe\u00E7a agora e receba no conforto da sua casa.`;
  }

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

  // Preco display considerando variações
  function getPrecoDisplay(produto: Produto): string {
    const tamanhos = produto.variacoes.filter(v => v.tipo_variacao === "tamanho");
    if (tamanhos.length > 0) {
      const precos = tamanhos.map(t => produto.preco + t.preco_adicional);
      const min = Math.min(...precos);
      const max = Math.max(...precos);
      if (min === max) return `R$ ${min.toFixed(2)}`;
      return `R$ ${min.toFixed(2)} ~ R$ ${max.toFixed(2)}`;
    }
    if (produto.promocao && produto.preco_promocional) {
      return `R$ ${produto.preco_promocional.toFixed(2)}`;
    }
    return `R$ ${produto.preco.toFixed(2)}`;
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
    // Scroll nav button into view
    const navBtn = document.querySelector(`[data-cat-id="${catId}"]`);
    if (navBtn) {
      navBtn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
    }
  }, []);

  // IntersectionObserver para auto-highlight da categoria ativa ao scrollar
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

  if (siteLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-pulse-subtle">{getEmojiRestaurante()}</div>
          <p className="text-[var(--text-muted)]">Carregando...</p>
        </div>
      </div>
    );
  }

  if (siteError) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4">{"\u{1F615}"}</div>
          <p className="text-[var(--text-muted)]">{siteError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">

      {/* ═══════════ TopBar ═══════════ */}
      <div className="bg-[var(--bg-surface)] border-b border-[var(--border-subtle)] text-[var(--text-muted)] text-xs">
        <div className="container flex items-center justify-between py-1.5">
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: siteInfo?.status_aberto ? "#22C55E" : "#EF4444" }}
            />
            <span className="text-[var(--text-secondary)]">
              {isLoggedIn
                ? `Ol\u00E1, ${cliente?.nome?.split(" ")[0] || "Cliente"}!`
                : "Bem-vindo!"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <>
                <Link href="/orders" className="hover:text-[var(--text-primary)] transition-colors">Meus Pedidos</Link>
                <Link href="/account" className="hover:text-[var(--text-primary)] transition-colors">Minha Conta</Link>
                <button onClick={logout} className="hover:text-[var(--text-primary)] transition-colors">Sair</button>
              </>
            ) : (
              <>
                <Link href="/login" className="hover:text-[var(--text-primary)] transition-colors">Entrar</Link>
                <Link href="/login" className="hover:text-[var(--text-primary)] transition-colors">Criar Conta</Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════ Header Principal (sticky) ═══════════ */}
      <header className="sticky top-0 z-50 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)]" style={{ boxShadow: "0 2px 12px rgba(0,0,0,0.5)" }}>
        <div className="container flex items-center justify-between py-3">
          <Link href="/" className="flex items-center gap-3">
            {siteInfo?.logo_url ? (
              <img
                src={siteInfo.logo_url}
                alt={nomeRestaurante}
                className="w-12 h-12 rounded-full object-cover"
                style={{ border: "2px solid var(--cor-primaria)" }}
              />
            ) : (
              <div className="w-12 h-12 rounded-full flex items-center justify-center text-2xl" style={{ background: "var(--cor-primaria)", color: "#fff" }}>
                {getEmojiRestaurante()}
              </div>
            )}
            <div>
              <h1 className="text-lg md:text-xl font-extrabold text-[var(--text-primary)] tracking-tight leading-tight">
                {nomeRestaurante}
              </h1>
              <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
                <Clock className="w-3 h-3" />
                <span>{siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}</span>
              </div>
            </div>
          </Link>

          {/* Desktop: Busca + Ações */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="/loyalty">
              <Button variant="ghost" size="sm" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]">
                Fidelidade
              </Button>
            </Link>
            {isLoggedIn ? (
              <Link href="/account">
                <Button variant="ghost" size="sm" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]">
                  <User className="w-4 h-4 mr-1" />
                  {cliente?.nome?.split(" ")[0]}
                </Button>
              </Link>
            ) : (
              <Link href="/login">
                <Button variant="ghost" size="sm" className="text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-card)]">
                  <User className="w-4 h-4 mr-1" />
                  Entrar
                </Button>
              </Link>
            )}
            <Link href="/cart">
              <Button
                size="sm"
                className="relative text-white border-0 gap-2 btn-press"
                style={{ background: "var(--cor-primaria)" }}
              >
                <ShoppingCart className="w-5 h-5" />
                <span className="font-semibold">Carrinho</span>
                {cartCount > 0 && (
                  <span className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-white text-[10px] font-bold flex items-center justify-center" style={{ color: "var(--cor-primaria)" }}>
                    {cartCount}
                  </span>
                )}
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button className="md:hidden text-[var(--text-primary)]" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[var(--border-subtle)] p-4 space-y-2 bg-[var(--bg-surface)]">
            <Link href="/cart" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]">
                <ShoppingCart className="w-4 h-4 mr-2" />
                Carrinho {cartCount > 0 && `(${cartCount})`}
              </Button>
            </Link>
            <Link href="/loyalty" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]">
                Fidelidade
              </Button>
            </Link>
            {isLoggedIn ? (
              <>
                <Link href="/orders" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]">
                    Meus Pedidos
                  </Button>
                </Link>
                <Link href="/account" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]">
                    <User className="w-4 h-4 mr-2" />
                    Minha Conta
                  </Button>
                </Link>
                <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]" onClick={() => { logout(); setMobileMenuOpen(false); }}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Sair
                </Button>
              </>
            ) : (
              <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="outline" size="sm" className="w-full justify-start border-[var(--border-subtle)] text-[var(--text-primary)] bg-transparent hover:bg-[var(--bg-card)]">
                  <User className="w-4 h-4 mr-2" />
                  Entrar / Criar Conta
                </Button>
              </Link>
            )}
          </div>
        )}
      </header>

      {/* ═══════════ Nav Categorias (sticky abaixo do header) ═══════════ */}
      <nav className="sticky top-[60px] z-40 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)]" style={{ boxShadow: "0 1px 6px rgba(0,0,0,0.3)" }}>
        <div className="container">
          <div ref={navRef} className="flex gap-2 overflow-x-auto scrollbar-hide py-2.5 category-fade">
            {loadingCat ? (
              [1, 2, 3, 4].map(i => (
                <div key={i} className="h-9 w-28 skeleton-dark rounded-full flex-shrink-0" />
              ))
            ) : (
              categorias.map((cat: Categoria) => {
                const count = produtosPorCategoria.get(cat.id)?.length || 0;
                if (count === 0) return null;
                return (
                  <button
                    key={cat.id}
                    data-cat-id={cat.id}
                    onClick={() => scrollToSection(cat.id)}
                    className={`flex items-center gap-1.5 whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-all flex-shrink-0 border ${
                      activeSection === cat.id
                        ? "text-white border-transparent shadow-md"
                        : "bg-[var(--bg-card)] text-[var(--text-secondary)] border-[var(--border-subtle)] hover:bg-[var(--bg-card-hover)] hover:text-[var(--text-primary)]"
                    }`}
                    style={activeSection === cat.id ? { background: "var(--cor-primaria)", borderColor: "var(--cor-primaria)" } : {}}
                  >
                    {cat.icone && <span>{cat.icone}</span>}
                    {cat.nome.replace(/^[^\w\s]+\s*/, "")}
                    <span className={`text-xs ${activeSection === cat.id ? "text-white/70" : "text-[var(--text-muted)]"}`}>
                      ({count})
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </nav>

      {/* ═══════════ Banner / Hero ═══════════ */}
      {siteInfo?.banner_principal_url ? (
        <div className="w-full h-40 md:h-56 overflow-hidden relative">
          <img src={siteInfo.banner_principal_url} alt={nomeRestaurante} className="w-full h-full object-cover" />
          <div className="absolute inset-0 bg-gradient-to-t from-[var(--bg-base)] via-transparent to-transparent" />
          <div className="absolute bottom-4 left-0 right-0">
            <div className="container">
              <div className="flex items-center gap-3">
                <h2 className="text-white text-xl md:text-2xl font-bold drop-shadow-lg">{nomeRestaurante}</h2>
                <span className="text-xs px-2 py-0.5 rounded-full text-white/80 border border-white/30 bg-white/10 backdrop-blur-sm">
                  {siteInfo?.tipo_restaurante || "Restaurante"}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-1 text-white/70 text-sm">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  ~{siteInfo?.tempo_entrega_estimado || 50} min
                </span>
                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5" />
                  Entrega e Retirada
                </span>
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div
          className="w-full h-36 md:h-48 flex items-center justify-center relative overflow-hidden"
          style={{ background: `linear-gradient(135deg, var(--cor-primaria), var(--cor-secundaria))` }}
        >
          <div className="absolute inset-0 bg-black/20" />
          <div className="text-center text-white relative z-10">
            <div className="text-5xl md:text-6xl mb-2">{getEmojiRestaurante()}</div>
            <p className="text-lg md:text-xl font-bold">{nomeRestaurante}</p>
            <div className="flex items-center justify-center gap-4 mt-2 text-white/70 text-sm">
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                ~{siteInfo?.tempo_entrega_estimado || 50} min
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Status do restaurante */}
      {siteInfo && !siteInfo.status_aberto && (
        <div className="bg-yellow-500/10 border-b border-yellow-500/20 text-yellow-400 text-center py-2.5 text-sm font-semibold">
          Estamos fechados no momento. Hor\u00E1rio: {siteInfo.horario_abertura} - {siteInfo.horario_fechamento}
        </div>
      )}

      {/* ═══════════ Main Content ═══════════ */}
      <main className="container py-6 px-4 md:py-8">

        {/* ── Combos e Ofertas ── */}
        {combos.length > 0 && (
          <section className="mb-10 animate-fade-in-up">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-1 h-7 rounded-full" style={{ background: "var(--cor-primaria)" }} />
              <h2 className="text-xl font-bold text-[var(--text-primary)]">{"\u{1F381}"} Combos e Ofertas</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {combos.map((combo: Combo) => {
                const economia = combo.preco_original - combo.preco_combo;
                const pct = combo.preco_original > 0 ? Math.round((economia / combo.preco_original) * 100) : 0;
                return (
                  <div
                    key={combo.id}
                    className="overflow-hidden rounded-xl card-hover group"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-card)" }}
                  >
                    <div className="flex flex-row">
                      {/* Imagem lado esquerdo */}
                      <div className="w-36 h-36 md:w-44 md:h-44 flex-shrink-0 flex items-center justify-center relative overflow-hidden" style={{ background: "var(--bg-card-hover)" }}>
                        {combo.imagem_url ? (
                          <img src={combo.imagem_url} alt={combo.nome} className="w-full h-full object-cover img-zoom" />
                        ) : (
                          <span className="text-5xl">{"\u{1F381}"}</span>
                        )}
                        <span className="absolute top-2 left-2 text-white text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider" style={{ background: "var(--cor-primaria)" }}>
                          -{pct}%
                        </span>
                      </div>
                      {/* Info lado direito */}
                      <div className="flex-1 p-4 flex flex-col justify-between">
                        <div>
                          <h3 className="font-bold text-base mb-1 text-[var(--text-primary)]">{combo.nome}</h3>
                          {combo.descricao && (
                            <p className="text-sm text-[var(--text-muted)] mb-1 line-clamp-2">{combo.descricao}</p>
                          )}
                          <div className="text-xs text-[var(--text-muted)] mb-2">
                            {combo.itens.map((it, i) => (
                              <span key={i}>{it.quantidade}x {it.produto_nome}{i < combo.itens.length - 1 ? " + " : ""}</span>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex flex-col">
                            <span className="text-xs text-[var(--text-muted)] line-through">
                              R$ {combo.preco_original.toFixed(2)}
                            </span>
                            <span className="font-extrabold text-lg" style={{ color: "var(--cor-primaria)" }}>
                              R$ {combo.preco_combo.toFixed(2)}
                            </span>
                          </div>
                          <Button
                            size="sm"
                            disabled={addingCombo === combo.id}
                            className="text-white btn-press"
                            onClick={async () => {
                              setAddingCombo(combo.id);
                              try {
                                await adicionarComboAoCarrinho(combo.id);
                                alert("Combo adicionado ao carrinho!");
                              } catch {
                                alert("Erro ao adicionar combo");
                              } finally {
                                setAddingCombo(null);
                              }
                            }}
                            style={{ background: "var(--cor-primaria)" }}
                          >
                            {addingCombo === combo.id ? "..." : "Adicionar"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Skeleton loading ── */}
        {loadingProd && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
              <div key={i} className="rounded-xl overflow-hidden" style={{ background: "var(--bg-card)", border: "1px solid var(--border-subtle)" }}>
                <div className="aspect-square skeleton-dark" />
                <div className="p-3 space-y-2">
                  <div className="h-4 skeleton-dark rounded w-2/3" />
                  <div className="h-3 skeleton-dark rounded w-full" />
                  <div className="h-5 skeleton-dark rounded w-1/3" />
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
                <div className="w-1 h-7 rounded-full" style={{ background: "var(--cor-primaria)" }} />
                {cat.icone && <span className="text-2xl">{cat.icone}</span>}
                <h3 className="text-lg font-bold text-[var(--text-primary)]">{cat.nome.replace(/^[^\w\s]+\s*/, "")}</h3>
                <span className="text-xs text-[var(--text-muted)] bg-[var(--bg-card)] px-2 py-0.5 rounded-full">
                  {produtos.length} {produtos.length === 1 ? "item" : "itens"}
                </span>
              </div>

              {/* Grid de produtos */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {produtos.map((produto: Produto) => (
                  <Link key={produto.id} href={`/product/${produto.id}`}>
                    <div
                      className="cursor-pointer overflow-hidden rounded-xl h-full flex flex-col card-hover group"
                      style={{ background: "var(--bg-card)", border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-card)" }}
                    >
                      {/* Imagem quadrada */}
                      <div className="aspect-square flex items-center justify-center text-4xl relative overflow-hidden" style={{ background: "var(--bg-card-hover)" }}>
                        {produto.imagem_url ? (
                          <img src={produto.imagem_url} alt={produto.nome} className="w-full h-full object-cover img-zoom" />
                        ) : (
                          <span className="text-5xl">{getEmoji(produto)}</span>
                        )}
                        {/* Overlay gradiente */}
                        <div className="absolute inset-0 bg-gradient-to-t from-black/40 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                        {/* Tags */}
                        {produto.destaque && (
                          <span className="absolute top-2 left-2 bg-emerald-500 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-lg">
                            Destaque
                          </span>
                        )}
                        {produto.promocao && (
                          <span className="absolute top-2 right-2 text-white text-[9px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider shadow-lg" style={{ background: "var(--cor-primaria)" }}>
                            Promo
                          </span>
                        )}
                      </div>
                      {/* Info */}
                      <div className="p-3 flex flex-col flex-1">
                        <h4 className="font-bold text-sm mb-1 line-clamp-1 uppercase text-[var(--text-primary)]">{produto.nome}</h4>
                        {produto.descricao && (
                          <p className="text-xs text-[var(--text-muted)] mb-2 line-clamp-2 flex-1">
                            {produto.descricao}
                          </p>
                        )}
                        {/* Separador */}
                        <div className="border-t border-[var(--border-subtle)] my-2" />
                        <div className="flex items-center justify-between mt-auto">
                          <div className="flex flex-col">
                            {produto.promocao && produto.preco_promocional && (
                              <span className="text-[10px] text-[var(--text-muted)] line-through">
                                R$ {produto.preco.toFixed(2)}
                              </span>
                            )}
                            <span className="font-extrabold text-sm" style={{ color: "var(--cor-primaria)" }}>
                              {getPrecoDisplay(produto)}
                            </span>
                          </div>
                          <span
                            className="text-xs px-2.5 py-1.5 rounded-lg font-semibold text-white btn-press"
                            style={{ background: "var(--cor-primaria)" }}
                          >
                            Comprar
                          </span>
                        </div>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}

        {/* Nenhum produto */}
        {!loadingProd && todosProdutos.length === 0 && (
          <p className="text-[var(--text-muted)] text-center py-12">Nenhum produto dispon\u00EDvel no card\u00E1pio.</p>
        )}
      </main>

      {/* ═══════════ Footer ═══════════ */}
      <footer className="bg-[var(--bg-surface)] border-t border-[var(--border-subtle)] mt-12">
        {/* Accent line */}
        <div className="h-1" style={{ background: `linear-gradient(90deg, var(--cor-primaria), var(--cor-secundaria))` }} />

        <div className="container px-4 py-10">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="font-bold text-base mb-3" style={{ color: "var(--cor-secundaria)" }}>
                Sobre
              </h3>
              <p className="text-[var(--text-muted)] text-sm leading-relaxed">
                {getSobreTexto()}
              </p>
            </div>
            <div>
              <h3 className="font-bold text-base mb-3" style={{ color: "var(--cor-secundaria)" }}>
                {nomeRestaurante}
              </h3>
              <p className="text-[var(--text-muted)] text-sm flex items-start gap-1.5">
                <MapPin className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                {siteInfo?.endereco_completo}
              </p>
            </div>
            <div>
              <h3 className="font-bold text-base mb-3" style={{ color: "var(--cor-secundaria)" }}>
                Contato
              </h3>
              <p className="text-[var(--text-muted)] text-sm">{siteInfo?.telefone}</p>
              {siteInfo?.whatsapp_ativo && siteInfo.whatsapp_numero && (
                <p className="text-[var(--text-muted)] text-sm mt-1">WhatsApp: {siteInfo.whatsapp_numero}</p>
              )}
            </div>
            <div>
              <h3 className="font-bold text-base mb-3" style={{ color: "var(--cor-secundaria)" }}>
                Hor\u00E1rio
              </h3>
              <p className="text-[var(--text-muted)] text-sm flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" />
                {siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}
              </p>
            </div>
          </div>
          <div className="border-t border-[var(--border-subtle)] mt-8 pt-6 text-center text-[var(--text-muted)] text-xs">
            &copy; {new Date().getFullYear()} {nomeRestaurante} - Powered by Super Food
          </div>
        </div>
      </footer>

      {/* ═══════════ FAB Carrinho (mobile) ═══════════ */}
      <Link href="/cart">
        <button
          className="md:hidden fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center text-white fab-pulse btn-press"
          style={{ background: "var(--cor-primaria)" }}
        >
          <ShoppingCart className="w-6 h-6" />
          {cartCount > 0 && (
            <span className="absolute -top-1 -right-1 w-5 h-5 rounded-full bg-white text-[10px] font-bold flex items-center justify-center" style={{ color: "var(--cor-primaria)" }}>
              {cartCount}
            </span>
          )}
        </button>
      </Link>
    </div>
  );
}
