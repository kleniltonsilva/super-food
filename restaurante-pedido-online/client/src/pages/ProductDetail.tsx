import { useParams, useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, Plus, Minus } from "lucide-react";
import { useState, useEffect } from "react";
import { trpc } from "@/lib/trpc";
import { useAuth } from "@/_core/hooks/useAuth";
import { toast } from "sonner";

export default function ProductDetail() {
  const params = useParams();
  const [, navigate] = useLocation();
  const { isAuthenticated } = useAuth();
  const productId = parseInt(params?.id || "0");

  const [quantity, setQuantity] = useState(1);
  const [selectedSize, setSelectedSize] = useState<number | null>(null);
  const [selectedFlavors, setSelectedFlavors] = useState<number[]>([]);
  const [customizationNotes, setCustomizationNotes] = useState("");

  const productQuery = trpc.menu.getProductById.useQuery({ productId });
  const sizesQuery = trpc.menu.getSizes.useQuery();
  const flavorsQuery = trpc.menu.getFlavors.useQuery();
  const addToCartMutation = trpc.cart.addItem.useMutation();

  useEffect(() => {
    if (sizesQuery.data && sizesQuery.data.length > 0) {
      setSelectedSize(sizesQuery.data[0].id);
    }
  }, [sizesQuery.data]);

  const handleAddFlavor = (flavorId: number) => {
    if (selectedFlavors.includes(flavorId)) {
      setSelectedFlavors(selectedFlavors.filter((id) => id !== flavorId));
    } else {
      if (selectedFlavors.length < 4) {
        setSelectedFlavors([...selectedFlavors, flavorId]);
      } else {
        toast.error("Máximo de 4 sabores permitidos");
      }
    }
  };

  const handleAddToCart = async () => {
    if (!isAuthenticated) {
      toast.error("Faça login para adicionar ao carrinho");
      return;
    }

    if (!productQuery.data) {
      toast.error("Produto não encontrado");
      return;
    }

    const product = productQuery.data;
    let unitPrice = parseFloat(product.basePrice);

    // Add size multiplier
    if (selectedSize && sizesQuery.data) {
      const size = sizesQuery.data.find((s) => s.id === selectedSize);
      if (size) {
        unitPrice *= parseFloat(size.priceMultiplier);
      }
    }

    // Add flavor prices
    if (selectedFlavors.length > 0 && flavorsQuery.data) {
      const flavorPrices = selectedFlavors.reduce((sum, flavorId) => {
        const flavor = flavorsQuery.data?.find((f) => f.id === flavorId);
        return sum + (flavor ? parseFloat(flavor.priceAdditional) : 0);
      }, 0);
      unitPrice += flavorPrices;
    }

    try {
      await addToCartMutation.mutateAsync({
        productId,
        quantity,
        unitPrice: unitPrice.toFixed(2),
        sizeId: selectedSize || undefined,
        selectedFlavors: selectedFlavors.length > 0 ? selectedFlavors : undefined,
        customizationNotes: customizationNotes || undefined,
      });

      toast.success("Adicionado ao carrinho!");
      navigate("/cart");
    } catch (error) {
      toast.error("Erro ao adicionar ao carrinho");
    }
  };

  if (productQuery.isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8">
          <div className="animate-pulse space-y-4">
            <div className="h-96 bg-muted rounded-lg" />
            <div className="h-8 bg-muted rounded w-1/3" />
            <div className="h-4 bg-muted rounded w-2/3" />
          </div>
        </div>
      </div>
    );
  }

  if (!productQuery.data) {
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
          <p className="text-center text-muted-foreground">Produto não encontrado</p>
        </div>
      </div>
    );
  }

  const product = productQuery.data;

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

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Product Image */}
          <div>
            <Card className="overflow-hidden">
              <div className="w-full aspect-square bg-muted flex items-center justify-center text-6xl">
                {product.imageUrl ? (
                  <img
                    src={product.imageUrl}
                    alt={product.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  "🍕"
                )}
              </div>
            </Card>
          </div>

          {/* Product Info */}
          <div className="space-y-6">
            <div>
              <h1 className="text-4xl font-bold mb-2">{product.name}</h1>
              {product.description && (
                <p className="text-muted-foreground mb-4">{product.description}</p>
              )}
            </div>

            {/* Size Selection */}
            {product.isCustomizable && sizesQuery.data && sizesQuery.data.length > 0 && (
              <div>
                <h3 className="text-lg font-bold mb-3">Tamanho</h3>
                <div className="grid grid-cols-2 gap-3">
                  {sizesQuery.data.map((size) => (
                    <button
                      key={size.id}
                      onClick={() => setSelectedSize(size.id)}
                      className={`p-3 border rounded-lg transition-all ${
                        selectedSize === size.id
                          ? "border-accent bg-red-50"
                          : "border-border hover:border-accent"
                      }`}
                    >
                      <div className="font-bold">{size.name}</div>
                      {size.description && (
                        <div className="text-xs text-muted-foreground">
                          {size.description}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Flavor Selection */}
            {product.isCustomizable && flavorsQuery.data && flavorsQuery.data.length > 0 && (
              <div>
                <h3 className="text-lg font-bold mb-3">
                  Sabores (Máximo 4)
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {flavorsQuery.data.map((flavor) => (
                    <button
                      key={flavor.id}
                      onClick={() => handleAddFlavor(flavor.id)}
                      className={`w-full p-3 border rounded-lg text-left transition-all ${
                        selectedFlavors.includes(flavor.id)
                          ? "border-accent bg-red-50"
                          : "border-border hover:border-accent"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-bold">{flavor.name}</div>
                          {flavor.description && (
                            <div className="text-xs text-muted-foreground">
                              {flavor.description}
                            </div>
                          )}
                        </div>
                        {parseFloat(flavor.priceAdditional) > 0 && (
                          <span className="text-sm font-bold text-accent">
                            +R$ {parseFloat(flavor.priceAdditional).toFixed(2)}
                          </span>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  Selecionados: {selectedFlavors.length}/4
                </p>
              </div>
            )}

            {/* Customization Notes */}
            <div>
              <label className="text-sm font-bold mb-2 block">
                Observações (opcional)
              </label>
              <textarea
                value={customizationNotes}
                onChange={(e) => setCustomizationNotes(e.target.value)}
                placeholder="Ex: Sem cebola, extra queijo..."
                className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
                rows={3}
              />
            </div>

            {/* Quantity and Price */}
            <div className="space-y-4">
              <div className="flex items-center gap-4">
                <span className="text-sm font-bold">Quantidade:</span>
                <div className="quantity-selector">
                  <button
                    className="quantity-btn"
                    onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  >
                    <Minus className="w-4 h-4" />
                  </button>
                  <span className="px-4 py-1 font-bold">{quantity}</span>
                  <button
                    className="quantity-btn"
                    onClick={() => setQuantity(quantity + 1)}
                  >
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="border-t border-border pt-4">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-lg font-bold">Total:</span>
                  <span className="text-2xl font-bold text-accent">
                    R$ {(
                      parseFloat(product.basePrice) * quantity
                    ).toFixed(2)}
                  </span>
                </div>

                <Button
                  onClick={handleAddToCart}
                  disabled={addToCartMutation.isPending}
                  className="w-full bg-accent hover:bg-accent/90 text-white py-6 text-lg"
                >
                  {addToCartMutation.isPending
                    ? "Adicionando..."
                    : "Adicionar ao Carrinho"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
