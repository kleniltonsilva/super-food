import { useState } from "react";
import { useMotoboyAuth } from "@/motoboy/contexts/MotoboyAuthContext";
import { useAtualizarStatus, useAlterarSenha } from "@/motoboy/hooks/useMotoboyQueries";
import MotoboyLayout from "@/motoboy/components/MotoboyLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import {
  User, Phone, MapPin, Wifi, WifiOff, Lock, LogOut, Loader2,
  ChevronDown, ChevronUp, Hash,
} from "lucide-react";

export default function MotoboyPerfil() {
  const { motoboy, logout, refreshMotoboy } = useMotoboyAuth();
  const atualizarStatus = useAtualizarStatus();
  const alterarSenha = useAlterarSenha();

  const [showSenha, setShowSenha] = useState(false);
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");

  if (!motoboy) return null;

  async function handleToggleStatus() {
    try {
      await atualizarStatus.mutateAsync({ disponivel: !motoboy!.disponivel });
      await refreshMotoboy();
      toast.success(motoboy!.disponivel ? "Status: Offline" : "Status: Online");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao atualizar status";
      toast.error(msg);
    }
  }

  async function handleAlterarSenha(e: React.FormEvent) {
    e.preventDefault();
    if (!senhaAtual.trim() || !novaSenha.trim() || !confirmarSenha.trim()) {
      toast.error("Preencha todos os campos");
      return;
    }
    if (novaSenha !== confirmarSenha) {
      toast.error("As senhas não coincidem");
      return;
    }
    if (novaSenha.trim().length < 6) {
      toast.error("A nova senha deve ter no mínimo 6 caracteres");
      return;
    }
    try {
      await alterarSenha.mutateAsync({ senha_atual: senhaAtual.trim(), nova_senha: novaSenha.trim() });
      toast.success("Senha alterada com sucesso!");
      setSenhaAtual("");
      setNovaSenha("");
      setConfirmarSenha("");
      setShowSenha(false);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || "Erro ao alterar senha";
      toast.error(msg);
    }
  }

  async function handleLogout() {
    try {
      // Marcar como offline antes de sair
      if (motoboy?.disponivel) {
        await atualizarStatus.mutateAsync({ disponivel: false });
      }
    } catch {
      // Ignore — vamos fazer logout de qualquer forma
    }
    logout();
  }

  return (
    <MotoboyLayout>
      <div className="space-y-4 p-4">
        {/* Info do Motoboy */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-green-500 to-green-700 text-xl font-bold text-white shadow-lg shadow-green-500/20">
              {(motoboy.nome || "M").charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">{motoboy.nome}</h2>
              <p className="text-sm text-gray-400">@{motoboy.usuario}</p>
            </div>
          </div>

          <div className="space-y-2.5">
            {motoboy.telefone && (
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <Phone className="h-4 w-4 text-gray-500" />
                {motoboy.telefone}
              </div>
            )}
            {motoboy.restaurante?.nome && (
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <MapPin className="h-4 w-4 text-gray-500" />
                {motoboy.restaurante.nome_fantasia || motoboy.restaurante.nome}
              </div>
            )}
            {motoboy.ordem_hierarquia != null && (
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <Hash className="h-4 w-4 text-gray-500" />
                Posição na fila: #{motoboy.ordem_hierarquia}
              </div>
            )}
          </div>
        </div>

        {/* Status Online/Offline */}
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {motoboy.disponivel ? (
                <>
                  <div className="h-3 w-3 rounded-full bg-green-500" />
                  <span className="font-semibold text-green-400">ONLINE — Disponível</span>
                </>
              ) : (
                <>
                  <div className="h-3 w-3 rounded-full bg-gray-500" />
                  <span className="font-semibold text-gray-400">OFFLINE — Não recebendo</span>
                </>
              )}
            </div>
          </div>

          <Button
            className={`mt-3 h-12 w-full font-bold ${
              motoboy.disponivel
                ? "bg-gray-700 text-white hover:bg-gray-600"
                : "bg-green-600 text-white hover:bg-green-700"
            }`}
            onClick={handleToggleStatus}
            disabled={atualizarStatus.isPending}
          >
            {atualizarStatus.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : motoboy.disponivel ? (
              <WifiOff className="mr-2 h-4 w-4" />
            ) : (
              <Wifi className="mr-2 h-4 w-4" />
            )}
            {motoboy.disponivel ? "Ficar Offline" : "Ficar Online"}
          </Button>

          {/* Status de rota */}
          <div className="mt-3 rounded-lg bg-gray-800 px-3 py-2 text-center text-sm">
            {motoboy.em_rota ? (
              <span className="text-blue-400">
                Em Rota — {motoboy.entregas_pendentes || 0} entrega(s) pendente(s)
              </span>
            ) : (
              <span className="text-gray-500">Sem rota ativa</span>
            )}
          </div>
        </div>

        {/* Alterar Senha */}
        <div className="rounded-xl border border-gray-800 bg-gray-900">
          <button
            onClick={() => setShowSenha(!showSenha)}
            className="flex w-full items-center justify-between p-4"
          >
            <div className="flex items-center gap-2 text-gray-300">
              <Lock className="h-4 w-4 text-gray-500" />
              <span className="text-sm font-medium">Alterar Senha</span>
            </div>
            {showSenha ? (
              <ChevronUp className="h-4 w-4 text-gray-500" />
            ) : (
              <ChevronDown className="h-4 w-4 text-gray-500" />
            )}
          </button>

          {showSenha && (
            <form onSubmit={handleAlterarSenha} className="space-y-3 border-t border-gray-800 p-4">
              <div>
                <label className="text-xs text-gray-400">Senha atual</label>
                <Input
                  type="password"
                  value={senhaAtual}
                  onChange={(e) => setSenhaAtual(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                  autoComplete="current-password"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">Nova senha</label>
                <Input
                  type="password"
                  value={novaSenha}
                  onChange={(e) => setNovaSenha(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                  autoComplete="new-password"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400">Confirmar nova senha</label>
                <Input
                  type="password"
                  value={confirmarSenha}
                  onChange={(e) => setConfirmarSenha(e.target.value)}
                  className="mt-1 border-gray-700 bg-gray-800 text-white"
                  autoComplete="new-password"
                />
              </div>
              <Button
                type="submit"
                className="w-full bg-green-600 font-bold hover:bg-green-700"
                disabled={alterarSenha.isPending}
              >
                {alterarSenha.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Lock className="mr-2 h-4 w-4" />
                )}
                Alterar Senha
              </Button>
            </form>
          )}
        </div>

        {/* Logout */}
        <Button
          variant="outline"
          className="h-12 w-full border-red-600/50 text-red-500 hover:bg-red-600/10"
          onClick={handleLogout}
        >
          <LogOut className="mr-2 h-4 w-4" />
          Sair
        </Button>

        {/* Versão do app */}
        <p className="pt-2 text-center text-[10px] text-gray-700">
          Derekh Entregador v1.1.0
        </p>
      </div>
    </MotoboyLayout>
  );
}
