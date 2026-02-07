import { useAuth } from "@/_core/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ShoppingCart, Menu, X, LogOut } from "lucide-react";
import { getLoginUrl } from "@/const";
import { useState, useEffect } from "react";
import { trpc } from "@/lib/trpc";
import { Link } from "wouter";

export default function Home() {
  const { user, loading, isAuthenticated, logout } = useAuth();
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [cartCount, setCartCount] = useState(0);

  const categoriesQuery = trpc.menu.getCategories.useQuery();
  const cartItemsQuery = trpc.cart.getItems.useQuery(undefined, {
    enabled: isAuthenticated,
  });

  const productsQuery = trpc.menu.getProductsByCategory.useQuery(
    { categoryId: selectedCategory || 1 },
    { enabled: selectedCategory !== null }
  );

  // Set initial category
  useEffect(() => {
    if (categoriesQuery.data && categoriesQuery.data.length > 0 && !selectedCategory) {
      setSelectedCategory(categoriesQuery.data[0].id);
    }
  }, [categoriesQuery.data, selectedCategory]);

  // Update cart count
  useEffect(() => {
    if (cartItemsQuery.data) {
      const count = cartItemsQuery.data.reduce((sum, item) => sum + item.quantity, 0);
      setCartCount(count);
    }
  }, [cartItemsQuery.data]);

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="pizza-header">
        <div className="container flex items-center justify-between py-4">
          <div className="flex items-center gap-2">
            <div className="text-3xl">🍕</div>
            <h1 className="pizza-logo">Pizzaria Online</h1>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            {isAuthenticated ? (
              <>
                <span className="text-sm text-muted-foreground">
                  Olá, {user?.name || "Cliente"}
                </span>
                <Link href="/cart">
                  <Button variant="outline" size="sm" className="relative">
                    <ShoppingCart className="w-4 h-4" />
                    {cartCount > 0 && (
                      <span className="cart-badge">{cartCount}</span>
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
                {user?.role === "admin" && (
                  <Link href="/admin">
                    <Button variant="outline" size="sm">
                      Admin
                    </Button>
                  </Link>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="text-red-600 hover:text-red-700"
                >
                  <LogOut className="w-4 h-4" />
                </Button>
              </>
            ) : (
              <Button asChild size="sm">
                <a href={getLoginUrl()}>Entrar</a>
              </Button>
            )}
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
            {isAuthenticated ? (
              <>
                <p className="text-sm text-muted-foreground px-2">
                  Olá, {user?.name || "Cliente"}
                </p>
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
                {user?.role === "admin" && (
                  <Link href="/admin">
                    <Button variant="outline" size="sm" className="w-full justify-start">
                      Admin
                    </Button>
                  </Link>
                )}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleLogout}
                  className="w-full justify-start text-red-600 hover:text-red-700"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sair
                </Button>
              </>
            ) : (
              <Button asChild size="sm" className="w-full">
                <a href={getLoginUrl()}>Entrar</a>
              </Button>
            )}
          </div>
        )}
      </header>

      {/* Main Content */}
      <main className="container py-8">
        {!isAuthenticated ? (
          <div className="text-center py-12">
            <h2 className="text-3xl font-bold mb-4">Bem-vindo à Pizzaria Online</h2>
            <p className="text-muted-foreground mb-6">
              Faça login para começar a fazer seu pedido
            </p>
            <Button asChild size="lg">
              <a href={getLoginUrl()}>Entrar ou Cadastrar</a>
            </Button>
          </div>
        ) : (
          <>
            {/* Categories */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">Categorias</h2>
              <div className="category-nav">
                {categoriesQuery.data?.map((category) => (
                  <button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    className={`category-btn ${
                      selectedCategory === category.id ? "active" : ""
                    }`}
                  >
                    {category.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Products Grid */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold mb-4">
                {categoriesQuery.data?.find((c) => c.id === selectedCategory)?.name ||
                  "Produtos"}
              </h2>

              {productsQuery.isLoading ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[1, 2, 3, 4, 5, 6].map((i) => (
                    <div
                      key={i}
                      className="product-card animate-pulse"
                    >
                      <div className="product-image bg-muted" />
                      <div className="product-info">
                        <div className="h-4 bg-muted rounded mb-2" />
                        <div className="h-3 bg-muted rounded mb-3" />
                        <div className="h-5 bg-muted rounded w-1/3" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {productsQuery.data?.map((product) => (
                    <Link key={product.id} href={`/product/${product.id}`}>
                      <Card className="product-card cursor-pointer">
                        <div className="product-image">
                          {product.imageUrl ? (
                            <img
                              src={product.imageUrl}
                              alt={product.name}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-4xl">
                              🍕
                            </div>
                          )}
                        </div>
                        <div className="product-info">
                          <h3 className="product-name">{product.name}</h3>
                          {product.description && (
                            <p className="product-description">
                              {product.description}
                            </p>
                          )}
                          <div className="flex items-center justify-between">
                            <span className="product-price">
                              R$ {parseFloat(product.basePrice).toFixed(2)}
                            </span>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={(e) => {
                                e.preventDefault();
                                // Add to cart logic
                              }}
                            >
                              +
                            </Button>
                          </div>
                        </div>
                      </Card>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
