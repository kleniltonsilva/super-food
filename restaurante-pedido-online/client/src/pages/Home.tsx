/**
 * Home.tsx — Página principal do site cliente.
 *
 * Layout estilo "Expresso Delivery":
 * - TopBar com saudação + links de login/conta
 * - Header sticky com logo + carrinho
 * - Nav de categorias com scroll suave para seções
 * - Combos em cards horizontais
 * - Todas as categorias como seções na página com grid de produtos
 * - Cards compactos com imagem quadrada + tags + botão "Comprar"
 */

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ShoppingCart, Menu, X, User, LogOut, ChevronRight } from "lucide-react";
import { useState, useMemo, useRef } from "react";
import { adicionarComboAoCarrinho } from "@/lib/apiClient";
import { useCategorias, useTodosProdutos, useCombos } from "@/hooks/useQueries";
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
  function scrollToSection(catId: number) {
    setActiveSection(catId);
    const el = document.getElementById(`cat-${catId}`);
    if (el) {
      const offset = 140; // header + nav height
      const top = el.getBoundingClientRect().top + window.scrollY - offset;
      window.scrollTo({ top, behavior: "smooth" });
    }
  }

  if (siteLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">{getEmojiRestaurante()}</div>
          <p className="text-muted-foreground">Carregando...</p>
        </div>
      </div>
    );
  }

  if (siteError) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="text-4xl mb-4">{"\u{1F615}"}</div>
          <p className="text-muted-foreground">{siteError}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ═══════════ TopBar ═══════════ */}
      <div className="bg-gray-900 text-gray-300 text-xs">
        <div className="container flex items-center justify-between py-1.5">
          <span>
            {isLoggedIn
              ? `Ol\u00E1, ${cliente?.nome?.split(" ")[0] || "Cliente"}!`
              : "Bem-vindo! Fa\u00E7a login para acompanhar seus pedidos."}
          </span>
          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <>
                <Link href="/orders" className="hover:text-white transition-colors">Meus Pedidos</Link>
                <Link href="/account" className="hover:text-white transition-colors">Minha Conta</Link>
                <button onClick={logout} className="hover:text-white transition-colors">Sair</button>
              </>
            ) : (
              <>
                <Link href="/login" className="hover:text-white transition-colors">Entrar</Link>
                <Link href="/login" className="hover:text-white transition-colors">Criar Conta</Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════ Header Principal (sticky) ═══════════ */}
      <header
        className="sticky top-0 z-50 shadow-md"
        style={{ background: `var(--cor-primaria, #E31A24)` }}
      >
        <div className="container flex items-center justify-between py-3">
          <Link href="/" className="flex items-center gap-3">
            {siteInfo?.logo_url ? (
              <img src={siteInfo.logo_url} alt={nomeRestaurante} className="w-12 h-12 rounded-full object-cover border-2 border-white/30" />
            ) : (
              <div className="text-4xl">{getEmojiRestaurante()}</div>
            )}
            <h1 className="text-xl md:text-2xl font-extrabold text-white tracking-tight">
              {nomeRestaurante}
            </h1>
          </Link>

          {/* Desktop: Carrinho */}
          <div className="hidden md:flex items-center gap-3">
            <Link href="/loyalty">
              <Button variant="ghost" size="sm" className="text-white/80 hover:text-white hover:bg-white/10">
                Fidelidade
              </Button>
            </Link>
            <Link href="/cart">
              <Button size="sm" className="bg-white/20 hover:bg-white/30 text-white border-0 gap-2">
                <ShoppingCart className="w-5 h-5" />
                <span className="font-semibold">Carrinho</span>
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button className="md:hidden text-white" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-white/20 p-4 space-y-2">
            <Link href="/cart" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white">
                <ShoppingCart className="w-4 h-4 mr-2" />
                Carrinho
              </Button>
            </Link>
            <Link href="/loyalty" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white">
                Fidelidade
              </Button>
            </Link>
            {isLoggedIn ? (
              <>
                <Link href="/orders" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white">
                    Meus Pedidos
                  </Button>
                </Link>
                <Link href="/account" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white">
                    <User className="w-4 h-4 mr-2" />
                    Minha Conta
                  </Button>
                </Link>
                <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white" onClick={() => { logout(); setMobileMenuOpen(false); }}>
                  <LogOut className="w-4 h-4 mr-2" />
                  Sair
                </Button>
              </>
            ) : (
              <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="outline" size="sm" className="w-full justify-start border-white/30 text-white">
                  <User className="w-4 h-4 mr-2" />
                  Entrar / Criar Conta
                </Button>
              </Link>
            )}
          </div>
        )}
      </header>

      {/* ═══════════ Nav Categorias (sticky abaixo do header) ═══════════ */}
      <nav className="sticky top-[60px] z-40 bg-white shadow-sm border-b">
        <div className="container">
          <div ref={navRef} className="flex gap-1 overflow-x-auto scrollbar-hide py-2">
            {loadingCat ? (
              [1, 2, 3, 4].map(i => (
                <div key={i} className="h-9 w-28 bg-gray-200 rounded-full animate-pulse flex-shrink-0" />
              ))
            ) : (
              categorias.map((cat: Categoria) => {
                const count = produtosPorCategoria.get(cat.id)?.length || 0;
                if (count === 0) return null;
                return (
                  <button
                    key={cat.id}
                    onClick={() => scrollToSection(cat.id)}
                    className={`flex items-center gap-1.5 whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-all flex-shrink-0 ${
                      activeSection === cat.id
                        ? "text-white shadow-sm"
                        : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                    }`}
                    style={activeSection === cat.id ? { background: `var(--cor-primaria, #E31A24)` } : {}}
                  >
                    {cat.icone && <span>{cat.icone}</span>}
                    {cat.nome.replace(/^[^\w\s]+\s*/, "")}
                    <span className={`text-xs ${activeSection === cat.id ? "text-white/70" : "text-gray-400"}`}>
                      ({count})
                    </span>
                  </button>
                );
              })
            )}
          </div>
        </div>
      </nav>

      {/* Banner / Hero */}
      {siteInfo?.banner_principal_url ? (
        <div className="w-full h-40 md:h-56 overflow-hidden">
          <img src={siteInfo.banner_principal_url} alt={nomeRestaurante} className="w-full h-full object-cover" />
        </div>
      ) : (
        <div
          className="w-full h-32 md:h-44 flex items-center justify-center"
          style={{ background: `linear-gradient(135deg, var(--cor-primaria, #E31A24), var(--cor-secundaria, #FFD700))` }}
        >
          <div className="text-center text-white">
            <div className="text-5xl md:text-6xl mb-1">{getEmojiRestaurante()}</div>
            <p className="text-lg md:text-xl font-bold">{nomeRestaurante}</p>
          </div>
        </div>
      )}

      {/* Status do restaurante */}
      {siteInfo && !siteInfo.status_aberto && (
        <div className="bg-yellow-100 text-yellow-800 text-center py-2 text-sm font-semibold">
          Estamos fechados no momento. Hor\u00E1rio: {siteInfo.horario_abertura} - {siteInfo.horario_fechamento}
        </div>
      )}

      {/* ═══════════ Main Content ═══════════ */}
      <main className="container py-6 px-4 md:py-8">

        {/* ── Combos e Ofertas (cards horizontais) ── */}
        {combos.length > 0 && (
          <section className="mb-10">
            <div className="flex items-center gap-2 mb-4">
              <h2 className="text-2xl font-bold">{"\u{1F381}"} Combos e Ofertas</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {combos.map((combo: Combo) => {
                const economia = combo.preco_original - combo.preco_combo;
                const pct = combo.preco_original > 0 ? Math.round((economia / combo.preco_original) * 100) : 0;
                return (
                  <Card key={combo.id} className="overflow-hidden rounded-xl border hover:shadow-lg transition-all">
                    <div className="flex flex-row">
                      {/* Imagem lado esquerdo */}
                      <div className="w-36 h-36 md:w-44 md:h-44 flex-shrink-0 bg-gradient-to-br from-yellow-400 to-orange-500 flex items-center justify-center relative">
                        {combo.imagem_url ? (
                          <img src={combo.imagem_url} alt={combo.nome} className="w-full h-full object-cover" />
                        ) : (
                          <span className="text-5xl">{"\u{1F381}"}</span>
                        )}
                        <span className="absolute top-2 left-2 bg-red-600 text-white text-xs font-bold px-2 py-0.5 rounded">
                          -{pct}%
                        </span>
                      </div>
                      {/* Info lado direito */}
                      <div className="flex-1 p-4 flex flex-col justify-between">
                        <div>
                          <h3 className="font-bold text-lg mb-1">{combo.nome}</h3>
                          {combo.descricao && (
                            <p className="text-sm text-muted-foreground mb-1 line-clamp-2">{combo.descricao}</p>
                          )}
                          <div className="text-xs text-muted-foreground mb-2">
                            {combo.itens.map((it, i) => (
                              <span key={i}>{it.quantidade}x {it.produto_nome}{i < combo.itens.length - 1 ? " + " : ""}</span>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <div className="flex flex-col">
                            <span className="text-xs text-muted-foreground line-through">
                              R$ {combo.preco_original.toFixed(2)}
                            </span>
                            <span className="font-extrabold text-lg" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                              R$ {combo.preco_combo.toFixed(2)}
                            </span>
                          </div>
                          <Button
                            size="sm"
                            disabled={addingCombo === combo.id}
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
                            style={{ background: `var(--cor-primaria, #E31A24)`, color: "white" }}
                          >
                            {addingCombo === combo.id ? "..." : "Adicionar"}
                          </Button>
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </section>
        )}

        {/* ── Skeleton loading ── */}
        {loadingProd && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map(i => (
              <div key={i} className="animate-pulse rounded-xl border bg-white">
                <div className="aspect-square bg-gray-200 rounded-t-xl" />
                <div className="p-3 space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-2/3" />
                  <div className="h-3 bg-gray-200 rounded w-full" />
                  <div className="h-5 bg-gray-200 rounded w-1/3" />
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
            <section key={cat.id} id={`cat-${cat.id}`} className="mb-10">
              {/* Titulo da categoria */}
              <div className="flex items-center gap-2 mb-4 pb-2 border-b-2" style={{ borderColor: `var(--cor-primaria, #E31A24)` }}>
                {cat.icone && <span className="text-2xl">{cat.icone}</span>}
                <h3 className="text-xl font-bold">{cat.nome.replace(/^[^\w\s]+\s*/, "")}</h3>
                <span className="text-sm text-muted-foreground">({produtos.length} {produtos.length === 1 ? "item" : "itens"})</span>
              </div>

              {/* Grid de produtos */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {produtos.map((produto: Produto) => (
                  <Link key={produto.id} href={`/product/${produto.id}`}>
                    <Card className="cursor-pointer overflow-hidden rounded-xl border bg-white hover:shadow-lg transition-all hover:-translate-y-1 h-full flex flex-col">
                      {/* Imagem quadrada */}
                      <div className="aspect-square bg-gray-100 flex items-center justify-center text-4xl relative overflow-hidden">
                        {produto.imagem_url ? (
                          <img src={produto.imagem_url} alt={produto.nome} className="w-full h-full object-cover" />
                        ) : (
                          <span className="text-5xl">{getEmoji(produto)}</span>
                        )}
                        {/* Tags */}
                        {produto.destaque && (
                          <span className="absolute top-2 left-2 bg-green-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow">
                            DESTAQUE
                          </span>
                        )}
                        {produto.promocao && (
                          <span className="absolute top-2 right-2 bg-red-600 text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow">
                            PROMO
                          </span>
                        )}
                      </div>
                      {/* Info */}
                      <div className="p-3 flex flex-col flex-1">
                        <h4 className="font-bold text-sm mb-1 line-clamp-1 uppercase">{produto.nome}</h4>
                        {produto.descricao && (
                          <p className="text-xs text-muted-foreground mb-2 line-clamp-2 flex-1">
                            {produto.descricao}
                          </p>
                        )}
                        <div className="flex items-center justify-between mt-auto">
                          <div className="flex flex-col">
                            {produto.promocao && produto.preco_promocional && (
                              <span className="text-[10px] text-muted-foreground line-through">
                                R$ {produto.preco.toFixed(2)}
                              </span>
                            )}
                            <span className="font-extrabold text-sm" style={{ color: `var(--cor-primaria, #E31A24)` }}>
                              {getPrecoDisplay(produto)}
                            </span>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-xs px-2 py-1 h-7"
                            style={{ borderColor: `var(--cor-primaria, #E31A24)`, color: `var(--cor-primaria, #E31A24)` }}
                          >
                            Comprar
                            <ChevronRight className="w-3 h-3 ml-0.5" />
                          </Button>
                        </div>
                      </div>
                    </Card>
                  </Link>
                ))}
              </div>
            </section>
          );
        })}

        {/* Nenhum produto */}
        {!loadingProd && todosProdutos.length === 0 && (
          <p className="text-muted-foreground text-center py-12">Nenhum produto dispon\u00EDvel no card\u00E1pio.</p>
        )}
      </main>

      {/* ═══════════ Footer ═══════════ */}
      <footer className="bg-gray-900 text-white py-10 mt-12">
        <div className="container px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="font-bold text-lg mb-3" style={{ color: `var(--cor-secundaria, #FFD700)` }}>
                Sobre
              </h3>
              <p className="text-gray-400 text-sm leading-relaxed">
                {getSobreTexto()}
              </p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-3" style={{ color: `var(--cor-secundaria, #FFD700)` }}>
                {nomeRestaurante}
              </h3>
              <p className="text-gray-400 text-sm">
                {siteInfo?.endereco_completo}
              </p>
            </div>
            <div>
              <h3 className="font-bold text-lg mb-3" style={{ color: `var(--cor-secundaria, #FFD700)` }}>
                Contato
              </h3>
              <p className="text-gray-400 text-sm">{siteInfo?.telefone}</p>
              {siteInfo?.whatsapp_ativo && siteInfo.whatsapp_numero && (
                <p className="text-gray-400 text-sm mt-1">WhatsApp: {siteInfo.whatsapp_numero}</p>
              )}
            </div>
            <div>
              <h3 className="font-bold text-lg mb-3" style={{ color: `var(--cor-secundaria, #FFD700)` }}>
                Hor\u00E1rio
              </h3>
              <p className="text-gray-400 text-sm">
                {siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}
              </p>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-8 pt-6 text-center text-gray-500 text-xs">
            &copy; {new Date().getFullYear()} {nomeRestaurante} - Powered by Super Food
          </div>
        </div>
      </footer>

      {/* ═══════════ FAB Carrinho (mobile) ═══════════ */}
      <Link href="/cart">
        <button
          className="md:hidden fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full shadow-lg flex items-center justify-center text-white"
          style={{ background: `var(--cor-primaria, #E31A24)` }}
        >
          <ShoppingCart className="w-6 h-6" />
        </button>
      </Link>
    </div>
  );
}
