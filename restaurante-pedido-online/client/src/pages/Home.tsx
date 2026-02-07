/**
 * Página Inicial - Site do Restaurante
 * Adaptado para consumir API FastAPI via hooks customizados
 */
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ShoppingCart, Menu, X, LogOut, MapPin, Clock, Phone } from "lucide-react";
import { useState, useEffect } from "react";
import { Link } from "wouter";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { useCategories, useProductsByCategory } from "@/hooks/useMenu";
import { useCartItems } from "@/hooks/useCart";

export default function Home() {
  const { siteInfo, loading: siteLoading, error: siteError } = useRestaurante();
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  // Simula autenticação (TODO: implementar sistema de auth)
  const isAuthenticated = true;
  const clienteId = 1; // TODO: pegar do contexto de auth

  const categoriesQuery = useCategories();
  const cartItemsQuery = useCartItems(clienteId, isAuthenticated);

  const productsQuery = useProductsByCategory(selectedCategory);

  // Set initial category
  useEffect(() => {
    if (categoriesQuery.data && categoriesQuery.data.length > 0 && !selectedCategory) {
      setSelectedCategory(categoriesQuery.data[0].id);
    }
  }, [categoriesQuery.data, selectedCategory]);

  // Update cart count
  useEffect(() => {
    if (cartItemsQuery.data?.itens) {
      const count = cartItemsQuery.data.itens.reduce(
        (sum: number, item: any) => sum + (item.quantidade || 1),
        0
      );
      setCartCount(count);
    }
  }, [cartItemsQuery.data]);

  // Loading state
  if (siteLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Carregando...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (siteError) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="text-center max-w-md px-4">
          <div className="text-6xl mb-4">🍕</div>
          <h1 className="text-2xl font-bold text-red-600 mb-2">Ops!</h1>
          <p className="text-muted-foreground mb-4">{siteError}</p>
          <p className="text-sm text-muted-foreground">
            Verifique se o código do restaurante está correto na URL.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="pizza-header sticky top-0 z-50 bg-background/95 backdrop-blur border-b">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center gap-3">
            {siteInfo?.logo_url ? (
              <img src={siteInfo.logo_url} alt={siteInfo.nome_fantasia} className="h-10 w-10 rounded-full object-cover" />
            ) : (
              <div className="text-3xl">🍕</div>
            )}
            <div>
              <h1 className="pizza-logo text-xl font-bold">{siteInfo?.nome_fantasia}</h1>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span className={`w-2 h-2 rounded-full ${siteInfo?.status_aberto ? 'bg-green-500' : 'bg-red-500'}`}></span>
                {siteInfo?.status_aberto ? 'Aberto' : 'Fechado'}
              </div>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/cart">
              <Button variant="outline" size="sm" className="relative">
                <ShoppingCart className="w-4 h-4" />
                {cartCount > 0 && (
                  <span className="absolute -top-2 -right-2 bg-primary text-primary-foreground text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {cartCount}
                  </span>
                )}
              </Button>
            </Link>
            <Link href="/orders">
              <Button variant="outline" size="sm">
                Meus Pedidos
              </Button>
            </Link>
            <Link href="/loyalty">
              <Button variant="outline" size="sm">
                Fidelidade
              </Button>
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border p-4 space-y-2">
            <Link href="/cart">
              <Button variant="outline" size="sm" className="w-full justify-start">
                <ShoppingCart className="w-4 h-4 mr-2" />
                Carrinho {cartCount > 0 && `(${cartCount})`}
              </Button>
            </Link>
            <Link href="/orders">
              <Button variant="outline" size="sm" className="w-full justify-start">
                Meus Pedidos
              </Button>
            </Link>
            <Link href="/loyalty">
              <Button variant="outline" size="sm" className="w-full justify-start">
                Fidelidade
              </Button>
            </Link>
          </div>
        )}
      </header>

      {/* Banner */}
      {siteInfo?.banner_principal_url && (
        <div className="relative h-48 md:h-64 overflow-hidden">
          <img
            src={siteInfo.banner_principal_url}
            alt="Banner"
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent" />
        </div>
      )}

      {/* Info Bar */}
      <div className="container py-4 border-b">
        <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <Clock className="w-4 h-4" />
            <span>Entrega: ~{siteInfo?.tempo_entrega_estimado}min</span>
          </div>
          <div className="flex items-center gap-1">
            <MapPin className="w-4 h-4" />
            <span>Retirada: ~{siteInfo?.tempo_retirada_estimado}min</span>
          </div>
          {siteInfo?.whatsapp_ativo && siteInfo?.whatsapp_numero && (
            <a
              href={`https://wa.me/55${siteInfo.whatsapp_numero}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-green-600 hover:text-green-700"
            >
              <Phone className="w-4 h-4" />
              <span>WhatsApp</span>
            </a>
          )}
          {siteInfo?.pedido_minimo > 0 && (
            <span>Pedido mínimo: R$ {siteInfo.pedido_minimo.toFixed(2)}</span>
          )}
        </div>
      </div>

      {/* Main Content */}
      <main className="container py-8">
        {/* Categories */}
        <div className="mb-8">
          <h2 className="text-2xl font-bold mb-4">Cardápio</h2>
          <div className="flex gap-2 overflow-x-auto pb-2 -mx-4 px-4 md:mx-0 md:px-0">
            {categoriesQuery.isLoading ? (
              // Loading skeleton
              Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 w-24 bg-muted rounded-lg animate-pulse flex-shrink-0" />
              ))
            ) : (
              categoriesQuery.data?.map((category: any) => (
                <button
                  key={category.id}
                  onClick={() => setSelectedCategory(category.id)}
                  className={`px-4 py-2 rounded-lg whitespace-nowrap flex-shrink-0 transition-colors ${
                    selectedCategory === category.id
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted hover:bg-muted/80"
                  }`}
                >
                  {category.icone && <span className="mr-1">{category.icone}</span>}
                  {category.nome}
                </button>
              ))
            )}
          </div>
        </div>

        {/* Products Grid */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-4">
            {categoriesQuery.data?.find((c: any) => c.id === selectedCategory)?.nome || "Produtos"}
          </h2>

          {productsQuery.isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="rounded-lg overflow-hidden animate-pulse">
                  <div className="h-48 bg-muted" />
                  <div className="p-4 space-y-2">
                    <div className="h-4 bg-muted rounded w-3/4" />
                    <div className="h-3 bg-muted rounded w-full" />
                    <div className="h-5 bg-muted rounded w-1/3" />
                  </div>
                </div>
              ))}
            </div>
          ) : productsQuery.data?.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <div className="text-4xl mb-2">🍽️</div>
              <p>Nenhum produto nesta categoria</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {productsQuery.data?.map((product: any) => (
                <Link key={product.id} href={`/product/${product.id}`}>
                  <Card className="overflow-hidden cursor-pointer hover:shadow-lg transition-shadow h-full">
                    <div className="h-48 bg-muted relative">
                      {product.imagem_url ? (
                        <img
                          src={product.imagem_url}
                          alt={product.nome}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-6xl">
                          🍕
                        </div>
                      )}
                      {product.promocao && (
                        <span className="absolute top-2 left-2 bg-red-500 text-white text-xs px-2 py-1 rounded">
                          Promoção
                        </span>
                      )}
                      {product.destaque && !product.promocao && (
                        <span className="absolute top-2 left-2 bg-primary text-primary-foreground text-xs px-2 py-1 rounded">
                          Destaque
                        </span>
                      )}
                    </div>
                    <div className="p-4">
                      <h3 className="font-semibold text-lg mb-1">{product.nome}</h3>
                      {product.descricao && (
                        <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                          {product.descricao}
                        </p>
                      )}
                      <div className="flex items-center justify-between">
                        {product.preco_promocional ? (
                          <div>
                            <span className="text-lg font-bold text-green-600">
                              R$ {product.preco_promocional.toFixed(2)}
                            </span>
                            <span className="text-sm text-muted-foreground line-through ml-2">
                              R$ {product.preco.toFixed(2)}
                            </span>
                          </div>
                        ) : (
                          <span className="text-lg font-bold">
                            R$ {product.preco.toFixed(2)}
                          </span>
                        )}
                        <Button size="sm" variant="outline">
                          Ver
                        </Button>
                      </div>
                    </div>
                  </Card>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t py-8 bg-muted/30">
        <div className="container">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="text-center md:text-left">
              <p className="font-semibold">{siteInfo?.nome_fantasia}</p>
              <p className="text-sm text-muted-foreground">{siteInfo?.endereco_completo}</p>
            </div>
            <div className="text-sm text-muted-foreground">
              Horário: {siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}
            </div>
          </div>
          <div className="mt-4 pt-4 border-t text-center text-xs text-muted-foreground">
            Powered by Super Food
          </div>
        </div>
      </footer>
    </div>
  );
}
