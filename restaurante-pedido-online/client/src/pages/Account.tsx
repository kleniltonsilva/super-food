import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ArrowLeft, User, MapPin, Trash2, Star } from "lucide-react";
import { useLocation } from "wouter";
import { useAuth } from "@/contexts/AuthContext";
import { useRestaurante } from "@/contexts/RestauranteContext";
import { getEnderecos, removerEndereco, definirEnderecoPadrao, atualizarPerfil } from "@/lib/apiClient";
import { toast } from "sonner";
import { useState, useEffect } from "react";

interface Endereco {
  id: number;
  apelido: string | null;
  endereco_completo: string;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  padrao: boolean;
}

export default function Account() {
  const [, navigate] = useLocation();
  const { cliente, isLoggedIn, refreshCliente, logout } = useAuth();
  const { siteInfo } = useRestaurante();

  const [enderecos, setEnderecos] = useState<Endereco[]>([]);
  const [loading, setLoading] = useState(true);

  // Edição de perfil
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (!isLoggedIn) {
      setLoading(false);
      return;
    }
    setNome(cliente?.nome || "");
    setTelefone(cliente?.telefone || "");

    async function load() {
      try {
        const ends = await getEnderecos();
        setEnderecos(ends);
      } catch {
        setEnderecos([]);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [isLoggedIn, cliente]);

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen bg-background">
        <div className="container py-8 px-4">
          <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Voltar
          </Button>
          <Card className="p-8 text-center">
            <p className="text-muted-foreground mb-4">Faça login para acessar sua conta</p>
            <Button onClick={() => navigate("/login")} style={{ background: `var(--cor-primaria, #E31A24)` }} className="text-white">
              Fazer Login
            </Button>
          </Card>
        </div>
      </div>
    );
  }

  const handleSalvarPerfil = async () => {
    if (!nome.trim()) { toast.error("Nome é obrigatório"); return; }
    setSalvando(true);
    try {
      await atualizarPerfil({ nome: nome.trim(), telefone: telefone.trim() });
      await refreshCliente();
      setEditando(false);
      toast.success("Perfil atualizado!");
    } catch {
      toast.error("Erro ao atualizar perfil");
    } finally {
      setSalvando(false);
    }
  };

  const handleRemoverEndereco = async (id: number) => {
    try {
      await removerEndereco(id);
      setEnderecos(prev => prev.filter(e => e.id !== id));
      toast.success("Endereço removido");
    } catch {
      toast.error("Erro ao remover endereço");
    }
  };

  const handleDefinirPadrao = async (id: number) => {
    try {
      await definirEnderecoPadrao(id);
      setEnderecos(prev => prev.map(e => ({ ...e, padrao: e.id === id })));
      toast.success("Endereço padrão definido");
    } catch {
      toast.error("Erro ao definir endereço padrão");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="container py-6 px-4 md:py-8 max-w-2xl mx-auto">
        <Button variant="ghost" onClick={() => navigate("/")} className="mb-4">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Voltar
        </Button>

        <h1 className="text-2xl md:text-3xl font-bold mb-6">Minha Conta</h1>

        {/* Dados Pessoais */}
        <Card className="p-4 md:p-6 mb-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <User className="w-5 h-5" />
            Dados Pessoais
          </h2>

          {editando ? (
            <div className="space-y-3">
              <div>
                <label className="text-sm font-bold mb-1 block">Nome</label>
                <input type="text" value={nome} onChange={e => setNome(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg" />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Telefone</label>
                <input type="tel" value={telefone} onChange={e => setTelefone(e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg" />
              </div>
              <div>
                <label className="text-sm font-bold mb-1 block">Email</label>
                <input type="email" value={cliente?.email || ""} disabled
                  className="w-full px-4 py-2 border rounded-lg bg-gray-50 text-muted-foreground" />
              </div>
              <div className="flex gap-2">
                <Button size="sm" onClick={handleSalvarPerfil} disabled={salvando}
                  style={{ background: `var(--cor-primaria, #E31A24)` }} className="text-white">
                  {salvando ? "Salvando..." : "Salvar"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditando(false)}>Cancelar</Button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold">{cliente?.nome}</p>
                  <p className="text-sm text-muted-foreground">{cliente?.email}</p>
                  <p className="text-sm text-muted-foreground">{cliente?.telefone}</p>
                </div>
                <Button size="sm" variant="outline" onClick={() => setEditando(true)}>Editar</Button>
              </div>
            </div>
          )}
        </Card>

        {/* Endereços */}
        <Card className="p-4 md:p-6 mb-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <MapPin className="w-5 h-5" />
            Meus Endereços
          </h2>

          {loading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-16 bg-muted rounded" />
              <div className="h-16 bg-muted rounded" />
            </div>
          ) : enderecos.length > 0 ? (
            <div className="space-y-3">
              {enderecos.map(end => (
                <div key={end.id} className={`p-3 border rounded-lg flex justify-between items-start ${end.padrao ? "border-2" : ""}`}
                  style={end.padrao ? { borderColor: `var(--cor-primaria, #E31A24)` } : {}}>
                  <div>
                    <div className="flex items-center gap-2">
                      {end.apelido && <span className="font-bold text-sm">{end.apelido}</span>}
                      {end.padrao && (
                        <span className="text-xs px-2 py-0.5 rounded-full text-white"
                          style={{ background: `var(--cor-primaria, #E31A24)` }}>Padrão</span>
                      )}
                    </div>
                    <p className="text-sm mt-1">
                      {end.endereco_completo}
                      {end.numero ? `, ${end.numero}` : ""}
                      {end.complemento ? ` - ${end.complemento}` : ""}
                    </p>
                    {end.bairro && <p className="text-xs text-muted-foreground">{end.bairro}</p>}
                  </div>
                  <div className="flex gap-1 shrink-0 ml-2">
                    {!end.padrao && (
                      <Button size="sm" variant="ghost" onClick={() => handleDefinirPadrao(end.id)} title="Definir como padrão">
                        <Star className="w-4 h-4" />
                      </Button>
                    )}
                    <Button size="sm" variant="ghost" onClick={() => handleRemoverEndereco(end.id)} title="Remover"
                      className="text-red-500 hover:text-red-700">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Nenhum endereço salvo. Adicione um no checkout.</p>
          )}
        </Card>

        {/* Ações */}
        <div className="space-y-3">
          <Button variant="outline" className="w-full" onClick={() => navigate("/orders")}>
            Meus Pedidos
          </Button>
          <Button variant="outline" className="w-full text-red-600 hover:text-red-700 hover:bg-red-50"
            onClick={() => { logout(); navigate("/"); }}>
            Sair da Conta
          </Button>
        </div>
      </div>
    </div>
  );
}
