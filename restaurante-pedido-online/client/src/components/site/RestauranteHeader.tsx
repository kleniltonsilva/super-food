/**
 * RestauranteHeader.tsx — Header temático do site cliente.
 *
 * Adapta-se ao tipo de restaurante:
 * - Dark (Hamburgueria, Sushi, Restaurante): fundo escuro, texto claro
 * - Light (Bebidas): fundo claro, texto escuro
 * - Pattern (Pizzaria, Açaí, Salgados, Esfiharia): imagem de fundo + borda colorida
 *
 * Inclui: TopBar de login + Header principal com logo, busca, carrinho + Menu mobile.
 */

import { Button } from "@/components/ui/button";
import { ShoppingCart, Menu, X, User, LogOut, Search, Clock } from "lucide-react";
import { useState } from "react";
import { useRestaurante, useRestauranteTheme } from "@/contexts/RestauranteContext";
import { useAuth } from "@/contexts/AuthContext";
import { Link } from "wouter";

interface RestauranteHeaderProps {
  cartCount: number;
  busca: string;
  onBuscaChange: (value: string) => void;
}

export default function RestauranteHeader({ cartCount, busca, onBuscaChange }: RestauranteHeaderProps) {
  const { siteInfo } = useRestaurante();
  const theme = useRestauranteTheme();
  const { cliente, isLoggedIn, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);

  const nomeRestaurante = siteInfo?.nome_fantasia || "Restaurante";
  const isDark = theme.isDark;

  // Estilos dinâmicos baseados no tema
  const topBarStyle: React.CSSProperties = {
    background: theme.colors.topBarBg,
    color: theme.colors.topBarText,
  };

  const headerStyle: React.CSSProperties = {
    background: theme.colors.headerBg,
    boxShadow: isDark ? "0 2px 12px rgba(0,0,0,0.5)" : "0 2px 12px rgba(0,0,0,0.08)",
    ...(theme.headerStyle === "pattern" && theme.headerPattern ? {
      backgroundImage: `url(${theme.headerPattern})`,
      backgroundRepeat: "repeat-x",
      backgroundSize: "auto 100%",
    } : {}),
  };

  const textColor = isDark || theme.headerStyle === "dark" ? "#ffffff" : theme.colors.textPrimary;
  const mutedColor = isDark || theme.headerStyle === "dark" ? "rgba(255,255,255,0.6)" : theme.colors.textMuted;
  const inputBg = isDark ? "rgba(255,255,255,0.08)" : "#f5f5f5";
  const inputBorder = isDark ? "rgba(255,255,255,0.10)" : "#e0e0e0";

  return (
    <>
      {/* ═══════════ TopBar ═══════════ */}
      <div className="text-xs" style={topBarStyle}>
        <div className="container flex items-center justify-between py-1.5">
          <div className="flex items-center gap-2">
            <span
              className="w-2 h-2 rounded-full inline-block"
              style={{ background: siteInfo?.status_aberto ? "#22C55E" : "#EF4444" }}
            />
            <span style={{ opacity: 0.8 }}>
              {isLoggedIn
                ? `Olá, ${cliente?.nome?.split(" ")[0] || "Cliente"}!`
                : "Bem-vindo!"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            {isLoggedIn ? (
              <>
                <Link href="/orders" className="hover:opacity-100 transition-opacity" style={{ opacity: 0.7 }}>Meus Pedidos</Link>
                <Link href="/account" className="hover:opacity-100 transition-opacity" style={{ opacity: 0.7 }}>Minha Conta</Link>
                <button onClick={logout} className="hover:opacity-100 transition-opacity" style={{ opacity: 0.7 }}>Sair</button>
              </>
            ) : (
              <>
                <Link href="/login" className="hover:opacity-100 transition-opacity" style={{ opacity: 0.7 }}>Entrar</Link>
                <Link href="/login" className="hover:opacity-100 transition-opacity" style={{ opacity: 0.7 }}>Criar Conta</Link>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ═══════════ Header Principal (sticky) ═══════════ */}
      <header className="sticky top-0 z-50" style={headerStyle}>
        <div className="container flex items-center justify-between py-3">
          <Link href="/" className="flex items-center gap-3">
            {siteInfo?.logo_url ? (
              <img
                src={siteInfo.logo_url}
                alt={nomeRestaurante}
                className="w-12 h-12 rounded-full object-cover"
                style={{
                  border: `2px solid ${theme.colors.primary}`,
                  maxWidth: theme.logoMaxWidth,
                }}
              />
            ) : (
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center text-2xl"
                style={{ background: theme.colors.primary, color: "#fff" }}
              >
                {theme.label.charAt(0)}
              </div>
            )}
            <div>
              <h1
                className="text-lg md:text-xl font-extrabold tracking-tight leading-tight"
                style={{
                  color: textColor,
                  fontFamily: theme.fonts.heading,
                }}
              >
                {nomeRestaurante}
              </h1>
              <div className="flex items-center gap-2 text-xs" style={{ color: mutedColor }}>
                <Clock className="w-3 h-3" />
                <span>{siteInfo?.horario_abertura} - {siteInfo?.horario_fechamento}</span>
              </div>
            </div>
          </Link>

          {/* Desktop: Busca + Ações */}
          <div className="hidden md:flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: mutedColor }} />
              <input
                type="text"
                value={busca}
                onChange={e => onBuscaChange(e.target.value)}
                placeholder="Buscar produto..."
                className="pl-9 pr-3 py-1.5 text-sm w-48 rounded-full focus:outline-none focus:ring-1"
                style={{
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  ["--tw-ring-color" as string]: theme.colors.primary,
                }}
              />
            </div>
            <Link href="/loyalty">
              <Button variant="ghost" size="sm" style={{ color: mutedColor }} className="hover:opacity-100">
                Fidelidade
              </Button>
            </Link>
            {isLoggedIn ? (
              <Link href="/account">
                <Button variant="ghost" size="sm" style={{ color: mutedColor }} className="hover:opacity-100">
                  <User className="w-4 h-4 mr-1" />
                  {cliente?.nome?.split(" ")[0]}
                </Button>
              </Link>
            ) : (
              <Link href="/login">
                <Button variant="ghost" size="sm" style={{ color: mutedColor }} className="hover:opacity-100">
                  <User className="w-4 h-4 mr-1" />
                  Entrar
                </Button>
              </Link>
            )}
            <Link href="/cart">
              <Button
                size="sm"
                className="relative text-white border-0 gap-2 btn-press"
                style={{ background: theme.colors.primary }}
              >
                <ShoppingCart className="w-5 h-5" />
                <span className="font-semibold">Carrinho</span>
                {cartCount > 0 && (
                  <span
                    className="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-white text-[10px] font-bold flex items-center justify-center"
                    style={{ color: theme.colors.primary }}
                  >
                    {cartCount}
                  </span>
                )}
              </Button>
            </Link>
          </div>

          {/* Mobile: Lupa + Menu */}
          <div className="flex items-center gap-2 md:hidden">
            <button
              style={{ color: textColor }}
              onClick={() => { setMobileSearchOpen(!mobileSearchOpen); setMobileMenuOpen(false); }}
              aria-label="Buscar"
            >
              <Search className="w-5 h-5" />
            </button>
            <button style={{ color: textColor }} onClick={() => { setMobileMenuOpen(!mobileMenuOpen); setMobileSearchOpen(false); }}>
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Search Bar */}
        {mobileSearchOpen && (
          <div
            className="md:hidden px-4 py-2"
            style={{
              background: theme.colors.headerBg,
              borderTop: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "#e8e8e8"}`,
            }}
          >
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: mutedColor }} />
              <input
                type="text"
                value={busca}
                onChange={e => onBuscaChange(e.target.value)}
                placeholder="Buscar produto..."
                autoFocus
                className="pl-9 pr-9 py-2 text-sm w-full rounded-full focus:outline-none focus:ring-1"
                style={{
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  ["--tw-ring-color" as string]: theme.colors.primary,
                }}
              />
              {busca && (
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: mutedColor }}
                  onClick={() => onBuscaChange("")}
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div
            className="md:hidden p-4 space-y-2"
            style={{
              background: theme.colors.headerBg,
              borderTop: `1px solid ${isDark ? "rgba(255,255,255,0.08)" : "#e8e8e8"}`,
            }}
          >
            <div className="relative mb-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: mutedColor }} />
              <input
                type="text"
                value={busca}
                onChange={e => onBuscaChange(e.target.value)}
                placeholder="Buscar produto..."
                className="pl-9 pr-3 py-2 text-sm w-full rounded-lg focus:outline-none focus:ring-1"
                style={{
                  background: inputBg,
                  border: `1px solid ${inputBorder}`,
                  color: textColor,
                  ["--tw-ring-color" as string]: theme.colors.primary,
                }}
              />
            </div>
            <Link href="/cart" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start" style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}>
                <ShoppingCart className="w-4 h-4 mr-2" />
                Carrinho {cartCount > 0 && `(${cartCount})`}
              </Button>
            </Link>
            <Link href="/loyalty" onClick={() => setMobileMenuOpen(false)}>
              <Button variant="outline" size="sm" className="w-full justify-start" style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}>
                Fidelidade
              </Button>
            </Link>
            {isLoggedIn ? (
              <>
                <Link href="/orders" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start" style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}>
                    Meus Pedidos
                  </Button>
                </Link>
                <Link href="/account" onClick={() => setMobileMenuOpen(false)}>
                  <Button variant="outline" size="sm" className="w-full justify-start" style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}>
                    <User className="w-4 h-4 mr-2" />
                    Minha Conta
                  </Button>
                </Link>
                <Button
                  variant="outline" size="sm"
                  className="w-full justify-start"
                  style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}
                  onClick={() => { logout(); setMobileMenuOpen(false); }}
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Sair
                </Button>
              </>
            ) : (
              <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
                <Button variant="outline" size="sm" className="w-full justify-start" style={{ borderColor: inputBorder, color: textColor, background: "transparent" }}>
                  <User className="w-4 h-4 mr-2" />
                  Entrar / Criar Conta
                </Button>
              </Link>
            )}
          </div>
        )}
      </header>
    </>
  );
}
